// SYNTHETIC fixture for the Odin web app prototype.
//
// Nothing here comes from Odin's service or any real session. The shapes
// are a working proposal for the browser-facing projection, not a schema.
//
// Semantics the prototype must preserve:
// - parent_session_id is session ANCESTRY only: the recorded session that
//   started this one. null means a root, or an imported session whose parent
//   is unknown. Never infer it from timing, layout or transcript wording.
// - Review, delegation, run association and assignment ownership are typed
//   entries in `relationships`, never parent edges.
// - cost covers the session's OWN turns only, so descendant totals can be
//   summed without counting a parent aggregate twice. amount_usd null means
//   unknown, not zero.
// - A resumption keeps the same Odin session (`resumption`); a new attempt
//   is a distinct session (`attempt_of`, `attempt`, `previous_attempt`).

export const synthetic = true;

export const projects = [
  {
    id: 'proj-odin-webapp',
    name: 'Odin web app (synthetic)',
    summary: 'Synthetic project used to exercise the agent tree.',
    host: 'workstation-a (synthetic)',
  },
  {
    id: 'proj-contract-pins',
    name: 'Contract pins (synthetic)',
    summary: 'Small second synthetic project.',
    host: 'workstation-a (synthetic)',
  },
];

export const commitments = [
  { id: 'cmt-webapp-v0', project_id: 'proj-odin-webapp', title: 'Deliver the agent tree prototype', status: 'at_risk', owner: 'ses-exec-01' },
  { id: 'cmt-ops-probe', project_id: 'proj-odin-webapp', title: 'Probe the offline host', status: 'blocked', owner: 'ses-exec-01' },
  { id: 'cmt-pin-refresh', project_id: 'proj-contract-pins', title: 'Refresh the pinned contract', status: 'in_progress', owner: 'ses-pin-exec' },
];

export const assignments = [
  { id: 'asg-portfolio', project_id: 'proj-odin-webapp', commitment_id: 'cmt-webapp-v0', owner_session_id: 'ses-exec-01', summary: 'Coordinate the web app commitment', progress: 'in_progress' },
  { id: 'asg-integration', project_id: 'proj-odin-webapp', commitment_id: 'cmt-webapp-v0', owner_session_id: 'ses-integ-01', summary: 'Integrate workstream returns', progress: 'in_progress' },
  { id: 'asg-tree-proto', project_id: 'proj-odin-webapp', commitment_id: 'cmt-webapp-v0', owner_session_id: 'ses-integ-01', summary: 'Build the tree prototype', progress: 'awaiting_review' },
  { id: 'asg-layout-spike', project_id: 'proj-odin-webapp', commitment_id: 'cmt-webapp-v0', owner_session_id: 'ses-worker-a2', summary: 'Measure layout on 500 nodes', progress: 'done_unverified' },
  { id: 'asg-review-exec', project_id: 'proj-odin-webapp', commitment_id: 'cmt-webapp-v0', owner_session_id: 'ses-exec-01', summary: 'Independent review of the tree prototype', progress: 'in_progress' },
  { id: 'asg-review-integ', project_id: 'proj-odin-webapp', commitment_id: 'cmt-webapp-v0', owner_session_id: 'ses-integ-01', summary: 'Integration review of the tree prototype', progress: 'in_progress' },
  { id: 'asg-docs', project_id: 'proj-odin-webapp', commitment_id: 'cmt-webapp-v0', owner_session_id: 'ses-exec-01', summary: 'Align the decision record', progress: 'in_progress' },
  { id: 'asg-ops-probe', project_id: 'proj-odin-webapp', commitment_id: 'cmt-ops-probe', owner_session_id: 'ses-exec-01', summary: 'Check the remote host', progress: 'blocked', blocked_reason: 'Host offline since the last observation' },
  { id: 'asg-legacy', project_id: 'proj-odin-webapp', commitment_id: null, owner_session_id: null, summary: 'Imported terminal session (owner unknown)', progress: 'unknown' },
  { id: 'asg-pin-coord', project_id: 'proj-contract-pins', commitment_id: 'cmt-pin-refresh', owner_session_id: 'ses-pin-exec', summary: 'Coordinate the pin refresh', progress: 'in_progress' },
  { id: 'asg-pin-update', project_id: 'proj-contract-pins', commitment_id: 'cmt-pin-refresh', owner_session_id: 'ses-pin-exec', summary: 'Update the producer pin', progress: 'in_progress' },
];

