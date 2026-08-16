import type { AiRun } from '@cmw/core';
import { describe, expect, it } from 'vitest';

import {
  BUDGET_WARN_PCT,
  DEFAULT_BUDGET_USD,
  aiRunRow,
  budgetStatus,
  costOf,
  describeBudget,
  estimateCost,
  estimateTokens,
  formatUsd,
  spendByKind,
} from '../cost.js';
import { MODELS, MODEL_IDS, isAiModelId, rateFor } from '../models.js';

const DURING_INTRO = '2099-01-01';

describe('the price list', () => {
  it('offers three models, Sonnet first', () => {
    expect(MODEL_IDS[0]).toBe('claude-sonnet-5');
    expect(MODEL_IDS).toHaveLength(3);
    for (const id of MODEL_IDS) expect(MODELS[id].id).toBe(id);
  });

  it('applies the promotional rate up to and including its last day', () => {
    const info = MODELS['claude-sonnet-5'];
    expect(info.intro).toBeDefined();
    const until = info.intro!.until;
    expect(rateFor('claude-sonnet-5', until)).toEqual({ input: 2, output: 10 });
  });

  it('reverts to the standard rate the day after the window closes', () => {
    // The bug this guards: a lapsed intro rate would silently halve every figure
    // the budget guardrail shows her.
    expect(rateFor('claude-sonnet-5', '2026-09-01')).toEqual({ input: 3, output: 15 });
  });

  it('leaves models without an intro window alone', () => {
    expect(rateFor('claude-opus-5', DURING_INTRO)).toEqual({ input: 5, output: 25 });
    expect(rateFor('claude-haiku-4-5', '2026-09-01')).toEqual({ input: 1, output: 5 });
  });

  it('records which models take adaptive thinking', () => {
    expect(MODELS['claude-opus-5'].supports_adaptive_thinking).toBe(true);
    expect(MODELS['claude-sonnet-5'].supports_adaptive_thinking).toBe(true);
    // Sending `thinking: adaptive` to a pre-4.6 model is a 400, not a downgrade.
    expect(MODELS['claude-haiku-4-5'].supports_adaptive_thinking).toBe(false);
  });

  it('recognises its own ids and nothing else', () => {
    expect(isAiModelId('claude-opus-5')).toBe(true);
    expect(isAiModelId('claude-opus-5-20260101')).toBe(false);
    expect(isAiModelId(null)).toBe(false);
  });
});

describe('costOf', () => {
  it('prices plain input and output at the rate for the day', () => {
    // 1M in at $3, 100k out at $15 = 3 + 1.5
    const cost = costOf('claude-sonnet-5', { input_tokens: 1_000_000, output_tokens: 100_000 }, '2026-09-01');
    expect(cost).toBe(4.5);
  });

  it('charges a cache write at 1.25x input and a cache read at a tenth', () => {
    const write = costOf(
      'claude-haiku-4-5',
      { input_tokens: 0, output_tokens: 0, cache_creation_input_tokens: 1_000_000 },
      '2099-01-01',
    );
    const read = costOf(
      'claude-haiku-4-5',
      { input_tokens: 0, output_tokens: 0, cache_read_input_tokens: 1_000_000 },
      '2099-01-01',
    );
    expect(write).toBe(1.25);
    expect(read).toBe(0.1);
    // The whole reason the methodology prompt carries a breakpoint.
    expect(read).toBeLessThan(write / 10);
  });

  it('treats missing cache fields as zero rather than as an error', () => {
    const bare = costOf('claude-haiku-4-5', { input_tokens: 1000, output_tokens: 0 }, '2099-01-01');
    const explicit = costOf(
      'claude-haiku-4-5',
      { input_tokens: 1000, output_tokens: 0, cache_creation_input_tokens: null, cache_read_input_tokens: null },
      '2099-01-01',
    );
    expect(bare).toBe(explicit);
  });

  it('rounds to a tenth of a cent so the exported ledger is byte-stable', () => {
    const cost = costOf('claude-sonnet-5', { input_tokens: 1, output_tokens: 1 }, '2026-09-01');
    expect(String(cost)).toBe(String(Number(cost.toFixed(6))));
  });

  it('estimates a call as if the methodology prompt is already cached', () => {
    const cached = estimateCost(
      'claude-sonnet-5',
      { input_tokens: 1000, output_tokens: 500, cached_input_tokens: 2000 },
      '2026-09-01',
    );
    const uncached = estimateCost(
      'claude-sonnet-5',
      { input_tokens: 3000, output_tokens: 500 },
      '2026-09-01',
    );
    expect(cached).toBeLessThan(uncached);
  });
});

describe('estimateTokens', () => {
  it('is a stand-in for the count the API returns, not a tokenizer', () => {
    expect(estimateTokens('')).toBe(0);
    expect(estimateTokens('abcd')).toBe(1);
    expect(estimateTokens('a'.repeat(4001))).toBe(1001);
  });
});

