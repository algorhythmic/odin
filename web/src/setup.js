// Synthetic configuration is kept apart from the service projection.
// Callers supply the fixture, so this store also runs without a browser.
const copy = (value) => structuredClone(value);
const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
export const STEPS = ['providers', 'harnesses', 'models', 'roles'];

export function createSetupStore(fixture, { fresh = false } = {}) {
  const catalogue = copy(fixture);
  let draft = {
    providers: copy(fixture.providers), harnesses: copy(fixture.state.harnesses),
    roles: copy(fixture.presets.cross_family.roles), preset: 'cross_family',
  };
  let completed = copy(fixture.state.completed);
  if (fresh) {
    for (const p of draft.providers) {
      for (const l of p.lineages) l.status = 'not_connected';
    }
    for (const h of Object.values(draft.harnesses)) h.enabled = false;
    completed = Object.fromEntries(STEPS.map((s) => [s, false]));
  }
  let applied = copy(draft);
  let appliedCompleted = copy(completed);
  let appliedOnce = false;
  let version = 0;
  const listeners = new Set();
  const notify = () => {
    version += 1;
    for (const fn of listeners) fn(version);
  };
  const harness = (id) => catalogue.harnesses.find((h) => h.id === id);
  const provider = (id) => draft.providers.find((p) => p.id === id);
  const lineages = (hid) => provider(harness(hid)?.provider)?.lineages.filter((l) => l.status === 'connected') || [];
  const enabled = () => catalogue.harnesses.filter((h) => draft.harnesses[h.id]?.enabled && !h.fixture_only);
  const model = (hid, mid) => catalogue.models[hid]?.find((m) => m.id === mid);
  const hasDefaultLineage = (h) => lineages(h.id).some((l) => l.id === draft.harnesses[h.id].lineage);
  const validDefault = (h) => {
    const d = draft.harnesses[h.id];
    return hasDefaultLineage(h) && model(h.id, d.model)?.efforts.includes(d.effort);
  };

  function validation() {
    const notes = [];
    const add = (role, kind, message) => notes.push({ role, kind, message });
    const counts = {};
    for (const r of Object.values(draft.roles)) counts[r.lineage] = (counts[r.lineage] || 0) + 1;
    for (const { id } of catalogue.roles) {
      const r = draft.roles[id];
      const h = harness(r.harness);
      if (id === 'executive' && r.harness !== 'claude-code') {
        add(id, 'blocking', 'The executive must use Claude Code for Remote Control and the Odin channel.');
      }
      if (!lineages(r.harness).length) {
        add(id, 'blocking', 'This harness’s provider has no connected sign-in.');
      } else if (!lineages(r.harness).some((l) => l.id === r.lineage)) {
        add(id, 'blocking', 'Choose a connected sign-in for this harness.');
      }
      if (!h || h.fixture_only || !draft.harnesses[r.harness]?.enabled) {
        add(id, 'blocking', 'Enable this harness before applying.');
      }
      if (!model(r.harness, r.model)?.efforts.includes(r.effort)) {
        add(id, 'blocking', 'Choose a supported model and effort.');
      }
    }
    for (const p of draft.providers) {
      for (const l of p.lineages) {
        if (counts[l.id] > l.max_concurrent_turns) {
          const turns = `limit ${l.max_concurrent_turns} concurrent turn${l.max_concurrent_turns === 1 ? '' : 's'}`;
          notes.push({
            role: null, lineage: l.id, kind: 'info',
            message: `${counts[l.id]} roles share ${l.label}; ${turns}. Roles interleave.`,
          });
        }
      }
    }
    const family = (r) => harness(r.harness)?.provider;
    if (family(draft.roles.independent_review) === family(draft.roles.implementer)) {
      add('independent_review', 'warning', 'Same model family as the author; review is less independent');
    }
    for (const h of enabled()) {
      if (!validDefault(h)) add(null, 'blocking', `${h.label}: choose a connected default sign-in, model and effort.`);
    }
    return notes;
  }

  function canContinue(step) {
    if (step === 'providers') {
      return draft.providers.some((p) => p.supported && p.lineages.some((l) => l.status === 'connected'));
    }
    if (step === 'harnesses') return enabled().length > 0 && enabled().every(hasDefaultLineage);
    if (step === 'models') return enabled().length > 0 && enabled().every(validDefault);
    return !validation().some((n) => n.kind === 'blocking');
  }
  // Editing a later draft does not undo the setup already applied.
  const isDone = (s) => completed[s] && (appliedOnce || canContinue(s));
  const getState = () => ({
    catalogue, draft, applied, version, appliedOnce,
    completed: Object.fromEntries(STEPS.map((s) => [s, isDone(s)])),
    progress: STEPS.filter(isDone).length,
    complete: STEPS.every(isDone), dirty: !equal(draft, applied), notes: validation(),
  });
  function edit(fn) {
    draft = copy(draft);
    fn();
    notify();
  }

  return {
    getState,
    subscribe(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
    connectedLineages: lineages, canContinue,
    firstIncomplete: () => STEPS.find((s) => !isDone(s)) || 'review',
    completeStep(step) {
      if (!canContinue(step)) return false;
      if (step !== 'roles') completed[step] = true;
      notify();
      return true;
    },
    connect(pid, lid) {
      edit(() => {
        const p = provider(pid);
        const l = p?.lineages.find((l) => l.id === lid);
        if (p?.supported && l) l.status = 'waiting';
      });
    },
    completeSignIn(pid, lid) {
      edit(() => {
        const l = provider(pid)?.lineages.find((l) => l.id === lid);
        if (l?.status === 'waiting') l.status = 'connected';
      });
    },
    addLineage(pid) {
      const p = provider(pid);
      if (!p?.supported) return;
      const id = `${pid}-sign-in-${p.lineages.length + 1}`;
      edit(() => provider(pid).lineages.push({
        id, label: 'Additional login', status: 'not_connected', account_label: 'additional@example.invalid',
        plan: 'Synthetic subscription', max_concurrent_turns: 1,
      }));
      return id;
    },
    setLineageLabel(pid, lid, label) {
      edit(() => { provider(pid).lineages.find((l) => l.id === lid).label = label; });
    },
    setHarness(hid, value) {
      if (!draft.harnesses[hid] || (value && !lineages(hid).length)) return false;
      edit(() => {
        const d = draft.harnesses[hid];
        d.enabled = value;
        if (!lineages(hid).some((l) => l.id === d.lineage)) d.lineage = lineages(hid)[0]?.id || '';
      });
      return true;
    },
    setDefaultLineage(hid, lid) {
      if (lineages(hid).some((l) => l.id === lid)) edit(() => { draft.harnesses[hid].lineage = lid; });
    },
    selectModel(hid, mid) {
      if (model(hid, mid)) edit(() => {
        const d = draft.harnesses[hid];
        d.model = mid;
        if (!model(hid, mid).efforts.includes(d.effort)) d.effort = model(hid, mid).efforts[0];
      });
    },
    setEffort(hid, effort) {
      if (model(hid, draft.harnesses[hid]?.model)?.efforts.includes(effort)) {
        edit(() => { draft.harnesses[hid].effort = effort; });
      }
    },
    applyPreset(id) {
      if (catalogue.presets[id]) edit(() => {
        draft.roles = copy(catalogue.presets[id].roles);
        draft.preset = id;
      });
    },
    changeRole(id, cell, value) {
      if (!draft.roles[id] || !['harness', 'lineage', 'model', 'effort'].includes(cell)) return;
      edit(() => {
        const r = draft.roles[id];
        r[cell] = value;
        if (cell === 'harness') {
          const d = draft.harnesses[value];
          r.lineage = lineages(value).find((l) => l.id === d?.lineage)?.id || lineages(value)[0]?.id || '';
          r.model = d?.model || catalogue.models[value]?.[0]?.id || '';
          r.effort = d?.effort || model(value, r.model)?.efforts[0] || '';
        }
        if (cell === 'model' && !model(r.harness, value)?.efforts.includes(r.effort)) {
          r.effort = model(r.harness, value)?.efforts[0] || '';
        }
        draft.preset = 'custom';
      });
    },
    apply() {
      if (!STEPS.slice(0, 3).every(canContinue) || !canContinue('roles')) return false;
      applied = copy(draft);
      completed = Object.fromEntries(STEPS.map((s) => [s, true]));
      appliedCompleted = copy(completed);
      appliedOnce = true;
      notify();
      return true;
    },
    discard() {
      draft = copy(applied);
      completed = copy(appliedCompleted);
      notify();
    },
  };
}
