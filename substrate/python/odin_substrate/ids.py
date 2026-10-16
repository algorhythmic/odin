"""ULID identifiers for Odin-minted records (schemas README §2; common $defs ``ulid``).

A ULID is 26 characters of Crockford base32, uppercase: a 48-bit
millisecond timestamp followed by 80 random bits. Validation is exactly the
schema's pattern ``^[0-9A-HJKMNP-TV-Z]{26}$`` with ``$`` meaning end of
string (no trailing newline).
"""

from __future__ import annotations

import re
import secrets
import time

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
"""Crockford base32 alphabet (no I, L, O, U)."""

LENGTH = 26
_PATTERN = re.compile(r"[0-9A-HJKMNP-TV-Z]{26}")
_TIME_MAX = (1 << 48) - 1
_DECODE = {c: i for i, c in enumerate(ALPHABET)}


def is_valid(value: object) -> bool:
    """Return whether ``value`` matches the common ``ulid`` pattern exactly.

    Like the schema, this accepts any 26-character Crockford string; it
    does not reject values whose leading character exceeds ``7`` (which
    would overflow 128 bits), because the schema does not.
    """
    return isinstance(value, str) and _PATTERN.fullmatch(value) is not None


def encode(value: int) -> str:
    """Encode a 128-bit integer as a 26-character ULID string."""
    if not 0 <= value < (1 << 128):
        raise ValueError("ULID value out of range")
    chars = []
    for _ in range(LENGTH):
        chars.append(ALPHABET[value & 31])
        value >>= 5
    return "".join(reversed(chars))


def mint(timestamp_ms: int | None = None, randomness: bytes | None = None) -> str:
    """Mint a ULID from a millisecond timestamp (default: now) and 80 random bits.

    ``randomness`` (10 bytes) may be supplied for deterministic tests; by
    default it comes from :mod:`secrets`.
    """
    if timestamp_ms is None:
        timestamp_ms = time.time_ns() // 1_000_000
    if not 0 <= timestamp_ms <= _TIME_MAX:
        raise ValueError("ULID timestamp out of range")
    if randomness is None:
        randomness = secrets.token_bytes(10)
    if len(randomness) != 10:
        raise ValueError("ULID randomness must be 10 bytes")
    return encode((timestamp_ms << 80) | int.from_bytes(randomness, "big"))


def timestamp_ms(ulid: str) -> int:
    """Return the millisecond timestamp encoded in a valid ULID."""
    if not is_valid(ulid):
        raise ValueError(f"not a ULID: {ulid!r}")
    value = 0
    for c in ulid:
        value = (value << 5) | _DECODE[c]
    return value >> 80
