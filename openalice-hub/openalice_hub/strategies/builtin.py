"""
Built-in, runnable strategies (pure stdlib) so the hub can backtest with ZERO
upstream deps. Each returns a target position per bar: 1=long, 0=flat, -1=short.
Signals use only data up to bar i (no lookahead); the backtester fills next-open.
"""
from __future__ import annotations
from ..core import indicators as ind


class Strategy:
    name = "base"
    allow_short = False

    def positions(self, bars: list[dict]) -> list[int]:
        raise NotImplementedError


class SMACross(Strategy):
    name = "sma_cross"

    def __init__(self, fast=20, slow=50):
        self.fast, self.slow = fast, slow

    def positions(self, bars):
        c = [b["c"] for b in bars]
        f, s = ind.sma(c, self.fast), ind.sma(c, self.slow)
        pos = []
        for i in range(len(c)):
            if f[i] is None or s[i] is None:
                pos.append(0)
            else:
                pos.append(1 if f[i] > s[i] else 0)
        return pos


class RSI2(Strategy):
    name = "rsi2"

    def __init__(self, n=2, buy=10, exit=60, trend=200):
        self.n, self.buy, self.exit, self.trend = n, buy, exit, trend

    def positions(self, bars):
        c = [b["c"] for b in bars]
        r = ind.rsi(c, self.n)
        t = ind.sma(c, self.trend)
        pos, cur = [], 0
        for i in range(len(c)):
            up = t[i] is not None and c[i] > t[i]
            if r[i] is not None:
                if cur == 0 and up and r[i] < self.buy:
                    cur = 1
                elif cur == 1 and r[i] > self.exit:
                    cur = 0
            pos.append(cur)
        return pos


class DonchianBreakout(Strategy):
    name = "donchian"

    def __init__(self, entry=20, exit=10):
        self.entry, self.exit = entry, exit

    def positions(self, bars):
        c = [b["c"] for b in bars]
        hi = ind.highest(c, self.entry)
        lo = ind.lowest(c, self.exit)
        pos, cur = [], 0
        for i in range(len(c)):
            if i > 0 and hi[i - 1] is not None and c[i] >= hi[i - 1]:
                cur = 1
            elif i > 0 and lo[i - 1] is not None and c[i] <= lo[i - 1]:
                cur = 0
            pos.append(cur)
        return pos


REGISTRY = {s.name: s for s in (SMACross, RSI2, DonchianBreakout)}


def make(name: str, **kw) -> Strategy:
    cls = REGISTRY.get(name)
    if not cls:
        raise ValueError(f"unknown strategy '{name}'. have: {', '.join(REGISTRY)}")
    return cls(**kw)
