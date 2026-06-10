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


class GMConfluence(GM):
    """N-of-M vote across the historically best OOS setups. k = votes needed."""
    name = "gm_confluence"; gm_id = 99
    MEMBERS = (GM12, GM17, GM24, GM15, GM09)   # top OOS rank

    def positions(self, bars):
        votes = [m(lb=self.lb, hold=self.hold).positions(bars) for m in self.MEMBERS]
        need = max(2, int(self.k))
        out = []
        for i in range(len(bars)):
            s = sum(v[i] for v in votes)
            out.append(1 if s >= need else (-1 if s <= -need else 0))
        return out


CLASSES = [GMConfluence, GM01, GM02, GM03, GM04, GM05, GM06, GM07, GM08, GM09, GM10, GM11, GM12,
           GM13, GM14, GM15, GM16, GM17, GM18, GM19, GM20, GM21, GM22, GM23, GM24, GM25]
GODMODE_REGISTRY = {c.name: c for c in CLASSES}
GODMODE_GRID = {"lb": [10, 20, 30], "k": [0.5, 1.0, 1.5], "hold": [5, 10, 20]}

# register into the shared backtest + optimize registries
from . import builtin as _b
_b.REGISTRY.update(GODMODE_REGISTRY)
from ..core import optimize as _o
for _n in GODMODE_REGISTRY:
    _o.GRIDS[_n] = GODMODE_GRID


class GMChecklist(GM):
    """ThePerfectTrade.net confluence checklist as a computable strategy.
    7 weighted conditions per timeframe (current + 5x-aggregated 'higher TF'):
      Trend +10 | At AOI/Rejected +10 | Touching EMA +5 | Round Psych Level +5
      Rejection from Prev Structure +10 | Candle Rejection at AOI +10 | Break&Retest +10
    Enter when directional confluence % >= k (param). Max 60/TF, 120 total."""
    name = "perfect_checklist"; gm_id = 98

    def _tf_score(self, i, x, bars):
        if i < self.lb + 3:
            return 0, 0
        c, h, l, o = x["c"], x["h"], x["l"], x["o"]
        a = self._atr(i, x) or (c[i] * 0.01)
        sma50 = sum(c[max(0, i-49):i+1]) / min(50, i+1)
        hh, ll = x["hh"][i-1], x["ll"][i-1]
        bull = bear = 0
        # 1 Trend (+10)
        if c[i] > sma50: bull += 10
        else: bear += 10
        # 2 At AOI / rejected (+10): near lookback swing low (long AOI) or high (short AOI)
        if hh and ll:
            if abs(l[i] - ll) < a: bull += 10
            if abs(h[i] - hh) < a: bear += 10
        # 3 Touching EMA20 (+5)
        ema = c[i]; k2 = 2/21
        e = c[max(0, i-30)]
        for j in range(max(1, i-29), i+1): e = c[j]*k2 + e*(1-k2)
        if abs(c[i] - e) < 0.3*a:
            bull += 5; bear += 5
        # 4 Round psychological level (+5) — guard: oil went negative in 2020
        import math as _m
        step = 10 ** _m.floor(_m.log10(abs(c[i]))) / 10 if abs(c[i]) > 1e-9 else 1.0
        if (c[i] % step) < 0.2*a or (step - c[i] % step) < 0.2*a:
            bull += 5; bear += 5
        # 5 Rejection from previous structure (+10): wick beyond, close back inside
        if ll and l[i] < ll and c[i] > ll: bull += 10
        if hh and h[i] > hh and c[i] < hh: bear += 10
        # 6 Candlestick rejection at AOI (+10): pin bar with long tail at the zone
        rng = (h[i]-l[i]) or 1e-9
        if (c[i]-l[i])/rng > 0.66 and ll and abs(l[i]-ll) < 1.5*a: bull += 10
        if (h[i]-c[i])/rng > 0.66 and hh and abs(h[i]-hh) < 1.5*a: bear += 10
        # 7 Break & retest (+10): broke swing high recently, now retesting it
        if hh and any(c[i-j] > hh for j in range(1, 4)) and abs(c[i]-hh) < a: bull += 10
        if ll and any(c[i-j] < ll for j in range(1, 4)) and abs(c[i]-ll) < a: bear += 10
        return bull, bear

    def positions(self, bars):
        x = self._ctx(bars)
        # higher timeframe = 5-bar aggregate
        htf = [{"t": b["t"], "o": bars[max(0,j-4)]["o"], "c": b["c"],
                "h": max(bb["h"] for bb in bars[max(0,j-4):j+1]),
                "l": min(bb["l"] for bb in bars[max(0,j-4):j+1]),
                "v": sum(bb["v"] for bb in bars[max(0,j-4):j+1])}
               for j, b in enumerate(bars)]
        x2 = self._ctx(htf)
        n = len(bars); pos = [0]*n; cur = 0; held = 0
        for i in range(n):
            b1, s1 = self._tf_score(i, x, bars)
            b2, s2 = self._tf_score(i, x2, htf)
            bull_pct = (b1 + b2) / 120 * 100
            bear_pct = (s1 + s2) / 120 * 100
            sig = 1 if (bull_pct >= self.k and bull_pct > bear_pct) else (-1 if (bear_pct >= self.k and bear_pct > bull_pct) else 0)
            if sig != 0:
                cur = sig; held = self.hold
            elif held > 0:
                held -= 1
                if held == 0: cur = 0
            pos[i] = cur
        return pos


