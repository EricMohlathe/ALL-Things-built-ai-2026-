"""indicators: the technical toolkit, on plain lists. Standard library only.

Every function takes lists (oldest first) and returns a list of the same length
with None where there is not enough history yet. Wilder smoothing where the
original indicator uses it (RSI, ATR, ADX), so the numbers match the platforms.

  trend       sma, ema, wma, hma, macd, supertrend, ichimoku, donchian, keltner
  momentum    rsi, stoch, roc, williams_r, cci
  volatility  atr, true_range, bollinger, stdev, atr_percentile
  strength    adx (adx, +DI, -DI), efficiency_ratio
  volume      vwap (session-anchored, with standard-deviation bands), obv
  levels      pivots (classic, fibonacci, camarilla), fib_levels
  regime      regime(): trend_up / trend_down / range / volatile / quiet, from ADX,
              the efficiency ratio and where ATR sits in its own history
"""

import math


def _none(n):
    return [None] * n


def sma(x, n):
    out, s = _none(len(x)), 0.0
    for i, v in enumerate(x):
        s += v
        if i >= n:
            s -= x[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def ema(x, n, seed_sma=True):
    out = _none(len(x))
    if len(x) < n:
        return out
    k = 2.0 / (n + 1)
    prev = sum(x[:n]) / n if seed_sma else x[0]
    start = n - 1 if seed_sma else 0
    out[start] = prev
    for i in range(start + 1, len(x)):
        prev = x[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def rma(x, n):
    """Wilder's moving average (alpha = 1/n), seeded with an SMA of the first n values."""
    out = _none(len(x))
    vals = [(i, v) for i, v in enumerate(x) if v is not None]
    if len(vals) < n:
        return out
    first = vals[0][0]
    prev = sum(v for _, v in vals[:n]) / n
    out[first + n - 1] = prev
    for i in range(first + n, len(x)):
        prev = (prev * (n - 1) + x[i]) / n
        out[i] = prev
    return out


def wma(x, n):
    out = _none(len(x))
    den = n * (n + 1) / 2.0
    for i in range(n - 1, len(x)):
        out[i] = sum(x[i - n + 1 + k] * (k + 1) for k in range(n)) / den
    return out


def hma(x, n):
    half, root = wma(x, max(1, n // 2)), wma(x, n)
    diff = [None if a is None or b is None else 2 * a - b for a, b in zip(half, root)]
    start = next((i for i, v in enumerate(diff) if v is not None), len(x))
    tail = wma([v for v in diff[start:]], max(1, int(math.sqrt(n))))
    return _none(start) + tail


def stdev(x, n):
    out = _none(len(x))
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        m = sum(w) / n
        out[i] = math.sqrt(sum((v - m) ** 2 for v in w) / n)
    return out


def true_range(h, l, c):
    out = []
    for i in range(len(c)):
        tr = h[i] - l[i]
        if i:
            tr = max(tr, abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        out.append(tr)
    return out


def atr(h, l, c, n=14):
    return rma(true_range(h, l, c), n)


def rsi(c, n=14):
    out = _none(len(c))
    if len(c) <= n:
        return out
    gains = [max(0.0, c[i] - c[i - 1]) for i in range(1, len(c))]
    losses = [max(0.0, c[i - 1] - c[i]) for i in range(1, len(c))]
    ag, al = sum(gains[:n]) / n, sum(losses[:n]) / n
    out[n] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(n, len(gains)):
        ag = (ag * (n - 1) + gains[i]) / n
        al = (al * (n - 1) + losses[i]) / n
        out[i + 1] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def adx(h, l, c, n=14):
    """(adx, plus_di, minus_di), Wilder."""
    size = len(c)
    pdm, mdm = [0.0], [0.0]
    for i in range(1, size):
        up, dn = h[i] - h[i - 1], l[i - 1] - l[i]
        pdm.append(up if up > dn and up > 0 else 0.0)
        mdm.append(dn if dn > up and dn > 0 else 0.0)
    tr = true_range(h, l, c)
    atr_, sp, sm = rma(tr, n), rma(pdm, n), rma(mdm, n)
    pdi, mdi, dx = _none(size), _none(size), _none(size)
    for i in range(size):
        if atr_[i]:
            pdi[i] = 100 * sp[i] / atr_[i]
            mdi[i] = 100 * sm[i] / atr_[i]
            s = pdi[i] + mdi[i]
            dx[i] = 100 * abs(pdi[i] - mdi[i]) / s if s else 0.0
    first = next((i for i, v in enumerate(dx) if v is not None), size)
    tail = rma(dx[first:], n)
    return _none(first) + tail, pdi, mdi


def macd(c, fast=12, slow=26, signal=9):
    f, s = ema(c, fast), ema(c, slow)
    line = [None if a is None or b is None else a - b for a, b in zip(f, s)]
    start = next((i for i, v in enumerate(line) if v is not None), len(c))
    sig = _none(start) + ema(line[start:], signal)
    hist = [None if a is None or b is None else a - b for a, b in zip(line, sig)]
    return line, sig, hist


def bollinger(c, n=20, k=2.0):
    mid, sd = sma(c, n), stdev(c, n)
    up = [None if m is None else m + k * s for m, s in zip(mid, sd)]
    lo = [None if m is None else m - k * s for m, s in zip(mid, sd)]
    return mid, up, lo


def keltner(h, l, c, n=20, k=2.0):
    mid, a = ema(c, n), atr(h, l, c, n)
    return mid, [None if m is None or x is None else m + k * x for m, x in zip(mid, a)], \
        [None if m is None or x is None else m - k * x for m, x in zip(mid, a)]


def donchian(h, l, n=20):
    up, lo = _none(len(h)), _none(len(h))
    for i in range(n - 1, len(h)):
        up[i] = max(h[i - n + 1:i + 1])
        lo[i] = min(l[i - n + 1:i + 1])
    return up, lo


def stoch(h, l, c, k=14, d=3):
    kk = _none(len(c))
    for i in range(k - 1, len(c)):
        hh, ll = max(h[i - k + 1:i + 1]), min(l[i - k + 1:i + 1])
        kk[i] = 100 * (c[i] - ll) / (hh - ll) if hh > ll else 50.0
    start = k - 1
    dd = _none(start) + sma(kk[start:], d) if len(c) > start else _none(len(c))
    return kk, dd


def roc(c, n=10):
    return [None if i < n or not c[i - n] else 100 * (c[i] / c[i - n] - 1) for i in range(len(c))]


def williams_r(h, l, c, n=14):
    out = _none(len(c))
    for i in range(n - 1, len(c)):
        hh, ll = max(h[i - n + 1:i + 1]), min(l[i - n + 1:i + 1])
        out[i] = -100 * (hh - c[i]) / (hh - ll) if hh > ll else -50.0
    return out


def cci(h, l, c, n=20):
    tp = [(a + b + d) / 3.0 for a, b, d in zip(h, l, c)]
    out = _none(len(c))
    for i in range(n - 1, len(c)):
        w = tp[i - n + 1:i + 1]
        m = sum(w) / n
        md = sum(abs(v - m) for v in w) / n
        out[i] = (tp[i] - m) / (0.015 * md) if md else 0.0
    return out


def supertrend(h, l, c, n=10, mult=3.0):
    """(line, direction) with direction +1 (up) / -1 (down)."""
    a = atr(h, l, c, n)
    line, dirn = _none(len(c)), _none(len(c))
    fu = fl = None
    d = 1
    for i in range(len(c)):
        if a[i] is None:
            continue
        hl2 = (h[i] + l[i]) / 2.0
        bu, bl = hl2 + mult * a[i], hl2 - mult * a[i]
        fu = bu if fu is None or bu < fu or c[i - 1] > fu else fu
        fl = bl if fl is None or bl > fl or c[i - 1] < fl else fl
        if d == 1 and c[i] < fl:
            d = -1
        elif d == -1 and c[i] > fu:
            d = 1
        line[i], dirn[i] = (fl if d == 1 else fu), d
    return line, dirn


def ichimoku(h, l, c, conv=9, base=26, span_b=52, disp=26):
    """(tenkan, kijun, cloud_a, cloud_b): the cloud AT each bar (spans shifted forward)."""
    def mid(n, i):
        return (max(h[i - n + 1:i + 1]) + min(l[i - n + 1:i + 1])) / 2.0 if i >= n - 1 else None
    size = len(c)
    ten = [mid(conv, i) for i in range(size)]
    kij = [mid(base, i) for i in range(size)]
    sa = [None if a is None or b is None else (a + b) / 2.0 for a, b in zip(ten, kij)]
    sb = [mid(span_b, i) for i in range(size)]
    ca = _none(size)
    cb = _none(size)
    for i in range(disp, size):
        ca[i], cb[i] = sa[i - disp], sb[i - disp]
    return ten, kij, ca, cb


def efficiency_ratio(c, n=20):
    """Kaufman: net move / sum of moves. 1 = a straight line, 0 = noise."""
    out = _none(len(c))
    for i in range(n, len(c)):
        path = sum(abs(c[k] - c[k - 1]) for k in range(i - n + 1, i + 1))
        out[i] = abs(c[i] - c[i - n]) / path if path else 0.0
    return out


def obv(c, v):
    out, s = [0.0], 0.0
    for i in range(1, len(c)):
        s += v[i] if c[i] > c[i - 1] else -v[i] if c[i] < c[i - 1] else 0.0
        out.append(s)
    return out


def vwap(t, h, l, c, v, anchor=86400, offset=0, bands=(1.0, 2.0)):
    """Session-anchored VWAP and standard-deviation bands. A new session starts each
    time (t - offset) // anchor changes. Bars without volume weigh 1 (tick-less feeds)."""
    vw, sd = _none(len(c)), _none(len(c))
    key = None
    pv = vv = pv2 = 0.0
    for i in range(len(c)):
        k = (t[i] - offset) // anchor
        if k != key:
            key, pv, vv, pv2 = k, 0.0, 0.0, 0.0
        tp = (h[i] + l[i] + c[i]) / 3.0
        w = v[i] if v[i] > 0 else 1.0
        pv += tp * w
        vv += w
        pv2 += tp * tp * w
        vw[i] = pv / vv
        sd[i] = math.sqrt(max(0.0, pv2 / vv - vw[i] ** 2))
    out = {"vwap": vw, "sd": sd}
    for b in bands:
        out["up%g" % b] = [None if a is None else a + b * s for a, s in zip(vw, sd)]
        out["dn%g" % b] = [None if a is None else a - b * s for a, s in zip(vw, sd)]
    return out


def pivots(h, l, c, kind="classic"):
    """Pivot levels from ONE prior bar (yesterday's high, low and close)."""
    p = (h + l + c) / 3.0
    r = h - l
    if kind == "fibonacci":
        return {"P": p, "R1": p + 0.382 * r, "R2": p + 0.618 * r, "R3": p + r,
                "S1": p - 0.382 * r, "S2": p - 0.618 * r, "S3": p - r}
    if kind == "camarilla":
        return {"P": p, "R1": c + r * 1.1 / 12, "R2": c + r * 1.1 / 6, "R3": c + r * 1.1 / 4, "R4": c + r * 1.1 / 2,
                "S1": c - r * 1.1 / 12, "S2": c - r * 1.1 / 6, "S3": c - r * 1.1 / 4, "S4": c - r * 1.1 / 2}
    return {"P": p, "R1": 2 * p - l, "R2": p + r, "R3": h + 2 * (p - l),
            "S1": 2 * p - h, "S2": p - r, "S3": l - 2 * (h - p)}


def fib_levels(a, b, levels=(0.0, 0.236, 0.382, 0.5, 0.618, 0.705, 0.79, 1.0, 1.272, 1.618)):
    """Retracement levels of the move a -> b (0 = b, 1 = a), the ICT OTE band is 0.62-0.79."""
    return {lv: b - (b - a) * lv for lv in levels}


def percentile_rank(x, n=100):
    """Where each value sits in its own last n values, 0-100."""
    out = _none(len(x))
    for i in range(len(x)):
        if x[i] is None:
            continue
        w = [v for v in x[max(0, i - n + 1):i + 1] if v is not None]
        if len(w) >= min(n, 20):
            out[i] = 100.0 * sum(1 for v in w if v <= x[i]) / len(w)
    return out


def zscore(x, n=20):
    out = _none(len(x))
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        m = sum(w) / n
        s = math.sqrt(sum((v - m) ** 2 for v in w) / n)
        out[i] = (x[i] - m) / s if s else 0.0
    return out


def regime(h, l, c, n=14, er_n=20, lookback=100):
    """Market regime per bar: 'trend_up', 'trend_down', 'range', 'volatile' or 'quiet'.
      trend    ADX >= 25 and the efficiency ratio >= 0.3, direction from +DI vs -DI
      volatile ATR in the top 15 % of its last `lookback` bars without a trend
      quiet    ATR in the bottom 15 %
      range    the rest"""
    a, pdi, mdi = adx(h, l, c, n)
    er = efficiency_ratio(c, er_n)
    ap = percentile_rank(atr(h, l, c, n), lookback)
    out = _none(len(c))
    for i in range(len(c)):
        if a[i] is None or er[i] is None:
            continue
        if a[i] >= 25 and er[i] >= 0.3:
            out[i] = "trend_up" if pdi[i] >= mdi[i] else "trend_down"
        elif ap[i] is not None and ap[i] >= 85:
            out[i] = "volatile"
        elif ap[i] is not None and ap[i] <= 15:
            out[i] = "quiet"
        else:
            out[i] = "range"
    return out


def correlation(a, b):
    """Pearson correlation of two equal-length lists (None pairs dropped)."""
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    n = len(pairs)
    if n < 3:
        return None
    mx = sum(p[0] for p in pairs) / n
    my = sum(p[1] for p in pairs) / n
    sxy = sum((x - mx) * (y - my) for x, y in pairs)
    sx = math.sqrt(sum((x - mx) ** 2 for x, _ in pairs))
    sy = math.sqrt(sum((y - my) ** 2 for _, y in pairs))
    return sxy / (sx * sy) if sx and sy else None


def returns(c):
    return [None] + [(c[i] / c[i - 1] - 1) if c[i - 1] else None for i in range(1, len(c))]
