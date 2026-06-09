"""
The 25 GODMODE OFEA setups as REAL, runnable Python detectors.

Each uses real Binance delta/CVD + a volume profile (see core/orderflow.py), so
ALL 25 backtest + optimize on real data. These are simplified, bar-resolution
proxies of the cTrader cBot logic — good for relative ranking + iterative
improvement, NOT a 1:1 replica of the order-flow cBot. Truth still = the cBot in
cTrader's Strategy Tester. But now every setup is green: it runs, scores, improves.

Shared params (so one optimizer grid fits all): lb (lookback), k (threshold), hold.
"""
from __future__ import annotations
from ..core import indicators as ind
from ..core import orderflow as of
from .builtin import Strategy


class GM(Strategy):
    name = "gm"; gm_id = 0; allow_short = True

    def __init__(self, lb=20, k=1.0, hold=10):
        self.lb = int(lb); self.k = float(k); self.hold = int(hold)

    def _ctx(self, bars):
        of.enrich(bars)
        c = [b["c"] for b in bars]; h = [b["h"] for b in bars]; l = [b["l"] for b in bars]
        o = [b["o"] for b in bars]; v = [b["v"] for b in bars]
        return {"bars": bars, "c": c, "h": h, "l": l, "o": o, "v": v,
                "d": [b["delta"] for b in bars], "cv": [b["cvd"] for b in bars],
                "hh": ind.highest(c, self.lb), "ll": ind.lowest(c, self.lb),
                "atr": ind.atr(bars, 14), "vma": ind.sma(v, self.lb),
                "cvma": ind.sma([b["cvd"] for b in bars], self.lb)}

    def signal(self, i, x):   # +1 long, -1 short, 0 none
        return 0

    def positions(self, bars):
        x = self._ctx(bars); n = len(bars); pos = [0] * n; cur = 0; held = 0
        for i in range(n):
            s = self.signal(i, x) or 0
            if s != 0:
                cur = s; held = self.hold
            elif held > 0:
                held -= 1
                if held == 0:
                    cur = 0
            pos[i] = cur
        return pos

    # helpers
    def _warm(self, i): return i < self.lb + 3
    def _atr(self, i, x): a = x["atr"][i]; return a if a else 0.0
    def _hivol(self, i, x): m = x["vma"][i]; return m and x["v"][i] >= self.k * 1.4 * m
    def _vp(self, i, x): return of.vp_window(x["bars"], i, win=self.lb * 4)


# ---- Absorption / CVD (1-4) ----
class GM01(GM):
    name = "gm01_absbot"; gm_id = 1
    def signal(self, i, x):
        if self._warm(i): return 0
        if x["c"][i] <= x["ll"][i-1] and self._hivol(i, x) and (x["h"][i]-x["l"][i]) < self.k*self._atr(i,x) and x["d"][i] > 0:
            return 1
        return 0
class GM02(GM):
    name = "gm02_abstop"; gm_id = 2
    def signal(self, i, x):
        if self._warm(i): return 0
        if x["c"][i] >= x["hh"][i-1] and self._hivol(i, x) and (x["h"][i]-x["l"][i]) < self.k*self._atr(i,x) and x["d"][i] < 0:
            return -1
        return 0
class GM03(GM):
    name = "gm03_cvdbear"; gm_id = 3
    def signal(self, i, x):
        if self._warm(i): return 0
        if x["c"][i] >= x["hh"][i-1] and x["cv"][i] < x["cvma"][i]: return -1
        return 0
class GM04(GM):
    name = "gm04_cvdbull"; gm_id = 4
    def signal(self, i, x):
        if self._warm(i): return 0
        if x["c"][i] <= x["ll"][i-1] and x["cv"][i] > x["cvma"][i]: return 1
        return 0

# ---- Volume profile (5-10) ----
class GM05(GM):
    name = "gm05_valbnc"; gm_id = 5
    def signal(self, i, x):
        if self._warm(i): return 0
        vp = self._vp(i, x)
        if vp and abs(x["c"][i]-vp["val"]) < self.k*self._atr(i,x) and x["d"][i] > 0: return 1
        return 0