export const runs = [
  { id: 'run-tree-1', project_id: 'proj-odin-webapp', assignment_id: 'asg-tree-proto', session_id: 'ses-worker-a1', outcome: 'failed', summary: 'Attempt 1 checks failed' },
  { id: 'run-tree-2', project_id: 'proj-odin-webapp', assignment_id: 'asg-tree-proto', session_id: 'ses-worker-a2', outcome: 'unverified', summary: 'Attempt 2 returned; review pending' },
  { id: 'run-layout', project_id: 'proj-odin-webapp', assignment_id: 'asg-layout-spike', session_id: 'ses-helper-01', outcome: 'unknown', summary: 'Outcome not recorded before retirement' },
  { id: 'run-pin', project_id: 'proj-contract-pins', assignment_id: 'asg-pin-update', session_id: 'ses-pin-worker', outcome: 'verified', summary: 'Digest check passed' },
];

const T = '2026-10-21T';

export const sessions = [
  {
    id: 'ses-exec-01', project_id: 'proj-odin-webapp', parent_session_id: null, provenance: 'recorded',
    role: 'executive', assignment_id: 'asg-portfolio', model: 'claude-fable-5-1', lifecycle: 'running',
    needs_operator_input: false, observed_at: `${T}10:42:00Z`, stale: false,
    cost: { amount_usd: 3.1, basis: 'measured' }, elapsed_s: 9240, budget: { limit_usd: 25, basis: 'requested' },
  },
  {
    id: 'ses-integ-01', project_id: 'proj-odin-webapp', parent_session_id: 'ses-exec-01', provenance: 'recorded',
    role: 'integration owner', assignment_id: 'asg-integration', model: 'claude-opus-5-5', lifecycle: 'running',
    needs_operator_input: false, observed_at: `${T}10:41:30Z`, stale: false,
    cost: { amount_usd: 4.05, basis: 'measured' }, elapsed_s: 7300, budget: { limit_usd: 20, basis: 'requested' },
  },
  {
    id: 'ses-worker-a1', project_id: 'proj-odin-webapp', parent_session_id: 'ses-integ-01', provenance: 'recorded',
    role: 'worker', assignment_id: 'asg-tree-proto', model: 'claude-opus-5-5', lifecycle: 'ended',
    needs_operator_input: false, observed_at: `${T}08:15:00Z`, stale: false,
    cost: { amount_usd: 1.4, basis: 'measured' }, elapsed_s: 2100, budget: null,
    attempt_of: 'asg-tree-proto', attempt: 1, previous_attempt: null,
  },
  {
    id: 'ses-worker-a2', project_id: 'proj-odin-webapp', parent_session_id: 'ses-integ-01', provenance: 'recorded',
    role: 'worker', assignment_id: 'asg-tree-proto', model: 'claude-opus-5-5', lifecycle: 'ended',
    needs_operator_input: false, observed_at: `${T}09:58:00Z`, stale: false,
    cost: { amount_usd: 2.2, basis: 'estimate' }, elapsed_s: 3300, budget: { limit_usd: 5, basis: 'requested' },
    attempt_of: 'asg-tree-proto', attempt: 2, previous_attempt: 'ses-worker-a1',
  },
  {
    id: 'ses-helper-01', project_id: 'proj-odin-webapp', parent_session_id: 'ses-worker-a2', provenance: 'recorded',
    role: 'subagent', assignment_id: 'asg-layout-spike', model: null, lifecycle: 'retired',
    needs_operator_input: false, observed_at: `${T}09:40:00Z`, stale: false,
    cost: { amount_usd: null, basis: 'unknown' }, elapsed_s: 600, budget: null,
  },
  {
    id: 'ses-review-exec', project_id: 'proj-odin-webapp', parent_session_id: 'ses-exec-01', provenance: 'recorded',
    role: 'reviewer', assignment_id: 'asg-review-exec', model: 'claude-haiku-5-5', lifecycle: 'waiting_for_input',
    needs_operator_input: true, observed_at: `${T}10:40:00Z`, stale: false,
    cost: { amount_usd: 0.35, basis: 'measured' }, elapsed_s: 900, budget: { limit_usd: 2, basis: 'requested' },
  },
  {
    id: 'ses-review-integ', project_id: 'proj-odin-webapp', parent_session_id: 'ses-integ-01', provenance: 'recorded',
    role: 'reviewer', assignment_id: 'asg-review-integ', model: 'claude-haiku-5-5', lifecycle: 'idle',
    needs_operator_input: false, observed_at: `${T}10:30:00Z`, stale: false,
    cost: { amount_usd: 0.2, basis: 'measured' }, elapsed_s: 720, budget: null,
  },
  {
    id: 'ses-docs-01', project_id: 'proj-odin-webapp', parent_session_id: 'ses-exec-01', provenance: 'recorded',
    role: 'documentation', assignment_id: 'asg-docs', model: 'claude-opus-5-5', lifecycle: 'running',
    needs_operator_input: false, observed_at: `${T}10:41:00Z`, stale: false,
    cost: { amount_usd: 0.9, basis: 'measured' }, elapsed_s: 4100, budget: null,
    resumption: { count: 1, resumed_from_host_session: 'host-sess-7f1 (synthetic)', resumed_at: `${T}09:00:00Z` },
  },
  {
    id: 'ses-ops-01', project_id: 'proj-odin-webapp', parent_session_id: 'ses-exec-01', provenance: 'recorded',
    role: 'operations', assignment_id: 'asg-ops-probe', model: 'gpt-codex (synthetic)', lifecycle: 'host_offline',
    needs_operator_input: false, observed_at: `${T}06:05:00Z`, stale: true,
    cost: { amount_usd: null, basis: 'unknown' }, elapsed_s: 1500, budget: null,
  },
  {
    id: 'ses-imported-01', project_id: 'proj-odin-webapp', parent_session_id: null, provenance: 'imported',
    role: 'imported terminal session', assignment_id: 'asg-legacy', model: null, lifecycle: 'retired',
    needs_operator_input: false, observed_at: `${T}02:00:00Z`, stale: false,
    cost: { amount_usd: null, basis: 'unknown' }, elapsed_s: null, budget: null,
  },
  {
    id: 'ses-pin-exec', project_id: 'proj-contract-pins', parent_session_id: null, provenance: 'recorded',
    role: 'executive', assignment_id: 'asg-pin-coord', model: 'claude-fable-5-1', lifecycle: 'running',
    needs_operator_input: false, observed_at: `${T}10:20:00Z`, stale: false,
    cost: { amount_usd: 0.6, basis: 'measured' }, elapsed_s: 1800, budget: null,
  },
  {
    id: 'ses-pin-worker', project_id: 'proj-contract-pins', parent_session_id: 'ses-pin-exec', provenance: 'recorded',
    role: 'worker', assignment_id: 'asg-pin-update', model: 'claude-sonnet-5-5', lifecycle: 'waiting_for_input',
    needs_operator_input: true, observed_at: `${T}10:19:00Z`, stale: false,
    cost: { amount_usd: 0.25, basis: 'estimate' }, elapsed_s: 1200, budget: null,
  },
  // Recorded parent outside this data set: shown as a labelled root, never
  // attached to a guessed parent. Its branch has no known cost at all.
  {
    id: 'ses-pin-audit', project_id: 'proj-contract-pins', parent_session_id: 'ses-pin-archived', provenance: 'recorded',
    role: 'audit worker', assignment_id: null, model: null, lifecycle: 'ended',
    needs_operator_input: false, observed_at: `${T}08:40:00Z`, stale: false,
    cost: { amount_usd: null, basis: 'unknown' }, elapsed_s: 900, budget: null,
  },
  {
    id: 'ses-pin-audit-helper', project_id: 'proj-contract-pins', parent_session_id: 'ses-pin-audit', provenance: 'recorded',
    role: 'audit helper', assignment_id: null, model: null, lifecycle: 'ended',
    needs_operator_input: false, observed_at: `${T}08:35:00Z`, stale: false,
    cost: { amount_usd: null, basis: 'unknown' }, elapsed_s: 300, budget: null,
  },
];

