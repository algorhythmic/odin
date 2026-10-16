package strictjson

import (
	"encoding/json"
	"errors"
	"reflect"
	"testing"
)

func TestDecodeDuplicateKeys(t *testing.T) {
	cases := []struct {
		doc  string
		want []string
	}{
		{`{"kind":"a","kind":"b"}`, []string{"/kind"}},
		{`{"a":{"x":1,"x":2},"b":[{"y":1,"y":1,"y":1}]}`, []string{"/a/x", "/b/0/y"}},
		{`{"a/b":1,"a/b":2,"c~d":1,"c~d":2}`, []string{"/a~1b", "/c~0d"}},
	}
	for _, c := range cases {
		_, err := Decode([]byte(c.doc))
		var dup *DuplicateKeyError
		if !errors.As(err, &dup) {
			t.Fatalf("Decode(%s) err = %v, want DuplicateKeyError", c.doc, err)
		}
		if !reflect.DeepEqual(dup.Pointers, c.want) {
			t.Errorf("Decode(%s) pointers = %v, want %v", c.doc, dup.Pointers, c.want)
		}
	}
}

func TestDecodeValues(t *testing.T) {
	v, err := Decode([]byte(` {"a":[1,"x",null,true,{"b":2.5}]} `))
	if err != nil {
		t.Fatal(err)
	}
	want := map[string]any{"a": []any{json.Number("1"), "x", nil, true, map[string]any{"b": json.Number("2.5")}}}
	if !reflect.DeepEqual(v, want) {
		t.Fatalf("Decode = %#v, want %#v", v, want)
	}
	// The same key in sibling objects is not a duplicate.
	if _, err := Decode([]byte(`[{"a":1},{"a":1}]`)); err != nil {
		t.Fatalf("sibling objects: %v", err)
	}
}

func TestDecodeRejectsTrailingData(t *testing.T) {
	for _, doc := range []string{`{} {}`, `1 2`, `{"a":1}x`} {
		if _, err := Decode([]byte(doc)); err == nil {
			t.Errorf("Decode(%q) err = nil, want an error", doc)
		}
	}
}

func TestUnmarshal(t *testing.T) {
	type rec struct {
		A int     `json:"a"`
		B *string `json:"b"`
	}
	var r rec
	if err := Unmarshal([]byte(`{"a":1,"b":null}`), &r); err != nil || r.A != 1 || r.B != nil {
		t.Fatalf("Unmarshal = %+v, %v", r, err)
	}
	if err := Unmarshal([]byte(`{"a":1,"c":2}`), &r); err == nil {
		t.Fatal("unknown key accepted")
	}
	if err := Unmarshal([]byte(`{"a":1,"a":2}`), &r); err == nil {
		t.Fatal("duplicate key accepted")
	}
	if err := Unmarshal([]byte(`{"a":"1"}`), &r); err == nil {
		t.Fatal("wrong type accepted")
	}
	if err := Unmarshal([]byte(`{"a":1} {}`), &r); err == nil {
		t.Fatal("trailing data accepted")
	}
	if err := Unmarshal([]byte(`{"A":1,"b":"x"}`), &r); err == nil {
		t.Fatal("case-folded key accepted")
	}
	type nested struct {
		Items []rec `json:"items"`
	}
	var n nested
	if err := Unmarshal([]byte(`{"items":[{"a":1,"b":"x"},{"a":2,"B":"y"}]}`), &n); err == nil {
		t.Fatal("case-folded nested key accepted")
	}
	if err := Unmarshal([]byte(`{"items":[{"a":1,"b":"x"}]}`), &n); err != nil {
		t.Fatalf("nested: %v", err)
	}
}