class GM06(GM):
    name = "gm06_vahfade"; gm_id = 6
    def signal(self, i, x):
        if self._warm(i): return 0
        vp = self._vp(i, x)
        if vp and abs(x["c"][i]-vp["vah"]) < self.k*self._atr(i,x) and x["d"][i] < 0: return -1
        return 0
class GM07(GM):
    name = "gm07_pocret"; gm_id = 7
    def signal(self, i, x):
        if self._warm(i): return 0
        vp = self._vp(i, x); a = self._atr(i, x)
        if not vp or not a: return 0
        if x["c"][i] > vp["poc"] + self.k*a: return -1
        if x["c"][i] < vp["poc"] - self.k*a: return 1
        return 0
class GM08(GM):
    name = "gm08_lvnlong"; gm_id = 8
    def signal(self, i, x):
        if self._warm(i): return 0
        vp = self._vp(i, x)
        if vp and x["c"][i] > vp["lvn"] and x["c"][i-1] <= vp["lvn"] and x["d"][i] > 0: return 1
        return 0
class GM09(GM):
    name = "gm09_lvnshort"; gm_id = 9
    def signal(self, i, x):
        if self._warm(i): return 0
        vp = self._vp(i, x)
        if vp and x["c"][i] < vp["lvn"] and x["c"][i-1] >= vp["lvn"] and x["d"][i] < 0: return -1
        return 0
class GM10(GM):
    name = "gm10_hvnrej"; gm_id = 10
    def signal(self, i, x):
        if self._warm(i): return 0
        vp = self._vp(i, x); a = self._atr(i, x)
        if vp and abs(x["c"][i]-vp["hvn"]) < self.k*a:
            return 1 if x["d"][i] > 0 else -1
        return 0

# ---- Footprint stacks (11-13) ----
class GM11(GM):
    name = "gm11_stackbull"; gm_id = 11
    def signal(self, i, x):
        if self._warm(i): return 0
        if all(x["d"][i-j] > 0 for j in range(3)) and x["d"][i] > self.k*abs(x["cvma"][i]-x["cvma"][i-1] or 1): return 1
        return 0
class GM12(GM):
    name = "gm12_stackbear"; gm_id = 12
    def signal(self, i, x):
        if self._warm(i): return 0
        if all(x["d"][i-j] < 0 for j in range(3)): return -1
        return 0
class GM13(GM):
    name = "gm13_pullstack"; gm_id = 13
    def signal(self, i, x):
        if self._warm(i): return 0
        if x["c"][i] < x["c"][i-1] and x["d"][i] > 0 and x["d"][i-2] > 0 and x["d"][i-3] > 0: return 1
        return 0

# ---- Wyckoff (14-17) ----
class GM14(GM):
    name = "gm14_spring"; gm_id = 14
    def signal(self, i, x):
        if self._warm(i): return 0
        if x["l"][i] < x["ll"][i-1] and x["c"][i] > x["ll"][i-1]: return 1
        return 0
class GM15(GM):
    name = "gm15_upthrust"; gm_id = 15
    def signal(self, i, x):
        if self._warm(i): return 0
        if x["h"][i] > x["hh"][i-1] and x["c"][i] < x["hh"][i-1]: return -1
        return 0
class GM16(GM):
    name = "gm16_sos"; gm_id = 16
    def signal(self, i, x):
        if self._warm(i): return 0
        rng = x["h"][i]-x["l"][i]
        if rng > self.k*self._atr(i,x) and x["c"][i] > x["o"][i] and x["d"][i] > 0 and x["c"][i] >= x["hh"][i-1]: return 1
        return 0
class GM17(GM):
    name = "gm17_lpsy"; gm_id = 17
    def signal(self, i, x):
        if self._warm(i): return 0
        if x["c"][i] < x["o"][i] and abs(x["h"][i]-x["hh"][i-1]) < self._atr(i,x) and x["d"][i] < 0: return -1
        return 0

