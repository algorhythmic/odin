import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig, devices } from '@playwright/test';

// Browsers live inside this directory; nothing is installed system-wide.
process.env.PLAYWRIGHT_BROWSERS_PATH ||= path.join(path.dirname(fileURLToPath(import.meta.url)), '.playwright-browsers');

// ODIN_WEB_TEST_PORT lets parallel worktrees run their suites side by side.
const port = Number(process.env.ODIN_WEB_TEST_PORT) || 5318;
const origin = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: { baseURL: origin, trace: 'off' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } }],
  webServer: {
    command: `npm run build && npx vite preview --host 127.0.0.1 --port ${port} --strictPort`,
    url: origin,
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
