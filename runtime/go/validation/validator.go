package validation

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/google/jsonschema-go/jsonschema"
)

// Root finds the runtime directory from the current tree, regardless of the
// caller's working directory. The source-location fallback supports go run.
func Root() (string, error) {
	cwd, err := os.Getwd()
	if err == nil {
		for dir := cwd; ; dir = filepath.Dir(dir) {
			candidate := filepath.Join(dir, "runtime")
			if isRuntimeRoot(candidate) {
				return candidate, nil
			}
			if isRuntimeRoot(dir) {
				return dir, nil
			}
			if filepath.Dir(dir) == dir {
				break
			}
		}
	}
	_, source, _, ok := runtime.Caller(0)
	if ok {
		candidate := filepath.Clean(filepath.Join(filepath.Dir(source), "../.."))
		if isRuntimeRoot(candidate) {
			return candidate, nil
		}
	}
	return "", errors.New("cannot find runtime/schemas/v1 and runtime/fixtures/v1")
}

func isRuntimeRoot(path string) bool {
	for _, part := range []string{"schemas/v1", "fixtures/v1"} {
		info, err := os.Stat(filepath.Join(path, part))
		if err != nil || !info.IsDir() {
			return false
		}
	}
	return true
}

type Validator struct {
	schemaDir string
	cache     map[string]*compiledSchema
}

type compiledSchema struct {
	resolved *jsonschema.Resolved
	raw      map[string]any
}

func New(schemaDir string) *Validator {
	return &Validator{schemaDir: schemaDir, cache: make(map[string]*compiledSchema)}
}

func safeSchemaName(name string) bool {
	return name != "" && name == filepath.Base(name) && strings.HasSuffix(name, ".schema.json") && name != ".schema.json"
}

func (v *Validator) loadRaw(name string) (map[string]any, error) {
	if !safeSchemaName(name) {
		return nil, fmt.Errorf("invalid local schema name %q", name)
	}
	data, err := os.ReadFile(filepath.Join(v.schemaDir, name))
	if err != nil {
		return nil, err
	}
	decoded, err := DecodeJSON(data)
	if err != nil {
		return nil, fmt.Errorf("schema %s: %w", name, err)
	}
	obj, ok := decoded.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("schema %s must be a JSON object", name)
	}
	if obj["$schema"] != "https://json-schema.org/draft/2020-12/schema" {
		return nil, fmt.Errorf("schema %s must declare Draft 2020-12", name)
	}
	if obj["$id"] != "https://odin.invalid/schemas/v1/"+name {
		return nil, fmt.Errorf("schema %s has unexpected $id", name)
	}
	if err := checkLocalRefs(obj); err != nil {
		return nil, fmt.Errorf("schema %s: %w", name, err)
	}
	injectFormatShapes(obj)
	return obj, nil
}

// jsonschema-go treats format as an annotation. Add the deterministic lexical
// part as an assertion before core validation, so oneOf/anyOf branch selection
// also observes formats. checkFormats performs the calendar/ULID checks.
func injectFormatShapes(value any) {
	switch typed := value.(type) {
	case map[string]any:
		for _, child := range typed {
			injectFormatShapes(child)
		}
		if format, ok := typed["format"].(string); ok {
			var pattern string
			switch format {
			case "date-time":
				pattern = `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$`
			case "ulid":
				pattern = `^[0-7][0-9A-HJKMNP-TV-Z]{25}$`
			}
			if pattern != "" {
				all, _ := typed["allOf"].([]any)
				typed["allOf"] = append(all, map[string]any{"pattern": pattern})
			}
		}
	case []any:
		for _, child := range typed {
			injectFormatShapes(child)
		}
	}
}

func checkLocalRefs(value any) error {
	switch typed := value.(type) {
	case map[string]any:
		for key, child := range typed {
			if key == "$ref" || key == "$dynamicRef" {
				ref, ok := child.(string)
				if !ok {
					return fmt.Errorf("%s must be a string", key)
				}
				filename, _, ok := strings.Cut(ref, "#")
				if !ok && ref != "" {
					filename = ref
				}
				if filename != "" && !safeSchemaName(filename) {
					return fmt.Errorf("nonlocal schema reference %q", ref)
				}
			}
			if err := checkLocalRefs(child); err != nil {
				return err
			}
		}
	case []any:
		for _, child := range typed {
			if err := checkLocalRefs(child); err != nil {
				return err
			}
		}
	}
	return nil
}

func (v *Validator) compile(name string) (*compiledSchema, error) {
	if cached := v.cache[name]; cached != nil {
		return cached, nil
	}
	raw, err := v.loadRaw(name)
	if err != nil {
		return nil, err
	}
	encoded, err := json.Marshal(raw)
	if err != nil {
		return nil, err
	}
	var schema jsonschema.Schema
	if err := json.Unmarshal(encoded, &schema); err != nil {
		return nil, fmt.Errorf("schema %s: %w", name, err)
	}
	resolved, err := schema.Resolve(&jsonschema.ResolveOptions{BaseURI: "https://odin.invalid/schemas/v1/" + name, Loader: v.loader})
	if err != nil {
		return nil, fmt.Errorf("resolve schema %s: %w", name, err)
	}
	compiled := &compiledSchema{resolved: resolved, raw: raw}
	v.cache[name] = compiled
	return compiled, nil
}

func (v *Validator) loader(uri *url.URL) (*jsonschema.Schema, error) {
	if uri.Scheme != "https" || uri.Host != "odin.invalid" || filepath.Dir(uri.Path) != "/schemas/v1" {
		return nil, fmt.Errorf("nonlocal schema reference %s", uri)
	}
	loaded, err := v.loadRaw(filepath.Base(uri.Path))
	if err != nil {
		return nil, err
	}
	data, err := json.Marshal(loaded)
	if err != nil {
		return nil, err
	}
	var result jsonschema.Schema
	return &result, json.Unmarshal(data, &result)
}

