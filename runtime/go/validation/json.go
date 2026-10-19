package validation

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math"
	"math/big"
	"strconv"
	"unicode/utf8"
)

// DecodeJSON reads exactly one JSON value and refuses duplicate object keys.
// This is stricter than encoding/json's usual last-key-wins behavior.
func DecodeJSON(data []byte) (any, error) {
	if !utf8.Valid(data) {
		return nil, errors.New("invalid UTF-8 in JSON")
	}
	if err := checkSurrogateEscapes(data); err != nil {
		return nil, err
	}
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.UseNumber()
	value, err := decodeValue(dec)
	if err != nil {
		return nil, err
	}
	if _, err := dec.Token(); !errors.Is(err, io.EOF) {
		if err == nil {
			return nil, errors.New("trailing JSON value")
		}
		return nil, fmt.Errorf("trailing data: %w", err)
	}
	return value, nil
}

func decodeValue(dec *json.Decoder) (any, error) {
	tok, err := dec.Token()
	if err != nil {
		return nil, err
	}
	switch value := tok.(type) {
	case json.Delim:
		switch value {
		case '{':
			obj := make(map[string]any)
			for dec.More() {
				keyToken, err := dec.Token()
				if err != nil {
					return nil, err
				}
				key, ok := keyToken.(string)
				if !ok {
					return nil, errors.New("object key is not a string")
				}
				if _, exists := obj[key]; exists {
					return nil, fmt.Errorf("duplicate JSON key %q", key)
				}
				item, err := decodeValue(dec)
				if err != nil {
					return nil, err
				}
				obj[key] = item
			}
			if _, err := dec.Token(); err != nil { // closing brace
				return nil, err
			}
			return obj, nil
		case '[':
			items := make([]any, 0)
			for dec.More() {
				item, err := decodeValue(dec)
				if err != nil {
					return nil, err
				}
				items = append(items, item)
			}
			if _, err := dec.Token(); err != nil { // closing bracket
				return nil, err
			}
			return items, nil
		default:
			return nil, errors.New("unexpected JSON delimiter")
		}
	case json.Number:
		parsed, err := strconv.ParseFloat(string(value), 64)
		if err != nil || math.IsNaN(parsed) || math.IsInf(parsed, 0) {
			return nil, fmt.Errorf("nonfinite or invalid JSON number %q", value)
		}
		if math.Abs(parsed) > 9007199254740991 {
			return nil, fmt.Errorf("JSON number exceeds safe interoperable range: %q", value)
		}
		original, ok := new(big.Rat).SetString(string(value))
		if !ok {
			return nil, fmt.Errorf("invalid JSON number %q", value)
		}
		roundTrip, ok := new(big.Rat).SetString(strconv.FormatFloat(parsed, 'g', -1, 64))
		if !ok || original.Cmp(roundTrip) != 0 {
			return nil, fmt.Errorf("JSON number loses decimal precision: %q", value)
		}
		return parsed, nil
	}
	return tok, nil
}

func checkSurrogateEscapes(data []byte) error {
	for i := 0; i < len(data); i++ {
		if data[i] != '"' {
			continue
		}
		for i++; i < len(data); i++ {
			if data[i] == '"' {
				break
			}
			if data[i] != '\\' {
				continue
			}
			if i+1 >= len(data) {
				return errors.New("incomplete JSON escape")
			}
			if data[i+1] != 'u' {
				i++
				continue
			}
			if i+6 > len(data) {
				return errors.New("incomplete Unicode escape")
			}
			code, err := strconv.ParseUint(string(data[i+2:i+6]), 16, 16)
			if err != nil {
				return errors.New("invalid Unicode escape")
			}
			if code >= 0xDC00 && code <= 0xDFFF {
				return errors.New("unpaired low surrogate")
			}
			if code >= 0xD800 && code <= 0xDBFF {
				if i+12 > len(data) || data[i+6] != '\\' || data[i+7] != 'u' {
					return errors.New("unpaired high surrogate")
				}
				low, err := strconv.ParseUint(string(data[i+8:i+12]), 16, 16)
				if err != nil || low < 0xDC00 || low > 0xDFFF {
					return errors.New("unpaired high surrogate")
				}
				i += 11
				continue
			}
			i += 5
		}
	}
	return nil
}
