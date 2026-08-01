import type { AiRun } from '@cmw/core';
import { describe, expect, it } from 'vitest';

import { digestContract, prepContract } from '../contracts.js';
import { latestRun } from '../ledger.js';
import { digestFixture, prepFixture } from './fixtures.js';

function run(overrides: Partial<AiRun> & Pick<AiRun, 'kind' | 'created_at'>): AiRun {
  return {
    id: `r-${overrides.created_at}`,
    model: 'claude-haiku-4-5',
    tokens_in: 100,
    tokens_out: 200,
    cost_usd: 0.001,
    updated_at: overrides.created_at,
    output: JSON.stringify(digestFixture()),
    ...overrides,
  };
}

describe('latestRun', () => {
  const contract = digestContract();

  it('returns nothing when the ledger is empty', () => {
    expect(latestRun([], 'weekly_digest', contract)).toBeNull();
  });

  it('picks the newest run of the kind asked for', () => {
    const found = latestRun(
      [
        run({ kind: 'weekly_digest', created_at: '2099-03-02T06:00:00.000Z' }),
        run({ kind: 'weekly_digest', created_at: '2099-03-09T06:00:00.000Z' }),
        run({ kind: 'session_analyzer', created_at: '2099-03-10T06:00:00.000Z' }),
      ],
      'weekly_digest',
      contract,
    );
    expect(found?.run.created_at).toBe('2099-03-09T06:00:00.000Z');
    expect(found?.data.focus_sentence).toContain('reviews slipped');
  });

  it('matches the subject exactly, so last week is never shown as this week', () => {
    const runs = [
      run({ kind: 'weekly_digest', created_at: '2099-03-02T06:00:00.000Z', input_ref: 'week:2099-03-02' }),
      run({ kind: 'weekly_digest', created_at: '2099-03-09T06:00:00.000Z', input_ref: 'week:2099-03-09' }),
    ];
    expect(latestRun(runs, 'weekly_digest', contract, 'week:2099-03-09')?.run.id).toBe(
      'r-2099-03-09T06:00:00.000Z',
    );
    expect(latestRun(runs, 'weekly_digest', contract, 'week:2099-03-16')).toBeNull();
  });

  it('ignores rows with no output — a failed call is on the ledger but has nothing to show', () => {
    const failed = run({ kind: 'weekly_digest', created_at: '2099-03-09T06:00:00.000Z', output: null });
    expect(latestRun([failed], 'weekly_digest', contract)).toBeNull();
  });

  it('ignores soft-deleted rows', () => {
    const deleted = run({
      kind: 'weekly_digest',
      created_at: '2099-03-09T06:00:00.000Z',
      deleted_at: '2099-03-10T00:00:00.000Z',
    });
    expect(latestRun([deleted], 'weekly_digest', contract)).toBeNull();
  });

  it('skips a row whose stored shape no longer validates, and keeps looking', () => {
    // A row restored from an old backup can predate a contract change. Falling
    // back to the previous good run beats crashing the Deck on a stale cache.
    const stale = run({
      kind: 'weekly_digest',
      created_at: '2099-03-09T06:00:00.000Z',
      output: JSON.stringify({ focus: 'an older shape' }),
    });
    const good = run({ kind: 'weekly_digest', created_at: '2099-03-08T06:00:00.000Z' });

    expect(latestRun([stale, good], 'weekly_digest', contract)?.run.created_at).toBe(
      '2099-03-08T06:00:00.000Z',
    );
    expect(latestRun([stale], 'weekly_digest', contract)).toBeNull();
  });

  it('survives output that is not JSON at all', () => {
    const junk = run({
      kind: 'weekly_digest',
      created_at: '2099-03-09T06:00:00.000Z',
      output: 'not json {',
    });
    expect(latestRun([junk], 'weekly_digest', contract)).toBeNull();
  });

  it('reads back whatever contract it is handed', () => {
    const prep = run({
      kind: 'prep_whisperer',
      created_at: '2099-03-10T07:00:00.000Z',
      output: JSON.stringify(prepFixture()),
      input_ref: 'prep:c-naledi@2099-03-10',
    });
    const found = latestRun([prep], 'prep_whisperer', prepContract(), 'prep:c-naledi@2099-03-10');
    // The contract's trimming applies on read, exactly as it did on write.
    expect(found?.data.recap_3_lines).toHaveLength(3);
  });
});
