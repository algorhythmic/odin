export const VIEW_LABELS = {
  tree: 'Tree', queue: 'Queue', lanes: 'Lanes', graph: 'Graph', decisions: 'Decisions', board: 'Board',
};

const VIEWS = {
  queue: {
    title: 'Agent Queue',
    reveals: 'Pending assignments, admission blockers, concurrency limits and backpressure.',
    controls: ['Reprioritize work', 'Pause scheduling', 'Adjust authorized limits'],
    records: 'Assignment priority, admission blockers, lineage capacity and authorized concurrency limits.',
  },
  lanes: {
    title: 'Agent Lanes',
    reveals: 'Parallel activity over time: execution, review, waits, interruptions and handoffs.',
    controls: ['Select an interval', 'Inspect a wait', 'Steer work', 'Pause work'],
    records: 'Recorded activity intervals, review and wait events, interruptions and handoffs.',
  },
  graph: {
    title: 'Agent Graph',
    reveals: 'Relationships among planners, workers, reviewer positions, assignments, tools and dependencies.',
    controls: ['Follow a dependency', 'Inspect ownership', 'Find what blocks an outcome'],
    records: 'Typed relationships, assignment ownership, tool associations and recorded dependencies.',
  },
  decisions: {
    title: 'Decision Tree',
    reveals: 'Recorded alternatives, their consequences, selected paths and unresolved operator choices.',
    controls: ['Choose an option', 'Request clarification', 'Approve a specific proposal'],
    records: 'Recorded options, consequences, selected and rejected alternatives, and unresolved choices. No inferred model reasoning.',
  },
  board: {
    title: 'Delegate Board',
    reveals: 'Assignment distribution, available capacity and capability fit.',
    controls: ['Assign work', 'Propose reassignment', 'Change priority', 'Inspect routing choices'],
    records: 'Assignments, available lineage capacity, capability requirements and recorded routing choices.',
  },
};

export function ViewPlaceholder({ view }) {
  const info = VIEWS[view];
  return (
    <section class="placeholder" data-testid="view-placeholder" aria-labelledby="view-title">
      <span class="eyebrow">Project view · Not built yet</span>
      <h2 id="view-title">{info.title}</h2>
      <p>{info.reveals}</p>
      <h3>Records needed</h3>
      <p class="muted">{info.records}</p>
      <h3>Planned controls</h3>
      <div class="actions-row">
        {info.controls.map((label) => (
          <button key={label} type="button" disabled aria-describedby="view-command-note">{label}</button>
        ))}
      </div>
      <p id="view-command-note" class="muted">Commands are not connected</p>
    </section>
  );
}
