package eventlog

import (
	"fmt"
	"reflect"
	"strings"
	"testing"
)

func catalogue(t *testing.T) *Catalogue {
	t.Helper()
	c, err := LoadCatalogue()
	if err != nil {
		t.Fatal(err)
	}
	return c
}

const validEnvelope = `{
  "id": "01JAEV00000000000000000001",
  "envelope": 1,
  "namespace": "odin_history",
  "producer": "saga",
  "kind": "run.state.accepted",
  "scope": {"run": "run-alpha-0001"},
  "source_seq": 7,
  "received_at": "2026-10-16T09:00:00Z",
  "causation": null,
  "correlation": null,
  "payload": {"note": "synthetic"},
  "payload_ref": null,
  "dedupe_key": "saga:7",
  "wake": "none",
  "state": "received"
}`

func TestCatalogue(t *testing.T) {
	c := catalogue(t)
	ns, ok := c.Namespace("execution_ledger")
	if !ok || ns.Writer != "saga_adapter" || !ns.ReadOnly {
		t.Fatalf("execution_ledger = %+v, %v", ns, ok)
	}
	for _, name := range []string{"odin_history", "transcript_archive", "surface_events"} {
		if n, ok := c.Namespace(name); !ok || n.ReadOnly {
			t.Errorf("%s = %+v, %v", name, n, ok)
		}
	}
	for _, k := range []string{"operator.command.stop", "operator.command.pause", "operator.command.revoke",
		"operator.command.take", "operator.command.return"} {
		if !c.IsControl(k) {
			t.Errorf("%s is not control", k)
		}
	}
	if c.IsControl("operator.message") || c.KnownKind("run.state") || !c.KnownKind("run.state.limit_paused") {
		t.Error("catalogue control or kind set is wrong")
	}
}

func TestDecodeEnvelopeStrict(t *testing.T) {
	c := catalogue(t)
	e, err := DecodeEnvelope([]byte(validEnvelope))
	if err != nil {
		t.Fatal(err)
	}
	if err := e.Check(c); err != nil {
		t.Fatal(err)
	}
	if e.SourceSeq == nil || *e.SourceSeq != 7 || e.Scope.Run == nil || !e.HasPayload() || e.PayloadRef != nil {
		t.Fatalf("decoded %+v", e)
	}
	bad := map[string]string{
		"unknown key":       strings.Replace(validEnvelope, `"wake"`, `"extra": 1, "wake"`, 1),
		"unknown scope key": strings.Replace(validEnvelope, `{"run":`, `{"repo": "x", "run":`, 1),
		"duplicate key":     strings.Replace(validEnvelope, `"wake": "none"`, `"wake": "none", "wake": "log"`, 1),
		"case-folded key":   strings.Replace(validEnvelope, `"kind"`, `"Kind"`, 1),
		"wrong type":        strings.Replace(validEnvelope, `"source_seq": 7`, `"source_seq": "7"`, 1),
		"trailing data":     validEnvelope + "{}",
	}
	for name, doc := range bad {
		if _, err := DecodeEnvelope([]byte(doc)); err == nil {
			t.Errorf("%s: decoded without error", name)
		}
	}
}

func TestEnvelopeCheck(t *testing.T) {
	c := catalogue(t)
	base, err := DecodeEnvelope([]byte(validEnvelope))
	if err != nil {
		t.Fatal(err)
	}
	mutations := map[string]func(*Envelope){
		"version":        func(e *Envelope) { e.Envelope = 2 },
		"id":             func(e *Envelope) { e.ID = "not-a-ulid" },
		"namespace":      func(e *Envelope) { e.Namespace = "elsewhere" },
		"kind":           func(e *Envelope) { e.Kind = "run.state" },
		"state":          func(e *Envelope) { e.State = "done" },
		"dedupe key":     func(e *Envelope) { e.DedupeKey = "" },
		"no payload":     func(e *Envelope) { e.Payload = []byte("null") },
		"absent payload": func(e *Envelope) { e.Payload = nil },
	}
	for name, mutate := range mutations {
		e := base
		mutate(&e)
		if err := e.Check(c); err == nil {
			t.Errorf("%s: Check passed", name)
		}
	}
}

func ev(id, ns, producer, key string, seq *int64) Envelope {
	ref := "evid:inbox/" + id
	return Envelope{ID: id, Envelope: 1, Namespace: ns, Producer: producer, Kind: "run.state.accepted",
		SourceSeq: seq, DedupeKey: key, PayloadRef: &ref, Wake: "none", State: StateReceived}
}

func seq(n int64) *int64 { return &n }

