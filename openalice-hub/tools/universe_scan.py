#!/usr/bin/env python3
"""WIDE-UNIVERSE D1 scan. Find EVERY validated symbol-setup slot across a broad
market universe, so a portfolio of them aggregates to 3-6 trades/DAY — every trade
a real, OOS-validated edge (no cost-eaten intraday). Writes registry/universe.json."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openalice_hub.core import data as datamod, backtest as bt, metrics as met, optimize as opt
from openalice_hub.strategies import builtin, godmode_setups  # noqa
from openalice_hub.core.execution_gate import ExecutionGate
G = lambda: ExecutionGate(mode="paper")

# volume-free strategies (work everywhere incl spot forex) + delta ones (futures/crypto only)
PRICE_ONLY = ["gm14_spring", "gm15_upthrust", "gm18_liqsweep", "archon_orb", "archon_tsmom", "rsi2"]
WITH_VOL   = PRICE_ONLY + ["gm11_stackbull", "gm16_sos", "gm22_amd", "gm24_poorhl"]

SPOT_FX = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD",
           "EURJPY", "GBPJPY", "EURGBP", "AUDJPY", "EURAUD", "GBPAUD", "CADJPY",
           "CHFJPY", "NZDJPY", "EURCHF", "AUDNZD"]                       # spot -> price-only
VOL_MKTS = ["GOLD", "SILVER", "PLATINUM", "PALLADIUM", "COPPER",         # metals
            "OIL", "BRENT", "NATGAS", "WHEAT", "CORN", "COFFEE", "SUGAR",# energy/ags
            "ES", "NQ", "YM", "RTY",                                     # index futures
            "6E", "6B", "6J", "6A", "6C",                               # fx futures
            "ZB", "ZN",                                                  # bonds
            "BTCUSDT", "ETHUSDT", "SOLUSDT"]                            # crypto -> full set

rows = []
def do(mkt, strat_list, src_hint=None):
    try:
        if mkt.endswith("USDT"):
            sym, src = mkt, "binance"
        else:
            sym, src = datamod.resolve(mkt)
        bars = datamod.get_ohlcv(sym, source=src, interval="1d", limit=4000)
    except Exception as e:
        print("  DATA FAIL", mkt, e, flush=True); return
    if len(bars) < 300:
        print("  thin", mkt, len(bars), flush=True); return
    ann = 365 if src == "binance" else 252
    n = len(bars); cut = int(n * 0.7)
    for nm in strat_list:
        try:
            best = opt.exit_search(nm, {}, bars, gate=G(), ann=ann, metric="profit_factor")
            ex = best["exits"] if best else {}
            m = met.compute(bt.run(builtin.make(nm), bars, gate=G(), **ex), ann)
            om = met.compute(bt.run(builtin.make(nm), bars[cut:], gate=G(), **ex), ann)
            rows.append({"s": nm, "mkt": mkt, "sym": sym, "src": src, "nbars": n,
                         "pf": m["profit_factor"], "wr": m["win_rate"]*100, "trd": m["num_trades"],
                         "ret": m["total_return"]*100, "dd": m["max_drawdown"]*100,
                         "oos_pf": om["profit_factor"], "oos_ret": om["total_return"]*100,
                         "tpd": m["num_trades"]/n, "ex": ex})
        except Exception:
            pass
    print(f"  done {mkt} (rows {len(rows)})", flush=True)

print("=== SPOT FX (price-only) ===", flush=True)
for m in SPOT_FX: do(m, PRICE_ONLY)
print("=== VOL MARKETS (full set) ===", flush=True)
for m in VOL_MKTS: do(m, WITH_VOL)

passed = [r for r in rows if r["ret"] > 0 and r["oos_ret"] > 0 and r["pf"] >= 1.4 and r["trd"] >= 25]
passed.sort(key=lambda r: (r["pf"], r["oos_pf"]), reverse=True)
agg_tpd = sum(r["tpd"] for r in passed)   # portfolio trades per trading-day if all run concurrently
json.dump({"passed": passed, "scanned": len(rows), "agg_trades_per_day": agg_tpd},
          open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "registry", "universe.json"), "w"),
          indent=1, default=str)
print(f"\nUNIVERSE: {len(passed)} validated slots / {len(rows)} scanned", flush=True)
print(f"AGGREGATE PORTFOLIO FREQUENCY: ~{agg_tpd:.1f} trades/day (all slots concurrent)", flush=True)
for r in passed[:60]:
    print(f"  {r['s']:15}{r['mkt']:9}PF{r['pf']:5.2f} WR{r['wr']:4.0f} {r['trd']:4}trd oos{r['oos_pf']:5.2f} {r['tpd']*252:4.0f}/yr  {r['ex']}", flush=True)