// Typed relationships other than ancestry. `from` and `to` are record ids.
export const relationships = [
  { id: 'rel-1', type: 'review', from: 'ses-review-exec', to: 'ses-worker-a2' },
  { id: 'rel-2', type: 'review', from: 'ses-review-integ', to: 'ses-worker-a2' },
  { id: 'rel-3', type: 'delegation', from: 'ses-integ-01', to: 'ses-worker-a2' },
  { id: 'rel-4', type: 'run_association', from: 'ses-worker-a2', to: 'run-tree-2' },
  { id: 'rel-5', type: 'run_association', from: 'ses-worker-a1', to: 'run-tree-1' },
  { id: 'rel-6', type: 'assignment_owner', from: 'ses-integ-01', to: 'asg-tree-proto' },
  { id: 'rel-7', type: 'run_association', from: 'ses-pin-worker', to: 'run-pin' },
];

export const decisions = [
  {
    id: 'dec-001', project_id: 'proj-odin-webapp', kind: 'approval', status: 'pending',
    requested_by: 'ses-review-exec', title: 'Approve merging the tree prototype',
    proposal: { id: 'prop-tree-merge', revision: 3, digest: 'sha256:5f2c…synthetic' },
  },
  {
    id: 'dec-002', project_id: 'proj-contract-pins', kind: 'decision', status: 'pending',
    requested_by: 'ses-pin-worker', title: 'Choose the pin refresh window',
    proposal: { id: 'prop-pin-window', revision: 1, digest: 'sha256:a91e…synthetic' },
  },
];

