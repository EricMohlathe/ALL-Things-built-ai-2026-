"""The GODMODE setup library: GM01-GM26 (and two claude-trader strategies) as isolated,
testable Python rules for the Setup Lab. Standard library only.

Each setup mirrors one Expert Advisor of MT5_MasterLibrary/Experts/GODMODE and one cBot of
cTrader_MasterLibrary, so a setup can be researched here on years of free history and then
run on the platform. They are clean-room bar-based versions of the ideas, not ports of the
MQL5 / C# code: where an EA needs a footprint or real ticks, the Python version says what
it uses instead (the delta source of trader-core/orderflow.py).

Every setup:
  decides at a bar's CLOSE using only what was known then (events with at <= i),
  returns a Signal (side, stop, target, entry) or a Skip (a candidate it filtered, with why),
  carries `defaults` (its parameters) and `grid` (what the optimiser may vary),
  names its family (the compendium's split map) and its GM files.
"""

import bisect
import datetime
import math

import engine
import indicators as ind
import smc
import orderflow as of
import tradercore as tc

Signal, Skip = engine.Signal, engine.Skip
REGISTRY = {}


def register(cls):
    REGISTRY[cls.name] = cls
    return cls


class Setup(object):
    name = ""
    title = ""
    family = ""
    gm = ""
    defaults = {}
    grid = {}
    warmup = 60
    tf = "M15"
    classes = ("forex", "commodity", "index", "crypto")
    note = ""

    def prepare(self, ctx):
        pass

    def signal(self, ctx, i):
        return None

    @classmethod
    def files(cls):
        stem = cls.gm and "%s_%s" % (cls.gm, cls.__name__)
        return {"mt5": "MT5_MasterLibrary/Experts/GODMODE/%s.mq5" % stem if cls.gm.startswith("GM") else None,
                "ctrader": "cTrader_MasterLibrary/%s.cs" % stem if cls.gm.startswith("GM") else None}


# ---------------------------------------------------------------- shared helpers

def atr(ctx, i):
    return ctx.ind("atr", 14)[i]


def target_r(side, entry, stop, r):
    d = abs(entry - stop)
    return entry + r * d if side == "buy" else entry - r * d


def htf_trend(ctx, i, tf="1h", fast=50, slow=200):
    """'up' / 'down' / None from the last CLOSED higher-timeframe bar: close vs EMA fast vs EMA slow."""
    key = ("htf_ema", tf, fast, slow)
    if key not in ctx.state:
        hb, idx = ctx.htf(tf)
        ctx.state[key] = (idx, hb.c, ind.ema(hb.c, fast), ind.ema(hb.c, slow))
    idx, c, ef, es = ctx.state[key]
    k = idx[i]
    if k < 0 or ef[k] is None or es[k] is None:
        return None
    if c[k] > ef[k] > es[k]:
        return "up"
    if c[k] < ef[k] < es[k]:
        return "down"
    return None


