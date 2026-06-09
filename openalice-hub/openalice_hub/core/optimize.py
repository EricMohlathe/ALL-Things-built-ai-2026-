"""
Parameter optimizer — grid search over a strategy's parameters via real backtests.

Honesty (matches the GODMODE brief's contract):
  * every score comes from a REAL backtest on REAL data through the paper gate
  * results are IN-SAMPLE on one period — high risk of overfitting. The optimizer
    SAYS SO and reports a train/test split so you can see out-of-sample decay.
"""
from __future__ import annotations
import itertools
from . import backtest as bt, metrics as met
from ..strategies import builtin

# sensible grids per built-in strategy
GRIDS = {
    "sma_cross": {"fast": [10, 20, 30, 50], "slow": [50, 100, 150, 200]},
    "rsi2": {"n": [2, 3], "buy": [5, 10, 15], "exit": [55, 60, 70]},
    "donchian": {"entry": [10, 20, 40, 55], "exit": [5, 10, 20]},
}


def _combos(grid: dict):
    keys = list(grid)
    for vals in itertools.product(*(grid[k] for k in keys)):
        yield dict(zip(keys, vals))


# fixed exit menu (stop/tp/trail in ATR multiples); {} = strategy's own exits
EXIT_MENU = [
    {},
    {"stop_atr": 2, "tp_atr": 4, "trail_atr": 3},
    {"stop_atr": 1.5, "tp_atr": 3, "trail_atr": 2},
    {"stop_atr": 2, "trail_atr": 2.5},
    {"stop_atr": 3, "tp_atr": 6},
    {"stop_atr": 1, "tp_atr": 2, "trail_atr": 1.5},
]


def _score(strategy_name, params, bars, gate, ann, metric, exits=None):
    # skip invalid combos (e.g. fast>=slow)
    if strategy_name == "sma_cross" and params["fast"] >= params["slow"]:
        return None
    strat = builtin.make(strategy_name, **params)
    res = bt.run(strat, bars, gate=gate, **(exits or {}))
    m = met.compute(res, ann)
    if "error" in m:
        return None
    return {"params": params, "metric": m.get(metric, 0), "return": m["total_return"],
            "sharpe": m["sharpe"], "maxdd": m["max_drawdown"], "trades": m["num_trades"]}


def grid_search(strategy_name, bars, gate=None, ann=365, metric="sharpe", top=10,
                split=0.7) -> dict:
    grid = GRIDS.get(strategy_name)
    if not grid:
        raise ValueError(f"no grid for '{strategy_name}'. have: {', '.join(GRIDS)}")
    n = len(bars); cut = int(n * split)
    train, test = bars[:cut], bars[cut:]
    rows = []
    for params in _combos(grid):
        r = _score(strategy_name, params, train, gate, ann, metric)
        if r is None:
            continue
        # out-of-sample check on the held-out tail
        oos = _score(strategy_name, params, test, gate, ann, metric)
        r["oos_metric"] = oos["metric"] if oos else None
        r["oos_return"] = oos["return"] if oos else None
        rows.append(r)
    rows.sort(key=lambda x: x["metric"], reverse=True)
    return {"strategy": strategy_name, "metric": metric, "evaluated": len(rows),
            "train_bars": len(train), "test_bars": len(test), "leaderboard": rows[:top]}


def exit_search(strategy_name, params, bars, gate=None, ann=365, metric="sharpe", split=0.7):
    """Given winning strategy params, find the best ATR-exit combo (train), report OOS."""
    cut = int(len(bars) * split)
    train, test = bars[:cut], bars[cut:]
    best = None
    for ex in EXIT_MENU:
        r = _score(strategy_name, params, train, gate, ann, metric, exits=ex)
        if r is None:
            continue
        oos = _score(strategy_name, params, test, gate, ann, metric, exits=ex)
        row = {"exits": ex, "metric": r["metric"],
               "oos_metric": oos["metric"] if oos else None,
               "oos_return": oos["return"] if oos else None}
        # select on TRAIN metric (picking by OOS would leak the test set)
        if best is None or row["metric"] > best["metric"]:
            best = row
    return best


def render(result: dict) -> str:
    L = ["─" * 72,
         f"  Optimize {result['strategy']}  —  rank by {result['metric']}   "
         f"({result['evaluated']} combos, train {result['train_bars']} / test {result['test_bars']})",
         "─" * 72,
         f"  {'params':<34}{'IS '+result['metric']:>9}{'IS ret':>9}{'OOS '+result['metric']:>10}{'OOS ret':>9}{'DD':>7}{'trd':>5}"]
    for r in result["leaderboard"]:
        p = ",".join(f"{k}={v}" for k, v in r["params"].items())
        oos = f"{r['oos_metric']:.2f}" if r.get("oos_metric") is not None else "-"
        oosr = f"{r['oos_return']*100:+.0f}%" if r.get("oos_return") is not None else "-"
        L.append(f"  {p:<34}{r['metric']:>9.2f}{r['return']*100:>8.0f}%{oos:>10}{oosr:>9}"
                 f"{r['maxdd']*100:>6.0f}%{r['trades']:>5}")
    L += ["─" * 72,
          "  IS = in-sample (optimized). OOS = out-of-sample (held-out tail) — trust this more.",
          "  Big IS→OOS drop = overfit. Past performance ≠ future results."]
    return "\n".join(L)
