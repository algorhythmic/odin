// Package strictjson decodes JSON the way the substrate contract requires:
// a duplicate key anywhere rejects the document, unknown keys reject a typed
// decode, and nothing may follow the top-level value (substrate/schemas
// README §4.1 step 1; §2 "Strict JSON").
package strictjson

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"sort"
	"strings"
)

// DuplicateKeyError reports every duplicated object key in a document as a
// sorted, de-duplicated list of RFC 6901 JSON pointers (README §4.1 step 1).
type DuplicateKeyError struct {
	Pointers []string
}

func (e *DuplicateKeyError) Error() string {
	return "strictjson: duplicate keys at " + strings.Join(e.Pointers, ", ")
}

// Decode parses data into generic values (objects as map[string]any, arrays
// as []any, numbers as json.Number). A duplicate key anywhere returns a
// *DuplicateKeyError naming all of them; trailing data is an error.
func Decode(data []byte) (any, error) {
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.UseNumber()
	w := walker{dec: dec, dups: map[string]bool{}}
	v, err := w.value("")
	if err != nil {
		return nil, err
	}
	if err := expectEOF(dec); err != nil {
		return nil, err
	}
	if len(w.dups) > 0 {
		ptrs := make([]string, 0, len(w.dups))
		for p := range w.dups {
			ptrs = append(ptrs, p)
		}
		sort.Strings(ptrs)
		return nil, &DuplicateKeyError{Pointers: ptrs}
	}
	return v, nil
}

// Unmarshal decodes data into v after rejecting duplicate keys, with unknown
// struct fields disallowed and trailing data rejected. It is the decoder for
// every typed substrate value (envelopes, records, fixture inputs).
//
// encoding/json matches keys to fields case-insensitively; Unmarshal then
// re-encodes v and requires every input key to reappear with its exact
// spelling, so `"Kind"` does not pass for `"kind"`. Optional fields must
// therefore be pointers (or maps) with omitempty, never omitempty values.
func Unmarshal(data []byte, v any) error {
	in, err := Decode(data)
	if err != nil {
		return err
	}
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.DisallowUnknownFields()
	if err := dec.Decode(v); err != nil {
		return err
	}
	if err := expectEOF(dec); err != nil {
		return err
	}
	re, err := json.Marshal(v)
	if err != nil {
		return err
	}
	out, err := Decode(re)
	if err != nil {
		return err
	}
	return sameKeys(in, out, "")
}

// sameKeys reports the first key of in that out lacks, comparing exact
// spellings through nested objects and arrays.
func sameKeys(in, out any, ptr string) error {
	switch a := in.(type) {
	case map[string]any:
		b, ok := out.(map[string]any)
		if !ok {
			return fmt.Errorf("strictjson: %q did not decode as an object", ptr)
		}
		for k, av := range a {
			child := Pointer(ptr, k)
			bv, ok := b[k]
			if !ok {
				return fmt.Errorf("strictjson: unknown key %q", child)
			}
			if err := sameKeys(av, bv, child); err != nil {
				return err
			}
		}
	case []any:
		b, ok := out.([]any)
		if !ok || len(b) != len(a) {
			return fmt.Errorf("strictjson: %q did not decode as the same array", ptr)
		}
		for i := range a {
			if err := sameKeys(a[i], b[i], fmt.Sprintf("%s/%d", ptr, i)); err != nil {
				return err
			}
		}
	}
	return nil
}

// Pointer appends one reference token to an RFC 6901 pointer, escaping `~`
// as `~0` and `/` as `~1`.
func Pointer(base, token string) string {
	token = strings.ReplaceAll(token, "~", "~0")
	token = strings.ReplaceAll(token, "/", "~1")
	return base + "/" + token
}

func expectEOF(dec *json.Decoder) error {
	if _, err := dec.Token(); err != io.EOF {
		if err == nil {
			return errors.New("strictjson: data after the top-level value")
		}
		return err
	}
	return nil
}

type walker struct {
	dec  *json.Decoder
	dups map[string]bool
}

func (w *walker) value(ptr string) (any, error) {
	tok, err := w.dec.Token()
	if err != nil {
		return nil, err
	}
	switch t := tok.(type) {
	case json.Delim:
		switch t {
		case '{':
			return w.object(ptr)
		case '[':
			return w.array(ptr)
		}
		return nil, fmt.Errorf("strictjson: unexpected %q at %q", t, ptr)
	default:
		return t, nil
	}
}

func (w *walker) object(ptr string) (any, error) {
	obj := map[string]any{}
	for w.dec.More() {
		tok, err := w.dec.Token()
		if err != nil {
			return nil, err
		}
		key, ok := tok.(string)
		if !ok {
			return nil, fmt.Errorf("strictjson: object key is not a string at %q", ptr)
		}
		child := Pointer(ptr, key)
		if _, seen := obj[key]; seen {
			w.dups[child] = true
		}
		v, err := w.value(child)
		if err != nil {
			return nil, err
		}
		obj[key] = v
	}
	if _, err := w.dec.Token(); err != nil { // '}'
		return nil, err
	}
	return obj, nil
}

func (w *walker) array(ptr string) (any, error) {
	arr := []any{}
	for i := 0; w.dec.More(); i++ {
		v, err := w.value(fmt.Sprintf("%s/%d", ptr, i))
		if err != nil {
			return nil, err
		}
		arr = append(arr, v)
	}
	if _, err := w.dec.Token(); err != nil { // ']'
		return nil, err
	}
	return arr, nil
}
