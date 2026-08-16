/**
 * Transport — where the key lives (§7's non-negotiable rule).
 *
 * §7 says the Anthropic key sits in a Supabase Edge Function for the hosted
 * builds and the browser never sees it; §6 says Build 1 uses a key she pastes
 * into Settings on her own device. Those are two different trust models for one
 * set of prompts, so the prompts do not get to know which one they are running
 * under. Everything above this file talks to `AiTransport`; the choice is made
 * once at boot.
 *
 * The interface is also what makes the rest of this package testable without a
 * network: `packages/ai` has one integration point, and every test fakes it.
 */

import Anthropic from '@anthropic-ai/sdk';
import type { AiRun } from '@cmw/core';

import type { JsonSchema } from './contracts.js';
import type { TokenUsage } from './cost.js';
import { MODELS, type AiModelId } from './models.js';

/**
 * A system-prompt block. `cacheable` marks the breakpoint — the methodology
 * block is byte-identical across every call, so it is paid for once and read at
 * a tenth of the price thereafter.
 */
export interface SystemBlock {
  text: string;
  cacheable?: boolean;
}

export interface AiCall {
  model: AiModelId;
  system: SystemBlock[];
  user: string;
  max_tokens: number;
  schema: JsonSchema;
  /** Adaptive thinking. Silently skipped on models that predate it. */
  think?: boolean;
}

export interface AiRawResult {
  /** As reported by the API, which may differ from what was asked for. */
  model: string;
  json: unknown;
  usage: TokenUsage;
  stop_reason: string | null;
}

export interface AiTransport {
  /** Shown in Settings so she can see where her data is going. */
  readonly label: string;
  send(call: AiCall, signal?: AbortSignal): Promise<AiRawResult>;
  /** Exact pre-flight count, when the transport can reach the API to ask. */
  countTokens?(call: AiCall): Promise<number>;
}

// ── Errors ────────────────────────────────────────────────────────────────

export type AiErrorCode =
  | 'no_transport'
  | 'auth'
  | 'rate_limit'
  | 'overloaded'
  | 'refusal'
  | 'truncated'
  | 'unparseable'
  | 'contract'
  | 'network'
  | 'budget'
  | 'unknown';

/**
 * Every failure carries copy she can act on.
 *
 * The hint is part of the error rather than a lookup table in the UI because the
 * cause is the only place that knows what would actually fix it — and because
 * three surfaces would otherwise write three versions of the same sentence.
 */
export class AiError extends Error {
  /**
   * The ledger row for a call that cost money and still failed.
   *
   * Present when the API answered and billed but the answer was unusable — a
   * malformed contract, most often. The caller must persist it anyway, or the
   * budget guardrail under-reports exactly the spend she would most want to see.
   */
  readonly run?: AiRun;

  constructor(
    readonly code: AiErrorCode,
    message: string,
    readonly hint: string,
    options?: { cause?: unknown; run?: AiRun },
  ) {
    super(message, options?.cause ? { cause: options.cause } : undefined);
    this.name = 'AiError';
    if (options?.run) this.run = options.run;
  }
}

/**
 * Reads a status code without depending on the SDK's error class names.
 *
 * `instanceof Anthropic.APIError` would work today and is the documented route,
 * but this package is bundled into a file she keeps for years; a duck-typed read
 * of `status` survives an SDK reshuffle where a class check would not.
 */
function statusOf(cause: unknown): number | null {
  if (typeof cause === 'object' && cause !== null && 'status' in cause) {
    const status = (cause as { status: unknown }).status;
    if (typeof status === 'number') return status;
  }
  return null;
}

function messageOf(cause: unknown): string {
  return cause instanceof Error ? cause.message : String(cause);
}

