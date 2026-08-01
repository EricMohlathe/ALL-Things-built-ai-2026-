/**
 * The AI proxy (§7 — "the Edge Function holds the Anthropic key server-side; the
 * browser NEVER sees it. Non-negotiable security rule").
 *
 * This is the other end of `proxyTransport` in `packages/ai/src/provider.ts`.
 * The two are a contract: the request body has no key field at all, so a
 * misconfigured deployment fails closed rather than accepting a credential from
 * a client, and there is no code path here that reads one from the request.
 *
 * Deno, not Node — this runs on Supabase Edge Functions. It deliberately calls
 * the Messages API over `fetch` rather than pulling the SDK into the edge
 * runtime: the surface used here is one POST, and the browser bundle already
 * carries the SDK for the local-key build.
 *
 * Deploy:
 *   supabase secrets set ANTHROPIC_API_KEY=sk-ant-...
 *   supabase functions deploy ai-proxy
 *
 * The key is a secret, never a committed value and never a build argument.
 */

const ANTHROPIC_URL = 'https://api.anthropic.com/v1/messages';
const ANTHROPIC_COUNT_URL = 'https://api.anthropic.com/v1/messages/count_tokens';
const ANTHROPIC_VERSION = '2023-06-01';

/**
 * Models this proxy will pay for.
 *
 * An allowlist rather than a pass-through, because here *she* is not paying per
 * call — the deployment is. Without it, anyone holding a session token could
 * request the most expensive model in the catalogue with a million-token prompt
 * and bill it to her.
 */
const ALLOWED_MODELS = new Set(['claude-opus-5', 'claude-sonnet-5', 'claude-haiku-4-5']);

/** Models that take `thinking: {type:'adaptive'}`; earlier ones 400 on it. */
const ADAPTIVE_THINKING = new Set(['claude-opus-5', 'claude-sonnet-5']);

/** Ceiling on what one call may generate, whatever the client asks for. */
const MAX_OUTPUT_TOKENS = 8000;

interface SystemBlock {
  text: string;
  cacheable?: boolean;
}

interface ProxyRequest {
  model: string;
  system: SystemBlock[];
  user: string;
  max_tokens: number;
  schema: Record<string, unknown>;
  think?: boolean;
}

function cors(origin: string | null): Record<string, string> {
  // Set ALLOWED_ORIGIN to her domain in production. Absent, the function is
  // still safe — every request must carry a valid Supabase JWT — but pinning it
  // stops another site from spending her budget through a logged-in visitor.
  const allowed = Deno.env.get('ALLOWED_ORIGIN');
  return {
    'access-control-allow-origin': allowed ?? origin ?? '*',
    'access-control-allow-headers': 'authorization, content-type',
    'access-control-allow-methods': 'POST, OPTIONS',
    vary: 'origin',
  };
}

function json(body: unknown, status: number, origin: string | null): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json', ...cors(origin) },
  });
}

/**
 * Reads and checks the request body.
 *
 * Every field is validated rather than forwarded. The schema in particular is
 * passed through to Anthropic, so it must at least be an object — and `model`
 * and `max_tokens` are the two fields that decide what a call costs.
 */
function parseBody(body: unknown): ProxyRequest | string {
  if (typeof body !== 'object' || body === null) return 'Body must be an object.';
  const source = body as Record<string, unknown>;

  const model = source.model;
  if (typeof model !== 'string' || !ALLOWED_MODELS.has(model)) {
    return `Unsupported model. Allowed: ${[...ALLOWED_MODELS].join(', ')}.`;
  }

  if (!Array.isArray(source.system) || source.system.length === 0) {
    return 'system must be a non-empty array of blocks.';
  }
  const system: SystemBlock[] = [];
  for (const block of source.system) {
    if (typeof block !== 'object' || block === null) return 'Each system block must be an object.';
    const text = (block as Record<string, unknown>).text;
    if (typeof text !== 'string' || text.length === 0) return 'Each system block needs text.';
    system.push({ text, cacheable: Boolean((block as Record<string, unknown>).cacheable) });
  }

  if (typeof source.user !== 'string' || source.user.length === 0) {
    return 'user must be a non-empty string.';
  }

  const maxTokens = source.max_tokens;
  if (typeof maxTokens !== 'number' || !Number.isFinite(maxTokens) || maxTokens <= 0) {
    return 'max_tokens must be a positive number.';
  }

  if (typeof source.schema !== 'object' || source.schema === null || Array.isArray(source.schema)) {
    return 'schema must be a JSON Schema object.';
  }

  return {
    model,
    system,
    user: source.user,
    max_tokens: Math.min(MAX_OUTPUT_TOKENS, Math.floor(maxTokens)),
    schema: source.schema as Record<string, unknown>,
    think: Boolean(source.think),
  };
}

