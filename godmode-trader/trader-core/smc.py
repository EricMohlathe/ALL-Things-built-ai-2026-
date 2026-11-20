"""smc: Smart Money Concepts and ICT price action on OHLC lists. Standard library only.

Every event carries `at`: the index of the bar whose CLOSE made it knowable. A
backtest at bar i may only use events with at <= i. That one rule is the whole
difference between a real test and a fantasy one.

  swings          fractal swing highs and lows (left/right bars); confirmed `right` bars later
  structure       BOS (continuation) and CHoCH (change of character) on closes beyond swings
  fvgs            fair value gaps (three-candle imbalance), with first touch, CE and full fill
  order_blocks    the last opposite candle before the leg that broke structure; mitigation,
                  invalidation, and the breaker block it becomes when invalidated
  liquidity       equal highs / equal lows (resting stops) and when they were swept
  sweeps          a wick through a level that closes back inside (stop hunt, SFP, turtle soup)
  displacement    a large-bodied, close-near-the-extreme bar (institutional intent)
  premium/discount, OTE (0.62-0.79), ICT killzones and Silver Bullet windows (New York time)
  analyze         one snapshot of all of it with a confluence score and a bias
"""

import math

KILLZONES = {  # New York wall-clock (ICT)
    "asia": ("20:00", "00:00"), "london_open": ("02:00", "05:00"), "ny_am": ("07:00", "10:00"),
    "london_close": ("10:00", "12:00"), "ny_pm": ("13:30", "16:00"),
}
SILVER_BULLET = {"london_sb": ("03:00", "04:00"), "am_sb": ("10:00", "11:00"), "pm_sb": ("14:00", "15:00")}