/** Maps a transport failure onto something she can do something about. */
export function toAiError(cause: unknown): AiError {
  if (cause instanceof AiError) return cause;

  const status = statusOf(cause);

  if (status === 401 || status === 403) {
    return new AiError('auth', messageOf(cause), 'That API key was rejected. Check it in Settings — keys start with `sk-ant-`.', { cause });
  }
  if (status === 429) {
    return new AiError('rate_limit', messageOf(cause), 'Too many requests in a row. Wait a minute and try again.', { cause });
  }
  if (status === 529 || status === 503) {
    return new AiError('overloaded', messageOf(cause), 'Anthropic is busy. This usually clears in a few minutes.', { cause });
  }
  if (status !== null && status >= 500) {
    return new AiError('unknown', messageOf(cause), 'Something went wrong on the API side. Try again shortly.', { cause });
  }
  if (status === 400) {
    return new AiError('unknown', messageOf(cause), 'The request was rejected. If this keeps happening the notes may be longer than the model can hold.', { cause });
  }

  return new AiError(
    'network',
    messageOf(cause),
    'Could not reach the API. Everything else in the app works offline — only the Copilot needs a connection.',
    { cause },
  );
}

// ── Build 1 · her own key, on her own device ──────────────────────────────

export interface AnthropicTransportOptions {
  apiKey: string;
  /** Injected in tests and on hosts with their own fetch. */
  fetch?: typeof globalThis.fetch;
  baseURL?: string;
  maxRetries?: number;
}

/**
 * Calls the Messages API directly with a key she supplies.
 *
 * `dangerouslyAllowBrowser` is exactly as dangerous as the SDK says when the key
 * belongs to a server operator. Here it belongs to the person typing it in, is
 * held in her own IndexedDB, is excluded from every backup file
 * (`UNEXPORTED_SETTING_KEYS`), and never leaves her device except to Anthropic.
 * The alternative — a proxy — is what the hosted builds use, and it is not
 * available to a file she opens from her downloads folder.
 */
export function anthropicTransport(options: AnthropicTransportOptions): AiTransport {
  const client = new Anthropic({
    apiKey: options.apiKey,
    dangerouslyAllowBrowser: true,
    maxRetries: options.maxRetries ?? 2,
    ...(options.fetch ? { fetch: options.fetch } : {}),
    ...(options.baseURL ? { baseURL: options.baseURL } : {}),
  });

  function paramsFor(call: AiCall) {
    const supportsThinking = MODELS[call.model].supports_adaptive_thinking;
    return {
      model: call.model,
      max_tokens: call.max_tokens,
      system: call.system.map((block) => ({
        type: 'text' as const,
        text: block.text,
        ...(block.cacheable ? { cache_control: { type: 'ephemeral' as const } } : {}),
      })),
      messages: [{ role: 'user' as const, content: call.user }],
      output_config: { format: { type: 'json_schema' as const, schema: call.schema } },
      ...(call.think && supportsThinking ? { thinking: { type: 'adaptive' as const } } : {}),
    };
  }

  return {
    label: 'your own API key, stored on this device',

    async send(call, signal) {
      let message;
      try {
        message = await client.messages.create(paramsFor(call), signal ? { signal } : {});
      } catch (cause) {
        throw toAiError(cause);
      }

      // Checked before touching `content`: a refusal has no JSON in it, and
      // parsing first would report "unparseable" for a response that was
      // perfectly well-formed and simply declined.
      if (message.stop_reason === 'refusal') {
        throw new AiError(
          'refusal',
          'The model declined to answer.',
          'The model would not answer this one. If the notes describe something clinical, that is deliberate — the Copilot is not allowed to give medical advice.',
        );
      }
      if (message.stop_reason === 'max_tokens') {
        throw new AiError(
          'truncated',
          'The response was cut off at the token limit.',
          'The answer was too long to finish. Try again with shorter notes.',
        );
      }

      const text = message.content
        .filter((part): part is Anthropic.TextBlock => part.type === 'text')
        .map((part) => part.text)
        .join('');

      return {
        model: message.model,
        json: parseJson(text),
        stop_reason: message.stop_reason,
        usage: {
          input_tokens: message.usage.input_tokens,
          output_tokens: message.usage.output_tokens,
          cache_creation_input_tokens: message.usage.cache_creation_input_tokens,
          cache_read_input_tokens: message.usage.cache_read_input_tokens,
        },
      };
    },

    async countTokens(call) {
      const params = paramsFor(call);
      try {
        const counted = await client.messages.countTokens({
          model: params.model,
          system: params.system,
          messages: params.messages,
        });
        return counted.input_tokens;
      } catch (cause) {
        throw toAiError(cause);
      }
    },
  };
}