# ---- ICT / liquidity (18-22) ----
class GM18(GM):
    name = "gm18_liqsweep"; gm_id = 18
    def signal(self, i, x):
        if self._warm(i): return 0
        rng = (x["h"][i]-x["l"][i]) or 1
        if x["l"][i] < x["ll"][i-1] and x["c"][i] > x["l"][i] + 0.5*rng: return 1
        if x["h"][i] > x["hh"][i-1] and x["c"][i] < x["h"][i] - 0.5*rng: return -1
        return 0
class GM19(GM):
    name = "gm19_obreturn"; gm_id = 19
    def signal(self, i, x):
        if self._warm(i): return 0
        # displacement up over last 3 bars, price pulls back with buy delta
        if x["c"][i-1] > x["hh"][i-4] and x["c"][i] < x["c"][i-1] and x["d"][i] > 0: return 1
        if x["c"][i-1] < x["ll"][i-4] and x["c"][i] > x["c"][i-1] and x["d"][i] < 0: return -1
        return 0
class GM20(GM):
    name = "gm20_smtdiv"; gm_id = 20
    def signal(self, i, x):  # single-symbol proxy: price new low, CVD higher low
        if self._warm(i): return 0
        if x["l"][i] <= x["ll"][i-1] and x["cv"][i] > x["cv"][i-self.lb]: return 1
        if x["h"][i] >= x["hh"][i-1] and x["cv"][i] < x["cv"][i-self.lb]: return -1
        return 0
class GM21(GM):
    name = "gm21_breaker"; gm_id = 21
    def signal(self, i, x):
        if self._warm(i): return 0
        if x["c"][i] > x["hh"][i-1] and min(x["l"][i-3:i]) < x["ll"][i-4] and x["d"][i] > 0: return 1
        return 0
class GM22(GM):
    name = "gm22_amd"; gm_id = 22
    def signal(self, i, x):  # manipulation sweep then expansion
        if self._warm(i): return 0
        if x["l"][i-1] < x["ll"][i-2] and x["c"][i] > x["c"][i-1] and (x["h"][i]-x["l"][i]) > self.k*self._atr(i,x) and x["d"][i] > 0: return 1
        return 0

# ---- Auction / footprint (23-25) ----
class GM23(GM):
    name = "gm23_unfauc"; gm_id = 23
    def signal(self, i, x):  # unfinished auction: close at extreme -> continuation
        if self._warm(i): return 0
        rng = (x["h"][i]-x["l"][i]) or 1
        if (x["h"][i]-x["c"][i])/rng < 0.1 and x["d"][i] > 0: return 1
        if (x["c"][i]-x["l"][i])/rng < 0.1 and x["d"][i] < 0: return -1
        return 0
class GM24(GM):
    name = "gm24_poorhl"; gm_id = 24
    def signal(self, i, x):  # poor high (matching highs) -> fade short; poor low -> long
        if self._warm(i): return 0
        a = self._atr(i, x) * 0.25
        if abs(x["h"][i]-x["h"][i-1]) < a and x["d"][i] < 0: return -1
        if abs(x["l"][i]-x["l"][i-1]) < a and x["d"][i] > 0: return 1
        return 0
class GM25(GM):
    name = "gm25_iceberg"; gm_id = 25
    def signal(self, i, x):  # repeated high vol, tiny range -> hidden absorption, fade with delta
        if self._warm(i): return 0
        small = all((x["h"][i-j]-x["l"][i-j]) < self.k*self._atr(i,x) for j in range(2))
        if small and self._hivol(i, x):
            return 1 if x["d"][i] > 0 else -1
        return 0


CLASSES = [GM01, GM02, GM03, GM04, GM05, GM06, GM07, GM08, GM09, GM10, GM11, GM12,
           GM13, GM14, GM15, GM16, GM17, GM18, GM19, GM20, GM21, GM22, GM23, GM24, GM25]
GODMODE_REGISTRY = {c.name: c for c in CLASSES}
GODMODE_GRID = {"lb": [10, 20, 30], "k": [0.5, 1.0, 1.5], "hold": [5, 10, 20]}

# register into the shared backtest + optimize registries
from . import builtin as _b
_b.REGISTRY.update(GODMODE_REGISTRY)
from ..core import optimize as _o
for _n in GODMODE_REGISTRY:
    _o.GRIDS[_n] = GODMODE_GRID
