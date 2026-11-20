"""bars: OHLCV(+delta) series for the research tools. Standard library only.

A Bars object holds parallel lists, oldest first: t (bar START, unix seconds
UTC), o, h, l, c, v (volume: real, tick or zero), d (delta: buy minus sell
volume, None when unknown) and the bar length in seconds. Parallel lists keep a
100,000-bar backtest fast in plain Python.

    b = Bars.from_chart(tradercore.get_chart(...))     # a Yahoo v8 chart
    b = Bars.from_csv("trader/data/EURUSD/M1.csv")      # the history cache
    h1 = b.resample("1h")                               # complete bars only
    i = h1.last_closed_at(t)                            # no look-ahead alignment
"""

import bisect
import csv
import os

TF = {"1m": 60, "M1": 60, "5m": 300, "M5": 300, "15m": 900, "M15": 900, "30m": 1800, "M30": 1800,
      "1h": 3600, "H1": 3600, "60m": 3600, "4h": 14400, "H4": 14400, "1d": 86400, "D1": 86400}
TF_NAME = {60: "M1", 300: "M5", 900: "M15", 1800: "M30", 3600: "H1", 14400: "H4", 86400: "D1"}


def tf_seconds(tf):
    if isinstance(tf, int):
        return tf
    if str(tf) not in TF:
        raise ValueError("timeframe is one of %s, not %r" % (", ".join(sorted(set(TF))), tf))
    return TF[str(tf)]


