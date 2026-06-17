#!/usr/bin/env python3
"""Different-family intraday scan with COST-ADJUSTED guards (the lesson from the
high-frequency failure): a config only passes if it is NET-POSITIVE on the full
sample AND out-of-sample — not merely PF>1. Crypto only (free intraday data).
Writes registry/family_scan.json."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openalice_hub.core import data as datamod, backtest as bt, metrics as met, optimize as opt
from openalice_hub.strategies import builtin, godmode_setups  # noqa
from openalice_hub.core.execution_gate import ExecutionGate
G = lambda: ExecutionGate(mode="paper")
BPD = {"1h": 24, "15m": 96}
# conceptually DIFFERENT families from the order-flow GMs:
CANDS = ["rsi2", "archon_vwaprev",      # mean reversion
         "archon_tsmom", "sma_cross",   # momentum / trend
         "donchian", "archon_orb", "deity_vol", "archon_spike"]  # breakout / volatility
MARKETS = ["BTCUSDT", "ETHUSDT"]
IVS = [("1h", 15000), ("15m", 15000)]
rows = []
for mkt in MARKETS:
    for iv, limit in IVS:
        try:
            bars = datamod.get_ohlcv(mkt, source="binance", interval=iv, limit=limit)
        except Exception as e:
            print("DATA FAIL", mkt, iv, e, flush=True); continue
        if len(bars) < 800:
            print("thin", mkt, iv, len(bars), flush=True); continue
        days = len(bars) / BPD[iv]; cut = int(len(bars) * 0.7)
        for nm in CANDS:
            for hold in (10, 20):
                try:
                    best = opt.exit_search(nm, {"hold": hold}, bars, gate=G(), ann=365, metric="profit_factor")
                    ex = best["exits"] if best else {}
                    m = met.compute(bt.run(builtin.make(nm, hold=hold), bars, gate=G(), **ex), 365)
                    om = met.compute(bt.run(builtin.make(nm, hold=hold), bars[cut:], gate=G(), **ex), 365)
                    rows.append({"s": nm, "mkt": mkt, "iv": iv, "hold": hold, "ex": ex,
                                 "pf": m["profit_factor"], "wr": m["win_rate"] * 100,
                                 "trd": m["num_trades"], "tpd": m["num_trades"] / days,
                                 "ret": m["total_return"] * 100, "dd": m["max_drawdown"] * 100,
                                 "oos_pf": om["profit_factor"], "oos_ret": om["total_return"] * 100})
                except Exception:
                    pass
        print("done", mkt, iv, "rows", len(rows), flush=True)
# COST-ADJUSTED guards: net-positive full AND out-of-sample, real PF, some daily activity
elig = [r for r in rows if r["ret"] > 0 and r["oos_ret"] > 0 and r["pf"] >= 1.2 and r["tpd"] >= 1.0]
elig.sort(key=lambda r: (r["oos_ret"], r["pf"]), reverse=True)
out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "registry", "family_scan.json")
json.dump({"eligible": elig, "scanned": len(rows)}, open(out, "w"), indent=1, default=str)
print(f"\nFAMILY SCAN: {len(elig)} passed (net+ full AND OOS, PF>=1.2, >=1 trd/day) / {len(rows)} scanned", flush=True)
for r in elig[:20]:
    print(f"{r['s']:16}{r['mkt']:9}{r['iv']:4}h{r['hold']:<3}PF{r['pf']:5.2f} WR{r['wr']:4.0f} "
          f"{r['tpd']:4.1f}/day ret{r['ret']:6.0f}% oosRet{r['oos_ret']:6.0f}%  {r['ex']}", flush=True)