GODMODE_REGISTRY["perfect_checklist"] = GMChecklist
_b.REGISTRY["perfect_checklist"] = GMChecklist
_o.GRIDS["perfect_checklist"] = {"lb": [15, 25], "k": [35, 45, 55], "hold": [5, 10, 20]}


class GMGated(GM):
    """GODMODE hybrid: gm_confluence entries, taken ONLY when the PerfectTrade
    checklist confluence agrees (regime gate). Weak signals filtered by structure."""
    name = "gm_gated"; gm_id = 97

    def positions(self, bars):
        conf = GMConfluence(lb=self.lb, k=2, hold=self.hold).positions(bars)
        chk = GMChecklist(lb=max(15, self.lb), k=self.k, hold=self.hold)
        x = chk._ctx(bars)
        out = []; cur = 0; held = 0
        for i in range(len(bars)):
            sig = conf[i]
            if sig != 0 and sig != cur:
                b, s = chk._tf_score(i, x, bars)
                pct = (b if sig > 0 else s) / 60 * 100
                if pct >= self.k:        # checklist must agree
                    cur = sig; held = self.hold
                else:
                    sig = 0
            if cur != 0 and conf[i] == 0:
                held -= 1
                if held <= 0: cur = 0
            out.append(cur)
        return out


GODMODE_REGISTRY["gm_gated"] = GMGated
_b.REGISTRY["gm_gated"] = GMGated
_o.GRIDS["gm_gated"] = {"lb": [10, 20, 30], "k": [25, 35, 45], "hold": [5, 10, 20]}


# ==== DEITY series: dead concepts reborn in high-PF structure ====
# PF >= 3.7 comes from R-asymmetry (tiny losses, fat winners), NOT win rate.
# Dead parents: gm04 (CVD), gm16 (SOS), gm21 (breaker), gm18 (sweep), gm14 (spring).

class GMDeityTrend(GM):
    """Trend deity: donchian breakout + trend + CVD agreement (gm04/gm16/gm21 concepts).
    Only with-trend. Exits handled by wide trail via EXIT_MENU (let winners run)."""
    name = "deity_trend"; gm_id = 96

    def signal(self, i, x):
        if self._warm(i) or i < 55: return 0
        c = x["c"]
        sma = sum(c[i-49:i+1]) / 50
        up = c[i] > sma
        if up and c[i] >= x["hh"][i-1] and x["cv"][i] > x["cvma"][i]:
            return 1
        if (not up) and c[i] <= x["ll"][i-1] and x["cv"][i] < x["cvma"][i]:
            return -1
        return 0


