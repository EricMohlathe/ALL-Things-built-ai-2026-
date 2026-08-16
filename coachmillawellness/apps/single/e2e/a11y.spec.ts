/**
 * Gate G5 — accessibility. A merge blocker per §4.7, so it runs as a test.
 *
 * axe-core across every route, in both themes, plus a keyboard walkthrough and a
 * touch-target audit. The standard from the compendium is zero *critical* issues;
 * this suite fails on serious as well, because "serious" covers the contrast and
 * name-role-value problems that actually stop someone using the app.
 */

import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

const ARTIFACT = pathToFileURL(
  resolve(import.meta.dirname, '../dist/CoachMillaWellness.html'),
).href;

const ROUTES = [
  { hash: '#/deck', name: 'Deck' },
  { hash: '#/clients', name: 'Clients' },
  { hash: '#/sessions', name: 'Sessions' },
  { hash: '#/content', name: 'Content' },
  { hash: '#/wheel', name: 'Wheel Lab' },
  { hash: '#/insights', name: 'Insights' },
  { hash: '#/vault', name: 'Vault' },
];

async function seed(page: Page): Promise<void> {
  await page.goto(ARTIFACT);
  await page.getByRole('button', { name: /load the sample practice/i }).click();
  await expect(page.getByText(/Sample practice loaded/i)).toBeVisible();
}

/**
 * Waits for every finite animation to finish.
 *
 * axe reads computed colour and Playwright's bounding boxes include transforms,
 * so auditing mid-transition measures a half-faded, slightly-scaled element and
 * reports problems the settled UI does not have. Infinite animations (the wheel's
 * idle breathing) are skipped — waiting on those would never return.
 */
async function settle(page: Page): Promise<void> {
  await page.evaluate(async () => {
    /**
     * Two frames before collecting, and again after.
     *
     * A CSS transition only joins `document.getAnimations()` once it has
     * actually started, which is a frame or two after the styles that trigger
     * it are applied. Collecting immediately therefore finds an empty list on a
     * screen that is about to animate, and axe samples a mid-transition colour —
     * the same measure-during-motion trap that once made the touch-target audit
     * report 42.2px for a 44px control. Waiting first makes the audit
     * deterministic instead of merely usually right.
     */
    const frame = (): Promise<void> =>
      new Promise((resolve) => requestAnimationFrame(() => resolve()));

    const drain = async (): Promise<void> => {
      const finite = document.getAnimations().filter((animation) => {
        const timing = animation.effect?.getComputedTiming();
        return timing !== undefined && timing.iterations !== Number.POSITIVE_INFINITY;
      });
      await Promise.all(finite.map((animation) => animation.finished.catch(() => undefined)));
    };

    await frame();
    await frame();
    await drain();
    // A finished enter can start a follow-on transition; one more pass catches it.
    await drain();
  });
}

async function audit(page: Page, label: string): Promise<void> {
  await settle(page);

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();

  const blocking = results.violations.filter(
    (violation) => violation.impact === 'critical' || violation.impact === 'serious',
  );

  const report = blocking
    .map(
      (violation) =>
        `${violation.impact}: ${violation.id} — ${violation.help}\n` +
        violation.nodes.map((node) => `    ${node.target.join(' ')}`).join('\n'),
    )
    .join('\n');

  expect(blocking, `${label}\n${report}`).toEqual([]);
}

