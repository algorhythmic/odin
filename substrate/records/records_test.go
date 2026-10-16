package records

import (
	"reflect"
	"testing"
)

func num(n int64) *int64 { return &n }

func TestCheckRevision(t *testing.T) {
	if CheckRevision(3, nil) != ExpectedRevisionRequired || CheckRevision(3, num(3)) != OK ||
		CheckRevision(3, num(2)) != StaleRevision || CheckRevision(3, num(4)) != StaleRevision {
		t.Fatal("CheckRevision")
	}
}

func TestCheckOwner(t *testing.T) {
	c := Commitment{OwnershipGeneration: 2}
	cases := map[string]struct {
		s    PlanningSession
		want Outcome
	}{
		"current":  {PlanningSession{State: "active", OwnershipGeneration: 2}, OK},
		"retiring": {PlanningSession{State: "retiring", OwnershipGeneration: 2}, OK},
		"retired":  {PlanningSession{State: "retired", OwnershipGeneration: 2}, StaleOwner},
		"older":    {PlanningSession{State: "active", OwnershipGeneration: 1}, StaleOwner},
		"newer":    {PlanningSession{State: "active", OwnershipGeneration: 3}, StaleOwner},
	}
	for name, c2 := range cases {
		if got := CheckOwner(c2.s, c); got != c2.want {
			t.Errorf("%s: %s", name, got)
		}
	}
}

func TestTransferCommitment(t *testing.T) {
	c := Commitment{Meta: Meta{ID: "01JACM00000000000000000001", Rev: 7}, OwnershipGeneration: 2}
	eff := func(id, state string, gen *int64) Effect {
		return Effect{Meta: Meta{ID: id}, State: state, OwnerGeneration: gen}
	}
	effects := []Effect{
		eff("01JAEF00000000000000000003", EffectQueued, num(2)),
		eff("01JAEF00000000000000000001", EffectHeld, num(1)),
		eff("01JAEF00000000000000000002", EffectInFlight, num(2)),
		eff("01JAEF00000000000000000004", EffectQueued, nil),
		eff("01JAEF00000000000000000005", EffectQueued, num(3)),
	}
	if r := TransferCommitment(c, "01JAPS00000000000000000002", num(6), effects); r.Outcome != StaleRevision {
		t.Fatalf("stale: %s", r.Outcome)
	}
	if r := TransferCommitment(c, "01JAPS00000000000000000002", nil, effects); r.Outcome != ExpectedRevisionRequired {
		t.Fatalf("missing: %s", r.Outcome)
	}
	r := TransferCommitment(c, "01JAPS00000000000000000002", num(7), effects)
	if r.Outcome != Transferred || r.GenerationAfter != 3 || r.RevAfter != 8 ||
		*r.Commitment.Owner != "01JAPS00000000000000000002" {
		t.Fatalf("transfer: %+v", r)
	}
	if want := []string{"01JAEF00000000000000000001", "01JAEF00000000000000000003"}; !reflect.DeepEqual(r.HeldEffects, want) {
		t.Fatalf("held = %v", r.HeldEffects)
	}
	if b := r.Effects[0].DispatchBlockedBy; r.Effects[0].State != EffectHeld || b == nil || *b != "ownership_transfer:01JACM00000000000000000001" {
		t.Fatalf("held effect: %+v", r.Effects[0])
	}
	if r.Effects[2].State != EffectInFlight || r.Effects[3].DispatchBlockedBy != nil || effects[0].State != EffectQueued {
		t.Fatal("transfer touched effects it must leave alone, or its input")
	}
}

func TestOperationReuse(t *testing.T) {
	a := Effect{OperationID: "01JAXP00000000000000000001", PayloadDigest: "aa"}
	b := a
	if o, err := OperationReuse(a, b); err != nil || o != OperationIdempotent {
		t.Fatal(o, err)
	}
	b.PayloadDigest = "bb"
	if o, err := OperationReuse(a, b); err != nil || o != OperationConflict {
		t.Fatal(o, err)
	}
	b.OperationID = "01JAXP00000000000000000002"
	if _, err := OperationReuse(a, b); err == nil {
		t.Fatal("different operation ids accepted")
	}
}