def smc_cache(ctx, swing=2):
    key = ("smc", swing)
    if key not in ctx.state:
        o, h, l, c = ctx.o, ctx.h, ctx.l, ctx.c
        a = ctx.ind("atr", 14)
        sw = smc.swings(h, l, swing, swing)
        ev, trend = smc.structure(h, l, c, sw)
        med = sorted(x for x in a if x)[len([x for x in a if x]) // 2] if any(a) else 0.0
        gaps = smc.fvgs(h, l, c, min_size=0.1 * med)
        obs = smc.order_blocks(o, h, l, c, ev)
        st = {"swings": sw, "events": ev, "trend": trend, "fvgs": gaps, "obs": obs, "breakers": smc.breakers(obs),
              "sw_at": [x["at"] for x in sw]}
        for name, items, field in (("fvg_touch", gaps, "touched_at"), ("ob_touch", obs, "touched_at"),
                                   ("ev_at", ev, "at"), ("fvg_at", gaps, "at")):
            m = {}
            for it in items:
                if it.get(field) is not None:
                    m.setdefault(it[field], []).append(it)
            st[name] = m
        ctx.state[key] = st
    return ctx.state[key]


def swings_before(ctx, i, last=12):
    """The last `last` swings confirmed strictly before bar i (bisect, not a scan)."""
    st = smc_cache(ctx)
    k = bisect.bisect_left(st["sw_at"], i)
    return st["swings"][max(0, k - last):k]


def pivots(ctx):
    """{bar: [last alternating pivots]} at each bar where a swing is confirmed. Two highs in a
    row keep the higher one (two lows, the lower), so the list alternates H, L, H, L..."""
    if "pivots" not in ctx.state:
        pts, snap = [], {}
        for x in smc_cache(ctx)["swings"]:
            if pts and pts[-1]["kind"] == x["kind"]:
                if (x["kind"] == "H") == (x["price"] > pts[-1]["price"]):
                    pts[-1] = x
            else:
                pts.append(x)
                if len(pts) > 8:
                    pts.pop(0)
            snap[x["at"]] = list(pts)
        ctx.state["pivots"] = snap
    return ctx.state["pivots"]


class Zones(object):
    """Zones sorted by the bar they become known; `live(i)` walks a pointer forward and
    drops used or expired zones, so each bar costs only the zones alive at that moment."""

    def __init__(self, zones, max_age):
        self.z = sorted(zones, key=lambda z: z["at"])
        self.k, self.alive, self.max_age = 0, [], max_age

    def live(self, i):
        while self.k < len(self.z) and self.z[self.k]["at"] < i:
            self.alive.append(self.z[self.k])
            self.k += 1
        self.alive = [z for z in self.alive if not z["used"] and i - z["at"] <= self.max_age]
        return self.alive


def sessions(ctx, sname, range_minutes=None):
    """Per bar: the session instance it belongs to (dict with open/close/range_end as unix
    seconds and the local date), or None. Cached."""
    key = ("sess", sname, range_minutes)
    if key in ctx.state:
        return ctx.state[key]
    s = tc.session_def(sname, ctx.cfg)
    rng = int(range_minutes or s["range"])
    cache, out, last = {}, [None] * len(ctx.t), None
    tz = s["tz"]
    for i, t in enumerate(ctx.t):
        if last is not None and last["open"] <= t < last["close"]:
            out[i] = last
            continue
        d = tc.to_local(tz, tc.utc_of(t)).date()
        hit = None
        for day in (d - datetime.timedelta(days=1), d):
            if day not in cache:
                inst = tc.session_instance(sname, day, ctx.cfg)
                cache[day] = None if inst is None else {
                    "date": inst["date"], "open": tc.ts_of(inst["open_utc"]), "close": tc.ts_of(inst["close_utc"]),
                    "range_end": tc.ts_of(inst["open_utc"]) + rng * 60,
                    "cutoff": tc.ts_of(inst["close_utc"]) - int(ctx.cfg.get("entry_cutoff_minutes", 30)) * 60,
                    "flat": tc.ts_of(inst["close_utc"]) - int(ctx.cfg.get("flat_by_minutes", 5)) * 60}
            if cache[day] and cache[day]["open"] <= t < cache[day]["close"]:
                hit = cache[day]
        out[i] = last = hit
    ctx.state[key] = out
    return out


def day_levels(ctx):
    """Per bar: (previous day high, previous day low, previous close) on the trading-day grid."""
    if "pdl" not in ctx.state:
        off = ctx.day_offset()
        d = ctx.bars.resample_partial("1d", off)
        days = {d.t[k]: k for k in range(len(d))}
        out = []
        for t in ctx.t:
            k = days.get((t - off) // 86400 * 86400 + off, -1)
            out.append((d.h[k - 1], d.l[k - 1], d.c[k - 1]) if k >= 1 else None)
        ctx.state["pdl"] = out
    return ctx.state["pdl"]


def once_per_day(ctx, i, key):
    off = ctx.day_offset()
    day = (ctx.t[i] - off) // 86400
    k = ("once", key)
    if ctx.state.get(k) == day:
        return False
    ctx.state[k] = day
    return True


# ---------------------------------------------------------------- GM01-GM26

@register
class OpeningRangeBreakout(Setup):
    name, gm, family, tf = "GM01", "GM01", "breakout", "M5"
    title = "Opening-range breakout: the first close beyond the session's opening range"
    defaults = {"session": None, "range_minutes": None, "target_r": 2.0, "stop": "mid", "side": "both"}
    grid = {"target_r": [1.0, 1.5, 2.0, 3.0], "stop": ["mid", "far"]}

    def signal(self, ctx, i):
        sname = ctx.p["session"] or ctx.inst["session"]
        ss = sessions(ctx, sname, ctx.p["range_minutes"])
        s = ss[i]
        t_end = ctx.bars.end(i)
        if s is None or t_end <= s["range_end"] or t_end > s["cutoff"]:
            return None
        key = ("orb", s["date"])
        if key not in ctx.state:
            idx = [k for k in range(max(0, i - 400), i + 1) if ss[k] is s and ctx.t[k] < s["range_end"]]
            if not idx:
                ctx.state[key] = None
            else:
                ctx.state[key] = {"hi": max(ctx.h[k] for k in idx), "lo": min(ctx.l[k] for k in idx), "done": False}
        r = ctx.state[key]
        if r is None or r["done"]:
            return None
        c = ctx.c[i]
        side = "buy" if c > r["hi"] else "sell" if c < r["lo"] else None
        if side is None or (ctx.p["side"] != "both" and side != ctx.p["side"]):
            return None
        r["done"] = True
        stop = (r["hi"] + r["lo"]) / 2.0 if ctx.p["stop"] == "mid" else (r["lo"] if side == "buy" else r["hi"])
        return Signal(side, stop, target_r(side, c, stop, ctx.p["target_r"]), flat_at=s["flat"], tag=sname,
                      features={"range": r["hi"] - r["lo"]})


@register
class SessionSweepReversal(Setup):
    name, gm, family, tf = "GM02", "GM02", "liquidity", "M5"
    title = "Session sweep reversal: London sweeps the Asian range and closes back inside"
    defaults = {"asia_start": "00:00", "asia_end": "07:00", "zone": "Europe/London", "trade_until": "11:00",
                "target": "opposite", "target_r": 2.0, "buffer_atr": 0.1}
    grid = {"target_r": [1.5, 2.0, 3.0], "trade_until": ["10:00", "11:00", "12:00"]}
    classes = ("forex", "commodity", "index")

    def signal(self, ctx, i):
        loc = ctx.local(i, ctx.p["zone"])
        m = loc.hour * 60 + loc.minute
        a0, a1, until = (tc.parse_hhmm(ctx.p[k]) for k in ("asia_start", "asia_end", "trade_until"))
        day = loc.date()
        key = ("asia", day)
        if a0 <= m < a1:
            r = ctx.state.setdefault(key, {"hi": ctx.h[i], "lo": ctx.l[i], "done": False})
            r["hi"], r["lo"] = max(r["hi"], ctx.h[i]), min(r["lo"], ctx.l[i])
            return None
        r = ctx.state.get(key)
        if r is None or r["done"] or not (a1 <= m < until):
            return None
        buf = ctx.p["buffer_atr"] * (atr(ctx, i) or 0)
        if smc.sweep_at(i, ctx.h, ctx.l, ctx.c, r["hi"], "high"):
            r["done"] = True
            stop = ctx.h[i] + buf
            tgt = r["lo"] if ctx.p["target"] == "opposite" else target_r("sell", ctx.c[i], stop, ctx.p["target_r"])
            return Signal("sell", stop, tgt, max_bars=96, tag="asia high swept")
        if smc.sweep_at(i, ctx.h, ctx.l, ctx.c, r["lo"], "low"):
            r["done"] = True
            stop = ctx.l[i] - buf
            tgt = r["hi"] if ctx.p["target"] == "opposite" else target_r("buy", ctx.c[i], stop, ctx.p["target_r"])
            return Signal("buy", stop, tgt, max_bars=96, tag="asia low swept")
        return None


@register
class FVGEntry(Setup):
    name, gm, family = "GM03", "GM03", "smc"
    title = "FVG entry: first retrace into a fair value gap in the higher-timeframe trend"
    defaults = {"htf": "1h", "max_age": 30, "target_r": 2.0, "buffer_atr": 0.1}
    grid = {"target_r": [1.5, 2.0, 3.0], "max_age": [10, 30, 60]}

    def signal(self, ctx, i):
        st = smc_cache(ctx)
        for g in st["fvg_touch"].get(i, []):
            if i - g["at"] > ctx.p["max_age"] or (g["filled_at"] is not None and g["filled_at"] <= i):
                continue
            want = "up" if g["side"] == "bull" else "down"
            tr = htf_trend(ctx, i, ctx.p["htf"])
            if tr != want:
                return Skip("buy" if want == "up" else "sell", "FVG against the %s trend (%s)" % (ctx.p["htf"], tr))
            buf = ctx.p["buffer_atr"] * (atr(ctx, i) or 0)
            if g["side"] == "bull" and ctx.c[i] > g["bottom"]:
                stop = g["bottom"] - buf
                return Signal("buy", stop, target_r("buy", ctx.c[i], stop, ctx.p["target_r"]), max_bars=96, tag="FVG")
            if g["side"] == "bear" and ctx.c[i] < g["top"]:
                stop = g["top"] + buf
                return Signal("sell", stop, target_r("sell", ctx.c[i], stop, ctx.p["target_r"]), max_bars=96, tag="FVG")
        return None


@register
class OrderBlockReturn(Setup):
    name, gm, family = "GM04", "GM04", "smc"
    title = "Order-block return: first touch of the order block left by a structure break"
    defaults = {"htf": "1h", "max_age": 60, "target_r": 2.0, "buffer_atr": 0.1, "choch_only": False}
    grid = {"target_r": [1.5, 2.0, 3.0], "choch_only": [False, True]}

    def signal(self, ctx, i):
        for ob in smc_cache(ctx)["ob_touch"].get(i, []):
            if i - ob["at"] > ctx.p["max_age"] or (ob["invalid_at"] is not None and ob["invalid_at"] <= i):
                continue
            if ctx.p["choch_only"] and ob["kind"] != "CHoCH":
                continue
            side = "buy" if ob["side"] == "bull" else "sell"
            if htf_trend(ctx, i, ctx.p["htf"]) not in (None, "up" if side == "buy" else "down"):
                return Skip(side, "order block against the higher-timeframe trend")
            buf = ctx.p["buffer_atr"] * (atr(ctx, i) or 0)
            stop = ob["bottom"] - buf if side == "buy" else ob["top"] + buf
            if (side == "buy" and ctx.c[i] <= stop) or (side == "sell" and ctx.c[i] >= stop):
                continue
            return Signal(side, stop, target_r(side, ctx.c[i], stop, ctx.p["target_r"]), max_bars=96, tag=ob["kind"])
        return None


@register
class ICTUnicorn(Setup):
    name, gm, family = "GM05", "GM05", "smc"
    title = "ICT Unicorn: a breaker block overlapping a fair value gap, traded on the first touch"
    defaults = {"target_r": 2.0, "window": 12, "buffer_atr": 0.1}
    grid = {"target_r": [1.5, 2.0, 3.0]}

    def prepare(self, ctx):
        st = smc_cache(ctx)
        zones = []
        for b in st["breakers"]:
            for g in st["fvgs"]:
                if g["side"] == b["side"] and abs(g["at"] - b["at"]) <= ctx.p["window"]:
                    top, bot = min(b["top"], g["top"]), max(b["bottom"], g["bottom"])
                    if top > bot:
                        zones.append({"side": b["side"], "top": top, "bottom": bot, "at": max(b["at"], g["at"]),
                                      "used": False})
        ctx.state["unicorns"] = Zones(zones, 60)

    def signal(self, ctx, i):
        for z in ctx.state["unicorns"].live(i):
            if z["side"] == "bull" and ctx.l[i] <= z["top"] and ctx.c[i] > z["bottom"]:
                z["used"] = True
                stop = z["bottom"] - ctx.p["buffer_atr"] * (atr(ctx, i) or 0)
                return Signal("buy", stop, target_r("buy", ctx.c[i], stop, ctx.p["target_r"]), max_bars=96, tag="unicorn")
            if z["side"] == "bear" and ctx.h[i] >= z["bottom"] and ctx.c[i] < z["top"]:
                z["used"] = True
                stop = z["top"] + ctx.p["buffer_atr"] * (atr(ctx, i) or 0)
                return Signal("sell", stop, target_r("sell", ctx.c[i], stop, ctx.p["target_r"]), max_bars=96, tag="unicorn")
        return None


@register
class WyckoffSpring(Setup):
    name, gm, family = "GM06", "GM06", "wyckoff"
    title = "Wyckoff spring / upthrust: a sweep of a tight range that closes back inside, with delta divergence"
    defaults = {"lookback": 40, "max_width_atr": 6.0, "need_divergence": True, "target": "opposite", "target_r": 2.0}
    grid = {"lookback": [20, 40, 60], "need_divergence": [True, False]}

    def prepare(self, ctx):
        d, src = of.delta_of(ctx.bars)
        ctx.state["cvd"], ctx.state["delta_src"] = of.cvd(d), src

    def signal(self, ctx, i):
        n = ctx.p["lookback"]
        if i < n + 1:
            return None
        hi, lo = max(ctx.h[i - n:i]), min(ctx.l[i - n:i])
        a = atr(ctx, i) or 0
        if a <= 0 or hi - lo > ctx.p["max_width_atr"] * a:
            return None
        cvd = ctx.state["cvd"]
        if ctx.l[i] < lo and ctx.c[i] > lo and ctx.c[i] > (ctx.h[i] + ctx.l[i]) / 2:
            if ctx.p["need_divergence"] and cvd[i] < min(cvd[i - n:i]):
                return Skip("buy", "spring without bullish delta divergence")
            stop = ctx.l[i] - 0.1 * a
            tgt = hi if ctx.p["target"] == "opposite" else target_r("buy", ctx.c[i], stop, ctx.p["target_r"])
            return Signal("buy", stop, tgt, max_bars=120, tag="spring", features={"delta": ctx.state["delta_src"]})
        if ctx.h[i] > hi and ctx.c[i] < hi and ctx.c[i] < (ctx.h[i] + ctx.l[i]) / 2:
            if ctx.p["need_divergence"] and cvd[i] > max(cvd[i - n:i]):
                return Skip("sell", "upthrust without bearish delta divergence")
            stop = ctx.h[i] + 0.1 * a
            tgt = lo if ctx.p["target"] == "opposite" else target_r("sell", ctx.c[i], stop, ctx.p["target_r"])
            return Signal("sell", stop, tgt, max_bars=120, tag="upthrust", features={"delta": ctx.state["delta_src"]})
        return None


@register
class VWAPMeanReversion(Setup):
    name, gm, family = "GM07", "GM07", "mean_reversion"
    title = "VWAP mean reversion: fade a k-sigma stretch from the session VWAP in a non-trending market"
    defaults = {"k": 2.0, "max_adx": 25.0, "stop_atr": 1.0}
    grid = {"k": [1.5, 2.0, 2.5], "max_adx": [20.0, 25.0, 30.0]}

    def signal(self, ctx, i):
        vw = ctx.ind("vwap")
        a = atr(ctx, i)
        adx = ctx.ind("adx", 14)[0][i]
        if a is None or adx is None or vw["sd"][i] in (None, 0):
            return None
        z = (ctx.c[i] - vw["vwap"][i]) / vw["sd"][i]
        if abs(z) < ctx.p["k"]:
            return None
        side = "sell" if z > 0 else "buy"
        if adx > ctx.p["max_adx"]:
            return Skip(side, "trending (ADX %.0f)" % adx)
        stop = ctx.c[i] + ctx.p["stop_atr"] * a if side == "sell" else ctx.c[i] - ctx.p["stop_atr"] * a
        if (side == "buy" and vw["vwap"][i] <= ctx.c[i]) or (side == "sell" and vw["vwap"][i] >= ctx.c[i]):
            return None
        return Signal(side, stop, vw["vwap"][i], max_bars=48, tag="vwap %.1f sd" % z)


@register
class MomentumDisplacement(Setup):
    name, gm, family = "GM08", "GM08", "momentum"
    title = "Momentum displacement: a large-bodied close-at-the-extreme bar with the trend, continuation"
    defaults = {"k": 1.8, "htf": "1h", "target_r": 2.0, "stop": "half"}
    grid = {"k": [1.5, 1.8, 2.2], "target_r": [1.5, 2.0, 3.0]}

    def signal(self, ctx, i):
        d = smc.displacement(ctx.o, ctx.h, ctx.l, ctx.c, ctx.ind("atr", 14), i, ctx.p["k"])
        if not d:
            return None
        side = "buy" if d > 0 else "sell"
        if htf_trend(ctx, i, ctx.p["htf"]) != ("up" if d > 0 else "down"):
            return Skip(side, "displacement against the higher-timeframe trend")
        mid = (ctx.h[i] + ctx.l[i]) / 2.0
        stop = mid if ctx.p["stop"] == "half" else (ctx.l[i] if d > 0 else ctx.h[i])
        return Signal(side, stop, target_r(side, ctx.c[i], stop, ctx.p["target_r"]), max_bars=48, tag="displacement")


@register
class OrderFlowAbsorption(Setup):
    name, gm, family = "GM09", "GM09", "absorption"
    title = "Order-flow absorption at the edge of value: heavy volume, small range, delta against the candle"
    defaults = {"vol_z": 2.0, "range_atr": 0.6, "profile_bars": 96, "edge_atr": 0.5}
    grid = {"vol_z": [1.5, 2.0, 2.5]}
    note = "needs real volume; on forex the tick-volume / CLV proxy stands in (see delta source)"

    def prepare(self, ctx):
        d, src = of.delta_of(ctx.bars)
        ctx.state["delta"], ctx.state["src"] = d, src
        ctx.state["novol"] = not any(x > 0 for x in ctx.v)

    def signal(self, ctx, i):
        n = ctx.p["profile_bars"]
        if i < n:
            return None
        if ctx.state["novol"]:
            if not ctx.state.get("novol_said"):
                ctx.state["novol_said"] = True
                return Skip("buy", "this series has no volume: absorption cannot be measured")
            return None
        d = ctx.state["delta"]
        side = of.absorption(ctx.o, ctx.h, ctx.l, ctx.c, ctx.v, d, ctx.ind("atr", 14), i, ctx.p["vol_z"],
                             ctx.p["range_atr"])
        if side is None:
            return None
        prof = of.volume_profile(ctx.h[i - n:i], ctx.l[i - n:i], ctx.c[i - n:i], ctx.v[i - n:i])
        a = atr(ctx, i) or 0
        if side == "bullish":
            if abs(ctx.l[i] - prof["val"]) > ctx.p["edge_atr"] * a and ctx.l[i] > prof["val"]:
                return Skip("buy", "absorption away from the value-area low")
            stop = ctx.l[i] - 0.2 * a
            tgt = prof["poc"] if prof["poc"] > ctx.c[i] else target_r("buy", ctx.c[i], stop, 2.0)
            return Signal("buy", stop, tgt, max_bars=48, tag="absorption@VAL", features={"delta": ctx.state["src"]})
        if abs(ctx.h[i] - prof["vah"]) > ctx.p["edge_atr"] * a and ctx.h[i] < prof["vah"]:
            return Skip("sell", "absorption away from the value-area high")
        stop = ctx.h[i] + 0.2 * a
        tgt = prof["poc"] if prof["poc"] < ctx.c[i] else target_r("sell", ctx.c[i], stop, 2.0)
        return Signal("sell", stop, tgt, max_bars=48, tag="absorption@VAH", features={"delta": ctx.state["src"]})


@register
class PowerOfThree_CRT(Setup):
    name, gm, family = "GM10", "GM10", "liquidity"
    title = "Power of three / candle range theory: the new higher-timeframe candle sweeps the last one's extreme, then reverses"
    defaults = {"htf": "4h", "buffer_atr": 0.1}
    grid = {"htf": ["1h", "4h"]}

    def signal(self, ctx, i):
        hb, idx = ctx.htf(ctx.p["htf"])
        k = idx[i]
        if k < 1:
            return None
        prev_h, prev_l = hb.h[k], hb.l[k]
        key = ("crt", k)
        st = ctx.state.setdefault(key, {"swept_lo": None, "swept_hi": None, "done": False})
        if st["done"]:
            return None
        if ctx.l[i] < prev_l:
            st["swept_lo"] = min(st["swept_lo"] or ctx.l[i], ctx.l[i])
        if ctx.h[i] > prev_h:
            st["swept_hi"] = max(st["swept_hi"] or ctx.h[i], ctx.h[i])
        a = atr(ctx, i) or 0
        if st["swept_lo"] is not None and st["swept_hi"] is None and ctx.c[i] > prev_l:
            st["done"] = True
            return Signal("buy", st["swept_lo"] - ctx.p["buffer_atr"] * a, prev_h, max_bars=int(hb.step // ctx.bars.step) * 2,
                          tag="CRT low sweep")
        if st["swept_hi"] is not None and st["swept_lo"] is None and ctx.c[i] < prev_h:
            st["done"] = True
            return Signal("sell", st["swept_hi"] + ctx.p["buffer_atr"] * a, prev_l,
                          max_bars=int(hb.step // ctx.bars.step) * 2, tag="CRT high sweep")
        return None


@register
class SilverBullet(Setup):
    name, gm, family, tf = "GM11", "GM11", "smc", "M5"
    title = "ICT Silver Bullet: the first fair value gap inside the 10-11 (or 3-4, 14-15) New York window"
    defaults = {"windows": ["am_sb"], "target_r": 2.0, "buffer_atr": 0.1}
    grid = {"target_r": [1.5, 2.0, 3.0], "windows": [["am_sb"], ["london_sb"], ["am_sb", "pm_sb"]]}

    def signal(self, ctx, i):
        w = smc.silver_bullet(ctx.ny_minutes(i))
        if w not in ctx.p["windows"]:
            return None
        key = ("sbdone", ctx.ny(i).date(), w)
        if ctx.state.get(key):
            return None
        for g in smc_cache(ctx)["fvg_at"].get(i, []):
            ctx.state[key] = True
            a = atr(ctx, i) or 0
            if g["side"] == "bull":
                stop = ctx.l[g["i"] - 1] - ctx.p["buffer_atr"] * a
                return Signal("buy", stop, target_r("buy", g["top"], stop, ctx.p["target_r"]), entry=g["top"],
                              expiry_bars=12, max_bars=36, tag=w)
            stop = ctx.h[g["i"] - 1] + ctx.p["buffer_atr"] * a
            return Signal("sell", stop, target_r("sell", g["bottom"], stop, ctx.p["target_r"]), entry=g["bottom"],
                          expiry_bars=12, max_bars=36, tag=w)
        return None


@register
class OTE(Setup):
    name, gm, family = "GM12", "GM12", "smc"
    title = "Optimal trade entry: a limit at the 0.705 retracement of the leg that broke structure"
    defaults = {"level": 0.705, "expiry": 24, "target": "leg", "buffer_atr": 0.1}
    grid = {"level": [0.62, 0.705, 0.79], "expiry": [12, 24, 48]}

    def signal(self, ctx, i):
        st = smc_cache(ctx)
        for ev in st["ev_at"].get(i, []):
            if ev["kind"] != "BOS":
                continue
            lo_i = max(0, ev["swing_i"] - 30)
            a = atr(ctx, i) or 0
            if ev["dir"] == "up":
                leg_lo, leg_hi = min(ctx.l[lo_i:i + 1]), max(ctx.h[lo_i:i + 1])
                entry = leg_hi - (leg_hi - leg_lo) * ctx.p["level"]
                stop = leg_lo - ctx.p["buffer_atr"] * a
                return Signal("buy", stop, leg_hi if ctx.p["target"] == "leg" else target_r("buy", entry, stop, 2.0),
                              entry=entry, expiry_bars=ctx.p["expiry"], max_bars=96, tag="OTE")
            leg_lo, leg_hi = min(ctx.l[lo_i:i + 1]), max(ctx.h[lo_i:i + 1])
            entry = leg_lo + (leg_hi - leg_lo) * ctx.p["level"]
            stop = leg_hi + ctx.p["buffer_atr"] * a
            return Signal("sell", stop, leg_lo if ctx.p["target"] == "leg" else target_r("sell", entry, stop, 2.0),
                          entry=entry, expiry_bars=ctx.p["expiry"], max_bars=96, tag="OTE")
        return None


@register
class PriceAction(Setup):
    name, gm, family = "GM13", "GM13", "price_action"
    title = "Price action: a pin bar or an engulfing candle at a recent swing level, with the trend"
    defaults = {"htf": "1h", "level_atr": 0.3, "target_r": 2.0}
    grid = {"target_r": [1.5, 2.0, 3.0]}

    def signal(self, ctx, i):
        o, h, l, c = ctx.o, ctx.h, ctx.l, ctx.c
        a = atr(ctx, i) or 0
        rng = h[i] - l[i]
        if rng <= 0 or a <= 0:
            return None
        body = abs(c[i] - o[i])
        bull_pin = (min(o[i], c[i]) - l[i]) >= 0.6 * rng and body <= 0.3 * rng
        bear_pin = (h[i] - max(o[i], c[i])) >= 0.6 * rng and body <= 0.3 * rng
        bull_eng = c[i] > o[i] and c[i - 1] < o[i - 1] and c[i] >= o[i - 1] and o[i] <= c[i - 1]
        bear_eng = c[i] < o[i] and c[i - 1] > o[i - 1] and c[i] <= o[i - 1] and o[i] >= c[i - 1]
        sw = swings_before(ctx, i, 12)
        lows = [s["price"] for s in sw if s["kind"] == "L"]
        highs = [s["price"] for s in sw if s["kind"] == "H"]
        tr = htf_trend(ctx, i, ctx.p["htf"])
        if (bull_pin or bull_eng) and any(abs(l[i] - x) <= ctx.p["level_atr"] * a for x in lows):
            if tr == "down":
                return Skip("buy", "bullish pattern against the trend")
            stop = l[i] - 0.1 * a
            return Signal("buy", stop, target_r("buy", c[i], stop, ctx.p["target_r"]), max_bars=60,
                          tag="pin" if bull_pin else "engulf")
        if (bear_pin or bear_eng) and any(abs(h[i] - x) <= ctx.p["level_atr"] * a for x in highs):
            if tr == "up":
                return Skip("sell", "bearish pattern against the trend")
            stop = h[i] + 0.1 * a
            return Signal("sell", stop, target_r("sell", c[i], stop, ctx.p["target_r"]), max_bars=60,
                          tag="pin" if bear_pin else "engulf")
        return None


@register
class TurtleSoupSFP(Setup):
    name, gm, family = "GM14", "GM14", "liquidity"
    title = "Turtle soup / swing failure: a break of the N-bar extreme that closes back inside"
    defaults = {"lookback": 20, "target": "mid", "target_r": 2.0}
    grid = {"lookback": [10, 20, 50], "target": ["mid", "r"]}

    def signal(self, ctx, i):
        n = ctx.p["lookback"]
        if i <= n:
            return None
        hi, lo = max(ctx.h[i - n:i]), min(ctx.l[i - n:i])
        a = atr(ctx, i) or 0
        if smc.sweep_at(i, ctx.h, ctx.l, ctx.c, lo, "low"):
            stop = ctx.l[i] - 0.1 * a
            tgt = (hi + lo) / 2 if ctx.p["target"] == "mid" else target_r("buy", ctx.c[i], stop, ctx.p["target_r"])
            if tgt > ctx.c[i]:
                return Signal("buy", stop, tgt, max_bars=60, tag="SFP low")
        if smc.sweep_at(i, ctx.h, ctx.l, ctx.c, hi, "high"):
            stop = ctx.h[i] + 0.1 * a
            tgt = (hi + lo) / 2 if ctx.p["target"] == "mid" else target_r("sell", ctx.c[i], stop, ctx.p["target_r"])
            if tgt < ctx.c[i]:
                return Signal("sell", stop, tgt, max_bars=60, tag="SFP high")
        return None


@register
class SupplyDemand(Setup):
    name, gm, family = "GM15", "GM15", "zones"
    title = "Supply and demand: the first return to a base that launched a strong move"
    defaults = {"base_max": 3, "launch_atr": 1.5, "max_age": 100, "target_r": 2.0}
    grid = {"launch_atr": [1.2, 1.5, 2.0], "target_r": [1.5, 2.0, 3.0]}

    def prepare(self, ctx):
        o, h, l, c = ctx.o, ctx.h, ctx.l, ctx.c
        a = ctx.ind("atr", 14)
        zones = []
        for k in range(5, len(c)):
            if a[k] is None:
                continue
            body = c[k] - o[k]
            if abs(body) < ctx.p["launch_atr"] * a[k]:
                continue
            base = [j for j in range(k - ctx.p["base_max"], k) if abs(c[j] - o[j]) <= 0.5 * a[k]]
            if not base or base[-1] != k - 1:
                continue
            top, bot = max(h[j] for j in base), min(l[j] for j in base)
            zones.append({"side": "bull" if body > 0 else "bear", "top": top, "bottom": bot, "at": k, "used": False})
        ctx.state["zones"] = Zones(zones, ctx.p["max_age"])

    def signal(self, ctx, i):
        for z in ctx.state["zones"].live(i):
            a = atr(ctx, i) or 0
            if z["side"] == "bull" and ctx.l[i] <= z["top"] and ctx.c[i] > z["bottom"]:
                z["used"] = True
                stop = z["bottom"] - 0.1 * a
                return Signal("buy", stop, target_r("buy", ctx.c[i], stop, ctx.p["target_r"]), max_bars=96, tag="demand")
            if z["side"] == "bear" and ctx.h[i] >= z["bottom"] and ctx.c[i] < z["top"]:
                z["used"] = True
                stop = z["top"] + 0.1 * a
                return Signal("sell", stop, target_r("sell", ctx.c[i], stop, ctx.p["target_r"]), max_bars=96, tag="supply")
            if (z["side"] == "bull" and ctx.c[i] < z["bottom"]) or (z["side"] == "bear" and ctx.c[i] > z["top"]):
                z["used"] = True
        return None


@register
class MarketStructure(Setup):
    name, gm, family = "GM16", "GM16", "smc"
    title = "Market structure: trade the change of character (or the break of structure) on its close"
    defaults = {"event": "CHoCH", "target_r": 2.0, "buffer_atr": 0.1}
    grid = {"event": ["CHoCH", "BOS"], "target_r": [1.5, 2.0, 3.0]}

    def signal(self, ctx, i):
        st = smc_cache(ctx)
        for ev in st["ev_at"].get(i, []):
            if ev["kind"] != ctx.p["event"]:
                continue
            a = atr(ctx, i) or 0
            prior = [x for x in swings_before(ctx, i + 1, 20) if x["kind"] == ("L" if ev["dir"] == "up" else "H")]
            if not prior:
                return None
            side = "buy" if ev["dir"] == "up" else "sell"
            stop = prior[-1]["price"] - ctx.p["buffer_atr"] * a if side == "buy" else prior[-1]["price"] + ctx.p["buffer_atr"] * a
            if not engine.risk_ok(abs(ctx.c[i] - stop), ctx, i):
                return Skip(side, "the structural stop is too far or too tight")
            return Signal(side, stop, target_r(side, ctx.c[i], stop, ctx.p["target_r"]), max_bars=96, tag=ev["kind"])
        return None


@register
class InitialBalance(Setup):
    name, gm, family, tf = "GM17", "GM17", "breakout", "M5"
    title = "Initial balance: a close beyond the session's first hour, aiming for a 1x extension"
    defaults = {"session": None, "ib_minutes": 60, "extension": 1.0}
    grid = {"extension": [0.5, 1.0, 1.5], "ib_minutes": [30, 60]}

    def signal(self, ctx, i):
        sname = ctx.p["session"] or ctx.inst["session"]
        ss = sessions(ctx, sname, ctx.p["ib_minutes"])
        s = ss[i]
        if s is None or ctx.bars.end(i) <= s["range_end"] or ctx.bars.end(i) > s["cutoff"]:
            return None
        key = ("ib", s["date"])
        if key not in ctx.state:
            idx = [k for k in range(max(0, i - 400), i + 1) if ss[k] is s and ctx.t[k] < s["range_end"]]
            ctx.state[key] = {"hi": max(ctx.h[k] for k in idx), "lo": min(ctx.l[k] for k in idx), "done": False} if idx else None
        r = ctx.state[key]
        if r is None or r["done"]:
            return None
        width = r["hi"] - r["lo"]
        mid = (r["hi"] + r["lo"]) / 2.0
        if ctx.c[i] > r["hi"]:
            r["done"] = True
            return Signal("buy", mid, r["hi"] + ctx.p["extension"] * width, flat_at=s["flat"], tag="IB up")
        if ctx.c[i] < r["lo"]:
            r["done"] = True
            return Signal("sell", mid, r["lo"] - ctx.p["extension"] * width, flat_at=s["flat"], tag="IB down")
        return None


@register
class Harmonic(Setup):
    name, gm, family = "GM18", "GM18", "patterns"
    title = "Harmonic AB=CD: equal legs with a 0.382-0.886 BC retracement, reversal at D"
    defaults = {"tolerance": 0.12, "target_fib": 0.618}
    grid = {"tolerance": [0.08, 0.12, 0.2]}

    def signal(self, ctx, i):
        pts = pivots(ctx).get(i)
        if not pts or len(pts) < 4 or pts[-1]["at"] != i:
            return None
        A, B, C, Dp = pts[-4:]
        ab, bc, cd = abs(A["price"] - B["price"]), abs(B["price"] - C["price"]), abs(C["price"] - Dp["price"])
        if ab <= 0 or not (0.382 <= bc / ab <= 0.886) or abs(cd / ab - 1) > ctx.p["tolerance"]:
            return None
        a = atr(ctx, i) or 0
        if Dp["kind"] == "L" and A["kind"] == "H" and Dp["price"] < B["price"]:
            stop = Dp["price"] - 0.5 * a
            return Signal("buy", stop, Dp["price"] + ctx.p["target_fib"] * (A["price"] - Dp["price"]), max_bars=120,
                          tag="AB=CD bull")
        if Dp["kind"] == "H" and A["kind"] == "L" and Dp["price"] > B["price"]:
            stop = Dp["price"] + 0.5 * a
            return Signal("sell", stop, Dp["price"] - ctx.p["target_fib"] * (Dp["price"] - A["price"]), max_bars=120,
                          tag="AB=CD bear")
        return None


@register
class RSI2MeanReversion(Setup):
    name, gm, family, tf = "GM19", "GM19", "mean_reversion", "H1"
    title = "RSI(2) mean reversion (Connors): buy a deep dip above the 200 average, out when price reclaims the 5 average"
    defaults = {"entry": 10.0, "trend": 200, "exit_ma": 5, "stop_atr": 2.5, "max_bars": 10}
    grid = {"entry": [5.0, 10.0, 15.0], "stop_atr": [2.0, 3.0]}
    warmup = 210

    def signal(self, ctx, i):
        r2 = ctx.ind("rsi", 2)[i]
        ma = ctx.ind("sma", ctx.p["trend"])[i]
        a = atr(ctx, i)
        if r2 is None or ma is None or a is None:
            return None
        if ctx.c[i] > ma and r2 < ctx.p["entry"]:
            return Signal("buy", ctx.c[i] - ctx.p["stop_atr"] * a, None, max_bars=ctx.p["max_bars"], tag="rsi2 dip")
        if ctx.c[i] < ma and r2 > 100 - ctx.p["entry"]:
            return Signal("sell", ctx.c[i] + ctx.p["stop_atr"] * a, None, max_bars=ctx.p["max_bars"], tag="rsi2 pop")
        return None

    def exit_rule(self, ctx, i, pos):
        m = ctx.ind("sma", ctx.p["exit_ma"])[i]
        return m is not None and ((pos["side"] == "buy" and ctx.c[i] > m) or (pos["side"] == "sell" and ctx.c[i] < m))


@register
class GapFade(Setup):
    name, gm, family = "GM20", "GM20", "gaps"
    title = "Gap fade: a session that opens more than k ATR away from the last close, faded back toward it"
    defaults = {"min_gap_atr": 0.5, "stop_mult": 1.0, "min_hours": 1.0}
    grid = {"min_gap_atr": [0.3, 0.5, 1.0]}

    def signal(self, ctx, i):
        if ctx.t[i] - ctx.t[i - 1] < ctx.p["min_hours"] * 3600:
            return None
        gap = ctx.o[i] - ctx.c[i - 1]
        a = atr(ctx, i - 1) or 0
        if a <= 0 or abs(gap) < ctx.p["min_gap_atr"] * a:
            return None
        if gap > 0 and ctx.c[i] < ctx.o[i]:
            return Signal("sell", ctx.h[i] + ctx.p["stop_mult"] * abs(gap) * 0.5, ctx.c[i - 1], max_bars=48, tag="gap up")
        if gap < 0 and ctx.c[i] > ctx.o[i]:
            return Signal("buy", ctx.l[i] - ctx.p["stop_mult"] * abs(gap) * 0.5, ctx.c[i - 1], max_bars=48, tag="gap down")
        return None


@register
class PrevDayLevels(Setup):
    name, gm, family = "GM21", "GM21", "liquidity"
    title = "Previous-day levels: a sweep of yesterday's high or low that closes back, toward the middle"
    defaults = {"target": "mid", "target_r": 2.0, "buffer_atr": 0.1}
    grid = {"target": ["mid", "r"]}

    def signal(self, ctx, i):
        lv = day_levels(ctx)[i]
        if lv is None:
            return None
        pdh, pdl, _ = lv
        a = atr(ctx, i) or 0
        mid = (pdh + pdl) / 2.0
        if smc.sweep_at(i, ctx.h, ctx.l, ctx.c, pdh, "high") and once_per_day(ctx, i, "pdh"):
            stop = ctx.h[i] + ctx.p["buffer_atr"] * a
            tgt = mid if ctx.p["target"] == "mid" and mid < ctx.c[i] else target_r("sell", ctx.c[i], stop, ctx.p["target_r"])
            return Signal("sell", stop, tgt, max_bars=96, tag="PDH sweep")
        if smc.sweep_at(i, ctx.h, ctx.l, ctx.c, pdl, "low") and once_per_day(ctx, i, "pdl"):
            stop = ctx.l[i] - ctx.p["buffer_atr"] * a
            tgt = mid if ctx.p["target"] == "mid" and mid > ctx.c[i] else target_r("buy", ctx.c[i], stop, ctx.p["target_r"])
            return Signal("buy", stop, tgt, max_bars=96, tag="PDL sweep")
        return None


@register
class EMAPullback(Setup):
    name, gm, family = "GM22", "GM22", "trend"
    title = "EMA pullback: an EMA20/50/200 stack with a rising ADX, entered on a stochastic pullback"
    defaults = {"htf": "4h", "adx_min": 22.0, "stoch_low": 25.0, "sl_atr": 1.2, "target_r": 2.5}
    grid = {"adx_min": [18.0, 22.0, 28.0], "target_r": [1.5, 2.5, 3.5]}
    note = "the claude-trader EURUSD baseline (MIT): H4 stack + ADX rising + RSI 58/42, H1/M15 stochastic pullback"

    def prepare(self, ctx):
        hb, idx = ctx.htf(ctx.p["htf"])
        ctx.state["h4"] = (idx, hb.c, ind.ema(hb.c, 20), ind.ema(hb.c, 50), ind.ema(hb.c, 200),
                           ind.adx(hb.h, hb.l, hb.c)[0], ind.rsi(hb.c), ind.atr(hb.h, hb.l, hb.c))

    def signal(self, ctx, i):
        idx, c, e20, e50, e200, adx, rsi, hatr = ctx.state["h4"]
        k = idx[i]
        if k < 1 or None in (e200[k], adx[k], adx[k - 1], rsi[k]):
            return None
        rising = adx[k] > ctx.p["adx_min"] and adx[k] > adx[k - 1]
        bull = c[k] > e20[k] > e50[k] and c[k] > e200[k] and rsi[k] > 58 and rising
        bear = c[k] < e20[k] < e50[k] and c[k] < e200[k] and rsi[k] < 42 and rising
        sk = ctx.ind("stoch", 14)[0]
        if sk[i] is None or sk[i - 1] is None:
            return None
        sl = ctx.p["sl_atr"] * hatr[k]
        if bull and sk[i - 1] < ctx.p["stoch_low"] <= sk[i]:
            return Signal("buy", ctx.c[i] - sl, ctx.c[i] + ctx.p["target_r"] * sl, max_bars=60, tag="pullback long")
        if bear and sk[i - 1] > 100 - ctx.p["stoch_low"] >= sk[i]:
            return Signal("sell", ctx.c[i] + sl, ctx.c[i] - ctx.p["target_r"] * sl, max_bars=60, tag="pullback short")
        return None


@register
class OpeningGapCE(Setup):
    name, gm, family = "GM23", "GM23", "gaps"
    title = "Opening gap CE: price returns to the consequent encroachment (midpoint) of the new-day / new-week opening gap"
    defaults = {"min_gap_atr": 0.2, "min_hours": 1.0, "target_r": 2.0, "max_age": 200}
    grid = {"target_r": [1.5, 2.0, 3.0]}

    def signal(self, ctx, i):
        if ctx.t[i] - ctx.t[i - 1] >= ctx.p["min_hours"] * 3600:
            a = atr(ctx, i - 1) or 0
            g = (ctx.c[i - 1], ctx.o[i])
            if a > 0 and abs(g[1] - g[0]) >= ctx.p["min_gap_atr"] * a:
                ctx.state["gap"] = {"top": max(g), "bottom": min(g), "ce": sum(g) / 2.0, "at": i,
                                    "above": ctx.o[i] > sum(g) / 2.0, "used": False}
            return None
        gp = ctx.state.get("gap")
        if not gp or gp["used"] or i - gp["at"] > ctx.p["max_age"]:
            return None
        a = atr(ctx, i) or 0
        if gp["above"] and ctx.l[i] <= gp["ce"] and ctx.c[i] > gp["ce"]:
            gp["used"] = True
            stop = gp["bottom"] - 0.1 * a
            return Signal("buy", stop, target_r("buy", ctx.c[i], stop, ctx.p["target_r"]), max_bars=96, tag="gap CE support")
        if not gp["above"] and ctx.h[i] >= gp["ce"] and ctx.c[i] < gp["ce"]:
            gp["used"] = True
            stop = gp["top"] + 0.1 * a
            return Signal("sell", stop, target_r("sell", ctx.c[i], stop, ctx.p["target_r"]), max_bars=96, tag="gap CE resistance")
        return None


@register
class SMTDivergence(Setup):
    name, gm, family = "GM24", "GM24", "intermarket"
    title = "SMT divergence: this market sweeps its low while the correlated one does not (or the highs)"
    defaults = {"lookback": 20, "target_r": 2.0, "inverse": False}
    grid = {"lookback": [10, 20, 40]}
    note = "pass the correlated market's bars as cfg['smt_bars'] (lab.py --with GBPUSD); inverse=True for USDCHF vs EURUSD"

    def prepare(self, ctx):
        other = ctx.cfg.get("smt_bars")
        ctx.state["other"] = None
        if other is not None:
            m = {other.t[k]: k for k in range(len(other))}
            ctx.state["other"] = (other, [m.get(t) for t in ctx.t])

    def signal(self, ctx, i):
        n = ctx.p["lookback"]
        if ctx.state["other"] is None:
            if not ctx.state.get("smt_warned"):
                ctx.state["smt_warned"] = True
                return Skip("buy", "needs a correlated market (cfg smt_bars)")
            return None
        ob, idx = ctx.state["other"]
        if i < n:
            return None
        k = idx[i]
        ks = [idx[j] for j in range(i - n, i)]
        if k is None or None in ks:
            return None
        # with an inverse pair (USDCHF vs EURUSD) our low lines up with their high
        their_new_low = (ob.h[k] > max(ob.h[j] for j in ks)) if ctx.p["inverse"] else (ob.l[k] < min(ob.l[j] for j in ks))
        their_new_high = (ob.l[k] < min(ob.l[j] for j in ks)) if ctx.p["inverse"] else (ob.h[k] > max(ob.h[j] for j in ks))
        my_low = ctx.l[i] < min(ctx.l[i - n:i])
        my_high = ctx.h[i] > max(ctx.h[i - n:i])
        a = atr(ctx, i) or 0
        if my_low and not their_new_low and ctx.c[i] > ctx.o[i]:
            stop = ctx.l[i] - 0.1 * a
            return Signal("buy", stop, target_r("buy", ctx.c[i], stop, ctx.p["target_r"]), max_bars=60, tag="bull SMT")
        if my_high and not their_new_high and ctx.c[i] < ctx.o[i]:
            stop = ctx.h[i] + 0.1 * a
            return Signal("sell", stop, target_r("sell", ctx.c[i], stop, ctx.p["target_r"]), max_bars=60, tag="bear SMT")
        return None


@register
class BreakoutRetest(Setup):
    name, gm, family = "GM25", "GM25", "breakout"
    title = "Breakout and retest: a close beyond the N-bar range, then the first retest of the broken level holds"
    defaults = {"lookback": 30, "retest_bars": 15, "tol_atr": 0.2, "target_r": 2.0}
    grid = {"lookback": [20, 30, 60], "target_r": [1.5, 2.0, 3.0]}

    def signal(self, ctx, i):
        n = ctx.p["lookback"]
        if i <= n:
            return None
        a = atr(ctx, i) or 0
        lvl = ctx.state.get("lvl")
        hi, lo = max(ctx.h[i - n:i]), min(ctx.l[i - n:i])
        if ctx.c[i] > hi:
            ctx.state["lvl"] = {"side": "buy", "level": hi, "at": i}
            return None
        if ctx.c[i] < lo:
            ctx.state["lvl"] = {"side": "sell", "level": lo, "at": i}
            return None
        if not lvl or i - lvl["at"] > ctx.p["retest_bars"]:
            return None
        tol = ctx.p["tol_atr"] * a
        if lvl["side"] == "buy" and ctx.l[i] <= lvl["level"] + tol and ctx.c[i] > lvl["level"]:
            ctx.state["lvl"] = None
            stop = min(ctx.l[i], lvl["level"]) - 0.3 * a
            return Signal("buy", stop, target_r("buy", ctx.c[i], stop, ctx.p["target_r"]), max_bars=96, tag="retest")
        if lvl["side"] == "sell" and ctx.h[i] >= lvl["level"] - tol and ctx.c[i] < lvl["level"]:
            ctx.state["lvl"] = None
            stop = max(ctx.h[i], lvl["level"]) + 0.3 * a
            return Signal("sell", stop, target_r("sell", ctx.c[i], stop, ctx.p["target_r"]), max_bars=96, tag="retest")
        return None


@register
class ConfluenceStack(Setup):
    name, gm, family = "GM26", "GM26", "confluence"
    title = "Confluence stack: trade only when at least k independent factors agree (gates, not one pooled score)"
    defaults = {"min_score": 4, "stop_atr": 1.5, "target_r": 2.0, "htf": "1h"}
    grid = {"min_score": [3, 4, 5], "target_r": [1.5, 2.0, 3.0]}

    def signal(self, ctx, i):
        st = smc_cache(ctx)
        a = atr(ctx, i)
        if a is None:
            return None
        score, why = 0, []
        tr = htf_trend(ctx, i, ctx.p["htf"])
        score += {"up": 1, "down": -1}.get(tr, 0)
        score += {"up": 1, "down": -1}.get(st["trend"][i], 0)
        lo, hi = min(ctx.l[max(0, i - 50):i + 1]), max(ctx.h[max(0, i - 50):i + 1])
        zone, _ = smc.premium_discount(hi, lo, ctx.c[i])
        score += {"discount": 1, "premium": -1}.get(zone, 0)
        vw = ctx.ind("vwap")["vwap"][i]
        score += 1 if ctx.c[i] > vw else -1
        r = ctx.ind("rsi", 14)[i] or 50
        score += 1 if r > 55 else -1 if r < 45 else 0
        d = smc.displacement(ctx.o, ctx.h, ctx.l, ctx.c, ctx.ind("atr", 14), i)
        score += d
        kz = smc.killzone(ctx.ny_minutes(i))
        in_kz = kz in ("london_open", "ny_am")
        if abs(score) < ctx.p["min_score"]:
            return None
        side = "buy" if score > 0 else "sell"
        if not in_kz:
            return Skip(side, "score %d outside the London / New York killzones" % score)
        if not once_per_day(ctx, i, "stack"):
            return None
        stop = ctx.c[i] - ctx.p["stop_atr"] * a if side == "buy" else ctx.c[i] + ctx.p["stop_atr"] * a
        return Signal(side, stop, target_r(side, ctx.c[i], stop, ctx.p["target_r"]), max_bars=60,
                      tag="score %d" % score, features={"score": score})


# ---------------------------------------------------------------- claude-trader strategies (MIT)

@register
class TrendSMC(Setup):
    name, gm, family, tf = "CT01", "CT01", "trend", "H1"
    title = "claude-trader SMC trend: H4 EMA stack, ADX rising, RSI 58/42 (50 with SMC), entered at an H1 FVG or OB, liquidity target"
    defaults = {"htf": "4h", "adx_min": 25.0, "sl_atr": 1.2, "tp_mult": 2.5}
    grid = {"adx_min": [20.0, 25.0, 30.0], "tp_mult": [2.0, 2.5, 3.0]}
    note = "after claude-trader backtest.py signal_gold_smc (MIT)"

    def prepare(self, ctx):
        EMAPullback.prepare(self, ctx)

    def signal(self, ctx, i):
        idx, c, e20, e50, e200, adx, rsi, hatr = ctx.state["h4"]
        k = idx[i]
        if k < 1 or None in (e200[k], adx[k], adx[k - 1], rsi[k], hatr[k]):
            return None
        rising = adx[k] > ctx.p["adx_min"] and adx[k] > adx[k - 1]
        st = smc_cache(ctx)
        touch_bull = any(g["side"] == "bull" for g in st["fvg_touch"].get(i, [])) or \
            any(ob["side"] == "bull" for ob in st["ob_touch"].get(i, []))
        touch_bear = any(g["side"] == "bear" for g in st["fvg_touch"].get(i, [])) or \
            any(ob["side"] == "bear" for ob in st["ob_touch"].get(i, []))
        bull = c[k] > e20[k] > e50[k] > e200[k] and rising and (rsi[k] > 58 or (touch_bull and rsi[k] > 50))
        bear = c[k] < e20[k] < e50[k] < e200[k] and rising and (rsi[k] < 42 or (touch_bear and rsi[k] < 50))
        sl = ctx.p["sl_atr"] * hatr[k]
        if bull and touch_bull:
            return Signal("buy", ctx.c[i] - sl, ctx.c[i] + ctx.p["tp_mult"] * sl, max_bars=60, tag="trend+SMC")
        if bear and touch_bear:
            return Signal("sell", ctx.c[i] + sl, ctx.c[i] - ctx.p["tp_mult"] * sl, max_bars=60, tag="trend+SMC")
        return None


@register
class IchimokuTrend(Setup):
    name, gm, family = "CT02", "CT02", "trend"
    title = "claude-trader Ichimoku trend (the USDJPY agent): price above the cloud, tenkan over kijun, ADX > 25"
    defaults = {"adx_min": 25.0, "sl_atr": 1.5, "tp_mult": 2.5}
    grid = {"adx_min": [20.0, 25.0, 30.0]}
    warmup = 80

    def signal(self, ctx, i):
        ten, kij, ca, cb = ctx.ind("ichimoku")
        adx = ctx.ind("adx", 14)[0]
        a = atr(ctx, i)
        if None in (ten[i], kij[i], ca[i], cb[i], adx[i], ten[i - 1], kij[i - 1], a):
            return None
        top, bot = max(ca[i], cb[i]), min(ca[i], cb[i])
        cross_up = ten[i - 1] <= kij[i - 1] and ten[i] > kij[i]
        cross_dn = ten[i - 1] >= kij[i - 1] and ten[i] < kij[i]
        sl = ctx.p["sl_atr"] * a
        if cross_up and ctx.c[i] > top and adx[i] > ctx.p["adx_min"]:
            return Signal("buy", ctx.c[i] - sl, ctx.c[i] + ctx.p["tp_mult"] * sl, max_bars=60, tag="TK cross up")
        if cross_dn and ctx.c[i] < bot and adx[i] > ctx.p["adx_min"]:
            return Signal("sell", ctx.c[i] + sl, ctx.c[i] - ctx.p["tp_mult"] * sl, max_bars=60, tag="TK cross down")
        return None


FAMILIES = {}
for _n, _c in REGISTRY.items():
    FAMILIES.setdefault(_c.family, []).append(_n)


def get(name):
    key = str(name).upper()
    if key not in REGISTRY:
        raise tc.TraderError("unknown setup %r: one of %s" % (name, ", ".join(sorted(REGISTRY))))
    return REGISTRY[key]()


def grid_of(setup, keys=None):
    """Every combination of the setup's grid (or the named keys only), as dicts."""
    g = {k: v for k, v in setup.grid.items() if keys is None or k in keys}
    combos = [{}]
    for k, vals in sorted(g.items()):
        combos = [dict(c, **{k: v}) for c in combos for v in vals]
    return combos
