import base from './playwright.config.js';

// Timing scenario for handoff check 9, kept out of the default run so the
// functional suite and its --repeat-each runs are not slowed or skewed.
export default { ...base, testDir: './tests-perf' };
