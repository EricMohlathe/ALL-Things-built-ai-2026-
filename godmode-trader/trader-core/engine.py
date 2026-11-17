"""engine: the bar-by-bar backtester behind the Setup Lab. Standard library only.

One setup, one instrument, one series, one position at a time: the isolation the
GODMODE compendium asks for (Part 7: you cannot judge a setup inside a pooled score).

  At each bar's CLOSE the setup may emit a Signal (side, stop, target, entry type).
  A market entry fills at the NEXT bar's open, plus half the spread and the entry slippage.
  A limit entry waits up to `expiry_bars` and fills at the limit (or a better open).
  Inside a bar the stop is checked BEFORE the target (a bar touching both is a loss), a
  stop fills with stop slippage, and a gap through the stop fills at the open (worse).
  Exits: stop, target, break-even (be_at_r), trailing stop (trail_atr), time (max_bars),
  a session flat-by timestamp, the setup's own exit rule (exit_rule: e.g. RSI2 closes when
  price reclaims its 5-bar mean), or the end of the data.
  Costs: spread (half in, half out), slippage, commission per lot round turn, all in R.

Every signal is logged, the ones not taken too, with why (already in a trade, outside
the session, a filter): the denominator the compendium says the monolith never logged.
Results are in R (multiples of the initial risk) so setups compare across instruments.
"""

import datetime
import math

import indicators as ind
import tradercore as tc


class Signal(object):
    __slots__ = ("side", "stop", "target", "entry", "expiry_bars", "max_bars", "flat_at", "tag", "features",
                 "be_at_r", "trail_atr")

    def __init__(self, side, stop, target=None, entry="market", expiry_bars=3, max_bars=None, flat_at=None,
                 tag="", features=None, be_at_r=None, trail_atr=None):
        self.side = side
        self.stop = float(stop)
        self.target = None if target is None else float(target)
        self.entry = entry
        self.expiry_bars = expiry_bars
        self.max_bars = max_bars
        self.flat_at = flat_at
        self.tag = tag
        self.features = features or {}
        self.be_at_r = be_at_r
        self.trail_atr = trail_atr


class Skip(object):
    """A candidate the setup saw but filtered out, with the reason: logged, not traded."""
    __slots__ = ("side", "reason")

    def __init__(self, side, reason):
        self.side, self.reason = side, reason


class Context(object):
    """What a setup can see: the bars, cached indicators, higher timeframes aligned
    without look-ahead, New York clock helpers and the instrument."""

    def __init__(self, bars, inst, params, cfg=None):
        self.bars, self.inst, self.p, self.cfg = bars, inst, params, cfg or {}
        self._cache, self._htf, self.state = {}, {}, {}
        b = bars
        self.o, self.h, self.l, self.c, self.v, self.t = b.o, b.h, b.l, b.c, b.v, b.t
        self._ny = None

    def ind(self, name, *args):
        key = (name,) + tuple(args)
        if key not in self._cache:
            b = self.bars
            f = {"atr": lambda n: ind.atr(b.h, b.l, b.c, n), "rsi": lambda n: ind.rsi(b.c, n),
                 "ema": lambda n: ind.ema(b.c, n), "sma": lambda n: ind.sma(b.c, n),
                 "adx": lambda n: ind.adx(b.h, b.l, b.c, n), "regime": lambda: ind.regime(b.h, b.l, b.c),
                 "vwap": lambda: ind.vwap(b.t, b.h, b.l, b.c, b.v, 86400, self.day_offset()),
                 "boll": lambda n, k: ind.bollinger(b.c, n, k), "stoch": lambda n: ind.stoch(b.h, b.l, b.c, n),
                 "donchian": lambda n: ind.donchian(b.h, b.l, n), "ichimoku": lambda: ind.ichimoku(b.h, b.l, b.c),
                 "zvol": lambda n: ind.zscore([x if x > 0 else 1.0 for x in b.v], n)}[name]
            self._cache[key] = f(*args)
        return self._cache[key]

    def htf(self, tf):
        """(Bars at tf, {base index -> last CLOSED htf index}) built from the base bars."""
        if tf not in self._htf:
            hb = self.bars.resample(tf, self.day_offset() if tf in ("1d", "D1") else 0)
            idx = [hb.last_closed_at(self.bars.end(i)) for i in range(len(self.bars))]
            self._htf[tf] = (hb, idx)
        return self._htf[tf]

    def day_offset(self):
        """Where the trading day starts, in seconds after 00:00 UTC: 17:00 New York for 24-hour
        markets (forex, metals, futures), 00:00 UTC for crypto. Approximated with EST (22:00 UTC)."""
        return 0 if self.inst["class"] == "crypto" else 22 * 3600

    def ny(self, i):
        """New York wall-clock datetime of bar i's START."""
        if self._ny is None:
            self._ny = {}
        if i not in self._ny:
            self._ny[i] = tc.to_local("America/New_York", tc.utc_of(self.t[i]))
        return self._ny[i]

    def ny_minutes(self, i):
        d = self.ny(i)
        return d.hour * 60 + d.minute

    def local(self, i, zone):
        return tc.to_local(zone, tc.utc_of(self.t[i]))


