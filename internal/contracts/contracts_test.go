package contracts

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestSharedFixtures(t *testing.T) {
	suite, err := Load("../../schemas")
	if err != nil {
		t.Fatal(err)
	}
	count, err := suite.Fixtures("../../fixtures/contracts.json")
	if err != nil {
		t.Fatal(err)
	}
	if count < 53 {
		t.Fatal("missing fixture coverage")
	}
	paths, err := filepath.Glob("../../fixtures/*-contracts.json")
	if err != nil {
		t.Fatal(err)
	}
	for _, path := range paths {
		t.Run(filepath.Base(path), func(t *testing.T) {
			if _, err := suite.Fixtures(path); err != nil {
				t.Fatal(err)
			}
		})
	}
	raw, err := os.ReadFile("../../fixtures/examples.json")
	if err != nil {
		t.Fatal(err)
	}
	var value any
	if err := json.Unmarshal(raw, &value); err != nil {
		t.Fatal(err)
	}
	if err := suite.Validate("examples", value); err != nil {
		t.Fatal(err)
	}
}
