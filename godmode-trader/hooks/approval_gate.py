#!/usr/bin/env python3
"""GODMODE Trader approval gate: a Claude Code PreToolUse hook on MCP tools.

It stays silent for every tool that cannot open a position. For one that can (a name like
place_order, execute_order, submit_order, create_order, order_send, open_position ...),
it looks for an order that, TODAY:
  1. trader-risk passed (trader/state/risk.json, same fingerprint), and
  2. the user approved with an explicit yes for that one order (trader/state/broker.json,
     ticket.py approve), still unused (no result, decline or fill recorded since), and
  3. matches the tool call's symbol and side.
Found: "ask" (Claude Code still shows its own Allow / Deny card; the gate never says allow).
Not found, unclear, or anything goes wrong: "deny", with the reason and what to run.

Exits (close, cancel, flatten, reduce) are never blocked: getting out must always be possible.
Standard library only; reads the files of the project Claude is working in (the hook's cwd).
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "trader-core"))

ENTRY = re.compile(r"(^|_)(place|submit|create|send|execute|open|new|make|buy|sell)(_[a-z0-9]+)*_?"
                   r"(order|orders|trade|trades|position|positions)($|_)")
EXACT = {"order_send", "ordersend", "place_crypto_order", "execute_spot_order", "execute_orders_batch",
         "execute_prediction_order", "market_order", "limit_order", "buy", "sell"}
EXIT_WORDS = {"cancel", "close", "flatten", "remove", "reduce", "exit", "get", "list", "view", "show", "read",
              "preview", "suggest", "quote", "status", "history", "search", "analyze", "analyse", "help", "modify",
              "update", "edit", "set", "check", "simulate", "paper", "plan"}
SYMBOL_KEYS = ("symbol", "instrument", "asset", "coin", "ticker", "market", "pair")
SIDE_KEYS = ("side", "action", "direction", "type", "order_type", "is_buy")


def base_name(tool):
    raw = tool.split("__")[-1]
    raw = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", raw)          # placeOrder -> place_Order
    return re.sub(r"[\-\s]+", "_", raw).lower()


def is_entry_tool(tool):
    name = base_name(tool)
    if set(name.split("_")) & EXIT_WORDS:
        return False
    return name in EXACT or bool(ENTRY.search(name))


def walk(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k).lower(), v
            for kv in walk(v):
                yield kv
    elif isinstance(obj, list):
        for v in obj:
            for kv in walk(v):
                yield kv


def norm(sym):
    return re.sub(r"[^A-Z0-9]", "", str(sym).upper())


def call_symbols(tool_input):
    return {norm(v) for k, v in walk(tool_input) if any(s in k for s in SYMBOL_KEYS) and isinstance(v, str) and v.strip()}


def call_side(tool_input):
    for k, v in walk(tool_input):
        if isinstance(v, bool) and k in ("is_buy", "isbuy", "buy"):
            return "buy" if v else "sell"
        if any(s == k or k.endswith("_" + s) for s in SIDE_KEYS) and isinstance(v, str):
            t = v.lower()
            if "buy" in t or "long" in t or t == "bid":
                return "buy"
            if "sell" in t or "short" in t or t == "ask":
                return "sell"
    for k, v in walk(tool_input):
        if k in ("units", "qty", "quantity", "size", "amount") and isinstance(v, (int, float, str)):
            try:
                x = float(v)
            except ValueError:
                continue
            if x < 0:
                return "sell"
    return None


def symbol_matches(want, got_set):
    w = norm(want)
    for g in got_set:
        if g == w or (len(g) >= 3 and (w.startswith(g) or g.startswith(w))):
            return True
    return False


def decide(event):
    """(decision, reason) or (None, None) to stay out of the way."""
    tool = str(event.get("tool_name") or "")
    if not tool.startswith("mcp__") or not is_entry_tool(tool):
        return None, None
    import tradercore as tc
    cwd = event.get("cwd") or os.getcwd()
    path = lambda *p: os.path.join(cwd, "trader", *p)  # noqa: E731
    cfg = tc.load_config(path("config.json"))
    today = tc.to_local(cfg["timezone"], tc.utc_now()).date().isoformat()
    risk = tc.read_json(path("state", "risk.json"), "risk check", required=False) or {}
    state = tc.read_json(path("state", "broker.json"), "broker state", required=False) or {}
    passed = {r.get("fingerprint") for r in risk.get("results", []) if r.get("verdict") == "PASS"} \
        if risk.get("date") == today else set()
    latest = {}
    for rec in state.get("orders", []):
        if rec.get("fingerprint") and str(rec.get("date", "")) == today:
            latest[rec["fingerprint"]] = rec
    ready = [r for fp, r in latest.items() if r.get("status") == "approved" and fp in passed]
    syms, side = call_symbols(event.get("tool_input") or {}), call_side(event.get("tool_input") or {})
    how = ("Run the pack's path first: trader-budget, then trader-risk (check.py), then show the ticket and record the "
           "user's explicit yes for that one order (ticket.py approve). The gate never lets an unapproved order through.")
    if not ready:
        why = "no order is both risk-PASSED and approved by the user today"
        if risk.get("date") not in (None, today):
            why = "the last risk check is from %s, not today" % risk.get("date")
        return "deny", "GODMODE approval gate: %s (%s). %s" % (why, base_name(tool), how)
    if not syms:
        return "deny", ("GODMODE approval gate: cannot tell which symbol %s would trade, so it cannot match it to an "
                        "approved order. %s" % (base_name(tool), how))
    for r in ready:
        if symbol_matches(r.get("symbol", ""), syms) and (side is None or side == r.get("side")):
            mode = "PAPER" if cfg.get("paper", True) else "LIVE (real money)"
            return "ask", ("GODMODE approval gate: matches approved order #%s, %s (trader-risk PASS today, the user's "
                           "yes at %s). Config mode: %s. Confirm it is exactly this order before allowing it." % (
                               r.get("index"), r.get("plain") or "%s %s" % (r.get("side"), r.get("symbol")),
                               r.get("at"), mode))
    return "deny", ("GODMODE approval gate: %s on %s%s does not match any approved order today (approved: %s). %s" % (
        base_name(tool), "/".join(sorted(syms)), " (%s)" % side if side else "",
        ", ".join("%s %s" % (r.get("side"), r.get("symbol")) for r in ready), how))


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    try:
        decision, reason = decide(event)
    except Exception as e:  # fail closed: an order tool we could not verify is denied
        if is_entry_tool(str(event.get("tool_name") or "")):
            decision, reason = "deny", "GODMODE approval gate could not verify this order (%s: %s)" % (
                type(e).__name__, e)
        else:
            return 0
    if decision is None:
        return 0
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                             "permissionDecisionReason": reason}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
