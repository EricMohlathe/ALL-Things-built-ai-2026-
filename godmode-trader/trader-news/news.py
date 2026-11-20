#!/usr/bin/env python3
"""News monitor for trader-news: headlines, the economic calendar and the day's
move for the forex pairs, commodities, indices and coins you watch. Standard
library only.

Prints only what is new since the last check, newest first, each headline
tagged with what moves these markets (central banks, inflation, jobs, growth,
energy, geopolitics, crypto flows and hacks ...), plus the calendar events
for each instrument's currencies and how far it has moved today.

    python3 news.py                                  # watchlist + plan + portfolio symbols
    python3 news.py --symbols EURUSD XAUUSD BTCUSD
    python3 news.py --symbols USDJPY --all --hours 72
    python3 news.py --no-calendar --no-moves

Your symbols, when --symbols is not given: the hits in trader/watchlist.json
(trader-scanner), the symbol in trader/plan.json (trader-exit) and the positions
in trader/portfolio.json.

Sources, one request each per symbol:
  - Yahoo Finance headline RSS for the instrument's feed:
    https://feeds.finance.yahoo.com/rss/2.0/headline?s=<FEED>&region=US&lang=en-US
  - trader/calendar.json (trader-calendar) for the currencies it moves on
  - the move: Yahoo's chart endpoint, the last price against the previous close

Times print in the config's "timezone". State: trader/state/news.json remembers
what you have seen (30 days), so an item shows once. --offline DIR reads
yahoo-<SYMBOL>.xml from DIR (and --charts DIR for the moves).

Headlines are leads, not facts: open the story before acting, and treat
nothing here as advice.
"""

import argparse
import datetime
import email.utils
import hashlib
import json
import os
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "trader-core"))
import tradercore as tc  # noqa: E402

YAHOO = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%s&region=US&lang=en-US"
STATE = "trader/state/news.json"
KEEP_DAYS = 30
TAGS = [
    ("central bank", r"\b(fed|fomc|powell|ecb|lagarde|boe|bailey|boj|ueda|rba|rbnz|snb|boc|central bank|rate (hike|cut|"
                     r"decision|path)|hawkish|dovish|minutes|policy meeting|interest rates?)\b"),
    ("inflation", r"\b(cpi|ppi|pce|inflation|prices rose|core prices)\b"),
    ("jobs", r"\b(payrolls?|nfp|jobs report|unemployment|jobless|claims|labou?r market|wages)\b"),
    ("growth", r"\b(gdp|pmi|retail sales|recession|growth|industrial production|ism)\b"),
    ("yields", r"\b(yields?|treasur(y|ies)|bunds?|gilts?|jgbs?|bonds?)\b"),
    ("intervention", r"\b(intervention|intervene|jawbon\w*|verbal warning)\b"),
    ("energy", r"\b(opec\+?|crude|oil|brent|wti|inventor(y|ies)|eia|api stocks|natural gas|lng)\b"),
    ("metals", r"\b(gold|silver|bullion|platinum|copper|wgc|etf (in|out)flows?)\b"),
    ("geopolitics", r"\b(war|sanctions?|tariffs?|election|strike|conflict|ceasefire|missile|attack)\b"),
    ("crypto flows", r"\b(etf flows?|inflows?|outflows?|spot etf|blackrock|grayscale|stablecoin|halving)\b"),
    ("crypto risk", r"\b(hack(ed)?|exploit|drain(ed|s)?|depeg|liquidat\w+|insolven\w+|bankrupt\w*)\b"),
    ("regulation", r"\b(sec|cftc|regulat\w+|lawsuit|ban(ned)?|approv\w+|delay(s|ed)? decision)\b"),
    ("risk mood", r"\b(risk[- ](on|off)|safe[- ]haven|sell-?off|rally|slump|surge|plunge)\b"),
]


class NewsError(tc.TraderError):
    pass


def tags_for(title):
    t = title.lower()
    return [name for name, rx in TAGS if re.search(rx, t)]


