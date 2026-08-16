/**
 * Gate G6 — the twelve-step cross-platform smoke script.
 *
 * Runs against the *built* single file over `file://`, which is how she will
 * actually open it. That matters: a dev-server test would pass while a real
 * `file://` load failed on an absolute asset path or a blocked module import, and
 * the whole premise of Build 1 is that it works from her Files app.
 *
 * The script from §12 G6: add client → session → analyze → wheel → content →
 * export.
 */

import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

import { expect, test, type Page } from '@playwright/test';

const ARTIFACT = pathToFileURL(
  resolve(import.meta.dirname, '../dist/CoachMillaWellness.html'),
).href;

async function open(page: Page): Promise<void> {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });

  await page.goto(ARTIFACT);
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

  // A single-file app that throws on boot still renders a shell, so failing the
  // test on console errors is the only way to catch it.
  expect(errors, `console errors on load:\n${errors.join('\n')}`).toEqual([]);
}

/**
 * Clicks a primary nav destination.
 *
 * Scoped to the nav landmark and matched exactly, because a loose
 * `getByRole('link', { name: 'Content' })` also matches the "Skip to content"
 * link — and because the rail and the tab bar are both present in the DOM, with
 * only one visible at any viewport.
 */
async function go(page: Page, label: string): Promise<void> {
  await page
    .getByRole('navigation', { name: 'Main' })
    .getByRole('link', { name: label, exact: true })
    .first()
    .click();
}

