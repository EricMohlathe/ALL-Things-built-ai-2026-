#!/usr/bin/env python3
"""Chart Scanner for trader-scanner: scans forex, commodities, indices and crypto
for setups, long and short. Standard library only.

    python3 scan.py universe                              # the instrument registry -> trader/universe.txt
    python3 scan.py daily                                 # daily setups, every class -> trader/watchlist.json
    python3 scan.py daily --class forex,crypto            # or --symbols EURUSD,XAUUSD,BTCUSD
    python3 scan.py range                                 # session-range breakouts so far today, both sides
    python3 scan.py range --class forex --session london  # one session for every pair
    python3 scan.py range --offline tests/fixtures/charts --now "2026-11-16 09:00 London"

universe  The built-in registry (tradercore.py instruments), plus your own from
          trader/instruments.json. Spot, CFD and cash-index instruments by
          default; --futures adds the CME contracts (ES, NQ, GC, CL, 6E ...).

daily     Daily CLOSES (Yahoo spark, 20 symbols a request, 6 months of 1-day
          bars; today's bar is dropped until its session closes). Every
          threshold is scaled to the instrument's own volatility (sigma = the
          standard deviation of its daily log returns), so one rule fits
          EURUSD at 0.4 % a day and SOLUSD at 4 %:
            breakout_20d / breakdown_20d   the last close beyond every close of the 20 before
            bull_flag / bear_flag          a 10-session run of 2 sigma or more, then 5 tight closes
            reclaim_ma20 / lose_ma20       crossed back over the 20-day average
            overbought / oversold          RSI 14 (Wilder) above 70 / under 30
            overbought_fade / oversold_bounce  that yesterday, and today turned
            squeeze                        the 20-day Bollinger band width within 10 % of its 60-day low
          Each hit gets a bias (long, short or neutral) from its setups.

range     Session-range breakouts, 5-minute bars, with exactly the Entry Timer's
          rule (trader-entry): each instrument in its own session (London for
          forex, COMEX for metals, NYMEX for energy, US cash for US indices,
          Xetra / LSE / TSE ... for the others, the UTC day for crypto) or
          --session for all. A hit is the first completed bar after the range
          that CLOSED above its high (long) or below its low (short), inside
          the entry window. Instruments whose session is not open are counted.

Yahoo's endpoints are free, unofficial and can lag. --offline reads saved
files: a folder of <SYMBOL>-*.json(.gz) charts, or one bundle {"FEED": v8 doc}.
A scan is a list of charts that match a rule, not a list of trades to take.
Exit code 0 when the scan found something, 1 when it did not or could not run.
"""

import argparse
import datetime
import importlib.util
import json
import math
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "trader-core"))
import tradercore as tc  # noqa: E402

SPARK_MAX = 20
MIN_DAILY = 30
NOTE = "A scan is a list of charts that match a rule, not a list of trades to take."
SETUPS = [
    ("breakout_20d", "20-day closing-high breakout", "long"),
    ("breakdown_20d", "20-day closing-low breakdown", "short"),
    ("bull_flag", "bull flag", "long"),
    ("bear_flag", "bear flag", "short"),
    ("reclaim_ma20", "reclaimed the 20-day average", "long"),
    ("lose_ma20", "lost the 20-day average", "short"),
    ("oversold", "oversold (RSI under 30)", "long"),
    ("overbought", "overbought (RSI over 70)", "short"),
    ("oversold_bounce", "oversold bounce", "long"),
    ("overbought_fade", "overbought fade", "short"),
    ("squeeze", "volatility squeeze", "neutral"),
]
LABEL = {k: v for k, v, _ in SETUPS}
BIAS = {k: b for k, _, b in SETUPS}


class ScanError(tc.TraderError):
    pass


