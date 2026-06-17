#!/usr/bin/env python3
"""Combined portfolio backtest of the GODMODE_DECORR roster. Runs every slot,
derives per-DATE returns, blends at equal capital allocation, and reports the
real combined equity curve + Sharpe / maxDD / etc. Writes registry/portfolio_decorr.json."""
import os, sys, json, math, datetime as dt
HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HUB)
from openalice_hub.core import data as datamod, backtest as bt, metrics as met
from openalice_hub.strategies import builtin, godmode_setups  # noqa
from openalice_hub.core.execution_gate import ExecutionGate
G = lambda: ExecutionGate(mode="paper")

META = json.load(open(os.path.join(HUB, "registry", "roster_meta.json")))
U = json.load(open(os.path.join(HUB, "registry", "universe_full2.json")))["passed"]
SET = {"gm14_spring":"SPRING","gm15_upthrust":"UPTHRUST","gm16_sos":"SOS","gm11_stackbull":"STACKBULL",
       "gm22_amd":"AMD","gm18_liqsweep":"LIQSWEEP","archon_orb":"ORB","gm24_poorhl":"POORHL",
       "archon_tsmom":"TSMOM","rsi2":"RSI2"}
# index universe rows by (mkt, setup) -> full info (strategy name, exits, src)
idx = {(r["mkt"], SET[r["s"]]): r for r in U}
slots = META["godmode_decorr"]["slots"]

def day(t): t = t/1000 if t > 1e11 else t; return dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d")

per_slot = []   # list of {ret: {date: r}}
done = 0
for s in slots:
    row = idx.get((s["mkt"], s["setup"]))
    if not row: continue
    try:
        sym, src = row["sym"], row["src"]
        bars = datamod.get_ohlcv(sym, source=src, interval="1d", limit=4000)
        res = bt.run(builtin.make(row["s"]), bars, symbol=sym, gate=G(), **row["ex"])
        eq = res["equity_curve"]
        r = {}
        for i in range(1, len(eq)):
            if eq[i-1] > 0:
                r[day(bars[i]["t"])] = eq[i]/eq[i-1] - 1
        per_slot.append(r); done += 1
        if done % 20 == 0: print("  backtested", done, "slots", flush=True)
    except Exception as e:
        pass
print("slots backtested:", len(per_slot), flush=True)

# blend at equal capital allocation: portfolio daily return = mean of slot returns (flat=0)
N = len(per_slot)
alldates = sorted(set().union(*[set(r) for r in per_slot]))
pr = []
for d in alldates:
    pr.append(sum(r.get(d, 0.0) for r in per_slot) / N)
# cumulative equity
eq = [1.0]
for x in pr: eq.append(eq[-1]*(1+x))
total_ret = eq[-1]-1
# metrics
mean = sum(pr)/len(pr); var = sum((x-mean)**2 for x in pr)/len(pr); sd = math.sqrt(var)
sharpe = (mean/sd*math.sqrt(252)) if sd > 0 else 0
peak = eq[0]; mdd = 0
for v in eq:
    peak = max(peak, v); mdd = min(mdd, v/peak-1)
yrs = len(pr)/252.0
cagr = (eq[-1])**(1/yrs)-1 if yrs > 0 else 0
wd = sum(1 for x in pr if x > 0)/len(pr)
# downsample equity for chart
step = max(1, len(eq)//220)
out = {"n_slots": N, "dates": [alldates[0], alldates[-1]], "days": len(pr),
       "metrics": {"total_return": round(total_ret, 4), "cagr": round(cagr, 4),
                   "sharpe": round(sharpe, 2), "max_drawdown": round(mdd, 4),
                   "win_days": round(wd, 4), "years": round(yrs, 1)},
       "equity": [round(v, 4) for v in eq[::step]]}
json.dump(out, open(os.path.join(HUB, "registry", "portfolio_decorr.json"), "w"), indent=1)
m = out["metrics"]
print(f"\nPORTFOLIO ({N} slots, {m['years']}yr): ret {m['total_return']*100:.0f}% | CAGR {m['cagr']*100:.1f}% | "
      f"Sharpe {m['sharpe']} | maxDD {m['max_drawdown']*100:.1f}% | win-days {m['win_days']*100:.0f}%", flush=True)
