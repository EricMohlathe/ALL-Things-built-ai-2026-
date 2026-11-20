#!/usr/bin/env python3
"""Economic calendar for trader-calendar: the data releases and central-bank
events that move forex, gold, oil, indices and crypto, with a news blackout
around each one. Standard library only.

    python3 econ.py week                         # this week, High and Medium impact, every currency
    python3 econ.py week --write                 # also save trader/calendar.json for trader-risk
    python3 econ.py week --impact high --currencies USD,EUR
    python3 econ.py next --symbol EURUSD         # the next events that move EURUSD (EUR and USD)
    python3 econ.py blackout --symbol XAUUSD     # exit 1 inside a blackout: no new entries
    python3 econ.py week --offline tests/fixtures/calendar/ff_calendar_thisweek.json --now "2026-11-16 08:45 London"

Source: the free weekly export of the Forex Factory calendar,
  https://nfs.faireconomy.media/ff_calendar_thisweek.json  (and _nextweek.json)
a list of {"title", "country" (the currency), "date" (ISO with the New York
offset), "impact" (High / Medium / Low / Holiday), "forecast", "previous"}. It
is unofficial and asks to be polled gently: the answer is cached in
trader/state/calendar-cache.json and fetched again after an hour at most.

Which currencies an instrument moves on: a forex pair its two currencies
(EURUSD: EUR and USD); gold, oil and US indices USD; the DAX, CAC and Euro
Stoxx EUR; the FTSE GBP; the Nikkei JPY; the Hang Seng HKD and CNY; the ASX
AUD; crypto USD. Override per symbol with "currencies" in the config's
"instruments".

The blackout: no new entries "news_blackout_minutes" (30) before or after an
event whose impact is in "news_blackout_impact" (["High"]). trader-risk reads
trader/calendar.json and blocks inside it. Times print in your config's
"timezone".
"""

import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "trader-core"))
import tradercore as tc  # noqa: E402

URLS = {"this": "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
        "next": "https://nfs.faireconomy.media/ff_calendar_nextweek.json"}
CACHE = "trader/state/calendar-cache.json"
CACHE_MINUTES = 60
IMPACTS = ("High", "Medium", "Low", "Holiday")


class CalError(tc.TraderError):
    pass


def normalize(raw, source="forexfactory"):
    """The export's list -> trader/calendar.json: events with UTC times, sorted."""
    if isinstance(raw, dict) and "events" in raw:
        return raw
    if not isinstance(raw, list):
        raise CalError("the calendar is not a list of events")
    events = []
    for e in raw:
        if not isinstance(e, dict):
            continue
        t = tc.parse_utc(e.get("date"))
        if t is None:
            continue
        imp = str(e.get("impact") or "").title()
        events.append({"title": str(e.get("title") or "").strip(), "currency": str(e.get("country") or "").upper(),
                       "time_utc": tc.iso(t), "impact": imp if imp in IMPACTS else (imp or "Low"),
                       "forecast": e.get("forecast") or "", "previous": e.get("previous") or ""})
    events.sort(key=lambda x: (x["time_utc"], x["currency"], x["title"]))
    if not events:
        raise CalError("no events with a time in the calendar")
    first = tc.parse_utc(events[0]["time_utc"])
    monday = first.date() - datetime.timedelta(days=(first.weekday() + 1) % 7)
    start = datetime.datetime.combine(monday, datetime.time()) - datetime.timedelta(days=0)
    return {"created_by": "trader-calendar", "source": source, "from": tc.iso(start - datetime.timedelta(hours=12)),
            "to": tc.iso(start + datetime.timedelta(days=7, hours=12)), "events": events}


def fetch(which="this", cache=CACHE, now=None, refresh=False):
    now = now or tc.utc_now()
    doc = tc.read_json(cache, "calendar cache", required=False) or {}
    hit = doc.get(which)
    if hit and not refresh:
        age = (now - (tc.parse_utc(hit.get("fetched_at")) or tc.EPOCH)).total_seconds() / 60.0
        if 0 <= age <= CACHE_MINUTES:
            return hit["calendar"], "cache (%d min old)" % int(age)
    try:
        text = tc.http_get(URLS[which], timeout=20, headers={"Accept": "application/json"})
        raw = json.loads(text)
    except (ValueError, OSError, tc.urllib.error.URLError) as e:
        if hit:
            return hit["calendar"], "cache (the feed did not answer: %s)" % getattr(e, "reason", e)
        raise CalError("could not read the Forex Factory export (%s): try again in a few minutes"
                       % getattr(e, "reason", e))
    cal = normalize(raw)
    doc[which] = {"fetched_at": tc.iso(now), "calendar": cal}
    tc.write_json(cache, doc)
    return cal, "forexfactory export"


