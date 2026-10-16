package records

import (
	"fmt"
	"sort"
	"unicode/utf8"
)

// Outcome is an exact outcome string of the semantics contract
// (substrate/schemas README §4.9).
type Outcome string

// Outcomes of the revision, ownership, operation, size and review checks.
const (
	OK                       Outcome = "ok"
	StaleRevision            Outcome = "stale_revision"
	ExpectedRevisionRequired Outcome = "expected_revision_required"
	StaleOwner               Outcome = "stale_owner"
	Transferred              Outcome = "transferred"
	OperationConflict        Outcome = "operation_conflict"
	OperationIdempotent      Outcome = "operation_idempotent"
	SizeMismatch             Outcome = "size_mismatch"
)

// CheckRevision is the optimistic-concurrency check of §2 (substrate README
// §4.5): a write that depends on prior state must name the revision it
// read. Missing (nil) gives expected_revision_required; equal gives ok; any
// other value, lower or higher, gives stale_revision (the 409).
func CheckRevision(recordRev int64, expected *int64) Outcome {
	switch {
	case expected == nil:
		return ExpectedRevisionRequired
	case *expected == recordRev:
		return OK
	default:
		return StaleRevision
	}
}

// CheckOwner reports whether session may act on commitment (§2 ownership;
// substrate README §4.5): stale_owner when the session is retired or its
// ownership_generation differs from the commitment's; otherwise ok. A
// retiring session at the current generation is ok.
func CheckOwner(session PlanningSession, commitment Commitment) Outcome {
	if session.State == "retired" || session.OwnershipGeneration != commitment.OwnershipGeneration {
		return StaleOwner
	}
	return OK
}

// TransferResult is the result of TransferCommitment.
type TransferResult struct {
	Outcome Outcome
	// Set only when Outcome is Transferred.
	Commitment      Commitment
	GenerationAfter int64
	RevAfter        int64
	HeldEffects     []string // sorted by code point
	Effects         []Effect // the input effects after the transfer
}

// TransferCommitment is the commitment.transfer operation (§2, §9;
// substrate README §4.5). It checks expected against the commitment's rev
// first and returns that outcome alone on failure. Otherwise it sets the new
// owner, increments ownership_generation and rev, and holds every queued or
// held effect whose non-null owner_generation is below the new generation,
// with dispatch_blocked_by "ownership_transfer:<commitment id>"; those are
// revalidated before dispatch (effects.Revalidate).
func TransferCommitment(c Commitment, newOwner string, expected *int64, effects []Effect) TransferResult {
	if out := CheckRevision(c.Rev, expected); out != OK {
		return TransferResult{Outcome: out}
	}
	owner := newOwner
	c.Owner = &owner
	c.OwnershipGeneration++
	c.Rev++
	blocker := "ownership_transfer:" + c.ID
	after := make([]Effect, len(effects))
	held := []string{}
	for i, e := range effects {
		if (e.State == EffectQueued || e.State == EffectHeld) &&
			e.OwnerGeneration != nil && *e.OwnerGeneration < c.OwnershipGeneration {
			e.State = EffectHeld
			b := blocker
			e.DispatchBlockedBy = &b
			held = append(held, e.ID)
		}
		after[i] = e
	}
	sort.Strings(held)
	return TransferResult{
		Outcome:         Transferred,
		Commitment:      c,
		GenerationAfter: c.OwnershipGeneration,
		RevAfter:        c.Rev,
		HeldEffects:     held,
		Effects:         after,
	}
}

// OperationReuse compares an incoming effect with an existing one under the
// same operation id (§9 "durable operation id"; substrate README §4.5): a
// different payload digest is operation_conflict (the 409), the same digest
// is operation_idempotent. Different operation ids are a caller error.
func OperationReuse(existing, incoming Effect) (Outcome, error) {
	if existing.OperationID != incoming.OperationID {
		return "", fmt.Errorf("records: operation ids differ (%s, %s)", existing.OperationID, incoming.OperationID)
	}
	if existing.PayloadDigest != incoming.PayloadDigest {
		return OperationConflict, nil
	}
	return OperationIdempotent, nil
}

// CheckMessageSize checks the §3 rule that `size` is the byte length of
// `text` in UTF-8: ok or size_mismatch. Go strings decoded from JSON are
// UTF-8 (invalid sequences become U+FFFD), so the byte length is len(text).
func CheckMessageSize(m Message) Outcome {
	if !utf8.ValidString(m.Text) || int64(len(m.Text)) != m.Size {
		return SizeMismatch
	}
	return OK
}
