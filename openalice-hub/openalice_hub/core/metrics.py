"""Performance metrics + text tearsheet — pure stdlib."""
from __future__ import annotations
import math, statistics


def _returns(eq: list[float]) -> list[float]:
    return [(eq[i] / eq[i - 1] - 1) for i in range(1, len(eq)) if eq[i - 1]]


def compute(result: dict, ann: int = 365) -> dict:
    eq = result["equity_curve"]
    if len(eq) < 3:
        return {"error": "not enough bars"}
    rets = _returns(eq)
    total = result["final"] / result["cash0"] - 1
    n = len(eq)
    cagr = (result["final"] / result["cash0"]) ** (ann / n) - 1 if result["cash0"] else 0
    mean = statistics.mean(rets) if rets else 0
    sd = statistics.pstdev(rets) if len(rets) > 1 else 0
    downside = [r for r in rets if r < 0]
    dsd = statistics.pstdev(downside) if len(downside) > 1 else 0
    sharpe = (mean / sd * math.sqrt(ann)) if sd else 0
    sortino = (mean / dsd * math.sqrt(ann)) if dsd else 0
    # max drawdown
    peak, mdd = eq[0], 0.0
    for v in eq:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    tr = result["trades"]
    wins = [t for t in tr if t["pnl"] > 0]
    losses = [t for t in tr if t["pnl"] <= 0]
    gp = sum(t["pnl"] for t in wins)
    gl = abs(sum(t["pnl"] for t in losses))
    return {
        "total_return": total, "cagr": cagr, "sharpe": sharpe, "sortino": sortino,
        "max_drawdown": mdd, "vol_annual": sd * math.sqrt(ann),
        "num_trades": len(tr), "win_rate": (len(wins) / len(tr) if tr else 0),
        "profit_factor": min(gp / gl if gl else (99.0 if gp else 0), 99.0),
        "buy_hold_return": result["buy_hold"] / result["cash0"] - 1,
        "final": result["final"], "cash0": result["cash0"],
    }


def tearsheet(result: dict, ann: int = 365) -> str:
    m = compute(result, ann)
    if "error" in m:
        return f"tearsheet: {m['error']}"
    pct = lambda x: f"{x*100:+.2f}%"
    vs = m["total_return"] - m["buy_hold_return"]
    L = [
        "─" * 52,
        f"  {result['strategy']}  on  {result['symbol']}   ({result['bars']} bars)",
        "─" * 52,
        f"  Start equity     ${m['cash0']:,.0f}",
        f"  Final equity     ${m['final']:,.0f}",
        f"  Total return     {pct(m['total_return'])}",
        f"  Buy & hold       {pct(m['buy_hold_return'])}   (alpha {pct(vs)})",
        f"  CAGR             {pct(m['cagr'])}",
        f"  Sharpe / Sortino {m['sharpe']:.2f} / {m['sortino']:.2f}",
        f"  Max drawdown     {pct(m['max_drawdown'])}",
        f"  Annual vol       {pct(m['vol_annual'])}",
        f"  Trades           {m['num_trades']}   win-rate {m['win_rate']*100:.1f}%   PF {m['profit_factor']:.2f}",
        "─" * 52,
        "  PAPER backtest — past performance ≠ future results.",
    ]
    return "\n".join(L)
