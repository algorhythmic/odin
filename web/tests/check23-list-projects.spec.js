// R4b synthetic prototype: a project is a grouping, with no session identity or selection state.
import { test, expect } from '@playwright/test';
import { snapshot } from './helpers.js';

for (const mode of ['Tree', 'List']) test(`project identity and disclosure in ${mode}`, async ({ page }) => {
  for (const p of snapshot.projects) {
    await page.goto(`/#/projects/${p.id}`);
    await page.getByRole('button', { name: mode, exact: true }).click();
    const node = mode === 'Tree' ? page.getByTestId('project-node')
      : page.getByRole('treeitem', { name: `Project ${p.name}`, exact: true });
    await expect(node.getByTestId('project-glyph').locator('svg path').first()).toBeAttached();
    await expect(node.locator('.project-eyebrow')).toHaveText('PROJECT');
    await expect(node.locator('strong')).toHaveText(p.name);
    const live = snapshot.sessions.filter((s) => s.project_id === p.id && s.lifecycle !== 'retired');
    const counts = [
      [live.filter((s) => s.lifecycle === 'running').length, 'running'],
      [live.filter((s) => s.lifecycle === 'waiting_for_input' || s.needs_operator_input).length, 'needs you'],
      [live.filter((s) => s.lifecycle === 'ended'
        && snapshot.runs.some((r) => r.session_id === s.id && r.outcome === 'failed')).length, 'failed'],
    ];
    for (const [count, label] of counts) {
      await expect(node.locator('.project-count').filter({ hasText: `${count} ${label}` })).toHaveCount(1);
    }
    await expect(node.locator('.project-state-bar')).toHaveAttribute('role', 'img');
    await expect(node.locator('.project-state-bar')).toHaveAttribute('aria-label', /No live agents|\d+ (running|needs you|done)/);
    await expect(node.locator('.project-metrics')).toContainText(`${live.length} agents`);
    await expect(node.locator('.project-metrics')).toContainText(/tok|unknown/);
    await expect(node.getByTestId('provider-logo')).toHaveCount(0);
    await expect(node.getByTestId('status-chip')).toHaveCount(0);
    await expect(node).not.toHaveClass(/selected|card/);
    await expect(node).not.toHaveAttribute('aria-selected');
    await expect(node).toHaveAttribute('aria-expanded', 'true');
    if (mode === 'Tree') await expect(node).toHaveAccessibleName(`Collapse project ${p.name}`);
    else await expect(node).toHaveAccessibleDescription(`Collapse project ${p.name}`);
    await node.focus();
    await page.keyboard.press('Enter');
    await expect(node).toBeFocused();
    await expect(node).toHaveAttribute('aria-expanded', 'false');
    if (mode === 'Tree') await expect(node).toHaveAccessibleName(`Expand project ${p.name}`);
    else await expect(node).toHaveAccessibleDescription(`Expand project ${p.name}`);
    await page.keyboard.press('Space');
    await expect(node).toHaveAttribute('aria-expanded', 'true');
    await expect(page.getByTestId('detail-panel')).toHaveCount(0);
  }
});
