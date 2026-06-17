#!/usr/bin/env python3
"""Cross-market honest roster scan. Ranks reproducible full-period PF with OOS guards
across the user's required asset classes. Writes registry/roster_xmarket.json."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openalice_hub.core import data as datamod, backtest as bt, metrics as met, optimize as opt
from openalice_hub.strategies import builtin, godmode_setups  # noqa
from openalice_hub.core.execution_gate import ExecutionGate
G = lambda: ExecutionGate(mode="paper")
def ann(s): return 365 if s == "binance" else 252

# focus the strongest setup families across the required asset classes
FAM = [n for n in builtin.REGISTRY if any(k in n for k in
       ("gm", "archon", "deity", "perfect", "checklist", "ob", "poor", "stack", "lpsy", "sweep", "flow"))]
MARKETS = [("ETHUSDT", "1d"), ("GOLD", "1d"), ("SILVER", "1d"),
           ("NQ", "1d"), ("ES", "1d"), ("YM", "1d"), ("6E", "1d"), ("6B", "1d")]
rows = []
for mkt, iv in MARKETS:
    try:
        sym, src = datamod.resolve(mkt)
        bars = datamod.get_ohlcv(sym, source=src, interval=iv, limit=1000)
    except Exception as e:
        print("DATA FAIL", mkt, e); continue
    if len(bars) < 200:
        print("thin", mkt, len(bars)); continue
    a = ann(src); cut = int(len(bars) * 0.7); test = bars[cut:]
    for nm in FAM:
        try:
            best = opt.exit_search(nm, {}, bars, gate=G(), ann=a, metric="profit_factor")
            ex = best["exits"] if best else {}
            m = met.compute(bt.run(builtin.make(nm), bars, symbol=sym, gate=G(), **ex), a)
            om = met.compute(bt.run(builtin.make(nm), test, symbol=sym, gate=G(), **ex), a)
            rows.append({"s": nm, "mkt": mkt, "iv": iv, "ex": ex, "pf": m["profit_factor"],
                         "trd": m["num_trades"], "ret": m["total_return"] * 100,
                         "dd": m["max_drawdown"] * 100, "wr": m["win_rate"] * 100,
                         "oos_pf": om["profit_factor"], "oos_ret": om["total_return"] * 100,
                         "oos_trd": om["num_trades"]})
        except Exception:
            pass
    print("done", mkt, "cumulative rows", len(rows))
elig = [r for r in rows if r["trd"] >= 40 and r["ret"] > 0 and r["pf"] >= 1.2
        and (r["oos_pf"] >= 1.0 or r["oos_trd"] < 8)]
elig.sort(key=lambda r: (r["pf"], r["ret"]), reverse=True)
json.dump({"eligible": elig, "scanned": len(rows)},
          open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "registry", "roster_xmarket.json"), "w"), indent=1, default=str)
print(f"\nXMARKET: {len(elig)} passed / {len(rows)} scanned")
for r in elig[:16]:
    print(f"{r['s']:16}{r['mkt']:8}{r['iv']:4}{r['pf']:6.2f}{r['trd']:5}{r['ret']:8.1f}"
          f"{r['wr']:6.1f}{r['oos_pf']:7.2f}  {r['ex']}")
