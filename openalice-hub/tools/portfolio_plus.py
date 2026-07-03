#!/usr/bin/env python3
"""Apply the 13 validated trend-filter improvements: upgrade the decorrelated roster
(6th field = TrendSMA) and re-run the blended portfolio backtest to measure the lift.
Updates roster_meta + roster_godmode_decorr.txt + portfolio_decorr.json."""
import os, sys, json, math, datetime as dt
HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HUB)
from openalice_hub.core import data as datamod, backtest as bt, metrics as met, indicators as ind
from openalice_hub.core import orderflow as of
from openalice_hub.strategies import builtin, godmode_setups  # noqa
from openalice_hub.core.execution_gate import ExecutionGate
G = lambda: ExecutionGate(mode="paper")

class TrendGate(builtin.Strategy):
    allow_short = True
    def __init__(self, base, filt): self.base = base; self.filt = int(filt)
    def positions(self, bars):
        pos = self.base.positions(bars)
        if not self.filt: return pos
        c = [b["c"] for b in bars]; sma = ind.sma(c, self.filt); out = []
        for i in range(len(bars)):
            p = pos[i]
            if p > 0 and (sma[i] is None or c[i] <= sma[i]): p = 0
            if p < 0 and (sma[i] is None or c[i] >= sma[i]): p = 0
            out.append(p)
        return out

# 13 improvements: (broker_sym, SETUP) -> (stop, tp, trail, trendN, strategy, data_market)
IMP = {
 ("XAGUSD","AMD"):        (0,0,0,200,"gm22_amd","SILVER"),
 ("NAS100","TSMOM"):      (3,6,0,200,"archon_tsmom","NQ"),
 ("EURJPY","ORB"):        (1,2,1.5,200,"archon_orb","EURJPY"),
 ("NAS100","STACKBULL"):  (0,0,0,200,"gm11_stackbull","NQ"),
 ("XAUUSD","SPRING"):     (3,1,0,100,"gm14_spring","GOLD"),
 ("US500","SOS"):         (3,1,0,200,"gm16_sos","ES"),
 ("CHFJPY","ORB"):        (3,1,0,200,"archon_orb","CHFJPY"),
 ("US30","AMD"):          (0,0,0,200,"gm22_amd","YM"),
 ("EURJPY","SPRING"):     (3,1,0,50,"gm14_spring","EURJPY"),
 ("BTCUSD","ORB"):        (0,0,0,100,"archon_orb","BTCUSDT"),
 ("NAS100","SOS"):        (2,4,3,50,"gm16_sos","NQ"),
 ("XAUUSD","STACKBULL"):  (4,1.5,0,200,"gm11_stackbull","GOLD"),
 ("XAGUSD","SOS"):        (1.5,3,2,100,"gm16_sos","SILVER"),
}

META = json.load(open(os.path.join(HUB, "registry", "roster_meta.json")))
roster = META["godmode_decorr"]["roster"].split(";")
# upgrade matching slots to 6-field (append TrendSMA), update exits
def g(x): return ("%g" % x) if x else "0"
upgraded = 0
new = []
for slot in roster:
    p = slot.split(":")
    key = (p[0], p[1])
    if key in IMP:
        st, tp, tr, tn, nm, mk = IMP[key]
        new.append(f"{p[0]}:{p[1]}:{g(st)}:{g(tp)}:{g(tr)}:{tn}"); upgraded += 1
    else:
        new.append(slot)
plus = ";".join(new)
open(os.path.join(HUB, "registry", "roster_godmode_decorr.txt"), "w").write(plus)
META["godmode_decorr"]["roster"] = plus
META["godmode_decorr"]["improved_slots"] = upgraded

# ---- re-run blended portfolio on the upgraded roster ----
U = json.load(open(os.path.join(HUB, "registry", "universe_full2.json")))["passed"]
SET = {"gm14_spring":"SPRING","gm15_upthrust":"UPTHRUST","gm16_sos":"SOS","gm11_stackbull":"STACKBULL",
       "gm22_amd":"AMD","gm18_liqsweep":"LIQSWEEP","archon_orb":"ORB","gm24_poorhl":"POORHL",
       "archon_tsmom":"TSMOM","rsi2":"RSI2"}
idx = {(r["mkt"], SET[r["s"]]): r for r in U}
slots = META["godmode_decorr"]["slots"]
def day(t): t = t/1000 if t > 1e11 else t; return dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d")
IMP_by_bs = {(k[0], k[1]): v for k, v in IMP.items()}

per = []
for s in slots:
    row = idx.get((s["mkt"], s["setup"]))
    if not row: continue
    sym, src = row["sym"], row["src"]
    bars = datamod.get_ohlcv(sym, source=src, interval="1d", limit=4000)
    for b in bars: b.pop("delta", None); b.pop("cvd", None)
    of.enrich(bars)
    # if this slot was improved, apply trend filter + improved exits
    imp = IMP_by_bs.get((s["sym"], s["setup"]))
    if imp:
        st, tp, tr, tn, nm, mk = imp
        strat = TrendGate(builtin.make(row["s"]), tn)
        ex = {}
        if st: ex["stop_atr"] = st
        if tp: ex["tp_atr"] = tp
        if tr: ex["trail_atr"] = tr
    else:
        strat = builtin.make(row["s"]); ex = row["ex"]
    try:
        res = bt.run(strat, bars, symbol=sym, gate=G(), **ex)
        eq = res["equity_curve"]; r = {}
        for i in range(1, len(eq)):
            if eq[i-1] > 0: r[day(bars[i]["t"])] = eq[i]/eq[i-1] - 1
        per.append(r)
    except Exception:
        pass
N = len(per); alldates = sorted(set().union(*[set(r) for r in per]))
pr = [sum(r.get(d, 0.0) for r in per)/N for d in alldates]
eq = [1.0]
for x in pr: eq.append(eq[-1]*(1+x))
mean = sum(pr)/len(pr); sd = math.sqrt(sum((x-mean)**2 for x in pr)/len(pr))
sharpe = mean/sd*math.sqrt(252) if sd > 0 else 0
peak = eq[0]; mdd = 0
for v in eq: peak = max(peak, v); mdd = min(mdd, v/peak-1)
yrs = len(pr)/252.0; cagr = eq[-1]**(1/yrs)-1
wd = sum(1 for x in pr if x > 0)/len(pr); step = max(1, len(eq)//220)
out = {"n_slots": N, "dates": [alldates[0], alldates[-1]], "days": len(pr), "improved_slots": upgraded,
       "metrics": {"total_return": round(eq[-1]-1, 4), "cagr": round(cagr, 4), "sharpe": round(sharpe, 2),
                   "max_drawdown": round(mdd, 4), "win_days": round(wd, 4), "years": round(yrs, 1)},
       "equity": [round(v, 4) for v in eq[::step]]}
json.dump(out, open(os.path.join(HUB, "registry", "portfolio_decorr.json"), "w"), indent=1)
json.dump(META, open(os.path.join(HUB, "registry", "roster_meta.json"), "w"), indent=1, default=str)
m = out["metrics"]
print(f"UPGRADED {upgraded} slots with trend filters.")
print(f"PORTFOLIO+ ({N} slots): ret {m['total_return']*100:.0f}% | CAGR {m['cagr']*100:.1f}% | "
      f"Sharpe {m['sharpe']} | maxDD {m['max_drawdown']*100:.1f}% | win-days {m['win_days']*100:.0f}%")
print("roster_godmode_decorr.txt + roster_meta + portfolio_decorr.json updated.")
