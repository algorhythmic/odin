package contracts

import (
	"os"
	"path/filepath"
	"testing"
)

func TestTransitions(t *testing.T) {
	root := filepath.Join("..", "..")
	suite, err := Load(filepath.Join(root, "schemas"))
	if err != nil {
		t.Fatal(err)
	}
	raw, err := os.ReadFile(filepath.Join(root, "fixtures", "transitions.json"))
	if err != nil {
		t.Fatal(err)
	}
	value, err := Decode(raw)
	if err != nil {
		t.Fatal(err)
	}
	if err := suite.Validate("transitions", value); err != nil {
		t.Fatal(err)
	}
	for _, entry := range value.(map[string]any)["cases"].([]any) {
		c := entry.(map[string]any)
		t.Run(c["name"].(string), func(t *testing.T) {
			actual, err := Transition(c["kind"].(string), c["input"].(map[string]any))
			if err != nil || actual != c["expected"] {
				t.Fatalf("got %q (%v), expected %q", actual, err, c["expected"])
			}
		})
	}
}

func TestStrictJSON(t *testing.T) {
	for _, raw := range []string{`{"x":1,"x":2}`, `{"x":{"a":1,"a":2}}`, `{} {}`, `1e999`, `NaN`} {
		if _, err := Decode([]byte(raw)); err == nil {
			t.Errorf("accepted %s", raw)
		}
	}
}
