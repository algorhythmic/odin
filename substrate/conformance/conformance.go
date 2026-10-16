// Package conformance runs the I0 fixture set (substrate/schemas
// fixtures/cases.json) through the Go implementation and returns one result
// per case in the results format of substrate/schemas README §3. The same
// fixtures run through the Python implementation; the compare script checks
// both against `expected` (ODIN-ADR-008 exit evidence).
//
// A fixture that does not match its own input schema is a defect in the
// fixture set, not a case outcome: Run fails loudly instead of reporting it.
package conformance

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/fs"
	"reflect"
	"sort"
	"strings"

	"github.com/algorhythmic/odin/substrate/eventlog"
	"github.com/algorhythmic/odin/substrate/records"
	"github.com/algorhythmic/odin/substrate/schemacheck"
	"github.com/algorhythmic/odin/substrate/schemas"
	"github.com/algorhythmic/odin/substrate/strictjson"
)

// Paths of the case index and the operation input schemas, relative to
// substrate/schemas.
const (
	CasesPath        = "fixtures/cases.json"
	CasesSchemaPath  = "fixtures/cases.schema.json"
	InputsSchemaPath = "fixtures/inputs.schema.json"
)

// Result is one case's result: `outcome` plus the extra keys its operation
// defines (README §4), or `steps` for a sequence operation. Keys that do not
// apply are absent, never null; `cursor_after` is the one key whose value
// may be null. encoding/json writes map keys sorted, which is the order the
// results file requires.
type Result map[string]any

// Case is one entry of fixtures/cases.json.
type Case struct {
	ID        string          `json:"id"`
	Group     string          `json:"group"`
	Operation string          `json:"operation"`
	Schema    *string         `json:"schema,omitempty"`
	Input     string          `json:"input"`
	Expected  json.RawMessage `json:"expected"`
	Cites     []string        `json:"cites"`
	Note      string          `json:"note"`
}

// Runner runs cases against one loaded contract.
type Runner struct {
	fsys      fs.FS
	validator *schemacheck.Validator
	catalog   *eventlog.Catalogue
	fields    []string // commitment fields, for check_mapping_coverage
}

// NewRunner loads the embedded contract (schemas.FS).
func NewRunner() (*Runner, error) {
	return NewRunnerFS(schemas.FS)
}

// NewRunnerFS loads the contract from fsys, rooted like substrate/schemas.
func NewRunnerFS(fsys fs.FS) (*Runner, error) {
	cat, err := eventlog.LoadCatalogueFS(fsys)
	if err != nil {
		return nil, err
	}
	v, err := schemacheck.NewFS(fsys, cat)
	if err != nil {
		return nil, err
	}
	fields, err := records.CommitmentFieldsFS(fsys)
	if err != nil {
		return nil, err
	}
	return &Runner{fsys: fsys, validator: v, catalog: cat, fields: fields}, nil
}

// Cases loads fixtures/cases.json after validating it against
// fixtures/cases.schema.json, and checks that ids are unique and prefixed
// by their group.
func (r *Runner) Cases() ([]Case, error) {
	data, err := fs.ReadFile(r.fsys, CasesPath)
	if err != nil {
		return nil, err
	}
	doc, err := strictjson.Decode(data)
	if err != nil {
		return nil, fmt.Errorf("conformance: %s: %w", CasesPath, err)
	}
	ptrs, err := r.validator.ValidateValue(CasesSchemaPath, doc)
	if err != nil {
		return nil, err
	}
	if len(ptrs) > 0 {
		return nil, fmt.Errorf("conformance: fixture defect: %s fails %s at %v", CasesPath, CasesSchemaPath, ptrs)
	}
	var cases []Case
	if err := strictjson.Unmarshal(data, &cases); err != nil {
		return nil, fmt.Errorf("conformance: %s: %w", CasesPath, err)
	}
	seen := map[string]bool{}
	for _, c := range cases {
		if seen[c.ID] {
			return nil, fmt.Errorf("conformance: fixture defect: case id %s repeated", c.ID)
		}
		seen[c.ID] = true
		if !strings.HasPrefix(c.ID, c.Group+"/") {
			return nil, fmt.Errorf("conformance: fixture defect: case %s is not in group %s", c.ID, c.Group)
		}
	}
	return cases, nil
}

