"""GODMODE portfolio — the validated legs combined at capital level.
Measured 2026-06-10: 50/50 Sharpe 0.92 > both solos (0.76/0.60). Diversification."""
from __future__ import annotations
import statistics, math
from . import data as D, backtest as bt, metrics as met
from .execution_gate import ExecutionGate

LEGS = [
    {"name": "deity_trend", "symbol": "GOLD", "params": {"lb": 55, "k": 0.8, "hold": 40}, "exits": {}},
    {"name": "archon_orb", "symbol": "NQ", "params": {"lb": 20, "k": 1.2, "hold": 12},
     "exits": {"stop_atr": 1.5, "tp_atr": 3, "trail_atr": 2}},
    # gm_confluence BTC joins after each quarterly re-fit (godmode-rank BTCUSDT)
]


def run(limit=1000):
    from ..strategies import builtin
    from ..strategies import godmode_setups  # noqa: register
    g = ExecutionGate(mode="paper")
    legs_out, curves = [], []
    for leg in LEGS:
        rs, src = D.resolve(leg["symbol"])
        bars = D.get_ohlcv(rs, source=src, limit=limit)
        kw = {k: v for k, v in leg["exits"].items() if v}
        r = bt.run(builtin.make(leg["name"], **leg["params"]), bars, gate=g, **kw)
        m = met.compute(r, 365 if src in ("binance", "deriv") else 252)
        legs_out.append({"name": leg["name"], "symbol": leg["symbol"], "pf": m["profit_factor"],
                         "ret": m["total_return"], "dd": m["max_drawdown"],
                         "trades": m["num_trades"], "win_rate": m["win_rate"]})
        curves.append(r["equity_curve"])
    n = min(len(c) for c in curves)
    port = [sum(c[i] / c[0] for c in curves) / len(curves) for i in range(n)]
    peak, mdd = port[0], 0.0
    for v in port:
        peak = max(peak, v); mdd = min(mdd, v / peak - 1)
    rets = [port[i] / port[i - 1] - 1 for i in range(1, n) if port[i - 1]]
    sh = (statistics.mean(rets) / statistics.pstdev(rets) * math.sqrt(252)) if len(rets) > 2 and statistics.pstdev(rets) else 0
    step = max(1, n // 200)
    return {"legs": legs_out, "portfolio": {"return": port[-1] - 1, "max_drawdown": mdd,
            "sharpe": sh, "bars": n}, "equity": port[::step],
            "note": "Equal-weight, paper. gm_confluence BTC = 3rd leg after quarterly godmode-rank re-fit. Past ≠ future."}


def render(res):
    L = ["─" * 64, "  GODMODE PORTFOLIO — validated legs, equal-weight capital", "─" * 64]
    for x in res["legs"]:
        L.append(f"  {x['name']:<14} {x['symbol']:<6} PF {x['pf']:.2f}  ret {x['ret']*100:+.0f}%  "
                 f"DD {x['dd']*100:.0f}%  WR {x['win_rate']*100:.0f}%  trd {x['trades']}")
    p = res["portfolio"]
    L += ["─" * 64,
          f"  COMBINED: return {p['return']*100:+.1f}%   maxDD {p['max_drawdown']*100:.1f}%   Sharpe {p['sharpe']:.2f}",
          "  " + res["note"]]
    return "\n".join(L)
