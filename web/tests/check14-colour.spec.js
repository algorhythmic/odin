// Pass 4 operator colour decisions (synthetic): the synthetic-data badge
// is a quiet --warn badge, visibly calmer than and distinct from the
// needs-you status, and --accent is confined to links, buttons, focus
// rings, active resize feedback and the typed-relationship overlay. Checked in both themes.
import { test, expect } from '@playwright/test';
import { PID, sessionUrl, shot } from './helpers.js';

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
  await page.getByRole('button', { name: 'Key', exact: true }).click();
  // Focus the key's overlay switch so its accent focus ring joins the walk.
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
  await checkGrouping(page);
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
  await checkGrouping(page);
  await shot(page, 'colour-light');
});


async function checkGrouping(page) {
  // Follow the Agents entry so this also works when the dashboard becomes home.
  await page.goto(`/#/projects/${PID}`);
  await page.goto(`/${await page.getByTestId('sidebar-executive').getAttribute('href')}`);
  const group = await resolveToken(page, '--group');
  const canvas = await resolveToken(page, '--canvas');
  const luminance = (rgb) => {
    const c = rgb.match(/\d+/g).slice(0, 3).map((n) => {
      const x = Number(n) / 255;
      return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
    });
    return c[0] * 0.2126 + c[1] * 0.7152 + c[2] * 0.0722;
  };
  const [a, b] = [luminance(group), luminance(canvas)].sort((x, y) => y - x);
  expect((a + 0.05) / (b + 0.05), 'grouping contrast against canvas').toBeGreaterThanOrEqual(3);
  const hits = await page.evaluate(([rgb, props]) => {
    const offenders = [];
    for (const el of document.querySelectorAll('*')) for (const prop of props) {
      if (getComputedStyle(el).getPropertyValue(prop) !== rgb) continue;
      const allowed = el.closest('.legend-row[data-style="project"]')
        || el.matches('.project-edge') && prop === 'stroke'
        || el.closest('.project-node, .list-row[data-node-kind="project"]');
      if (!allowed) offenders.push(`${el.tagName}.${el.getAttribute('class')} ${prop}`);
    }
    return offenders;
  }, [group, PROPS]);
  expect(hits, '--group is reserved for project grouping').toEqual([]);
  expect(await page.locator('.project-node').first().evaluate((el) => getComputedStyle(el).borderLeftColor)).toBe(group);
  expect(await page.locator('.project-edge').first().evaluate((el) => getComputedStyle(el).stroke)).toBe(group);
}

// Resolve mixed and transparent colours through canvas, including ancestor surfaces.
async function projectTextContrast(page) {
  const failures = await page.locator('.project-label').evaluateAll((labels) => {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 1;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    const luminance = (c) => {
      const linear = [...c].slice(0, 3).map((v) => {
        const x = v / 255;
        return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
      });
      return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722;
    };
    return labels.flatMap((label) => [...label.querySelectorAll(
      '.project-eyebrow, strong, .project-count, .project-metrics > span')].flatMap((el) => {
      const ancestors = [];
      for (let p = el; p; p = p.parentElement) ancestors.unshift(p);
      ctx.clearRect(0, 0, 1, 1);
      for (const p of ancestors) {
        ctx.fillStyle = getComputedStyle(p).backgroundColor;
        ctx.fillRect(0, 0, 1, 1);
      }
      const bg = luminance(ctx.getImageData(0, 0, 1, 1).data);
      ctx.fillStyle = getComputedStyle(el).color;
      ctx.fillRect(0, 0, 1, 1);
      const fg = luminance(ctx.getImageData(0, 0, 1, 1).data);
      const ratio = (Math.max(fg, bg) + 0.05) / (Math.min(fg, bg) + 0.05);
      return ratio >= 4.5 ? [] : [{ text: el.textContent, ratio }];
    }));
  });
  expect(failures, 'all project text meets 4.5:1 on its actual surface').toEqual([]);
}

for (const theme of ['dark', 'light']) test(`project surfaces and text contrast in tree and list: ${theme}`, async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  if (theme === 'light') await page.getByTestId('theme-toggle').click();
  for (const mode of ['Tree', 'List']) {
    await page.getByRole('button', { name: mode, exact: true }).click();
    await projectTextContrast(page);
    const surfaces = await page.evaluate(() => {
      const project = document.querySelector('.project-node, .list-row[data-node-kind="project"]');
      const session = document.querySelector('.card, .list-row[data-node-kind="session"]');
      return [getComputedStyle(project).backgroundColor, getComputedStyle(session).backgroundColor];
    });
    expect(surfaces[0], 'project surface differs from a session').not.toBe(surfaces[1]);
    await shot(page, `r4b-project-${mode.toLowerCase()}-${theme}`);
  }
});
