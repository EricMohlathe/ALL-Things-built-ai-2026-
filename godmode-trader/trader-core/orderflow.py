"""orderflow: volume profile, delta and cumulative delta, divergence and absorption.
Standard library only.

Delta sources, best first, and the tools always say which one they used:
  taker   Binance klines carry the taker-buy volume: real aggressor delta for crypto
          (buy = taker buy, sell = volume - taker buy)
  tick    Dukascopy ticks: the tick rule on the mid price (uptick = buy, downtick =
          sell, unchanged = the last sign); delta in ticks, not contracts
  clv     any OHLCV bar: volume x the close location value, 2(c - l)/(h - l) - 1.
          A shape proxy, not order flow: treat it as such
A forex feed has no exchange volume at all; tick counts stand in for it.

  volume_profile   POC, value area (VAH/VAL, 70 %), high- and low-volume nodes, shape
  cvd              running sum of delta (per session if you pass session keys)
  divergence       price makes a new extreme that cumulative delta does not
  absorption       heavy volume, small range, delta against the candle: someone big
                   absorbed the aggression at that price
"""

import math

import indicators as ind


def delta_clv(o, h, l, c, v):
    out = []
    for i in range(len(c)):
        rng = h[i] - l[i]
        clv = (2 * (c[i] - l[i]) / rng - 1) if rng > 0 else (1.0 if c[i] > o[i] else -1.0 if c[i] < o[i] else 0.0)
        out.append((v[i] if v[i] > 0 else 1.0) * clv)
    return out


def delta_of(bars):
    """(delta list, source): taker/tick delta stored in the bars, else the CLV proxy."""
    if bars.has_delta():
        clv = delta_clv(bars.o, bars.h, bars.l, bars.c, bars.v)
        return [d if d is not None else clv[i] for i, d in enumerate(bars.d)], "measured"
    return delta_clv(bars.o, bars.h, bars.l, bars.c, bars.v), "clv"


