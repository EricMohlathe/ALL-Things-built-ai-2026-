import { beforeEach, describe, expect, it } from 'vitest';

import {
  WHEEL_MAX,
  clampScore,
  domainsBelow,
  gapToTarget,
  groupWheelRows,
  interpolateSnapshots,
  latestSnapshot,
  snapshotOn,
  snapshotToRows,
  wheelAverage,
  wheelDelta,
} from '../wheel.js';
import { NALEDI, THABO, resetIds, snapshot, wheelRow } from './factories.js';

beforeEach(resetIds);

describe('clampScore', () => {
  it('holds the 0–10 range', () => {
    expect(clampScore(5)).toBe(5);
    expect(clampScore(11)).toBe(WHEEL_MAX);
    expect(clampScore(-3)).toBe(0);
    expect(clampScore(Number.NaN)).toBe(0);
  });
});

describe('groupWheelRows', () => {
  it('groups flat rows into dated snapshots, oldest first', () => {
    const snapshots = groupWheelRows([
      wheelRow({ date: '2026-07-15', domain: 'Health', score: 5 }),
      wheelRow({ date: '2026-07-15', domain: 'Career', score: 7 }),
      wheelRow({ date: '2026-03-01', domain: 'Health', score: 3 }),
    ]);

    expect(snapshots.map((s) => s.date)).toEqual(['2026-03-01', '2026-07-15']);
    expect(snapshots[1]!.domains.map((d) => d.domain)).toEqual(['Health', 'Career']);
  });

  it('filters to one coachee when asked', () => {
    const rows = [
      wheelRow({ coachee_id: NALEDI }),
      wheelRow({ coachee_id: THABO, domain: 'Career' }),
    ];
    expect(groupWheelRows(rows, NALEDI)).toHaveLength(1);
    expect(groupWheelRows(rows)).toHaveLength(2);
  });

  it('separates two coachees scored on the same day', () => {
    const snapshots = groupWheelRows([
      wheelRow({ coachee_id: THABO }),
      wheelRow({ coachee_id: NALEDI }),
    ]);
    expect(snapshots).toHaveLength(2);
    expect(snapshots.map((s) => s.coachee_id)).toEqual([NALEDI, THABO]);
  });

  it('lets a re-scored domain on the same date replace the earlier value', () => {
    const snapshots = groupWheelRows([
      wheelRow({ domain: 'Health', score: 4 }),
      wheelRow({ domain: 'Health', score: 6 }),
    ]);
    expect(snapshots[0]!.domains).toEqual([{ domain: 'Health', score: 6, target: 8 }]);
  });

  it('ignores deleted rows and clamps stored values', () => {
    const snapshots = groupWheelRows([
      wheelRow({ domain: 'Health', score: 99, target: -1 }),
      wheelRow({ domain: 'Career', deleted_at: '2026-07-16T00:00:00.000Z' }),
    ]);
    expect(snapshots[0]!.domains).toEqual([{ domain: 'Health', score: 10, target: 0 }]);
  });
});

describe('snapshot lookup', () => {
  const rows = [
    wheelRow({ date: '2026-03-01', score: 3 }),
    wheelRow({ date: '2026-07-15', score: 6 }),
  ];

  it('finds the most recent snapshot', () => {
    expect(latestSnapshot(rows, NALEDI)?.date).toBe('2026-07-15');
    expect(latestSnapshot([], NALEDI)).toBeNull();
  });

  it('finds a snapshot by date', () => {
    expect(snapshotOn(rows, NALEDI, '2026-03-01')?.domains[0]!.score).toBe(3);
    expect(snapshotOn(rows, NALEDI, '2026-01-01')).toBeNull();
  });
});

describe('wheelAverage', () => {
  it('averages the domains', () => {
    expect(
      wheelAverage(
        snapshot('2026-07-15', [
          ['Health', 4, 8],
          ['Career', 7, 9],
        ]),
      ),
    ).toBe(5.5);
  });

  it('has no answer without data', () => {
    expect(wheelAverage(null)).toBeNull();
    expect(wheelAverage(snapshot('2026-07-15', []))).toBeNull();
  });
});

