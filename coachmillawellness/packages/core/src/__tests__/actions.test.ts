import { beforeEach, describe, expect, it } from 'vitest';

import {
  actionCompletionRate,
  coacheeRisk,
  missingReviewDate,
  overdueDue,
  overdueReviews,
  reviewsDueToday,
  reviewsDueWithin,
  sessionStreakWeeks,
  weekKey,
} from '../actions.js';
import { NALEDI, THABO, action, resetIds, session } from './factories.js';

beforeEach(resetIds);

const NOW = '2026-07-30';

describe('overdueReviews', () => {
  it('finds outstanding actions whose review date has passed, oldest first', () => {
    const overdue = overdueReviews(
      [
        action({ review_date: '2026-07-20' }),
        action({ review_date: '2026-07-10' }),
        action({ review_date: '2026-08-05' }),
      ],
      NOW,
    );
    expect(overdue.map((a) => a.review_date)).toEqual(['2026-07-10', '2026-07-20']);
  });

  it('ignores completed, deleted and unreviewed actions', () => {
    const overdue = overdueReviews(
      [
        action({ review_date: '2026-07-10', status: 'done' }),
        action({ review_date: '2026-07-10', deleted_at: '2026-07-11T00:00:00.000Z' }),
        action({ review_date: null }),
        action({}),
      ],
      NOW,
    );
    expect(overdue).toEqual([]);
  });

  it("does not treat today's review as slipped", () => {
    expect(overdueReviews([action({ review_date: NOW })], NOW)).toEqual([]);
  });

  it('defaults its clock to today', () => {
    expect(overdueReviews([action({ review_date: '2000-01-01' })])).toHaveLength(1);
  });
});

describe('review windows', () => {
  const actions = [
    action({ review_date: NOW }),
    action({ review_date: '2026-08-02' }),
    action({ review_date: '2026-08-20' }),
    action({ review_date: '2026-07-01' }),
  ];

  it('finds what is up for review today', () => {
    expect(reviewsDueToday(actions, NOW)).toHaveLength(1);
  });

  it('finds what is coming inside a horizon, soonest first', () => {
    const soon = reviewsDueWithin(actions, 7, NOW);
    expect(soon.map((a) => a.review_date)).toEqual([NOW, '2026-08-02']);
  });

  it('defaults its clock to today', () => {
    // Dated far enough out that the assertion holds whenever the suite runs —
    // a fixture near the real today would make this test rot by tomorrow.
    const far = [action({ review_date: '2099-01-01' })];
    expect(reviewsDueWithin(far, 7)).toEqual([]);
    expect(reviewsDueToday(far)).toEqual([]);
  });

  it('finds overdue due-dates separately from overdue reviews', () => {
    const late = overdueDue(
      [
        action({ due_date: '2026-07-01' }),
        action({ due_date: '2026-06-01' }),
        action({ due_date: '2026-08-30' }),
        action({ due_date: null }),
      ],
      NOW,
    );
    expect(late.map((a) => a.due_date)).toEqual(['2026-06-01', '2026-07-01']);
    expect(overdueDue([action({ due_date: '2000-01-01' })])).toHaveLength(1);
  });

  it('finds actions carrying no review date at all', () => {
    const missing = missingReviewDate([
      action({ review_date: '2026-08-01' }),
      action({ review_date: null }),
      action({ status: 'done' }),
    ]);
    expect(missing).toHaveLength(1);
  });
});

describe('actionCompletionRate', () => {
  it('counts each status and the completion rate', () => {
    const stats = actionCompletionRate([
      action({ status: 'done' }),
      action({ status: 'done' }),
      action({ status: 'open' }),
      action({ status: 'in_review' }),
      action({ status: 'open', deleted_at: '2026-07-01T00:00:00.000Z' }),
    ]);

    expect(stats).toEqual({ total: 4, done: 2, open: 1, in_review: 1, rate: 0.5 });
  });

  it('has no rate to report with no actions', () => {
    expect(actionCompletionRate([]).rate).toBeNull();
  });
});