def _cost_r(inst, entry, stop, cfg):
    """Round-trip costs as a fraction of R: the spread, two slippages and commission."""
    risk = abs(entry - stop)
    if risk <= 0:
        return 0.0
    spread = float(cfg.get("spread") if cfg.get("spread") is not None else inst.get("spread") or 0)
    slip = float(cfg.get("slippage_ticks", 0)) * inst["tick"]
    comm_lot = float(cfg.get("commission_per_lot", 0) or 0)
    comm_price = comm_lot / inst["contract"] if inst["contract"] else 0.0
    return (spread + 2 * slip + comm_price) / risk


def run(bars, setup, inst, params=None, cfg=None, start=None, end=None):
    """Backtest one setup on one series. Returns {trades, signals, params, bars, span}."""
    cfg = dict(cfg or {})
    p = dict(setup.defaults)
    p.update(params or {})
    ctx = Context(bars, inst, p, cfg)
    setup.prepare(ctx)
    n = len(bars)
    lo = max(getattr(setup, "warmup", 50), bars.first_from(start) if start else 0, 1)
    hi = n if end is None else min(n, max(lo, bars.last_closed_at(end) + 1))
    trades, signals = [], []
    pos = pending = None
    atr_l = ctx.ind("atr", 14)
    half_spread = float(cfg.get("spread") if cfg.get("spread") is not None else inst.get("spread") or 0) / 2.0
    slip = float(cfg.get("slippage_ticks", 0)) * inst["tick"]
    for i in range(lo, hi):
        o, h, l, c = bars.o[i], bars.h[i], bars.l[i], bars.c[i]
        # 1. a pending limit order: fill or expire
        if pending is not None and pos is None:
            sg, placed = pending
            fill = None
            if sg.side == "buy" and l <= sg.entry:
                fill = min(o, sg.entry)
            elif sg.side == "sell" and h >= sg.entry:
                fill = max(o, sg.entry)
            if fill is not None:
                pos = _open(sg, i, fill, inst, cfg, signals_i=placed)
                pending = None
            elif i - placed >= sg.expiry_bars:
                signals.append({"t": bars.t[placed], "side": sg.side, "taken": False, "reason": "limit not filled",
                                "tag": sg.tag})
                pending = None
        # 2. manage the open position through bar i
        if pos is not None:
            done = _manage(pos, i, o, h, l, c, bars, atr_l, slip)
            if not done and getattr(setup, "exit_rule", None) and i > pos["entry_i"] and setup.exit_rule(ctx, i, pos):
                pos["exit"], pos["exit_i"], pos["outcome"] = c, i, "rule"
                done = True
            if done:
                trades.append(_close(pos, inst, cfg, ctx))
                pos = None
        # 3. at the close of bar i: ask the setup (never on the last bar: nothing to fill on)
        if i >= n - 1:
            continue
        out = setup.signal(ctx, i)
        if out is None:
            continue
        if isinstance(out, Skip):
            signals.append({"t": bars.t[i], "side": out.side, "taken": False, "reason": out.reason, "tag": ""})
            continue
        if pos is not None or pending is not None:
            signals.append({"t": bars.t[i], "side": out.side, "taken": False, "reason": "already in a trade",
                            "tag": out.tag})
            continue
        if (out.side == "buy" and out.stop >= c) or (out.side == "sell" and out.stop <= c):
            signals.append({"t": bars.t[i], "side": out.side, "taken": False, "reason": "stop on the wrong side",
                            "tag": out.tag})
            continue
        signals.append({"t": bars.t[i], "side": out.side, "taken": True, "reason": "", "tag": out.tag})
        if out.entry == "market":
            fill = bars.o[i + 1] + (half_spread + slip) * (1 if out.side == "buy" else -1)
            if (out.side == "buy" and fill <= out.stop) or (out.side == "sell" and fill >= out.stop):
                signals[-1].update(taken=False, reason="gapped through the stop before the fill")
                continue
            pos = _open(out, i + 1, fill, inst, cfg, signals_i=i, at_open=True)
        else:
            pending = (out, i)
    if pos is not None:
        pos["exit"], pos["exit_i"], pos["outcome"] = bars.c[hi - 1], hi - 1, "end"
        trades.append(_close(pos, inst, cfg, ctx))
    if pending is not None:
        sg, placed = pending
        signals.append({"t": bars.t[placed], "side": sg.side, "taken": False, "reason": "limit still pending at the end",
                        "tag": sg.tag})
    return {"trades": trades, "signals": signals, "params": p, "bars": hi - lo,
            "span": [bars.t[lo] if lo < n else None, bars.t[hi - 1] if hi - 1 < n else None]}


