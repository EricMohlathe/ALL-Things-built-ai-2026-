import { beforeEach, describe, expect, it } from 'vitest';

import { buildDeck, greetingFor } from '../deck.js';
import {
  NALEDI,
  THABO,
  action,
  coachee,
  content,
  resetIds,
  session,
} from './factories.js';

beforeEach(resetIds);

const NOW = '2026-07-30';

const naledi = coachee({ id: NALEDI, name: 'Naledi M.' });
const thabo = coachee({ id: THABO, name: 'Thabo K.' });

function deck(overrides: Parameters<typeof buildDeck>[0] extends never ? never : Partial<Parameters<typeof buildDeck>[0]> = {}) {
  return buildDeck({
    coachees: [naledi, thabo],
    sessions: [],
    actions: [],
    content: [],
    now: NOW,
    hour: 9,
    ...overrides,
  });
}

describe('greetingFor', () => {
  it('keys off the time of day', () => {
    expect(greetingFor(0)).toBe('morning');
    expect(greetingFor(11)).toBe('morning');
    expect(greetingFor(12)).toBe('afternoon');
    expect(greetingFor(16)).toBe('afternoon');
    expect(greetingFor(17)).toBe('evening');
    expect(greetingFor(23)).toBe('evening');
  });
});

describe('buildDeck', () => {
  it("answers 'what does today need from me' with today's sessions first", () => {
    const summary = deck({
      sessions: [
        session({ id: 's-today', date: NOW }),
        session({ id: 's-later', date: '2026-08-04' }),
        session({ id: 's-past', date: '2026-07-01' }),
      ],
    });

    expect(summary.today_sessions.map((s) => s.id)).toEqual(['s-today']);
    expect(summary.next_session?.id).toBe('s-later');
    expect(summary.focus).toContain('GROW with Naledi today');
    expect(summary.focus).toContain('prep card');
    expect(summary.all_clear).toBe(false);
  });

  it('names both people in a joint session and counts the rest of the day', () => {
    const summary = deck({
      sessions: [
        session({ id: 's1', date: NOW, participants: [NALEDI, THABO] }),
        session({ id: 's2', date: NOW }),
      ],
    });
    expect(summary.focus).toContain('Naledi and Thabo');
    expect(summary.focus).toContain('then 1 more session');
  });

  it('pluralises the remaining sessions', () => {
    const summary = deck({
      sessions: [
        session({ id: 's1', date: NOW }),
        session({ id: 's2', date: NOW }),
        session({ id: 's3', date: NOW }),
      ],
    });
    expect(summary.focus).toContain('then 2 more sessions');
  });

  it('falls back to a generic name when a participant is unknown', () => {
    const summary = deck({
      coachees: [],
      sessions: [session({ id: 's1', date: NOW })],
    });
    expect(summary.focus).toContain('your coachee');
  });

  it('separates slipped reviews from those due today and soon', () => {
    const summary = deck({
      actions: [
        action({ review_date: '2026-07-20' }),
        action({ review_date: NOW }),
        action({ review_date: '2026-08-02' }),
        action({ review_date: '2026-09-30' }),
      ],
    });

    expect(summary.overdue_reviews).toHaveLength(1);
    expect(summary.reviews_due_today).toHaveLength(1);
    // "Soon" excludes today so the two widgets never double-count an action.
    expect(summary.reviews_due_soon.map((a) => a.review_date)).toEqual(['2026-08-02']);
  });

  it('promotes an at-risk coachee above general admin', () => {
    const summary = deck({
      actions: [action({ coachee_id: NALEDI, review_date: '2026-07-10' })],
    });

    expect(summary.at_risk).toHaveLength(1);
    expect(summary.at_risk[0]!.level).toBe('at_risk');
    expect(summary.focus).toBe('Naledi needs a nudge — review slipped 20 days ago.');
  });

  it('sorts at-risk coachees by how far they have slipped', () => {
    const summary = deck({
      actions: [
        action({ coachee_id: NALEDI, review_date: '2026-07-28' }),
        action({ coachee_id: THABO, review_date: '2026-07-05' }),
      ],
    });
    expect(summary.at_risk.map((r) => r.coachee_id)).toEqual([THABO, NALEDI]);
  });

  it('only flags active coachees', () => {
    const summary = deck({
      coachees: [coachee({ id: NALEDI, status: 'alumni' })],
      actions: [action({ coachee_id: NALEDI, review_date: '2026-07-01' })],
    });
    expect(summary.at_risk).toEqual([]);
    // The review is still overdue — it just is not a retention risk any more.
    expect(summary.overdue_reviews).toHaveLength(1);
    expect(summary.focus).toContain('1 review slipped');
  });

  it('pluralises slipped reviews', () => {
    const summary = deck({
      coachees: [],
      actions: [action({ review_date: '2026-07-01' }), action({ review_date: '2026-07-02' })],
    });
    expect(summary.focus).toContain('2 reviews slipped');
  });

  it("falls through to today's reviews when nothing has slipped", () => {
    const summary = deck({ actions: [action({ review_date: NOW })] });
    expect(summary.focus).toBe('1 action is up for review today — a quick pass keeps the rhythm.');
  });

  it('pluralises reviews due today', () => {
    const summary = deck({
      actions: [action({ review_date: NOW }), action({ review_date: NOW })],
    });
    expect(summary.focus).toContain('2 actions are up for review today');
  });

  it('surfaces content scheduled for today that has not shipped', () => {
    const summary = deck({
      content: [
        content({ title: 'The 20-minute rule', status: 'script', publish_date: NOW }),
        content({ title: 'Already out', status: 'posted', publish_date: NOW }),
        content({ title: 'Analysed', status: 'analyzed', publish_date: NOW }),
        content({ title: 'Tomorrow', status: 'idea', publish_date: '2026-07-31' }),
      ],
    });

    expect(summary.content_due_today.map((c) => c.title)).toEqual(['The 20-minute rule']);
    expect(summary.focus).toBe('"The 20-minute rule" is scheduled for today and still sitting at script.');
  });

  it('reports a genuinely clear day rather than inventing work', () => {
    const summary = deck();
    expect(summary.all_clear).toBe(true);
    expect(summary.focus).toContain('Use the space to get ahead on content');
    expect(summary.greeting).toBe('morning');
    expect(summary.date).toBe(NOW);
  });

  it('carries the streaks', () => {
    const summary = deck({
      sessions: [session({ date: '2026-07-28' })],
      content: [content({ publish_date: NOW }), content({ publish_date: '2026-07-29' })],
    });
    expect(summary.session_streak_weeks).toBe(1);
    expect(summary.publish_streak_days).toBe(2);
  });

  it('ignores deleted sessions and content', () => {
    const summary = deck({
      sessions: [session({ date: NOW, deleted_at: '2026-07-31T00:00:00.000Z' })],
      content: [
        content({ status: 'idea', publish_date: NOW, deleted_at: '2026-07-31T00:00:00.000Z' }),
      ],
    });
    expect(summary.today_sessions).toEqual([]);
    expect(summary.content_due_today).toEqual([]);
    expect(summary.all_clear).toBe(true);
  });

  it('defaults its clock and hour to now', () => {
    const summary = buildDeck({ coachees: [], sessions: [], actions: [], content: [] });
    expect(summary.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(['morning', 'afternoon', 'evening']).toContain(summary.greeting);
  });
});
