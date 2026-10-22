// Pass 4 operator colour decisions (synthetic): the synthetic-data badge
// is a quiet --warn badge, visibly calmer than and distinct from the
// needs-you status, and --accent is confined to links, buttons, focus
// rings and the typed-relationship overlay. Checked in both themes.
import { test, expect } from '@playwright/test';
import { sessionUrl, shot } from './helpers.js';

const badge = (page) => page.getByTestId('synthetic-badge');
const theme = (page) => page.evaluate(() => document.documentElement.dataset.theme);

// Resolves a colour token to the rgb() form getComputedStyle reports,
// through a probe element (the raw value may be a hex string).
function resolveToken(page, name) {
  return page.evaluate((token) => {
    const value = getComputedStyle(document.documentElement).getPropertyValue(token);
    const probe = document.createElement('div');
    probe.style.color = value.trim();
    document.body.appendChild(probe);
    const rgb = getComputedStyle(probe).color;
    probe.remove();
    return rgb;
  }, name);
}

const PROPS = [
  'color', 'background-color',
  'border-top-color', 'border-right-color', 'border-bottom-color', 'border-left-color',
  'outline-color', 'fill', 'stroke',
];

async function checkBadge(page) {
  const warn = await resolveToken(page, '--warn');
  const needs = await resolveToken(page, '--status-needs');
  expect(warn, '--warn must differ from --status-needs').not.toBe(needs);
  await expect(badge(page)).toBeVisible();
  const styles = await badge(page).evaluate((el) => {
    const cs = getComputedStyle(el);
    return { color: cs.color, border: cs.borderTopColor };
  });
  expect(styles.color, 'badge text uses --warn').toBe(warn);
  expect(styles.border, 'badge border uses --warn').toBe(warn);
  return warn;
}

async function checkAccentConfined(page) {
  const accent = await resolveToken(page, '--accent');
  // Project view, relationship overlay on (the default), a session
  // selected through the URL.
  await page.goto(sessionUrl('ses-worker-a2'));
  await expect(page.locator('.relation-edge').first()).toBeVisible();
  await expect(page.getByTestId('session-card').first()).toBeVisible();
  // Focus the overlay toggle so its accent focus ring joins the walk.
  await page.evaluate(() => document.querySelector('.check input[type="checkbox"]').focus());

  const { hits, offenders } = await page.evaluate(([accentRgb, props]) => {
    const hits = [];
    const offenders = [];
    const label = (el) => [
      el.tagName.toLowerCase(),
      el.id ? `#${el.id}` : '',
      el.getAttribute('class') ? `.${String(el.getAttribute('class')).trim().split(/\s+/).join('.')}` : '',
      el.getAttribute('data-testid') ? `[data-testid=${el.getAttribute('data-testid')}]` : '',
    ].join('');
    for (const el of document.querySelectorAll('*')) {
      const cs = getComputedStyle(el);
      for (const prop of props) {
        if (cs.getPropertyValue(prop) !== accentRgb) continue;
        const where = `${label(el)} ${prop}`;
        const allowed = el.closest('a') || el.closest('button') || el.closest('.relation-edge')
          || (prop === 'outline-color' && el === document.activeElement);
        (allowed ? hits : offenders).push(where);
      }
    }
    return { hits, offenders };
  }, [accent, PROPS]);
  expect(offenders, 'accent colour outside links, buttons, overlays and the focused outline').toEqual([]);
  expect(hits.length, 'accent colour is actually used').toBeGreaterThan(0);
}

test('colour rules hold in the dark default theme', async ({ page }) => {
  await page.goto('/#/');
  expect(await theme(page)).toBe('dark');
  const warn = await checkBadge(page);
  expect(warn).toBe('rgb(194, 163, 110)');
  await checkAccentConfined(page);
  await shot(page, 'colour-dark');
});

test('colour rules hold in the light theme', async ({ page }) => {
  await page.goto('/#/');
  const toggle = page.getByTestId('theme-toggle');
  await toggle.click();
  expect(await theme(page)).toBe('light');
  const warn = await checkBadge(page);
  expect(warn).toBe('rgb(113, 96, 58)');
  await checkAccentConfined(page);
  await shot(page, 'colour-light');
});
