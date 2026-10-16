// Package eventlog models the I0 event substrate: the version 1 event
// envelope, the namespace and kind catalogues, and an in-memory append-only
// log with the namespace writer check, intake with dedupe, inbox processing
// and replay (I/O contract §1, §2, §9; ODIN-ADR-006; substrate/schemas
// README §4.2 to §4.4).
//
// It is a model of the semantics only. The physical store layout is open
// (X-11) and decided before I1; nothing here is a store.
package eventlog

import (
	"bytes"
	"encoding/json"
	"fmt"

	"github.com/algorhythmic/odin/substrate/ids"
	"github.com/algorhythmic/odin/substrate/strictjson"
)

// EnvelopeVersion is the only envelope version I0 defines.
const EnvelopeVersion = 1

// Inbox processing states (I/O contract Appendix A, "Event processing
// states (inbox) received → processed").
const (
	StateReceived  = "received"
	StateProcessed = "processed"
)

// Envelope is the event envelope, version 1: the Event record as stored in
// the inbox (I/O contract §2 Event and Appendix A; envelope.schema.json).
// Nullable fields are pointers; the payload is opaque and kept as raw JSON.
type Envelope struct {
	ID          string          `json:"id"`
	Envelope    int             `json:"envelope"`
	Namespace   string          `json:"namespace"`
	Producer    string          `json:"producer"`
	Kind        string          `json:"kind"`
	Scope       Scope           `json:"scope"`
	SourceSeq   *int64          `json:"source_seq"`
	ReceivedAt  string          `json:"received_at"`
	Causation   *string         `json:"causation"`
	Correlation *string         `json:"correlation"`
	Payload     json.RawMessage `json:"payload"`
	PayloadRef  *string         `json:"payload_ref"`
	DedupeKey   string          `json:"dedupe_key"`
	Wake        string          `json:"wake"`
	State       string          `json:"state"`
}

// Scope is the envelope's project or run scope; every key is optional.
type Scope struct {
	Project    *string `json:"project,omitempty"`
	Run        *string `json:"run,omitempty"`
	Assignment *string `json:"assignment,omitempty"`
	Session    *string `json:"session,omitempty"`
	Host       *string `json:"host,omitempty"`
	Commitment *string `json:"commitment,omitempty"`
}

// DecodeEnvelope decodes one envelope strictly: unknown keys, duplicate
// keys, wrong types and trailing data are rejected (substrate README §2,
// "Strict JSON"). Patterns and required keys are the schema's job;
// validate with schemacheck first when the input is untrusted.
func DecodeEnvelope(data []byte) (Envelope, error) {
	var e Envelope
	if err := strictjson.Unmarshal(data, &e); err != nil {
		return Envelope{}, err
	}
	return e, nil
}

// HasPayload reports whether the inline payload is present and not null.
func (e Envelope) HasPayload() bool {
	p := bytes.TrimSpace(e.Payload)
	return len(p) > 0 && !bytes.Equal(p, []byte("null"))
}

// Check verifies the envelope invariants code relies on: version 1, a ULID
// id, a catalogued namespace and kind, a non-empty dedupe key, a known
// inbox state and at least one of payload and payload_ref
// (envelope.schema.json). It is not a replacement for schema validation.
func (e Envelope) Check(c *Catalogue) error {
	switch {
	case e.Envelope != EnvelopeVersion:
		return fmt.Errorf("eventlog: envelope version %d, want %d", e.Envelope, EnvelopeVersion)
	case !ids.Valid(e.ID):
		return fmt.Errorf("eventlog: id %q is not a ULID", e.ID)
	case e.DedupeKey == "":
		return fmt.Errorf("eventlog: event %s has an empty dedupe key", e.ID)
	case e.State != StateReceived && e.State != StateProcessed:
		return fmt.Errorf("eventlog: event %s has state %q", e.ID, e.State)
	case !e.HasPayload() && e.PayloadRef == nil:
		return fmt.Errorf("eventlog: event %s has neither payload nor payload_ref", e.ID)
	}
	if _, ok := c.Namespace(e.Namespace); !ok {
		return fmt.Errorf("eventlog: event %s has unknown namespace %q", e.ID, e.Namespace)
	}
	if !c.KnownKind(e.Kind) {
		return fmt.Errorf("eventlog: event %s has unknown kind %q", e.ID, e.Kind)
	}
	return nil
}
