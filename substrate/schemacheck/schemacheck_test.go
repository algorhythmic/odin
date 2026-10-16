package schemacheck

import (
	"io/fs"
	"reflect"
	"strings"
	"testing"
	"testing/fstest"

	"github.com/algorhythmic/odin/substrate/eventlog"
	"github.com/algorhythmic/odin/substrate/schemas"
)

func TestContractCompiles(t *testing.T) {
	v, err := New()
	if err != nil {
		t.Fatal(err)
	}
	n := 0
	err = fs.WalkDir(schemas.FS, ".", func(p string, d fs.DirEntry, err error) error {
		if err == nil && !d.IsDir() && strings.HasSuffix(p, ".schema.json") {
			n++
		}
		return err
	})
	if err != nil {
		t.Fatal(err)
	}
	if got := len(v.Paths()); got != n || n < 20 {
		t.Fatalf("%d schemas registered, %d on disk", got, n)
	}
	if _, err := v.Schema("fixtures/inputs.schema.json#/$defs/reconcile"); err != nil {
		t.Fatal(err)
	}
	if _, err := v.Schema("../outside.schema.json"); err == nil {
		t.Fatal("path outside the contract accepted")
	}
}

const testSchema = `{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://odin.invalid/substrate/schemas/test/t.schema.json",
  "type": "object",
  "additionalProperties": false,
  "required": ["a", "b", "c"],
  "properties": {
    "a": {"type": "string", "pattern": "^[0-9]{2}$"},
    "b": {"anyOf": [{"type": "integer", "minimum": 5}, {"type": "null"}]},
    "c": {"type": "array", "items": {"$ref": "other.schema.json#/$defs/item"}},
    "d": {"not": {"const": 1}},
    "e": {"type": "array", "contains": {"const": "x"}},
    "f": {"oneOf": [{"type": "string"}, {"type": "string", "minLength": 1}]},
    "g": {"type": "object", "additionalProperties": false, "properties": {"k": {"type": "integer"}}}
  },
  "allOf": [
    {"if": {"required": ["a"], "properties": {"a": {"const": "00"}}},
     "then": {"properties": {"g": {"required": ["k"], "properties": {"k": {"minimum": 3}}}}}}
  ]
}`

const otherSchema = `{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://odin.invalid/substrate/schemas/test/other.schema.json",
  "$defs": {"item": {"type": "object", "additionalProperties": false, "required": ["n"],
    "properties": {"n": {"type": "integer", "maximum": 9}}}}
}`

func testValidator(t *testing.T, files map[string]string) (*Validator, error) {
	t.Helper()
	cat, err := eventlog.LoadCatalogue()
	if err != nil {
		t.Fatal(err)
	}
	m := fstest.MapFS{}
	for p, data := range files {
		m[p] = &fstest.MapFile{Data: []byte(data)}
	}
	return NewFS(m, cat)
}

func TestErrorPointers(t *testing.T) {
	v, err := testValidator(t, map[string]string{"test/t.schema.json": testSchema, "test/other.schema.json": otherSchema})
	if err != nil {
		t.Fatal(err)
	}
	cases := []struct {
		name string
		doc  string
		want []string
	}{
		{"valid", `{"a":"12","b":null,"c":[{"n":1}]}`, nil},
		{"missing keys", `{"a":"12"}`, []string{"/b", "/c"}},
		{"unknown keys escaped", `{"a":"12","b":5,"c":[],"x/y":1,"m~n":2}`, []string{"/m~0n", "/x~1y"}},
		{"anyOf hides sub-errors", `{"a":"12","b":3,"c":[]}`, []string{"/b"}},
		{"through ref and items", `{"a":"12","b":5,"c":[{"n":1},{"n":10,"z":0}]}`, []string{"/c/1/n", "/c/1/z"}},
		{"not", `{"a":"12","b":5,"c":[],"d":1}`, []string{"/d"}},
		{"contains", `{"a":"12","b":5,"c":[],"e":["y"]}`, []string{"/e"}},
		{"oneOf", `{"a":"12","b":5,"c":[],"f":"two"}`, []string{"/f"}},
		{"if then leaf", `{"a":"00","b":5,"c":[],"g":{"k":1}}`, []string{"/g/k"}},
		{"if then required", `{"a":"00","b":5,"c":[],"g":{}}`, []string{"/g/k"}},
		{"pattern end is end of string", "{\"a\":\"12\\n\",\"b\":5,\"c\":[]}", []string{"/a"}},
		{"root type", `[]`, []string{""}},
	}
	for _, c := range cases {
		res, err := v.Validate("test/t.schema.json", []byte(c.doc))
		if err != nil {
			t.Fatalf("%s: %v", c.name, err)
		}
		if c.want == nil {
			if res.Outcome != SchemaValid || res.Errors != nil {
				t.Errorf("%s: %+v", c.name, res)
			}
			continue
		}
		if res.Outcome != SchemaInvalid || !reflect.DeepEqual(res.Errors, c.want) {
			t.Errorf("%s: got %+v, want %v", c.name, res, c.want)
		}
	}
}

