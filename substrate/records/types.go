// Package records holds the typed records of I/O contract §2 and
// Appendix A (one struct per records/*.schema.json) and the semantic checks
// that need more than a schema: revisions, ownership, commitment transfer,
// operation-id reuse, message size, review combination and the heimdall
// mapping coverage (substrate/schemas README §4.5, §4.6, §4.8).
//
// Nullable fields are pointers; optional keys are pointers with omitempty;
// objects the contract leaves open (an Effect's receipt, a verdict's
// checklist) are raw JSON. Decode with Decode, which is strict.
package records

import (
	"encoding/json"

	"github.com/algorhythmic/odin/substrate/strictjson"
)

// Decode strictly decodes one record (or any substrate value) into v:
// unknown keys, duplicate keys, wrong types and trailing data are rejected.
func Decode(data []byte, v any) error {
	return strictjson.Unmarshal(data, v)
}

// Meta holds the fields every revisioned record carries (Appendix A).
type Meta struct {
	ID        string `json:"id"`
	Rev       int64  `json:"rev"`
	CreatedAt string `json:"created_at"`
	UpdatedAt string `json:"updated_at"`
}

// SubjectRef is common.schema.json#/$defs/subject_ref.
type SubjectRef struct {
	Kind string `json:"kind"`
	ID   string `json:"id"`
}

// RecordRef is common.schema.json#/$defs/record_ref: a record id with the
// revision it was read at.
type RecordRef struct {
	ID  string `json:"id"`
	Rev int64  `json:"rev"`
}

// Usage is common.schema.json#/$defs/usage (§12; AC-22 for unavailable).
type Usage struct {
	Unavailable      *bool    `json:"unavailable,omitempty"`
	InputTokens      *int64   `json:"input_tokens,omitempty"`
	OutputTokens     *int64   `json:"output_tokens,omitempty"`
	CacheReadTokens  *int64   `json:"cache_read_tokens,omitempty"`
	CacheWriteTokens *int64   `json:"cache_write_tokens,omitempty"`
	LatencyMS        *int64   `json:"latency_ms,omitempty"`
	Retries          *int64   `json:"retries,omitempty"`
	CostUSD          *float64 `json:"cost_usd,omitempty"`
}

// Project is records/project.schema.json (§2 Project).
type Project struct {
	Meta
	Name                   string          `json:"name"`
	Sources                []ProjectSource `json:"sources"`
	Delegations            []string        `json:"delegations"`
	InterfaceDecisionOwner *string         `json:"interface_decision_owner"`
}

// ProjectSource is one registered source of a project.
type ProjectSource struct {
	Locator      string `json:"locator"`
	Digest       string `json:"digest"`
	Version      string `json:"version"`
	RegisteredAt string `json:"registered_at"`
}

// Commitment is records/commitment.schema.json (§2 Commitment;
// ODIN-ADR-007 checkpoints, decisions and provenance).
type Commitment struct {
	Meta
	Project             string         `json:"project"`
	Objective           string         `json:"objective"`
	Criteria            []Criterion    `json:"criteria"`
	State               string         `json:"state"`
	Owner               *string        `json:"owner"`
	OwnershipGeneration int64          `json:"ownership_generation"`
	Dependencies        []string       `json:"dependencies"`
	OpenDecisions       []OpenDecision `json:"open_decisions"`
	NextTrigger         *string        `json:"next_trigger"`
	Delegation          *string        `json:"delegation"`
	Evidence            []string       `json:"evidence"`
	Checkpoints         []Checkpoint   `json:"checkpoints"`
	Decisions           []TaskDecision `json:"decisions"`
	Provenance          *Provenance    `json:"provenance"`
}

// Criterion is one acceptance criterion of a commitment.
type Criterion struct {
	ID       string   `json:"id"`
	Text     string   `json:"text"`
	Evidence []string `json:"evidence"`
	Met      bool     `json:"met"`
}

// OpenDecision is a decision a commitment is waiting on.
type OpenDecision struct {
	ID       string `json:"id"`
	Text     string `json:"text"`
	RaisedBy string `json:"raised_by"`
}

