package eventlog

// Outcome is an exact outcome string of the semantics contract
// (substrate/schemas README §4.9).
type Outcome string

// Outcomes of append, amend, delete, intake, process and replay.
const (
	Accepted                Outcome = "accepted"
	NamespaceWriterMismatch Outcome = "namespace_writer_mismatch"
	MirrorRequiresSourceSeq Outcome = "mirror_requires_source_seq"
	AppendOnlyViolation     Outcome = "append_only_violation"
	DuplicateDedupeKey      Outcome = "duplicate_dedupe_key"
	DuplicateSequence       Outcome = "duplicate_sequence"
	Processed               Outcome = "processed"
	AlreadyProcessed        Outcome = "already_processed"
	UnknownEvent            Outcome = "unknown_event"
	Replayed                Outcome = "replayed"
)

// IntakeResult is the result of one intake step (substrate README §4.3):
// the outcome, the cursor of the event's (namespace, producer) pair after
// the step (nil while the pair has accepted no sequence), and the running
// total of duplicates seen by this log.
type IntakeResult struct {
	Outcome           Outcome
	CursorAfter       *int64
	DuplicatesCounted int
}

// Log is the append-only event log. Events are only ever appended; the one
// change an event may undergo is its inbox state moving from received to
// processed (Appendix A). Amendment and deletion are refused.
type Log interface {
	// Append appends e to e.Namespace on behalf of writer (§4.2).
	Append(writer string, e Envelope) Outcome
	// Amend refuses to change an appended event (§4.2).
	Amend(writer string, e Envelope) Outcome
	// Delete refuses to remove an appended event (§4.2).
	Delete(writer string, id string) Outcome
	// Intake records e in the inbox unless it is a duplicate (§4.3).
	Intake(e Envelope) IntakeResult
	// Process moves a received event to processed (§4.4).
	Process(id string) Outcome
	// Replay returns the ids of every received event, control kinds
	// first, each group in received order (§4.4).
	Replay() []string
}

type pairKey struct {
	namespace string
	producer  string
}

type pairState struct {
	cursor *int64
	seen   map[string]bool
}

// MemoryLog is the in-memory Log of I0. It is not safe for concurrent use.
type MemoryLog struct {
	cat        *Catalogue
	events     []Envelope // received order
	pairs      map[pairKey]*pairState
	duplicates int
}

var _ Log = (*MemoryLog)(nil)

// NewMemoryLog returns an empty log using the catalogue c.
func NewMemoryLog(c *Catalogue) *MemoryLog {
	return &MemoryLog{cat: c, pairs: map[pairKey]*pairState{}}
}

// Restore returns a log holding events in received order with the states
// they carry, as an inbox read back after a restart (I/O contract §9
// step 3). It does not apply intake rules.
func Restore(c *Catalogue, events []Envelope) *MemoryLog {
	l := NewMemoryLog(c)
	l.events = append(l.events, events...)
	return l
}

// Events returns a copy of the log's events in received order.
func (l *MemoryLog) Events() []Envelope {
	return append([]Envelope(nil), l.events...)
}

// Append implements the namespace writer check (substrate README §4.2;
// ODIN-ADR-006): the writer must be the catalogue's single writer for the
// namespace, checked first; a read-only namespace (the execution-ledger
// mirror) then accepts only events carrying Saga's source_seq.
func (l *MemoryLog) Append(writer string, e Envelope) Outcome {
	ns, ok := l.cat.Namespace(e.Namespace)
	if !ok || ns.Writer != writer {
		return NamespaceWriterMismatch
	}
	if ns.ReadOnly && e.SourceSeq == nil {
		return MirrorRequiresSourceSeq
	}
	l.events = append(l.events, e)
	return Accepted
}

// Amend always refuses: the log is append-only in every namespace and for
// every writer, the namespace's own included (§4.2). Redaction is a
// tombstone message operation (I/O contract §8), out of I0 scope.
func (l *MemoryLog) Amend(writer string, e Envelope) Outcome {
	return AppendOnlyViolation
}

// Delete always refuses, like Amend.
func (l *MemoryLog) Delete(writer string, id string) Outcome {
	return AppendOnlyViolation
}

// Intake applies the dedupe rules of substrate README §4.3 (AC-01; I/O
// contract §9), with state per (namespace, producer) pair: a dedupe key
// already seen is duplicate_dedupe_key; a source_seq at or below the
// pair's cursor is duplicate_sequence; otherwise the event is accepted with
// state received, its key recorded and the cursor moved to its source_seq
// when it has one. Duplicates are counted and not recorded.
func (l *MemoryLog) Intake(e Envelope) IntakeResult {
	k := pairKey{e.Namespace, e.Producer}
	p := l.pairs[k]
	if p == nil {
		p = &pairState{seen: map[string]bool{}}
		l.pairs[k] = p
	}
	var out Outcome
	switch {
	case p.seen[e.DedupeKey]:
		out = DuplicateDedupeKey
	case e.SourceSeq != nil && p.cursor != nil && *e.SourceSeq <= *p.cursor:
		out = DuplicateSequence
	default:
		out = Accepted
	}
	if out == Accepted {
		e.State = StateReceived
		l.events = append(l.events, e)
		p.seen[e.DedupeKey] = true
		if e.SourceSeq != nil {
			seq := *e.SourceSeq
			p.cursor = &seq
		}
	} else {
		l.duplicates++
	}
	return IntakeResult{Outcome: out, CursorAfter: copyInt(p.cursor), DuplicatesCounted: l.duplicates}
}

// Cursor returns the cursor of a (namespace, producer) pair, nil when the
// pair has accepted no sequence.
func (l *MemoryLog) Cursor(namespace, producer string) *int64 {
	if p := l.pairs[pairKey{namespace, producer}]; p != nil {
		return copyInt(p.cursor)
	}
	return nil
}

func copyInt(p *int64) *int64 {
	if p == nil {
		return nil
	}
	v := *p
	return &v
}

// Process moves the first event with this id from received to processed
// (substrate README §4.4; AC-27): processed, already_processed (an
// idempotent no-op) or unknown_event.
func (l *MemoryLog) Process(id string) Outcome {
	for i := range l.events {
		if l.events[i].ID != id {
			continue
		}
		if l.events[i].State == StateProcessed {
			return AlreadyProcessed
		}
		l.events[i].State = StateProcessed
		return Processed
	}
	return UnknownEvent
}

// Replay returns the ids of every event still received: first those whose
// kind is a control kind in kinds.json, in received order, then the rest in
// received order (I/O contract §9 step 3; substrate README §4.4).
func (l *MemoryLog) Replay() []string {
	control := []string{}
	rest := []string{}
	for _, e := range l.events {
		if e.State != StateReceived {
			continue
		}
		if l.cat.IsControl(e.Kind) {
			control = append(control, e.ID)
		} else {
			rest = append(rest, e.ID)
		}
	}
	return append(control, rest...)
}
