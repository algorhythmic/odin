package conformance

import (
	"fmt"

	"github.com/algorhythmic/odin/substrate/effects"
	"github.com/algorhythmic/odin/substrate/eventlog"
	"github.com/algorhythmic/odin/substrate/records"
	"github.com/algorhythmic/odin/substrate/strictjson"
)

// operation runs one operation on a schema-checked input file.
type operation func(r *Runner, data []byte) (Result, error)

// operations maps every cases.json operation except validate to its
// runner; the input types mirror fixtures/inputs.schema.json.
var operations = map[string]operation{
	"append":                 runNamespace("append"),
	"amend":                  runNamespace("amend"),
	"delete":                 runNamespace("delete"),
	"intake_sequence":        runIntake,
	"replay":                 runReplay,
	"inbox_sequence":         runInboxSequence,
	"check_revision":         runCheckRevision,
	"check_owner":            runCheckOwner,
	"commitment_transfer":    runTransfer,
	"operation_reuse":        runOperationReuse,
	"check_message_size":     runMessageSize,
	"combine":                runCombine,
	"restart":                runRestart,
	"reconcile":              runReconcile,
	"dispatch":               runDispatch,
	"revalidate":             runRevalidate,
	"check_mapping_coverage": runMappingCoverage,
}

func decode(data []byte, v any) error {
	if err := strictjson.Unmarshal(data, v); err != nil {
		return fmt.Errorf("fixture defect: strict decode: %w", err)
	}
	return nil
}

func outcome[T ~string](o T) Result { return Result{"outcome": string(o)} }

// --- §4.2 namespace writer check -------------------------------------------

type namespaceInput struct {
	Log    []eventlog.Envelope `json:"log"`
	Writer string              `json:"writer"`
	Event  eventlog.Envelope   `json:"event"`
}

func runNamespace(op string) operation {
	return func(r *Runner, data []byte) (Result, error) {
		var in namespaceInput
		if err := decode(data, &in); err != nil {
			return nil, err
		}
		// `log` is what was appended before; it is restored, not re-checked.
		l := eventlog.Restore(r.catalog, in.Log)
		switch op {
		case "append":
			return outcome(l.Append(in.Writer, in.Event)), nil
		case "amend":
			return outcome(l.Amend(in.Writer, in.Event)), nil
		default:
			return outcome(l.Delete(in.Writer, in.Event.ID)), nil
		}
	}
}

// --- §4.3 intake ----------------------------------------------------------

type eventsInput struct {
	Events []eventlog.Envelope `json:"events"`
}

func runIntake(r *Runner, data []byte) (Result, error) {
	var in eventsInput
	if err := decode(data, &in); err != nil {
		return nil, err
	}
	l := eventlog.NewMemoryLog(r.catalog)
	steps := make([]Result, 0, len(in.Events))
	for i, e := range in.Events {
		if err := e.Check(r.catalog); err != nil {
			return nil, fmt.Errorf("fixture defect: event %d: %w", i, err)
		}
		res := l.Intake(e)
		var cursor any // null until the pair accepts a sequence
		if res.CursorAfter != nil {
			cursor = *res.CursorAfter
		}
		steps = append(steps, Result{
			"outcome":            string(res.Outcome),
			"cursor_after":       cursor,
			"duplicates_counted": res.DuplicatesCounted,
		})
	}
	return Result{"steps": steps}, nil
}

// --- §4.4 processing and replay ------------------------------------------

func replayResult(l *eventlog.MemoryLog) Result {
	return Result{"outcome": string(eventlog.Replayed), "replay_order": l.Replay()}
}

func runReplay(r *Runner, data []byte) (Result, error) {
	var in eventsInput
	if err := decode(data, &in); err != nil {
		return nil, err
	}
	return replayResult(eventlog.Restore(r.catalog, in.Events)), nil
}

type inboxInput struct {
	Events []eventlog.Envelope `json:"events"`
	Steps  []inboxStep         `json:"steps"`
}

type inboxStep struct {
	Op      string  `json:"op"`
	EventID *string `json:"event_id,omitempty"`
}

func runInboxSequence(r *Runner, data []byte) (Result, error) {
	var in inboxInput
	if err := decode(data, &in); err != nil {
		return nil, err
	}
	l := eventlog.Restore(r.catalog, in.Events)
	steps := make([]Result, 0, len(in.Steps))
	for i, s := range in.Steps {
		switch {
		case s.Op == "process" && s.EventID != nil:
			steps = append(steps, outcome(l.Process(*s.EventID)))
		case s.Op == "replay":
			steps = append(steps, replayResult(l))
		default:
			return nil, fmt.Errorf("fixture defect: step %d: op %q", i, s.Op)
		}
	}
	return Result{"steps": steps}, nil
}

// --- §4.5 revisions, ownership, operations, size ---------------------------

type checkRevisionInput struct {
	RecordRev        int64  `json:"record_rev"`
	ExpectedRevision *int64 `json:"expected_revision"`
}

func runCheckRevision(_ *Runner, data []byte) (Result, error) {
	var in checkRevisionInput
	if err := decode(data, &in); err != nil {
		return nil, err
	}
	return outcome(records.CheckRevision(in.RecordRev, in.ExpectedRevision)), nil
}

type checkOwnerInput struct {
	Session    records.PlanningSession `json:"session"`
	Commitment records.Commitment      `json:"commitment"`
}