// Checkpoint is a commitment checkpoint (ODIN-ADR-007).
type Checkpoint struct {
	ID         string   `json:"id"`
	At         string   `json:"at"`
	Summary    string   `json:"summary"`
	Evidence   []string `json:"evidence"`
	RecordedBy string   `json:"recorded_by"`
}

// TaskDecision is a recorded task decision (ODIN-ADR-007).
type TaskDecision struct {
	ID        string   `json:"id"`
	Question  string   `json:"question"`
	Choice    string   `json:"choice"`
	Rationale string   `json:"rationale"`
	DecidedBy string   `json:"decided_by"`
	At        string   `json:"at"`
	Evidence  []string `json:"evidence"`
}

// Provenance records an import from standalone heimdall (§14).
type Provenance struct {
	Source        string `json:"source"`
	NativeID      string `json:"native_id"`
	NativeRev     int64  `json:"native_rev"`
	ImportReceipt string `json:"import_receipt"`
}

// Assignment is records/assignment.schema.json (§2 Assignment).
type Assignment struct {
	Meta
	Commitment     string            `json:"commitment"`
	CommitmentRev  int64             `json:"commitment_rev"`
	Inputs         []AssignmentInput `json:"inputs"`
	Scope          string            `json:"scope"`
	OutputContract string            `json:"output_contract"`
	Owner          string            `json:"owner"`
	Backend        string            `json:"backend"`
	Limits         AssignmentLimits  `json:"limits"`
	State          string            `json:"state"`
	Run            *string           `json:"run"`
	RequestID      *string           `json:"request_id"`
}

// AssignmentInput is one pinned input of an assignment.
type AssignmentInput struct {
	Ref    string `json:"ref"`
	Digest string `json:"digest"`
}

// AssignmentLimits are an assignment's optional limits.
type AssignmentLimits struct {
	Iterations *int64   `json:"iterations,omitempty"`
	BudgetUSD  *float64 `json:"budget_usd,omitempty"`
}

// PlanningSession is records/planning_session.schema.json (§2).
type PlanningSession struct {
	Meta
	Project             string  `json:"project"`
	Adapter             string  `json:"adapter"`
	NativeSessionID     *string `json:"native_session_id"`
	Incarnation         int64   `json:"incarnation"`
	State               string  `json:"state"`
	Briefing            *string `json:"briefing"`
	BudgetUSD           float64 `json:"budget_usd"`
	OwnershipGeneration int64   `json:"ownership_generation"`
	Profile             string  `json:"profile"`
	Auth                Auth    `json:"auth"`
}

// Auth names a session's credential lineage by reference, never by value
// (AGENTS.md §6; D24).
type Auth struct {
	Mode          string `json:"mode"`
	CredentialRef string `json:"credential_ref"`
	RefreshOwner  string `json:"refresh_owner"`
}

// SessionBinding is records/session_binding.schema.json (§2;
// ODIN-ADR-009 host_offline).
type SessionBinding struct {
	Meta
	Subject         SubjectRef `json:"subject"`
	Harness         string     `json:"harness"`
	NativeSessionID string     `json:"native_session_id"`
	Host            string     `json:"host"`
	Incarnation     int64      `json:"incarnation"`
	State           string     `json:"state"`
	Environment     RecordRef  `json:"environment"`
	Capabilities    []string   `json:"capabilities"`
	Workspace       *Workspace `json:"workspace"`
	Predecessor     *string    `json:"predecessor"`
}

// Workspace is a binding's attachable workspace pane.
type Workspace struct {
	Host              string `json:"host"`
	ServerIncarnation int64  `json:"server_incarnation"`
	Pane              string `json:"pane"`
}

// Environment is records/environment.schema.json (ODIN-ADR-009).
type Environment struct {
	Meta
	Host               string              `json:"host"`
	HostIncarnation    int64               `json:"host_incarnation"`
	ProbedAt           string              `json:"probed_at"`
	ProbeVersion       string              `json:"probe_version"`
	Harnesses          []Harness           `json:"harnesses"`
	Herdr              *HerdrInfo          `json:"herdr"`
	Isolation          Isolation           `json:"isolation"`
	Surfaces           []string            `json:"surfaces"`
	Sensors            []string            `json:"sensors"`
	CredentialLineages []CredentialLineage `json:"credential_lineages"`
}

