import { beforeEach, describe, expect, it } from 'vitest';

import { checklistFromSession, missingSmarterFlags, smarterComplete } from '../checklist.js';
import { LOW_SCORE_THRESHOLD } from '../frameworks.js';
import type { ChecklistItem, ChecklistState } from '../types.js';
import { action, goal, resetIds, session, smarter, snapshot } from './factories.js';

beforeEach(resetIds);

function stateOf(
  result: ReturnType<typeof checklistFromSession>,
  item: ChecklistItem,
): ChecklistState {
  return result.lines.find((l) => l.item === item)!.state;
}

function detailOf(
  result: ReturnType<typeof checklistFromSession>,
  item: ChecklistItem,
): string {
  return result.lines.find((l) => l.item === item)!.detail;
}

describe('SMARTER flags', () => {
  it('reports a complete goal as complete', () => {
    expect(smarterComplete(goal())).toBe(true);
    expect(missingSmarterFlags(smarter())).toEqual([]);
  });

  it('names the missing letters', () => {
    expect(missingSmarterFlags(smarter({ E: false, Rw: false }))).toEqual(['E', 'Rw']);
    expect(smarterComplete(goal({ smarter: smarter({ M: false }) }))).toBe(false);
  });
});

describe('checklistFromSession — SMARTER', () => {
  it('passes when every letter is named across the goals', () => {
    const result = checklistFromSession({
      session: session(),
      goals: [goal(), goal()],
      actions: [],
    });
    expect(stateOf(result, 'smarter_met')).toBe('pass');
    expect(detailOf(result, 'smarter_met')).toContain('2 goals');
  });

  it('uses the singular for one goal', () => {
    const result = checklistFromSession({ session: session(), goals: [goal()], actions: [] });
    expect(detailOf(result, 'smarter_met')).toContain('1 goal.');
  });

  it('calls out Exciting and Rewarded specifically — her known gap', () => {
    const result = checklistFromSession({
      session: session(),
      goals: [goal({ smarter: smarter({ E: false, Rw: false }) })],
      actions: [],
    });

    expect(stateOf(result, 'smarter_met')).toBe('fail');
    expect(result.missing_smarter).toEqual(['E', 'Rw']);
    expect(detailOf(result, 'smarter_met')).toBe(
      'Missing Exciting and Rewarded — Exciting and Rewarded are the ones that usually go unnamed.',
    );
  });

  it('reports an ordinary missing letter without the gap framing', () => {
    const result = checklistFromSession({
      session: session(),
      goals: [goal({ smarter: smarter({ M: false }) })],
      actions: [],
    });
    expect(detailOf(result, 'smarter_met')).toBe('Missing Measurable.');
  });

  it('names one often-missed letter in the singular', () => {
    const result = checklistFromSession({
      session: session(),
      goals: [goal({ smarter: smarter({ E: false }) })],
      actions: [],
    });
    expect(detailOf(result, 'smarter_met')).toBe(
      'Missing Exciting — Exciting is the one that usually goes unnamed.',
    );
  });

  it('is not applicable when no open goal is attached', () => {
    const result = checklistFromSession({
      session: session(),
      goals: [
        goal({ status: 'achieved' }),
        goal({ deleted_at: '2026-07-01T00:00:00.000Z' }),
      ],
      actions: [],
    });
    expect(stateOf(result, 'smarter_met')).toBe('na');
    expect(detailOf(result, 'smarter_met')).toContain('No open goals');
  });

  it('pools missing letters across several goals in canonical order', () => {
    const result = checklistFromSession({
      session: session(),
      goals: [
        goal({ smarter: smarter({ Rw: false }) }),
        goal({ smarter: smarter({ S: false }) }),
      ],
      actions: [],
    });
    // Collected Rw-then-S, but rendered in SMARTER order.
    expect(detailOf(result, 'smarter_met')).toContain('Specific and Rewarded');
  });
});

describe('checklistFromSession — low wheel scores', () => {
  const lowWheel = snapshot('2026-07-15', [
    ['Health', 3, 8],
    ['Finances', 2, 7],
    ['Career', 8, 9],
  ]);

  it('is not applicable when nothing is low', () => {
    const result = checklistFromSession({
      session: session(),
      goals: [],
      actions: [],
      wheel: snapshot('2026-07-15', [['Career', 8, 9]]),
    });
    expect(stateOf(result, 'low_scores_flagged')).toBe('na');
    expect(detailOf(result, 'low_scores_flagged')).toContain(`at or below ${LOW_SCORE_THRESHOLD}`);
  });

  it('is not applicable when no wheel was scored at all', () => {
    const result = checklistFromSession({ session: session(), goals: [], actions: [] });
    expect(stateOf(result, 'low_scores_flagged')).toBe('na');
    expect(detailOf(result, 'low_scores_flagged')).toBe('No wheel scored in this session.');
  });

  it('passes when every low domain was named', () => {
    const result = checklistFromSession({
      session: session({ flagged_domains: ['Health', 'Finances'] }),
      goals: [],
      actions: [],
      wheel: lowWheel,
    });
    expect(stateOf(result, 'low_scores_flagged')).toBe('pass');
    expect(result.unflagged_low_domains).toEqual([]);
    expect(detailOf(result, 'low_scores_flagged')).toBe('All 2 low domains named.');
  });

  it('passes but still lists what went unnamed', () => {
    const result = checklistFromSession({
      session: session({ flagged_domains: ['Health'] }),
      goals: [],
      actions: [],
      wheel: lowWheel,
    });
    expect(stateOf(result, 'low_scores_flagged')).toBe('pass');
    expect(result.unflagged_low_domains).toEqual(['Finances']);
    expect(detailOf(result, 'low_scores_flagged')).toContain('Still unnamed: Finances');
  });

  it('uses the singular when exactly one low domain was named', () => {
    const result = checklistFromSession({
      session: session({ flagged_domains: ['Health'] }),
      goals: [],
      actions: [],
      wheel: snapshot('2026-07-15', [['Health', 3, 8]]),
    });
    expect(detailOf(result, 'low_scores_flagged')).toBe('All 1 low domain named.');
  });

  it('fails when low scores went entirely unnamed', () => {
    const result = checklistFromSession({
      session: session(),
      goals: [],
      actions: [],
      wheel: lowWheel,
    });
    expect(stateOf(result, 'low_scores_flagged')).toBe('fail');
    expect(detailOf(result, 'low_scores_flagged')).toContain('Health, Finances are at or below');
    expect(detailOf(result, 'low_scores_flagged')).toContain('reframe');
  });

  it('uses the singular verb for a single unnamed low domain', () => {
    const result = checklistFromSession({
      session: session(),
      goals: [],
      actions: [],
      wheel: snapshot('2026-07-15', [['Health', 3, 8]]),
    });
    expect(detailOf(result, 'low_scores_flagged')).toContain('Health is at or below');
  });

  it('treats exactly the threshold as low', () => {
    const result = checklistFromSession({
      session: session(),
      goals: [],
      actions: [],
      wheel: snapshot('2026-07-15', [['Health', LOW_SCORE_THRESHOLD, 8]]),
    });
    expect(stateOf(result, 'low_scores_flagged')).toBe('fail');
  });
});