describe('coacheeRisk', () => {
  it('is clear when nothing has slipped', () => {
    const risk = coacheeRisk(NALEDI, [action({ review_date: '2026-08-05' })], NOW);
    expect(risk.level).toBe('none');
    expect(risk.reason).toBeNull();
    expect(risk.days_slipped).toBe(0);
  });

  it('treats a couple of days late as something to watch, not a crisis', () => {
    const risk = coacheeRisk(NALEDI, [action({ review_date: '2026-07-28' })], NOW);
    expect(risk.level).toBe('watch');
    expect(risk.reason).toBe('Review slipped 2 days ago');
  });

  it('uses the singular for exactly one day', () => {
    const risk = coacheeRisk(NALEDI, [action({ review_date: '2026-07-29' })], NOW);
    expect(risk.reason).toBe('Review slipped 1 day ago');
  });

  it('escalates once a review is a week old', () => {
    const risk = coacheeRisk(NALEDI, [action({ review_date: '2026-07-23' })], NOW);
    expect(risk.level).toBe('at_risk');
    expect(risk.days_slipped).toBe(7);
  });

  it('escalates on volume even when nothing has slipped far', () => {
    const risk = coacheeRisk(
      NALEDI,
      [
        action({ review_date: '2026-07-29' }),
        action({ review_date: '2026-07-28' }),
        action({ review_date: '2026-07-27' }),
      ],
      NOW,
    );
    expect(risk.level).toBe('at_risk');
    expect(risk.overdue_count).toBe(3);
    expect(risk.reason).toBe('3 reviews outstanding, oldest 3 days ago');
  });

  it('stays at watch for two slipped reviews', () => {
    const risk = coacheeRisk(
      NALEDI,
      [action({ review_date: '2026-07-29' }), action({ review_date: '2026-07-28' })],
      NOW,
    );
    expect(risk.level).toBe('watch');
    expect(risk.reason).toBe('2 reviews outstanding, oldest 2 days ago');
  });

  it('only looks at that coachee', () => {
    const risk = coacheeRisk(
      NALEDI,
      [action({ coachee_id: THABO, review_date: '2026-07-01' })],
      NOW,
    );
    expect(risk.level).toBe('none');
  });

  it('defaults its clock to today', () => {
    expect(coacheeRisk(NALEDI, [action({ review_date: '2000-01-01' })]).level).toBe('at_risk');
  });
});

describe('sessionStreakWeeks', () => {
  it('counts back consecutive weeks that held a session', () => {
    // Weekly rather than daily: a coach does not run sessions every day, so a
    // daily streak would read as broken during a perfectly healthy week.
    const streak = sessionStreakWeeks(
      [
        session({ id: 's1', date: '2026-07-28' }),
        session({ id: 's2', date: '2026-07-21' }),
        session({ id: 's3', date: '2026-07-14' }),
      ],
      NOW,
    );
    expect(streak).toBe(3);
  });

  it('breaks on a missed week', () => {
    const streak = sessionStreakWeeks(
      [session({ id: 's1', date: '2026-07-28' }), session({ id: 's2', date: '2026-07-14' })],
      NOW,
    );
    expect(streak).toBe(1);
  });

  it('is zero when this week is empty', () => {
    expect(sessionStreakWeeks([session({ date: '2026-07-21' })], NOW)).toBe(0);
    expect(sessionStreakWeeks([], NOW)).toBe(0);
  });

  it('ignores deleted sessions', () => {
    expect(
      sessionStreakWeeks([session({ date: NOW, deleted_at: '2026-07-31T00:00:00.000Z' })], NOW),
    ).toBe(0);
  });

  it('defaults its clock to today', () => {
    expect(sessionStreakWeeks([session({ date: '2000-01-01' })])).toBe(0);
  });

  it('buckets a week to its Monday', () => {
    // 2026-07-30 is a Thursday; its week starts Monday 2026-07-27.
    expect(weekKey('2026-07-30')).toBe('2026-07-27');
    expect(weekKey('2026-07-27')).toBe('2026-07-27');
    // Sunday belongs to the week that began the previous Monday.
    expect(weekKey('2026-07-26')).toBe('2026-07-20');
  });
});
