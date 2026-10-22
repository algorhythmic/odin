import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig, devices } from '@playwright/test';

// Browsers live inside this directory; nothing is installed system-wide.
process.env.PLAYWRIGHT_BROWSERS_PATH ||= path.join(path.dirname(fileURLToPath(import.meta.url)), '.playwright-browsers');

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: { baseURL: 'http://127.0.0.1:5318', trace: 'off' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } }],
  webServer: {
    command: 'npm run build && npm run preview',
    url: 'http://127.0.0.1:5318',
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