def _mins(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def in_window(ny_minutes, window):
    a, b = _mins(window[0]), _mins(window[1])
    if b <= a:
        return ny_minutes >= a or ny_minutes < b
    return a <= ny_minutes < b


def killzone(ny_minutes):
    for k, w in KILLZONES.items():
        if in_window(ny_minutes, w):
            return k
    return None


def silver_bullet(ny_minutes):
    for k, w in SILVER_BULLET.items():
        if in_window(ny_minutes, w):
            return k
    return None


# ---------------------------------------------------------------- swings and structure

def swings(h, l, left=2, right=2):
    """[{i, at, price, kind 'H'|'L'}]: a swing high is higher than `left` bars before and
    `right` bars after (ties allowed on the left). Known at i + right."""
    out = []
    for i in range(left, len(h) - right):
        if all(h[i] >= h[i - k] for k in range(1, left + 1)) and all(h[i] > h[i + k] for k in range(1, right + 1)):
            out.append({"i": i, "at": i + right, "price": h[i], "kind": "H"})
        if all(l[i] <= l[i - k] for k in range(1, left + 1)) and all(l[i] < l[i + k] for k in range(1, right + 1)):
            out.append({"i": i, "at": i + right, "price": l[i], "kind": "L"})
    out.sort(key=lambda s: (s["at"], s["i"]))
    return out


def structure(h, l, c, sw):
    """Market structure from closes beyond confirmed swings.
    Returns (events, trend) where events = [{at, kind 'BOS'|'CHoCH', dir 'up'|'down', level,
    swing_i}] and trend[i] in {'up', 'down', None} is the state after bar i closes."""
    events, trend = [], [None] * len(c)
    last_h = last_l = None
    state = None
    k = 0
    for i in range(len(c)):
        while k < len(sw) and sw[k]["at"] <= i:
            if sw[k]["kind"] == "H":
                last_h = dict(sw[k], broken=False)
            else:
                last_l = dict(sw[k], broken=False)
            k += 1
        if last_h and not last_h["broken"] and c[i] > last_h["price"]:
            events.append({"at": i, "kind": "CHoCH" if state == "down" else "BOS", "dir": "up",
                           "level": last_h["price"], "swing_i": last_h["i"]})
            last_h["broken"] = True
            state = "up"
        elif last_l and not last_l["broken"] and c[i] < last_l["price"]:
            events.append({"at": i, "kind": "CHoCH" if state == "up" else "BOS", "dir": "down",
                           "level": last_l["price"], "swing_i": last_l["i"]})
            last_l["broken"] = True
            state = "down"
        trend[i] = state
    return events, trend


# ---------------------------------------------------------------- imbalances and blocks

def fvgs(h, l, c, min_size=0.0):
    """Fair value gaps. Bullish: low[i+1] > high[i-1]; bearish: high[i+1] < low[i-1].
    Each: {i (the displacement candle), at (i+1), side, top, bottom, ce, touched_at, filled_at}."""
    out = []
    for i in range(1, len(c) - 1):
        if l[i + 1] > h[i - 1] and l[i + 1] - h[i - 1] > min_size:
            out.append({"i": i, "at": i + 1, "side": "bull", "top": l[i + 1], "bottom": h[i - 1]})
        elif h[i + 1] < l[i - 1] and l[i - 1] - h[i + 1] > min_size:
            out.append({"i": i, "at": i + 1, "side": "bear", "top": l[i - 1], "bottom": h[i + 1]})
    for g in out:
        g["ce"] = (g["top"] + g["bottom"]) / 2.0
        g["touched_at"] = g["filled_at"] = None
        for k in range(g["at"] + 1, len(c)):
            if g["side"] == "bull":
                if g["touched_at"] is None and l[k] <= g["top"]:
                    g["touched_at"] = k
                if l[k] <= g["bottom"]:
                    g["filled_at"] = k
                    break
            else:
                if g["touched_at"] is None and h[k] >= g["bottom"]:
                    g["touched_at"] = k
                if h[k] >= g["top"]:
                    g["filled_at"] = k
                    break
    return out


def order_blocks(o, h, l, c, events, max_back=20):
    """For each structure break, the last opposite-colored candle before the leg that broke
    it. Bullish OB = last down candle before an up break; zone = that candle's high..low.
    Each: {at (the break bar), i, side, top, bottom, mid, touched_at, invalid_at}; an OB whose
    far side is closed through becomes a breaker of the opposite side (invalid_at)."""
    out = []
    for ev in events:
        b = ev["at"]
        lo = max(0, min(ev.get("swing_i", b), b) - max_back)
        found = None
        for i in range(b - 1, lo - 1, -1):
            if ev["dir"] == "up" and c[i] < o[i]:
                found = i
                break
            if ev["dir"] == "down" and c[i] > o[i]:
                found = i
                break
        if found is None:
            continue
        ob = {"at": b, "i": found, "side": "bull" if ev["dir"] == "up" else "bear", "top": h[found],
              "bottom": l[found], "kind": ev["kind"]}
        ob["mid"] = (ob["top"] + ob["bottom"]) / 2.0
        ob["touched_at"] = ob["invalid_at"] = None
        for k in range(b + 1, len(c)):
            if ob["side"] == "bull":
                if ob["touched_at"] is None and l[k] <= ob["top"]:
                    ob["touched_at"] = k
                if c[k] < ob["bottom"]:
                    ob["invalid_at"] = k
                    break
            else:
                if ob["touched_at"] is None and h[k] >= ob["bottom"]:
                    ob["touched_at"] = k
                if c[k] > ob["top"]:
                    ob["invalid_at"] = k
                    break
        out.append(ob)
    return out


def breakers(obs):
    """Order blocks that failed: a closed-through bullish OB is a bearish breaker from the
    invalidation bar on (resistance), and the other way round."""
    return [{"at": ob["invalid_at"], "side": "bear" if ob["side"] == "bull" else "bull", "top": ob["top"],
             "bottom": ob["bottom"], "mid": ob["mid"], "from_ob_at": ob["at"]}
            for ob in obs if ob["invalid_at"] is not None]


# ---------------------------------------------------------------- liquidity

def liquidity(sw, h, l, tol):
    """Equal highs / lows: two or more swing points within `tol` (price). Each pool:
    {kind 'EQH'|'EQL', level, count, at (when the second touch was confirmed), swept_at}."""
    pools = []
    for kind in ("H", "L"):
        pts = [s for s in sw if s["kind"] == kind]
        used = set()
        for a in range(len(pts)):
            if a in used:
                continue
            group = [pts[a]]
            for b in range(a + 1, len(pts)):
                if b not in used and abs(pts[b]["price"] - pts[a]["price"]) <= tol:
                    group.append(pts[b])
                    used.add(b)
            if len(group) >= 2:
                used.add(a)
                level = max(g["price"] for g in group) if kind == "H" else min(g["price"] for g in group)
                at = sorted(g["at"] for g in group)[1]
                pools.append({"kind": "EQH" if kind == "H" else "EQL", "level": level, "count": len(group),
                              "at": at, "swept_at": None})
    for p in pools:
        for k in range(p["at"] + 1, len(h)):
            if (p["kind"] == "EQH" and h[k] > p["level"]) or (p["kind"] == "EQL" and l[k] < p["level"]):
                p["swept_at"] = k
                break
    return pools


def sweep_at(i, h, l, c, level, side):
    """Did bar i sweep `level` and close back? side 'high' (wick above, close below: bearish)
    or 'low' (wick below, close above: bullish)."""
    if side == "high":
        return h[i] > level and c[i] < level
    return l[i] < level and c[i] > level


def displacement(o, h, l, c, atr_list, i, k=1.5, close_frac=0.25):
    """+1 / -1 / 0: a body over k x ATR that closes in the last `close_frac` of its range."""
    a = atr_list[i]
    if a is None or a <= 0:
        return 0
    body = c[i] - o[i]
    rng = h[i] - l[i]
    if abs(body) < k * a or rng <= 0:
        return 0
    if body > 0 and (h[i] - c[i]) <= close_frac * rng:
        return 1
    if body < 0 and (c[i] - l[i]) <= close_frac * rng:
        return -1
    return 0


def premium_discount(hi, lo, price):
    """('premium'|'discount'|'equilibrium', position 0..1) in the dealing range lo..hi."""
    if hi <= lo:
        return "equilibrium", 0.5
    pos = (price - lo) / (hi - lo)
    if abs(pos - 0.5) < 0.02:
        return "equilibrium", pos
    return ("premium" if pos > 0.5 else "discount"), pos


def ote_zone(leg_from, leg_to):
    """The 0.62-0.79 retracement of a leg (leg_from -> leg_to), (low, high) of the zone."""
    a = leg_to - (leg_to - leg_from) * 0.62
    b = leg_to - (leg_to - leg_from) * 0.79
    return min(a, b), max(a, b)


# ---------------------------------------------------------------- one snapshot

def analyze(bars, ny_minutes_now=None, atr_n=14, swing=2, eq_tol_atr=0.1):
    """Everything above, as of the last closed bar of `bars` (a Bars object)."""
    import indicators as ind
    o, h, l, c = bars.o, bars.h, bars.l, bars.c
    n = len(c)
    if n < max(30, atr_n + 5):
        raise ValueError("need at least 30 bars for a structure read, got %d" % n)
    i = n - 1
    a = ind.atr(h, l, c, atr_n)
    av = a[i] or (sum(h[-20:]) - sum(l[-20:])) / 20.0
    sw = swings(h, l, swing, swing)
    events, trend = structure(h, l, c, sw)
    gaps = [g for g in fvgs(h, l, c, min_size=0.1 * av) if g["at"] <= i]
    obs = [ob for ob in order_blocks(o, h, l, c, events) if ob["at"] <= i]
    brk = [b for b in breakers(obs) if b["at"] <= i]
    pools = [p for p in liquidity([s for s in sw if s["at"] <= i], h, l, eq_tol_atr * av) if p["at"] <= i]
    price = c[i]
    open_gaps = [g for g in gaps if g["filled_at"] is None]
    live_obs = [ob for ob in obs if ob["invalid_at"] is None]
    above = lambda z: z["bottom"] > price  # noqa: E731
    below = lambda z: z["top"] < price  # noqa: E731
    near = lambda zs, f, key: sorted([z for z in zs if f(z)], key=key)[:3]  # noqa: E731
    hi_sw = [s["price"] for s in sw if s["kind"] == "H" and s["at"] <= i][-1:] or [max(h[-50:])]
    lo_sw = [s["price"] for s in sw if s["kind"] == "L" and s["at"] <= i][-1:] or [min(l[-50:])]
    rng_hi, rng_lo = max(h[-50:]), min(l[-50:])
    pd_zone, pd_pos = premium_discount(rng_hi, rng_lo, price)
    disp = displacement(o, h, l, c, a, i)
    recent_sweep = None
    for p in pools:
        if p["swept_at"] is not None and i - p["swept_at"] <= 5:
            k = p["swept_at"]
            back = c[k] < p["level"] if p["kind"] == "EQH" else c[k] > p["level"]
            recent_sweep = dict(p, closed_back=back, bars_ago=i - k)
    t = trend[i]
    score, why = 0, []
    if t:
        score += 1 if t == "up" else -1
        why.append("structure %s" % t)
    last_ev = events[-1] if events else None
    if last_ev and i - last_ev["at"] <= 10:
        s = 1 if last_ev["dir"] == "up" else -1
        score += s * (2 if last_ev["kind"] == "CHoCH" else 1)
        why.append("%s %s %d bars ago" % (last_ev["kind"], last_ev["dir"], i - last_ev["at"]))
    if pd_zone == "discount":
        score += 1
        why.append("price in discount (%.0f%% of the range)" % (pd_pos * 100))
    elif pd_zone == "premium":
        score -= 1
        why.append("price in premium (%.0f%% of the range)" % (pd_pos * 100))
    for g in open_gaps[-10:]:
        if g["bottom"] <= price <= g["top"]:
            score += 1 if g["side"] == "bull" else -1
            why.append("inside a %s FVG" % g["side"])
    for ob in live_obs[-10:]:
        if ob["bottom"] - 0.5 * av <= price <= ob["top"] + 0.5 * av:
            score += 1 if ob["side"] == "bull" else -1
            why.append("at a %s order block" % ob["side"])
    if recent_sweep and recent_sweep["closed_back"]:
        s = -1 if recent_sweep["kind"] == "EQH" else 1
        score += s * 2
        why.append("swept %s %d bars ago and closed back" % (recent_sweep["kind"], recent_sweep["bars_ago"]))
    if disp:
        score += disp
        why.append("displacement %s" % ("up" if disp > 0 else "down"))
    kz = killzone(ny_minutes_now) if ny_minutes_now is not None else None
    sb = silver_bullet(ny_minutes_now) if ny_minutes_now is not None else None
    bias = "bullish" if score >= 2 else "bearish" if score <= -2 else "neutral"
    return {"price": price, "atr": av, "trend": t, "last_event": last_ev,
            "events": events[-6:], "swing_high": hi_sw[0], "swing_low": lo_sw[0],
            "fvgs_above": near(open_gaps, above, lambda z: z["bottom"]),
            "fvgs_below": near(open_gaps, below, lambda z: -z["top"]),
            "obs_above": near(live_obs, above, lambda z: z["bottom"]),
            "obs_below": near(live_obs, below, lambda z: -z["top"]),
            "breakers": brk[-3:],
            "liquidity_above": sorted([p for p in pools if p["swept_at"] is None and p["level"] > price],
                                      key=lambda p: p["level"])[:3],
            "liquidity_below": sorted([p for p in pools if p["swept_at"] is None and p["level"] < price],
                                      key=lambda p: -p["level"])[:3],
            "recent_sweep": recent_sweep, "premium_discount": pd_zone, "range_position": round(pd_pos, 3),
            "dealing_range": [rng_lo, rng_hi], "ote_long": ote_zone(lo_sw[0], hi_sw[0]),
            "ote_short": ote_zone(hi_sw[0], lo_sw[0]), "displacement": disp, "killzone": kz,
            "silver_bullet": sb, "score": score, "bias": bias, "reasons": why}


def round_number(price, pip, every_pips=50):
    """The nearest 'big figure' style level: every 50 pips by default."""
    step = every_pips * pip
    return round(price / step) * step if step > 0 else price


def distance_atr(a, b, atr_value):
    return abs(a - b) / atr_value if atr_value else math.inf
