/**
 * The Copilot's *off* path, tested as carefully as its on path (§9, M6).
 *
 * These tests never call the API. That is the point: the claim this build makes
 * is that the app is complete without a key, and the way to prove it is to run
 * the whole thing with no key configured and assert that nothing is broken,
 * nothing is nagging, and nothing has quietly reached for the network.
 *
 * The on path cannot be exercised here without a real credential, and a test
 * that ships a key would fail gate G7 by design. The transport is covered by
 * unit tests against a fake in `@cmw/ai`; what only a browser can prove is that
 * the Anthropic SDK — a Node-first library whose credential chain Vite shims out
 * — does not break the file on load.
 */

import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

import { expect, test, type Page } from '@playwright/test';

const ARTIFACT = pathToFileURL(
  resolve(import.meta.dirname, '../dist/CoachMillaWellness.html'),
).href;

async function seeded(page: Page): Promise<string[]> {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });

  await page.goto(ARTIFACT);
  await page.getByRole('button', { name: /load the sample practice/i }).click();
  await expect(page.getByText(/Sample practice loaded/i)).toBeVisible();
  return errors;
}

test.describe('the Copilot with no key configured', () => {
  test('offers to switch on rather than showing a broken feature', async ({ page }) => {
    await seeded(page);

    await page.goto(`${ARTIFACT}#/sessions`);
    await page.getByText(/GROW|GREAT/).first().click();
    await expect(page.getByRole('heading', { name: 'Framework' })).toBeVisible();

    await expect(page.getByText(/needs the Copilot/i).first()).toBeVisible();
    await expect(page.getByRole('button', { name: /open settings/i }).first()).toBeVisible();
    // No dead control: the run button must not exist at all when it cannot run.
    await expect(page.getByRole('button', { name: 'Analyze session' })).toHaveCount(0);
  });

  test('settings say plainly that it is off and what that costs her', async ({ page }) => {
    await seeded(page);
    await page.goto(`${ARTIFACT}#/vault`);

    await expect(page.getByRole('heading', { name: 'AI Copilot' })).toBeVisible();
    await expect(page.getByText(/Sessions, wheels and content all work exactly as they do now/i)).toBeVisible();

    // The key field exists, is a password field, and is empty.
    const key = page.getByLabel('Anthropic API key');
    await expect(key).toHaveAttribute('type', 'password');
    await expect(key).toHaveValue('');

    // The model pickers stay hidden until there is a Copilot to configure —
    // four selects for a feature she has not switched on is furniture.
    await expect(page.getByLabel('Session Analyzer')).toHaveCount(0);
  });

  test('does not offer a download of the file she already has open', async ({ page }) => {
    // The hosted build offers the offline copy; over `file://` she is holding it,
    // and a button offering to download it reads as a bug.
    await seeded(page);
    await page.goto(`${ARTIFACT}#/vault`);
    await expect(page.getByRole('heading', { name: 'Your data' })).toBeVisible();
    await expect(page.getByRole('button', { name: /download the offline copy/i })).toHaveCount(0);
  });

  test('the ledger reads zero, not blank', async ({ page }) => {
    await seeded(page);
    await page.goto(`${ARTIFACT}#/insights`);

    await expect(page.getByRole('heading', { name: /how your practice is going/i })).toBeVisible();
    await expect(page.getByText(/Nothing spent yet/i)).toBeVisible();
    await expect(page.getByText(/\$0\.00 this month/i).first()).toBeVisible();
  });

  test('the Coach Growth Curve charts the sample practice', async ({ page }) => {
    // M5's reason to exist: her own adherence per element, from graded sessions.
    await seeded(page);
    await page.goto(`${ARTIFACT}#/insights`);

    await expect(page.getByRole('heading', { name: 'Coach Growth Curve' })).toBeVisible();
    await expect(page.getByText('Across every graded cycle')).toBeVisible();
    await expect(page.getByText(/is your thinnest element/i)).toBeVisible();

    // Both frameworks are reachable, and GREAT has its own elements.
    await page.getByRole('tab', { name: 'GREAT' }).click();
    await expect(page.getByText('Reality & Rapport').first()).toBeVisible();
  });

  test('bundling the Anthropic SDK did not cost the file its offline promise', async ({ page }) => {
    const external: string[] = [];
    page.on('request', (request) => {
      const url = request.url();
      if (!url.startsWith('file://') && !url.startsWith('data:') && !url.startsWith('blob:')) {
        external.push(url);
      }
    });

    const errors = await seeded(page);
    await page.goto(`${ARTIFACT}#/insights`);
    await page.goto(`${ARTIFACT}#/vault`);

    // The SDK imports `node:fs` and `node:path` for its default credential
    // chain; Vite replaces both with empty stubs. Passing an explicit key means
    // that chain is never entered — this is the assertion that keeps it true.
    expect(errors, `console errors:\n${errors.join('\n')}`).toEqual([]);
    expect(external, `external requests: ${external.join(', ')}`).toEqual([]);
  });
});