def _entry_module():
    path = os.path.join(HERE, "..", "trader-entry", "entry.py")
    spec = importlib.util.spec_from_file_location("trader_entry_for_scan", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- daily setups

def rsi(closes, n=14):
    """Wilder's RSI on closes."""
    if len(closes) < n + 1:
        return None
    g = [max(0.0, closes[i] - closes[i - 1]) for i in range(1, len(closes))]
    lo = [max(0.0, closes[i - 1] - closes[i]) for i in range(1, len(closes))]
    ag, al = sum(g[:n]) / n, sum(lo[:n]) / n
    for i in range(n, len(g)):
        ag = (ag * (n - 1) + g[i]) / n
        al = (al * (n - 1) + lo[i]) / n
    return 100 - 100 / (1 + ag / al) if al else 100.0


def sigma_of(c):
    """Daily volatility: stdev of log returns, leaving out the last 15 (a fresh run
    should not set its own yardstick)."""
    rets = [math.log(c[i] / c[i - 1]) for i in range(1, len(c)) if c[i - 1] > 0 and c[i] > 0]
    base = rets[:-15] if len(rets) >= 30 else rets
    return statistics.pstdev(base) if len(base) >= 2 else 0.0


def bandwidth(c):
    m = sum(c) / len(c)
    return 4 * statistics.pstdev(c) / m if m else 0.0


def find_setups(c):
    """closes (oldest first, >= 30) -> (setup keys, numbers)."""
    last = c[-1]
    hi20, lo20 = max(c[-21:-1]), min(c[-21:-1])
    ma20, ma20_prev = sum(c[-20:]) / 20.0, sum(c[-21:-1]) / 20.0
    sig = sigma_of(c) or 1e-9
    run = math.log(c[-6] / c[-16])
    run_z = run / (sig * math.sqrt(10))
    rng5 = math.log(max(c[-5:]) / min(c[-5:]))
    tight = rng5 < sig * math.sqrt(5)
    r, r_prev = rsi(c), rsi(c[:-1])
    mom = math.log(c[-1] / c[-21]) / (sig * math.sqrt(20))
    tags = []
    if last > hi20:
        tags.append("breakout_20d")
    if last < lo20:
        tags.append("breakdown_20d")
    if run_z > 2.0 and tight:
        tags.append("bull_flag")
    if run_z < -2.0 and tight:
        tags.append("bear_flag")
    if c[-2] < ma20_prev and last > ma20:
        tags.append("reclaim_ma20")
    if c[-2] > ma20_prev and last < ma20:
        tags.append("lose_ma20")
    if r is not None and r < 30:
        tags.append("oversold")
    if r is not None and r > 70:
        tags.append("overbought")
    if r_prev is not None and r_prev < 30 and last > c[-2]:
        tags.append("oversold_bounce")
    if r_prev is not None and r_prev > 70 and last < c[-2]:
        tags.append("overbought_fade")
    look = min(60, len(c) - 20)
    if look >= 40:
        widths = [bandwidth(c[i - 20:i]) for i in range(len(c) - look + 1, len(c) + 1)]
        if widths[-1] <= 1.10 * min(widths) + 1e-12:
            tags.append("squeeze")
    return tags, {"rsi": r, "rsi_prev": r_prev, "high20": hi20, "low20": lo20, "ma20": ma20,
                  "sigma_pct": sig * 100, "run_z": run_z, "momentum_z": mom}


def bias_of(tags):
    longs = sum(1 for t in tags if BIAS[t] == "long")
    shorts = sum(1 for t in tags if BIAS[t] == "short")
    return "long" if longs > shorts else "short" if shorts > longs else "neutral"


def daily_closes(series, inst, now_utc, cfg):
    """[(date, close)] of complete daily bars: today's dropped until its session closes."""
    sname = inst["session"]
    tz = tc.session_def(sname, cfg)["tz"]
    today = tc.to_local(tz, now_utc).date()
    sinst, phase = tc.locate(sname, now_utc, cfg)
    today_done = sinst is None or (phase == "closed" and sinst["date"] == today.isoformat())
    out = {}
    for b in series["bars"]:
        d = tc.to_local(tz, tc.utc_of(b["t"])).date()
        if d > today or (d == today and not today_done):
            continue
        out[d] = float(b["c"])
    return sorted(out.items())


def scan_daily(data, insts, now_utc, cfg):
    """Pure. data = {SYMBOL: parsed chart}. Returns (hits, counts, last_dates)."""
    hits, dates = [], {}
    counts = {"requested": len(insts), "fetched": 0, "short": 0, "scanned": 0}
    for inst in insts:
        s = data.get(inst["symbol"])
        if not s:
            continue
        counts["fetched"] += 1
        bars = daily_closes(s, inst, now_utc, cfg)
        if len(bars) < MIN_DAILY:
            counts["short"] += 1
            continue
        counts["scanned"] += 1
        dates[bars[-1][0]] = dates.get(bars[-1][0], 0) + 1
        closes = [c for _, c in bars]
        tags, nums = find_setups(closes)
        if tags:
            hits.append({"symbol": inst["symbol"], "class": inst["class"], "session": inst["session"],
                         "setups": tags, "bias": bias_of(tags), "price": round(closes[-1], inst["digits"]),
                         "close_date": bars[-1][0].isoformat(), "rsi": round(nums["rsi"], 1) if nums["rsi"] else None,
                         "sigma_pct": round(nums["sigma_pct"], 2), "momentum_z": round(nums["momentum_z"], 2),
                         "level": round(nums["high20"] if bias_of(tags) == "long" else nums["low20"], inst["digits"])})
    hits.sort(key=lambda h: (-len(h["setups"]), -abs(h["momentum_z"]), h["symbol"]))
    counts["hits"] = len(hits)
    return hits, counts, dates


# ---------------------------------------------------------------- data

def parse_spark(text_or_doc):
    """Spark JSON -> {FEED: parsed chart}. Unknown symbols are simply missing."""
    doc = json.loads(text_or_doc) if isinstance(text_or_doc, str) else text_or_doc
    sp = (doc or {}).get("spark") if isinstance(doc, dict) else None
    if not isinstance(sp, dict):
        raise ScanError("Yahoo's spark answer is not the shape this tool knows")
    out = {}
    for item in sp.get("result") or []:
        resp = item.get("response") or []
        if not resp:
            continue
        feed = str(item.get("symbol") or (resp[0].get("meta") or {}).get("symbol") or "").upper()
        try:
            out[feed] = tc.parse_chart({"chart": {"result": [resp[0]]}}, feed)
        except tc.TraderError:
            continue
    if not out and sp.get("error"):
        err = sp["error"]
        raise ScanError("Yahoo spark: %s" % (err.get("description") or err.get("code") or err))
    return out


def fetch_daily(insts, pause, quiet=False):
    """Batches of 20 feeds -> ({SYMBOL: chart}, {SYMBOL: error})."""
    feeds = {}
    for i in insts:
        feeds.setdefault(i["feed"].upper(), []).append(i["symbol"])
    keys = list(feeds)
    data, failed = {}, {}
    for k in range(0, len(keys), SPARK_MAX):
        batch = keys[k:k + SPARK_MAX]
        if k and pause:
            tc.SLEEP(pause)
        path = "/v7/finance/spark?symbols=%s&range=6mo&interval=1d" % ",".join(
            tc.urllib.parse.quote(f, safe="=-") for f in batch)
        try:
            got = parse_spark(tc.yahoo_get(path))
        except (tc.TraderError, ValueError) as e:
            got = {}
            for f in batch:
                for s in feeds[f]:
                    failed[s] = str(e)
        for f in batch:
            for s in feeds[f]:
                if f in got:
                    data[s] = got[f]
                elif s not in failed:
                    failed[s] = "no data from Yahoo"
    return data, failed


def load_bundle(path, insts):
    """Offline daily data: a bundle {"FEED": v8 doc} file, or a folder of charts."""
    data, failed = {}, {}
    if os.path.isfile(path):
        doc = tc.read_json(path, "offline bundle")
        by_feed = {str(k).upper(): v for k, v in doc.items()} if isinstance(doc, dict) and "chart" not in doc else {}
        for i in insts:
            v = by_feed.get(i["feed"].upper())
            if v is None:
                continue
            try:
                data[i["symbol"]] = tc.parse_chart(v, i["feed"])
            except tc.TraderError as e:
                failed[i["symbol"]] = str(e)
        return data, failed
    for i in insts:
        try:
            data[i["symbol"]] = tc.get_chart(i, "1d", offline=path)
        except tc.TraderError as e:
            failed[i["symbol"]] = str(e)
    return data, failed


def pick(a, cfg):
    """The instruments to scan: --symbols, --watchlist, or the registry by --class."""
    if getattr(a, "symbols", None):
        out = []
        for s in re.split(r"[,\s]+", a.symbols):
            if s:
                inst = tc.resolve(s, cfg)
                if inst["symbol"] not in [x["symbol"] for x in out]:
                    out.append(inst)
        return out
    if getattr(a, "watchlist", None):
        doc = tc.read_json(a.watchlist, "watchlist")
        items = doc.get("hits", []) if isinstance(doc, dict) else doc
        return [tc.resolve(x.get("symbol") if isinstance(x, dict) else x, cfg) for x in items if x]
    kinds = None if getattr(a, "futures", False) else ("spot", "cfd")
    allowed = cfg.get("allowed_classes") or list(tc.CLASSES)
    classes = tc.parse_classes(getattr(a, "cls", None)) or [c for c in tc.CLASSES if c in allowed]
    blocked = {str(b).upper() for b in cfg.get("blocked") or []}
    out = [i for i in tc.universe(classes, cfg, kinds) if i["symbol"] not in blocked]
    if getattr(a, "limit", None):
        out = out[:a.limit]
    if not out:
        raise ScanError("no instruments to scan")
    return out


# ---------------------------------------------------------------- commands

def cmd_universe(a):
    cfg = tc.load_config(a.config)
    insts = pick(a, cfg)
    if not a.no_write:
        d = os.path.dirname(a.out)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            for i in insts:
                fh.write("%s|%s|%s|%s|%s\n" % (i["symbol"], i["class"], i["name"], i["feed"], i["session"]))
    by = {}
    for i in insts:
        by[i["class"]] = by.get(i["class"], 0) + 1
    if a.json:
        print(json.dumps({"count": len(insts), "by_class": by, "out": None if a.no_write else a.out}, indent=2))
    else:
        print("%d instruments: %s." % (len(insts), ", ".join("%d %s" % (by[c], c) for c in tc.CLASSES if c in by)))
        if not a.no_write:
            print("Wrote %s (SYMBOL|class|name|feed|session a line)." % a.out)
    return 0 if insts else 1


def cmd_daily(a):
    cfg = tc.load_config(a.config)
    now = tc.parse_now(a.now, cfg["timezone"])
    insts = pick(a, cfg)
    if a.offline:
        data, failed = load_bundle(a.offline, insts)
    else:
        if not a.quiet and not a.json:
            print("Fetching daily closes for %d instruments..." % len(insts), file=sys.stderr)
        data, failed = fetch_daily(insts, a.pause)
    hits, counts, dates = scan_daily(data, insts, now, cfg)
    nfailed = len(insts) - counts["fetched"]
    doc = {"created_by": "trader-scanner", "created_at": tc.iso(now), "mode": "daily",
           "as_of": max(dates, key=lambda d: (dates[d], d)).isoformat() + " close" if dates else None, "universe": len(insts),
           "scanned": counts["scanned"], "failed": nfailed, "source": "offline" if a.offline else "yahoo",
           "note": NOTE, "hits": hits}
    if not a.no_write:
        tc.write_json(a.out, doc)
    if a.json:
        print(json.dumps(dict(doc, counts=counts, failed_detail=failed), indent=2))
        return 0 if hits else 1
    print("Daily scan at %s, closes through %s (daily closes only, thresholds in each instrument's own sigma)."
          % (tc.stamp(now, cfg["timezone"]), doc["as_of"] or "nothing"))
    print("Fetched %d of %d instruments%s; %d scanned%s." % (
        counts["fetched"], len(insts), (" (%d failed or had no data)" % nfailed) if nfailed else "", counts["scanned"],
        (", %d had under %d days" % (counts["short"], MIN_DAILY)) if counts["short"] else ""))
    if hits:
        per = [(k, sum(1 for h in hits if k in h["setups"])) for k, _, _ in SETUPS]
        print("%d matched a setup: %s." % (len(hits), ", ".join("%d %s" % (n, LABEL[k]) for k, n in per if n)))
    else:
        print("No setups.")
    for h in hits[:a.show]:
        inst = tc.resolve(h["symbol"], cfg)
        print("  %-8s %-9s %-7s %14s  RSI %5s  sigma %5.2f%%  %s" % (
            h["symbol"], h["class"], h["bias"], tc.fmt_price(h["price"], inst),
            ("%.1f" % h["rsi"]) if h["rsi"] is not None else "-", h["sigma_pct"],
            ", ".join(LABEL[t] for t in h["setups"])))
    if len(hits) > a.show:
        print("  ... and %d more in the watchlist (--show N for more)." % (len(hits) - a.show))
    if not a.no_write:
        print("Wrote %s (mode daily, %d hit%s)." % (a.out, len(hits), "" if len(hits) == 1 else "s"))
    print(NOTE + " Next: pick one chart, then /trader-news SYMBOL and /trader-calendar.")
    return 0 if hits else 1


def cmd_range(a):
    cfg = tc.load_config(a.config)
    entry = _entry_module()
    insts = pick(a, cfg)
    if a.offline and not a.symbols and not a.watchlist and os.path.isdir(a.offline):
        have = []
        for i in insts:
            try:
                tc.offline_file(a.offline, i)
                have.append(i)
            except tc.TraderError:
                continue
        insts = have or insts
    zone = tc.session_def(a.session, cfg)["tz"] if a.session else cfg["timezone"]
    now = tc.parse_now(a.now, zone) if a.now else None
    hits, rows = [], []
    counts = {"requested": len(insts), "scanned": 0, "not_open": 0, "forming": 0, "failed": 0, "expired": 0}
    for n, inst in enumerate(insts):
        sname = a.session or inst["session"]
        clock = now or tc.utc_now()
        sinst, phase = tc.locate(sname, clock, cfg)
        if sinst is None or phase == "pre-open":
            counts["not_open"] += 1
            continue
        try:
            if a.offline:
                chart = tc.get_chart(inst, "5m", offline=a.offline)
            else:
                if n and a.pause:
                    tc.SLEEP(a.pause)
                chart = tc.get_chart(inst, "5m", "5d")
            res = entry.evaluate(chart, inst, clock, session=sname, range_minutes=a.range_minutes,
                                 side=a.side, cfg=cfg)
        except tc.TraderError as e:
            counts["failed"] += 1
            rows.append({"symbol": inst["symbol"], "error": str(e)})
            continue
        if res["phase"] == "forming":
            counts["forming"] += 1
            continue
        if res["status"] == "no-data":
            counts["failed"] += 1
            rows.append({"symbol": inst["symbol"], "error": res["reason"]})
            continue
        counts["scanned"] += 1
        if res["status"] == "expired":
            counts["expired"] += 1
        t = res.get("trigger")
        if t:
            hits.append({"symbol": inst["symbol"], "class": inst["class"], "session": sname, "tz": res["tz"],
                         "setups": ["range"], "side": t["side"], "direction": t["direction"], "date": res["date"],
                         "time": t["time"], "time_utc": t["time_utc"], "price": t["price"], "level": t["level"],
                         "range_high": res["range"]["high"], "range_low": res["range"]["low"],
                         "beyond_pips": t["beyond_pips"], "pip_label": inst["pip_label"], "bar_index": t["bar_index"]})
    hits.sort(key=lambda h: (h["time_utc"], h["symbol"]))
    clock = now or tc.utc_now()
    doc = {"created_by": "trader-scanner", "created_at": tc.iso(clock), "mode": "range", "as_of": tc.iso(clock),
           "universe": len(insts), "scanned": counts["scanned"], "failed": counts["failed"],
           "source": "offline" if a.offline else "yahoo", "session": a.session or "each instrument's own",
           "interval": "5m", "note": NOTE, "hits": hits}
    if not a.no_write:
        tc.write_json(a.out, doc)
    if a.json:
        print(json.dumps(dict(doc, counts=counts, errors=rows), indent=2))
        return 0 if hits else 1
    print("Session-range breakout scan at %s, 5-minute bars, %s session%s." % (
        tc.stamp(clock, zone), a.session or "each instrument's own", "" if a.session else "s"))
    print("%d instruments: %d scanned, %d not open yet, %d range still forming, %d failed or no data%s." % (
        len(insts), counts["scanned"], counts["not_open"], counts["forming"], counts["failed"],
        (", %d past their entry cutoff" % counts["expired"]) if counts["expired"] else ""))
    if hits:
        print("%d broke out of their range:" % len(hits))
        for h in hits[:a.show]:
            inst = tc.resolve(h["symbol"], cfg)
            print("  %5s %-9s %-8s %-6s %14s  range %s to %s  %.1f %s beyond  (%s)" % (
                h["time"], tc.zone_label(h["tz"]), h["symbol"], h["direction"].upper(), tc.fmt_price(h["price"], inst),
                tc.fmt_price(h["range_low"], inst), tc.fmt_price(h["range_high"], inst), h["beyond_pips"],
                h["pip_label"], h["session"]))
        if len(hits) > a.show:
            print("  ... and %d more in the watchlist (--show N for more)." % (len(hits) - a.show))
    else:
        print("Nothing has closed beyond its range yet.")
    for r in rows[:5]:
        print("  no data: %s (%s)" % (r["symbol"], r["error"][:90]))
    if not a.no_write:
        print("Wrote %s (mode range, %d hit%s)." % (a.out, len(hits), "" if len(hits) == 1 else "s"))
    print(NOTE + " Next: /trader-news SYMBOL, /trader-calendar, then /trader-entry SYMBOL.")
    return 0 if hits else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Chart Scanner (trader-scanner): forex, commodities, indices, crypto.")
    sub = ap.add_subparsers(dest="cmd")

    def common(p, data=True):
        g = p.add_mutually_exclusive_group()
        g.add_argument("--symbols", help="comma-separated symbols instead of the registry")
        g.add_argument("--watchlist", metavar="FILE", help="a watchlist.json (its hits)")
        p.add_argument("--class", dest="cls", help="forex, commodity, index, crypto (comma separated)")
        p.add_argument("--futures", action="store_true", help="include the CME futures contracts")
        p.add_argument("--limit", type=int, help="scan only the first N instruments")
        p.add_argument("--config", default="trader/config.json")
        p.add_argument("--json", action="store_true")
        p.add_argument("--no-write", action="store_true")
        if data:
            p.add_argument("--offline", metavar="PATH", help="a folder of charts or a bundle file, no network")
            p.add_argument("--now", help='pretend it is this time, e.g. "2026-11-16 09:00 London"')
            p.add_argument("--out", default="trader/watchlist.json")
            p.add_argument("--pause", type=float, default=tc.PAUSE)
            p.add_argument("--show", type=int, default=40, help="hits to print (all are written)")
            p.add_argument("--quiet", action="store_true")

    p = sub.add_parser("universe", help="the instrument registry -> trader/universe.txt")
    common(p, data=False)
    p.add_argument("--out", default="trader/universe.txt")
    p = sub.add_parser("daily", help="daily setups from closes, long and short")
    common(p)
    p = sub.add_parser("range", help="session-range breakouts so far, long and short")
    common(p)
    p.add_argument("--session", help="one session for every instrument (default: each one's own)")
    p.add_argument("--range-minutes", type=int, help="range length (default: the session's)")
    p.add_argument("--side", default="both", help="both, buy or sell")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        return {"universe": cmd_universe, "daily": cmd_daily, "range": cmd_range}[a.cmd](a)
    except tc.TraderError as e:
        print("scan.py: %s" % e, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("scan.py: stopped", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