def load(a, now):
    if a.offline:
        return normalize(tc.read_json(a.offline, "offline calendar"), "offline:" + os.path.basename(a.offline)), "offline"
    if getattr(a, "which", "this") == "both":
        c1, s1 = fetch("this", now=now, refresh=a.refresh)
        c2, _ = fetch("next", now=now, refresh=a.refresh)
        c1 = dict(c1, events=c1["events"] + c2["events"], to=c2["to"])
        return c1, s1
    return fetch(getattr(a, "which", "this"), now=now, refresh=a.refresh)


def currencies_for(symbols, cfg):
    out = []
    for s in symbols:
        for c in tc.resolve(s, cfg).get("currencies") or []:
            if c not in out:
                out.append(c.upper())
    return out


def default_currencies(cfg):
    """Your currencies: those of the plan, the watchlist and the portfolio. None = every one."""
    syms = []
    for path, key in (("trader/plan.json", None), ("trader/watchlist.json", "hits"), ("trader/portfolio.json", "positions")):
        doc = tc.read_json(path, "", required=False)
        if not doc:
            continue
        items = [doc] if key is None else (doc.get(key) or [])
        for it in items:
            if isinstance(it, dict) and it.get("symbol"):
                syms.append(it["symbol"])
    if not syms:
        return None
    try:
        return currencies_for(syms, cfg)
    except tc.TraderError:
        return None


def pick_events(cal, currencies=None, impacts=None, start=None, end=None):
    out = []
    for e in cal["events"]:
        if currencies and e["currency"] not in currencies:
            continue
        if impacts and e["impact"].lower() not in impacts:
            continue
        t = tc.parse_utc(e["time_utc"])
        if start and t < start:
            continue
        if end and t > end:
            continue
        out.append(e)
    return out


def blackout(cal, inst, now, cfg, minutes=None):
    """(inside, events) for one instrument right now."""
    minutes = int(minutes if minutes is not None else cfg.get("news_blackout_minutes") or 30)
    impacts = {str(x).lower() for x in cfg.get("news_blackout_impact") or ["High"]}
    span = datetime.timedelta(minutes=minutes)
    evs = pick_events(cal, inst["currencies"], impacts, now - span, now + span)
    return bool(evs), evs


def line(e, zone, now=None):
    t = tc.parse_utc(e["time_utc"])
    rel = ""
    if now is not None:
        m = int(round((t - now).total_seconds() / 60.0))
        rel = "in %s" % _dur(m) if m > 0 else ("now" if m == 0 else "%s ago" % _dur(-m))
    extra = ""
    if e.get("forecast") or e.get("previous"):
        extra = "  (forecast %s, previous %s)" % (e.get("forecast") or "-", e.get("previous") or "-")
    return "  %s  %-3s %-7s %s%s%s" % (tc.to_local(zone, t).strftime("%a %d %H:%M"), e["currency"], e["impact"],
                                       e["title"], extra, ("  [%s]" % rel) if rel else "")


