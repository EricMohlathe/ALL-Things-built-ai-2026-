/**
 * The Copilot — the four §9 features, assembled.
 *
 * Everything that has to happen on every AI call happens here exactly once:
 * check the budget, build the prompt from her methodology, send, validate the
 * contract, and write a ledger row. A screen that skipped any one of those would
 * be a screen that spends her money silently, so screens do not get to call the
 * transport directly.
 *
 * Nothing in this file touches storage. Each method returns the `AiRun` row it
 * generated and the caller persists it — which is what lets the same Copilot run
 * against IndexedDB in the single file, Supabase on the web, and SQLite on the
 * desktop without knowing which.
 */

import { toIsoDate, type AiRun, type AiRunKind } from '@cmw/core';

import {
  coherenceContract,
  digestContract,
  prepContract,
  sessionAnalysisContract,
  AiContractError,
  type AiContract,
  type CoherenceVerdict,
  type PrepBrief,
  type SessionAnalysis,
  type WeeklyDigest,
} from './contracts.js';
import {
  DEFAULT_BUDGET_USD,
  aiRunRow,
  budgetStatus,
  estimateCost,
  estimateTokens,
  type BudgetStatus,
} from './cost.js';
import { MODELS, type AiModelId } from './models.js';
import {
  ANALYZER_TASK,
  COHERENCE_TASK,
  DIGEST_TASK,
  PREP_TASK,
  analyzerPrompt,
  coherencePrompt,
  digestPrompt,
  methodologyPrompt,
  prepPrompt,
  type AnalyzerInput,
  type CoherenceInput,
  type DigestInput,
  type PrepInput,
} from './prompts.js';
import { AiError, type AiCall, type AiTransport } from './provider.js';

/**
 * §9: "default model Sonnet-class (cost/quality sweet spot), Haiku-class for the
 * digest." Held as her stated preference, overridable per feature in Settings —
 * the analyzer is the one worth paying Opus for, and that is her call to make,
 * not a default to impose.
 */
export const DEFAULT_MODELS: Record<AiRunKind, AiModelId> = {
  session_analyzer: 'claude-sonnet-5',
  coherence_checker: 'claude-sonnet-5',
  weekly_digest: 'claude-haiku-4-5',
  prep_whisperer: 'claude-sonnet-5',
};

/**
 * Output ceilings, and the reasoning behind the one that looks generous.
 *
 * The analyzer runs with adaptive thinking, and thinking tokens are drawn from
 * `max_tokens` — a 3,000 ceiling would truncate a careful grading of five
 * elements mid-sentence. Output is billed on what is generated, not on the
 * ceiling, so a high limit costs nothing until it is used.
 */
const MAX_TOKENS: Record<AiRunKind, number> = {
  session_analyzer: 6000,
  coherence_checker: 1200,
  weekly_digest: 1600,
  prep_whisperer: 1200,
};

/** Only the analyzer makes a judgement against a rubric; the rest summarise. */
const THINKS: Record<AiRunKind, boolean> = {
  session_analyzer: true,
  coherence_checker: false,
  weekly_digest: false,
  prep_whisperer: false,
};

/** Rough expected output size, for the pre-flight price only. */
const EXPECTED_OUTPUT: Record<AiRunKind, number> = {
  session_analyzer: 900,
  coherence_checker: 250,
  weekly_digest: 400,
  prep_whisperer: 300,
};

export interface CopilotConfig {
  /** `null` when she has not supplied a key — the app stays fully usable. */
  transport: AiTransport | null;
  models?: Partial<Record<AiRunKind, AiModelId>>;
  /** Her wheel domains, when she has edited them (M7). */
  wheelDomains?: readonly string[];
  /**
   * The ledger, read at call time rather than passed in once. The guardrail has
   * to see spend that happened seconds ago, including in another tab.
   */
  ledger?: () => readonly AiRun[];
  budgetUsd?: number;
  /** Injectable clock, so cost-at-a-date and ledger rows are testable. */
  now?: () => Date;
}

