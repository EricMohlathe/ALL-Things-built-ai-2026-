#!/usr/bin/env python3
"""Forex-specific edge hunt. Spot FX (Yahoo) has ~no volume, so delta/footprint
setups can't work there -> use PRICE-ONLY structure strategies on spot majors.
FX FUTURES (6E/6B/...) have real volume -> test the full set there too.
Cost-adjusted guards: net-positive full AND OOS. Writes registry/forex_edge.json."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openalice_hub.core import data as datamod, backtest as bt, metrics as met, optimize as opt
from openalice_hub.strategies import builtin, godmode_setups  # noqa
from openalice_hub.core.execution_gate import ExecutionGate
G = lambda: ExecutionGate(mode="paper")

PRICE_ONLY = ["gm14_spring", "gm15_upthrust", "gm18_liqsweep", "donchian", "rsi2",
              "archon_orb", "archon_tsmom"]                 # no volume needed
WITH_VOL  = PRICE_ONLY + ["gm11_stackbull", "gm16_sos", "gm22_amd", "gm24_poorhl"]
SPOT = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "EURJPY", "GBPJPY"]
FUT  = ["6E", "6B", "6J", "6A", "6C"]

def run(markets, strer_list):
    rows = []
    for mkt in markets:
        try:
            sym, src = datamod.resolve(mkt)
            bars = datamod.get_ohlcv(sym, source=src, interval="1d", limit=4000)
        except Exception as e:
            print("  DATA FAIL", mkt, e, flush=True); continue
        if len(bars) < 300:
            print("  thin", mkt, len(bars), flush=True); continue
        a = 252; cut = int(len(bars) * 0.7)
        for nm in strer_list:
            try:
                best = opt.exit_search(nm, {}, bars, gate=G(), ann=a, metric="profit_factor")
                ex = best["exits"] if best else {}
                m = met.compute(bt.run(builtin.make(nm), bars, gate=G(), **ex), a)
                om = met.compute(bt.run(builtin.make(nm), bars[cut:], gate=G(), **ex), a)
                rows.append({"s": nm, "mkt": mkt, "sym": sym, "pf": m["profit_factor"], "wr": m["win_rate"]*100,
                             "trd": m["num_trades"], "ret": m["total_return"]*100, "dd": m["max_drawdown"]*100,
                             "oos_pf": om["profit_factor"], "oos_ret": om["total_return"]*100, "ex": ex})
            except Exception:
                pass
        print(f"  done {mkt} (rows {len(rows)})", flush=True)
    return rows

print("=== SPOT FOREX (price-only structure strategies) ===", flush=True)
spot = run(SPOT, PRICE_ONLY)
print("=== FX FUTURES (full set, real volume) ===", flush=True)
fut = run(FUT, WITH_VOL)
allrows = spot + fut
passed = [r for r in allrows if r["ret"] > 0 and r["oos_ret"] > 0 and r["pf"] >= 1.4 and r["trd"] >= 25]
passed.sort(key=lambda r: (r["pf"], r["oos_pf"]), reverse=True)
json.dump({"passed": passed, "scanned": len(allrows)},
          open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "registry", "forex_edge.json"), "w"),
          indent=1, default=str)
print(f"\nFOREX EDGE: {len(passed)} pass (PF>=1.4, trd>=25, net+ full&OOS) / {len(allrows)} scanned", flush=True)
for r in passed[:24]:
    print(f"  {r['s']:15}{r['mkt']:8}PF{r['pf']:5.2f} WR{r['wr']:4.0f} {r['trd']:4}trd ret{r['ret']:6.0f}% oosPF{r['oos_pf']:5.2f}  {r['ex']}", flush=True)
