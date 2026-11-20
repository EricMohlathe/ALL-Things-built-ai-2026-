#!/usr/bin/env python3
"""Market data for trader-data: years of free history into a local cache, so the Setup
Lab, the Time Machine and the scanner can test on far more than 60 days. Standard library only.

    python3 data.py get EURUSD --from 2022-01-01 --to 2025-12-31          # Dukascopy M1, every day
    python3 data.py get EURUSD --from 2026-11-01 --ticks                   # M1 built from raw ticks (+ delta)
    python3 data.py get BTCUSD --tf 5m --from 2024-01-01                   # Binance, with taker delta
    python3 data.py get BTCUSD --tf 1h --from 2021-01 --source binance_vision   # monthly bulk files
    python3 data.py get GBPUSD --source histdata --year 2024               # HistData M1, one year
    python3 data.py get US500 --tf 1d --source stooq                       # decades of dailies
    python3 data.py get XAUUSD --tf 1h --source yahoo                      # two years of hourlies
    python3 data.py info                                                   # what is cached
    python3 data.py quality EURUSD --tf M1                                 # gaps, flat bars, bad jumps
    python3 data.py resample EURUSD --to H1                                # save a bigger timeframe
    python3 data.py fred CPIAUCSL DGS10 DGS2                               # macro series (trader-macro)
    python3 data.py import EURUSD --csv mt5_export.csv --tf M15            # your own CSV (MT5, cTrader)

Sources (--source, default auto): dukascopy (forex, metals, indices, oil; M1 from candles
or --ticks), binance and binance_vision (crypto, taker delta), histdata (forex M1), yahoo,
stooq (daily). Cache: trader/data/<SYMBOL>/<TF>.csv, merged on every download.

Every source here is free and unofficial or semi-official; each can change, throttle or
disappear. The data is for research. Check anything that matters against your broker.
"""

import argparse
import csv
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "trader-core"))
import tradercore as tc  # noqa: E402
import history as hist  # noqa: E402
from bars import Bars, TF_NAME, tf_seconds  # noqa: E402


def _date(text, end=False):
    if not text:
        return None
    t = str(text)
    if len(t) == 7:
        y, m = int(t[:4]), int(t[5:7])
        if end:
            nxt = datetime.date(y + (m == 12), m % 12 + 1, 1)
            return nxt - datetime.timedelta(days=1)
        return datetime.date(y, m, 1)
    if len(t) == 4:
        return datetime.date(int(t), 12, 31) if end else datetime.date(int(t), 1, 1)
    return datetime.date.fromisoformat(t)


def say(a, msg):
    if not a.json:
        print(msg, file=sys.stderr)


def cmd_get(a):
    cfg = tc.load_config(a.config)
    inst = tc.resolve(a.symbol, cfg)
    today = tc.utc_now().date()
    d1 = _date(a.to, True) or today - datetime.timedelta(days=1)
    d0 = _date(a.frm) or (d1 - datetime.timedelta(days=30))
    if d0 > d1:
        raise tc.TraderError("--from is after --to")
    tf = a.tf or ("1m" if a.source in (None, "auto", "dukascopy", "histdata") else "1d")
    src = a.source if a.source not in (None, "auto") else hist.auto_source(inst, tf)
    progress = (lambda m: say(a, m))
    if src == "dukascopy":
        bars = hist.fetch_dukascopy(inst, d0, d1, ticks=a.ticks, scale=a.scale, progress=progress)
    elif src == "binance":
        t0 = tc.ts_of(datetime.datetime.combine(d0, datetime.time()))
        t1 = tc.ts_of(datetime.datetime.combine(d1 + datetime.timedelta(days=1), datetime.time()))
        bars = hist.fetch_binance(inst, tf, t0, t1, progress=progress)
    elif src == "binance_vision":
        bars = hist.fetch_binance_vision(inst, tf, hist.months_between(d0, d1))
    elif src == "histdata":
        years = [a.year] if a.year else list(range(d0.year, d1.year + 1))
        bars = Bars(60, inst["symbol"])
        for y in years:
            say(a, "  histdata %s %d" % (inst["symbol"], y))
            bars = bars.merge(hist.fetch_histdata(inst, y))
    elif src == "yahoo":
        bars = hist.fetch_yahoo(inst, tf)
    elif src == "stooq":
        bars = hist.fetch_stooq(inst)
    else:
        raise tc.TraderError("unknown source %r" % src)
    if not len(bars):
        raise tc.TraderError("%s sent no bars for %s in that range" % (src, inst["symbol"]))
    merged = hist.save(bars, a.root)
    doc = {"symbol": inst["symbol"], "source": src, "tf": TF_NAME[bars.step], "downloaded": len(bars),
           "cached": len(merged), "first": tc.iso(tc.utc_of(merged.t[0])), "last": tc.iso(tc.utc_of(merged.t[-1])),
           "delta": "taker" if src.startswith("binance") else "tick-rule" if a.ticks else None,
           "path": hist.cache_path(inst["symbol"], bars.step, a.root)}
    if a.json:
        print(json.dumps(doc, indent=2))
    else:
        print("%s %s from %s: %s bars downloaded; the cache now holds %s bars, %s to %s (%s)." % (
            inst["symbol"], doc["tf"], src, "{:,}".format(doc["downloaded"]), "{:,}".format(doc["cached"]),
            doc["first"][:10], doc["last"][:10], doc["path"]))
        if doc["delta"]:
            print("Delta stored: %s." % doc["delta"])
    return 0


