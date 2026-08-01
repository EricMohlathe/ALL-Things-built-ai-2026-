import type { AiRun } from '@cmw/core';
import { buildDeck } from '@cmw/core';
import { describe, expect, it, vi } from 'vitest';

import { DEFAULT_MODELS, createCopilot } from '../copilot.js';
import { AiError, type AiCall, type AiRawResult, type AiTransport } from '../provider.js';
import {
  NOW,
  TODAY,
  action,
  analysisFixture,
  coherenceFixture,
  content,
  digestFixture,
  goal,
  naledi,
  pillar,
  prepFixture,
  session,
  thabo,
  wheel,
} from './fixtures.js';

/**
 * A transport that never touches the network.
 *
 * `packages/ai` has exactly one integration point, which is what makes every
 * behaviour below testable as a pure function of a recorded call.
 */
function fakeTransport(
  reply: unknown,
  overrides: Partial<AiRawResult> = {},
): AiTransport & { calls: AiCall[] } {
  const calls: AiCall[] = [];
  return {
    calls,
    label: 'a test double',
    send(call) {
      calls.push(call);
      return Promise.resolve({
        model: call.model,
        json: reply,
        stop_reason: 'end_turn',
        usage: { input_tokens: 200, output_tokens: 400, cache_read_input_tokens: 2600 },
        ...overrides,
      });
    },
  };
}

const analyzerInput = {
  session,
  coachee: naledi,
  participants: [naledi],
  goals: [goal],
  notes: 'She named Health at a 3.',
  wheel,
  openActions: [action],
};

function copilotWith(transport: AiTransport | null, ledger: AiRun[] = [], budgetUsd?: number) {
  return createCopilot({
    transport,
    ledger: () => ledger,
    now: () => NOW,
    ...(budgetUsd === undefined ? {} : { budgetUsd }),
  });
}

describe('createCopilot', () => {
  it('reports itself unavailable with no key, without throwing', () => {
    // The app has to be fully usable with the Copilot switched off — every screen
    // reads `available` before it offers a button.
    const copilot = copilotWith(null);
    expect(copilot.available).toBe(false);
    expect(copilot.transportLabel).toBeNull();
  });

  it('refuses to run with no transport, and says what would fix it', async () => {
    const copilot = copilotWith(null);
    await expect(copilot.analyzeSession(analyzerInput)).rejects.toMatchObject({
      code: 'no_transport',
      hint: expect.stringContaining('Settings'),
    });
  });

  it('uses the §9 default models, Haiku for the digest', () => {
    const copilot = copilotWith(fakeTransport({}));
    expect(DEFAULT_MODELS.weekly_digest).toBe('claude-haiku-4-5');
    expect(copilot.modelFor('session_analyzer')).toBe('claude-sonnet-5');
    expect(copilot.modelFor('weekly_digest')).toBe('claude-haiku-4-5');
  });

  it('honours a per-feature model override from Settings', () => {
    const copilot = createCopilot({
      transport: fakeTransport({}),
      models: { session_analyzer: 'claude-opus-5' },
      now: () => NOW,
    });
    expect(copilot.modelFor('session_analyzer')).toBe('claude-opus-5');
    expect(copilot.modelFor('coherence_checker')).toBe('claude-sonnet-5');
  });
});