class GMDeitySweep(GM):
    """Sweep deity: liquidity sweep + spring (gm18/gm14 concepts) but ONLY with-trend
    + displacement confirmation. The counter-trend versions died; this one rides."""
    name = "deity_sweep"; gm_id = 95

    def signal(self, i, x):
        if self._warm(i) or i < 55: return 0
        c, h, l = x["c"], x["h"], x["l"]
        a = self._atr(i, x)
        if not a: return 0
        sma = sum(c[i-49:i+1]) / 50
        rng = (h[i]-l[i]) or 1e-9
        # uptrend: sweep below recent low, strong close back up (spring WITH trend)
        if c[i] > sma and l[i] < x["ll"][i-1] and (c[i]-l[i])/rng > 0.6 and (h[i]-l[i]) > self.k*a:
            return 1
        if c[i] < sma and h[i] > x["hh"][i-1] and (h[i]-c[i])/rng > 0.6 and (h[i]-l[i]) > self.k*a:
            return -1
        return 0


class GMDeityVol(GM):
    """Volatility deity: SOS expansion (gm16 concept) fired only on low-vol -> expansion
    transition (regime). Squeeze then go; asymmetric exits do the rest."""
    name = "deity_vol"; gm_id = 94

    def signal(self, i, x):
        if self._warm(i) or i < 30: return 0
        atr = x["atr"]
        if not atr[i] or not atr[i-10]: return 0
        squeezed = atr[i-1] < 0.8 * (atr[i-10] or 1e9)   # vol contraction
        expanding = (x["h"][i]-x["l"][i]) > self.k * 1.5 * atr[i]
        if squeezed and expanding:
            if x["c"][i] > x["o"][i] and x["d"][i] > 0: return 1
            if x["c"][i] < x["o"][i] and x["d"][i] < 0: return -1
        return 0


for cls in (GMDeityTrend, GMDeitySweep, GMDeityVol):
    GODMODE_REGISTRY[cls.name] = cls
    _b.REGISTRY[cls.name] = cls
    _o.GRIDS[cls.name] = {"lb": [20, 40, 55], "k": [0.8, 1.2, 1.8], "hold": [10, 20, 40]}


# ==== ARCHON tier: documented quant anomalies (above deity) ====
class ArchonTSMom(GM):
    """Time-series momentum (Moskowitz/Ooi/Pedersen 2012) — one of the most robust
    documented anomalies. Long if return over lookback > 0, else short. Vol-scaled by exits."""
    name = "archon_tsmom"; gm_id = 90
    def signal(self, i, x):
        if i < self.lb + 2: return 0
        c = x["c"]; r = c[i] / c[i-self.lb] - 1.0
        thr = self.k * 0.01
        if r > thr: return 1
        if r < -thr: return -1
        return 0


class ArchonVWAPRev(GM):
    """VWAP mean-reversion: fade extension from rolling VWAP by k*ATR, ONLY in range
    regime (price inside its own lb-range, not trending). Classic intraday desk edge."""
    name = "archon_vwaprev"; gm_id = 91
    def signal(self, i, x):
        if self._warm(i): return 0
        c, h, l, v = x["c"], x["h"], x["l"], x["v"]
        a = self._atr(i, x)
        if not a: return 0
        win = self.lb
        num = sum(((h[j]+l[j]+c[j])/3)*v[j] for j in range(i-win+1, i+1))
        den = sum(v[j] for j in range(i-win+1, i+1)) or 1e-9
        vwap = num/den
        sma = sum(c[i-win+1:i+1])/win
        ranging = abs(c[i]-sma) < 1.5*a            # only fade when not trending
        if ranging:
            if c[i] < vwap - self.k*a: return 1
            if c[i] > vwap + self.k*a: return -1
        return 0