// Harness is one probed harness and its version.
type Harness struct {
	Name    string `json:"name"`
	Version string `json:"version"`
}

// HerdrInfo describes the third-party workspace multiplexer when present.
type HerdrInfo struct {
	Version string `json:"version"`
	Access  string `json:"access"`
}

// Isolation describes a host's sandboxing.
type Isolation struct {
	Sandbox          *string `json:"sandbox"`
	PlannerWorkspace bool    `json:"planner_workspace"`
}

// CredentialLineage names a credential lineage by reference (X-12, D24).
type CredentialLineage struct {
	Ref       string `json:"ref"`
	Mode      string `json:"mode"`
	Refresher string `json:"refresher"`
}

// HumanRequest is records/human_request.schema.json (§2).
type HumanRequest struct {
	Meta
	Assignment     string         `json:"assignment"`
	Run            *string        `json:"run"`
	Kind           string         `json:"kind"`
	Question       string         `json:"question"`
	Options        []string       `json:"options"`
	Authorizes     string         `json:"authorizes"`
	ProposalDigest *string        `json:"proposal_digest"`
	Recipient      string         `json:"recipient"`
	ExpiresAt      string         `json:"expires_at"`
	State          string         `json:"state"`
	Response       *HumanResponse `json:"response"`
	Channel        *string        `json:"channel"`
}

// HumanResponse is the answer to a human request.
type HumanResponse struct {
	Answer      string `json:"answer"`
	By          string `json:"by"`
	At          string `json:"at"`
	SourceEvent string `json:"source_event"`
}

// Approval is records/approval.schema.json (§2).
type Approval struct {
	Meta
	RequestID      string `json:"request_id"`
	RequestRev     int64  `json:"request_rev"`
	Principal      string `json:"principal"`
	ProposalDigest string `json:"proposal_digest"`
	SourceEvent    string `json:"source_event"`
	Channel        string `json:"channel"`
	ReceivedAt     string `json:"received_at"`
	ExpiresAt      string `json:"expires_at"`
	State          string `json:"state"`
}

// Review is records/review.schema.json (§2, §10; ODIN-ADR-013).
type Review struct {
	Meta
	RequestID          *string    `json:"request_id"`
	Type               string     `json:"type"`
	ArtifactLineage    []string   `json:"artifact_lineage"`
	EvidencePackDigest string     `json:"evidence_pack_digest"`
	Reviewer           string     `json:"reviewer"`
	Round              int64      `json:"round"`
	Positions          []Position `json:"positions"`
	Combination        *string    `json:"combination"`
	Verdict            *Verdict   `json:"verdict"`
	Usage              Usage      `json:"usage"`
}

// Position is one reviewer position of a review (ODIN-ADR-013).
type Position struct {
	Position string   `json:"position"`
	Harness  string   `json:"harness"`
	Model    string   `json:"model"`
	Family   string   `json:"family"`
	Verdict  *Verdict `json:"verdict"`
	Usage    Usage    `json:"usage"`
}

// Verdict is a review verdict (§10).
type Verdict struct {
	Result    string          `json:"result"`
	Checklist json.RawMessage `json:"checklist"`
	Findings  []Finding       `json:"findings"`
}

// Finding is one finding of a verdict (§10).
type Finding struct {
	Evidence          []string `json:"evidence"`
	Consequence       string   `json:"consequence"`
	MinimalCorrection string   `json:"minimal_correction"`
	Citations         []string `json:"citations"`
}

// EvaluatorResult is records/evaluator_result.schema.json (§2).
type EvaluatorResult struct {
	Meta
	Evaluator   string   `json:"evaluator"`
	Model       string   `json:"model"`
	InputDigest string   `json:"input_digest"`
	Result      string   `json:"result"`
	P           *float64 `json:"p"`
	Status      string   `json:"status"`
	Consequence string   `json:"consequence"`
	Outcome     *string  `json:"outcome"`
}