func (v *Validator) branchValid(schema map[string]any, instance any, name string) bool {
	data, err := json.Marshal(schema)
	if err != nil {
		return false
	}
	var copy map[string]any
	if err := json.Unmarshal(data, &copy); err != nil {
		return false
	}
	injectFormatShapes(copy)
	data, err = json.Marshal(copy)
	if err != nil {
		return false
	}
	var branch jsonschema.Schema
	if err := json.Unmarshal(data, &branch); err != nil {
		return false
	}
	resolved, err := branch.Resolve(&jsonschema.ResolveOptions{BaseURI: "https://odin.invalid/schemas/v1/" + name, Loader: v.loader})
	return err == nil && resolved.Validate(instance) == nil
}

func (v *Validator) Validate(name string, data []byte) error {
	instance, err := DecodeJSON(data)
	if err != nil {
		return err
	}
	compiled, err := v.compile(name)
	if err != nil {
		return err
	}
	if err := compiled.resolved.Validate(instance); err != nil {
		return err
	}
	return v.checkFormats(compiled.raw, instance, name, 0)
}

func (v *Validator) checkFormats(schema map[string]any, instance any, name string, depth int) error {
	if depth > 32 {
		return errors.New("format reference depth exceeded")
	}
	if ref, ok := schema["$ref"].(string); ok {
		filename, fragment, _ := strings.Cut(ref, "#")
		if filename == "" {
			filename = name
		}
		var target map[string]any
		if filename == name {
			target, _ = v.loadRaw(name)
		} else {
			target, _ = v.loadRaw(filename)
		}
		if target == nil {
			return fmt.Errorf("invalid format reference %q", ref)
		}
		if fragment != "" {
			for _, part := range strings.Split(strings.TrimPrefix(fragment, "/"), "/") {
				part = strings.ReplaceAll(strings.ReplaceAll(part, "~1", "/"), "~0", "~")
				next, ok := target[part].(map[string]any)
				if !ok {
					return fmt.Errorf("invalid format reference %q", ref)
				}
				target = next
			}
		}
		if err := v.checkFormats(target, instance, filename, depth+1); err != nil {
			return err
		}
	}
	if text, ok := instance.(string); ok {
		if format, ok := schema["format"].(string); ok {
			if err := checkFormat(format, text); err != nil {
				return err
			}
		}
	}
	if branches, ok := schema["allOf"].([]any); ok {
		for _, branch := range branches {
			if sub, ok := branch.(map[string]any); ok {
				if err := v.checkFormats(sub, instance, name, depth+1); err != nil {
					return err
				}
			}
		}
	}
	for _, keyword := range []string{"anyOf", "oneOf"} {
		if branches, ok := schema[keyword].([]any); ok {
			matched := false
			for _, branch := range branches {
				sub, ok := branch.(map[string]any)
				if ok && v.branchValid(sub, instance, name) && v.checkFormats(sub, instance, name, depth+1) == nil {
					matched = true
					break
				}
			}
			if !matched {
				return fmt.Errorf("no %s branch satisfies asserted formats", keyword)
			}
		}
	}
	if conditional, ok := schema["if"].(map[string]any); ok {
		chosen := "else"
		if v.branchValid(conditional, instance, name) && v.checkFormats(conditional, instance, name, depth+1) == nil {
			chosen = "then"
		}
		if sub, ok := schema[chosen].(map[string]any); ok {
			if err := v.checkFormats(sub, instance, name, depth+1); err != nil {
				return err
			}
		}
	}
	if obj, ok := instance.(map[string]any); ok {
		if props, ok := schema["properties"].(map[string]any); ok {
			for key, child := range props {
				if value, present := obj[key]; present {
					if sub, ok := child.(map[string]any); ok {
						if err := v.checkFormats(sub, value, name, depth+1); err != nil {
							return fmt.Errorf("%s: %w", key, err)
						}
					}
				}
			}
		}
		if sub, ok := schema["additionalProperties"].(map[string]any); ok {
			props, _ := schema["properties"].(map[string]any)
			for key, value := range obj {
				if _, defined := props[key]; !defined {
					if err := v.checkFormats(sub, value, name, depth+1); err != nil {
						return fmt.Errorf("%s: %w", key, err)
					}
				}
			}
		}
	}
	if items, ok := instance.([]any); ok {
		if sub, ok := schema["items"].(map[string]any); ok {
			for i, item := range items {
				if err := v.checkFormats(sub, item, name, depth+1); err != nil {
					return fmt.Errorf("item %d: %w", i, err)
				}
			}
		}
	}
	return nil
}

func checkFormat(format, value string) error {
	switch format {
	case "ulid":
		if len(value) != 26 || value[0] > '7' || value == strings.Repeat("0", 26) {
			return fmt.Errorf("invalid ulid %q", value)
		}
		for _, r := range value {
			if !strings.ContainsRune("0123456789ABCDEFGHJKMNPQRSTVWXYZ", r) {
				return fmt.Errorf("invalid ulid %q", value)
			}
		}
	case "date-time":
		if !strings.HasSuffix(value, "Z") {
			return fmt.Errorf("invalid UTC date-time %q", value)
		}
		parsed, err := time.Parse(time.RFC3339Nano, value)
		if err != nil || parsed.Year() < 1 {
			return fmt.Errorf("invalid date-time %q", value)
		}
	default:
		return fmt.Errorf("unsupported asserted format %q", format)
	}
	return nil
}
