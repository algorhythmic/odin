// Handoff check 8 (partial, synthetic): transcript markup is shown as text.
import { test, expect } from '@playwright/test';
import { sessionUrl, shot } from './helpers.js';

test('hostile transcript markup renders as literal text', async ({ page }) => {
  const dialogs = [];
  page.on('dialog', (d) => { dialogs.push(d.message()); d.dismiss(); });
  await page.goto(sessionUrl('ses-worker-a2'));
  const transcript = page.getByTestId('transcript');
  await expect(transcript).toContainText('<img src=x onerror=alert(1)>');
  await expect(transcript).toContainText('<script>alert("xss")</script>');
  await expect(transcript).toContainText('javascript:alert(1)');
  await expect(transcript.locator('img, script, a, iframe, object')).toHaveCount(0);
  await page.waitForTimeout(200);
  expect(dialogs).toEqual([]);
  // The browser stores layout preferences only.
  const keys = await page.evaluate(() => Object.keys(localStorage));
  expect(keys.every((k) => k.startsWith('odin-web-prefs'))).toBe(true);
  await shot(page, 'untrusted-transcript');
});
