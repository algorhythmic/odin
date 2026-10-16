// Package schemacheck validates JSON documents against the substrate
// contract (substrate/schemas README §2 and §4.1). It registers every
// *.schema.json file of the embedded contract under its `$id`, never
// fetches anything, and reports failures as the sorted set of JSON
// pointers that README §4.1 defines, so the Go and Python implementations
// produce identical error sets.
package schemacheck

import (
	"errors"
	"fmt"
	"io/fs"
	"path"
	"sort"
	"strings"
	"sync"

	"github.com/santhosh-tekuri/jsonschema/v6"
	"github.com/santhosh-tekuri/jsonschema/v6/kind"

	"github.com/algorhythmic/odin/substrate/eventlog"
	"github.com/algorhythmic/odin/substrate/schemas"
	"github.com/algorhythmic/odin/substrate/strictjson"
)

// BaseID is the `$id` prefix of every contract schema: a non-resolvable
// placeholder under which the files are registered locally (README §2).
const BaseID = "https://odin.invalid/substrate/schemas/"

// EnvelopeSchema is the schema whose valid documents also get the
// catalogue check (README §4.1 step 3).
const EnvelopeSchema = "envelope.schema.json"

// Outcomes of validate (README §4.9).
const (
	SchemaValid   = "schema_valid"
	SchemaInvalid = "schema_invalid"
	UnknownKind   = "unknown_kind"
)

// Result is the result of Validate: an outcome and, only with
// schema_invalid, the sorted and de-duplicated JSON pointers that failed.
type Result struct {
	Outcome string
	Errors  []string
}

// Validator holds the compiled contract schemas and the kind catalogue.
// It is safe for concurrent use.
type Validator struct {
	mu       sync.Mutex
	compiler *jsonschema.Compiler
	compiled map[string]*jsonschema.Schema
	paths    []string
	catalog  *eventlog.Catalogue
}

// New loads the embedded contract (schemas.FS).
func New() (*Validator, error) {
	cat, err := eventlog.LoadCatalogue()
	if err != nil {
		return nil, err
	}
	return NewFS(schemas.FS, cat)
}

// NewFS loads every *.schema.json under fsys, which is rooted like
// substrate/schemas. Each file must decode strictly and carry the `$id`
// BaseID + its path; every schema is compiled up front, so a broken
// reference fails here rather than mid-run.
func NewFS(fsys fs.FS, cat *eventlog.Catalogue) (*Validator, error) {
	c := jsonschema.NewCompiler()
	c.DefaultDraft(jsonschema.Draft2020)
	c.UseLoader(refuseLoader{})
	v := &Validator{compiler: c, compiled: map[string]*jsonschema.Schema{}, catalog: cat}
	err := fs.WalkDir(fsys, ".", func(p string, d fs.DirEntry, err error) error {
		if err != nil || d.IsDir() || !strings.HasSuffix(p, ".schema.json") {
			return err
		}
		data, err := fs.ReadFile(fsys, p)
		if err != nil {
			return err
		}
		doc, err := strictjson.Decode(data)
		if err != nil {
			return fmt.Errorf("schemacheck: %s: %w", p, err)
		}
		obj, _ := doc.(map[string]any)
		if id, _ := obj["$id"].(string); id != BaseID+p {
			return fmt.Errorf("schemacheck: %s has $id %q, want %q", p, id, BaseID+p)
		}
		if err := c.AddResource(BaseID+p, doc); err != nil {
			return fmt.Errorf("schemacheck: %s: %w", p, err)
		}
		v.paths = append(v.paths, p)
		return nil
	})
	if err != nil {
		return nil, err
	}
	if len(v.paths) == 0 {
		return nil, errors.New("schemacheck: no *.schema.json files found")
	}
	sort.Strings(v.paths)
	for _, p := range v.paths {
		if _, err := v.Schema(p); err != nil {
			return nil, err
		}
	}
	return v, nil
}

// refuseLoader is the loader for every URL not registered from the
// contract: the `$id`s are placeholders and are never fetched (README §2).
type refuseLoader struct{}

func (refuseLoader) Load(url string) (any, error) {
	return nil, fmt.Errorf("schemacheck: refusing to load %s: only the embedded contract is used", url)
}

// Paths returns the registered schema paths, sorted.
func (v *Validator) Paths() []string {
	return append([]string(nil), v.paths...)
}

