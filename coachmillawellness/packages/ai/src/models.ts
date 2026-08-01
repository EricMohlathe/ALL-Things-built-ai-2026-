/**
 * Model catalogue and price list (§9).
 *
 * The prices live here as data rather than in the cost function because they are
 * the one part of this package with an expiry date: rates change, and a
 * promotional rate that has lapsed would quietly under-report every figure the
 * budget guardrail shows her. `rateFor()` therefore takes a date and the intro
 * window is explicit.
 *
 * `supports_adaptive_thinking` is not trivia. Adaptive thinking replaced
 * `budget_tokens` on 4.6-and-later models, and sending the wrong one is a 400
 * rather than a graceful degrade — so the capability travels with the model and
 * the transport reads it, which means changing the default model in Settings
 * cannot produce a failed call.
 */

import type { IsoDate } from '@cmw/core';

/**
 * The models offered in Settings. Deliberately three, not the full catalogue:
 * she is choosing a cost/quality trade-off, not shopping.
 */
export type AiModelId = 'claude-opus-5' | 'claude-sonnet-5' | 'claude-haiku-4-5';

/** USD per million tokens. */
export interface Rate {
  input: number;
  output: number;
}

export interface ModelInfo {
  id: AiModelId;
  label: string;
  /** One line she can decide from without knowing what a token is. */
  blurb: string;
  context_tokens: number;
  standard: Rate;
  /** Promotional rate and the last day it applies, inclusive. */
  intro?: { rate: Rate; until: IsoDate };
  /** 4.6-and-later take `thinking: {type:'adaptive'}`; earlier models do not. */
  supports_adaptive_thinking: boolean;
}

export const MODELS: Record<AiModelId, ModelInfo> = {
  'claude-opus-5': {
    id: 'claude-opus-5',
    label: 'Opus 5',
    blurb: 'The most careful reader of a session. Roughly five times the cost of Sonnet.',
    context_tokens: 1_000_000,
    standard: { input: 5, output: 25 },
    supports_adaptive_thinking: true,
  },
  'claude-sonnet-5': {
    id: 'claude-sonnet-5',
    label: 'Sonnet 5',
    blurb: 'The default. Strong judgement at a price a solo practice can run monthly.',
    context_tokens: 1_000_000,
    standard: { input: 3, output: 15 },
    intro: { rate: { input: 2, output: 10 }, until: '2026-08-31' },
    supports_adaptive_thinking: true,
  },
  'claude-haiku-4-5': {
    id: 'claude-haiku-4-5',
    label: 'Haiku 4.5',
    blurb: 'Fast and cheap. Enough for the Monday digest, which summarises rather than judges.',
    context_tokens: 200_000,
    standard: { input: 1, output: 5 },
    supports_adaptive_thinking: false,
  },
};

export const MODEL_IDS: AiModelId[] = ['claude-sonnet-5', 'claude-opus-5', 'claude-haiku-4-5'];

export function isAiModelId(value: unknown): value is AiModelId {
  return typeof value === 'string' && value in MODELS;
}

/**
 * The rate in force on a given day.
 *
 * `on` is a calendar date rather than an instant because the intro window is
 * published as a date, and comparing ISO date strings is exact where a timezone
 * conversion would introduce an off-by-one at the boundary.
 */
export function rateFor(model: AiModelId, on: IsoDate): Rate {
  const info = MODELS[model];
  if (info.intro && on <= info.intro.until) return info.intro.rate;
  return info.standard;
}

/**
 * Cache pricing multipliers against the input rate.
 *
 * A cache write costs a quarter more than a fresh read; a cache hit costs a
 * tenth. Her methodology prompt is identical on every call, so once it is cached
 * the recurring cost of "grades against Appendix A" is a rounding error — which
 * is the whole reason the system prompt carries a cache breakpoint.
 */
export const CACHE_WRITE_MULTIPLIER = 1.25;
export const CACHE_READ_MULTIPLIER = 0.1;
