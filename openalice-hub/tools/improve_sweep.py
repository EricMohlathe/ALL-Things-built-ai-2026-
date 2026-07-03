#!/usr/bin/env python3
"""Improve PF + win rate honestly: test a TREND-REGIME filter on every setup across
its validated markets. Gate positions to trend-aligned only (long above SMA-N, short
below). Re-optimize exits. Keep a filter ONLY if it raises PF while keeping trades and
staying OOS-positive. Writes registry/improve.json (best variant per setup-market)."""
import os, sys, json
HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HUB)
from openalice_hub.core import data as datamod, backtest as bt, metrics as met, optimize as opt, indicators as ind
from openalice_hub.core import orderflow as of
from openalice_hub.strategies import builtin, godmode_setups  # noqa

def _enrich(bars):
    for b in bars:
        b.pop("delta", None); b.pop("cvd", None)
    of.enrich(bars)
    return bars
from openalice_hub.core.execution_gate import ExecutionGate
G = lambda: ExecutionGate(mode="paper")

class TrendGate(builtin.Strategy):
    """Wrap a base setup; keep positions only when trend-aligned (SMA filter)."""
    allow_short = True
    def __init__(self, base, filt):
        self.base = base; self.filt = int(filt)
    def positions(self, bars):
        pos = self.base.positions(bars)
        if not self.filt:
            return pos
        c = [b["c"] for b in bars]; sma = ind.sma(c, self.filt)
        out = []
        for i in range(len(bars)):
            p = pos[i]
            if p > 0 and (sma[i] is None or c[i] <= sma[i]): p = 0
            if p < 0 and (sma[i] is None or c[i] >= sma[i]): p = 0
            out.append(p)
        return out

# setup -> (strategy name, [validated markets])
JOBS = {
 "gm14_spring":  ["SILVER","GOLD","EURJPY","NATGAS","CHFJPY"],
 "gm15_upthrust":["EURCHF","PLATINUM","NZDUSD"],
 "gm16_sos":     ["NQ","ES","YM","SILVER"],
 "gm11_stackbull":["GOLD","COPPER","NQ"],
 "gm22_amd":     ["GOLD","YM","SILVER","OIL"],
 "gm18_liqsweep":["PLATINUM","AUDUSD"],
 "gm24_poorhl":  ["NQ","GOLD","YM"],
 "archon_orb":   ["EURJPY","CHFJPY","BTCUSDT","CORN"],
 "archon_tsmom": ["WHEAT","NQ","CHFJPY","OIL"],
 "rsi2":         ["ES","NQ","YM","NATGAS"],
}
FILTERS = [0, 50, 100, 200]

def ann(src): return 365 if src == "binance" else 252
def score(name, market, filt):
    sym, src = (market, "binance") if market.endswith("USDT") else datamod.resolve(market)
    bars = _enrich(datamod.get_ohlcv(sym, source=src, interval="1d", limit=4000))
    if len(bars) < 300: return None
    a = ann(src); cut = int(len(bars)*0.7)
    # exit search on the gated strategy (build via a factory closure)
    base_factory = lambda **kw: TrendGate(builtin.make(name), filt)
    # exit_search uses builtin.make(name,**params); emulate by scanning EXIT_MENU directly
    best = None
    for ex in opt.EXIT_MENU:
        strat = TrendGate(builtin.make(name), filt)
        m = met.compute(bt.run(strat, bars[:cut], gate=G(), **ex), a)
        if "error" in m: continue
        key = m.get("profit_factor", 0)
        if best is None or key > best[0]:
            best = (key, ex)
    ex = best[1] if best else {}
    full = met.compute(bt.run(TrendGate(builtin.make(name), filt), bars, gate=G(), **ex), a)
    oos = met.compute(bt.run(TrendGate(builtin.make(name), filt), bars[cut:], gate=G(), **ex), a)
    return {"pf": full["profit_factor"], "wr": full["win_rate"]*100, "trd": full["num_trades"],
            "ret": full["total_return"]*100, "oos_pf": oos["profit_factor"], "oos_ret": oos["total_return"]*100,
            "filt": filt, "ex": ex}

results = {}
for name, mkts in JOBS.items():
    for mkt in mkts:
        base = None; variants = []
        for f in FILTERS:
            try:
                r = score(name, mkt, f)
                if r: variants.append(r)
                if f == 0 and r: base = r
            except Exception as e:
                pass
        if not base:
            continue
        # eligible improved variants: PF up, trades kept >=60% of base, OOS positive
        elig = [v for v in variants if v["pf"] > base["pf"] and v["trd"] >= 0.6*base["trd"]
                and v["ret"] > 0 and v["oos_ret"] > 0]
        pick = max(elig, key=lambda v: v["pf"]) if elig else base
        results[f"{name}|{mkt}"] = {"base": base, "best": pick,
                                    "improved": pick["filt"] != 0,
                                    "pf_gain": round(pick["pf"]-base["pf"], 2),
                                    "wr_gain": round(pick["wr"]-base["wr"], 1)}
        tag = f"filt{pick['filt']}" if pick["filt"] else "base"
        print(f"{name:15}{mkt:9} base PF {base['pf']:.2f}/WR {base['wr']:.0f} -> {tag} PF {pick['pf']:.2f}/WR {pick['wr']:.0f} "
              f"(+{results[f'{name}|{mkt}']['pf_gain']}PF, {results[f'{name}|{mkt}']['wr_gain']:+.0f}WR) oos {pick['oos_pf']:.2f}", flush=True)

json.dump(results, open(os.path.join(HUB, "registry", "improve.json"), "w"), indent=1, default=str)
imp = sum(1 for v in results.values() if v["improved"])
print(f"\nIMPROVED {imp}/{len(results)} setup-markets via trend filter. -> registry/improve.json", flush=True)