describe('domainsBelow', () => {
  it('lists domains at or under the threshold', () => {
    const s = snapshot('2026-07-15', [
      ['Health', 3, 8],
      ['Finances', 4, 7],
      ['Career', 5, 9],
    ]);
    expect(domainsBelow(s, 4)).toEqual(['Health', 'Finances']);
    expect(domainsBelow(null, 4)).toEqual([]);
  });
});

describe('gapToTarget', () => {
  it('sorts by the widest gap first', () => {
    const gaps = gapToTarget(
      snapshot('2026-07-15', [
        ['Career', 8, 9],
        ['Health', 3, 9],
      ]),
    );
    expect(gaps.map((g) => g.domain)).toEqual(['Health', 'Career']);
    expect(gaps[0]!.gap).toBe(6);
    expect(gapToTarget(null)).toEqual([]);
  });
});

describe('wheelDelta', () => {
  const march = snapshot('2026-03-01', [
    ['Health', 3, 8],
    ['Career', 7, 9],
    ['Finances', 5, 7],
  ]);
  const july = snapshot('2026-07-15', [
    ['Health', 6, 8],
    ['Career', 5, 9],
    ['Finances', 5, 7],
  ]);

  it('reports movement per domain', () => {
    const delta = wheelDelta(march, july);

    expect(delta.improved).toEqual(['Health']);
    expect(delta.declined).toEqual(['Career']);
    expect(delta.unchanged).toEqual(['Finances']);
    expect(delta.biggest_gain?.domain).toBe('Health');
    expect(delta.biggest_gain?.delta).toBe(3);
    expect(delta.biggest_drop?.domain).toBe('Career');
    expect(delta.biggest_drop?.delta).toBe(-2);
  });

  it('reports the averages and their difference', () => {
    const delta = wheelDelta(march, july);
    expect(delta.average_from).toBe(5);
    expect(delta.average_to).toBeCloseTo(5.33, 2);
    expect(delta.average_delta).toBeCloseTo(0.33, 2);
    expect(delta.from_date).toBe('2026-03-01');
    expect(delta.to_date).toBe('2026-07-15');
  });

  it('picks the largest mover regardless of where it sits on the wheel', () => {
    const flat = snapshot('2026-03-01', [
      ['Health', 3, 8],
      ['Career', 3, 8],
    ]);
    // Same two domains, but which one moved most swaps between the pair.
    const careerLeads = snapshot('2026-07-15', [
      ['Health', 5, 8],
      ['Career', 8, 8],
    ]);
    const healthLeads = snapshot('2026-07-15', [
      ['Health', 8, 8],
      ['Career', 5, 8],
    ]);

    expect(wheelDelta(flat, careerLeads).biggest_gain?.domain).toBe('Career');
    expect(wheelDelta(flat, healthLeads).biggest_gain?.domain).toBe('Health');

    // Reversing the comparison turns the same movers into the biggest drops,
    // which is where a comparator that only ever keeps the newer value fails.
    expect(wheelDelta(careerLeads, flat).biggest_drop?.domain).toBe('Career');
    expect(wheelDelta(healthLeads, flat).biggest_drop?.domain).toBe('Health');
  });

  it('handles a first-ever snapshot with nothing to compare against', () => {
    const delta = wheelDelta(null, july);

    expect(delta.from_date).toBeNull();
    expect(delta.average_from).toBeNull();
    expect(delta.average_delta).toBeNull();
    expect(delta.improved).toEqual([]);
    expect(delta.declined).toEqual([]);
    expect(delta.biggest_gain).toBeNull();
    expect(delta.biggest_drop).toBeNull();
    expect(delta.domains.every((d) => d.delta === null && d.from === null)).toBe(true);
    expect(delta.domains_added).toEqual(['Health', 'Career', 'Finances']);
  });

  it('handles having no newer snapshot', () => {
    const delta = wheelDelta(march, null);
    expect(delta.average_to).toBeNull();
    expect(delta.domains_removed).toEqual(['Health', 'Career', 'Finances']);
    expect(delta.domains.every((d) => d.to === null)).toBe(true);
    // Target falls back to the older snapshot's value so the ghost ring still draws.
    expect(delta.domains[0]!.target).toBe(8);
    expect(delta.domains[0]!.gap).toBeNull();
  });

  it('compares two empty snapshots without inventing findings', () => {
    const delta = wheelDelta(null, null);
    expect(delta.domains).toEqual([]);
    expect(delta.average_delta).toBeNull();
  });

  it('tracks domains she added to or removed from her wheel', () => {
    const before = snapshot('2026-03-01', [
      ['Health', 5, 8],
      ['Romance/Partner', 4, 8],
    ]);
    const after = snapshot('2026-07-15', [
      ['Health', 7, 8],
      ['Spirituality/Purpose', 6, 9],
    ]);
    const delta = wheelDelta(before, after);

    expect(delta.domains_added).toEqual(['Spirituality/Purpose']);
    expect(delta.domains_removed).toEqual(['Romance/Partner']);
    // The current wheel's order leads; the dropped domain trails it.
    expect(delta.domains.map((d) => d.domain)).toEqual([
      'Health',
      'Spirituality/Purpose',
      'Romance/Partner',
    ]);
    // A domain present on only one side has no delta rather than a fake zero.
    const added = delta.domains.find((d) => d.domain === 'Spirituality/Purpose')!;
    expect(added.delta).toBeNull();
    expect(added.improved).toBe(false);
    expect(added.gap).toBe(3);
  });
});