describe('analyzeSession', () => {
  it('returns the parsed analysis and a ledger row for the spend', async () => {
    const transport = fakeTransport(analysisFixture());
    const { data, run } = await copilotWith(transport).analyzeSession(analyzerInput);

    expect(data.elements).toHaveLength(4);
    expect(data.checklist.smarter_met).toBe('fail');
    expect(run.kind).toBe('session_analyzer');
    expect(run.model).toBe('claude-sonnet-5');
    expect(run.tokens_in).toBe(2800);
    expect(run.tokens_out).toBe(400);
    expect(run.cost_usd).toBeGreaterThan(0);
    expect(run.input_ref).toBe('session:s-1#c-naledi');
  });

  it('puts the cache breakpoint on the methodology block only', async () => {
    const transport = fakeTransport(analysisFixture());
    await copilotWith(transport).analyzeSession(analyzerInput);

    const [call] = transport.calls;
    expect(call!.system).toHaveLength(2);
    expect(call!.system[0]!.cacheable).toBe(true);
    expect(call!.system[1]!.cacheable).toBeUndefined();
    // Her methodology first, the task second — the stable block is what gets cached.
    expect(call!.system[0]!.text).toContain('Her frameworks');
    expect(call!.system[1]!.text).toContain('Session Analyzer');
  });

  it('sends the framework-specific schema', async () => {
    const transport = fakeTransport(analysisFixture());
    await copilotWith(transport).analyzeSession(analyzerInput);
    const schema = JSON.stringify(transport.calls[0]!.schema);
    expect(schema).toContain('options');
    expect(schema).not.toContain('take_action');
  });

  it('asks for adaptive thinking, since it is grading against a rubric', async () => {
    const transport = fakeTransport(analysisFixture());
    await copilotWith(transport).analyzeSession(analyzerInput);
    expect(transport.calls[0]!.think).toBe(true);
  });

  it('never asks a pre-4.6 model to think, because that is a 400', async () => {
    const transport = fakeTransport(analysisFixture());
    await copilotWith(transport).analyzeSession(analyzerInput, { model: 'claude-haiku-4-5' });
    expect(transport.calls[0]!.model).toBe('claude-haiku-4-5');
    expect(transport.calls[0]!.think).toBe(false);
  });

  it('keeps the ledger row when the response fails the contract', async () => {
    // The call was billed. Losing the row would make the guardrail under-report
    // exactly the spend she would most want to see.
    const transport = fakeTransport({ elements: 'all good' });
    try {
      await copilotWith(transport).analyzeSession(analyzerInput);
      expect.unreachable('should have thrown');
    } catch (error) {
      expect(error).toBeInstanceOf(AiError);
      const failure = error as AiError;
      expect(failure.code).toBe('contract');
      expect(failure.run?.cost_usd).toBeGreaterThan(0);
      expect(failure.run?.kind).toBe('session_analyzer');
    }
  });

  it('passes an abort signal straight through', async () => {
    // Parameters are declared so `mock.calls` is typed as the pair the transport
    // actually receives — a bare `vi.fn(() => …)` types them away entirely.
    const send = vi.fn((_call: AiCall, _signal?: AbortSignal) =>
      Promise.resolve<AiRawResult>({
        model: 'claude-sonnet-5',
        json: analysisFixture(),
        stop_reason: 'end_turn',
        usage: { input_tokens: 1, output_tokens: 1 },
      }),
    );
    const controller = new AbortController();
    const copilot = copilotWith({ label: 'x', send });
    await copilot.analyzeSession(analyzerInput, { signal: controller.signal });
    expect(send.mock.calls[0]![1]).toBe(controller.signal);
  });
});

describe('the other three features', () => {
  it('checks coherence against the pillar', async () => {
    const transport = fakeTransport(coherenceFixture());
    const { data, run } = await copilotWith(transport).checkCoherence({
      item: content,
      pillar,
      recent: [],
    });
    expect(data.verdict).toBe('on');
    expect(run.input_ref).toBe('content:ct-1');
    expect(transport.calls[0]!.think).toBe(false);
  });

  it('writes the weekly digest on the cheap model', async () => {
    const deck = buildDeck({
      coachees: [naledi, thabo],
      sessions: [session],
      actions: [action],
      content: [content],
      now: TODAY,
      hour: 7,
    });
    const transport = fakeTransport(digestFixture());
    const { data, run } = await copilotWith(transport).weeklyDigest({
      deck,
      coachees: [naledi, thabo],
      weekOf: '2099-03-09',
    });
    expect(data.focus_sentence).toContain('reviews slipped');
    expect(run.model).toBe('claude-haiku-4-5');
    expect(run.input_ref).toBe('week:2099-03-09');
  });

  it('writes the prep brief', async () => {
    const transport = fakeTransport(prepFixture());
    const { data, run } = await copilotWith(transport).prepBrief({
      coachee: naledi,
      framework: 'GROW',
      lastSession: session,
      today: TODAY,
    });
    expect(data.recap_3_lines).toHaveLength(3);
    expect(run.input_ref).toBe('prep:c-naledi@2099-03-10');
  });
});

