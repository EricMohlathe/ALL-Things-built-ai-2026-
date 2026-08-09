#!/usr/bin/env python3
"""
fetch_dukascopy.py — real tick data, free, no API key.

Dukascopy publishes its historical feed as one LZMA-compressed file per
instrument per hour. Each tick is 20 bytes, big-endian:

    uint32   milliseconds since the top of the hour
    uint32   ask, in integer points
    uint32   bid, in integer points
    float32  ask volume
    float32  bid volume

Timestamps are UTC. This matters more than anything else in this workspace:
every window in Isaiah 60:22 is New York local, and UTC is the only honest
place to convert from.

    python3 fetch_dukascopy.py --symbols XAUUSD EURUSD --start 2025-08-01 \
                               --end 2026-08-01 --hours 12-22

Bars are built from the BID series, which is what a chart shows, and the
mean spread of each bar is carried alongside so the backtest can pay the
real cost of crossing rather than an assumption about it.

Output: backtest/data/<SYMBOL>_M1.csv.gz with columns
    time_utc, open, high, low, close, spread, ticks
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import lzma
import os
import struct
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

CA = "/root/.ccr/ca-bundle.crt"
BASE = "https://datafeed.dukascopy.com/datafeed"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Dukascopy stores prices as integers; this is the divisor per instrument.
SCALE = {
    "EURUSD": 1e5, "GBPUSD": 1e5, "AUDUSD": 1e5, "NZDUSD": 1e5,
    "USDCHF": 1e5, "USDCAD": 1e5, "EURGBP": 1e5, "EURAUD": 1e5,
    "USDJPY": 1e3, "EURJPY": 1e3, "GBPJPY": 1e3, "AUDJPY": 1e3,
    "CADJPY": 1e3, "CHFJPY": 1e3, "NZDJPY": 1e3,
    "GBPAUD": 1e5, "GBPCAD": 1e5, "GBPCHF": 1e5, "AUDCAD": 1e5,
    "AUDCHF": 1e5, "AUDNZD": 1e5, "CADCHF": 1e5, "EURCAD": 1e5,
    "EURNZD": 1e5, "EURCHF": 1e5, "NZDCAD": 1e5, "NZDCHF": 1e5,
    "XAUUSD": 1e3, "XAGUSD": 1e3,
    # verified against live 2026 prices, not guessed
    "BTCUSD": 1e1, "ETHUSD": 1e1,
    "LIGHTCMDUSD": 1e3, "BRENTCMDUSD": 1e3, "COPPERCMDUSD": 1e4,
    "USATECHIDXUSD": 1e3, "USA500IDXUSD": 1e3, "USA30IDXUSD": 1e3,
    "DEUIDXEUR": 1e3, "GBRIDXGBP": 1e3,
}

# Pip size, used only to report spreads in familiar units.
PIP = {
    "EURUSD": 1e-4, "GBPUSD": 1e-4, "AUDUSD": 1e-4, "NZDUSD": 1e-4,
    "USDCHF": 1e-4, "USDCAD": 1e-4, "EURGBP": 1e-4, "EURAUD": 1e-4,
    "USDJPY": 1e-2, "EURJPY": 1e-2, "GBPJPY": 1e-2, "AUDJPY": 1e-2,
    "CADJPY": 1e-2, "CHFJPY": 1e-2, "NZDJPY": 1e-2,
    "GBPAUD": 1e-4, "GBPCAD": 1e-4, "GBPCHF": 1e-4, "AUDCAD": 1e-4,
    "AUDCHF": 1e-4, "AUDNZD": 1e-4, "CADCHF": 1e-4, "EURCAD": 1e-4,
    "EURNZD": 1e-4, "EURCHF": 1e-4, "NZDCAD": 1e-4, "NZDCHF": 1e-4,
    "XAUUSD": 0.1, "XAGUSD": 0.01,
    "BTCUSD": 1.0, "ETHUSD": 0.1,
    "LIGHTCMDUSD": 0.01, "BRENTCMDUSD": 0.01, "COPPERCMDUSD": 1e-4,
    "USATECHIDXUSD": 1.0, "USA500IDXUSD": 1.0, "USA30IDXUSD": 1.0,
    "DEUIDXEUR": 1.0, "GBRIDXGBP": 1.0,
}

_local = threading.local()
_lock = threading.Lock()
_done = {"n": 0, "hit": 0, "none": 0, "fail": 0}


def session() -> requests.Session:
    if not hasattr(_local, "s"):
        s = requests.Session()
        s.headers.update({"User-Agent": "Mozilla/5.0"})
        ad = requests.adapters.HTTPAdapter(pool_connections=64, pool_maxsize=64)
        s.mount("https://", ad)
        _local.s = s
    return _local.s


def fetch_hour(symbol: str, when: dt.datetime, retries: int = 4) -> bytes | None:
    """Returns bytes on success, b'' for a genuine 404, None if it kept failing."""
    url = (f"{BASE}/{symbol}/{when.year}/{when.month - 1:02d}/{when.day:02d}/"
           f"{when.hour:02d}h_ticks.bi5")
    for attempt in range(retries):
        try:
            r = session().get(url, timeout=40, verify=CA)
            if r.status_code == 200:
                return r.content
            if r.status_code == 404:
                return b""          # no data for this hour (holiday/roll)
        except Exception:
            pass
        time.sleep(0.4 * (attempt + 1))     # the feed resets connections under load
    return None


def decode(raw: bytes, scale: float, hour_start: dt.datetime) -> list[tuple]:
    if not raw:
        return []
    try:
        data = lzma.LZMADecompressor().decompress(raw)
    except Exception:
        return []

    out = []
    for i in range(0, len(data) - 19, 20):
        ms, ask, bid, _av, _bv = struct.unpack(">IIIff", data[i:i + 20])
        if bid <= 0 or ask <= 0:
            continue
        out.append((hour_start + dt.timedelta(milliseconds=ms),
                    ask / scale, bid / scale))
    return out


def hours_in_range(start: dt.date, end: dt.date, lo: int, hi: int):
    """Yield every UTC hour in [start, end) whose hour-of-day is in [lo, hi]."""
    cur = dt.datetime(start.year, start.month, start.day, tzinfo=dt.timezone.utc)
    stop = dt.datetime(end.year, end.month, end.day, tzinfo=dt.timezone.utc)
    while cur < stop:
        if cur.weekday() < 5 or (cur.weekday() == 6 and cur.hour >= 21):
            if lo <= hi:
                if lo <= cur.hour <= hi:
                    yield cur
            else:                      # wraps midnight
                if cur.hour >= lo or cur.hour <= hi:
                    yield cur
        cur += dt.timedelta(hours=1)


def build_m1(ticks: list[tuple]) -> pd.DataFrame:
    if not ticks:
        return pd.DataFrame()
    df = pd.DataFrame(ticks, columns=["t", "ask", "bid"])
    df["spread"] = df["ask"] - df["bid"]
    df = df.set_index("t")

    g = df["bid"].resample("1min")
    bars = pd.DataFrame({
        "open": g.first(), "high": g.max(), "low": g.min(), "close": g.last(),
        "spread": df["spread"].resample("1min").mean(),
        "ticks": df["bid"].resample("1min").count(),
    }).dropna(subset=["open"])
    return bars


def fetch_symbol(symbol: str, start: dt.date, end: dt.date,
                 lo: int, hi: int, workers: int) -> pd.DataFrame:
    scale = SCALE.get(symbol)
    if scale is None:
        sys.exit(f"Unknown scale for {symbol}. Add it to SCALE in this file.")

    hours = list(hours_in_range(start, end, lo, hi))
    print(f"  {symbol}: {len(hours)} hourly files to fetch")

    results: dict[dt.datetime, list] = {}

    def work(h: dt.datetime):
        raw = fetch_hour(symbol, h)
        with _lock:
            _done["n"] += 1
            if raw:
                _done["hit"] += 1
            elif raw is None:
                _done["fail"] += 1
            else:
                _done["none"] += 1
            if _done["n"] % 400 == 0:
                print(f"    {_done['n']}/{len(hours)}  "
                      f"{_done['hit']} data / {_done['none']} no-data / "
                      f"{_done['fail']} FAILED", flush=True)
        if raw:
            results[h] = decode(raw, scale, h)

    _done.update({"n": 0, "hit": 0, "none": 0, "fail": 0})
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, hours))

    if _done["fail"]:
        print(f"    WARNING: {_done['fail']} hours failed after retries — "
              f"bars for those hours are missing, not empty.")

    ticks = []
    for h in sorted(results):
        ticks.extend(results[h])

    if not ticks:
        print(f"  {symbol}: NO DATA")
        return pd.DataFrame()

    bars = build_m1(ticks)
    pipsz = PIP.get(symbol, 1e-4)
    print(f"  {symbol}: {len(ticks):,} ticks -> {len(bars):,} M1 bars   "
          f"mean spread {bars['spread'].mean() / pipsz:.2f} pips")
    return bars


def main() -> None:
    ap = argparse.ArgumentParser(description="Download Dukascopy ticks into M1 bars.")
    ap.add_argument("--symbols", nargs="+", required=True)
    ap.add_argument("--start", required=True, help="YYYY-MM-DD (UTC)")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD (UTC, exclusive)")
    ap.add_argument("--hours", default="0-23",
                    help="UTC hour range to fetch, e.g. 12-22 or 22-17 (wraps)")
    ap.add_argument("--workers", type=int, default=32)
    args = ap.parse_args()

    lo, hi = (int(x) for x in args.hours.split("-"))
    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)

    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Dukascopy  {start} -> {end}  UTC hours {lo}-{hi}")

    for sym in args.symbols:
        out = os.path.join(DATA_DIR, f"{sym}_M1.csv.gz")
        if os.path.exists(out):
            print(f"  {sym}: cached at {out}, skipping")
            continue
        bars = fetch_symbol(sym, start, end, lo, hi, args.workers)
        if bars.empty:
            continue
        bars.index.name = "time_utc"
        with gzip.open(out, "wt") as fh:
            bars.to_csv(fh)
        print(f"  {sym}: wrote {out}")


if __name__ == "__main__":
    main()