describe('interpolateSnapshots', () => {
  const from = snapshot('2026-03-01', [['Health', 2, 6]]);
  const to = snapshot('2026-07-15', [['Health', 8, 10]]);

  it('returns the endpoints exactly', () => {
    expect(interpolateSnapshots(from, to, 0)[0]).toEqual({ domain: 'Health', score: 2, target: 6 });
    expect(interpolateSnapshots(from, to, 1)[0]).toEqual({ domain: 'Health', score: 8, target: 10 });
  });

  it('tweens the midpoint', () => {
    expect(interpolateSnapshots(from, to, 0.5)[0]).toEqual({
      domain: 'Health',
      score: 5,
      target: 8,
    });
  });

  it('clamps the scrubber to the timeline', () => {
    expect(interpolateSnapshots(from, to, -2)[0]!.score).toBe(2);
    expect(interpolateSnapshots(from, to, 9)[0]!.score).toBe(8);
  });

  it('holds a newly added domain steady instead of growing it from zero', () => {
    // Otherwise adding a domain reads as the wheel collapsing and re-inflating.
    const withNew = snapshot('2026-07-15', [
      ['Health', 8, 10],
      ['Fun & Recreation', 5, 9],
    ]);
    const frames = [0, 0.5, 1].map(
      (t) => interpolateSnapshots(from, withNew, t).find((d) => d.domain === 'Fun & Recreation')!,
    );
    expect(frames.map((f) => f.score)).toEqual([5, 5, 5]);
  });

  it('holds a removed domain steady as well', () => {
    const frames = [0, 0.5, 1].map(
      (t) => interpolateSnapshots(to, null, t).find((d) => d.domain === 'Health')!,
    );
    expect(frames.map((f) => f.score)).toEqual([8, 8, 8]);
  });

  it('has nothing to draw between two empty snapshots', () => {
    expect(interpolateSnapshots(null, null, 0.5)).toEqual([]);
  });
});

describe('snapshotToRows', () => {
  it('flattens a snapshot back into persistable rows', () => {
    let n = 0;
    const rows = snapshotToRows(
      snapshot('2026-07-15', [
        ['Health', 6, 8],
        ['Career', 12, 9],
      ]),
      () => `row-${(n += 1)}`,
      '2026-07-15T10:00:00.000Z',
    );

    expect(rows).toEqual([
      {
        id: 'row-1',
        coachee_id: NALEDI,
        date: '2026-07-15',
        domain: 'Health',
        score: 6,
        target: 8,
        updated_at: '2026-07-15T10:00:00.000Z',
      },
      {
        id: 'row-2',
        coachee_id: NALEDI,
        date: '2026-07-15',
        domain: 'Career',
        score: 10,
        target: 9,
        updated_at: '2026-07-15T10:00:00.000Z',
      },
    ]);
  });
});
