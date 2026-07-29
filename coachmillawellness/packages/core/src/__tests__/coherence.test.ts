import { beforeEach, describe, expect, it } from 'vitest';

import {
  coherenceMatrix,
  consistencyHeatmap,
  distributionBalance,
  pipelineFunnel,
  publishStreak,
} from '../coherence.js';
import { content, pillar, resetIds } from './factories.js';

beforeEach(resetIds);

const NOW = '2026-07-30';

describe('distributionBalance', () => {
  it('is perfectly balanced when posts are spread evenly', () => {
    expect(distributionBalance([5, 5, 5])).toBe(1);
  });

  it('collapses to zero when one pillar takes everything', () => {
    expect(distributionBalance([10, 0, 0])).toBe(0);
  });

  it('sits in between for a lopsided spread', () => {
    const balance = distributionBalance([10, 5, 5]);
    expect(balance).toBeGreaterThan(0);
    expect(balance).toBeLessThan(1);
  });

  it('tells apart two spreads that share a dominant pillar', () => {
    // The reason this uses entropy rather than a max/total ratio.
    expect(distributionBalance([10, 10, 0])).not.toBe(distributionBalance([10, 5, 5]));
  });

  it('reports balance rather than alarm when there is nothing to compare', () => {
    expect(distributionBalance([])).toBe(1);
    expect(distributionBalance([7])).toBe(1);
    expect(distributionBalance([0, 0, 0])).toBe(1);
  });
});