describe('checklistFromSession — Will step', () => {
  it('passes when the session produced actions', () => {
    const result = checklistFromSession({
      session: session(),
      goals: [],
      actions: [action(), action()],
    });
    expect(stateOf(result, 'will_step')).toBe('pass');
    expect(detailOf(result, 'will_step')).toBe('2 actions committed.');
  });

  it('uses the singular for one action', () => {
    const result = checklistFromSession({ session: session(), goals: [], actions: [action()] });
    expect(detailOf(result, 'will_step')).toBe('1 action committed.');
  });

  it('fails when nothing was committed', () => {
    const result = checklistFromSession({ session: session(), goals: [], actions: [] });
    expect(stateOf(result, 'will_step')).toBe('fail');
    expect(detailOf(result, 'will_step')).toContain('did not land');
  });

  it('ignores actions from other sessions and deleted actions', () => {
    const result = checklistFromSession({
      session: session(),
      goals: [],
      actions: [
        action({ session_id: 'session-other' }),
        action({ deleted_at: '2026-07-16T00:00:00.000Z' }),
      ],
    });
    expect(stateOf(result, 'will_step')).toBe('fail');
  });
});

describe('checklistFromSession — review date', () => {
  it('passes on a session-level review date', () => {
    const result = checklistFromSession({
      session: session({ review_dates: ['2026-07-22', '2026-07-25'] }),
      goals: [],
      actions: [],
    });
    expect(stateOf(result, 'review_date_set')).toBe('pass');
    expect(detailOf(result, 'review_date_set')).toBe('Review set for 2026-07-22 and 2026-07-25.');
  });

  it('also passes when every action carries its own review date', () => {
    const result = checklistFromSession({
      session: session(),
      goals: [],
      actions: [action({ review_date: '2026-07-22' }), action({ review_date: '2026-07-25' })],
    });
    expect(stateOf(result, 'review_date_set')).toBe('pass');
    expect(detailOf(result, 'review_date_set')).toBe('Every action carries its own review date.');
  });

  it('fails when only some actions have a review date', () => {
    const result = checklistFromSession({
      session: session(),
      goals: [],
      actions: [action({ review_date: '2026-07-22' }), action()],
    });
    expect(stateOf(result, 'review_date_set')).toBe('fail');
    expect(detailOf(result, 'review_date_set')).toBe('1 of 2 actions have no review date.');
  });

  it('fails distinctly when there is nothing to hang a review on', () => {
    const result = checklistFromSession({ session: session(), goals: [], actions: [] });
    expect(stateOf(result, 'review_date_set')).toBe('fail');
    expect(detailOf(result, 'review_date_set')).toBe('No review date, and no actions to hang one on.');
  });
});

describe('checklistFromSession — roll-up', () => {
  it('counts a clean run as all clear, with na items not spoiling it', () => {
    const result = checklistFromSession({
      session: session({ review_dates: ['2026-07-22'] }),
      goals: [],
      actions: [action()],
      wheel: snapshot('2026-07-15', [['Career', 9, 9]]),
    });

    expect(result.passed).toBe(2);
    expect(result.na).toBe(2);
    expect(result.failed).toBe(0);
    expect(result.all_clear).toBe(true);
  });

  it('reports the worst case honestly', () => {
    const result = checklistFromSession({
      session: session(),
      goals: [goal({ smarter: smarter({ E: false, Rw: false }) })],
      actions: [],
      wheel: snapshot('2026-07-15', [['Health', 2, 8]]),
    });

    expect(result.failed).toBe(4);
    expect(result.all_clear).toBe(false);
    expect(result.session_id).toBe('session-1');
    expect(result.lines.map((l) => l.item)).toEqual([
      'smarter_met',
      'low_scores_flagged',
      'will_step',
      'review_date_set',
    ]);
  });

  it('labels every line with the wording from her own checklist', () => {
    const result = checklistFromSession({ session: session(), goals: [], actions: [] });
    expect(result.lines.map((l) => l.label)).toEqual([
      'SMARTER goals met — including Exciting and Rewarded, named out loud',
      'Low Wheel scores flagged as a good sign',
      'Ended with a Will / Take-action step',
      'Review date set before closing',
    ]);
  });
});