export interface RunOptions {
  /** Set when she has answered the over-budget prompt with "run it anyway". */
  allowOverBudget?: boolean;
  model?: AiModelId;
  signal?: AbortSignal;
}

export interface CopilotResult<T> {
  data: T;
  /** Persist this. It is the only record that the money was spent. */
  run: AiRun;
}

export interface PriceEstimate {
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  /** False when the figure came from the local approximation. */
  exact: boolean;
  model: AiModelId;
}

export interface Copilot {
  /** False when no key is configured. Every screen checks this before offering. */
  readonly available: boolean;
  /** Where the data goes, in words, for Settings. */
  readonly transportLabel: string | null;
  modelFor(kind: AiRunKind): AiModelId;
  budget(): BudgetStatus;

  analyzeSession(input: AnalyzerInput, options?: RunOptions): Promise<CopilotResult<SessionAnalysis>>;
  checkCoherence(input: CoherenceInput, options?: RunOptions): Promise<CopilotResult<CoherenceVerdict>>;
  weeklyDigest(input: DigestInput, options?: RunOptions): Promise<CopilotResult<WeeklyDigest>>;
  prepBrief(input: PrepInput, options?: RunOptions): Promise<CopilotResult<PrepBrief>>;

  /** Instant, approximate. For the line beside the button. */
  estimate(kind: AiRunKind, userPrompt: string, options?: RunOptions): PriceEstimate;
  /** Exact, one API round trip. For a pre-flight before a large paste. */
  priceCheck(kind: AiRunKind, userPrompt: string, options?: RunOptions): Promise<PriceEstimate>;
}