func runCheckOwner(_ *Runner, data []byte) (Result, error) {
	var in checkOwnerInput
	if err := decode(data, &in); err != nil {
		return nil, err
	}
	return outcome(records.CheckOwner(in.Session, in.Commitment)), nil
}

type transferInput struct {
	Commitment       records.Commitment `json:"commitment"`
	NewOwner         string             `json:"new_owner"`
	ExpectedRevision *int64             `json:"expected_revision"`
	Effects          []records.Effect   `json:"effects"`
}

func runTransfer(_ *Runner, data []byte) (Result, error) {
	var in transferInput
	if err := decode(data, &in); err != nil {
		return nil, err
	}
	res := records.TransferCommitment(in.Commitment, in.NewOwner, in.ExpectedRevision, in.Effects)
	out := outcome(res.Outcome)
	if res.Outcome == records.Transferred {
		out["generation_after"] = res.GenerationAfter
		out["rev_after"] = res.RevAfter
		out["held_effects"] = res.HeldEffects
	}
	return out, nil
}

type operationReuseInput struct {
	Existing records.Effect `json:"existing"`
	Incoming records.Effect `json:"incoming"`
}

func runOperationReuse(_ *Runner, data []byte) (Result, error) {
	var in operationReuseInput
	if err := decode(data, &in); err != nil {
		return nil, err
	}
	o, err := records.OperationReuse(in.Existing, in.Incoming)
	if err != nil {
		return nil, fmt.Errorf("fixture defect: %w", err)
	}
	return outcome(o), nil
}

func runMessageSize(_ *Runner, data []byte) (Result, error) {
	var m records.Message
	if err := decode(data, &m); err != nil {
		return nil, err
	}
	return outcome(records.CheckMessageSize(m)), nil
}

// --- §4.6 review combination ----------------------------------------------

type combineInput struct {
	Round     int64              `json:"round"`
	Positions []records.Position `json:"positions"`
}

func runCombine(_ *Runner, data []byte) (Result, error) {
	var in combineInput
	if err := decode(data, &in); err != nil {
		return nil, err
	}
	res := records.Combine(in.Round, in.Positions)
	out := outcome(res.Outcome)
	if res.Outcome == records.Approved {
		out["verdict_result"] = res.VerdictResult
	}
	return out, nil
}

// --- §4.7 effects -----------------------------------------------------------

type effectsInput struct {
	Effects []records.Effect `json:"effects"`
}

func runRestart(_ *Runner, data []byte) (Result, error) {
	var in effectsInput
	if err := decode(data, &in); err != nil {
		return nil, err
	}
	res := effects.Restart(in.Effects)
	return Result{"outcome": string(res.Outcome), "marked_unknown": res.MarkedUnknown}, nil
}

type reconcileInput struct {
	Effect    records.Effect `json:"effect"`
	Lookup    *string        `json:"lookup"`
	HostState *string        `json:"host_state"`
}

func runReconcile(_ *Runner, data []byte) (Result, error) {
	var in reconcileInput
	if err := decode(data, &in); err != nil {
		return nil, err
	}
	res := effects.Reconcile(in.Effect, in.Lookup, in.HostState)
	out := outcome(res.Outcome)
	if res.Outcome != effects.Reconciled {
		return out, nil
	}
	out["state_after"] = res.StateAfter
	out["retry_allowed"] = res.RetryAllowed
	if res.SurfaceToOperator {
		out["surface_to_operator"] = true
	}
	if res.Note != "" {
		out["note"] = res.Note
	}
	if res.SameRequestID {
		out["same_request_id"] = true
	}
	if res.CountsAgainstCaps {
		out["counts_against_caps"] = true
	}
	if res.HeldForHost {
		out["held_for_host"] = true
	}
	return out, nil
}

type dispatchInput struct {
	Effect             records.Effect           `json:"effect"`
	Prompt             *records.AttentionPrompt `json:"prompt"`
	RecoveryInProgress bool                     `json:"recovery_in_progress"`
}

func runDispatch(_ *Runner, data []byte) (Result, error) {
	var in dispatchInput
	if err := decode(data, &in); err != nil {
		return nil, err
	}
	res := effects.Dispatch(in.Effect, in.Prompt, in.RecoveryInProgress)
	out := outcome(res.Outcome)
	if res.Outcome == effects.Dispatched {
		out["state_after"] = res.StateAfter
	}
	return out, nil
}

type revalidateInput struct {
	Effect  records.Effect  `json:"effect"`
	Context effects.Context `json:"context"`
}

func runRevalidate(_ *Runner, data []byte) (Result, error) {
	var in revalidateInput
	if err := decode(data, &in); err != nil {
		return nil, err
	}
	res := effects.Revalidate(in.Effect, in.Context)
	out := outcome(res.Outcome)
	if res.Outcome == effects.CancelledStale {
		out["reason"] = res.Reason
	}
	return out, nil
}

// --- §4.8 migration mapping ---------------------------------------------------

func runMappingCoverage(r *Runner, data []byte) (Result, error) {
	var m records.Mapping
	if err := decode(data, &m); err != nil {
		return nil, err
	}
	res := records.CheckMappingCoverage(m, r.fields)
	return Result{"outcome": string(res.Outcome), "uncovered": res.Uncovered}, nil
}
