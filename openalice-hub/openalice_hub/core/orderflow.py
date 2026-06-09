"""
Order-flow primitives from REAL data — pure stdlib.

Binance klines include taker-buy base volume (field 9), so per-bar delta and
cumulative volume delta (CVD) are REAL, not invented:
    delta = takerBuyVol - (totalVol - takerBuyVol) = 2*bv - v
For sources without taker volume (Yahoo/CSV) we fall back to a signed-volume
proxy (up bar = +vol, down bar = -vol). This is bar-resolution order flow — a
legitimate proxy, upgradeable to true tick footprint via Binance aggTrades.
"""
from __future__ import annotations


def enrich(bars: list[dict]) -> list[dict]:
    """Add 'delta' and 'cvd' to each bar (idempotent)."""
    if bars and "cvd" in bars[0]:
        return bars
    cvd = 0.0
    for b in bars:
        bv = b.get("bv")
        d = (2 * bv - b["v"]) if bv is not None else ((1 if b["c"] >= b["o"] else -1) * b["v"])
        b["delta"] = d
        cvd += d
        b["cvd"] = cvd
    return bars


def vp_window(bars: list[dict], i: int, win: int = 80, bins: int = 24):
    """Volume profile over the trailing `win` bars ending at i.
    Volume of each bar is spread uniformly across its [low,high]. Returns POC,
    value-area high/low (70%), and the highest/lowest volume node price."""
    a = max(0, i - win + 1)
    seg = bars[a:i + 1]
    if len(seg) < 5:
        return None
    lo = min(b["l"] for b in seg)
    hi = max(b["h"] for b in seg)
    if hi <= lo:
        return None
    w = (hi - lo) / bins
    prof = [0.0] * bins
    for b in seg:
        bl = max(0, min(bins - 1, int((b["l"] - lo) / w)))
        bh = max(0, min(bins - 1, int((b["h"] - lo) / w)))
        share = b["v"] / (bh - bl + 1)
        for k in range(bl, bh + 1):
            prof[k] += share
    poc = prof.index(max(prof))
    tot = sum(prof)
    acc = prof[poc]
    lo_i = hi_i = poc
    while acc < 0.7 * tot and (lo_i > 0 or hi_i < bins - 1):
        up = prof[hi_i + 1] if hi_i < bins - 1 else -1
        dn = prof[lo_i - 1] if lo_i > 0 else -1
        if up >= dn:
            hi_i += 1; acc += max(up, 0)
        else:
            lo_i -= 1; acc += max(dn, 0)
    price = lambda b: lo + (b + 0.5) * w
    return {"poc": price(poc), "vah": price(hi_i), "val": price(lo_i),
            "hvn": price(poc), "lvn": price(prof.index(min(prof)))}
