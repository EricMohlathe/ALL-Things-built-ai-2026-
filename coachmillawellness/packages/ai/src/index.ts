/**
 * @cmw/ai — the AI Copilot (§9 / M6).
 *
 * Her methodology is the standard the model is held to, and it is read from
 * `@cmw/core` rather than restated here. The transport is injected, so the same
 * four features run with a key she pastes into the offline file or behind a
 * server-side proxy on the web, with no prompt written twice.
 *
 * The app is fully usable with none of this configured. That is the point of the
 * shape: `Copilot.available` is false, screens hide the buttons, and nothing
 * degrades.
 */

export {
  MODELS,
  MODEL_IDS,
  CACHE_READ_MULTIPLIER,
  CACHE_WRITE_MULTIPLIER,
  isAiModelId,
  rateFor,
  type AiModelId,
  type ModelInfo,
  type Rate,
} from './models.js';

export {
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
  type AiRunInput,
  type BudgetOptions,
  type BudgetState,
  type BudgetStatus,
  type TokenUsage,
} from './cost.js';

export {
  AiContractError,
  coherenceContract,
  digestContract,
  prepContract,
  sessionAnalysisContract,
  type AiContract,
  type AnalyzedChecklist,
  type AnalyzedElement,
  type CoherenceVerdict,
  type CoherenceVerdictLevel,
  type DigestClient,
  type JsonSchema,
  type PrepBrief,
  type SessionAnalysis,
  type SuggestedAction,
  type WeeklyDigest,
} from './contracts.js';

export {
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
  type MethodologyOptions,
  type PrepInput,
} from './prompts.js';

export { latestRun, type StoredRun } from './ledger.js';

export { promptName, promptNames, scrubNotes } from './redact.js';

export {
  AiError,
  anthropicTransport,
  proxyTransport,
  toAiError,
  type AiCall,
  type AiErrorCode,
  type AiRawResult,
  type AiTransport,
  type AnthropicTransportOptions,
  type ProxyTransportOptions,
  type SystemBlock,
} from './provider.js';

export {
  DEFAULT_MODELS,
  createCopilot,
  type Copilot,
  type CopilotConfig,
  type CopilotResult,
  type PriceEstimate,
  type RunOptions,
} from './copilot.js';
