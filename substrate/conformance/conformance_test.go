package conformance

import (
	"encoding/json"
	"io/fs"
	"strings"
	"testing"
	"testing/fstest"

	"github.com/algorhythmic/odin/substrate/schemas"
)

// TestFixtures runs every case of fixtures/cases.json and requires each
// result to equal its `expected` value, reporting every differing case in
// one failure.
func TestFixtures(t *testing.T) {
	r, err := NewRunner()
	if err != nil {
		t.Fatal(err)
	}
	cases, err := r.Cases()
	if err != nil {
		t.Fatal(err)
	}
	if len(cases) == 0 {
		t.Fatal("no cases")
	}
	results, err := r.RunAll(cases)
	if err != nil {
		t.Fatal(err)
	}
	if len(results) != len(cases) {
		t.Fatalf("%d results for %d cases", len(results), len(cases))
	}
	mismatches, err := Compare(cases, results)
	if err != nil {
		t.Fatal(err)
	}
	if len(mismatches) > 0 {
		var b strings.Builder
		for _, m := range mismatches {
			b.WriteString("\n  " + m.ID + "\n    expected " + m.Expected + "\n    got      " + m.Got)
		}
		t.Fatalf("%d of %d cases differ from expected:%s", len(mismatches), len(cases), b.String())
	}
	t.Logf("%d cases match expected", len(cases))
}

// TestEveryOperationCovered checks that each operation of cases.schema.json
// has a runner and is exercised by at least one case.
func TestEveryOperationCovered(t *testing.T) {
	r, err := NewRunner()
	if err != nil {
		t.Fatal(err)
	}
	cases, err := r.Cases()
	if err != nil {
		t.Fatal(err)
	}
	used := map[string]bool{}
	for _, c := range cases {
		used[c.Operation] = true
	}
	for op := range operations {
		if !used[op] {
			t.Errorf("operation %s has no case", op)
		}
	}
	for op := range used {
		if _, ok := operations[op]; !ok && op != "validate" {
			t.Errorf("operation %s has no runner", op)
		}
	}
}

// overlay copies the embedded contract into a MapFS and replaces files.
func overlay(t *testing.T, replace map[string]string) fs.FS {
	t.Helper()
	m := fstest.MapFS{}
	err := fs.WalkDir(schemas.FS, ".", func(p string, d fs.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return err
		}
		data, err := fs.ReadFile(schemas.FS, p)
		if err != nil {
			return err
		}
		m[p] = &fstest.MapFile{Data: data}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	for p, data := range replace {
		m[p] = &fstest.MapFile{Data: []byte(data)}
	}
	return m
}

// TestFixtureDefectFailsLoudly: an input that does not match
// inputs.schema.json is an error, never a case outcome.
func TestFixtureDefectFailsLoudly(t *testing.T) {
	inputs := map[string]string{
		"fixtures/revision/check-revision-ok.json":    `{"record_rev": 0, "expected_revision": 1}`,
		"fixtures/revision/check-revision-stale.json": `{"record_rev": 1, "record_rev": 2}`,
		"fixtures/revision/check-revision-null.json":  `{"record_rev": 1, "extra": true}`,
	}
	r, err := NewRunnerFS(overlay(t, inputs))
	if err != nil {
		t.Fatal(err)
	}
	for input := range inputs {
		c := Case{ID: "revision/x", Group: "revision", Operation: "check_revision", Input: input}
		if res, err := r.RunCase(c); err == nil || !strings.Contains(err.Error(), "fixture defect") {
			t.Errorf("%s: result %v, err %v; want a fixture defect error", input, res, err)
		}
	}
}

func TestCasesIndexDefect(t *testing.T) {
	r, err := NewRunnerFS(overlay(t, map[string]string{CasesPath: `[{"id": "schema/x"}]`}))
	if err != nil {
		t.Fatal(err)
	}
	if _, err := r.Cases(); err == nil || !strings.Contains(err.Error(), "fixture defect") {
		t.Fatalf("Cases() err = %v, want a fixture defect error", err)
	}
}

func TestEncodeFormat(t *testing.T) {
	results := map[string]Result{
		"b/case": {"steps": []Result{{"outcome": "accepted", "cursor_after": nil, "duplicates_counted": 0}}},
		"a/case": {"outcome": "schema_invalid", "errors": []string{"/a<b"}},
	}
	got, err := Encode(results)
	if err != nil {
		t.Fatal(err)
	}
	want := `{
  "a/case": {
    "errors": [
      "/a<b"
    ],
    "outcome": "schema_invalid"
  },
  "b/case": {
    "steps": [
      {
        "cursor_after": null,
        "duplicates_counted": 0,
        "outcome": "accepted"
      }
    ]
  }
}
`
	if string(got) != want {
		t.Fatalf("Encode =\n%s\nwant\n%s", got, want)
	}
	var v map[string]any
	if err := json.Unmarshal(got, &v); err != nil {
		t.Fatal(err)
	}
}

func TestCompareReportsEveryMismatch(t *testing.T) {
	cases := []Case{
		{ID: "a/same", Expected: json.RawMessage(`{"outcome":"ok"}`)},
		{ID: "a/differs", Expected: json.RawMessage(`{"outcome":"ok"}`)},
		{ID: "a/extra-key", Expected: json.RawMessage(`{"outcome":"ok"}`)},
		{ID: "a/missing", Expected: json.RawMessage(`{"outcome":"ok"}`)},
	}
	results := map[string]Result{
		"a/same":      {"outcome": "ok"},
		"a/differs":   {"outcome": "stale_revision"},
		"a/extra-key": {"outcome": "ok", "reason": "x"},
	}
	ms, err := Compare(cases, results)
	if err != nil {
		t.Fatal(err)
	}
	var ids []string
	for _, m := range ms {
		ids = append(ids, m.ID)
	}
	if got := strings.Join(ids, ","); got != "a/differs,a/extra-key,a/missing" {
		t.Fatalf("mismatches = %s", got)
	}
}