def _open(sg, i, fill, inst, cfg, signals_i, at_open=False):
    risk = abs(fill - sg.stop)
    return {"sg": sg, "side": sg.side, "entry_i": i, "signal_i": signals_i, "entry": fill, "stop": sg.stop,
            "stop0": sg.stop, "target": sg.target, "risk": risk, "mae": 0.0, "mfe": 0.0, "be_done": False,
            "first_bar_open": at_open}


def _manage(pos, i, o, h, l, c, bars, atr_l, slip):
    sg = pos["sg"]
    long = pos["side"] == "buy"
    risk = pos["risk"] or 1e-12
    adverse = (pos["entry"] - l) if long else (h - pos["entry"])
    favor = (h - pos["entry"]) if long else (pos["entry"] - l)
    pos["mae"] = max(pos["mae"], adverse / risk)
    pos["mfe"] = max(pos["mfe"], favor / risk)
    st, tg = pos["stop"], pos["target"]
    if long:
        if l <= st:
            pos["exit"] = min(o, st) - slip if o < st else st - slip
            pos["outcome"] = "be" if pos["be_done"] and abs(st - pos["entry"]) < 1e-12 else \
                "trail" if pos.get("trailed") else "stop"
        elif tg is not None and h >= tg:
            pos["exit"], pos["outcome"] = max(o, tg) if o > tg else tg, "target"
    else:
        if h >= st:
            pos["exit"] = max(o, st) + slip if o > st else st + slip
            pos["outcome"] = "be" if pos["be_done"] and abs(st - pos["entry"]) < 1e-12 else \
                "trail" if pos.get("trailed") else "stop"
        elif tg is not None and l <= tg:
            pos["exit"], pos["outcome"] = min(o, tg) if o < tg else tg, "target"
    if "outcome" in pos:
        pos["exit_i"] = i
        return True
    held = i - pos["entry_i"] + 1
    if (sg.max_bars and held >= sg.max_bars) or (sg.flat_at and bars.end(i) >= sg.flat_at):
        pos["exit"], pos["exit_i"], pos["outcome"] = c, i, "time"
        return True
    # after the bar: break-even and trailing for the NEXT bar
    if sg.be_at_r and not pos["be_done"] and pos["mfe"] >= sg.be_at_r:
        pos["stop"], pos["be_done"] = pos["entry"], True
    if sg.trail_atr and atr_l[i]:
        if long:
            new = c - sg.trail_atr * atr_l[i]
            if new > pos["stop"]:
                pos["stop"], pos["trailed"] = new, True
        else:
            new = c + sg.trail_atr * atr_l[i]
            if new < pos["stop"]:
                pos["stop"], pos["trailed"] = new, True
    return False


def _close(pos, inst, cfg, ctx):
    long = pos["side"] == "buy"
    exit_px = pos["exit"]
    risk = pos["risk"] or 1e-12
    gross = ((exit_px - pos["entry"]) if long else (pos["entry"] - exit_px)) / risk
    spread = float(cfg.get("spread") if cfg.get("spread") is not None else inst.get("spread") or 0)
    comm = float(cfg.get("commission_per_lot", 0) or 0) / (inst["contract"] or 1)
    # still to pay: half the spread on the way out (a limit entry paid none on the way in) and commission
    r = gross - (spread / 2.0 * (1 if pos["first_bar_open"] else 2) + comm) / risk
    bars = ctx.bars
    et = bars.t[pos["entry_i"]]
    ny = tc.to_local("America/New_York", tc.utc_of(et))
    reg = ctx.ind("regime")
    return {"side": pos["side"], "tag": pos["sg"].tag, "signal_t": bars.t[pos["signal_i"]], "entry_t": et,
            "exit_t": bars.end(pos["exit_i"]), "entry": pos["entry"], "stop": pos["stop0"], "target": pos["target"],
            "exit": pos["exit"], "outcome": pos["outcome"], "r": round(r, 4), "gross_r": round(gross, 4),
            "bars": pos["exit_i"] - pos["entry_i"] + 1, "mae_r": round(pos["mae"], 3), "mfe_r": round(pos["mfe"], 3),
            "risk": pos["risk"], "hour_ny": ny.hour, "weekday": ny.strftime("%a"),
            "date": tc.to_local("America/New_York", tc.utc_of(et) + datetime.timedelta(hours=7)).date().isoformat(),
            "regime": reg[pos["signal_i"]], "features": pos["sg"].features}


def risk_ok(stop_dist, ctx, i, min_atr=0.1, max_atr=6.0):
    """A sane stop: between min_atr and max_atr x ATR(14). The compendium's 0.4-pip stop that
    asked for 6.24 lots is exactly what this catches."""
    a = ctx.ind("atr", 14)[i]
    if a is None or a <= 0 or stop_dist <= 0:
        return False
    return min_atr * a <= stop_dist <= max_atr * a


def nan_to_none(x):
    return None if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))) else x