class Bars(object):
    __slots__ = ("t", "o", "h", "l", "c", "v", "d", "step", "symbol")

    def __init__(self, step, symbol=""):
        self.step = int(step)
        self.symbol = symbol
        self.t, self.o, self.h, self.l, self.c, self.v, self.d = [], [], [], [], [], [], []

    def __len__(self):
        return len(self.t)

    def append(self, t, o, h, l, c, v=0.0, d=None):
        self.t.append(int(t))
        self.o.append(float(o))
        self.h.append(float(max(h, o, c)))
        self.l.append(float(min(l, o, c)))
        self.c.append(float(c))
        self.v.append(float(v or 0.0))
        self.d.append(None if d is None else float(d))

    def end(self, i):
        return self.t[i] + self.step

    def has_delta(self):
        return any(x is not None for x in self.d)

    def slice(self, a, b):
        out = Bars(self.step, self.symbol)
        for k in ("t", "o", "h", "l", "c", "v", "d"):
            setattr(out, k, getattr(self, k)[a:b])
        return out

    def between(self, t0, t1):
        """Bars whose start is in [t0, t1)."""
        return self.slice(bisect.bisect_left(self.t, t0), bisect.bisect_left(self.t, t1))

    def last_closed_at(self, t):
        """Index of the last bar that had CLOSED by time t (its end <= t), or -1. The
        only safe way to read a higher timeframe from a lower one: no look-ahead."""
        return bisect.bisect_right(self.t, t - self.step) - 1

    def index_at(self, t):
        i = bisect.bisect_left(self.t, t)
        return i if i < len(self.t) and self.t[i] == t else -1

    def first_from(self, t):
        """Index of the first bar starting at or after t (len(self) if none)."""
        return bisect.bisect_left(self.t, t)

    # ---------------------------------------------------------------- building

    @classmethod
    def from_rows(cls, rows, step, symbol=""):
        b = cls(step, symbol)
        seen = {}
        for r in rows:
            seen[int(r["t"])] = r
        for k in sorted(seen):
            r = seen[k]
            b.append(k, r["o"], r["h"], r["l"], r["c"], r.get("v", 0.0), r.get("d"))
        return b

    @classmethod
    def from_chart(cls, chart, step=None, symbol=""):
        """A tradercore.get_chart() result -> Bars (off-grid live ticks dropped)."""
        gran = chart.get("granularity") or "5m"
        step = step or tf_seconds({"60m": "1h"}.get(gran, gran))
        rows = [b for b in chart["bars"] if b["t"] % min(step, 86400) == 0 or step >= 86400]
        return cls.from_rows(rows, step, symbol or chart.get("symbol", ""))

    @classmethod
    def from_csv(cls, path, symbol=""):
        rows, step = [], None
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                d = r.get("delta")
                rows.append({"t": int(float(r["time"])), "o": float(r["open"]), "h": float(r["high"]),
                             "l": float(r["low"]), "c": float(r["close"]), "v": float(r.get("volume") or 0),
                             "d": float(d) if d not in (None, "", "None") else None})
        if len(rows) >= 2:
            gaps = sorted(rows[i + 1]["t"] - rows[i]["t"] for i in range(min(len(rows) - 1, 500)))
            step = gaps[0] if gaps else 60
        name = os.path.splitext(os.path.basename(path))[0]
        step = TF.get(name, step or 60)
        return cls.from_rows(rows, step, symbol)

    def to_csv(self, path):
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["time", "open", "high", "low", "close", "volume", "delta"])
            for i in range(len(self.t)):
                w.writerow([self.t[i], repr(self.o[i]), repr(self.h[i]), repr(self.l[i]), repr(self.c[i]),
                            repr(self.v[i]), "" if self.d[i] is None else repr(self.d[i])])
        os.replace(tmp, path)

    def merge(self, other):
        """Union by time; `other` wins where both have a bar."""
        if other.step != self.step:
            raise ValueError("cannot merge %ss bars with %ss bars" % (self.step, other.step))
        by = {}
        for src in (self, other):
            for i in range(len(src.t)):
                by[src.t[i]] = (src.o[i], src.h[i], src.l[i], src.c[i], src.v[i], src.d[i])
        out = Bars(self.step, self.symbol or other.symbol)
        for k in sorted(by):
            out.append(k, *by[k])
        return out

    def resample(self, tf, offset=0):
        """Bigger bars from smaller ones. A bar is kept only when the source covers
        its whole span's last minute (the last source bar ends at the target end), so
        a still-forming bar never leaks. `offset` (seconds) shifts the grid, e.g. a
        daily bar that starts at 17:00 New York (FX) or 22:00 UTC."""
        step = tf_seconds(tf)
        if step < self.step or step % self.step:
            raise ValueError("cannot build %ss bars from %ss bars" % (step, self.step))
        out = Bars(step, self.symbol)
        cur = None
        for i in range(len(self.t)):
            k = (self.t[i] - offset) // step * step + offset
            if cur is None or cur[0] != k:
                if cur is not None and cur[7]:
                    out.append(cur[0], cur[1], cur[2], cur[3], cur[4], cur[5], cur[6])
                cur = [k, self.o[i], self.h[i], self.l[i], self.c[i], self.v[i], self.d[i], False]
            else:
                cur[2] = max(cur[2], self.h[i])
                cur[3] = min(cur[3], self.l[i])
                cur[4] = self.c[i]
                cur[5] += self.v[i]
                if self.d[i] is not None:
                    cur[6] = (cur[6] or 0.0) + self.d[i]
            cur[7] = self.t[i] + self.step == k + step
        if cur is not None and cur[7]:
            out.append(cur[0], cur[1], cur[2], cur[3], cur[4], cur[5], cur[6])
        return out

    def resample_partial(self, tf, offset=0):
        """Like resample, but keeps every bar, finished or not (for daily ranges over
        sessions that do not trade 24 hours: a stock index day ends at its close)."""
        step = tf_seconds(tf)
        out = Bars(step, self.symbol)
        cur = None
        for i in range(len(self.t)):
            k = (self.t[i] - offset) // step * step + offset
            if cur is None or cur[0] != k:
                if cur is not None:
                    out.append(*cur)
                cur = [k, self.o[i], self.h[i], self.l[i], self.c[i], self.v[i], self.d[i]]
            else:
                cur[2] = max(cur[2], self.h[i])
                cur[3] = min(cur[3], self.l[i])
                cur[4] = self.c[i]
                cur[5] += self.v[i]
                if self.d[i] is not None:
                    cur[6] = (cur[6] or 0.0) + self.d[i]
        if cur is not None:
            out.append(*cur)
        return out
