package validation

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDecodeJSONStrict(t *testing.T) {
	for _, input := range []string{
		`{"outer":{"x":1,"x":2}}`,
		`{"n":9007199254740992}`,
		`{"n":1e999}`,
		`{"n":1.0000000000000001}`,
		`{"n":1e-9999}`,
		`{"n":1} {"n":2}`,
		`{"n":NaN}`,
		`{"text":"\uD800"}`,
		`{"text":"\uDC00"}`,
	} {
		if _, err := DecodeJSON([]byte(input)); err == nil {
			t.Errorf("accepted invalid JSON %s", input)
		}
	}
	if _, err := DecodeJSON([]byte(`{"n":9007199254740991}`)); err != nil {
		t.Fatalf("rejected maximum safe integer: %v", err)
	}
	for _, input := range []string{`{"n":0.1}`, `{"text":"\uD800\uDC00"}`} {
		if _, err := DecodeJSON([]byte(input)); err != nil {
			t.Fatalf("rejected valid JSON %s: %v", input, err)
		}
	}
	if _, err := DecodeJSON([]byte{'"', 0xff, '"'}); err == nil {
		t.Fatal("accepted invalid UTF-8")
	}
}

func TestFormatsInSelectedBranches(t *testing.T) {
	v := New(t.TempDir())
	branch := map[string]any{
		"oneOf": []any{
			map[string]any{"type": "string", "format": "date-time"},
			map[string]any{"type": "integer"},
		},
	}
	if err := v.checkFormats(branch, "2026-13-01T00:00:00Z", "test.schema.json", 0); err == nil {
		t.Fatal("invalid calendar date escaped selected oneOf branch")
	}
	if err := v.checkFormats(branch, float64(3), "test.schema.json", 0); err != nil {
		t.Fatalf("valid integer branch rejected: %v", err)
	}
	conditional := map[string]any{
		"if":   map[string]any{"properties": map[string]any{"kind": map[string]any{"const": "timed"}}},
		"then": map[string]any{"properties": map[string]any{"value": map[string]any{"format": "date-time"}}},
	}
	if err := v.checkFormats(conditional, map[string]any{"kind": "timed", "value": "bad"}, "test.schema.json", 0); err == nil {
		t.Fatal("invalid date-time escaped conditional branch")
	}
}

func TestOneOfFormatShapesAreAssertions(t *testing.T) {
	dir := t.TempDir()
	schema := `{"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"https://odin.invalid/schemas/v1/test.schema.json","oneOf":[{"type":"string","format":"date-time"},{"type":"string","format":"ulid"}]}`
	if err := os.WriteFile(filepath.Join(dir, "test.schema.json"), []byte(schema), 0600); err != nil {
		t.Fatal(err)
	}
	v := New(dir)
	for _, good := range []string{`"2026-10-16T01:02:03Z"`, `"01ARZ3NDEKTSV4RRFFQ69G5FAV"`} {
		if err := v.Validate("test.schema.json", []byte(good)); err != nil {
			t.Fatalf("rejected %s: %v", good, err)
		}
	}
	for _, bad := range []string{`"2026-13-16T01:02:03Z"`, `"not either format"`} {
		if err := v.Validate("test.schema.json", []byte(bad)); err == nil {
			t.Fatalf("accepted %s", bad)
		}
	}
}

func TestAnyOfDateTimeCalendarAssertion(t *testing.T) {
	dir := t.TempDir()
	schema := `{"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"https://odin.invalid/schemas/v1/test.schema.json","anyOf":[{"type":"string","format":"date-time"},{"type":"string","format":"ulid"}]}`
	if err := os.WriteFile(filepath.Join(dir, "test.schema.json"), []byte(schema), 0600); err != nil {
		t.Fatal(err)
	}
	v := New(dir)
	if err := v.Validate("test.schema.json", []byte(`"0001-01-01T00:00:00Z"`)); err != nil {
		t.Fatalf("rejected year 0001: %v", err)
	}
	if err := v.Validate("test.schema.json", []byte(`"0000-01-01T00:00:00Z"`)); err == nil {
		t.Fatal("accepted year 0000 through anyOf")
	}
}

func TestLocalRefsAndPureSemantics(t *testing.T) {
	if err := checkLocalRefs(map[string]any{"$ref": "https://example.com/schema"}); err == nil {
		t.Fatal("remote reference accepted")
	}
	if err := checkLocalRefs(map[string]any{"$ref": "common.schema.json#/$defs/ulid"}); err != nil {
		t.Fatal(err)
	}
	last, next := int64(4), int64(9)
	if got, err := ClassifyIntake(&last, &next, false); err != nil || got != "new" {
		t.Fatalf("non-dense Saga sequence rejected: %s", got)
	}
	negative, zero := int64(-1), int64(0)
	if _, err := ClassifyIntake(&negative, &next, false); err == nil {
		t.Fatal("accepted negative source sequence")
	}
	if _, err := CheckRevision(zero, zero); err == nil {
		t.Fatal("accepted zero revision")
	}
	if _, err := CheckOwnership(zero, zero); err == nil {
		t.Fatal("accepted zero ownership generation")
	}
	result, err := ReconcileOperation("unknown_expired")
	if err != nil || result.State != "unknown" || !strings.Contains(result.Action, "operator") {
		t.Fatalf("unknown_expired was retried: %+v, %v", result, err)
	}
	result, err = ReconcileOperation("superseded")
	if err != nil || result.State != "superseded" || result.Action != "none" {
		t.Fatalf("superseded was retried: %+v, %v", result, err)
	}
}
