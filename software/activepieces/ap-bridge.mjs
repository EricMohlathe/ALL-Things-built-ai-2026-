#!/usr/bin/env node
// ap-bridge — zero-dependency CLI bridging Agent OS agents to a local
// Activepieces instance (https://github.com/activepieces/activepieces).
//
//   AP_BASE_URL  base URL of the instance (default http://localhost:8080)
//   AP_API_KEY   API key, if the instance has one configured (optional)
//
// Usage:
//   ap-bridge.mjs health                          # instance liveness
//   ap-bridge.mjs flows [limit]                   # list flows
//   ap-bridge.mjs runs  [limit]                   # list recent flow runs
//   ap-bridge.mjs trigger <flowId> ['{"k":"v"}']  # fire a webhook-triggered flow
//   ap-bridge.mjs api <METHOD> <path> ['{json}']  # raw API escape hatch

const BASE = (process.env.AP_BASE_URL ?? "http://localhost:8080").replace(/\/$/, "");
const KEY = process.env.AP_API_KEY;

async function call(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(KEY ? { Authorization: `Bearer ${KEY}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let out;
  try { out = JSON.parse(text); } catch { out = text; }
  if (!res.ok) {
    console.error(`HTTP ${res.status} ${method} ${path}`);
    console.error(typeof out === "string" ? out : JSON.stringify(out, null, 2));
    process.exit(1);
  }
  return out;
}

const [cmd, ...args] = process.argv.slice(2);
const print = (o) => console.log(typeof o === "string" ? o : JSON.stringify(o, null, 2));

switch (cmd) {
  case "health":
    print(await call("GET", "/api/v1/flags").then(() => ({ status: "ok", url: BASE })));
    break;
  case "flows":
    print(await call("GET", `/api/v1/flows?limit=${args[0] ?? 10}`));
    break;
  case "runs":
    print(await call("GET", `/api/v1/flow-runs?limit=${args[0] ?? 10}`));
    break;
  case "trigger": {
    if (!args[0]) { console.error("trigger requires a flow id"); process.exit(1); }
    const payload = args[1] ? JSON.parse(args[1]) : {};
    print(await call("POST", `/api/v1/webhooks/${args[0]}`, payload));
    break;
  }
  case "api": {
    const [method, path, body] = args;
    if (!method || !path) { console.error("api requires METHOD and path"); process.exit(1); }
    print(await call(method.toUpperCase(), path, body ? JSON.parse(body) : undefined));
    break;
  }
  default:
    console.error("commands: health | flows [limit] | runs [limit] | trigger <flowId> [json] | api <METHOD> <path> [json]");
    process.exit(cmd ? 1 : 0);
}
