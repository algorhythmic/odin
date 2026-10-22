package main

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"os"
	"path/filepath"

	"odin/validation"
)

type fixtureCase struct {
	Name   string `json:"name"`
	Schema string `json:"schema"`
	File   string `json:"file"`
	Valid  bool   `json:"valid"`
}
type fixtureManifest struct {
	SchemaVersion int           `json:"schema_version"`
	Cases         []fixtureCase `json:"cases"`
}
type verdict struct {
	Name          string `json:"name"`
	ActualValid   bool   `json:"actual_valid"`
	ExpectedValid bool   `json:"expected_valid"`
	Pass          bool   `json:"pass"`
}
type semanticCase struct {
	Name      string          `json:"name"`
	Operation string          `json:"operation"`
	Input     json.RawMessage `json:"input"`
	Expected  any             `json:"expected"`
}
type semanticManifest struct {
	SchemaVersion int            `json:"schema_version"`
	Cases         []semanticCase `json:"cases"`
}
type semanticVerdict struct {
	Name     string `json:"name"`
	Actual   any    `json:"actual"`
	Expected any    `json:"expected"`
	Pass     bool   `json:"pass"`
}

func emit(value any) error {
	data, err := json.Marshal(value)
	if err != nil {
		return err
	}
	var ordered any
	if err := json.Unmarshal(data, &ordered); err != nil {
		return err
	}
	data, err = json.Marshal(ordered) // map keys sorted, matching Python's deterministic output
	if err == nil {
		_, err = fmt.Fprintln(os.Stdout, string(data))
	}
	return err
}

func fixtures(root string) error {
	manifestPath := filepath.Join(root, "fixtures/v1/cases.json")
	data, err := os.ReadFile(manifestPath)
	if err != nil {
		return err
	}
	v := validation.New(filepath.Join(root, "schemas/v1"))
	if err := v.Validate("cases.schema.json", data); err != nil {
		return fmt.Errorf("fixture manifest: %w", err)
	}
	var manifest fixtureManifest
	if err := json.Unmarshal(data, &manifest); err != nil {
		return err
	}
	failed := false
	for _, c := range manifest.Cases {
		file, err := os.ReadFile(filepath.Join(root, "fixtures/v1", c.File))
		if err != nil {
			return err
		}
		actual := v.Validate(c.Schema, file) == nil
		pass := actual == c.Valid
		if err := emit(verdict{c.Name, actual, c.Valid, pass}); err != nil {
			return err
		}
		if !pass {
			failed = true
		}
	}
	if failed {
		return errors.New("fixture verdict mismatch")
	}
	return nil
}

func semantics(root string) error {
	data, err := os.ReadFile(filepath.Join(root, "fixtures/v1/semantics.json"))
	if err != nil {
		return err
	}
	if err := validation.New(filepath.Join(root, "schemas/v1")).Validate("semantics.schema.json", data); err != nil {
		return fmt.Errorf("semantics manifest: %w", err)
	}
	var manifest semanticManifest
	if err := json.Unmarshal(data, &manifest); err != nil {
		return err
	}
	if manifest.SchemaVersion != 1 || len(manifest.Cases) == 0 {
		return errors.New("invalid semantics manifest")
	}
	failed := false
	for _, c := range manifest.Cases {
		actual, err := evaluate(c.Operation, c.Input)
		if err != nil {
			return fmt.Errorf("%s: %w", c.Name, err)
		}
		got, _ := json.Marshal(actual)
		want, _ := json.Marshal(c.Expected)
		pass := string(got) == string(want)
		if err := emit(semanticVerdict{c.Name, actual, c.Expected, pass}); err != nil {
			return err
		}
		if !pass {
			failed = true
		}
	}
	if failed {
		return errors.New("semantic verdict mismatch")
	}
	return nil
}

func evaluate(operation string, raw json.RawMessage) (any, error) {
	switch operation {
	case "intake":
		var input struct {
			LastSequence     *float64 `json:"last_sequence"`
			IncomingSequence *float64 `json:"incoming_sequence"`
			DedupeSeen       bool     `json:"dedupe_seen"`
		}
		if err := json.Unmarshal(raw, &input); err != nil {
			return nil, err
		}
		var last, incoming *int64
		if input.LastSequence != nil {
			value := int64(*input.LastSequence)
			last = &value
		}
		if input.IncomingSequence != nil {
			value := int64(*input.IncomingSequence)
			incoming = &value
		}
		return validation.ClassifyIntake(last, incoming, input.DedupeSeen)
	case "revision":
		var input struct {
			Expected float64 `json:"expected"`
			Actual   float64 `json:"actual"`
		}
		if err := json.Unmarshal(raw, &input); err != nil {
			return nil, err
		}
		return validation.CheckRevision(int64(input.Expected), int64(input.Actual))
	case "owner":
		var input struct {
			ExpectedGeneration float64 `json:"expected_generation"`
			ActualGeneration   float64 `json:"actual_generation"`
		}
		if err := json.Unmarshal(raw, &input); err != nil {
			return nil, err
		}
		return validation.CheckOwnership(int64(input.ExpectedGeneration), int64(input.ActualGeneration))
	case "reconcile":
		var input struct {
			Status string `json:"status"`
		}
		if err := json.Unmarshal(raw, &input); err != nil {
			return nil, err
		}
		result, err := validation.ReconcileOperation(input.Status)
		if err != nil {
			return nil, err
		}
		return map[string]string{"state": result.State, "action": result.Action}, nil
	default:
		return nil, fmt.Errorf("unknown operation %q", operation)
	}
}

func run() error {
	schema := flag.String("schema", "", "schema filename under runtime/schemas/v1")
	fixturesFlag := flag.Bool("fixtures", false, "validate shared schema fixtures")
	semanticsFlag := flag.Bool("semantics", false, "validate shared pure-semantics fixtures")
	flag.Parse()
	root, err := validation.Root()
	if err != nil {
		return err
	}
	if *fixturesFlag {
		if *schema != "" || *semanticsFlag || flag.NArg() != 0 {
			return errors.New("--fixtures takes no other arguments")
		}
		return fixtures(root)
	}
	if *semanticsFlag {
		if *schema != "" || flag.NArg() != 0 {
			return errors.New("--semantics takes no other arguments")
		}
		return semantics(root)
	}
	if *schema == "" || flag.NArg() != 1 {
		return errors.New("usage: validate --schema event.schema.json PATH | --fixtures | --semantics")
	}
	data, err := os.ReadFile(flag.Arg(0))
	if err != nil {
		return err
	}
	return validation.New(filepath.Join(root, "schemas/v1")).Validate(*schema, data)
}

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
