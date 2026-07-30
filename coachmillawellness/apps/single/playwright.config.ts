import { existsSync } from 'node:fs';

import { defineConfig, devices } from '@playwright/test';

/**
 * Gate G6 runs against the built artefact over `file://`, not a dev server —
 * that is the environment she actually opens it in.
 */

/**
 * Use a Chromium already on the machine when the pinned Playwright build differs
 * from what is installed. CI images commonly ship one browser revision and the
 * npm package expects another; downloading a second copy per run is slow and
 * fails outright in a sandbox with no egress.
 */
const PREINSTALLED = [
  '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  '/usr/bin/chromium',
  '/usr/bin/google-chrome',
];
const executablePath = PREINSTALLED.find((candidate) => existsSync(candidate));

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'line' : 'list',

  use: {
    ...devices['Desktop Chrome'],
    // The rail navigation appears at `lg`; the tab bar is covered separately.
    viewport: { width: 1280, height: 900 },
    acceptDownloads: true,
    trace: 'retain-on-failure',
    ...(executablePath ? { launchOptions: { executablePath } } : {}),
  },

  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    {
      name: 'mobile',
      // A real phone viewport, so the bottom tab bar and the ≥44px targets are
      // exercised rather than assumed.
      use: { ...devices['Pixel 7'] },
      testMatch: /mobile\.spec\.ts/,
    },
  ],
});