def tick_rule_bars(ticks, step):
    """Dukascopy-style ticks [(t_ms, ask, bid, ask_vol, bid_vol)] -> {bar_start: (o,h,l,c,ticks,delta,spread)}
    on mid prices. Delta by the tick rule; spread = average ask - bid in the bar."""
    out, last_mid, last_sign = {}, None, 0
    for t_ms, ask, bid, _av, _bv in ticks:
        mid = (ask + bid) / 2.0
        k = int(t_ms // 1000) // step * step
        sign = last_sign
        if last_mid is not None:
            sign = 1 if mid > last_mid else -1 if mid < last_mid else last_sign
        last_mid, last_sign = mid, sign
        b = out.get(k)
        if b is None:
            out[k] = [mid, mid, mid, mid, 1, sign, ask - bid]
        else:
            b[1], b[2], b[3] = max(b[1], mid), min(b[2], mid), mid
            b[4] += 1
            b[5] += sign
            b[6] += ask - bid
    return {k: (b[0], b[1], b[2], b[3], b[4], b[5], b[6] / b[4]) for k, b in out.items()}


def cvd(delta, keys=None):
    """Cumulative delta; restarts whenever keys[i] changes (a session key) if given."""
    out, s, last = [], 0.0, object()
    for i, d in enumerate(delta):
        if keys is not None and keys[i] != last:
            s, last = 0.0, keys[i]
        s += d
        out.append(s)
    return out


def volume_profile(h, l, c, v, bins=40, value_area=0.70, tick=None):
    """Spread each bar's volume evenly over its high-low range. Returns
    {poc, vah, val, hvn [prices], lvn [prices], shape, levels [(price, volume)], total}."""
    lo, hi = min(l), max(h)
    if hi <= lo:
        return {"poc": c[-1], "vah": hi, "val": lo, "hvn": [], "lvn": [], "shape": "flat", "levels": [], "total": 0.0}
    size = (hi - lo) / bins
    if tick:
        size = max(size, tick)
    nb = int(math.ceil((hi - lo) / size)) or 1
    vol = [0.0] * nb
    for i in range(len(c)):
        w = v[i] if v[i] > 0 else 1.0
        a = min(nb - 1, int((l[i] - lo) / size))
        b = min(nb - 1, int((h[i] - lo) / size))
        share = w / (b - a + 1)
        for k in range(a, b + 1):
            vol[k] += share
    total = sum(vol)
    poc_k = max(range(nb), key=lambda k: vol[k])
    lo_k = hi_k = poc_k
    acc = vol[poc_k]
    while acc < value_area * total and (lo_k > 0 or hi_k < nb - 1):
        up = vol[hi_k + 1] if hi_k < nb - 1 else -1
        dn = vol[lo_k - 1] if lo_k > 0 else -1
        if up >= dn:
            hi_k += 1
            acc += up
        else:
            lo_k -= 1
            acc += dn
    mid = lambda k: lo + (k + 0.5) * size  # noqa: E731
    mean = total / nb
    hvn = [mid(k) for k in range(1, nb - 1) if vol[k] > vol[k - 1] and vol[k] >= vol[k + 1] and vol[k] > 1.3 * mean]
    lvn = [mid(k) for k in range(1, nb - 1) if vol[k] < vol[k - 1] and vol[k] <= vol[k + 1] and vol[k] < 0.6 * mean]
    pos = (poc_k + 0.5) / nb
    shape = "P (buyers in control, short covering)" if pos > 0.65 else \
        "b (sellers in control, long liquidation)" if pos < 0.35 else "D (balanced)"
    return {"poc": mid(poc_k), "vah": lo + (hi_k + 1) * size, "val": lo + lo_k * size, "hvn": hvn, "lvn": lvn,
            "shape": shape, "levels": [(mid(k), vol[k]) for k in range(nb)], "total": total}


def divergence(h, l, cumdelta, i, lookback=20):
    """'bearish' when bar i makes a new high of the window but CVD does not; 'bullish' for the
    low side; else None."""
    if i < lookback:
        return None
    w = range(i - lookback, i)
    if h[i] > max(h[k] for k in w) and cumdelta[i] <= max(cumdelta[k] for k in w):
        return "bearish"
    if l[i] < min(l[k] for k in w) and cumdelta[i] >= min(cumdelta[k] for k in w):
        return "bullish"
    return None


def absorption(o, h, l, c, v, delta, atr_list, i, vol_z=2.0, range_atr=0.6, n=20):
    """'bullish' (selling absorbed: heavy volume, small range, negative delta, close >= open),
    'bearish' (the mirror) or None."""
    if i < n or atr_list[i] is None:
        return None
    w = v[i - n:i]
    m = sum(w) / n
    s = math.sqrt(sum((x - m) ** 2 for x in w) / n)
    z = (v[i] - m) / s if s else 0.0
    if z < vol_z or (h[i] - l[i]) > range_atr * atr_list[i]:
        return None
    if delta[i] < 0 and c[i] >= o[i]:
        return "bullish"
    if delta[i] > 0 and c[i] <= o[i]:
        return "bearish"
    return None


def summary(bars, session_keys=None, bins=40):
    """The order-flow picture of a Bars slice: profile, delta source, CVD trend, last divergence,
    last absorption, VWAP position."""
    o, h, l, c, v = bars.o, bars.h, bars.l, bars.c, bars.v
    delta, src = delta_of(bars)
    cum = cvd(delta, session_keys)
    prof = volume_profile(h, l, c, v, bins)
    a = ind.atr(h, l, c, 14)
    vw = ind.vwap(bars.t, h, l, c, v)
    i = len(c) - 1
    div = next((divergence(h, l, cum, k) for k in range(i, max(i - 5, 20), -1) if divergence(h, l, cum, k)), None)
    absb = next(((k, absorption(o, h, l, c, v, delta, a, k)) for k in range(i, max(i - 10, 20), -1)
                 if absorption(o, h, l, c, v, delta, a, k)), None)
    slope = cum[i] - cum[max(0, i - 10)]
    price = c[i]
    loc = "above value" if price > prof["vah"] else "below value" if price < prof["val"] else "inside value"
    return {"delta_source": src, "cvd": cum[i], "cvd_slope_10": slope, "profile": dict(prof, levels=None),
            "location": loc, "vwap": vw["vwap"][i], "vwap_sd": vw["sd"][i],
            "vwap_z": (price - vw["vwap"][i]) / vw["sd"][i] if vw["sd"][i] else 0.0,
            "divergence": div, "absorption": {"bars_ago": i - absb[0], "side": absb[1]} if absb else None,
            "volume_real": any(x > 0 for x in v)}
