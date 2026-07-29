import { describe, expect, it } from 'vitest';

import {
  CEMENT_SCRIPT,
  CEMENT_THRESHOLD,
  FRAMEWORK_NAMES,
  GREAT,
  GROW,
  LOW_SCORE_THRESHOLD,
  RATING_POINTS,
  RATING_RUBRIC,
  RATINGS,
  SMARTER_FLAGS,
  SMARTER_OFTEN_MISSED,
  WHEEL_DOMAINS_DEFAULT,
  elementDefinition,
  elementLabel,
  elementsOf,
  frameworkFor,
  isElementOf,
} from '../frameworks.js';

/**
 * These assertions guard Appendix A itself.
 *
 * The framework tables are her practice encoded as data — the AI grades against
 * them and the Session Engine prompts from them. A careless edit here would
 * quietly change how every session is scored, so the shape of her methodology is
 * pinned down the same way any other invariant would be.
 */

describe('GROW', () => {
  it('is Goal → Reality → Options → Will, in order', () => {
    expect(GROW.elements.map((e) => e.key)).toEqual(['goal', 'reality', 'options', 'will']);
    expect(GROW.elements.map((e) => e.letter).join('')).toBe('GROW');
    expect(GROW.expansion).toBe('Goal → Reality → Options → Will');
  });

  it('asks for the deeper goal as its own pass', () => {
    // The compendium names this as her gap: the success-definition question must
    // not be folded into the session-goal question.
    const goal = elementDefinition('GROW', 'goal')!;
    expect(goal.questions).toContain('What does success look like?');
    expect(goal.questions.length).toBeGreaterThanOrEqual(3);
    expect(goal.historically_skipped).toBe(true);
  });

  it('keeps pros-and-cons in Options', () => {
    const options = elementDefinition('GROW', 'options')!;
    expect(options.questions.some((q) => /pros and cons/i.test(q))).toBe(true);
    expect(options.historically_skipped).toBe(true);
  });

  it('asks for both 1–10 scores and a review date in Will', () => {
    const will = elementDefinition('GROW', 'will')!;
    expect(will.questions.some((q) => /confident/i.test(q))).toBe(true);
    expect(will.questions.some((q) => /committed/i.test(q))).toBe(true);
    expect(will.questions.some((q) => /review/i.test(q))).toBe(true);
  });

  it('does not flag Reality as a step she skips', () => {
    expect(elementDefinition('GROW', 'reality')!.historically_skipped).toBeUndefined();
  });
});

describe('GREAT', () => {
  it('is Goals → Reality & Rapport → Explore → Achieve → Take action, in order', () => {
    expect(GREAT.elements.map((e) => e.key)).toEqual([
      'goals',
      'reality_rapport',
      'explore',
      'achieve',
      'take_action',
    ]);
    expect(GREAT.elements.map((e) => e.letter).join('')).toBe('GREAT');
  });

  it('names reflective listening as the signature move of Rapport', () => {
    const rapport = elementDefinition('GREAT', 'reality_rapport')!;
    expect(rapport.questions.some((q) => /What I'm hearing you say/i.test(q))).toBe(true);
    expect(rapport.note).toMatch(/reflective listening/i);
  });

  it('obstacle-proofs in Achieve and pushes past a dismissive answer', () => {
    const achieve = elementDefinition('GREAT', 'achieve')!;
    expect(achieve.questions.some((q) => /could stop you/i.test(q))).toBe(true);
    expect(achieve.note).toMatch(/dismissive/i);
  });
});

describe('lookups', () => {
  it('resolves a framework and its element keys', () => {
    expect(frameworkFor('GROW')).toBe(GROW);
    expect(elementsOf('GREAT')).toHaveLength(5);
    expect(FRAMEWORK_NAMES).toEqual(['GROW', 'GREAT']);
  });

  it('labels an element without being told which framework it came from', () => {
    expect(elementLabel('options')).toBe('Options');
    expect(elementLabel('reality_rapport')).toBe('Reality & Rapport');
  });

  it('falls back to the raw key for something it does not recognise', () => {
    expect(elementLabel('nonsense' as never)).toBe('nonsense');
    expect(elementDefinition('GROW', 'nonsense' as never)).toBeUndefined();
  });

  it('keeps the two frameworks from bleeding into each other', () => {
    expect(isElementOf('GROW', 'goal')).toBe(true);
    expect(isElementOf('GROW', 'achieve')).toBe(false);
    expect(isElementOf('GREAT', 'achieve')).toBe(true);
    expect(isElementOf('GREAT', 'will')).toBe(false);
  });
});

describe('closing rules', () => {
  it('cements the agreement at 8 out of 10', () => {
    expect(CEMENT_THRESHOLD).toBe(8);
  });

  it('ships the actual script, not a reminder that one exists', () => {
    expect(CEMENT_SCRIPT.length).toBeGreaterThanOrEqual(3);
    expect(CEMENT_SCRIPT.join(' ')).toMatch(/review/i);
  });

  it('treats 4 out of 10 and below as a low score', () => {
    expect(LOW_SCORE_THRESHOLD).toBe(4);
  });
});

describe('rubric', () => {
  it('covers all five ratings from Appendix B', () => {
    expect(RATINGS).toEqual(['Strong', 'Adequate', 'Weak', 'Met', 'N/A']);
    for (const rating of RATINGS) {
      expect(RATING_RUBRIC[rating].length).toBeGreaterThan(20);
    }
  });

  it('orders the weights Strong > Met > Adequate > Weak', () => {
    expect(RATING_POINTS.Strong).toBeGreaterThan(RATING_POINTS.Met);
    expect(RATING_POINTS.Met).toBeGreaterThan(RATING_POINTS.Adequate);
    expect(RATING_POINTS.Adequate).toBeGreaterThan(RATING_POINTS.Weak);
    expect(RATING_POINTS.Weak).toBeGreaterThan(0);
  });
});

describe('SMARTER and the wheel', () => {
  it('has all seven letters, with Exciting and Rewarded present', () => {
    expect(SMARTER_FLAGS.map((f) => f.key)).toEqual(['S', 'M', 'A', 'R', 'T', 'E', 'Rw']);
    expect(SMARTER_FLAGS.map((f) => f.label)).toContain('Exciting');
    expect(SMARTER_FLAGS.map((f) => f.label)).toContain('Rewarded');
    expect(SMARTER_OFTEN_MISSED).toEqual(['E', 'Rw']);
  });

  it('defaults to her ten wheel domains', () => {
    expect(WHEEL_DOMAINS_DEFAULT).toHaveLength(10);
    expect(WHEEL_DOMAINS_DEFAULT).toContain('Spirituality/Purpose');
    expect(new Set(WHEEL_DOMAINS_DEFAULT).size).toBe(10);
  });
});
