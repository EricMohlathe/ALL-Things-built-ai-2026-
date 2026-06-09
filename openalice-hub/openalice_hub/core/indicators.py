"""Technical indicators — pure stdlib. Each returns a list aligned to input (None during warmup)."""
from __future__ import annotations


def sma(xs: list[float], n: int) -> list[float | None]:
    out: list[float | None] = [None] * len(xs)
    s = 0.0
    for i, x in enumerate(xs):
        s += x
        if i >= n:
            s -= xs[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def ema(xs: list[float], n: int) -> list[float | None]:
    out: list[float | None] = [None] * len(xs)
    k = 2 / (n + 1)
    e = None
    for i, x in enumerate(xs):
        e = x if e is None else x * k + e * (1 - k)
        if i >= n - 1:
            out[i] = e
    return out


def rsi(xs: list[float], n: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(xs)
    if len(xs) <= n:
        return out
    gains = losses = 0.0
    for i in range(1, n + 1):
        d = xs[i] - xs[i - 1]
        gains += max(d, 0); losses += max(-d, 0)
    ag, al = gains / n, losses / n
    out[n] = 100 - 100 / (1 + (ag / al if al else 1e9))
    for i in range(n + 1, len(xs)):
        d = xs[i] - xs[i - 1]
        ag = (ag * (n - 1) + max(d, 0)) / n
        al = (al * (n - 1) + max(-d, 0)) / n
        out[i] = 100 - 100 / (1 + (ag / al if al else 1e9))
    return out


def highest(xs: list[float], n: int) -> list[float | None]:
    return [max(xs[i - n + 1:i + 1]) if i >= n - 1 else None for i in range(len(xs))]


def lowest(xs: list[float], n: int) -> list[float | None]:
    return [min(xs[i - n + 1:i + 1]) if i >= n - 1 else None for i in range(len(xs))]


def atr(bars: list[dict], n: int = 14) -> list[float | None]:
    trs = []
    for i, b in enumerate(bars):
        if i == 0:
            trs.append(b["h"] - b["l"])
        else:
            pc = bars[i - 1]["c"]
            trs.append(max(b["h"] - b["l"], abs(b["h"] - pc), abs(b["l"] - pc)))
    return sma(trs, n)
