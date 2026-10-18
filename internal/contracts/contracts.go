// Package contracts validates Odin-local records, not producer wire formats.
package contracts

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"

	"github.com/santhosh-tekuri/jsonschema/v6"
)

// Decode rejects duplicate keys and trailing documents instead of silently
// selecting a conflicting value at a language boundary.
func Decode(raw []byte) (any, error) {
	d := json.NewDecoder(bytes.NewReader(raw))
	var read func() (any, error)
	read = func() (any, error) {
		token, err := d.Token()
		if err != nil {
			return nil, err
		}
		delimiter, ok := token.(json.Delim)
		if !ok {
			return token, nil
		}
		switch delimiter {
		case '{':
			value := map[string]any{}
			for d.More() {
				k, err := d.Token()
				if err != nil {
					return nil, err
				}
				key, ok := k.(string)
				if !ok {
					return nil, fmt.Errorf("invalid object key")
				}
				if _, seen := value[key]; seen {
					return nil, fmt.Errorf("duplicate key %q", key)
				}
				v, err := read()
				if err != nil {
					return nil, err
				}
				value[key] = v
			}
			_, err := d.Token()
			return value, err
		case '[':
			value := []any{}
			for d.More() {
				v, err := read()
				if err != nil {
					return nil, err
				}
				value = append(value, v)
			}
			_, err := d.Token()
			return value, err
		default:
			return nil, fmt.Errorf("unexpected delimiter")
		}
	}
	value, err := read()
	if err != nil {
		return nil, err
	}
	if _, err := d.Token(); err != io.EOF {
		return nil, fmt.Errorf("trailing JSON content")
	}
	return value, nil
}

type Suite struct{ schemas map[string]*jsonschema.Schema }

func Load(directory string) (*Suite, error) {
	compiler := jsonschema.NewCompiler()
	compiler.AssertFormat()
	paths, err := filepath.Glob(filepath.Join(directory, "*.schema.json"))
	if err != nil {
		return nil, err
	}
	for _, path := range paths {
		raw, err := os.ReadFile(path)
		if err != nil {
			return nil, err
		}
		value, err := Decode(raw)
		if err != nil {
			return nil, err
		}
		absolute, err := filepath.Abs(path)
		if err != nil {
			return nil, err
		}
		if err := compiler.AddResource(absolute, value); err != nil {
			return nil, err
		}
	}
	result := &Suite{schemas: map[string]*jsonschema.Schema{}}
	for _, path := range paths {
		absolute, err := filepath.Abs(path)
		if err != nil {
			return nil, err
		}
		schema, err := compiler.Compile(absolute)
		if err != nil {
			return nil, err
		}
		name := filepath.Base(path)
		result.schemas[name[:len(name)-len(".schema.json")]] = schema
	}
	return result, nil
}

func (s *Suite) Validate(name string, value any) error {
	schema, exists := s.schemas[name]
	if !exists {
		return fmt.Errorf("unknown schema %q", name)
	}
	return schema.Validate(value)
}

type Case struct {
	Name   string `json:"name"`
	Schema string `json:"schema"`
	Valid  bool   `json:"valid"`
	Value  any    `json:"value"`
}

func (s *Suite) Fixtures(path string) (int, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return 0, err
	}
	value, err := Decode(raw)
	if err != nil {
		return 0, err
	}
	if err := s.Validate("fixtures", value); err != nil {
		return 0, err
	}
	var fixture struct {
		Cases []Case `json:"cases"`
	}
	if err := json.Unmarshal(raw, &fixture); err != nil {
		return 0, err
	}
	names := map[string]bool{}
	for _, c := range fixture.Cases {
		if names[c.Name] {
			return 0, fmt.Errorf("duplicate case %s", c.Name)
		}
		names[c.Name] = true
		valid := s.Validate(c.Schema, c.Value) == nil
		if valid != c.Valid {
			return 0, fmt.Errorf("fixture disagrees: %s (expected %t)", c.Name, c.Valid)
		}
	}
	return len(fixture.Cases), nil
}
