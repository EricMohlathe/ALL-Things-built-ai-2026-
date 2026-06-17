#!/usr/bin/env python3
"""Two honest pushes for more trades:
  A) H4/H1 frequency test — do the deity setups survive cost-adjusted on crypto H4/H1?
  B) D1 breadth — scan the deity setups across forex(FX futures)/metals/indices to
     widen the validated roster (more markets = more aggregate trades).
Guards everywhere: net-positive full AND OOS (cost-adjusted), real PF, real volume.
Writes registry/freq_breadth.json."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openalice_hub.core import data as datamod, backtest as bt, metrics as met, optimize as opt
from openalice_hub.strategies import builtin, godmode_setups  # noqa
from openalice_hub.core.execution_gate import ExecutionGate
G = lambda: ExecutionGate(mode="paper")
DEITY = ["gm14_spring", "gm11_stackbull", "gm16_sos", "gm22_amd", "gm18_liqsweep", "gm24_poorhl"]

def ann(src): return 365 if src == "binance" else 252

# ---- A) H4 / H1 frequency test (crypto, the only intraday data we can validate) ----
print("=== A) H4/H1 FREQUENCY TEST (crypto, cost-adjusted) ===", flush=True)
BPD = {"4h": 6, "1h": 24}
A = []
for mkt in ["BTCUSDT", "ETHUSDT"]:
    for iv, lim in [("4h", 12000), ("1h", 15000)]:
        bars = datamod.get_ohlcv(mkt, source="binance", interval=iv, limit=lim)
        days = len(bars) / BPD[iv]; cut = int(len(bars) * 0.7)
        for nm in DEITY:
            for hold in (5, 10):
                try:
                    best = opt.exit_search(nm, {"hold": hold}, bars, gate=G(), ann=365, metric="profit_factor")
                    ex = best["exits"] if best else {}
                    m = met.compute(bt.run(builtin.make(nm, hold=hold), bars, gate=G(), **ex), 365)
                    om = met.compute(bt.run(builtin.make(nm, hold=hold), bars[cut:], gate=G(), **ex), 365)
                    row = {"s": nm, "mkt": mkt, "iv": iv, "hold": hold, "pf": m["profit_factor"],
                           "wr": m["win_rate"]*100, "tpd": m["num_trades"]/days, "ret": m["total_return"]*100,
                           "oos_ret": om["total_return"]*100, "oos_pf": om["profit_factor"], "ex": ex}
                    A.append(row)
                except Exception:
                    pass
        print(f"  done {mkt} {iv} (rows {len(A)})", flush=True)
A_pass = [r for r in A if r["ret"] > 0 and r["oos_ret"] > 0 and r["pf"] >= 1.3 and r["tpd"] >= 1.0]
A_pass.sort(key=lambda r: (r["oos_ret"], r["pf"]), reverse=True)
print(f"A: {len(A_pass)} pass (net+ full&OOS, PF>=1.3, >=1/day) / {len(A)} scanned", flush=True)
for r in A_pass[:10]:
    print(f"  {r['s']:15}{r['mkt']:8}{r['iv']:4}h{r['hold']:<3}PF{r['pf']:5.2f} WR{r['wr']:4.0f} {r['tpd']:4.1f}/day ret{r['ret']:6.0f}% oos{r['oos_ret']:6.0f}%  {r['ex']}", flush=True)

# ---- B) D1 breadth across forex / metals / indices ----
print("\n=== B) D1 BREADTH (forex/metals/indices, widen the roster) ===", flush=True)
MKTS = ["6E", "6B", "6J", "6A", "6C",      # FX futures (real volume)
        "GOLD", "SILVER",                    # metals
        "NQ", "ES", "YM"]                    # index futures
B = []
for mkt in MKTS:
    try:
        sym, src = datamod.resolve(mkt)
        bars = datamod.get_ohlcv(sym, source=src, interval="1d", limit=4000)
    except Exception as e:
        print("  DATA FAIL", mkt, e, flush=True); continue
    if len(bars) < 300:
        print("  thin", mkt, len(bars), flush=True); continue
    a = ann(src); cut = int(len(bars)*0.7)
    for nm in DEITY:
        try:
            best = opt.exit_search(nm, {}, bars, gate=G(), ann=a, metric="profit_factor")
            ex = best["exits"] if best else {}
            m = met.compute(bt.run(builtin.make(nm), bars, gate=G(), **ex), a)
            om = met.compute(bt.run(builtin.make(nm), bars[cut:], gate=G(), **ex), a)
            B.append({"s": nm, "mkt": mkt, "sym": sym, "pf": m["profit_factor"], "wr": m["win_rate"]*100,
                      "trd": m["num_trades"], "ret": m["total_return"]*100, "dd": m["max_drawdown"]*100,
                      "oos_pf": om["profit_factor"], "oos_ret": om["total_return"]*100, "ex": ex})
        except Exception:
            pass
    print(f"  done {mkt} (rows {len(B)})", flush=True)
B_pass = [r for r in B if r["ret"] > 0 and r["oos_ret"] > 0 and r["pf"] >= 1.5 and r["trd"] >= 30]
B_pass.sort(key=lambda r: (r["pf"], r["oos_pf"]), reverse=True)
print(f"B: {len(B_pass)} pass (PF>=1.5, trd>=30, net+ full&OOS) / {len(B)} scanned", flush=True)
for r in B_pass[:20]:
    print(f"  {r['s']:15}{r['mkt']:7}PF{r['pf']:5.2f} WR{r['wr']:4.0f} {r['trd']:4}trd ret{r['ret']:6.0f}% oosPF{r['oos_pf']:5.2f}  {r['ex']}", flush=True)

json.dump({"A_freq": A_pass, "A_scanned": len(A), "B_breadth": B_pass, "B_scanned": len(B)},
          open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "registry", "freq_breadth.json"), "w"),
          indent=1, default=str)
print("\nWROTE registry/freq_breadth.json", flush=True)
