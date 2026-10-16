package effects

import (
	"reflect"
	"testing"

	"github.com/algorhythmic/odin/substrate/records"
)

func str(s string) *string { return &s }
func num(n int64) *int64   { return &n }

func effect(id, destination, capability, state string) records.Effect {
	return records.Effect{
		Meta:                  records.Meta{ID: id, Rev: 1},
		OperationID:           "01JAXP00000000000000000001",
		Destination:           destination,
		DestinationCapability: capability,
		OwnerGeneration:       num(2),
		State:                 state,
	}
}

func TestRestart(t *testing.T) {
	in := []records.Effect{
		effect("01JAEF00000000000000000003", "saga:run.submit", IdempotentByKey, records.EffectInFlight),
		effect("01JAEF00000000000000000002", "saga:run.submit", IdempotentByKey, records.EffectQueued),
		effect("01JAEF00000000000000000001", "telegram:notify", IrreduciblyUnknown, records.EffectInFlight),
	}
	res := Restart(in)
	if want := []string{"01JAEF00000000000000000001", "01JAEF00000000000000000003"}; !reflect.DeepEqual(res.MarkedUnknown, want) {
		t.Fatalf("marked = %v", res.MarkedUnknown)
	}
	if res.Effects[0].State != records.EffectUnknown || res.Effects[1].State != records.EffectQueued || in[0].State != records.EffectInFlight {
		t.Fatal("restart changed the wrong effects or its input")
	}
	if got := Restart(nil).MarkedUnknown; got == nil || len(got) != 0 {
		t.Fatalf("empty restart marked %#v", got)
	}
}

func TestReconcile(t *testing.T) {
	saga := effect("01JAEF00000000000000000001", "saga:run.submit", IdempotentByKey, records.EffectUnknown)
	notify := effect("01JAEF00000000000000000002", "telegram:notify", IrreduciblyUnknown, records.EffectUnknown)
	request := effect("01JAEF00000000000000000003", "telegram:request", IrreduciblyUnknown, records.EffectUnknown)
	approval := effect("01JAEF00000000000000000004", "telegram:approval", IrreduciblyUnknown, records.EffectUnknown)
	other := effect("01JAEF00000000000000000005", "telegram:edit", IrreduciblyUnknown, records.EffectUnknown)
	prompt := effect("01JAEF00000000000000000006", "surface:prompt", SurfaceDeclared, records.EffectUnknown)
	host := func(state string) records.Effect {
		return effect("01JAEF00000000000000000007", "session_host:start", SessionHost, state)
	}
	strange := effect("01JAEF00000000000000000008", "saga:run.submit", "exactly_once", records.EffectUnknown)

	ok := func(state string, retry bool) ReconcileResult {
		return ReconcileResult{Outcome: Reconciled, StateAfter: state, RetryAllowed: retry}
	}
	with := func(r ReconcileResult, f func(*ReconcileResult)) ReconcileResult { f(&r); return r }
	invalid := ReconcileResult{Outcome: InvalidReconciliationInput}

	cases := []struct {
		name   string
		e      records.Effect
		lookup *string
		host   *string
		want   ReconcileResult
	}{
		{"saga completed", saga, str("completed"), nil, ok(records.EffectDelivered, false)},
		{"saga pending", saga, str("pending"), nil, ok(records.EffectUnknown, false)},
		{"saga failed", saga, str("failed"), nil, ok(records.EffectFailed, false)},
		{"saga superseded", saga, str("superseded"), nil, ok(records.EffectSuperseded, false)},
		{"saga absent", saga, str("absent"), nil, ok(records.EffectQueued, true)},
		{"saga expired", saga, str("unknown_expired"), nil,
			with(ok(records.EffectUnknown, false), func(r *ReconcileResult) { r.SurfaceToOperator = true })},
		{"saga bad lookup", saga, str("maybe"), nil, invalid},
		{"saga no lookup", saga, nil, nil, invalid},
		{"saga with host state", saga, str("completed"), str(HostOffline), invalid},
		{"saga not unknown", effect(saga.ID, saga.Destination, IdempotentByKey, records.EffectQueued), str("completed"), nil, invalid},
		{"telegram notify", notify, nil, nil,
			with(ok(records.EffectUnknown, false), func(r *ReconcileResult) { r.Note = NoteMayHaveBeenSent })},
		{"telegram request", request, nil, nil,
			with(ok(records.EffectQueued, true), func(r *ReconcileResult) { r.SameRequestID = true })},
		{"telegram approval", approval, nil, nil,
			with(ok(records.EffectQueued, true), func(r *ReconcileResult) { r.SameRequestID = true })},
		{"telegram other operation", other, nil, nil, invalid},
		{"telegram with lookup", notify, str("completed"), nil, invalid},
		{"surface prompt", prompt, nil, nil,
			with(ok(records.EffectUnknown, false), func(r *ReconcileResult) { r.CountsAgainstCaps = true })},
		{"surface with lookup", prompt, str("absent"), nil, invalid},
		{"host offline queued", host(records.EffectQueued), nil, str(HostOffline),
			with(ok(records.EffectQueued, false), func(r *ReconcileResult) { r.HeldForHost = true })},
		{"host offline in flight", host(records.EffectInFlight), nil, str(HostOffline),
			with(ok(records.EffectInFlight, false), func(r *ReconcileResult) { r.HeldForHost = true })},
		{"host offline unknown", host(records.EffectUnknown), nil, str(HostOffline),
			with(ok(records.EffectUnknown, false), func(r *ReconcileResult) { r.HeldForHost = true })},
		{"host offline with lookup", host(records.EffectUnknown), str("absent"), str(HostOffline), invalid},
		{"host returned completed", host(records.EffectUnknown), str("completed"), str(HostReturned), ok(records.EffectDelivered, false)},
		{"host returned absent", host(records.EffectInFlight), str("absent"), str(HostReturned), ok(records.EffectQueued, true)},
		{"host returned pending", host(records.EffectUnknown), str("pending"), str(HostReturned), invalid},
		{"host returned without report", host(records.EffectUnknown), nil, str(HostReturned), invalid},
		{"host without state", host(records.EffectUnknown), nil, nil, invalid},
		{"host delivered effect", host(records.EffectDelivered), nil, str(HostOffline), invalid},
		{"unknown capability", strange, str("completed"), nil, invalid},
	}
	for _, c := range cases {
		got := Reconcile(c.e, c.lookup, c.host)
		if got.Outcome == Reconciled && got.Effect.State != got.StateAfter {
			t.Errorf("%s: effect state %s, state_after %s", c.name, got.Effect.State, got.StateAfter)
		}
		got.Effect = records.Effect{}
		if !reflect.DeepEqual(got, c.want) {
			t.Errorf("%s: got %+v, want %+v", c.name, got, c.want)
		}
	}
}