export const conversations = {
  'proj-odin-webapp': [
    { at: `${T}08:00:00Z`, speaker: 'operator', text: 'Start the agent tree prototype with synthetic data.' },
    { at: `${T}08:01:00Z`, speaker: 'ses-exec-01', text: 'Opened an integration owner and a docs session.' },
    { at: `${T}10:40:00Z`, speaker: 'ses-review-exec', text: 'Review needs an operator decision on dec-001.' },
  ],
  'proj-contract-pins': [
    { at: `${T}10:00:00Z`, speaker: 'operator', text: 'Refresh the producer pin this week.' },
  ],
};

const HOSTILE = 'Pasted from a tool: <img src=x onerror=alert(1)> <script>alert("xss")</script> '
  + '[click me](javascript:alert(1)) <a href="javascript:alert(2)">link</a>';

const transcripts = {
  'ses-worker-a2': [
    { seq: 1, at: `${T}09:03:00Z`, speaker: 'ses-integ-01', text: 'Attempt 2: rebuild the tree prototype after attempt 1 failed checks.' },
    { seq: 2, at: `${T}09:10:00Z`, speaker: 'ses-worker-a2', text: HOSTILE },
    { kind: 'gap', from_seq: 3, to_seq: 7, reason: 'Transcript capture interrupted (synthetic gap)' },
    { seq: 8, at: `${T}09:57:00Z`, speaker: 'ses-worker-a2', text: 'Done. Returning for review.' },
  ],
};

const evidence = {
  'ses-worker-a2': [
    { id: 'ev-1', label: 'Playwright run (synthetic)', source: 'execution receipt rcpt-synthetic-1', owner: 'ses-worker-a2' },
    { id: 'ev-2', label: 'Diff summary (synthetic)', source: 'session return', owner: 'ses-worker-a2' },
  ],
  'ses-worker-a1': [
    { id: 'ev-3', label: 'Failing check log (synthetic)', source: 'execution receipt rcpt-synthetic-0', owner: 'ses-worker-a1' },
  ],
};

// Simulates a paginated detail request: transcripts and evidence load only
// for the selected session, never for the whole tree.
export function loadSessionDetail(sessionId) {
  const session = sessions.find((s) => s.id === sessionId);
  const transcript = transcripts[sessionId] || (session ? [
    { seq: 1, at: session.observed_at, speaker: sessionId, text: `Synthetic transcript entry for ${sessionId}.` },
  ] : []);
  return new Promise((resolve) => {
    setTimeout(() => resolve({ transcript, evidence: evidence[sessionId] || [] }), 30);
  });
}
