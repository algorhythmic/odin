package contracts

import (
	"encoding/json"
	"os"
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
