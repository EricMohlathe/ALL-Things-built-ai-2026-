#!/usr/bin/env python3
"""EXPANSION pass — widen the universe further to push aggregate trades/day toward
3-6. Same cost-adjusted guards. Merges with universe.json. Writes universe_expand.json."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openalice_hub.core import data as datamod, backtest as bt, metrics as met, optimize as opt
from openalice_hub.strategies import builtin, godmode_setups  # noqa
from openalice_hub.core.execution_gate import ExecutionGate
G = lambda: ExecutionGate(mode="paper")
PRICE_ONLY = ["gm14_spring", "gm15_upthrust", "gm18_liqsweep", "archon_orb", "archon_tsmom", "rsi2"]
WITH_VOL   = PRICE_ONLY + ["gm11_stackbull", "gm16_sos", "gm22_amd", "gm24_poorhl"]

# (symbol-or-alias, source, strategy_set)
JOBS = []
for x in ["GBPCHF","AUDCAD","AUDCHF","CADCHF","EURNZD","GBPNZD","GBPCAD","NZDCAD","EURCAD","USDSGD","USDNOK","USDSEK","USDMXN","USDZAR"]:
    JOBS.append((x, "auto", PRICE_ONLY))                          # extra FX crosses (spot, no volume)
for x in ["ADAUSDT","XRPUSDT","BNBUSDT","DOGEUSDT","LTCUSDT","AVAXUSDT","LINKUSDT","DOTUSDT"]:
    JOBS.append((x, "binance", WITH_VOL))                         # extra crypto
for x in ["CT=F","ZS=F","ZL=F","RB=F","HO=F","ZO=F","LE=F","HE=F","CC=F","KC=F","NKD=F","CL=F"]:
    JOBS.append((x, "yahoo", WITH_VOL))                           # extra commodities/world-index futures
for x in ["SPY","QQQ","IWM","DIA","GLD","SLV","USO","TLT","XLE","XLF","XLK","EEM","EFA","HYG","UNG","GDX"]:
    JOBS.append((x, "yahoo", WITH_VOL))                           # liquid ETFs (have volume)

rows = []
for sym0, src0, strat in JOBS:
    try:
        sym, src = (datamod.resolve(sym0) if src0 == "auto" else (sym0, src0))
        bars = datamod.get_ohlcv(sym, source=src, interval="1d", limit=4000)
    except Exception as e:
        print("  DATA FAIL", sym0, e, flush=True); continue
    if len(bars) < 300:
        print("  thin", sym0, len(bars), flush=True); continue
    ann = 365 if src == "binance" else 252
    n = len(bars); cut = int(n * 0.7)
    for nm in strat:
        try:
            best = opt.exit_search(nm, {}, bars, gate=G(), ann=ann, metric="profit_factor")
            ex = best["exits"] if best else {}
            m = met.compute(bt.run(builtin.make(nm), bars, gate=G(), **ex), ann)
            om = met.compute(bt.run(builtin.make(nm), bars[cut:], gate=G(), **ex), ann)
            rows.append({"s": nm, "mkt": sym0, "sym": sym, "src": src, "nbars": n,
                         "pf": m["profit_factor"], "wr": m["win_rate"]*100, "trd": m["num_trades"],
                         "ret": m["total_return"]*100, "oos_pf": om["profit_factor"],
                         "oos_ret": om["total_return"]*100, "tpd": m["num_trades"]/n, "ex": ex})
        except Exception:
            pass
    print(f"  done {sym0} (rows {len(rows)})", flush=True)

passed = [r for r in rows if r["ret"] > 0 and r["oos_ret"] > 0 and r["pf"] >= 1.4 and r["trd"] >= 25]
# merge with the first universe pass
base = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "registry", "universe.json")))
allslots = base["passed"] + passed
# de-dup by (strategy, market)
seen = set(); merged = []
for r in allslots:
    k = (r["s"], r["mkt"])
    if k in seen: continue
    seen.add(k); merged.append(r)
merged.sort(key=lambda r: (r["pf"], r["oos_pf"]), reverse=True)
agg = sum(r["tpd"] for r in merged)
json.dump({"passed": merged, "agg_trades_per_day": agg, "n": len(merged)},
          open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "registry", "universe_full.json"), "w"),
          indent=1, default=str)
print(f"\nEXPANSION: +{len(passed)} new / {len(rows)} scanned", flush=True)
print(f"MERGED UNIVERSE: {len(merged)} slots  ->  AGGREGATE ~{agg:.1f} trades/day", flush=True)