// SessionClassDecision is records/session_class_decision.schema.json
// (ODIN-ADR-014). The record never changes routing.
type SessionClassDecision struct {
	Meta
	Project   string             `json:"project"`
	Subject   SubjectRef         `json:"subject"`
	Chosen    string             `json:"chosen"`
	Rejected  []RejectedClass    `json:"rejected"`
	Inputs    SessionClassInputs `json:"inputs"`
	ConfigRev string             `json:"config_rev"`
	DecidedAt string             `json:"decided_at"`
	Outcome   *string            `json:"outcome"`
}

// RejectedClass is a session class the decision rejected, with why.
type RejectedClass struct {
	Class  string `json:"class"`
	Reason string `json:"reason"`
}

// SessionClassInputs are the inputs a session-class decision used.
type SessionClassInputs struct {
	EventKind              *string    `json:"event_kind"`
	AssignmentRequirements []string   `json:"assignment_requirements"`
	Environment            *RecordRef `json:"environment"`
	BudgetState            string     `json:"budget_state"`
}

// AttentionPrompt is records/attention_prompt.schema.json (ODIN-ADR-010).
type AttentionPrompt struct {
	Meta
	Effect        string          `json:"effect"`
	Project       string          `json:"project"`
	Subject       SubjectRef      `json:"subject"`
	Proposal      string          `json:"proposal"`
	Evidence      []string        `json:"evidence"`
	Surface       string          `json:"surface"`
	Rule          string          `json:"rule"`
	CoalescingKey string          `json:"coalescing_key"`
	Mode          string          `json:"mode"`
	CapState      CapState        `json:"cap_state"`
	ExpiresAt     string          `json:"expires_at"`
	State         string          `json:"state"`
	Response      *PromptResponse `json:"response"`
}

// CapState is a prompt's cap counters at creation.
type CapState struct {
	SurfaceToday int64 `json:"surface_today"`
	AllToday     int64 `json:"all_today"`
}

// PromptResponse is the operator's response to an attention prompt, or
// `expired` when none arrived.
type PromptResponse struct {
	Kind        string  `json:"kind"`
	Reason      *string `json:"reason"`
	Until       *string `json:"until"`
	By          *string `json:"by"`
	At          string  `json:"at"`
	SourceEvent *string `json:"source_event"`
}

// Prompt modes (ODIN-ADR-010).
const (
	PromptShadow = "shadow"
	PromptLive   = "live"
)

// Effect is records/effect.schema.json: one outbox entry (§2, §9).
type Effect struct {
	Meta
	OperationID           string          `json:"operation_id"`
	Destination           string          `json:"destination"`
	DestinationCapability string          `json:"destination_capability"`
	PayloadDigest         string          `json:"payload_digest"`
	Assignment            *string         `json:"assignment"`
	OwnerGeneration       *int64          `json:"owner_generation"`
	DelegationVersion     *int64          `json:"delegation_version"`
	ApprovalDigest        *string         `json:"approval_digest"`
	GuidanceRev           *int64          `json:"guidance_rev"`
	State                 string          `json:"state"`
	DispatchBlockedBy     *string         `json:"dispatch_blocked_by"`
	Attempts              int64           `json:"attempts"`
	Receipt               json.RawMessage `json:"receipt"`
	Reconciliation        *string         `json:"reconciliation"`
}

// Effect states (§2, §9).
const (
	EffectQueued         = "queued"
	EffectHeld           = "held"
	EffectInFlight       = "in_flight"
	EffectDelivered      = "delivered"
	EffectFailed         = "failed"
	EffectUnknown        = "unknown"
	EffectCancelledStale = "cancelled_stale"
	EffectSuperseded     = "superseded"
)

// Message is records/message.schema.json: one durable history row (§3).
// It is not a revisioned record.
type Message struct {
	Chat string  `json:"chat"`
	I    int64   `json:"i"`
	Kind string  `json:"kind"`
	Src  string  `json:"src"`
	Text string  `json:"text"`
	Size int64   `json:"size"`
	Date string  `json:"date"`
	Ref  *string `json:"ref"`
}
