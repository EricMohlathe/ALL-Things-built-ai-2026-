#!/usr/bin/env python3
"""
engine.py — bar-by-bar backtest of the Isaiah 60:22 session-range strategies.

This is a faithful Python port of the logic in the MT5 and cTrader builds:
the same New York clock with the real US daylight-saving rule, the same range
window, the same entry models, the same risk kernel, and the same journal CSV
schema — so srf_forensics.py, pf_lab.py, target_curve.py and portfolio.py all
consume its output without modification.

    python3 engine.py --symbol XAUUSD --strategy orb --model break_direct
    python3 engine.py --symbol XAUUSD --strategy orb --model retest --target-r 2
    python3 engine.py --symbol XAUUSD --strategy orb --exit time_only

WHAT IT IS HONEST ABOUT

  Real spread.  Every bar carries the mean bid-ask spread actually quoted in
  that minute. Entries pay it, exits pay it. No fixed-spread assumption.

  Intrabar.  M1 bars, not ticks. Within a bar the engine assumes the path
  touched the worse side first — if a bar's range spans both the stop and the
  target, the STOP is taken. That is the pessimistic convention and it is the
  right one: the alternative flatters every result you will ever produce.

  No look-ahead. Signals are evaluated on CLOSED bars only. An entry fills at
  the next bar's open plus half the spread, not at the signal bar's close.

WHAT IT IS NOT

  Not a tick simulator. Slippage beyond the spread is not modelled, and
  neither is broker rejection. Treat its numbers as an upper bound on what
  the same rules would do live.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import math
import os
import sys

import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "journals")

PIP = {
    "EURUSD": 1e-4, "GBPUSD": 1e-4, "AUDUSD": 1e-4, "NZDUSD": 1e-4,
    "USDCHF": 1e-4, "USDCAD": 1e-4, "EURGBP": 1e-4, "EURAUD": 1e-4,
    "USDJPY": 1e-2, "EURJPY": 1e-2, "GBPJPY": 1e-2, "AUDJPY": 1e-2,
    "XAUUSD": 0.1, "XAGUSD": 0.01,
    "USATECHIDXUSD": 1.0, "USA500IDXUSD": 1.0, "USA30IDXUSD": 1.0,
}


# ── New York clock, identical rule to the EAs ────────────────────────

def _first_sunday_offset(first: dt.datetime) -> int:
    # Monday=0 ... Sunday=6 ; we want Sunday
    return (6 - first.weekday()) % 7


def us_dst(utc: dt.datetime) -> bool:
    """EDT runs 2nd Sunday March 07:00 UTC -> 1st Sunday November 06:00 UTC."""
    mar1 = dt.datetime(utc.year, 3, 1, tzinfo=dt.timezone.utc)
    nov1 = dt.datetime(utc.year, 11, 1, tzinfo=dt.timezone.utc)
    dst_start = mar1 + dt.timedelta(days=_first_sunday_offset(mar1) + 7, hours=7)
    dst_end = nov1 + dt.timedelta(days=_first_sunday_offset(nov1), hours=6)
    return dst_start <= utc < dst_end


def to_ny(utc: pd.Timestamp) -> pd.Timestamp:
    u = utc.to_pydatetime()
    if u.tzinfo is None:
        u = u.replace(tzinfo=dt.timezone.utc)
    return utc + pd.Timedelta(hours=-4 if us_dst(u) else -5)


def in_window(now_min: int, start_min: int, end_min: int) -> bool:
    if start_min == end_min:
        return False
    if start_min < end_min:
        return start_min <= now_min < end_min
    return now_min >= start_min or now_min < end_min


# ── Presets, matching the EA defaults ────────────────────────────────

PRESETS = {
    "orb": dict(range_start=9 * 60 + 30, range_end=9 * 60 + 35,
                trade_start=9 * 60 + 35, trade_end=10 * 60 + 30,
                flat=15 * 60 + 55, max_trades=2, max_range_atr=3.0),
    "sweep": dict(range_start=19 * 60, range_end=0,
                  trade_start=2 * 60, trade_end=11 * 60,
                  flat=12 * 60, max_trades=1, max_range_atr=2.5),
}


class Journal:
    COLUMNS = ["run_tag", "symbol", "preset", "model", "ticket", "direction",
               "ny_day", "entry_time_ny", "exit_time_ny",
               "entry_price", "exit_price", "sl_price", "tp_price",
               "risk_points", "r_realized", "mfe_r", "mae_r",
               "spread_pts_entry", "range_high", "range_low", "range_pts",
               "atr_pts", "range_atr_ratio", "rvol", "bias", "lots",
               "profit_ccy", "balance_after", "bars_held", "exit_reason"]

    def __init__(self):
        self.rows: list[dict] = []

    def add(self, **kw):
        self.rows.append({c: kw.get(c, "") for c in self.COLUMNS})

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=self.COLUMNS)


def atr_from_daily(day_ranges: list[float], period: int = 14) -> float:
    if len(day_ranges) < 2:
        return 0.0
    return float(np.mean(day_ranges[-period:]))


# ── Market structure, mirroring DetectMSS in the EAs ─────────────────

def find_swing(bars: pd.DataFrame, upto: int, want_high: bool,
               fractal_right: int = 2, lookback: int = 40) -> tuple[float, int] | None:
    """
    Most recent CONFIRMED swing at or before bar `upto`.

    A swing needs `fractal_right` bars on each side, so it is only confirmed
    that many bars after it printed — which is exactly why the EA cannot act
    on it instantly either. Returns (level, index) or None.
    """
    n = fractal_right
    hi = bars["high"].to_numpy()
    lo = bars["low"].to_numpy()

    start = upto - n
    stop = max(0, upto - lookback)
    for i in range(start, stop, -1):
        if i - n < 0 or i + n > upto:
            continue
        pivot = hi[i] if want_high else lo[i]
        ok = True
        for k in range(1, n + 1):
            left = hi[i - k] if want_high else lo[i - k]
            right = hi[i + k] if want_high else lo[i + k]
            if want_high:
                if left >= pivot or right >= pivot:
                    ok = False
                    break
            else:
                if left <= pivot or right <= pivot:
                    ok = False
                    break
        if ok:
            return float(pivot), i
    return None


def detect_mss(bars: pd.DataFrame, i: int, trade_dir: int,
               fractal_right: int = 2, lookback: int = 40) -> float | None:
    """
    After a sweep of the low we need price to close above the most recent
    swing HIGH (and vice versa). That displacement is what says the reversal
    has intent — a wick alone is not the trade.

    Returns the protected extreme to stop behind, or None if no MSS yet.
    """
    c = float(bars["close"].iloc[i])

    if trade_dir > 0:
        sw = find_swing(bars, i, True, fractal_right, lookback)
        if sw is None or c <= sw[0]:
            return None
        lows = bars["low"].to_numpy()[sw[1]:i + 1]
        return float(lows.min()) if len(lows) else None

    sw = find_swing(bars, i, False, fractal_right, lookback)
    if sw is None or c >= sw[0]:
        return None
    highs = bars["high"].to_numpy()[sw[1]:i + 1]
    return float(highs.max()) if len(highs) else None


def build_bias_series(df: pd.DataFrame, mode: str, period: int = 50):
    """
    Higher-timeframe bias, computed so it can never see the future: the value
    used at time t comes from the last H4 bar that CLOSED strictly before t.
    """
    if mode == "off":
        return None

    if mode == "htf_ema":
        h4 = df.set_index("time_utc")["close"].resample("4h").last().dropna()
        if len(h4) < period + 2:
            return None
        ema = h4.ewm(span=period, adjust=False).mean()
        out = pd.DataFrame({"close": h4, "ema": ema})
        out["prev_ema"] = out["ema"].shift(1)
        out["bias"] = 0
        out.loc[(out["close"] > out["ema"]) & (out["ema"] >= out["prev_ema"]), "bias"] = 1
        out.loc[(out["close"] < out["ema"]) & (out["ema"] <= out["prev_ema"]), "bias"] = -1
        # shift so a bar's bias is only usable AFTER it closes
        out["bias"] = out["bias"].shift(1)
        return out["bias"].dropna()

    if mode == "prev_day":
        d = df.set_index("time_utc")["close"].resample("1D")
        mid = (d.max() + d.min()) / 2.0
        return mid.shift(1).dropna()

    return None


def bias_at(series, mode: str, when: pd.Timestamp, price: float) -> int:
    if series is None or len(series) == 0:
        return 0
    idx = series.index.searchsorted(when, side="right") - 1
    if idx < 0:
        return 0
    val = series.iloc[idx]
    if mode == "htf_ema":
        return int(val)
    if mode == "prev_day":
        if price > val:
            return 1
        if price < val:
            return -1
    return 0


def bars_midnight(g: pd.DataFrame) -> float:
    """Opening price of the 00:00 New York bar for this session."""
    m = g[g["ny_min"] == 0]
    return float(m["open"].iloc[0]) if len(m) else 0.0


def run(symbol: str, strategy: str, model: str, target_r: float,
        exit_mode: str, min_rvol: float, be_at_r: float,
        partial_at_r: float, partial_pct: float,
        risk_pct: float, run_tag: str,
        bias_mode: str = "off", require_bias: bool = False,
        use_midnight_open: bool = False) -> pd.DataFrame:

    path = os.path.join(DATA_DIR, f"{symbol}_M1.csv.gz")
    if not os.path.exists(path):
        sys.exit(f"No data for {symbol}. Run fetch_dukascopy.py first.")

    with gzip.open(path, "rt") as fh:
        df = pd.read_csv(fh, parse_dates=["time_utc"])
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    df["time_utc"] = pd.to_datetime(df["time_utc"], utc=True)

    # New York calendar columns
    off = df["time_utc"].dt.to_pydatetime()
    shifts = np.array([-4 if us_dst(u) else -5 for u in off])
    df["ny"] = df["time_utc"] + pd.to_timedelta(shifts, unit="h")
    df["ny_min"] = df["ny"].dt.hour * 60 + df["ny"].dt.minute
    df["ny_date"] = df["ny"].dt.date

    bias_series = build_bias_series(df, bias_mode)

    p = PRESETS[strategy]
    wraps = p["range_end"] <= p["range_start"]

    # session key: a wrapping range belongs to the session that follows it
    if wraps:
        key = np.where(df["ny_min"].to_numpy() >= p["range_start"],
                       (df["ny"] + pd.Timedelta(days=1)).dt.date, df["ny_date"])
        df["skey"] = key
    else:
        df["skey"] = df["ny_date"]

    pip = PIP.get(symbol, 1e-4)
    jr = Journal()

    balance = 10000.0
    ticket = 0
    day_ranges: list[float] = []
    rvol_hist: list[float] = []

    for skey, g in df.groupby("skey", sort=True):
        g = g.sort_values("time_utc")
        m = g["ny_min"].to_numpy()

        rng_mask = np.array([in_window(x, p["range_start"], p["range_end"]) for x in m])
        trd_mask = np.array([in_window(x, p["trade_start"], p["trade_end"]) for x in m])
        hold_mask = np.array([in_window(x, p["trade_start"], p["flat"]) for x in m])

        if rng_mask.sum() < 2 or trd_mask.sum() < 5:
            continue

        rh = float(g.loc[rng_mask, "high"].max())
        rl = float(g.loc[rng_mask, "low"].min())
        if not (rh > rl > 0):
            continue

        rng_pts = (rh - rl) / pip
        atr_pts = atr_from_daily(day_ranges)
        day_ranges.append(rng_pts)

        # relative volume, same definition as the EAs: this session's range
        # window tick count over the mean of the previous sessions'
        vol_today = float(g.loc[rng_mask, "ticks"].sum())
        rvol = (vol_today / np.mean(rvol_hist[-20:])) if len(rvol_hist) >= 2 else 1.0
        rvol_hist.append(vol_today)

        if atr_pts > 0 and p["max_range_atr"] > 0 and rng_pts > p["max_range_atr"] * atr_pts:
            continue
        if min_rvol > 0 and rvol < min_rvol:
            continue

        bars = g.reset_index(drop=True)
        trd_idx = np.where(trd_mask)[0]
        if len(trd_idx) == 0:
            continue
        first_trd, last_trd = int(trd_idx[0]), int(trd_idx[-1])
        hold_idx = np.where(hold_mask)[0]
        last_hold = int(hold_idx[-1]) if len(hold_idx) else last_trd

        midnight_open = 0.0
        if use_midnight_open:
            mid = bars_midnight(g)
            midnight_open = mid if mid else 0.0

        trades_today = 0
        break_dir = 0
        break_level = 0.0
        bars_since_break = 0
        sweep_side = 0
        sweep_extreme = 0.0
        bars_since_sweep = 0
        reclaimed = False
        i = first_trd

        while i <= last_trd and trades_today < p["max_trades"]:
            bar = bars.iloc[i]
            c, h, l = float(bar["close"]), float(bar["high"]), float(bar["low"])
            sig_dir, stop_price, trigger = 0, 0.0, ""

            if strategy == "orb":
                if break_dir == 0:
                    if c > rh:
                        break_dir, break_level, bars_since_break = 1, rh, 0
                    elif c < rl:
                        break_dir, break_level, bars_since_break = -1, rl, 0
                    if break_dir != 0 and model == "break_direct":
                        sig_dir = break_dir
                        stop_price = rl if break_dir > 0 else rh
                        trigger = "direct_break"
                else:
                    bars_since_break += 1
                    if bars_since_break > 60:
                        break_dir = 0
                    elif model == "retest" and 1 <= bars_since_break <= 20:
                        o = float(bar["open"])
                        if break_dir > 0 and l <= break_level and c > break_level and c > o:
                            sig_dir, stop_price, trigger = 1, l, "retest_rejection"
                        elif break_dir < 0 and h >= break_level and c < break_level and c < o:
                            sig_dir, stop_price, trigger = -1, h, "retest_rejection"

            else:  # sweep
                if sweep_side == 0:
                    if h > rh:
                        sweep_side, sweep_extreme, bars_since_sweep = 1, h, 0
                    elif l < rl:
                        sweep_side, sweep_extreme, bars_since_sweep = -1, l, 0
                else:
                    bars_since_sweep += 1
                    if sweep_side > 0:
                        sweep_extreme = max(sweep_extreme, h)
                    else:
                        sweep_extreme = min(sweep_extreme, l)

                    if not reclaimed:
                        inside = (c < rh) if sweep_side > 0 else (c > rl)
                        if inside:
                            reclaimed = True
                        elif bars_since_sweep > 6:
                            # not a sweep, a breakout — stand down
                            sweep_side, reclaimed = 0, False
                    else:
                        want = -sweep_side

                        # bias: the sweep predicts volatility, not direction,
                        # so direction has to come from here
                        b = bias_at(bias_series, bias_mode,
                                    bars.iloc[i]["time_utc"], c)
                        blocked = (require_bias and b == 0) or (b != 0 and b != want)

                        # midnight open: buy BELOW it, sell ABOVE it
                        if not blocked and midnight_open > 0:
                            side_ok = (c < midnight_open) if want > 0 else (c > midnight_open)
                            blocked = not side_ok

                        if not blocked:
                            if model == "sweep_mss":
                                prot = detect_mss(bars, i, want)
                                if prot is not None:
                                    sig_dir = want
                                    stop_price = prot
                                    trigger = "sweep_mss"
                            else:
                                sig_dir = want
                                stop_price = sweep_extreme
                                trigger = "sweep_reclaim"

            if sig_dir == 0 or i + 1 > last_trd:
                i += 1
                continue

            # ── fill on the NEXT bar's open, paying half the spread each side
            e = bars.iloc[i + 1]
            spread = float(e["spread"]) if not math.isnan(e["spread"]) else 0.0
            entry = float(e["open"]) + (spread / 2 if sig_dir > 0 else -spread / 2)

            risk = abs(entry - stop_price)
            if risk <= 0:
                i += 1
                continue

            # stop floor/ceiling in ATR terms, same as the EA
            risk_pts = risk / pip
            if atr_pts > 0:
                if risk_pts < 0.25 * atr_pts:
                    risk_pts = 0.25 * atr_pts
                    risk = risk_pts * pip
                if risk_pts > 3.0 * atr_pts:
                    i += 1
                    continue
            # spread gate: reject if the spread is more than 10% of the stop
            if risk_pts > 0 and (spread / pip) / risk_pts > 0.10:
                i += 1
                continue

            sl = entry - risk if sig_dir > 0 else entry + risk
            tp = None
            if exit_mode in ("fixed_r", "r_then_time"):
                tp = entry + risk * target_r if sig_dir > 0 else entry - risk * target_r

            # ── walk forward
            mfe = mae = 0.0
            exit_price, exit_reason, exit_idx = None, "", i + 1
            be_armed = False
            realized = 0.0
            remaining = 1.0

            for j in range(i + 1, last_hold + 1):
                b = bars.iloc[j]
                bh, bl = float(b["high"]), float(b["low"])
                sp = float(b["spread"]) if not math.isnan(b["spread"]) else spread

                fav = (bh - entry) if sig_dir > 0 else (entry - bl)
                adv = (entry - bl) if sig_dir > 0 else (bh - entry)
                mfe = max(mfe, fav / risk)
                mae = max(mae, adv / risk)

                if partial_at_r > 0 and remaining == 1.0 and mfe >= partial_at_r:
                    realized += (partial_pct / 100.0) * partial_at_r
                    remaining = 1.0 - partial_pct / 100.0

                if be_at_r > 0 and not be_armed and mfe >= be_at_r:
                    be_armed = True
                    sl = entry

                hit_sl = (bl - sp / 2 <= sl) if sig_dir > 0 else (bh + sp / 2 >= sl)
                hit_tp = tp is not None and ((bh - sp / 2 >= tp) if sig_dir > 0
                                             else (bl + sp / 2 <= tp))

                # PESSIMISTIC: if a bar spans both, the stop is taken
                if hit_sl:
                    exit_price, exit_reason, exit_idx = sl, (
                        "break_even" if be_armed and abs(sl - entry) < 1e-12 else "stop_loss"), j
                    break
                if hit_tp:
                    exit_price, exit_reason, exit_idx = tp, "take_profit", j
                    break

            if exit_price is None:
                b = bars.iloc[last_hold]
                sp = float(b["spread"]) if not math.isnan(b["spread"]) else spread
                exit_price = float(b["close"]) - (sp / 2 if sig_dir > 0 else -sp / 2)
                exit_reason, exit_idx = "session_flat", last_hold

            move = (exit_price - entry) if sig_dir > 0 else (entry - exit_price)
            realized += remaining * (move / risk)

            ticket += 1
            trades_today += 1
            profit = realized * (balance * risk_pct / 100.0)
            balance += profit

            jr.add(run_tag=run_tag, symbol=symbol, preset=strategy.upper(),
                   model=model, ticket=ticket,
                   direction="LONG" if sig_dir > 0 else "SHORT",
                   ny_day=str(skey),
                   entry_time_ny=str(bars.iloc[i + 1]["ny"]),
                   exit_time_ny=str(bars.iloc[exit_idx]["ny"]),
                   entry_price=f"{entry:.5f}", exit_price=f"{exit_price:.5f}",
                   sl_price=f"{sl:.5f}", tp_price=f"{tp:.5f}" if tp else "0",
                   risk_points=f"{risk / pip:.1f}", r_realized=f"{realized:.4f}",
                   mfe_r=f"{mfe:.4f}", mae_r=f"{mae:.4f}",
                   spread_pts_entry=f"{spread / pip:.1f}",
                   range_high=f"{rh:.5f}", range_low=f"{rl:.5f}",
                   range_pts=f"{rng_pts:.1f}", atr_pts=f"{atr_pts:.1f}",
                   range_atr_ratio=f"{(rng_pts / atr_pts) if atr_pts else 0:.3f}",
                   rvol=f"{rvol:.3f}", bias=bias_mode.upper(), lots="0.00",
                   profit_ccy=f"{profit:.2f}", balance_after=f"{balance:.2f}",
                   bars_held=str(exit_idx - i - 1), exit_reason=exit_reason)

            i = exit_idx + 1
            break_dir, sweep_side, reclaimed = 0, 0, False

    return jr.frame()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--strategy", choices=["orb", "sweep"], default="orb")
    ap.add_argument("--model", default="break_direct",
                    choices=["break_direct", "retest", "sweep_reclaim", "sweep_mss"])
    ap.add_argument("--target-r", type=float, default=2.0)
    ap.add_argument("--exit", dest="exit_mode", default="fixed_r",
                    choices=["fixed_r", "time_only", "r_then_time"])
    ap.add_argument("--min-rvol", type=float, default=0.0)
    ap.add_argument("--be-at-r", type=float, default=0.0)
    ap.add_argument("--partial-at-r", type=float, default=0.0)
    ap.add_argument("--partial-pct", type=float, default=50.0)
    ap.add_argument("--risk-pct", type=float, default=0.5)
    ap.add_argument("--bias", default="off", choices=["off", "htf_ema", "prev_day"])
    ap.add_argument("--require-bias", action="store_true")
    ap.add_argument("--midnight-open", action="store_true")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    tag = args.tag or f"{args.strategy}_{args.model}_{args.exit_mode}_t{args.target_r}"
    out = args.out or os.path.join(OUT_DIR, f"{args.symbol}_{tag}.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    df = run(args.symbol, args.strategy, args.model, args.target_r,
             args.exit_mode, args.min_rvol, args.be_at_r,
             args.partial_at_r, args.partial_pct, args.risk_pct, tag,
             args.bias, args.require_bias, args.midnight_open)

    if df.empty:
        print(f"{args.symbol:14s} {tag:34s} NO TRADES")
        return

    df.to_csv(out, index=False)
    r = pd.to_numeric(df["r_realized"])
    wins, losses = r[r > 0], r[r < 0]
    pf = (wins.sum() / -losses.sum()) if len(losses) and losses.sum() != 0 else float("inf")
    print(f"{args.symbol:14s} {tag:34s} n={len(df):4d} "
          f"sess={df['ny_day'].nunique():3d} WR={len(wins)/len(r):6.1%} "
          f"PF={pf:5.2f} E={r.mean():+.3f}R tot={r.sum():+7.1f}R -> {out}")


if __name__ == "__main__":
    main()