def parse_rss(text):
    """RSS -> [{id, title, link, time (naive UTC)}]."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise NewsError("the headline feed is not valid XML: %s" % e)
    out = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        if not title:
            continue
        link = (it.findtext("link") or "").strip()
        guid = (it.findtext("guid") or link or title).strip()
        when = None
        pub = it.findtext("pubDate")
        if pub:
            try:
                dt = email.utils.parsedate_to_datetime(pub)
                when = (dt - dt.utcoffset()).replace(tzinfo=None) if dt.tzinfo else dt
            except (TypeError, ValueError):
                when = None
        out.append({"id": hashlib.sha1(guid.encode("utf-8")).hexdigest()[:16], "title": title, "link": link,
                    "time": when})
    return out


def headlines(inst, offline=None):
    if offline:
        p = os.path.join(offline, "yahoo-%s.xml" % inst["symbol"])
        if not os.path.exists(p):
            return []
        return parse_rss(tc.read_text(p))
    try:
        text = tc.http_get(YAHOO % urllib.parse.quote(inst["feed"], safe="=-"), headers={"Accept": "application/rss+xml"})
    except (OSError, tc.urllib.error.URLError) as e:
        raise NewsError("Yahoo headlines for %s did not answer: %s" % (inst["symbol"], getattr(e, "reason", e)))
    return parse_rss(text)


def move(inst, now, charts=None):
    """(last, prev_close, pct) or None."""
    try:
        if charts:
            ch = tc.get_chart(inst, "5m", offline=charts)
            bars = [b for b in ch["bars"] if b["t"] % 300 == 0 and tc.utc_of(b["t"] + 300) <= now]
            if not bars:
                return None
            tz = tc.session_def(inst["session"])["tz"]
            day = tc.to_local(tz, tc.utc_of(bars[-1]["t"])).date()
            prev = [b for b in bars if tc.to_local(tz, tc.utc_of(b["t"])).date() < day]
            if not prev:
                return None
            last, pc = bars[-1]["c"], prev[-1]["c"]
        else:
            ch = tc.get_chart(inst, "5m", "1d")
            last = ch["meta"].get("regularMarketPrice") or (ch["bars"][-1]["c"] if ch["bars"] else None)
            pc = ch.get("prev_close")
        if not last or not pc:
            return None
        return last, pc, 100.0 * (last / pc - 1)
    except tc.TraderError:
        return None


def my_symbols(cfg):
    syms = []
    wl = tc.read_json("trader/watchlist.json", "", required=False) or {}
    syms += [h.get("symbol") for h in wl.get("hits", []) if isinstance(h, dict)]
    plan = tc.read_json("trader/plan.json", "", required=False) or {}
    if plan.get("symbol"):
        syms.append(plan["symbol"])
    pf = tc.read_json("trader/portfolio.json", "", required=False)
    syms += [p["symbol"] for p in tc.portfolio_positions(pf)]
    return [s for s in syms if s]


def run(a):
    cfg = tc.load_config(a.config)
    zone = cfg["timezone"]
    now = tc.parse_now(a.now, zone)
    syms = a.symbols or my_symbols(cfg)
    if not syms:
        raise NewsError("which symbols? --symbols EURUSD XAUUSD, or run /trader-scanner or /trader-exit first")
    insts = []
    for s in syms:
        i = tc.resolve(s, cfg)
        if i["symbol"] not in [x["symbol"] for x in insts]:
            insts.append(i)
    state = tc.read_json(a.state, "news state", required=False) or {"seen": {}}
    seen = state.setdefault("seen", {})
    cutoff = now - datetime.timedelta(hours=a.hours)
    calendar = None if a.no_calendar else tc.read_json(a.calendar, "calendar", required=False)
    out = {"now": tc.iso(now), "symbols": []}
    lines = ["News at %s for %s (Yahoo headlines%s%s). Times in %s." % (
        tc.stamp(now, zone), ", ".join(i["symbol"] for i in insts), ", the calendar" if calendar else "",
        ", today's move" if not a.no_moves else "", tc.zone_label(zone))]
    if not a.no_calendar and not calendar:
        lines.append("No trader/calendar.json: run /trader-calendar (econ.py week --write) for the events.")
    total_new = 0
    for n, inst in enumerate(insts):
        if n and not a.offline:
            tc.SLEEP(tc.PAUSE)
        block = {"symbol": inst["symbol"], "items": [], "events": [], "move": None}
        try:
            items = headlines(inst, a.offline)
        except NewsError as e:
            items = []
            lines.append("%s: %s" % (inst["symbol"], e))
        fresh = []
        for it in sorted(items, key=lambda x: x["time"] or tc.EPOCH, reverse=True):
            if it["time"] and it["time"] < cutoff:
                continue
            if it["time"] and it["time"] > now + datetime.timedelta(minutes=5):
                continue
            if not a.all and it["id"] in seen:
                continue
            fresh.append(dict(it, tags=tags_for(it["title"])))
        if calendar:
            curs = set(inst["currencies"])
            for ev in calendar.get("events") or []:
                t = tc.parse_utc(ev.get("time_utc"))
                if t and ev.get("currency") in curs and str(ev.get("impact")) in ("High", "Medium") and \
                        now - datetime.timedelta(hours=6) <= t <= now + datetime.timedelta(hours=a.ahead):
                    block["events"].append(ev)
        mv = None if a.no_moves else move(inst, now, a.charts)
        head = "%s (%s)" % (inst["symbol"], inst["name"])
        if mv:
            block["move"] = {"last": mv[0], "prev_close": mv[1], "pct": round(mv[2], 3)}
            pipmove = tc.fmt_dist(mv[0] - mv[1], inst)
            head += "  %s, %+.2f%% (%s %s) on the day" % (tc.fmt_price(mv[0], inst), mv[2],
                                                         "up" if mv[0] >= mv[1] else "down", pipmove)
        lines.append("")
        lines.append(head)
        for ev in block["events"]:
            t = tc.parse_utc(ev["time_utc"])
            lines.append("  CALENDAR %s  %s %-6s %s%s" % (tc.to_local(zone, t).strftime("%a %H:%M"), ev["currency"],
                                                         ev["impact"], ev["title"],
                                                         "  (already out)" if t <= now else ""))
        for it in fresh:
            when = tc.to_local(zone, it["time"]).strftime("%a %H:%M") if it["time"] else "     ?"
            lines.append("  %s  %s%s" % (when, it["title"], ("  [%s]" % ", ".join(it["tags"])) if it["tags"] else ""))
            block["items"].append({"title": it["title"], "link": it["link"], "time": tc.iso(it["time"])
                                   if it["time"] else None, "tags": it["tags"]})
        if not fresh:
            lines.append("  no new headlines%s." % ("" if a.all else " since your last check"))
        total_new += len(fresh)
        if not a.no_write:
            for it in fresh:
                seen[it["id"]] = tc.iso(now)
        out["symbols"].append(block)
    if not a.no_write:
        keep = now - datetime.timedelta(days=KEEP_DAYS)
        state["seen"] = {k: v for k, v in seen.items() if (tc.parse_utc(v) or now) >= keep}
        tc.write_json(a.state, state)
    lines.append("")
    lines.append("Headlines are leads, not facts: open the story before acting. A data release or a central banker can "
                 "move %s more in a minute than in the hour before." % ("these markets" if len(insts) > 1 else insts[0]["symbol"]))
    if a.json:
        print(json.dumps(out, indent=2))
    else:
        print("\n".join(lines))
    return 0 if total_new or any(b["events"] for b in out["symbols"]) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="News monitor (trader-news): headlines, calendar and moves.")
    ap.add_argument("--symbols", nargs="+")
    ap.add_argument("--hours", type=int, default=24, help="headlines this recent (default 24)")
    ap.add_argument("--ahead", type=int, default=24, help="calendar events this far ahead (hours, default 24)")
    ap.add_argument("--all", action="store_true", help="show headlines you have seen before too")
    ap.add_argument("--no-calendar", action="store_true")
    ap.add_argument("--no-moves", action="store_true")
    ap.add_argument("--calendar", default="trader/calendar.json")
    ap.add_argument("--config", default="trader/config.json")
    ap.add_argument("--state", default=STATE)
    ap.add_argument("--offline", metavar="DIR", help="yahoo-<SYMBOL>.xml files")
    ap.add_argument("--charts", metavar="DIR", help="saved charts for the moves (offline)")
    ap.add_argument("--now")
    ap.add_argument("--no-write", action="store_true", help="do not remember what was shown")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        return run(a)
    except tc.TraderError as e:
        print("news.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