function messagesPayload(request: ProxyRequest): Record<string, unknown> {
  return {
    model: request.model,
    max_tokens: request.max_tokens,
    system: request.system.map((block) => ({
      type: 'text',
      text: block.text,
      // The cache breakpoint the client asked for — her methodology prompt, which
      // is byte-identical on every call and so is paid for once.
      ...(block.cacheable ? { cache_control: { type: 'ephemeral' } } : {}),
    })),
    messages: [{ role: 'user', content: request.user }],
    output_config: { format: { type: 'json_schema', schema: request.schema } },
    ...(request.think && ADAPTIVE_THINKING.has(request.model)
      ? { thinking: { type: 'adaptive' } }
      : {}),
  };
}

/**
 * Confirms the caller is signed in.
 *
 * Supabase verifies the JWT before the function runs when `verify_jwt` is on,
 * which it is by default; this is the belt to that's braces, and it makes the
 * requirement legible to anyone reading the function on its own.
 */
function authorized(request: Request): boolean {
  const header = request.headers.get('authorization') ?? '';
  return header.toLowerCase().startsWith('bearer ') && header.length > 'bearer '.length;
}

Deno.serve(async (request: Request) => {
  const origin = request.headers.get('origin');

  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: cors(origin) });
  }
  if (request.method !== 'POST') {
    return json({ error: 'Use POST.' }, 405, origin);
  }
  if (!authorized(request)) {
    return json({ error: 'Sign in first.' }, 401, origin);
  }

  const apiKey = Deno.env.get('ANTHROPIC_API_KEY');
  if (!apiKey) {
    // Fails closed and says so. The one thing it must never do is look for a key
    // in the request body.
    return json({ error: 'This deployment has no Anthropic key configured.' }, 503, origin);
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'Body was not valid JSON.' }, 400, origin);
  }

  const parsed = parseBody(body);
  if (typeof parsed === 'string') return json({ error: parsed }, 400, origin);

  const path = new URL(request.url).pathname;
  const counting = path.endsWith('/count');

  const payload = messagesPayload(parsed);
  if (counting) {
    delete payload.max_tokens;
    delete payload.output_config;
    delete payload.thinking;
  }

  let upstream: Response;
  try {
    upstream = await fetch(counting ? ANTHROPIC_COUNT_URL : ANTHROPIC_URL, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': ANTHROPIC_VERSION,
      },
      body: JSON.stringify(payload),
    });
  } catch (cause) {
    return json({ error: `Could not reach Anthropic: ${String(cause)}` }, 502, origin);
  }

  if (!upstream.ok) {
    // The upstream status is forwarded so the client's error mapping — 401 to
    // "check your key", 429 to "wait a minute" — keeps working through the proxy.
    const detail = await upstream.text();
    return json({ error: `Anthropic responded ${upstream.status}`, detail }, upstream.status, origin);
  }

  const message = (await upstream.json()) as Record<string, unknown>;

  if (counting) {
    return json({ input_tokens: message.input_tokens ?? 0 }, 200, origin);
  }

  if (message.stop_reason === 'refusal') {
    return json({ stop_reason: 'refusal', model: message.model }, 200, origin);
  }

  const content = Array.isArray(message.content) ? message.content : [];
  const text = content
    .filter((part): part is { type: string; text: string } => {
      return typeof part === 'object' && part !== null && (part as { type?: string }).type === 'text';
    })
    .map((part) => part.text)
    .join('');

  let parsedJson: unknown;
  try {
    parsedJson = JSON.parse(text);
  } catch {
    return json({ error: 'The model did not return valid JSON.' }, 502, origin);
  }

  const usage = (message.usage ?? {}) as Record<string, unknown>;

  return json(
    {
      model: message.model,
      json: parsedJson,
      stop_reason: message.stop_reason ?? null,
      // Forwarded whole so the client's `ai_run` ledger records what was actually
      // billed, not what the proxy guessed.
      usage: {
        input_tokens: usage.input_tokens ?? 0,
        output_tokens: usage.output_tokens ?? 0,
        cache_creation_input_tokens: usage.cache_creation_input_tokens ?? 0,
        cache_read_input_tokens: usage.cache_read_input_tokens ?? 0,
      },
    },
    200,
    origin,
  );
});