// Schema returns the compiled schema for ref, a path relative to
// substrate/schemas with an optional fragment, for example
// "records/effect.schema.json" or "fixtures/inputs.schema.json#/$defs/combine".
func (v *Validator) Schema(ref string) (*jsonschema.Schema, error) {
	v.mu.Lock()
	defer v.mu.Unlock()
	if s, ok := v.compiled[ref]; ok {
		return s, nil
	}
	file, _, _ := strings.Cut(ref, "#")
	if path.Clean(file) != file || strings.HasPrefix(file, "../") || !strings.HasSuffix(file, ".schema.json") {
		return nil, fmt.Errorf("schemacheck: %q is not a contract schema path", ref)
	}
	s, err := v.compiler.Compile(BaseID + ref)
	if err != nil {
		return nil, fmt.Errorf("schemacheck: compile %s: %w", ref, err)
	}
	v.compiled[ref] = s
	return s, nil
}

// Validate is the `validate` operation of README §4.1: decode strictly (a
// duplicate key rejects the document with the duplicated keys' pointers),
// validate against the schema at ref (failures as error pointers), and for
// a valid envelope check its kind against kinds.json. The error is non-nil
// only when ref cannot be compiled or data is not JSON at all.
func (v *Validator) Validate(ref string, data []byte) (Result, error) {
	doc, err := strictjson.Decode(data)
	if err != nil {
		var dup *strictjson.DuplicateKeyError
		if errors.As(err, &dup) {
			return Result{Outcome: SchemaInvalid, Errors: dup.Pointers}, nil
		}
		return Result{}, err
	}
	ptrs, err := v.ValidateValue(ref, doc)
	if err != nil {
		return Result{}, err
	}
	if len(ptrs) > 0 {
		return Result{Outcome: SchemaInvalid, Errors: ptrs}, nil
	}
	if ref == EnvelopeSchema {
		obj, _ := doc.(map[string]any)
		k, _ := obj["kind"].(string)
		if !v.catalog.KnownKind(k) {
			return Result{Outcome: UnknownKind}, nil
		}
	}
	return Result{Outcome: SchemaValid}, nil
}

// ValidateValue validates an already decoded document (numbers as
// json.Number, as strictjson.Decode produces) against the schema at ref and
// returns the error pointers of README §4.1 step 2, or nil when it is valid.
func (v *Validator) ValidateValue(ref string, doc any) ([]string, error) {
	s, err := v.Schema(ref)
	if err != nil {
		return nil, err
	}
	err = s.Validate(doc)
	if err == nil {
		return nil, nil
	}
	var verr *jsonschema.ValidationError
	if !errors.As(err, &verr) {
		return nil, err
	}
	set := map[string]bool{}
	collect(verr, set)
	ptrs := make([]string, 0, len(set))
	for p := range set {
		ptrs = append(ptrs, p)
	}
	sort.Strings(ptrs) // byte order of UTF-8 is code-point order
	return ptrs, nil
}

// collect walks the error tree as README §4.1 step 2 prescribes: an
// unknown key reports the key's own pointer; a missing required key reports
// the missing key's pointer; anyOf, oneOf, not, contains, minContains and
// maxContains report the location of the value they apply to and hide their
// sub-errors; every other error is descended to its leaves, which report
// their instance location.
func collect(e *jsonschema.ValidationError, set map[string]bool) {
	loc := pointer(e.InstanceLocation)
	switch k := e.ErrorKind.(type) {
	case *kind.AdditionalProperties:
		for _, p := range k.Properties {
			set[strictjson.Pointer(loc, p)] = true
		}
		return
	case *kind.Required:
		for _, p := range k.Missing {
			set[strictjson.Pointer(loc, p)] = true
		}
		return
	case *kind.AnyOf, *kind.OneOf, *kind.Not, *kind.Contains, *kind.MinContains, *kind.MaxContains:
		set[loc] = true
		return
	}
	if len(e.Causes) == 0 {
		set[loc] = true
		return
	}
	for _, c := range e.Causes {
		collect(c, set)
	}
}

func pointer(tokens []string) string {
	var b strings.Builder
	for _, t := range tokens {
		b.WriteString(strictjson.Pointer("", t))
	}
	return b.String()
}