func TestIntake(t *testing.T) {
	l := NewMemoryLog(catalogue(t))
	type step struct {
		e      Envelope
		out    Outcome
		cursor *int64
		dups   int
	}
	steps := []step{
		{ev("01JAEV00000000000000000001", "odin_history", "saga", "saga:5", seq(5)), Accepted, seq(5), 0},
		// Same key: dedupe key is checked before the sequence.
		{ev("01JAEV00000000000000000002", "odin_history", "saga", "saga:5", seq(9)), DuplicateDedupeKey, seq(5), 1},
		// New key, sequence at the cursor.
		{ev("01JAEV00000000000000000003", "odin_history", "saga", "saga:5b", seq(5)), DuplicateSequence, seq(5), 2},
		// Below the cursor.
		{ev("01JAEV00000000000000000004", "odin_history", "saga", "saga:4", seq(4)), DuplicateSequence, seq(5), 3},
		// Sequences may skip.
		{ev("01JAEV00000000000000000005", "odin_history", "saga", "saga:9", seq(9)), Accepted, seq(9), 3},
		// No sequence: accepted, cursor unchanged.
		{ev("01JAEV00000000000000000006", "odin_history", "saga", "hash:a", nil), Accepted, seq(9), 3},
		// Same key and sequence under another producer, and another namespace.
		{ev("01JAEV00000000000000000007", "odin_history", "host:desk", "saga:5", seq(5)), Accepted, seq(5), 3},
		{ev("01JAEV00000000000000000008", "transcript_archive", "saga", "saga:5", seq(5)), Accepted, seq(5), 3},
		// A pair with no sequence yet has a null cursor.
		{ev("01JAEV00000000000000000009", "surface_events", "surface:focus", "k", nil), Accepted, nil, 3},
		{ev("01JAEV00000000000000000010", "surface_events", "surface:focus", "k", nil), DuplicateDedupeKey, nil, 4},
	}
	for i, s := range steps {
		got := l.Intake(s.e)
		want := IntakeResult{Outcome: s.out, CursorAfter: s.cursor, DuplicatesCounted: s.dups}
		if !reflect.DeepEqual(got, want) {
			t.Fatalf("step %d: got %+v (cursor %v), want %+v (cursor %v)", i, got, deref(got.CursorAfter), want, deref(want.CursorAfter))
		}
	}
	if n := len(l.Events()); n != 6 {
		t.Fatalf("%d events recorded, want 6 (duplicates are not recorded)", n)
	}
	for _, e := range l.Events() {
		if e.State != StateReceived {
			t.Fatalf("accepted event %s has state %s", e.ID, e.State)
		}
	}
	if c := l.Cursor("odin_history", "saga"); c == nil || *c != 9 {
		t.Fatalf("cursor = %v", deref(c))
	}
}

func deref(p *int64) string {
	if p == nil {
		return "null"
	}
	return fmt.Sprint(*p)
}

func TestAppendWriterCheck(t *testing.T) {
	l := NewMemoryLog(catalogue(t))
	if got := l.Append("service", ev("01JAEV00000000000000000001", "odin_history", "odin", "k1", nil)); got != Accepted {
		t.Fatalf("service to odin_history = %s", got)
	}
	if got := l.Append("capture_module", ev("01JAEV00000000000000000002", "odin_history", "odin", "k2", nil)); got != NamespaceWriterMismatch {
		t.Fatalf("capture_module to odin_history = %s", got)
	}
	// Writer check before the mirror's source_seq check.
	if got := l.Append("service", ev("01JAEV00000000000000000003", "execution_ledger", "saga", "k3", nil)); got != NamespaceWriterMismatch {
		t.Fatalf("service to execution_ledger = %s", got)
	}
	if got := l.Append("saga_adapter", ev("01JAEV00000000000000000004", "execution_ledger", "saga", "k4", nil)); got != MirrorRequiresSourceSeq {
		t.Fatalf("mirror without source_seq = %s", got)
	}
	if got := l.Append("saga_adapter", ev("01JAEV00000000000000000005", "execution_ledger", "saga", "k5", seq(1))); got != Accepted {
		t.Fatalf("mirror with source_seq = %s", got)
	}
	if n := len(l.Events()); n != 2 {
		t.Fatalf("%d events appended, want 2", n)
	}
	e := l.Events()[0]
	if l.Amend("service", e) != AppendOnlyViolation || l.Delete("service", e.ID) != AppendOnlyViolation {
		t.Fatal("amend or delete allowed")
	}
}

func TestProcessAndReplay(t *testing.T) {
	c := catalogue(t)
	mk := func(id, kind, state string) Envelope {
		e := ev(id, "odin_history", "operator:terminal", id, nil)
		e.Kind, e.State = kind, state
		return e
	}
	l := Restore(c, []Envelope{
		mk("01JAEV00000000000000000001", "run.state.accepted", StateReceived),
		mk("01JAEV00000000000000000002", "operator.command.return", StateReceived),
		mk("01JAEV00000000000000000003", "operator.message", StateProcessed),
		mk("01JAEV00000000000000000004", "operator.command.take", StateReceived),
		mk("01JAEV00000000000000000005", "operator.message", StateReceived),
	})
	want := []string{"01JAEV00000000000000000002", "01JAEV00000000000000000004",
		"01JAEV00000000000000000001", "01JAEV00000000000000000005"}
	if got := l.Replay(); !reflect.DeepEqual(got, want) {
		t.Fatalf("Replay = %v, want %v", got, want)
	}
	if got := l.Process("01JAEV00000000000000000004"); got != Processed {
		t.Fatalf("Process = %s", got)
	}
	if got := l.Process("01JAEV00000000000000000004"); got != AlreadyProcessed {
		t.Fatalf("second Process = %s", got)
	}
	if got := l.Process("01JAEV00000000000000000099"); got != UnknownEvent {
		t.Fatalf("Process(unknown) = %s", got)
	}
	want = []string{"01JAEV00000000000000000002", "01JAEV00000000000000000001", "01JAEV00000000000000000005"}
	if got := l.Replay(); !reflect.DeepEqual(got, want) {
		t.Fatalf("Replay after process = %v, want %v", got, want)
	}
	if got := NewMemoryLog(c).Replay(); got == nil || len(got) != 0 {
		t.Fatalf("empty Replay = %#v, want an empty non-nil slice", got)
	}
}