describe('aiRunRow', () => {
  const at = new Date('2099-03-10T08:00:00.000Z');

  it('records every token the call was billed for, cached ones included', () => {
    const row = aiRunRow({
      kind: 'session_analyzer',
      model: 'claude-sonnet-5',
      usage: {
        input_tokens: 400,
        output_tokens: 900,
        cache_creation_input_tokens: 0,
        cache_read_input_tokens: 2600,
      },
      input_ref: 'session:s-1#c-naledi',
      output: { one_growth_tip: 'ask for pros and cons' },
      at,
    });

    expect(row.tokens_in).toBe(3000);
    expect(row.tokens_out).toBe(900);
    expect(row.kind).toBe('session_analyzer');
    expect(row.model).toBe('claude-sonnet-5');
    expect(row.created_at).toBe('2099-03-10T08:00:00.000Z');
    expect(row.updated_at).toBe(row.created_at);
    expect(row.cost_usd).toBeGreaterThan(0);
  });

  it('keeps the proposal auditable as JSON, and the reference as a reference', () => {
    const row = aiRunRow({
      kind: 'coherence_checker',
      model: 'claude-sonnet-5',
      usage: { input_tokens: 10, output_tokens: 10 },
      input_ref: 'content:ct-1',
      output: { verdict: 'on' },
      at,
    });
    expect(JSON.parse(row.output!)).toEqual({ verdict: 'on' });
    // The ledger names what was analysed; it does not copy it.
    expect(row.input_ref).toBe('content:ct-1');
  });

  it('nulls the output when nothing was returned', () => {
    const row = aiRunRow({
      kind: 'weekly_digest',
      model: 'claude-haiku-4-5',
      usage: { input_tokens: 1, output_tokens: 1 },
      at,
    });
    expect(row.output).toBeNull();
    expect(row.input_ref).toBeNull();
  });

  it('mints a time-ordered id from the call instant', () => {
    const first = aiRunRow({ kind: 'weekly_digest', model: 'claude-haiku-4-5', usage: { input_tokens: 1, output_tokens: 1 }, at });
    const later = aiRunRow({
      kind: 'weekly_digest',
      model: 'claude-haiku-4-5',
      usage: { input_tokens: 1, output_tokens: 1 },
      at: new Date(at.getTime() + 60_000),
    });
    expect(first.id < later.id).toBe(true);
  });
});

describe('the budget guardrail', () => {
  const now = new Date('2099-03-10T08:00:00.000Z');

  function run(cost: number, createdAt: string, kind: AiRun['kind'] = 'session_analyzer'): AiRun {
    return {
      id: `r-${createdAt}-${cost}`,
      kind,
      model: 'claude-sonnet-5',
      tokens_in: 0,
      tokens_out: 0,
      cost_usd: cost,
      created_at: createdAt,
      updated_at: createdAt,
    };
  }

  it('defaults to the §9 soft cap', () => {
    expect(DEFAULT_BUDGET_USD).toBe(15);
    expect(budgetStatus([], { now }).cap_usd).toBe(15);
  });

  it('counts only the calendar month it is reporting on', () => {
    const status = budgetStatus(
      [run(5, '2099-03-01T00:00:00.000Z'), run(9, '2099-02-28T23:59:00.000Z')],
      { now },
    );
    expect(status.month).toBe('2099-03');
    expect(status.spent_usd).toBe(5);
    expect(status.runs).toBe(1);
  });

  it('ignores soft-deleted rows', () => {
    const deleted: AiRun = { ...run(9, '2099-03-02T00:00:00.000Z'), deleted_at: '2099-03-03T00:00:00.000Z' };
    expect(budgetStatus([deleted], { now }).spent_usd).toBe(0);
  });

  it('warns at 80% and reports over past the cap', () => {
    expect(budgetStatus([run(1, '2099-03-02T00:00:00.000Z')], { now }).state).toBe('ok');
    expect(budgetStatus([run(12, '2099-03-02T00:00:00.000Z')], { now }).state).toBe('warning');
    expect(budgetStatus([run(12, '2099-03-02T00:00:00.000Z')], { now }).pct).toBe(BUDGET_WARN_PCT);
    expect(budgetStatus([run(15, '2099-03-02T00:00:00.000Z')], { now }).state).toBe('over');
    expect(budgetStatus([run(40, '2099-03-02T00:00:00.000Z')], { now }).state).toBe('over');
  });

  it('never reports negative headroom', () => {
    const status = budgetStatus([run(40, '2099-03-02T00:00:00.000Z')], { now });
    expect(status.remaining_usd).toBe(0);
    expect(status.pct).toBeGreaterThan(100);
  });

  it('treats a zero cap as ask-every-time rather than dividing by zero', () => {
    const status = budgetStatus([], { now, cap_usd: 0 });
    expect(status.pct).toBe(100);
    expect(status.state).toBe('over');
    expect(Number.isFinite(status.pct)).toBe(true);
  });

  it('says what it means in words', () => {
    expect(describeBudget(budgetStatus([run(1, '2099-03-02T00:00:00.000Z')], { now }))).toContain('$1.00');
    expect(describeBudget(budgetStatus([run(12, '2099-03-02T00:00:00.000Z')], { now }))).toContain('80%');
    expect(describeBudget(budgetStatus([run(20, '2099-03-02T00:00:00.000Z')], { now }))).toContain('ask first');
  });

  it('breaks the month down by feature, dearest first', () => {
    const byKind = spendByKind(
      [
        run(0.1, '2099-03-02T00:00:00.000Z', 'coherence_checker'),
        run(2, '2099-03-03T00:00:00.000Z', 'session_analyzer'),
        run(0.4, '2099-03-04T00:00:00.000Z', 'session_analyzer'),
        run(9, '2099-02-01T00:00:00.000Z', 'weekly_digest'),
      ],
      { now },
    );
    expect(byKind).toEqual([
      { kind: 'session_analyzer', cost_usd: 2.4, runs: 2 },
      { kind: 'coherence_checker', cost_usd: 0.1, runs: 1 },
    ]);
  });
});

describe('formatUsd', () => {
  it('keeps sub-cent figures believable', () => {
    // "$0.00" next to a call she just paid for reads as broken.
    expect(formatUsd(0.0042)).toBe('$0.0042');
    expect(formatUsd(0)).toBe('$0.00');
    expect(formatUsd(1.5)).toBe('$1.50');
    expect(formatUsd(15)).toBe('$15.00');
  });
});