describe('the budget guardrail', () => {
  function spent(cost: number): AiRun[] {
    return [
      {
        id: 'r-1',
        kind: 'session_analyzer',
        model: 'claude-sonnet-5',
        tokens_in: 0,
        tokens_out: 0,
        cost_usd: cost,
        created_at: '2099-03-02T00:00:00.000Z',
        updated_at: '2099-03-02T00:00:00.000Z',
      },
    ];
  }

  it('reports the month as the copilot sees it', () => {
    const copilot = copilotWith(fakeTransport({}), spent(6));
    expect(copilot.budget()).toMatchObject({ month: '2099-03', spent_usd: 6, state: 'ok' });
  });

  it('runs while merely warning', async () => {
    const transport = fakeTransport(analysisFixture());
    const copilot = copilotWith(transport, spent(13));
    expect(copilot.budget().state).toBe('warning');
    await expect(copilot.analyzeSession(analyzerInput)).resolves.toBeDefined();
  });

  it('stops at the cap and offers the choice rather than making it', async () => {
    const transport = fakeTransport(analysisFixture());
    const copilot = copilotWith(transport, spent(15.5));
    await expect(copilot.analyzeSession(analyzerInput)).rejects.toMatchObject({
      code: 'budget',
      hint: expect.stringContaining('anyway'),
    });
    expect(transport.calls).toHaveLength(0);
  });

  it('spends anyway once she has said so', async () => {
    const transport = fakeTransport(analysisFixture());
    const copilot = copilotWith(transport, spent(15.5));
    await expect(
      copilot.analyzeSession(analyzerInput, { allowOverBudget: true }),
    ).resolves.toBeDefined();
    expect(transport.calls).toHaveLength(1);
  });

  it('reads the ledger at call time, not at construction', async () => {
    // Spend from another tab, or from the call she made ten seconds ago, has to
    // count — so the ledger is a function, not a snapshot.
    const ledger: AiRun[] = [];
    const copilot = createCopilot({
      transport: fakeTransport(analysisFixture()),
      ledger: () => ledger,
      now: () => NOW,
    });
    expect(copilot.budget().state).toBe('ok');
    ledger.push(...spent(20));
    expect(copilot.budget().state).toBe('over');
  });

  it('honours a raised cap', () => {
    expect(copilotWith(fakeTransport({}), spent(20), 50).budget().state).toBe('ok');
  });
});

describe('price estimates', () => {
  it('prices a call before making it, and says it is approximate', () => {
    const copilot = copilotWith(fakeTransport({}));
    const estimate = copilot.estimate('session_analyzer', 'a'.repeat(4000));
    expect(estimate.exact).toBe(false);
    expect(estimate.input_tokens).toBeGreaterThan(1000);
    expect(estimate.cost_usd).toBeGreaterThan(0);
    expect(estimate.model).toBe('claude-sonnet-5');
  });

  it('prefers the API count when the transport can ask', async () => {
    const transport: AiTransport = {
      label: 'counting double',
      send: () => Promise.reject(new Error('not used')),
      countTokens: () => Promise.resolve(4321),
    };
    const exact = await copilotWith(transport).priceCheck('coherence_checker', 'short prompt');
    expect(exact.exact).toBe(true);
    expect(exact.input_tokens).toBe(4321);
  });

  it('falls back to the approximation when it cannot', async () => {
    const rough = await copilotWith(fakeTransport({})).priceCheck('coherence_checker', 'short');
    expect(rough.exact).toBe(false);
  });

  it('returns the approximation rather than throwing with no transport', async () => {
    const estimate = await copilotWith(null).priceCheck('weekly_digest', 'anything');
    expect(estimate.exact).toBe(false);
    expect(estimate.model).toBe('claude-haiku-4-5');
  });
});
