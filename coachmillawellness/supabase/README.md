# Supabase — the server side

Two things live here, and only one of them is built yet.

## `functions/ai-proxy` — built

The other end of `proxyTransport` in `packages/ai/src/provider.ts`. §7 makes this
non-negotiable: **the Edge Function holds the Anthropic key, and the browser
never sees it.**

The two sides are a contract, and the contract's safety property is an absence —
the request body has no key field, and there is no code path in the function that
reads one from a request. A misconfigured deployment answers 503 rather than
quietly accepting a credential from a client.

```bash
supabase secrets set ANTHROPIC_API_KEY=sk-ant-...
supabase secrets set ALLOWED_ORIGIN=https://coachmillawellness.com
supabase functions deploy ai-proxy
```

Then point the app at it — `ai_proxy_endpoint` in settings — and the same four
Copilot features run with no key on the device at all.

What the function does beyond forwarding:

- **Model allowlist.** On this path the deployment pays, not her. Without the
  list, anyone holding a session token could ask for the dearest model with a
  million-token prompt and bill it to her.
- **`max_tokens` ceiling**, for the same reason.
- **Capability guard.** `thinking: adaptive` is omitted for models that predate
  it, so a client asking for it against Haiku gets an answer rather than a 400.
- **Upstream status forwarding**, so the client's error mapping — 401 to "check
  your key", 429 to "wait a minute" — keeps working through the proxy.

This directory is **Deno**, not Node. It is deliberately outside every
`tsconfig.json` in the monorepo: `deno check` validates it, and pointing the
workspace `tsc` at Deno globals would only produce noise. It pulls in no SDK —
the surface it needs is one POST, and the browser bundle already carries the SDK
for the local-key build.

## `migrations/` — not built yet

The §3.1 schema as Postgres, with RLS `owner_id = auth.uid()` on every table.
That lands with `apps/web` in P3, because a schema with no application to run
against it cannot be verified, and an unverified migration is worse than none.

Two things are already decided and should not be re-litigated when it is written:

- **`updated_at` drives sync.** The merge rule is written and property-tested in
  `packages/data/src/sync.ts`, and `MemoryRemote` in that file is the executable
  specification the Postgres side has to match — last write wins on `updated_at`,
  ties broken by canonical JSON so two devices independently pick the same
  winner.
- **The AI ledger is a normal table.** `ai_run` rows sync like everything else,
  which is what lets the budget guardrail see spend from her phone on her laptop.
