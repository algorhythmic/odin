// Package ids validates and mints the ULIDs Odin uses for every identifier
// it mints (I/O contract §2: "All identifiers are ULIDs minted by the owning
// service"; Appendix A field types).
//
// A ULID here is 26 characters of uppercase Crockford base32, exactly the
// `ulid` pattern of common.schema.json: a 48-bit millisecond timestamp
// followed by 80 bits of randomness from crypto/rand.
package ids

import (
	"crypto/rand"
	"errors"
	"io"
	"time"
)

// alphabet is Crockford's base32 alphabet: digits and uppercase letters
// without I, L, O and U.
const alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

// Length is the length of a ULID string.
const Length = 26

// maxTime is the largest millisecond timestamp a ULID can carry (48 bits).
const maxTime = 1<<48 - 1

// ErrTimeRange is returned when a timestamp does not fit in 48 bits of
// milliseconds since the Unix epoch.
var ErrTimeRange = errors.New("ids: timestamp outside the ULID range")

// Valid reports whether s matches common.schema.json#/$defs/ulid
// (`^[0-9A-HJKMNP-TV-Z]{26}$`). It checks the contract's pattern only; it
// does not reject a first character above 7, which the pattern allows.
func Valid(s string) bool {
	if len(s) != Length {
		return false
	}
	for i := 0; i < len(s); i++ {
		if !isCrockford(s[i]) {
			return false
		}
	}
	return true
}

func isCrockford(c byte) bool {
	switch {
	case c >= '0' && c <= '9':
		return true
	case c >= 'A' && c <= 'Z':
		return c != 'I' && c != 'L' && c != 'O' && c != 'U'
	}
	return false
}

// New mints a ULID for the current time with randomness from crypto/rand.
func New() (string, error) {
	return Mint(time.Now(), rand.Reader)
}

// Mint encodes t (truncated to milliseconds) and 80 bits read from entropy
// as a ULID. It fails if t is before the epoch or beyond 48 bits of
// milliseconds, or if entropy cannot supply ten bytes.
func Mint(t time.Time, entropy io.Reader) (string, error) {
	ms := t.UnixMilli()
	if ms < 0 || ms > maxTime {
		return "", ErrTimeRange
	}
	var b [16]byte
	for i := 5; i >= 0; i-- {
		b[i] = byte(ms)
		ms >>= 8
	}
	if _, err := io.ReadFull(entropy, b[6:]); err != nil {
		return "", err
	}
	return encode(b), nil
}

// encode writes the 128 bits of b as 26 base32 characters, most significant
// first; the first character carries the top 3 bits (130 bits in total, the
// first two always zero).
func encode(b [16]byte) string {
	var out [Length]byte
	// Treat b as a big-endian 128-bit integer and emit 5 bits at a time
	// from the least significant end.
	hi := uint64(b[0])<<56 | uint64(b[1])<<48 | uint64(b[2])<<40 | uint64(b[3])<<32 |
		uint64(b[4])<<24 | uint64(b[5])<<16 | uint64(b[6])<<8 | uint64(b[7])
	lo := uint64(b[8])<<56 | uint64(b[9])<<48 | uint64(b[10])<<40 | uint64(b[11])<<32 |
		uint64(b[12])<<24 | uint64(b[13])<<16 | uint64(b[14])<<8 | uint64(b[15])
	for i := Length - 1; i >= 0; i-- {
		out[i] = alphabet[lo&0x1f]
		lo = lo>>5 | hi<<59
		hi >>= 5
	}
	return string(out[:])
}
