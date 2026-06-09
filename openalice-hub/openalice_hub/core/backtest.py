"""
Event-driven backtester — pure stdlib.

Honest by construction:
  * positions[i] is decided from data up to bar i's CLOSE
  * the resulting trade FILLS at bar i+1's OPEN  -> no lookahead bias
  * every fill is routed through ExecutionGate in PAPER mode (same safety path
    as live), and fees are charged on traded notional.
"""
from __future__ import annotations
from .execution_gate import ExecutionGate, Order


def run(strategy, bars: list[dict], symbol="ASSET", cash=10_000.0,
        fee_bps=10.0, position_frac=1.0, gate: ExecutionGate | None = None,
        stop_atr=None, tp_atr=None, trail_atr=None) -> dict:
    """stop_atr/tp_atr/trail_atr: ATR-multiple risk exits (honest win-rate/PF lever)."""
    gate = gate or ExecutionGate(mode="paper")
    targets = strategy.positions(bars)
    if stop_atr or tp_atr or trail_atr:
        from . import indicators as _ind
        atr = _ind.atr(bars, 14)
        raw = list(targets); tg = [0] * len(bars); cur = 0; stop = tp = None
        for i in range(len(bars)):
            a = atr[i] or 0
            fresh = raw[i] != 0 and (i == 0 or raw[i] != raw[i - 1])  # new signal only
            if cur == 0:
                if fresh and a:
                    cur = raw[i]; px = bars[i]["c"]
                    stop = px - cur * (stop_atr or 99) * a
                    tp = px + cur * (tp_atr or 99) * a if tp_atr else None
            else:
                px = bars[i]["c"]
                if trail_atr and a:                          # ratchet stop
                    ns = px - cur * trail_atr * a
                    stop = max(stop, ns) if cur > 0 else min(stop, ns)
                hit_stop = (cur > 0 and bars[i]["l"] <= stop) or (cur < 0 and bars[i]["h"] >= stop)
                hit_tp = tp and ((cur > 0 and bars[i]["h"] >= tp) or (cur < 0 and bars[i]["l"] <= tp))
                if hit_stop or hit_tp or raw[i] == 0:        # risk exit or strategy exit
                    cur = 0; stop = tp = None
            tg[i] = cur
        targets = tg
    fee = fee_bps / 10_000.0
    cash0 = cash
    units = 0.0          # >0 long, <0 short
    equity_curve, trades = [], []
    entry_px = None
    pos = 0

    for i in range(len(bars) - 1):
        tgt = targets[i]
        if not getattr(strategy, "allow_short", False) and tgt < 0:
            tgt = 0
        if tgt != pos:
            fill = bars[i + 1]["o"]
            # close existing
            if units != 0:
                gross = units * fill
                cash += gross
                cash -= abs(gross) * fee
                if entry_px is not None:
                    pnl = (fill - entry_px) * units
                    trades.append({"entry": entry_px, "exit": fill, "units": units,
                                   "pnl": pnl, "ret": pnl / (abs(entry_px * units) or 1)})
                units = 0.0; entry_px = None
            # open new
            if tgt != 0:
                notional = cash * position_frac
                units = (notional / fill) * (1 if tgt > 0 else -1)
                cash -= units * fill
                cash -= abs(units * fill) * fee
                entry_px = fill
                gate.place(Order(symbol=symbol, side=("buy" if tgt > 0 else "sell"),
                                 qty=abs(units), price=fill, connector="paper"))
            pos = tgt
        equity_curve.append(cash + units * bars[i + 1]["c"])

    # liquidate at last close
    last = bars[-1]["c"]
    if units != 0:
        cash += units * last - abs(units * last) * fee
        if entry_px is not None:
            pnl = (last - entry_px) * units
            trades.append({"entry": entry_px, "exit": last, "units": units,
                           "pnl": pnl, "ret": pnl / (abs(entry_px * units) or 1)})
    final = cash
    bh = cash0 * (bars[-1]["c"] / bars[0]["c"])   # buy & hold benchmark
    return {"symbol": symbol, "strategy": getattr(strategy, "name", "?"),
            "cash0": cash0, "final": final, "equity_curve": equity_curve,
            "trades": trades, "buy_hold": bh, "bars": len(bars)}
