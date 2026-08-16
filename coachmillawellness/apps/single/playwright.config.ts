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

/**
 * One port, read once.
 *
 * `serve-dist.mjs` honours `PORT`, so hard-coding the URL here meant setting
 * `PORT=4174` started the server on 4174 while Playwright waited on 4173 —
 * sixty seconds of silence, then "Timed out waiting for config.webServer", which
 * points at the server rather than at the mismatch that actually caused it.
 * Deriving both from the same value makes the override work instead of misfire.
 */
const HOSTED_PORT = process.env.PORT ?? '4173';

export default defineConfig({
  testDir: './e2e',
  // Only the `hosted` project needs it; Playwright starts it once and the
  // `file://` projects simply ignore it.
  webServer: {
    command: 'node e2e/serve-dist.mjs',
    url: `http://localhost:${HOSTED_PORT}/index.html`,
    reuseExistingServer: !process.env.CI,
    stdout: 'ignore',
  },
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
    { name: 'desktop', use: { ...devices['Desktop Chrome'] }, testIgnore: /hosted\.spec\.ts/ },
    {
      // The deployed shape: HTTP origin, production headers. Split out because it
      // needs a server, and because every other project deliberately runs over
      // `file://` — the environment she opens the downloaded copy in.
      name: 'hosted',
      use: { ...devices['Desktop Chrome'] },
      testMatch: /hosted\.spec\.ts/,
    },
    {
      name: 'mobile',
      // A real phone viewport, so the bottom tab bar and the ≥44px targets are
      // exercised rather than assumed.
      use: { ...devices['Pixel 7'] },
      testMatch: /mobile\.spec\.ts/,
    },
  ],
});
