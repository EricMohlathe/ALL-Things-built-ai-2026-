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
        fee_bps=10.0, position_frac=1.0, gate: ExecutionGate | None = None) -> dict:
    gate = gate or ExecutionGate(mode="paper")
    targets = strategy.positions(bars)
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