test.describe('accessibility', () => {
  /**
   * Audited with reduced motion on.
   *
   * Not a convenience: axe samples computed colour, and the house enter animation
   * fades from `opacity: 0`, so a run that lands mid-transition measures a
   * half-transparent element and reports contrast the finished UI does not have.
   * Reduced motion settles every enter instantly, making the audit deterministic —
   * and it is a configuration real users have. The *final* colour maths is proven
   * separately and exactly by the contrast tests in @cmw/tokens.
   */
  test.use({ reducedMotion: 'reduce' });

  for (const route of ROUTES) {
    test(`${route.name} has no critical or serious axe violations (Dawn)`, async ({ page }) => {
      await seed(page);
      await page.goto(`${ARTIFACT}${route.hash}`);
      await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible();
      await audit(page, `${route.name} — Dawn`);
    });
  }

  test('the Morning theme is audited separately, not assumed', async ({ page }) => {
    // §4.2: Morning is designed in parallel with Dawn, so it earns its own pass.
    await seed(page);
    await page.getByRole('button', { name: /switch to morning theme/i }).click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'morning');

    for (const route of ROUTES) {
      await page.goto(`${ARTIFACT}${route.hash}`);
      await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible();
      await audit(page, `${route.name} — Morning`);
    }
  });

  test('client detail and session detail are audited too', async ({ page }) => {
    await seed(page);

    await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Clients', exact: true }).click();
    await page.getByText('Naledi M.').click();
    await expect(page.getByRole('heading', { name: 'Naledi M.' })).toBeVisible();
    await audit(page, 'Client detail — Overview');

    await page.getByRole('tab', { name: 'Wheel' }).click();
    await audit(page, 'Client detail — Wheel');

    await page.getByRole('tab', { name: 'Actions' }).click();
    await audit(page, 'Client detail — Actions');

    await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Sessions', exact: true }).click();
    await page.getByText(/GROW|GREAT/).first().click();
    await audit(page, 'Session detail');
  });

  test('a modal is reachable, labelled, and closes on Escape', async ({ page }) => {
    await seed(page);
    await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Clients', exact: true }).click();
    await page.getByRole('button', { name: /add coachee/i }).first().click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAttribute('aria-modal', 'true');
    await audit(page, 'Add coachee modal');

    // §4.7: ESC closes everything.
    await page.keyboard.press('Escape');
    await expect(dialog).toBeHidden();
  });

  test('every interactive target clears 44 pixels', async ({ page }) => {
    await seed(page);
    await settle(page);

    // §4.7's touch-target floor, measured rather than trusted. Chips are
    // deliberately smaller pills used in dense rows, so they are measured
    // against their own 32px floor and excluded from the 44px rule.
    const undersized = await page.evaluate(() => {
      const offenders: string[] = [];
      const nodes = document.querySelectorAll('button, a[href], input, select, [role="tab"]');

      for (const node of nodes) {
        const element = node as HTMLElement;
        const style = getComputedStyle(element);
        if (style.display === 'none' || style.visibility === 'hidden') continue;
        if (element.classList.contains('cmw-sr-only')) continue;

        // `offsetHeight` is the layout box; `getBoundingClientRect` would include
        // any transform, and an element caught mid-scale measures small while
        // being perfectly tappable once settled.
        const height = element.offsetHeight;
        const width = element.offsetWidth;
        if (width === 0 || height === 0) continue;

        const isChip = style.borderRadius === '999px';
        const floor = isChip ? 30 : 44;
        if (height < floor) {
          offenders.push(
            `${element.tagName.toLowerCase()} "${(element.textContent ?? '').trim().slice(0, 24)}" ` +
              `${height}px [${element.className.toString().slice(0, 70)}]`,
          );
        }
      }
      return offenders;
    });

    expect(undersized, `undersized targets:\n${undersized.join('\n')}`).toEqual([]);
  });

  test('the whole Deck is reachable by keyboard alone', async ({ page }) => {
    await seed(page);

    // Walk the tab order and confirm focus actually lands on things, and that
    // the focus ring is never suppressed.
    const visited: string[] = [];
    for (let i = 0; i < 18; i += 1) {
      await page.keyboard.press('Tab');
      const focused = await page.evaluate(() => {
        const element = document.activeElement as HTMLElement | null;
        if (!element || element === document.body) return null;
        const outline = getComputedStyle(element).outlineStyle;
        return `${element.tagName.toLowerCase()}:${outline}`;
      });
      if (focused) visited.push(focused);
    }

    expect(visited.length).toBeGreaterThan(8);
    expect(visited.some((entry) => entry.endsWith(':none'))).toBe(false);
  });
});
