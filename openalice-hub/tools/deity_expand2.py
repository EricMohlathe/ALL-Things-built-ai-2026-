#!/usr/bin/env python3
"""DEITY EXPANSION 2 — add broker-tradeable single stocks, world indices, and more
crypto to push deployable aggregate frequency past 3/day while keeping quality.
Same cost-adjusted guards. Merges into universe_full -> universe_full2.json."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openalice_hub.core import data as datamod, backtest as bt, metrics as met, optimize as opt
from openalice_hub.strategies import builtin, godmode_setups  # noqa
from openalice_hub.core.execution_gate import ExecutionGate
G = lambda: ExecutionGate(mode="paper")
FULL = ["gm14_spring", "gm15_upthrust", "gm18_liqsweep", "archon_orb", "archon_tsmom", "rsi2",
        "gm11_stackbull", "gm16_sos", "gm22_amd", "gm24_poorhl"]

STOCKS = ["AAPL","MSFT","NVDA","TSLA","AMZN","GOOGL","META","AMD","NFLX","JPM","V","UNH","XOM",
          "WMT","KO","DIS","BA","CAT","GS","INTC","CSCO","ORCL","CRM","ADBE","COST","MCD","NKE","HD","PFE","CVX"]
WIDX = ["^GDAXI","^FTSE","^FCHI","^N225","^HSI","^AXJO","^STOXX50E","^IBEX","^SSMI","^GSPTSE"]
CRYPTO = ["MATICUSDT","ATOMUSDT","NEARUSDT","FILUSDT","APTUSDT","ARBUSDT","OPUSDT","INJUSDT",
          "SUIUSDT","FTMUSDT","ALGOUSDT","AAVEUSDT","UNIUSDT","ICPUSDT","RUNEUSDT","GRTUSDT","SANDUSDT","AXSUSDT"]

rows = []
def do(sym0, src):
    try:
        bars = datamod.get_ohlcv(sym0, source=src, interval="1d", limit=4000)
    except Exception as e:
        print("  DATA FAIL", sym0, e, flush=True); return
    if len(bars) < 300:
        print("  thin", sym0, len(bars), flush=True); return
    ann = 365 if src == "binance" else 252
    n = len(bars); cut = int(n*0.7)
    for nm in FULL:
        try:
            best = opt.exit_search(nm, {}, bars, gate=G(), ann=ann, metric="profit_factor")
            ex = best["exits"] if best else {}
            m = met.compute(bt.run(builtin.make(nm), bars, gate=G(), **ex), ann)
            om = met.compute(bt.run(builtin.make(nm), bars[cut:], gate=G(), **ex), ann)
            rows.append({"s": nm, "mkt": sym0, "sym": sym0, "src": src, "nbars": n,
                         "pf": m["profit_factor"], "wr": m["win_rate"]*100, "trd": m["num_trades"],
                         "ret": m["total_return"]*100, "oos_pf": om["profit_factor"],
                         "oos_ret": om["total_return"]*100, "tpd": m["num_trades"]/n, "ex": ex})
        except Exception:
            pass
    print(f"  done {sym0} (rows {len(rows)})", flush=True)

print("=== STOCKS ===", flush=True)
for s in STOCKS: do(s, "yahoo")
print("=== WORLD INDICES ===", flush=True)
for s in WIDX: do(s, "yahoo")
print("=== MORE CRYPTO ===", flush=True)
for s in CRYPTO: do(s, "binance")

passed = [r for r in rows if r["ret"] > 0 and r["oos_ret"] > 0 and r["pf"] >= 1.4 and r["trd"] >= 25]
base = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "registry", "universe_full.json")))["passed"]
seen = set(); merged = []
for r in base + passed:
    k = (r["s"], r["mkt"])
    if k in seen: continue
    seen.add(k); merged.append(r)
merged.sort(key=lambda r: (r["pf"], r["oos_pf"]), reverse=True)
agg = sum(r["tpd"] for r in merged)
json.dump({"passed": merged, "agg_trades_per_day": agg, "n": len(merged)},
          open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "registry", "universe_full2.json"), "w"),
          indent=1, default=str)
print(f"\nEXPANSION2: +{len(passed)} new / {len(rows)} scanned", flush=True)
print(f"MERGED UNIVERSE2: {len(merged)} slots -> aggregate ~{agg:.1f} trades/day", flush=True)
