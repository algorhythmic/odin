package ids

import (
	"bytes"
	"strings"
	"testing"
	"time"
)

func TestValid(t *testing.T) {
	good := []string{
		"01JAEV00000000000000000305",
		"0123456789ABCDEFGHJKMNPQRS",
		"7ZZZZZZZZZZZZZZZZZZZZZZZZZ",
	}
	for _, s := range good {
		if !Valid(s) {
			t.Errorf("Valid(%q) = false, want true", s)
		}
	}
	bad := []string{
		"",
		"01JAEV0000000000000000030",   // 25 characters
		"01JAEV000000000000000003050", // 27 characters
		"01jaev00000000000000000305",  // lowercase
		"01JAEV0000000000000000030I",  // I is not Crockford
		"01JAEV0000000000000000030L",
		"01JAEV0000000000000000030O",
		"01JAEV0000000000000000030U",
		"01JAEV0000000000000000030\n",
	}
	for _, s := range bad {
		if Valid(s) {
			t.Errorf("Valid(%q) = true, want false", s)
		}
	}
}

func TestMintKnownValue(t *testing.T) {
	// Timestamp 1 ms, entropy all 0xFF: the time part is 0000000001 and the
	// random part is sixteen Zs (80 one bits).
	got, err := Mint(time.UnixMilli(1), bytes.NewReader(bytes.Repeat([]byte{0xFF}, 10)))
	if err != nil {
		t.Fatal(err)
	}
	want := "0000000001" + strings.Repeat("Z", 16)
	if got != want {
		t.Fatalf("Mint = %s, want %s", got, want)
	}
	// The maximum timestamp encodes as 7ZZZZZZZZZ.
	got, err = Mint(time.UnixMilli(maxTime), bytes.NewReader(make([]byte, 10)))
	if err != nil {
		t.Fatal(err)
	}
	if want := "7ZZZZZZZZZ" + strings.Repeat("0", 16); got != want {
		t.Fatalf("Mint(max) = %s, want %s", got, want)
	}
}

func TestMintRangeAndEntropy(t *testing.T) {
	if _, err := Mint(time.UnixMilli(-1), bytes.NewReader(make([]byte, 10))); err != ErrTimeRange {
		t.Fatalf("negative time: err = %v, want ErrTimeRange", err)
	}
	if _, err := Mint(time.UnixMilli(maxTime+1), bytes.NewReader(make([]byte, 10))); err != ErrTimeRange {
		t.Fatalf("time beyond 48 bits: err = %v, want ErrTimeRange", err)
	}
	if _, err := Mint(time.UnixMilli(1), bytes.NewReader(make([]byte, 9))); err == nil {
		t.Fatal("short entropy: err = nil, want an error")
	}
}

func TestNew(t *testing.T) {
	seen := map[string]bool{}
	for i := 0; i < 100; i++ {
		id, err := New()
		if err != nil {
			t.Fatal(err)
		}
		if !Valid(id) {
			t.Fatalf("New() = %q, not valid", id)
		}
		if seen[id] {
			t.Fatalf("New() repeated %q", id)
		}
		seen[id] = true
	}
	// The time prefix sorts with the clock.
	a, _ := Mint(time.UnixMilli(1_700_000_000_000), bytes.NewReader(make([]byte, 10)))
	b, _ := Mint(time.UnixMilli(1_700_000_000_001), bytes.NewReader(make([]byte, 10)))
	if !(a < b) {
		t.Fatalf("ULIDs do not sort by time: %s >= %s", a, b)
	}
}
