// Package effects models the outbox rules of I0: restart marks in-flight
// effects unknown, reconciliation by destination capability before any
// retry, the dispatch gate, and revalidation of queued and held effects
// (I/O contract §9 outbox table and recovery steps; D6; AC-02, AC-27;
// substrate/schemas README §4.7).
//
// Effects are at-least-once with stable operation ids and an explicit
// unknown state; nothing here claims exactly-once, and nothing here sends
// anything: no peer API is implemented.
package effects

import (
	"sort"
	"strings"

	"github.com/algorhythmic/odin/substrate/records"
)

// Outcome is an exact outcome string of the semantics contract
// (substrate/schemas README §4.9).
type Outcome string

// Outcomes of restart, reconcile, dispatch and revalidate. Queued, Held and
// CancelledStale are revalidation outcomes; CancelledStale is also a
// dispatch outcome.
const (
	Restarted                  Outcome = "restarted"
	Reconciled                 Outcome = "reconciled"
	InvalidReconciliationInput Outcome = "invalid_reconciliation_input"
	Dispatched                 Outcome = "dispatched"
	DispatchDisabled           Outcome = "dispatch_disabled"
	DispatchRefusedShadow      Outcome = "dispatch_refused_shadow"
	InvalidDispatchInput       Outcome = "invalid_dispatch_input"
	Queued                     Outcome = "queued"
	Held                       Outcome = "held"
	CancelledStale             Outcome = "cancelled_stale"
	InvalidRevalidationInput   Outcome = "invalid_revalidation_input"
)

// Destination capabilities (I/O contract §9 outbox table).
const (
	IdempotentByKey    = "idempotent_by_key"   // Saga: lookup by operation id
	IrreduciblyUnknown = "irreducibly_unknown" // Telegram: no lookup exists
	SurfaceDeclared    = "surface_declared"    // attention prompts, other surfaces
	SessionHost        = "session_host"        // workstation session host
)

// GuidanceDestination is the only destination for which Saga's operation
// lookup may answer superseded (§9 outbox table: "superseded (guidance
// only)"; B-13).
const GuidanceDestination = "saga:guidance"

// Host states a reconciliation of a session-host effect needs
// (ODIN-ADR-009).
const (
	HostOffline  = "host_offline"
	HostReturned = "host_returned"
)

// RestartResult is the result of Restart.
type RestartResult struct {
	Outcome       Outcome
	MarkedUnknown []string // sorted by code point; never nil
	Effects       []records.Effect
}

// Restart applies the restart rule of §9: every in_flight effect becomes
// unknown, because the service cannot know whether it left (substrate
// README §4.7).
func Restart(effects []records.Effect) RestartResult {
	after := make([]records.Effect, len(effects))
	marked := []string{}
	for i, e := range effects {
		if e.State == records.EffectInFlight {
			e.State = records.EffectUnknown
			marked = append(marked, e.ID)
		}
		after[i] = e
	}
	sort.Strings(marked)
	return RestartResult{Outcome: Restarted, MarkedUnknown: marked, Effects: after}
}

// ReconcileResult is the result of Reconcile. The flags are set exactly
// where the §4.7 table names them; Note is "may have been sent" for a
// Telegram notification.
type ReconcileResult struct {
	Outcome           Outcome
	StateAfter        string
	RetryAllowed      bool
	SurfaceToOperator bool
	Note              string
	SameRequestID     bool
	CountsAgainstCaps bool
	HeldForHost       bool
	Effect            records.Effect // the effect after reconciliation
}

// NoteMayHaveBeenSent is the note on an unknown Telegram notification.
const NoteMayHaveBeenSent = "may have been sent"

func invalidReconciliation() ReconcileResult {
	return ReconcileResult{Outcome: InvalidReconciliationInput}
}

