/**
 * Cost ledger and the budget guardrail (§9).
 *
 * Two jobs, kept in one file because they are the same fact seen twice: what a
 * call cost, and what the month has cost so far.
 *
 * The guardrail is a *soft* cap on purpose. A hard stop at $15 would mean the
 * one Monday she actually needs the digest is the Monday it refuses — so the cap
 * warns at 80%, reports `over` past 100%, and the caller decides whether to
 * spend anyway. What it will not do is spend silently.
 */

import { toIsoDate, uuidv7, type AiRun, type AiRunKind, type IsoDate } from '@cmw/core';

import {
  CACHE_READ_MULTIPLIER,
  CACHE_WRITE_MULTIPLIER,
  rateFor,
  type AiModelId,
} from './models.js';

/**
 * Token counts as the API reports them. The cache fields are optional because a
 * proxy may not forward them and a first call has no cache read — absent is
 * treated as zero rather than as an error.
 */
export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
  cache_creation_input_tokens?: number | null;
  cache_read_input_tokens?: number | null;
}

/** §9's soft monthly cap. */
export const DEFAULT_BUDGET_USD = 15;

/** The point at which she gets a toast rather than a surprise. */
export const BUDGET_WARN_PCT = 80;

/**
 * Six decimal places — a tenth of a cent.
 *
 * Rounding at all is a deliberate choice: the ledger is exported as JSON and
 * compared byte-for-byte by gate G2, and unrounded float arithmetic produces
 * values like 0.0030000000000000005 whose text form depends on the order the
 * additions happened in. Six places is finer than any single call.
 */
function round6(value: number): number {
  return Math.round(value * 1e6) / 1e6;
}

/** What one call cost, in USD, at the rate in force on `on`. */
export function costOf(model: AiModelId, usage: TokenUsage, on: IsoDate): number {
  const rate = rateFor(model, on);
  const cacheWrite = usage.cache_creation_input_tokens ?? 0;
  const cacheRead = usage.cache_read_input_tokens ?? 0;

  const inputUsd =
    (usage.input_tokens * rate.input +
      cacheWrite * rate.input * CACHE_WRITE_MULTIPLIER +
      cacheRead * rate.input * CACHE_READ_MULTIPLIER) /
    1_000_000;

  const outputUsd = (usage.output_tokens * rate.output) / 1_000_000;

  return round6(inputUsd + outputUsd);
}

/**
 * What a call is likely to cost, before making it.
 *
 * Used for the affordance next to the button, so she can see the price of
 * curiosity. Cache reads are assumed rather than counted — the methodology
 * prompt is stable across calls, so after the first one of the day that is the
 * accurate assumption and the estimate is not inflated by re-quoting it at full
 * price.
 */
export function estimateCost(
  model: AiModelId,
  estimate: { input_tokens: number; output_tokens: number; cached_input_tokens?: number },
  on: IsoDate,
): number {
  return costOf(
    model,
    {
      input_tokens: estimate.input_tokens,
      output_tokens: estimate.output_tokens,
      cache_read_input_tokens: estimate.cached_input_tokens ?? 0,
    },
    on,
  );
}

/**
 * A very rough local token count, for the pre-flight estimate only.
 *
 * Not a tokenizer, and not presented as one — the real count comes back with
 * every response and is what the ledger records. This exists because the single
 * HTML file has to price a call *before* it makes one, and spending an API round
 * trip on `countTokens` to decide whether to spend an API round trip is the
 * wrong trade for a $0.02 question.
 */
export function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

// ── Ledger rows ───────────────────────────────────────────────────────────

export interface AiRunInput {
  kind: AiRunKind;
  model: AiModelId;
  usage: TokenUsage;
  /** What was analysed, as a reference not a copy — e.g. `session:<uuid>`. */
  input_ref?: string | null;
  /** The JSON the model returned, so a proposal stays auditable after editing. */
  output?: unknown;
  at: Date;
}

/**
 * One ledger row per call, whatever the outcome.
 *
 * Built here rather than at the call site so cost is never computed twice, and
 * so a caller cannot log a run without logging what it cost.
 */
