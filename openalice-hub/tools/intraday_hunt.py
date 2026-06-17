#!/usr/bin/env python3
"""Deeper intraday hunt — find high-frequency (>=3 trades/day) configs that keep
PF>=1.3 AND survive out-of-sample (OOS PF>=1.1). Crypto only (real data+delta).
Writes registry/intraday_hunt.json."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openalice_hub.core import data as datamod, backtest as bt, metrics as met, optimize as opt
from openalice_hub.strategies import builtin, godmode_setups  # noqa
from openalice_hub.core.execution_gate import ExecutionGate
G = lambda: ExecutionGate(mode="paper")
BPD = {"5m": 288, "15m": 96, "1h": 24}
CANDS = ["gm18_liqsweep", "gm24_poorhl", "gm23_unfauc", "gm22_amd",
         "gm16_sos", "gm01_absbot", "gm21_breaker", "gm25_iceberg"]
MARKETS = ["BTCUSDT", "ETHUSDT"]
IVS = [("15m", 6000), ("5m", 6000)]
rows = []
for mkt in MARKETS:
    for iv, limit in IVS:
        try:
            bars = datamod.get_ohlcv(mkt, source="binance", interval=iv, limit=limit)
        except Exception as e:
            print("DATA FAIL", mkt, iv, e); continue
        if len(bars) < 500:
            print("thin", mkt, iv, len(bars)); continue
        days = len(bars) / BPD[iv]; cut = int(len(bars) * 0.7)
        for nm in CANDS:
            for hold in (5, 8):
                try:
                    best = opt.exit_search(nm, {"hold": hold}, bars, gate=G(), ann=365, metric="profit_factor")
                    ex = best["exits"] if best else {}
                    m = met.compute(bt.run(builtin.make(nm, hold=hold), bars, gate=G(), **ex), 365)
                    om = met.compute(bt.run(builtin.make(nm, hold=hold), bars[cut:], gate=G(), **ex), 365)
                    rows.append({"s": nm, "mkt": mkt, "iv": iv, "hold": hold, "ex": ex,
                                 "pf": m["profit_factor"], "wr": m["win_rate"] * 100,
                                 "trd": m["num_trades"], "tpd": m["num_trades"] / days,
                                 "ret": m["total_return"] * 100, "dd": m["max_drawdown"] * 100,
                                 "oos_pf": om["profit_factor"], "oos_trd": om["num_trades"]})
                except Exception:
                    pass
        print("done", mkt, iv, "rows", len(rows))
# guards: real frequency + edge + out-of-sample survival
elig = [r for r in rows if r["tpd"] >= 3.0 and r["pf"] >= 1.3 and r["oos_pf"] >= 1.1 and r["oos_trd"] >= 20]
elig.sort(key=lambda r: (r["oos_pf"], r["pf"]), reverse=True)
json.dump({"eligible": elig, "scanned": len(rows)},
          open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "registry", "intraday_hunt.json"), "w"), indent=1, default=str)
print(f"\nHUNT: {len(elig)} passed (>=3/day, PF>=1.3, OOS>=1.1) / {len(rows)} scanned")
for r in elig[:20]:
    print(f"{r['s']:15}{r['mkt']:9}{r['iv']:4}h{r['hold']:<3}PF{r['pf']:5.2f} WR{r['wr']:4.0f} "
          f"{r['tpd']:4.1f}/day oosPF{r['oos_pf']:5.2f}  {r['ex']}")