func TestDispatch(t *testing.T) {
	q := effect("01JAEF00000000000000000001", "surface:prompt", SurfaceDeclared, records.EffectQueued)
	shadow := &records.AttentionPrompt{Mode: records.PromptShadow}
	live := &records.AttentionPrompt{Mode: records.PromptLive}
	if got := Dispatch(q, shadow, true).Outcome; got != DispatchDisabled {
		t.Errorf("recovery first: %s", got)
	}
	if got := Dispatch(q, shadow, false).Outcome; got != DispatchRefusedShadow {
		t.Errorf("shadow: %s", got)
	}
	held := q
	held.State = records.EffectHeld
	if got := Dispatch(held, live, false).Outcome; got != InvalidDispatchInput {
		t.Errorf("held: %s", got)
	}
	res := Dispatch(q, live, false)
	if res.Outcome != Dispatched || res.StateAfter != records.EffectInFlight || res.Effect.Attempts != 1 {
		t.Errorf("dispatch: %+v", res)
	}
}

func TestRevalidate(t *testing.T) {
	pass := Context{CurrentGeneration: 2, AssignmentState: str("active")}
	held := effect("01JAEF00000000000000000001", "saga:guidance", IdempotentByKey, records.EffectHeld)
	held.DispatchBlockedBy = str("ownership_transfer:01JACM00000000000000000001")
	cases := []struct {
		name   string
		e      records.Effect
		ctx    Context
		out    Outcome
		reason string
	}{
		{"pass", held, pass, Queued, ""},
		{"generation", held, Context{CurrentGeneration: 3}, CancelledStale, ReasonOwnerGeneration},
		{"revoked", held, Context{CurrentGeneration: 2, DelegationRevoked: true}, CancelledStale, ReasonDelegationRevoked},
		{"assignment", held, Context{CurrentGeneration: 2, AssignmentState: str("failed")}, CancelledStale, ReasonAssignmentState},
		{"approval", held, Context{CurrentGeneration: 2, ApprovalExpired: true}, CancelledStale, ReasonApprovalExpired},
		{"order", held, Context{CurrentGeneration: 3, DelegationRevoked: true, ApprovalExpired: true}, CancelledStale, ReasonOwnerGeneration},
		{"in flight", effect(held.ID, held.Destination, IdempotentByKey, records.EffectInFlight), pass, InvalidRevalidationInput, ""},
	}
	for _, c := range cases {
		res := Revalidate(c.e, c.ctx)
		if res.Outcome != c.out || res.Reason != c.reason {
			t.Errorf("%s: got %s/%s, want %s/%s", c.name, res.Outcome, res.Reason, c.out, c.reason)
		}
	}
	res := Revalidate(held, pass)
	if res.Effect.State != records.EffectQueued || res.Effect.DispatchBlockedBy != nil {
		t.Errorf("held effect after pass: %+v", res.Effect)
	}
	noGen := held
	noGen.OwnerGeneration = nil
	if res := Revalidate(noGen, Context{CurrentGeneration: 9}); res.Outcome != Queued {
		t.Errorf("null owner_generation: %s", res.Outcome)
	}
}