// Run runs every case and returns the results by case id.
func Run() (map[string]Result, error) {
	r, err := NewRunner()
	if err != nil {
		return nil, err
	}
	cases, err := r.Cases()
	if err != nil {
		return nil, err
	}
	return r.RunAll(cases)
}

// RunAll runs cases and returns the results by case id. The first case
// that cannot run (a fixture defect) stops the run with an error naming it.
func (r *Runner) RunAll(cases []Case) (map[string]Result, error) {
	out := make(map[string]Result, len(cases))
	for _, c := range cases {
		res, err := r.RunCase(c)
		if err != nil {
			return nil, fmt.Errorf("conformance: case %s: %w", c.ID, err)
		}
		out[c.ID] = res
	}
	return out, nil
}

// RunCase runs one case. For every operation except validate, the input is
// first checked against inputs.schema.json#/$defs/<operation> and decoded
// strictly into the operation's typed input; a failure there is a fixture
// defect and returns an error.
func (r *Runner) RunCase(c Case) (Result, error) {
	data, err := fs.ReadFile(r.fsys, c.Input)
	if err != nil {
		return nil, err
	}
	if c.Operation == "validate" {
		if c.Schema == nil {
			return nil, fmt.Errorf("fixture defect: validate case without schema")
		}
		return r.validate(*c.Schema, data)
	}
	op, ok := operations[c.Operation]
	if !ok {
		return nil, fmt.Errorf("unknown operation %q", c.Operation)
	}
	doc, err := strictjson.Decode(data)
	if err != nil {
		return nil, fmt.Errorf("fixture defect: %s: %w", c.Input, err)
	}
	ref := InputsSchemaPath + "#/$defs/" + c.Operation
	ptrs, err := r.validator.ValidateValue(ref, doc)
	if err != nil {
		return nil, err
	}
	if len(ptrs) > 0 {
		return nil, fmt.Errorf("fixture defect: %s fails %s at %v", c.Input, ref, ptrs)
	}
	res, err := op(r, data)
	if err != nil {
		return nil, fmt.Errorf("%s: %w", c.Input, err)
	}
	return res, nil
}

func (r *Runner) validate(schema string, data []byte) (Result, error) {
	res, err := r.validator.Validate(schema, data)
	if err != nil {
		return nil, err
	}
	out := Result{"outcome": res.Outcome}
	if res.Outcome == schemacheck.SchemaInvalid {
		out["errors"] = res.Errors
	}
	return out, nil
}

// Mismatch is a case whose result differs from its expected value.
type Mismatch struct {
	ID       string
	Expected string // compact JSON
	Got      string // compact JSON
}

// Compare returns, sorted by case id, every case whose result is missing
// or differs from `expected`, comparing decoded JSON values.
func Compare(cases []Case, results map[string]Result) ([]Mismatch, error) {
	var out []Mismatch
	for _, c := range cases {
		var want any
		if err := json.Unmarshal(c.Expected, &want); err != nil {
			return nil, fmt.Errorf("conformance: case %s expected: %w", c.ID, err)
		}
		res, ok := results[c.ID]
		gotJSON := []byte("<missing>")
		var got any
		if ok {
			b, err := json.Marshal(res)
			if err != nil {
				return nil, fmt.Errorf("conformance: case %s result: %w", c.ID, err)
			}
			gotJSON = b
			if err := json.Unmarshal(b, &got); err != nil {
				return nil, err
			}
		}
		if !ok || !reflect.DeepEqual(want, got) {
			var exp bytes.Buffer
			if err := json.Compact(&exp, c.Expected); err != nil {
				return nil, err
			}
			out = append(out, Mismatch{ID: c.ID, Expected: exp.String(), Got: string(gotJSON)})
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out, nil
}

// Encode writes results in the format of README §3: one JSON object, keys
// sorted, two-space indentation, a trailing newline, no HTML escaping.
func Encode(results map[string]Result) ([]byte, error) {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	enc.SetIndent("", "  ")
	if err := enc.Encode(results); err != nil { // Encode appends "\n"
		return nil, err
	}
	return buf.Bytes(), nil
}
