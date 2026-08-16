/**
 * The hosted shape — the app served over HTTP, under production headers.
 *
 * Every other browser test in this suite runs over `file://`, because that is
 * how she opens the copy she keeps. This one exists because "deployable
 * anywhere" is a different claim, and the failures it catches are ones `file://`
 * cannot see:
 *
 *  - a Content-Security-Policy that looks harmless in a config file and blanks
 *    the app in a browser,
 *  - the root URL 404ing because the build renamed `index.html` away,
 *  - IndexedDB behaving differently under an http origin than under a file one,
 *  - the deployed page and the downloadable file drifting apart.
 *
 * The server under test sets the same headers `netlify.toml` sets, so any static
 * host configured equivalently is covered by these assertions.
 */

import { expect, test, type Page } from '@playwright/test';

const BASE = process.env.CMW_HOSTED_BASE ?? 'http://localhost:4173';

async function open(page: Page, path = '/'): Promise<string[]> {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    // A CSP violation surfaces here and nowhere else — a blocked inline script
    // leaves a blank page with a clean network log.
    if (message.type() === 'error') errors.push(message.text());
  });
  await page.goto(`${BASE}${path}`);
  return errors;
}

test.describe('served over HTTP', () => {
  test('the root URL is the app', async ({ page }) => {
    const errors = await open(page);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    expect(errors, `console errors:\n${errors.join('\n')}`).toEqual([]);
  });

  test('the production CSP does not break it', async ({ page }) => {
    const errors = await open(page);

    // Exercised rather than merely loaded: inline scripts, inline styles, an SVG
    // wheel, a canvas export path and IndexedDB all sit behind different CSP
    // directives, and a policy can pass a bare page load while failing the app.
    await page.getByRole('button', { name: /load the sample practice/i }).click();
    await expect(page.getByText(/Sample practice loaded/i)).toBeVisible();

    await page.goto(`${BASE}/#/wheel`);
    await expect(page.locator('svg').first()).toBeVisible();

    await page.goto(`${BASE}/#/insights`);
    await expect(page.getByRole('heading', { name: 'Coach Growth Curve' })).toBeVisible();

    expect(errors, `console errors under CSP:\n${errors.join('\n')}`).toEqual([]);
  });

  test('sends the headers the deployment promises', async ({ request }) => {
    const response = await request.get(`${BASE}/`);
    const headers = response.headers();

    expect(headers['content-security-policy']).toContain("default-src 'none'");
    // The Copilot's one outbound destination, and nothing else.
    expect(headers['content-security-policy']).toContain('connect-src');
    expect(headers['content-security-policy']).toContain('https://api.anthropic.com');
    expect(headers['content-security-policy']).toContain("frame-ancestors 'none'");
    expect(headers['x-content-type-options']).toBe('nosniff');
    expect(headers['x-frame-options']).toBe('DENY');
    expect(headers['referrer-policy']).toBe('no-referrer');
    // The document is the application, so a stale cache is a stale app.
    expect(headers['cache-control']).toContain('must-revalidate');
  });

  test('makes no third-party request when the Copilot is off', async ({ page }) => {
    const offsite: string[] = [];
    page.on('request', (request) => {
      const url = request.url();
      if (!url.startsWith(BASE) && !url.startsWith('data:') && !url.startsWith('blob:')) {
        offsite.push(url);
      }
    });

    await open(page);
    await page.getByRole('button', { name: /load the sample practice/i }).click();
    await expect(page.getByText(/Sample practice loaded/i)).toBeVisible();
    await page.goto(`${BASE}/#/content`);

    // §6's promise survives hosting: no font CDN, no analytics, no telemetry.
    expect(offsite, `third-party requests: ${offsite.join(', ')}`).toEqual([]);
  });

  test('persists to IndexedDB across a reload on an http origin', async ({ page }) => {
    // Storage is partitioned by origin, so this is genuinely a different test
    // from the `file://` one — not a duplicate of it.
    await open(page);
    await page.getByRole('button', { name: /load the sample practice/i }).click();
    await expect(page.getByText(/Sample practice loaded/i)).toBeVisible();

    await page.reload();
    await page.goto(`${BASE}/#/clients`);
    await expect(page.getByText('Naledi M.')).toBeVisible();
  });

  test('offers the artefact as a download, identical to the page being served', async ({ request }) => {
    const site = await request.get(`${BASE}/index.html`);
    const artefact = await request.get(`${BASE}/CoachMillaWellness.html`);

    expect(artefact.status()).toBe(200);
    expect(artefact.headers()['content-disposition']).toContain('attachment');
    // The file she downloads from the site is the site.
    expect(Buffer.from(await artefact.body()).equals(Buffer.from(await site.body()))).toBe(true);
  });

  test('routes the two convenience URLs', async ({ request }) => {
    const app = await request.get(`${BASE}/app`, { maxRedirects: 0 });
    expect(app.status()).toBe(302);
    expect(app.headers()['location']).toBe('/#/deck');

    const download = await request.get(`${BASE}/download`, { maxRedirects: 0 });
    expect(download.status()).toBe(302);
    expect(download.headers()['location']).toBe('/CoachMillaWellness.html');
  });

  test('offers the offline copy, and actually downloads it', async ({ page }) => {
    await open(page, '/#/vault');

    const button = page.getByRole('button', { name: /download the offline copy/i });
    await expect(button).toBeVisible();

    const download = await Promise.all([page.waitForEvent('download'), button.click()]).then(
      ([event]) => event,
    );
    expect(download.suggestedFilename()).toBe('CoachMillaWellness.html');
  });

  test('deep-links straight into a hash route on a cold load', async ({ page }) => {
    // The router is hash-based, so no SPA rewrite is needed — this proves it
    // rather than assuming it, because the absence of a rewrite in netlify.toml
    // is a deliberate decision that would otherwise look like an omission.
    const errors = await open(page, '/#/vault');
    await expect(page.getByRole('heading', { name: 'Your data' })).toBeVisible();
    expect(errors).toEqual([]);
  });
});