describe('coherenceMatrix', () => {
  it('counts published work per pillar per window', () => {
    const momentum = pillar({ name: 'Momentum' });
    const rest = pillar({ name: 'Rest' });

    const matrix = coherenceMatrix(
      [momentum, rest],
      [
        content({ pillar_id: momentum.id, publish_date: '2026-07-25' }),
        content({ pillar_id: momentum.id, publish_date: '2026-07-10' }),
        // 71 days back: inside the 90-day column, outside the 60-day one.
        content({ pillar_id: momentum.id, publish_date: '2026-05-20' }),
        content({ pillar_id: rest.id, publish_date: '2026-07-28' }),
      ],
      { now: NOW },
    );

    const momentumRow = matrix.rows.find((r) => r.name === 'Momentum')!;
    expect(momentumRow.cells.map((c) => c.count)).toEqual([2, 2, 3]);
    expect(momentumRow.total).toBe(3);
    expect(matrix.total_published).toBe(4);
    expect(matrix.windows).toEqual([30, 60, 90]);
  });

  it('scales cell intensity within its own column', () => {
    const loud = pillar({ name: 'Loud' });
    const quiet = pillar({ name: 'Quiet' });

    const matrix = coherenceMatrix(
      [loud, quiet],
      [
        content({ pillar_id: loud.id, publish_date: '2026-07-20' }),
        content({ pillar_id: loud.id, publish_date: '2026-07-21' }),
        content({ pillar_id: quiet.id, publish_date: '2026-07-22' }),
      ],
      { now: NOW, windows: [30] },
    );

    expect(matrix.rows.find((r) => r.name === 'Loud')!.cells[0]!.intensity).toBe(1);
    expect(matrix.rows.find((r) => r.name === 'Quiet')!.cells[0]!.intensity).toBe(0.5);
  });

  it('reports zero intensity for an empty column', () => {
    const matrix = coherenceMatrix([pillar()], [], { now: NOW, windows: [30] });
    expect(matrix.rows[0]!.cells[0]!.intensity).toBe(0);
    expect(matrix.rows[0]!.share).toBe(0);
  });

  it('flags a starved pillar and names the dominant one', () => {
    const loud = pillar({ name: 'Loud' });
    const starved = pillar({ name: 'Starved' });

    const matrix = coherenceMatrix(
      [loud, starved],
      [
        content({ pillar_id: loud.id, publish_date: '2026-07-20' }),
        // Inside the 90-day window but outside the 30-day one: still starved.
        content({ pillar_id: starved.id, publish_date: '2026-05-25' }),
      ],
      { now: NOW },
    );

    expect(matrix.starved_pillars).toEqual(['Starved']);
    expect(matrix.dominant_pillar).toBe('Loud');
    // Starvation is a recency signal and drift is a distribution one, so they
    // disagree here on purpose: over 90 days the two pillars are perfectly even
    // (drift 0) while one of them has gone quiet for the last month. Losing that
    // distinction would hide exactly the drift the map exists to catch.
    expect(matrix.drift).toBe(0);
    expect(matrix.rows.find((r) => r.name === 'Starved')!.cells[0]!.count).toBe(0);
  });

  it('reports drift when one pillar crowds out another in the same window', () => {
    const loud = pillar({ name: 'Loud' });
    const quiet = pillar({ name: 'Quiet' });

    const matrix = coherenceMatrix(
      [loud, quiet],
      [
        content({ pillar_id: loud.id, publish_date: '2026-07-20' }),
        content({ pillar_id: loud.id, publish_date: '2026-07-21' }),
        content({ pillar_id: loud.id, publish_date: '2026-07-22' }),
        content({ pillar_id: quiet.id, publish_date: '2026-07-23' }),
      ],
      { now: NOW },
    );

    expect(matrix.drift).toBeGreaterThan(0);
    expect(matrix.rows.find((r) => r.name === 'Loud')!.share).toBe(0.75);
  });

  it('has no dominant pillar before anything is published', () => {
    const matrix = coherenceMatrix([pillar(), pillar()], [], { now: NOW });
    expect(matrix.dominant_pillar).toBeNull();
    expect(matrix.balance).toBe(1);
    expect(matrix.drift).toBe(0);
  });

  it('picks the busier pillar when scanning in either order', () => {
    const first = pillar({ name: 'First' });
    const second = pillar({ name: 'Second' });
    const items = [
      content({ pillar_id: second.id, publish_date: '2026-07-20' }),
      content({ pillar_id: second.id, publish_date: '2026-07-21' }),
      content({ pillar_id: first.id, publish_date: '2026-07-22' }),
    ];
    expect(coherenceMatrix([first, second], items, { now: NOW }).dominant_pillar).toBe('Second');
    expect(coherenceMatrix([second, first], items, { now: NOW }).dominant_pillar).toBe('Second');
  });

  it('counts only work that actually reached an audience', () => {
    const p = pillar();
    const matrix = coherenceMatrix(
      [p],
      [
        content({ pillar_id: p.id, status: 'posted', publish_date: '2026-07-20' }),
        content({ pillar_id: p.id, status: 'analyzed', publish_date: '2026-07-21' }),
        content({ pillar_id: p.id, status: 'idea', publish_date: '2026-07-22' }),
        content({ pillar_id: p.id, status: 'script', publish_date: '2026-07-23' }),
        content({ pillar_id: p.id, status: 'filmed', publish_date: '2026-07-24' }),
      ],
      { now: NOW },
    );
    expect(matrix.total_published).toBe(2);
  });

  it('can be asked to count the pipeline too', () => {
    const p = pillar();
    const matrix = coherenceMatrix(
      [p],
      [
        content({ pillar_id: p.id, status: 'posted', publish_date: '2026-07-20' }),
        content({ pillar_id: p.id, status: 'filmed', publish_date: '2026-07-24' }),
      ],
      { now: NOW, statuses: ['posted', 'filmed'] },
    );
    expect(matrix.total_published).toBe(2);
  });

  it('surfaces published work that serves no pillar', () => {
    const p = pillar();
    const matrix = coherenceMatrix(
      [p],
      [
        content({ pillar_id: p.id, publish_date: '2026-07-20' }),
        content({ pillar_id: null, publish_date: '2026-07-21' }),
      ],
      { now: NOW },
    );
    expect(matrix.unassigned).toBe(1);
    // Share is of attributed posts, so the orphan does not dilute the pillar.
    expect(matrix.rows[0]!.share).toBe(1);
  });

  it('ignores deleted pillars, deleted items and undated items', () => {
    const live = pillar({ name: 'Live' });
    const gone = pillar({ name: 'Gone', deleted_at: '2026-07-01T00:00:00.000Z' });

    const matrix = coherenceMatrix(
      [live, gone],
      [
        content({ pillar_id: live.id, publish_date: '2026-07-20' }),
        content({ pillar_id: live.id, publish_date: '2026-07-21', deleted_at: '2026-07-22T00:00:00.000Z' }),
        content({ pillar_id: live.id, publish_date: null }),
      ],
      { now: NOW },
    );

    expect(matrix.rows.map((r) => r.name)).toEqual(['Live']);
    expect(matrix.total_published).toBe(1);
  });

  it('excludes posts outside the widest window and dated in the future', () => {
    const p = pillar();
    const matrix = coherenceMatrix(
      [p],
      [
        content({ pillar_id: p.id, publish_date: '2026-01-01' }),
        content({ pillar_id: p.id, publish_date: '2026-08-15' }),
      ],
      { now: NOW },
    );
    expect(matrix.total_published).toBe(0);
  });

  it('survives being asked for no windows at all', () => {
    const matrix = coherenceMatrix([pillar()], [content()], { now: NOW, windows: [] });
    expect(matrix.windows).toEqual([]);
    expect(matrix.rows[0]!.cells).toEqual([]);
    expect(matrix.rows[0]!.total).toBe(0);
  });

  it('sorts windows narrowest first regardless of input order', () => {
    const matrix = coherenceMatrix([pillar()], [], { now: NOW, windows: [90, 30, 60] });
    expect(matrix.windows).toEqual([30, 60, 90]);
  });

  it('defaults to today when no clock is supplied', () => {
    const matrix = coherenceMatrix([pillar()], []);
    expect(matrix.windows).toEqual([30, 60, 90]);
    expect(matrix.total_published).toBe(0);
  });
});

