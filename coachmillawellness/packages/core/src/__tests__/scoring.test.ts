import { beforeEach, describe, expect, it } from 'vitest';

import { CEMENT_THRESHOLD, RATING_POINTS } from '../frameworks.js';
import { closingCheck, coachGrowthCurve, scoreSession } from '../scoring.js';
import { NALEDI, THABO, resetIds, score, session } from './factories.js';

beforeEach(resetIds);

describe('scoreSession', () => {
  it('grades every element of the framework, scored or not', () => {
    const card = scoreSession({ session: session(), scores: [score({ element: 'goal' })] });

    expect(card.lines.map((l) => l.element)).toEqual(['goal', 'reality', 'options', 'will']);
    expect(card.lines.map((l) => l.letter)).toEqual(['G', 'R', 'O', 'W']);
    expect(card.unscored).toEqual(['reality', 'options', 'will']);
    expect(card.complete).toBe(false);
  });

  it('uses the GREAT elements when the session used GREAT', () => {
    const card = scoreSession({ session: session({ framework: 'GREAT' }), scores: [] });
    expect(card.lines.map((l) => l.element)).toEqual([
      'goals',
      'reality_rapport',
      'explore',
      'achieve',
      'take_action',
    ]);
    expect(card.lines.map((l) => l.letter)).toEqual(['G', 'R', 'E', 'A', 'T']);
  });

  it('averages adherence across graded elements only', () => {
    // Strong 1.0 + Weak 0.25 → 62.5% → 63 rounded. `will` is ungraded and must
    // not be counted as a zero, which would punish an in-progress scorecard.
    const card = scoreSession({
      session: session(),
      scores: [
        score({ element: 'goal', rating: 'Strong' }),
        score({ element: 'reality', rating: 'Weak' }),
      ],
    });

    expect(card.counted_elements).toBe(2);
    expect(card.adherence_pct).toBe(63);
  });

  it('excludes N/A from the denominator instead of scoring it', () => {
    const card = scoreSession({
      session: session(),
      scores: [
        score({ element: 'goal', rating: 'Strong' }),
        score({ element: 'reality', rating: 'N/A' }),
      ],
    });

    expect(card.counted_elements).toBe(1);
    expect(card.adherence_pct).toBe(100);
    expect(card.lines.find((l) => l.element === 'reality')?.counted).toBe(false);
    expect(card.lines.find((l) => l.element === 'reality')?.points).toBeNull();
    expect(card.rating_counts['N/A']).toBe(1);
  });

  it('reports no adherence figure when nothing is graded', () => {
    const card = scoreSession({ session: session(), scores: [] });
    expect(card.adherence_pct).toBeNull();
    expect(card.counted_elements).toBe(0);
    expect(card.strongest).toEqual([]);
    expect(card.weakest).toEqual([]);
  });

  it('ranks Met just below Strong so the growth curve can see the difference', () => {
    expect(RATING_POINTS.Met).toBeLessThan(RATING_POINTS.Strong);
    expect(RATING_POINTS.Met).toBeGreaterThan(RATING_POINTS.Adequate);

    const card = scoreSession({
      session: session(),
      scores: [
        score({ element: 'goal', rating: 'Strong' }),
        score({ element: 'will', rating: 'Met' }),
      ],
    });
    expect(card.strongest).toEqual(['goal']);
    expect(card.weakest).toEqual(['will']);
  });

  it('names no strongest or weakest when every graded element ties', () => {
    const card = scoreSession({
      session: session(),
      scores: [
        score({ element: 'goal', rating: 'Adequate' }),
        score({ element: 'reality', rating: 'Adequate' }),
      ],
    });
    expect(card.strongest).toEqual([]);
    expect(card.weakest).toEqual([]);
  });

  it('lists every element sharing the top and bottom score', () => {
    const card = scoreSession({
      session: session(),
      scores: [
        score({ element: 'goal', rating: 'Strong' }),
        score({ element: 'reality', rating: 'Strong' }),
        score({ element: 'options', rating: 'Weak' }),
        score({ element: 'will', rating: 'Weak' }),
      ],
    });
    expect(card.strongest).toEqual(['goal', 'reality']);
    expect(card.weakest).toEqual(['options', 'will']);
    expect(card.complete).toBe(true);
  });

  it('keeps the latest edit when an element is re-rated', () => {
    const early = score({
      element: 'goal',
      rating: 'Weak',
      updated_at: '2026-07-15T09:00:00.000Z',
    });
    const late = score({
      element: 'goal',
      rating: 'Strong',
      updated_at: '2026-07-15T11:00:00.000Z',
      notes: 'Reheard the recording',
    });

    // Both orderings must resolve to the same winner.
    for (const scores of [[early, late], [late, early]]) {
      const card = scoreSession({ session: session(), scores });
      const line = card.lines.find((l) => l.element === 'goal');
      expect(line?.rating).toBe('Strong');
      expect(line?.notes).toBe('Reheard the recording');
    }
  });

  it('ignores rows from other sessions, deleted rows and foreign elements', () => {
    const card = scoreSession({
      session: session(),
      scores: [
        score({ element: 'goal', session_id: 'session-other', rating: 'Weak' }),
        score({ element: 'reality', rating: 'Weak', deleted_at: '2026-07-16T00:00:00.000Z' }),
        // `achieve` belongs to GREAT — it must not leak into a GROW scorecard.
        score({ element: 'achieve', rating: 'Strong' }),
      ],
    });

    expect(card.counted_elements).toBe(0);
    expect(card.unscored).toHaveLength(4);
  });

  it('grades each participant of a joint session separately', () => {
    const joint = session({ participants: [NALEDI, THABO] });
    const scores = [
      score({ element: 'goal', coachee_id: NALEDI, rating: 'Strong' }),
      score({ element: 'goal', coachee_id: THABO, rating: 'Weak' }),
    ];

    const naledi = scoreSession({ session: joint, scores, coachee_id: NALEDI });
    const thabo = scoreSession({ session: joint, scores, coachee_id: THABO });

    expect(naledi.adherence_pct).toBe(100);
    expect(thabo.adherence_pct).toBe(25);
    expect(naledi.coachee_id).toBe(NALEDI);
  });

  it('pools every participant when no coachee is named', () => {
    const card = scoreSession({
      session: session({ participants: [NALEDI, THABO] }),
      scores: [
        score({ element: 'goal', coachee_id: NALEDI, rating: 'Strong' }),
        score({ element: 'reality', coachee_id: THABO, rating: 'Strong' }),
      ],
    });
    expect(card.coachee_id).toBeNull();
    expect(card.counted_elements).toBe(2);
  });

  it('carries evidence and the historically-skipped flag through to the UI', () => {
    const card = scoreSession({
      session: session(),
      scores: [score({ element: 'goal', evidence: '"What does success look like?" — 04:12' })],
    });

    const goalLine = card.lines.find((l) => l.element === 'goal');
    expect(goalLine?.evidence).toContain('success look like');
    expect(goalLine?.historically_skipped).toBe(true);
    // Reality is the one GROW element she is not recorded as skipping.
    expect(card.lines.find((l) => l.element === 'reality')?.historically_skipped).toBe(false);
    expect(card.lines.find((l) => l.element === 'reality')?.evidence).toBeNull();
  });
});