test.describe('CoachMillaWellness.html', () => {
  test('loads from the filesystem with no network requests', async ({ page }) => {
    const external: string[] = [];
    page.on('request', (request) => {
      const url = request.url();
      if (!url.startsWith('file://') && !url.startsWith('data:') && !url.startsWith('blob:')) {
        external.push(url);
      }
    });

    await open(page);

    // §6: zero external requests. This is what makes it work on a plane.
    expect(external, `external requests: ${external.join(', ')}`).toEqual([]);
  });

  test('first run guides setup rather than showing an empty dashboard', async ({ page }) => {
    await open(page);

    await expect(page.getByRole('heading', { name: /set up your practice/i })).toBeVisible();
    await expect(page.getByText('Add a coachee', { exact: false }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: /load the sample practice/i })).toBeVisible();
  });

  test('runs the full twelve-step script', async ({ page }) => {
    await open(page);

    // 1 — load the sample practice, so the Deck has something to answer with.
    await page.getByRole('button', { name: /load the sample practice/i }).click();
    await expect(page.getByText(/Sample practice loaded/i)).toBeVisible();

    // 2 — the Deck answers "what does today need from me?"
    await expect(page.getByRole('heading', { name: /^Good (morning|afternoon|evening)$/ })).toBeVisible();

    // 3 — clients index shows both seeded coachees with their risk state.
    await go(page, 'Clients');
    await expect(page.getByText('Naledi M.')).toBeVisible();
    await expect(page.getByText('Thabo K.')).toBeVisible();

    // 4 — add a coachee of our own.
    await page.getByRole('button', { name: /add coachee/i }).first().click();
    const dialog = page.getByRole('dialog');
    await dialog.getByLabel('Name').fill('Lerato Test');
    await dialog.getByRole('button', { name: 'Add coachee' }).click();
    await expect(page.getByRole('heading', { name: 'Lerato Test' })).toBeVisible();

    // 5 — add a goal, and prove the SMARTER gap is visible and toggleable.
    await page.getByLabel('New goal').fill('Swim twice a week');
    await page.getByRole('button', { name: /^Add$/ }).first().click();
    await expect(page.getByText('Swim twice a week')).toBeVisible();

    const exciting = page.getByRole('button', { name: /Exciting/ }).first();
    await expect(exciting).toHaveAttribute('aria-pressed', 'false');
    await exciting.click();
    await expect(exciting).toHaveAttribute('aria-pressed', 'true');

    // 6 — score a wheel through the keyboard-accessible controls (§4.7), and
    // confirm the wheel itself reflects it.
    await page.getByRole('tab', { name: 'Wheel' }).click();
    const wheel = page.locator('svg[role="img"]').first();
    await expect(wheel).toBeVisible();

    const careerSlider = page.getByRole('slider', { name: /Career score/ });
    await careerSlider.fill('9');
    await expect(careerSlider).toHaveValue('9');
    // The wheel's accessible readout is the non-visual reading of the same data.
    await expect(wheel).toHaveAttribute('aria-label', /Career 9 out of 10/);

    // 7 — log a session for the new coachee.
    await go(page, 'Sessions');
    await page.getByRole('button', { name: /log a session/i }).first().click();
    await page.getByRole('button', { name: 'Lerato Test' }).click();
    await page.getByRole('button', { name: /start session/i }).click();

    // 8 — the framework stepper shows GROW and flags the steps she skips.
    await expect(page.getByRole('heading', { name: 'Options' })).toBeVisible();
    await expect(page.getByText('often skipped').first()).toBeVisible();
    await expect(page.getByText('What are the pros and cons of each option?')).toBeVisible();

    // 9 — grade an element; adherence appears.
    await page.getByRole('button', { name: 'Strong' }).first().click();
    await expect(page.getByText('100%')).toBeVisible();

    // 10 — the closing script appears only once both scores reach 8.
    await expect(page.getByText(/cement the agreement/i)).toBeHidden();
    await page.getByRole('slider', { name: 'Confidence' }).fill('9');
    await page.getByRole('slider', { name: 'Commitment' }).fill('9');
    await expect(page.getByText(/cement the agreement out loud/i)).toBeVisible();

    // 11 — the reminders checklist grades itself and reports honestly.
    await expect(page.getByText(/Review date set before closing/)).toBeVisible();
    await expect(page.getByText(/to close out/)).toBeVisible();

    // Adding an action with a review date closes out the Will step and the
    // review date at once. Before: both are failing.
    await expect(page.getByText(/the Will step did not land/)).toBeVisible();

    await page.getByLabel('What will they do?').fill('Swim on Tuesday and Thursday');
    await page.getByRole('button', { name: /^Add$/ }).last().click();

    // It lands in two places by design — the action list, and the prep card's
    // "still open" summary — so this is scoped rather than loosened.
    await expect(
      page.getByRole('listitem').filter({ hasText: 'Swim on Tuesday and Thursday' }).first(),
    ).toBeVisible();

    // After: the checklist has re-graded itself from the data, with no save step.
    await expect(page.getByText(/the Will step did not land/)).toBeHidden();
    await expect(page.getByText(/1 action committed/)).toBeVisible();
    await expect(page.getByText(/Every action carries its own review date/)).toBeVisible();

    // 12 — content studio: pillars, coherence, pipeline.
    await go(page, 'Content');
    await expect(page.getByRole('heading', { name: 'Coherence map' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Pipeline' })).toBeVisible();

    // The pillar appears in the matrix, on its own card, and as a chip on each
    // post serving it — so the matrix row is what gets asserted.
    const matrix = page.getByRole('table');
    await expect(
      matrix.getByRole('rowheader', { name: /Start before you are ready/ }),
    ).toBeVisible();

    // Counts per window are printed, not merely shaded — a pale cell is
    // ambiguous where a numeral is not.
    const momentumRow = matrix.getByRole('row').filter({ hasText: 'Start before you are ready' });
    await expect(momentumRow.getByRole('cell').first()).toHaveText(/^\d+$/);

    /**
     * One seeded post deliberately carries no pillar, so its card is flagged.
     * The coherence map's "serves no pillar" warning is a *different* signal and
     * correctly stays silent here: that post is still an idea, and the map counts
     * published work only.
     */
    await expect(page.getByText('No pillar').first()).toBeVisible();
    await expect(page.getByText(/serves? no pillar/)).toHaveCount(0);
  });

  test('export, wipe and restore round-trips the practice — gate G2', async ({ page }) => {
    await open(page);
    await page.getByRole('button', { name: /load the sample practice/i }).click();
    await expect(page.getByText(/Sample practice loaded/i)).toBeVisible();

    // Read the export straight out of the store rather than through a download,
    // so the assertion is about the data and not about browser plumbing.
    const before = await page.evaluate(() => {
      const store = (window as unknown as { __cmw?: { exportBackup(): string } }).__cmw;
      return store?.exportBackup() ?? '';
    });
    expect(before.length).toBeGreaterThan(1000);

    await go(page, 'Vault & settings');
    await expect(page.getByRole('heading', { name: 'Your data' })).toBeVisible();

    // Clear everything, confirming through the modal.
    await page.getByRole('button', { name: /clear all data/i }).click();
    await page.getByRole('button', { name: /yes, clear it/i }).click();
    await expect(page.getByText('Everything cleared.')).toBeVisible();

    const emptied = await page.evaluate(() => {
      const store = (window as unknown as { __cmw?: { exportBackup(): string } }).__cmw;
      return store?.exportBackup() ?? '';
    });
    expect(JSON.parse(emptied).counts.coachees).toBe(0);

    // Restore, then re-export and compare. The export is deterministic, so the
    // only difference between the two files is their timestamp.
    const restored = await page.evaluate(async (backup: string) => {
      const store = (
        window as unknown as { __cmw?: { importBackup(json: string): Promise<void>; exportBackup(): string } }
      ).__cmw;
      await store?.importBackup(backup);
      return store?.exportBackup() ?? '';
    }, before);

    const strip = (json: string): unknown => {
      const parsed = JSON.parse(json) as Record<string, unknown>;
      delete parsed.exported_at;
      return parsed;
    };
    expect(strip(restored)).toEqual(strip(before));
  });

  test('survives a reload — data is genuinely persisted', async ({ page }) => {
    await open(page);
    await page.getByRole('button', { name: /load the sample practice/i }).click();
    await expect(page.getByText(/Sample practice loaded/i)).toBeVisible();

    await page.reload();

    // IndexedDB over file:// is the whole storage story for Build 1, so this is
    // the assertion that matters most.
    await expect(page.getByRole('heading', { name: /^Good (morning|afternoon|evening)$/ })).toBeVisible();
    await go(page, 'Clients');
    await expect(page.getByText('Naledi M.')).toBeVisible();
  });

  test('both themes render and reduced motion is respected', async ({ page }) => {
    await open(page);
    await page.getByRole('button', { name: /load the sample practice/i }).click();

    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dawn');
    await page.getByRole('button', { name: /switch to morning theme/i }).click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'morning');

    // The theme choice is a setting, so it has to outlive a reload.
    await page.reload();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'morning');
  });

  test('reduced motion removes the wheel breathing entirely', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await open(page);
    await page.getByRole('button', { name: /load the sample practice/i }).click();
    await go(page, 'Clients');
    await page.getByText('Naledi M.').click();
    await page.getByRole('tab', { name: 'Wheel' }).click();

    await expect(page.locator('svg[role="img"]').first()).toBeVisible();

    /**
     * §4.4 makes this non-negotiable. The wheel does not merely rely on the
     * stylesheet's kill-switch flattening its duration — it does not apply the
     * animation class at all, so there is nothing running to be overridden. That
     * is the stronger guarantee, so it is the one asserted.
     */
    await expect(page.locator('.cmw-wheel-breathe')).toHaveCount(0);
  });

  test('the wheel does breathe when motion is welcome', async ({ page }) => {
    // The counterpart to the test above: proving the animation exists at all is
    // what stops "reduced motion passes" from being vacuously true.
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await open(page);
    await page.getByRole('button', { name: /load the sample practice/i }).click();
    await go(page, 'Clients');
    await page.getByText('Naledi M.').click();
    await page.getByRole('tab', { name: 'Wheel' }).click();

    const breathing = page.locator('.cmw-wheel-breathe').first();
    await expect(breathing).toBeAttached();
    const duration = await breathing.evaluate(
      (node) => getComputedStyle(node).animationDuration,
    );
    expect(duration).toBe('4s');
  });
});