// Reconcile decides what happens to an effect whose delivery is uncertain,
// before any retry (I/O contract §9 outbox table; AC-02; substrate README
// §4.7). lookup is the destination's answer (nil when none exists) and
// hostState the session host's state (nil when not applicable). The rule
// is chosen by the effect's destination_capability; any input outside the
// rule's row is invalid_reconciliation_input.
func Reconcile(e records.Effect, lookup, hostState *string) ReconcileResult {
	var r ReconcileResult
	switch e.DestinationCapability {
	case IdempotentByKey:
		if e.State != records.EffectUnknown || hostState != nil || lookup == nil {
			return invalidReconciliation()
		}
		// Saga reports superseded for guidance only (§9 outbox table; B-13).
		if *lookup == "superseded" && e.Destination != GuidanceDestination {
			return invalidReconciliation()
		}
		switch *lookup {
		case "completed":
			r = ReconcileResult{StateAfter: records.EffectDelivered}
		case "pending":
			r = ReconcileResult{StateAfter: records.EffectUnknown}
		case "failed":
			r = ReconcileResult{StateAfter: records.EffectFailed}
		case "superseded":
			r = ReconcileResult{StateAfter: records.EffectSuperseded}
		case "absent":
			r = ReconcileResult{StateAfter: records.EffectQueued, RetryAllowed: true}
		case "unknown_expired":
			r = ReconcileResult{StateAfter: records.EffectUnknown, SurfaceToOperator: true}
		default:
			return invalidReconciliation()
		}
	case IrreduciblyUnknown:
		if e.State != records.EffectUnknown || lookup != nil || hostState != nil {
			return invalidReconciliation()
		}
		_, op, _ := strings.Cut(e.Destination, ":")
		switch op {
		case "notify":
			r = ReconcileResult{StateAfter: records.EffectUnknown, Note: NoteMayHaveBeenSent}
		case "request", "approval":
			r = ReconcileResult{StateAfter: records.EffectQueued, RetryAllowed: true, SameRequestID: true}
		default:
			return invalidReconciliation()
		}
	case SurfaceDeclared:
		if e.State != records.EffectUnknown || lookup != nil || hostState != nil {
			return invalidReconciliation()
		}
		r = ReconcileResult{StateAfter: records.EffectUnknown, CountsAgainstCaps: true}
	case SessionHost:
		switch e.State {
		case records.EffectQueued, records.EffectInFlight, records.EffectUnknown:
		default:
			return invalidReconciliation()
		}
		if hostState == nil {
			return invalidReconciliation()
		}
		switch *hostState {
		case HostOffline:
			if lookup != nil {
				return invalidReconciliation()
			}
			// §9: commands addressed to an offline host "stay queued, or
			// unknown if one was in flight".
			after := e.State
			if after == records.EffectInFlight {
				after = records.EffectUnknown
			}
			r = ReconcileResult{StateAfter: after, HeldForHost: true}
		case HostReturned:
			if lookup == nil {
				return invalidReconciliation()
			}
			switch *lookup {
			case "completed":
				r = ReconcileResult{StateAfter: records.EffectDelivered}
			case "absent":
				r = ReconcileResult{StateAfter: records.EffectQueued, RetryAllowed: true}
			default:
				return invalidReconciliation()
			}
		default:
			return invalidReconciliation()
		}
	default:
		return invalidReconciliation()
	}
	r.Outcome = Reconciled
	e.State = r.StateAfter
	r.Effect = e
	return r
}

// DispatchResult is the result of Dispatch. StateAfter is set only when
// Outcome is Dispatched, Reason only when it is CancelledStale.
type DispatchResult struct {
	Outcome    Outcome
	StateAfter string
	Reason     string
	Effect     records.Effect
}

// Dispatch is the gate every effect passes before it leaves the service
// (I/O contract §9 outbox and recovery step 8; ODIN-ADR-010; substrate
// README §4.7), checked in this order: during recovery nothing is
// dispatched (dispatch_disabled); a shadow-mode attention prompt is never
// sent (dispatch_refused_shadow); only a queued effect may be dispatched
// (invalid_dispatch_input); then the dispatcher revalidates the authority
// the effect was created under against ctx ("owner generation still
// current, delegation not revoked, assignment not cancelled, approval not
// expired", §9), and the first failing check gives cancelled_stale with its
// reason. Otherwise the effect becomes in_flight with one more attempt.
// Nothing is sent: I0 implements no destination.
func Dispatch(e records.Effect, prompt *records.AttentionPrompt, recoveryInProgress bool, ctx Context) DispatchResult {
	switch {
	case recoveryInProgress:
		return DispatchResult{Outcome: DispatchDisabled, Effect: e}
	case prompt != nil && prompt.Mode == records.PromptShadow:
		return DispatchResult{Outcome: DispatchRefusedShadow, Effect: e}
	case e.State != records.EffectQueued:
		return DispatchResult{Outcome: InvalidDispatchInput, Effect: e}
	}
	if reason := staleReason(e, ctx); reason != "" {
		e.State = records.EffectCancelledStale
		return DispatchResult{Outcome: CancelledStale, Reason: reason, Effect: e}
	}
	e.State = records.EffectInFlight
	e.Attempts++
	return DispatchResult{Outcome: Dispatched, StateAfter: records.EffectInFlight, Effect: e}
}