func TestCheckMessageSize(t *testing.T) {
	cases := []struct {
		text string
		size int64
		want Outcome
	}{
		{"", 0, OK},
		{"héllo", 6, OK},
		{"héllo", 5, SizeMismatch},
		{"日本", 6, OK},
		{"\xff", 1, SizeMismatch},
	}
	for _, c := range cases {
		if got := CheckMessageSize(Message{Text: c.text, Size: c.size}); got != c.want {
			t.Errorf("%q/%d: %s", c.text, c.size, got)
		}
	}
}

func TestCombine(t *testing.T) {
	pos := func(name, result string) Position {
		if result == "" {
			return Position{Position: name}
		}
		return Position{Position: name, Verdict: &Verdict{Result: result}}
	}
	cases := []struct {
		round   int64
		a, b    string
		out     Outcome
		verdict string
	}{
		{1, ResultApprove, ResultApprove, Approved, ResultApprove},
		{1, ResultApproveUnchanged, ResultApproveUnchanged, Approved, ResultApproveUnchanged},
		{2, ResultApproveUnchanged, ResultApprove, Approved, ResultApprove},
		{1, ResultApprove, ResultReject, Escalated, ""},
		{1, ResultInsufficientEvidence, ResultFlag, Escalated, ""},
		{1, ResultApprove, ResultFlag, ReReview, ""},
		{2, ResultApprove, ResultFlag, Escalated, ""},
		{1, ResultFlag, ResultFlag, Escalated, ""},
		{2, ResultFlag, ResultFlag, Escalated, ""},
		{1, "", ResultReject, Escalated, ""},
		{1, ResultInsufficientEvidence, "", Escalated, ""},
		{1, "", ResultApprove, Pending, ""},
		{1, ResultFlag, "", Pending, ""},
		{2, "", "", Pending, ""},
	}
	for _, c := range cases {
		got, err := Combine(c.round, []Position{pos("a", c.a), pos("b", c.b)})
		if err != nil || got.Outcome != c.out || got.VerdictResult != c.verdict {
			t.Errorf("round %d %q+%q: %+v, %v", c.round, c.a, c.b, got, err)
		}
	}
}

// TestCombineRefusesOtherThanAB checks that Combine never approves with
// fewer or other positions than one a and one b (ODIN-ADR-013).
func TestCombineRefusesOtherThanAB(t *testing.T) {
	approve := func(name string) Position {
		return Position{Position: name, Verdict: &Verdict{Result: ResultApprove}}
	}
	bad := map[string]struct {
		round     int64
		positions []Position
	}{
		"none":        {1, nil},
		"one":         {1, []Position{approve("a")}},
		"three":       {1, []Position{approve("a"), approve("b"), approve("b")}},
		"two a":       {1, []Position{approve("a"), approve("a")}},
		"unnamed":     {1, []Position{approve(""), approve("b")}},
		"round three": {3, []Position{approve("a"), approve("b")}},
		"bad result":  {1, []Position{approve("a"), {Position: "b", Verdict: &Verdict{Result: "MAYBE"}}}},
	}
	for name, c := range bad {
		if got, err := Combine(c.round, c.positions); err == nil || got.Outcome != "" {
			t.Errorf("%s: got %+v, %v; want an error and no outcome", name, got, err)
		}
	}
	if got, err := Combine(1, []Position{approve("b"), approve("a")}); err != nil || got.Outcome != Approved {
		t.Errorf("b then a: %+v, %v", got, err)
	}
}

func TestMappingCoverage(t *testing.T) {
	fields, err := CommitmentFields()
	if err != nil {
		t.Fatal(err)
	}
	if len(fields) != 18 || fields[0] != "checkpoints" {
		t.Fatalf("commitment fields = %v", fields)
	}
	s := func(v string) *string { return &v }
	m := Mapping{Rows: []MappingRow{
		{CommitmentField: s("provenance.native_rev")},
		{CommitmentField: s("objective")},
		{CommitmentField: nil},
	}}
	got := CheckMappingCoverage(m, []string{"objective", "provenance", "state", "decisions"})
	if got.Outcome != MappingIncomplete || !reflect.DeepEqual(got.Uncovered, []string{"decisions", "state"}) {
		t.Fatalf("coverage = %+v", got)
	}
	got = CheckMappingCoverage(m, []string{"objective", "provenance"})
	if got.Outcome != MappingComplete || got.Uncovered == nil || len(got.Uncovered) != 0 {
		t.Fatalf("complete coverage = %+v", got)
	}
}