def cmd_info(a):
    rows = hist.inventory(a.root)
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0 if rows else 1
    if not rows:
        print("Nothing cached in %s yet. Start with: data.py get EURUSD --from 2024-01-01" % a.root)
        return 1
    print("%-8s %-4s %12s  %-20s  %s" % ("SYMBOL", "TF", "BARS", "FIRST", "LAST"))
    for r in rows:
        print("%-8s %-4s %12s  %-20s  %s" % (r["symbol"], r["tf"], "{:,}".format(r["bars"]), r["first"], r["last"]))
    return 0


def cmd_quality(a):
    b = hist.load(a.symbol.upper(), a.tf, a.root)
    q = hist.quality(b)
    if a.json:
        print(json.dumps(q, indent=2))
    else:
        print("%s %s: %s bars. %d gaps over 72 hours (weekends excluded by length), %d flat bars, %d outlier jumps."
              % (a.symbol.upper(), a.tf, "{:,}".format(q["bars"]), q["long_gap_count"], q["zero_range_bars"],
                 q["outlier_count"]))
        for g in q["long_gaps"][:5]:
            print("  gap after %s: %.1f hours" % (g["after"], g["hours"]))
        for j in q["outlier_jumps"][:5]:
            print("  jump at %s: %+g" % (j["at"], j["gap"]))
    return 0 if not q["outlier_count"] else 1


def cmd_resample(a):
    b = hist.load(a.symbol.upper(), a.to, a.root)
    hist.save(b, a.root)
    print("Saved %s %s: %s bars (%s)." % (a.symbol.upper(), TF_NAME[b.step], "{:,}".format(len(b)),
                                          hist.cache_path(a.symbol.upper(), b.step, a.root)))
    return 0


def cmd_import(a):
    """Your own CSV: time (unix or 'YYYY-MM-DD HH:MM[:SS]' or MT5 'YYYY.MM.DD HH:MM'), open, high, low, close[, volume]."""
    cfg = tc.load_config(a.config)
    inst = tc.resolve(a.symbol, cfg)
    step = tf_seconds(a.tf)
    out = Bars(step, inst["symbol"])
    zone = tc.zone_name(a.tz or "UTC")
    with open(a.csv, newline="", encoding="utf-8-sig") as fh:
        sample = fh.read(2048)
        fh.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        rows = list(csv.reader(fh, dialect))
    for r in rows:
        if not r or not r[0][:1].isdigit():
            continue
        try:
            if r[0].isdigit() and len(r[0]) >= 9:
                t = int(r[0])
                vals = r[1:]
            else:
                stamp = r[0].replace(".", "-")
                vals = r[1:]
                if len(r) > 1 and ":" in r[1] and "-" not in r[1]:
                    stamp, vals = stamp + " " + r[1], r[2:]
                t = tc.ts_of(tc.to_utc(zone, datetime.datetime.fromisoformat(stamp.strip())))
            out.append(t, float(vals[0]), float(vals[1]), float(vals[2]), float(vals[3]),
                       float(vals[4]) if len(vals) > 4 and vals[4] else 0.0)
        except (ValueError, IndexError):
            continue
    if not len(out):
        raise tc.TraderError("no rows I could read in %s" % a.csv)
    merged = hist.save(out, a.root)
    print("Imported %s %s bars of %s (cache now %s bars)." % ("{:,}".format(len(out)), TF_NAME[step], inst["symbol"],
                                                             "{:,}".format(len(merged))))
    return 0


def cmd_fred(a):
    out = {}
    for s in a.series:
        rows = hist.fetch_fred(s)
        out[s] = [(d.isoformat(), v) for d, v in rows]
        if not a.json:
            d, v = rows[-1]
            print("%-10s %s observations, last %s = %s" % (s, "{:,}".format(len(rows)), d.isoformat(), v))
    path = os.path.join(a.root, "macro", "fred.json")
    old = tc.read_json(path, "fred cache", required=False) or {}
    old.update(out)
    tc.write_json(path, old)
    if a.json:
        print(json.dumps({k: v[-5:] for k, v in out.items()}, indent=2))
    else:
        print("Saved to %s." % path)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Historical market data (trader-data).")
    ap.add_argument("--root", default=hist.CACHE, help="cache folder (default trader/data)")
    ap.add_argument("--config", default="trader/config.json")
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("get")
    p.add_argument("symbol")
    p.add_argument("--from", dest="frm", help="YYYY-MM-DD, YYYY-MM or YYYY")
    p.add_argument("--to")
    p.add_argument("--tf", help="1m (default for dukascopy/histdata), 5m, 15m, 1h, 4h, 1d")
    p.add_argument("--source", choices=["auto", "dukascopy", "binance", "binance_vision", "histdata", "yahoo", "stooq"])
    p.add_argument("--ticks", action="store_true", help="dukascopy: build M1 from raw ticks (tick-rule delta)")
    p.add_argument("--scale", type=float, help="dukascopy price divisor override")
    p.add_argument("--year", type=int, help="histdata: one year")
    sub.add_parser("info")
    p = sub.add_parser("quality")
    p.add_argument("symbol")
    p.add_argument("--tf", default="M1")
    p = sub.add_parser("resample")
    p.add_argument("symbol")
    p.add_argument("--to", required=True)
    p = sub.add_parser("import")
    p.add_argument("symbol")
    p.add_argument("--csv", required=True)
    p.add_argument("--tf", required=True)
    p.add_argument("--tz", help="the zone of the CSV's times (default UTC). Most MT5 servers: --tz MT5 "
                                "(UTC+2 / +3, midnight at 17:00 New York); others: an IANA name")
    p = sub.add_parser("fred")
    p.add_argument("series", nargs="+")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        return {"get": cmd_get, "info": cmd_info, "quality": cmd_quality, "resample": cmd_resample,
                "import": cmd_import, "fred": cmd_fred}[a.cmd](a)
    except (tc.TraderError, ValueError) as e:
        print("data.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