describe('consistencyHeatmap', () => {
  it('returns one cell per day, oldest first', () => {
    const strip = consistencyHeatmap([], { now: NOW, days: 7 });
    expect(strip).toHaveLength(7);
    expect(strip[0]!.date).toBe('2026-07-24');
    expect(strip.at(-1)!.date).toBe(NOW);
  });

  it('counts posts per day and scales intensity to the busiest day', () => {
    const strip = consistencyHeatmap(
      [
        content({ publish_date: '2026-07-29' }),
        content({ publish_date: '2026-07-29' }),
        content({ publish_date: '2026-07-30' }),
      ],
      { now: NOW, days: 3 },
    );

    expect(strip.map((d) => d.count)).toEqual([0, 2, 1]);
    expect(strip.map((d) => d.intensity)).toEqual([0, 1, 0.5]);
  });

  it('leaves intensity flat when nothing was published', () => {
    const strip = consistencyHeatmap([content({ status: 'idea' })], { now: NOW, days: 2 });
    expect(strip.every((d) => d.intensity === 0)).toBe(true);
  });

  it('ignores deleted and undated items', () => {
    const strip = consistencyHeatmap(
      [
        content({ publish_date: '2026-07-30', deleted_at: '2026-07-31T00:00:00.000Z' }),
        content({ publish_date: null }),
      ],
      { now: NOW, days: 2 },
    );
    expect(strip.every((d) => d.count === 0)).toBe(true);
  });

  it('defaults to a 90-day window ending today', () => {
    expect(consistencyHeatmap([])).toHaveLength(90);
  });

  it('honours a custom status filter', () => {
    const strip = consistencyHeatmap([content({ status: 'filmed', publish_date: NOW })], {
      now: NOW,
      days: 1,
      statuses: ['filmed'],
    });
    expect(strip[0]!.count).toBe(1);
  });
});

describe('publishStreak', () => {
  it('counts consecutive days ending today', () => {
    const streak = publishStreak(
      [
        content({ publish_date: '2026-07-30' }),
        content({ publish_date: '2026-07-29' }),
        content({ publish_date: '2026-07-28' }),
      ],
      { now: NOW },
    );
    expect(streak.current).toBe(3);
    expect(streak.longest).toBe(3);
  });

  it('breaks the current streak on a gap but remembers the best run', () => {
    const streak = publishStreak(
      [
        content({ publish_date: '2026-07-20' }),
        content({ publish_date: '2026-07-21' }),
        content({ publish_date: '2026-07-22' }),
        content({ publish_date: '2026-07-23' }),
        content({ publish_date: '2026-07-30' }),
      ],
      { now: NOW },
    );
    expect(streak.current).toBe(1);
    expect(streak.longest).toBe(4);
  });

  it('is zero when nothing has been published', () => {
    expect(publishStreak([], { now: NOW })).toEqual({ current: 0, longest: 0 });
    expect(publishStreak([content({ status: 'idea' })], { now: NOW })).toEqual({
      current: 0,
      longest: 0,
    });
  });

  it('is zero today when the last post was yesterday', () => {
    const streak = publishStreak([content({ publish_date: '2026-07-29' })], { now: NOW });
    expect(streak.current).toBe(0);
    expect(streak.longest).toBe(1);
  });

  it('counts two posts on one day as a single streak day', () => {
    const streak = publishStreak(
      [content({ publish_date: NOW }), content({ publish_date: NOW })],
      { now: NOW },
    );
    expect(streak.current).toBe(1);
  });

  it('defaults its clock and status filter', () => {
    expect(publishStreak([content({ publish_date: '2020-01-01' })]).current).toBe(0);
    expect(
      publishStreak([content({ status: 'filmed', publish_date: NOW })], {
        now: NOW,
        statuses: ['filmed'],
      }).current,
    ).toBe(1);
  });
});

describe('pipelineFunnel', () => {
  it('counts each stage in pipeline order', () => {
    const funnel = pipelineFunnel([
      content({ status: 'idea' }),
      content({ status: 'idea' }),
      content({ status: 'script' }),
      content({ status: 'analyzed' }),
      content({ status: 'posted', deleted_at: '2026-07-01T00:00:00.000Z' }),
    ]);

    expect(funnel).toEqual([
      { status: 'idea', count: 2 },
      { status: 'script', count: 1 },
      { status: 'filmed', count: 0 },
      { status: 'posted', count: 0 },
      { status: 'analyzed', count: 1 },
    ]);
  });
});