export function createCopilot(config: CopilotConfig): Copilot {
  const clock = config.now ?? (() => new Date());
  const methodology = methodologyPrompt(
    config.wheelDomains ? { wheelDomains: config.wheelDomains } : {},
  );

  function modelFor(kind: AiRunKind, override?: AiModelId): AiModelId {
    return override ?? config.models?.[kind] ?? DEFAULT_MODELS[kind];
  }

  function budget(): BudgetStatus {
    return budgetStatus(config.ledger?.() ?? [], {
      cap_usd: config.budgetUsd ?? DEFAULT_BUDGET_USD,
      now: clock(),
    });
  }

  function transportOrThrow(): AiTransport {
    if (!config.transport) {
      throw new AiError(
        'no_transport',
        'No AI transport configured.',
        'Add your Anthropic API key in Settings to switch the Copilot on. Everything else works without it.',
      );
    }
    return config.transport;
  }

  function callFor(kind: AiRunKind, task: string, user: string, model: AiModelId, schema: AiCall['schema']): AiCall {
    return {
      model,
      // Two blocks, and the breakpoint is on the first: her methodology is
      // identical across all four features, so one cache entry serves them all.
      system: [
        { text: methodology, cacheable: true },
        { text: task },
      ],
      user,
      max_tokens: MAX_TOKENS[kind],
      schema,
      think: THINKS[kind] && MODELS[model].supports_adaptive_thinking,
    };
  }

  /**
   * One path for all four features.
   *
   * The ledger row is built before the contract is validated on purpose. A
   * response that fails validation was still billed, and an error that loses that
   * row would make the budget guardrail lie in the one direction that matters.
   */
  async function run<T>(
    kind: AiRunKind,
    contract: AiContract<T>,
    task: string,
    user: string,
    inputRef: string | null,
    options: RunOptions | undefined,
  ): Promise<CopilotResult<T>> {
    const transport = transportOrThrow();
    const status = budget();

    if (status.state === 'over' && !options?.allowOverBudget) {
      throw new AiError(
        'budget',
        `Monthly AI spend is ${status.spent_usd} of a ${status.cap_usd} cap.`,
        `You have used ${status.pct}% of this month's AI budget. Run it anyway, or raise the cap in Settings.`,
      );
    }

    const model = modelFor(kind, options?.model);
    const call = callFor(kind, task, user, model, contract.schema);
    const raw = await transport.send(call, options?.signal);

    const runRow = aiRunRow({
      kind,
      model,
      usage: raw.usage,
      input_ref: inputRef,
      output: raw.json,
      at: clock(),
    });

    try {
      return { data: contract.validate(raw.json), run: runRow };
    } catch (cause) {
      if (cause instanceof AiContractError) {
        throw new AiError(
          'contract',
          cause.message,
          'The model answered in an unexpected shape. Trying again usually fixes it — this run is still on your ledger because it was billed.',
          { cause, run: runRow },
        );
      }
      throw cause;
    }
  }

  function estimate(kind: AiRunKind, userPrompt: string, options?: RunOptions): PriceEstimate {
    const model = modelFor(kind, options?.model);
    const task = TASKS[kind];
    const inputTokens = estimateTokens(`${task}\n${userPrompt}`);
    const outputTokens = EXPECTED_OUTPUT[kind];
    return {
      input_tokens: inputTokens,
      output_tokens: outputTokens,
      exact: false,
      model,
      cost_usd: estimateCost(
        model,
        {
          input_tokens: inputTokens,
          output_tokens: outputTokens,
          // The methodology block is assumed to be a cache hit, which it is on
          // every call but the first of the window.
          cached_input_tokens: estimateTokens(methodology),
        },
        toIsoDate(clock()),
      ),
    };
  }

  return {
    get available() {
      return config.transport !== null;
    },
    get transportLabel() {
      return config.transport?.label ?? null;
    },
    modelFor: (kind) => modelFor(kind),
    budget,

    analyzeSession(input, options) {
      return run(
        'session_analyzer',
        sessionAnalysisContract(input.session.framework),
        ANALYZER_TASK,
        analyzerPrompt(input),
        `session:${input.session.id}#${input.coachee.id}`,
        options,
      );
    },

    checkCoherence(input, options) {
      return run(
        'coherence_checker',
        coherenceContract(),
        COHERENCE_TASK,
        coherencePrompt(input),
        `content:${input.item.id}`,
        options,
      );
    },

    weeklyDigest(input, options) {
      return run(
        'weekly_digest',
        digestContract(),
        DIGEST_TASK,
        digestPrompt(input),
        `week:${input.weekOf}`,
        options,
      );
    },

    prepBrief(input, options) {
      return run(
        'prep_whisperer',
        prepContract(),
        PREP_TASK,
        prepPrompt(input),
        `prep:${input.coachee.id}@${input.today}`,
        options,
      );
    },

    estimate,

    async priceCheck(kind, userPrompt, options) {
      const rough = estimate(kind, userPrompt, options);
      const transport = config.transport;
      if (!transport?.countTokens) return rough;

      const model = rough.model;
      const call = callFor(kind, TASKS[kind], userPrompt, model, EMPTY_SCHEMA);
      const inputTokens = await transport.countTokens(call);
      return {
        ...rough,
        input_tokens: inputTokens,
        exact: true,
        cost_usd: estimateCost(
          model,
          { input_tokens: inputTokens, output_tokens: rough.output_tokens },
          toIsoDate(clock()),
        ),
      };
    },
  };
}

const TASKS: Record<AiRunKind, string> = {
  session_analyzer: ANALYZER_TASK,
  coherence_checker: COHERENCE_TASK,
  weekly_digest: DIGEST_TASK,
  prep_whisperer: PREP_TASK,
};

/**
 * `countTokens` prices the prompt, not the answer, so the schema it is given is
 * irrelevant to the count — and passing the real one would mean threading a
 * framework through a pricing call that has no opinion about frameworks.
 */
const EMPTY_SCHEMA = { type: 'object' } as const;