func TestDuplicateKeysRejectBeforeValidation(t *testing.T) {
	v, err := testValidator(t, map[string]string{"test/t.schema.json": testSchema, "test/other.schema.json": otherSchema})
	if err != nil {
		t.Fatal(err)
	}
	// Missing b and c would be schema errors; only the duplicate is reported.
	res, err := v.Validate("test/t.schema.json", []byte(`{"a":"12","a":"13","g":{"k":1,"k":2}}`))
	if err != nil {
		t.Fatal(err)
	}
	if res.Outcome != SchemaInvalid || !reflect.DeepEqual(res.Errors, []string{"/a", "/g/k"}) {
		t.Fatalf("got %+v", res)
	}
	if _, err := v.Validate("test/t.schema.json", []byte(`{"a":`)); err == nil {
		t.Fatal("malformed JSON gave no error")
	}
}

func TestNeverFetches(t *testing.T) {
	remote := strings.Replace(otherSchema, `"$defs"`, `"$ref": "https://example.invalid/remote.schema.json", "$defs"`, 1)
	_, err := testValidator(t, map[string]string{"test/t.schema.json": testSchema, "test/other.schema.json": remote})
	if err == nil || !strings.Contains(err.Error(), "refusing to load") {
		t.Fatalf("err = %v, want a refused load", err)
	}
}

func TestIDMustMatchPath(t *testing.T) {
	_, err := testValidator(t, map[string]string{"test/moved.schema.json": testSchema, "test/other.schema.json": otherSchema})
	if err == nil || !strings.Contains(err.Error(), "$id") {
		t.Fatalf("err = %v, want an $id mismatch", err)
	}
}

func TestEnvelopeCatalogueCheck(t *testing.T) {
	v, err := New()
	if err != nil {
		t.Fatal(err)
	}
	env := `{"id":"01JAEV00000000000000000001","envelope":1,"namespace":"odin_history","producer":"saga",
"kind":"KIND","scope":{},"source_seq":null,"received_at":"2026-10-16T09:00:00Z","causation":null,
"correlation":null,"payload":{},"payload_ref":null,"dedupe_key":"saga:1","wake":"WAKE","state":"received"}`
	run := func(kind, wake string) Result {
		res, err := v.Validate(EnvelopeSchema, []byte(strings.NewReplacer("KIND", kind, "WAKE", wake).Replace(env)))
		if err != nil {
			t.Fatal(err)
		}
		return res
	}
	if res := run("run.state.accepted", "none"); res.Outcome != SchemaValid {
		t.Errorf("known kind: %+v", res)
	}
	if res := run("run.state", "none"); res.Outcome != UnknownKind || res.Errors != nil {
		t.Errorf("unknown kind: %+v", res)
	}
	// The catalogue check runs only on a schema-valid envelope.
	if res := run("run.state", "loud"); res.Outcome != SchemaInvalid || !reflect.DeepEqual(res.Errors, []string{"/wake"}) {
		t.Errorf("unknown kind and invalid wake: %+v", res)
	}
	// Other schemas get no catalogue check.
	res, err := v.Validate("kinds.schema.json", []byte(`{"version":1,"source":"x","kinds":[{"kind":"not.catalogued",
"default_wake":"none","conditional":false,"handling":"h","control":false,"source":"s"}]}`))
	if err != nil || res.Outcome != SchemaValid {
		t.Errorf("kinds.schema.json: %+v, %v", res, err)
	}
}
