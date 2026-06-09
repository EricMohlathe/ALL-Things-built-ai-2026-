"""
Prop-firm challenge simulator — evaluate a strategy's equity curve against the
PUBLIC rules of funded-account challenges (approximate; firms change rules —
verify on their site before paying for an eval).

Rules modeled per firm: profit target %, max daily loss %, max total drawdown %
(static from start or trailing from peak), minimum trading days.
"""
from __future__ import annotations

FIRMS = {
    "ftmo":     {"account": 100_000, "target": 0.10, "daily_loss": 0.05, "max_dd": 0.10, "dd_type": "static",   "min_days": 4,
                 "note": "FTMO Challenge ph.1 (approx public rules)"},
    "ftmo-v":   {"account": 100_000, "target": 0.05, "daily_loss": 0.05, "max_dd": 0.10, "dd_type": "static",   "min_days": 4,
                 "note": "FTMO Verification ph.2"},
    "topstep":  {"account": 50_000,  "target": 0.06, "daily_loss": 0.02, "max_dd": 0.04, "dd_type": "trailing", "min_days": 2,
                 "note": "Topstep 50K Combine (approx: $3k target, $1k DLL, $2k trailing)"},
    "apex":     {"account": 50_000,  "target": 0.06, "daily_loss": None, "max_dd": 0.05, "dd_type": "trailing", "min_days": 7,
                 "note": "Apex 50K (approx: $3k target, $2.5k trailing, no DLL)"},
    "fundednext": {"account": 100_000, "target": 0.10, "daily_loss": 0.05, "max_dd": 0.10, "dd_type": "static", "min_days": 5,
                 "note": "FundedNext Stellar ph.1 (approx)"},
}


def evaluate(equity: list[float], firm: str = "ftmo") -> dict:
    """equity = backtest equity curve starting at the firm's account size,
    one point per bar (daily bars => daily checks)."""
    f = FIRMS[firm]
    acct = equity[0]
    target = acct * (1 + f["target"])
    peak = acct
    trade_days = 0
    events = []
    for day, eq in enumerate(equity):
        prev = equity[day - 1] if day else acct
        if abs(eq - prev) > 1e-9:
            trade_days += 1
        # daily loss
        if f["daily_loss"] and (prev - eq) > acct * f["daily_loss"]:
            return {"result": "FAIL", "rule": f"daily loss limit ({f['daily_loss']*100:.0f}%)",
                    "day": day, "equity": eq, "firm": f}
        # drawdown
        peak = max(peak, eq)
        floor = (acct * (1 - f["max_dd"])) if f["dd_type"] == "static" else (peak - acct * f["max_dd"])
        if eq < floor:
            return {"result": "FAIL", "rule": f"max drawdown ({f['max_dd']*100:.0f}% {f['dd_type']})",
                    "day": day, "equity": eq, "firm": f}
        # target
        if eq >= target and trade_days >= f["min_days"]:
            return {"result": "PASS", "day": day, "equity": eq,
                    "trade_days": trade_days, "firm": f}
    return {"result": "INCOMPLETE", "rule": "target not reached in period",
            "day": len(equity) - 1, "equity": equity[-1], "firm": f}


def rolling_pass_rate(equity: list[float], firm: str = "ftmo", window: int = 90, step: int = 30) -> dict:
    """Evaluate the eval rules over every rolling `window`-bar slice (real evals
    are 30-90 days, not a decade). Returns pass/fail/incomplete counts."""
    out = {"pass": 0, "fail": 0, "incomplete": 0, "windows": 0}
    f = FIRMS[firm]; acct = f["account"]
    for s in range(0, max(1, len(equity) - window), step):
        seg = equity[s:s + window]
        base = seg[0]
        scaled = [acct * (e / base) for e in seg]   # restart each window at account size
        r = evaluate(scaled, firm)
        out[r["result"].lower()] += 1
        out["windows"] += 1
    out["pass_rate"] = out["pass"] / out["windows"] if out["windows"] else 0.0
    return out


def render(r: dict, strategy: str, symbol: str) -> str:
    f = r["firm"]
    icon = {"PASS": "✅", "FAIL": "❌", "INCOMPLETE": "⏳"}[r["result"]]
    L = ["─" * 60,
         f"  Prop-firm eval — {strategy} on {symbol}",
         f"  {f['note']}  (${f['account']:,})",
         "─" * 60,
         f"  {icon} {r['result']}" + (f" — broke: {r['rule']}" if r.get("rule") and r["result"] != "PASS" else ""),
         f"  day {r['day']}, equity ${r['equity']:,.0f}"]
    if r["result"] == "PASS":
        L.append(f"  trading days used: {r['trade_days']}")
    L += ["─" * 60,
          "  Approximate PUBLIC rules — verify current rules on the firm's site.",
          "  A pass here is a paper simulation, not a funded account."]
    return "\n".join(L)