// ── Builds 2 and 3 · the key stays server-side ────────────────────────────

export interface ProxyTransportOptions {
  /** The Edge Function URL. It holds the key; this side never sees it. */
  endpoint: string;
  /** Her Supabase session token, so the function can refuse strangers. */
  authToken?: string;
  fetch?: typeof globalThis.fetch;
}

/**
 * The wire contract between the app and the AI proxy.
 *
 * Written here, ahead of the Edge Function that answers it, because the request
 * shape is the thing both ends must agree on and the browser side is the one
 * with a type checker pointed at it. P3's function implements this shape; the
 * body deliberately carries no key field, so a misconfigured deployment fails
 * closed rather than accepting a key from a client.
 */
export function proxyTransport(options: ProxyTransportOptions): AiTransport {
  const doFetch = options.fetch ?? globalThis.fetch;

  async function post(path: string, call: AiCall, signal?: AbortSignal): Promise<unknown> {
    let response: Response;
    try {
      response = await doFetch(`${options.endpoint}${path}`, {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          ...(options.authToken ? { authorization: `Bearer ${options.authToken}` } : {}),
        },
        body: JSON.stringify({
          model: call.model,
          system: call.system,
          user: call.user,
          max_tokens: call.max_tokens,
          schema: call.schema,
          think: call.think ?? false,
        }),
        ...(signal ? { signal } : {}),
      });
    } catch (cause) {
      throw toAiError(cause);
    }

    if (!response.ok) {
      throw toAiError(
        Object.assign(new Error(`Proxy responded ${response.status}`), { status: response.status }),
      );
    }
    return response.json();
  }

  return {
    label: 'the CoachMillaWellness server, which holds the key',

    async send(call, signal) {
      const body = await post('/analyze', call, signal);
      return readProxyResult(body);
    },

    async countTokens(call) {
      const body = await post('/count', call);
      const record = asRecord(body, 'the proxy count response');
      const count = record.input_tokens;
      if (typeof count !== 'number') {
        throw new AiError('unparseable', 'Proxy returned no token count.', 'The server answered in a shape this version does not understand.');
      }
      return count;
    },
  };
}

function readProxyResult(body: unknown): AiRawResult {
  const record = asRecord(body, 'the proxy response');
  if (record.stop_reason === 'refusal') {
    throw new AiError('refusal', 'The model declined to answer.', 'The model would not answer this one.');
  }
  const usage = asRecord(record.usage ?? {}, 'the proxy usage block');
  return {
    model: typeof record.model === 'string' ? record.model : 'unknown',
    json: record.json,
    stop_reason: typeof record.stop_reason === 'string' ? record.stop_reason : null,
    usage: {
      input_tokens: numberOr(usage.input_tokens, 0),
      output_tokens: numberOr(usage.output_tokens, 0),
      cache_creation_input_tokens: numberOr(usage.cache_creation_input_tokens, 0),
      cache_read_input_tokens: numberOr(usage.cache_read_input_tokens, 0),
    },
  };
}

function asRecord(value: unknown, what: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new AiError('unparseable', `Expected an object for ${what}.`, 'The server answered in a shape this version does not understand.');
  }
  return value as Record<string, unknown>;
}

function numberOr(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function parseJson(text: string): unknown {
  try {
    return JSON.parse(text) as unknown;
  } catch (cause) {
    throw new AiError(
      'unparseable',
      'The response was not valid JSON.',
      'The model answered in the wrong format. Trying again usually fixes it.',
      { cause },
    );
  }
}