// Context is what revalidation checks an effect against: the authority
// current at dispatch time (I/O contract §9 step 4).
type Context struct {
	CurrentGeneration int64   `json:"current_generation"`
	DelegationRevoked bool    `json:"delegation_revoked"`
	AssignmentState   *string `json:"assignment_state"`
	ApprovalExpired   bool    `json:"approval_expired"`
	// DispatchBlockerActive reports whether what put a held effect in held
	// (its dispatch_blocked_by: take-control, ownership transfer or
	// revocation) still applies; a held effect is not released while it
	// does (§9). It is not consulted for a queued effect.
	DispatchBlockerActive bool `json:"dispatch_blocker_active"`
	// HostState is recorded for context and not consulted in I0.
	HostState *string `json:"host_state"`
}

// Revalidation failure reasons, in check order.
const (
	ReasonOwnerGeneration   = "owner_generation"
	ReasonDelegationRevoked = "delegation_revoked"
	ReasonAssignmentState   = "assignment_state"
	ReasonApprovalExpired   = "approval_expired"
)

// RevalidateResult is the result of Revalidate. Reason is set only when
// Outcome is CancelledStale.
type RevalidateResult struct {
	Outcome Outcome
	Reason  string
	Effect  records.Effect
}

// Revalidate checks a queued or held effect against the current authority
// (I/O contract §9 step 4; AC-27; substrate README §4.7). Any other effect
// state is invalid_revalidation_input. A held effect whose blocker still
// applies (ctx.DispatchBlockerActive) stays held, unchanged: it "leaves
// only through revalidation", and not while take-control, the transfer or
// the revocation that held it is in force (§9). Otherwise the first failing
// check decides cancelled_stale with its reason: owner_generation (a
// non-null owner_generation below the current one), delegation_revoked,
// assignment_state (cancelled, completed or failed), approval_expired. If
// all pass the effect is queued, so a held effect leaves held only to
// queued or cancelled_stale.
func Revalidate(e records.Effect, ctx Context) RevalidateResult {
	if e.State != records.EffectQueued && e.State != records.EffectHeld {
		return RevalidateResult{Outcome: InvalidRevalidationInput, Effect: e}
	}
	if e.State == records.EffectHeld && ctx.DispatchBlockerActive {
		return RevalidateResult{Outcome: Held, Effect: e}
	}
	if reason := staleReason(e, ctx); reason != "" {
		e.State = records.EffectCancelledStale
		return RevalidateResult{Outcome: CancelledStale, Reason: reason, Effect: e}
	}
	e.State = records.EffectQueued
	e.DispatchBlockedBy = nil
	return RevalidateResult{Outcome: Queued, Effect: e}
}

// staleReason runs the four authority checks of §4.7 in order and returns
// the first failing one's reason, or "" when all pass.
func staleReason(e records.Effect, ctx Context) string {
	switch {
	case e.OwnerGeneration != nil && *e.OwnerGeneration < ctx.CurrentGeneration:
		return ReasonOwnerGeneration
	case ctx.DelegationRevoked:
		return ReasonDelegationRevoked
	case ctx.AssignmentState != nil && terminalAssignment(*ctx.AssignmentState):
		return ReasonAssignmentState
	case ctx.ApprovalExpired:
		return ReasonApprovalExpired
	}
	return ""
}

func terminalAssignment(state string) bool {
	switch state {
	case "cancelled", "completed", "failed":
		return true
	}
	return false
}