describe('closingCheck', () => {
  it('expects the closing script when both scores reach the threshold', () => {
    const check = closingCheck(session({ confidence: 8, commitment: 9 }));
    expect(check.cement_expected).toBe(true);
    expect(check.threshold).toBe(CEMENT_THRESHOLD);
  });

  it('does not expect the script when either score falls short', () => {
    expect(closingCheck(session({ confidence: 8, commitment: 7 })).cement_expected).toBe(false);
    expect(closingCheck(session({ confidence: 7, commitment: 8 })).cement_expected).toBe(false);
  });

  it('does not expect the script when a score is missing', () => {
    expect(closingCheck(session({ confidence: 9 })).cement_expected).toBe(false);
    expect(closingCheck(session({ commitment: 9 })).cement_expected).toBe(false);
    const blank = closingCheck(session());
    expect(blank.confidence).toBeNull();
    expect(blank.commitment).toBeNull();
    expect(blank.cement_expected).toBe(false);
  });

  it('reports whether a review date was set', () => {
    expect(closingCheck(session()).review_date_set).toBe(false);
    expect(closingCheck(session({ review_dates: ['2026-07-22'] })).review_date_set).toBe(true);
  });
});

describe('coachGrowthCurve', () => {
  it('charts her adherence per element per month', () => {
    const june = session({ id: 's-june', date: '2026-06-10' });
    const july = session({ id: 's-july', date: '2026-07-10' });
    const curve = coachGrowthCurve(
      [june, july],
      [
        score({ session_id: 's-june', element: 'options', rating: 'Weak' }),
        score({ session_id: 's-july', element: 'options', rating: 'Strong' }),
      ],
      'GROW',
    );

    const options = curve.points.filter((p) => p.element === 'options');
    expect(options).toEqual([
      { month: '2026-06', element: 'options', label: 'Options', adherence_pct: 25, sessions: 1 },
      { month: '2026-07', element: 'options', label: 'Options', adherence_pct: 100, sessions: 1 },
    ]);
  });

  it('weights the overall average by how many sessions each month held', () => {
    const curve = coachGrowthCurve(
      [
        session({ id: 's1', date: '2026-06-01' }),
        session({ id: 's2', date: '2026-06-08' }),
        session({ id: 's3', date: '2026-07-01' }),
      ],
      [
        score({ session_id: 's1', element: 'goal', rating: 'Strong' }),
        score({ session_id: 's2', element: 'goal', rating: 'Strong' }),
        score({ session_id: 's3', element: 'goal', rating: 'Weak' }),
      ],
      'GROW',
    );

    const goal = curve.averages.find((a) => a.element === 'goal');
    expect(goal?.sessions).toBe(3);
    // (100 + 100 + 25) / 3 = 75 — not the unweighted mean of the two months.
    expect(goal?.adherence_pct).toBe(75);
  });

  it('identifies her weakest element across the window', () => {
    const curve = coachGrowthCurve(
      [session({ id: 's1', date: '2026-07-01' })],
      [
        score({ session_id: 's1', element: 'goal', rating: 'Strong' }),
        score({ session_id: 's1', element: 'options', rating: 'Weak' }),
      ],
      'GROW',
    );
    expect(curve.weakest_element).toBe('options');
    // Ungraded elements report zero sessions rather than a misleading zero score.
    expect(curve.averages.find((a) => a.element === 'will')).toEqual({
      element: 'will',
      label: 'Will',
      adherence_pct: 0,
      sessions: 0,
    });
  });

  it('has no weakest element before anything is graded', () => {
    const curve = coachGrowthCurve([session()], [], 'GROW');
    expect(curve.weakest_element).toBeNull();
    expect(curve.points).toEqual([]);
  });

  it('counts a joint session once per participant', () => {
    const curve = coachGrowthCurve(
      [session({ id: 's1', date: '2026-07-01', participants: [NALEDI, THABO] })],
      [
        score({ session_id: 's1', coachee_id: NALEDI, element: 'goal', rating: 'Strong' }),
        score({ session_id: 's1', coachee_id: THABO, element: 'goal', rating: 'Weak' }),
      ],
      'GROW',
    );
    const goal = curve.averages.find((a) => a.element === 'goal');
    expect(goal?.sessions).toBe(2);
    expect(goal?.adherence_pct).toBe(63);
  });

  it('handles a session with no participants recorded', () => {
    const curve = coachGrowthCurve(
      [session({ id: 's1', date: '2026-07-01', participants: [] })],
      [score({ session_id: 's1', element: 'goal', rating: 'Strong' })],
      'GROW',
    );
    expect(curve.averages.find((a) => a.element === 'goal')?.sessions).toBe(1);
  });

  it('ignores sessions from the other framework and deleted sessions', () => {
    const curve = coachGrowthCurve(
      [
        session({ id: 's1', date: '2026-07-01', framework: 'GREAT' }),
        session({ id: 's2', date: '2026-07-02', deleted_at: '2026-07-03T00:00:00.000Z' }),
      ],
      [
        score({ session_id: 's1', element: 'goals', rating: 'Strong' }),
        score({ session_id: 's2', element: 'goal', rating: 'Strong' }),
      ],
      'GROW',
    );
    expect(curve.points).toEqual([]);
  });

  it('sorts points by month then element so charts draw left to right', () => {
    const curve = coachGrowthCurve(
      [session({ id: 's1', date: '2026-07-01' })],
      [
        score({ session_id: 's1', element: 'will', rating: 'Strong' }),
        score({ session_id: 's1', element: 'goal', rating: 'Strong' }),
      ],
      'GROW',
    );
    expect(curve.points.map((p) => p.element)).toEqual(['goal', 'will']);
  });
});