def _dur(m):
    if m < 60:
        return "%d min" % m
    h, mm = divmod(m, 60)
    if h < 48:
        return "%dh%02d" % (h, mm)
    return "%d days" % (h // 24)


def cmd_week(a):
    cfg = tc.load_config(a.config)
    now = tc.parse_now(a.now, cfg["timezone"])
    cal, src = load(a, now)
    curs = [c.strip().upper() for c in re.split(r"[,\s]+", a.currencies) if c.strip()] if a.currencies else \
        (currencies_for(a.symbol.split(","), cfg) if a.symbol else default_currencies(cfg))
    imps = {x.strip().lower() for x in a.impact.split(",")} if a.impact else {"high", "medium"}
    evs = pick_events(cal, curs, imps)
    if a.write:
        tc.write_json(a.write, dict(cal, fetched_from=src, written_at=tc.iso(now)))
    if a.json:
        print(json.dumps({"source": src, "events": evs, "from": cal["from"], "to": cal["to"]}, indent=2))
        return 0 if evs else 1
    zone = cfg["timezone"]
    print("Economic calendar, %s to %s (%s), %s impact, %s. Times in %s." % (
        cal["from"][:10], cal["to"][:10], src, "/".join(sorted(i.title() for i in imps)),
        ", ".join(curs) if curs else "every currency", tc.zone_label(zone)))
    if not evs:
        print("  nothing on the calendar.")
    day = None
    for e in evs:
        d = tc.to_local(zone, tc.parse_utc(e["time_utc"])).date()
        if d != day:
            print("%s" % d.strftime("%A %Y-%m-%d"))
            day = d
        print(line(e, zone, now))
    if a.write:
        print("Wrote %s (all %d events, for trader-risk's news blackout)." % (a.write, len(cal["events"])))
    print("Leads, not forecasts: a release can move the market either way, and a big surprise can jump a stop.")
    return 0 if evs else 1


def cmd_next(a):
    cfg = tc.load_config(a.config)
    now = tc.parse_now(a.now, cfg["timezone"])
    cal, src = load(a, now)
    inst = tc.resolve(a.symbol, cfg)
    imps = {x.strip().lower() for x in a.impact.split(",")} if a.impact else {"high", "medium"}
    evs = pick_events(cal, inst["currencies"], imps, now, now + datetime.timedelta(hours=a.hours))
    if a.json:
        print(json.dumps({"symbol": inst["symbol"], "currencies": inst["currencies"], "events": evs}, indent=2))
        return 0 if evs else 1
    print("%s moves on %s. Next %d hours from %s (%s):" % (inst["symbol"], " and ".join(inst["currencies"]), a.hours,
                                                         tc.stamp(now, cfg["timezone"]), src))
    for e in evs:
        print(line(e, cfg["timezone"], now))
    if not evs:
        print("  nothing %s on the calendar." % "/".join(sorted(i.title() for i in imps)))
    return 0 if evs else 1


def cmd_blackout(a):
    cfg = tc.load_config(a.config)
    now = tc.parse_now(a.now, cfg["timezone"])
    cal, src = load(a, now)
    inst = tc.resolve(a.symbol, cfg)
    inside, evs = blackout(cal, inst, now, cfg, a.minutes)
    mins = int(a.minutes if a.minutes is not None else cfg.get("news_blackout_minutes") or 30)
    if a.json:
        print(json.dumps({"symbol": inst["symbol"], "inside": inside, "minutes": mins, "events": evs}, indent=2))
        return 1 if inside else 0
    if inside:
        print("BLACKOUT for %s at %s: no new entries within %d minutes of:" % (inst["symbol"],
                                                                             tc.stamp(now, cfg["timezone"]), mins))
        for e in evs:
            print(line(e, cfg["timezone"], now))
        return 1
    print("Clear: no %s event for %s within %d minutes of %s (%s)." % (
        "/".join(cfg.get("news_blackout_impact") or ["High"]), " / ".join(inst["currencies"]), mins,
        tc.stamp(now, cfg["timezone"]), src))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Economic calendar and news blackout (trader-calendar).")
    sub = ap.add_subparsers(dest="cmd")

    def common(p):
        p.add_argument("--config", default="trader/config.json")
        p.add_argument("--offline", metavar="FILE", help="a saved export (list) or trader/calendar.json")
        p.add_argument("--which", choices=["this", "next", "both"], default="this", help="this week, next week or both")
        p.add_argument("--refresh", action="store_true", help="ignore the one-hour cache")
        p.add_argument("--now", help='pretend it is this time, e.g. "2026-11-16 08:45 London"')
        p.add_argument("--impact", help="high, medium, low, holiday (comma separated)")
        p.add_argument("--json", action="store_true")
    p = sub.add_parser("week", help="the week's events")
    common(p)
    p.add_argument("--currencies", help="USD,EUR ... (default: your plan, watchlist and portfolio, else all)")
    p.add_argument("--symbol", help="the currencies one or more instruments move on")
    p.add_argument("--write", nargs="?", const="trader/calendar.json", metavar="PATH")
    p = sub.add_parser("next", help="the next events for one instrument")
    common(p)
    p.add_argument("--symbol", required=True)
    p.add_argument("--hours", type=int, default=48)
    p = sub.add_parser("blackout", help="exit 1 inside a news blackout for one instrument")
    common(p)
    p.add_argument("--symbol", required=True)
    p.add_argument("--minutes", type=int)
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        return {"week": cmd_week, "next": cmd_next, "blackout": cmd_blackout}[a.cmd](a)
    except tc.TraderError as e:
        print("econ.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