class ArchonORB(GM):
    """Opening-range breakout (Crabel/Williams volatility breakout): break of the prior
    lb-bar range by a k*ATR buffer in the trend direction. Fat-tail trend capture."""
    name = "archon_orb"; gm_id = 92
    def signal(self, i, x):
        if self._warm(i): return 0
        c = x["c"]; a = self._atr(i, x)
        if not a: return 0
        sma = sum(c[max(0,i-49):i+1])/min(50, i+1)
        if c[i] > x["hh"][i-1] + self.k*a*0.2 and c[i] > sma: return 1
        if c[i] < x["ll"][i-1] - self.k*a*0.2 and c[i] < sma: return -1
        return 0


for cls in (ArchonTSMom, ArchonVWAPRev, ArchonORB):
    GODMODE_REGISTRY[cls.name] = cls
    _b.REGISTRY[cls.name] = cls
    _o.GRIDS[cls.name] = {"lb": [10, 20, 40], "k": [0.5, 1.0, 2.0], "hold": [6, 12, 24]}


class ArchonSpike(GM):
    """Spike-specific (Boom/Crash structure): these synthetics drift one way then
    spike the other. BOOM = many small downs + rare up-spike -> only LONG into the
    spike side; CRASH = mirror, only SHORT. Detect compression then directional pop."""
    name = "archon_spike"; gm_id = 93
    def signal(self, i, x):
        if self._warm(i): return 0
        c, h, l = x["c"], x["h"], x["l"]; a = self._atr(i, x)
        if not a: return 0
        rng = h[i] - l[i]
        big = rng > self.k * 1.5 * a
        up = c[i] > c[i-1]
        # buy the up-pop after a down-drift run (boom side); sell the down-pop (crash side)
        drift_dn = sum(1 for j in range(i-self.lb+1, i) if c[j] < c[j-1]) > self.lb*0.6
        drift_up = sum(1 for j in range(i-self.lb+1, i) if c[j] > c[j-1]) > self.lb*0.6
        if big and up and drift_dn: return 1
        if big and (not up) and drift_up: return -1
        return 0

GODMODE_REGISTRY["archon_spike"]=ArchonSpike
_b.REGISTRY["archon_spike"]=ArchonSpike
_o.GRIDS["archon_spike"]={"lb":[10,20,40],"k":[0.8,1.2,2.0],"hold":[3,6,12]}


class GMDeityFlow(GM):
    """THE integration deity: ORDERFLOW (real taker delta) + LIQUIDITY (sweep of
    lookback extreme) + PRICE ACTION (strong rejection close) + trend alignment.
    Long: sweep below lows, buyers absorb (delta>0), close strong, uptrend. Mirror short."""
    name = "deity_flow"; gm_id = 89

    def signal(self, i, x):
        if self._warm(i) or i < 55: return 0
        c, h, l = x["c"], x["h"], x["l"]
        rng = (h[i] - l[i]) or 1e-9
        sma = sum(c[i-49:i+1]) / 50
        # LONG: liquidity sweep low + orderflow absorption + PA strong close + trend
        if (l[i] < x["ll"][i-1] and x["d"][i] > 0
                and (c[i] - l[i]) / rng > 0.55 and c[i] > sma * (1 - 0.002 * self.k)):
            return 1
        if (h[i] > x["hh"][i-1] and x["d"][i] < 0
                and (h[i] - c[i]) / rng > 0.55 and c[i] < sma * (1 + 0.002 * self.k)):
            return -1
        return 0


GODMODE_REGISTRY["deity_flow"] = GMDeityFlow
_b.REGISTRY["deity_flow"] = GMDeityFlow
_o.GRIDS["deity_flow"] = {"lb": [10, 20, 30], "k": [0.5, 1.0, 2.0], "hold": [6, 12, 24]}