export function aiRunRow(input: AiRunInput): AiRun {
  const created = input.at.toISOString();
  const day = toIsoDate(input.at);
  return {
    id: uuidv7({ now: input.at.getTime() }),
    kind: input.kind,
    input_ref: input.input_ref ?? null,
    output: input.output === undefined ? null : JSON.stringify(input.output),
    model: input.model,
    tokens_in:
      input.usage.input_tokens +
      (input.usage.cache_creation_input_tokens ?? 0) +
      (input.usage.cache_read_input_tokens ?? 0),
    tokens_out: input.usage.output_tokens,
    cost_usd: costOf(input.model, input.usage, day),
    created_at: created,
    updated_at: created,
  };
}

// ── Budget ────────────────────────────────────────────────────────────────

export type BudgetState = 'ok' | 'warning' | 'over';

export interface BudgetStatus {
  /** `YYYY-MM` — the window the figures cover. */
  month: string;
  spent_usd: number;
  cap_usd: number;
  /** Percentage of the cap used, rounded. Can exceed 100. */
  pct: number;
  /** Never negative — "you are $2 over" is said by `state`, not by a minus sign. */
  remaining_usd: number;
  state: BudgetState;
  runs: number;
}

export interface BudgetOptions {
  cap_usd?: number;
  now?: Date;
}

/**
 * Spend for the calendar month containing `now`.
 *
 * Calendar month, not rolling 30 days, because §9 says "per month" and because a
 * figure she can reconcile against a card statement is worth more than one that
 * is arithmetically tidier.
 */
export function budgetStatus(runs: readonly AiRun[], options: BudgetOptions = {}): BudgetStatus {
  const now = options.now ?? new Date();
  const cap = options.cap_usd ?? DEFAULT_BUDGET_USD;
  const month = toIsoDate(now).slice(0, 7);

  const inMonth = runs.filter((r) => !r.deleted_at && r.created_at.slice(0, 7) === month);
  const spent = round6(inMonth.reduce((sum, r) => sum + r.cost_usd, 0));

  // A cap of zero means "ask me every time" rather than a division by zero.
  const pct = cap > 0 ? Math.round((spent / cap) * 100) : 100;

  return {
    month,
    spent_usd: spent,
    cap_usd: cap,
    pct,
    remaining_usd: Math.max(0, round6(cap - spent)),
    state: spent >= cap ? 'over' : pct >= BUDGET_WARN_PCT ? 'warning' : 'ok',
    runs: inMonth.length,
  };
}

/** Plain-language line for the Settings screen and the 80% toast. */
export function describeBudget(status: BudgetStatus): string {
  const spent = formatUsd(status.spent_usd);
  if (status.state === 'over') {
    return `AI has cost ${spent} this month, past your ${formatUsd(status.cap_usd)} cap. Each run will ask first.`;
  }
  if (status.state === 'warning') {
    return `AI has cost ${spent} this month — ${status.pct}% of your ${formatUsd(status.cap_usd)} cap.`;
  }
  return `AI has cost ${spent} this month of a ${formatUsd(status.cap_usd)} cap.`;
}

/**
 * USD to two places, or to the nearest tenth of a cent below one cent.
 *
 * "$0.00" next to a call she just paid for reads as broken, so sub-cent figures
 * keep enough precision to be believable.
 */
export function formatUsd(value: number): string {
  if (value > 0 && value < 0.01) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(2)}`;
}

/** Monthly spend grouped by feature, for the Insights screen. */
export function spendByKind(
  runs: readonly AiRun[],
  options: BudgetOptions = {},
): Array<{ kind: AiRunKind; cost_usd: number; runs: number }> {
  const month = toIsoDate(options.now ?? new Date()).slice(0, 7);
  const totals = new Map<AiRunKind, { cost_usd: number; runs: number }>();

  for (const run of runs) {
    if (run.deleted_at || run.created_at.slice(0, 7) !== month) continue;
    const found = totals.get(run.kind) ?? { cost_usd: 0, runs: 0 };
    found.cost_usd = round6(found.cost_usd + run.cost_usd);
    found.runs += 1;
    totals.set(run.kind, found);
  }

  return [...totals.entries()]
    .map(([kind, t]) => ({ kind, ...t }))
    .sort((a, b) => b.cost_usd - a.cost_usd || a.kind.localeCompare(b.kind));
}
