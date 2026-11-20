#!/usr/bin/env python3
"""Price alerts and the world market clock for trader-alerts: forex, commodities,
indices and crypto. Standard library only.

    python3 alerts.py clock                          # which sessions are open, the overlaps, what opens next
    python3 alerts.py quote EURUSD XAUUSD --write    # quotes -> trader/prices.json
    python3 alerts.py quote --holdings --rates --write   # your plan and portfolio, plus the FX rates to convert them
    python3 alerts.py add --from-plan                # stop, target and flat-by from trader/plan.json, long or short
    python3 alerts.py add --symbol EURUSD --above 1.1650
    python3 alerts.py add --symbol XAUUSD --below 4040 --rearm
    python3 alerts.py add --symbol BTCUSD --pct 3
    python3 alerts.py add --session-open london      # rings when the London session opens
    python3 alerts.py add --at 16:55 --tz London --label "flat by"
    python3 alerts.py add --event --currencies USD,EUR --minutes 15   # 15 minutes before High-impact news
    python3 alerts.py check                          # rings what hit, once; exit 1 if nothing rang
    python3 alerts.py check --now "2026-11-16 09:50 London" --offline tests/fixtures/charts
    python3 alerts.py list
    python3 alerts.py reset eurusd-plan-stop

Rule types:
  above / below   the price is at or above / at or below "price". From a plan,
                  a long's stop is a "below" and its target an "above"; a
                  short's are the other way round
  pct_move        the price moved "pct" percent from the previous close (or
                  "ref"); "direction": "up" or "down" to watch one side
  session_open    the named session opened (rings once per session day)
  time            the clock passed "at" (HH:MM) in "tz" (once a day; a rule
                  with "date" only on that date)
  event           a calendar event (trader/calendar.json) for "currencies" of
                  "impact" (High) is "minutes" (15) away or less; once per event

An above / below alert rings ONCE and stays quiet until you reset it, unless it
has "rearm": true (it re-arms when the price crosses back). A pct_move alert
rings at most once a day.

Quotes come from Yahoo's chart endpoint (free, delayed, unofficial; for alerts
and sizing checks, never for timing an order). --offline DIR reads saved charts
instead and quotes the last bar closed by --now.
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

RULES = "trader/alerts.json"
STATE = "trader/state/alerts.json"
PRICES = "trader/prices.json"
TYPES = ("above", "below", "pct_move", "session_open", "time", "event")


class AlertError(tc.TraderError):
    pass


# ---------------------------------------------------------------- the clock

def clock_lines(now, cfg):
    zone = cfg["timezone"]
    out = ["World market clock at %s (%s)." % (tc.stamp(now, zone), tc.iso(now))]
    ny = tc.to_local("America/New_York", now)
    wd, mins = ny.weekday(), ny.hour * 60 + ny.minute
    fx_open = not (wd == 5 or (wd == 6 and mins < 17 * 60) or (wd == 4 and mins >= 17 * 60))
    out.append("Forex: %s (the FX week runs Sunday 17:00 to Friday 17:00 New York)." % (
        "OPEN" if fx_open else "CLOSED for the weekend"))
    out.append("Crypto: OPEN (24/7).")
    rows = []
    for name in tc.FX_SESSIONS + ("us_cash", "comex", "nymex", "cbot", "xetra", "lse", "euronext", "tse", "hkex", "asx"):
        inst, phase = tc.locate(name, now, cfg)
        if inst and phase == "open":
            rows.append(("OPEN", name, "closes %s (%s)" % (tc.stamp(inst["close_utc"], inst["tz"]),
                                                           _until(inst["close_utc"] - now))))
        else:
            nxt = tc.next_open(name, now, cfg)
            rows.append(("closed", name, "opens %s (%s)" % (tc.stamp(nxt["open_utc"], nxt["tz"]),
                                                            _until(nxt["open_utc"] - now)) if nxt else "unknown"))
    for st, name, what in rows:
        out.append("  %-6s %-12s %s" % (st, name, what))
    opened = [n for st, n, _ in rows if st == "OPEN" and n in tc.FX_SESSIONS]
    if len(opened) >= 2:
        out.append("Overlap: %s (the busiest forex hours)." % " + ".join(opened))
    return out


def _until(delta):
    m = int(delta.total_seconds() // 60)
    if m < 60:
        return "in %d min" % m
    h, mm = divmod(m, 60)
    return "in %dh%02d" % (h, mm) if h < 48 else "in %d days" % (h // 24)


# ---------------------------------------------------------------- quotes

def quote(inst, now=None, offline=None):
    """{price, time (naive UTC), prev_close, feed}."""
    if offline:
        ch = tc.get_chart(inst, "5m", offline=offline)
        bars = [b for b in ch["bars"] if b["t"] % 300 == 0 and (now is None or tc.utc_of(b["t"] + 300) <= now)]
        if not bars:
            raise AlertError("no bar for %s closed by %s in the offline chart" % (inst["symbol"], now))
        b = bars[-1]
        day0 = tc.to_local(tc.session_def(inst["session"])["tz"], tc.utc_of(b["t"])).date()
        prev = [x for x in bars if tc.to_local(tc.session_def(inst["session"])["tz"], tc.utc_of(x["t"])).date() < day0]
        return {"price": b["c"], "time": tc.utc_of(b["t"] + 300), "prev_close": prev[-1]["c"] if prev else None,
                "feed": inst["feed"]}
    ch = tc.get_chart(inst, "5m", "1d")
    m = ch["meta"]
    price = m.get("regularMarketPrice") or (ch["bars"][-1]["c"] if ch["bars"] else None)
    if price is None:
        raise AlertError("Yahoo sent no price for %s" % inst["symbol"])
    t = m.get("regularMarketTime")
    return {"price": float(price), "time": tc.utc_of(t) if t else tc.utc_now(), "prev_close": ch.get("prev_close"),
            "feed": inst["feed"]}


def conversion_pairs(insts, acct, reg):
    """The FX pairs needed to turn each instrument's quote currency into the account's."""
    out = []
    for i in insts:
        q = i["quote"].upper()
        if q == acct or (i["class"] == "forex" and i["base"].upper() == acct):
            continue
        for cand in (q + acct, acct + q, q + "USD", "USD" + q, "USD" + acct, acct + "USD"):
            if cand in reg and cand not in out and cand[:3] != cand[3:]:
                out.append(cand)
                if acct in cand:
                    break
    return out


# ---------------------------------------------------------------- rules

def load_rules(path):
    doc = tc.read_json(path, "alerts", required=False) or {"rules": []}
    rules = doc.get("rules", [])
    for r in rules:
        if r.get("type") not in TYPES:
            raise AlertError("alert %s has an unknown type %r" % (r.get("id"), r.get("type")))
    return doc


def save_rules(path, doc):
    tc.write_json(path, doc)


def add_rule(doc, rule):
    rules = [r for r in doc.setdefault("rules", []) if r.get("id") != rule["id"]]
    replaced = len(rules) != len(doc["rules"])
    rules.append(rule)
    doc["rules"] = rules
    return replaced


def rules_from_plan(plan, cfg):
    inst = tc.resolve(plan["symbol"], cfg)
    long = tc.side_word(plan.get("side") or "buy") == "buy"
    s = inst["symbol"].lower()
    d = plan.get("date")
    p = lambda x: float(tc.fmt_price(x, inst))  # noqa: E731
    return [
        {"id": "%s-plan-stop" % s, "symbol": inst["symbol"], "type": "below" if long else "above",
         "price": p(plan["stop"]), "note": "plan stop (%s)" % ("long" if long else "short"), "date": d},
        {"id": "%s-plan-target" % s, "symbol": inst["symbol"], "type": "above" if long else "below",
         "price": p(plan["target"]), "note": "plan target (%s)" % ("long" if long else "short"), "date": d},
        {"id": "%s-flat-by" % s, "symbol": inst["symbol"], "type": "time", "at": plan.get("flat_by") or "16:55",
         "tz": plan.get("tz") or tc.session_def(inst["session"], cfg)["tz"], "label": "flat by: close %s %s" % (
             inst["symbol"], "long" if long else "short"), "date": d},
    ]


def evaluate(rules, state, now, quotes, calendar, cfg):
    """Pure: (rang [(rule, message)], new state). quotes = {SYMBOL: quote dict}."""
    fired = dict(state.get("fired") or {})
    armed = dict(state.get("armed") or {})
    rang = []
    for r in rules:
        rid, typ = r["id"], r["type"]
        zone = r.get("tz") or (tc.session_def(tc.resolve(r["symbol"], cfg)["session"], cfg)["tz"]
                               if r.get("symbol") else cfg["timezone"])
        today = tc.to_local(zone, now).date().isoformat()
        if r.get("date") and r["date"] != today:
            continue
        if typ in ("above", "below"):
            q = quotes.get(r["symbol"])
            if not q:
                continue
            hit = q["price"] >= r["price"] if typ == "above" else q["price"] <= r["price"]
            if hit and armed.get(rid, True):
                inst = tc.resolve(r["symbol"], cfg)
                rang.append((r, "%s %s %s: last %s (quote %s)%s" % (
                    r["symbol"], "at or above" if typ == "above" else "at or below", tc.fmt_price(r["price"], inst),
                    tc.fmt_price(q["price"], inst), tc.stamp(q["time"], zone),
                    (" [%s]" % r["note"]) if r.get("note") else "")))
                armed[rid] = False
                fired[rid] = tc.iso(now)
            elif not hit and r.get("rearm"):
                armed[rid] = True
        elif typ == "pct_move":
            q = quotes.get(r["symbol"])
            ref = r.get("ref") or (q or {}).get("prev_close")
            if not q or not ref:
                continue
            move = 100.0 * (q["price"] / float(ref) - 1)
            want = r.get("direction")
            hit = abs(move) >= float(r["pct"]) and (not want or (want == "up") == (move > 0))
            if hit and fired.get(rid, "")[:10] != today:
                inst = tc.resolve(r["symbol"], cfg)
                rang.append((r, "%s moved %+.2f%% (%s from %s), over your %s%%" % (
                    r["symbol"], move, tc.fmt_price(q["price"], inst), tc.fmt_price(ref, inst), r["pct"])))
                fired[rid] = today + "T"
        elif typ == "session_open":
            inst_s, phase = tc.locate(r["session"], now, cfg)
            if inst_s and phase == "open" and fired.get(rid, "")[:10] != inst_s["date"]:
                rang.append((r, "%s is open (since %s)" % (inst_s["label"], tc.stamp(inst_s["open_utc"], inst_s["tz"]))))
                fired[rid] = inst_s["date"] + "T"
        elif typ == "time":
            loc = tc.to_local(zone, now)
            at = tc.parse_hhmm(r["at"], "alert %s at" % rid)
            weekday_ok = r.get("date") or loc.weekday() < 5 or r.get("every_day")
            if weekday_ok and loc.hour * 60 + loc.minute >= at and fired.get(rid, "")[:10] != today:
                rang.append((r, "%s %s: %s" % (r["at"], tc.zone_label(zone), r.get("label") or "time")))
                fired[rid] = today + "T"
        elif typ == "event":
            if not calendar:
                continue
            curs = {c.upper() for c in r.get("currencies") or []}
            imps = {str(x).lower() for x in r.get("impact") or ["High"]}
            lead = int(r.get("minutes") or 15)
            for ev in calendar.get("events") or []:
                t = tc.parse_utc(ev.get("time_utc"))
                if t is None or (curs and ev.get("currency", "").upper() not in curs):
                    continue
                if str(ev.get("impact", "")).lower() not in imps:
                    continue
                m = (t - now).total_seconds() / 60.0
                key = "%s|%s|%s" % (rid, ev.get("time_utc"), ev.get("title"))
                if 0 <= m <= lead and key not in fired:
                    rang.append((r, "%s %s (%s) at %s: in %d minutes" % (
                        ev.get("currency"), ev.get("title"), ev.get("impact"), tc.stamp(t, cfg["timezone"]),
                        int(round(m)))))
                    fired[key] = tc.iso(now)
    return rang, {"fired": fired, "armed": armed}


# ---------------------------------------------------------------- commands

def cmd_clock(a):
    cfg = tc.load_config(a.config)
    now = tc.parse_now(a.now, cfg["timezone"])
    print("\n".join(clock_lines(now, cfg)))
    return 0


def _holdings(cfg):
    syms = []
    plan = tc.read_json("trader/plan.json", "", required=False)
    if plan and plan.get("symbol"):
        syms.append(plan["symbol"])
    pf = tc.read_json("trader/portfolio.json", "", required=False)
    for p in tc.portfolio_positions(pf):
        syms.append(p["symbol"])
    return syms


def cmd_quote(a):
    cfg = tc.load_config(a.config)
    now = tc.parse_now(a.now, cfg["timezone"]) if a.now else None
    reg = tc.registry(cfg)
    syms = list(a.symbols or [])
    if a.holdings:
        syms += _holdings(cfg)
    if not syms:
        raise AlertError("which symbols? alerts.py quote EURUSD XAUUSD, or --holdings")
    insts = []
    for s in syms:
        i = tc.resolve(s, cfg, reg)
        if i["symbol"] not in [x["symbol"] for x in insts]:
            insts.append(i)
    if a.rates:
        for pair in conversion_pairs(insts, cfg["account_currency"], reg):
            if pair not in [x["symbol"] for x in insts]:
                insts.append(tc.resolve(pair, cfg, reg))
    doc = tc.read_json(a.out, "prices", required=False) if a.write else None
    doc = doc or {"prices": {}, "detail": {}}
    fetched = tc.iso(now or tc.utc_now())
    rows, failed = [], []
    for n, inst in enumerate(insts):
        try:
            if n and not a.offline:
                tc.SLEEP(tc.PAUSE)
            q = quote(inst, now, a.offline)
        except tc.TraderError as e:
            failed.append("%s: %s" % (inst["symbol"], e))
            continue
        doc["prices"][inst["symbol"]] = q["price"]
        doc.setdefault("detail", {})[inst["symbol"]] = {"time": tc.iso(q["time"]), "fetched": fetched,
                                                        "feed": q["feed"], "prev_close": q["prev_close"]}
        rows.append((inst, q))
    doc["as_of"] = fetched
    doc["source"] = "offline" if a.offline else "yahoo"
    if a.write:
        tc.write_json(a.out, doc)
    for inst, q in rows:
        ch = ("  %+.2f%% on the day" % (100.0 * (q["price"] / q["prev_close"] - 1))) if q["prev_close"] else ""
        print("%-8s %14s  at %s%s" % (inst["symbol"], tc.fmt_price(q["price"], inst), tc.stamp(q["time"], cfg["timezone"]),
                                      ch))
    for f in failed:
        print("failed: " + f)
    if a.write:
        print("Wrote %s (%d prices). Free and delayed: for alerts and sizing checks, not for timing an order." % (
            a.out, len(doc["prices"])))
    return 0 if rows else 1


def cmd_add(a):
    cfg = tc.load_config(a.config)
    doc = load_rules(a.rules)
    new = []
    if a.from_plan:
        plan = tc.read_json(a.plan, "plan (run trader-exit first)")
        new = rules_from_plan(plan, cfg)
    elif a.session_open:
        tc.session_def(a.session_open, cfg)
        new = [{"id": a.id or "%s-open" % a.session_open, "type": "session_open", "session": a.session_open}]
    elif a.event:
        curs = [c.strip().upper() for c in re.split(r"[,\s]+", a.currencies or "") if c.strip()]
        new = [{"id": a.id or "news-%s" % ("-".join(curs).lower() or "all"), "type": "event", "currencies": curs,
                "impact": [x.strip().title() for x in (a.impact or "High").split(",")], "minutes": a.minutes}]
    elif a.at:
        tc.parse_hhmm(a.at, "--at")
        new = [{"id": a.id or "time-%s" % a.at.replace(":", ""), "type": "time", "at": a.at,
                "tz": tc.zone_name(a.tz or cfg["timezone"]), "label": a.label or "time"}]
        if a.date:
            new[0]["date"] = a.date
    elif a.symbol:
        inst = tc.resolve(a.symbol, cfg)
        s = inst["symbol"]
        if a.above is not None:
            new.append({"id": a.id or "%s-above-%s" % (s.lower(), tc.num(a.above)), "symbol": s, "type": "above",
                        "price": a.above})
        if a.below is not None:
            new.append({"id": a.id or "%s-below-%s" % (s.lower(), tc.num(a.below)), "symbol": s, "type": "below",
                        "price": a.below})
        if a.pct is not None:
            r = {"id": a.id or "%s-move-%s" % (s.lower(), tc.num(a.pct)), "symbol": s, "type": "pct_move", "pct": a.pct}
            if a.direction:
                r["direction"] = a.direction
            new.append(r)
        if not new:
            raise AlertError("with --symbol give --above, --below or --pct")
        for r in new:
            if a.rearm:
                r["rearm"] = True
            if a.date:
                r["date"] = a.date
            if a.note:
                r["note"] = a.note
    else:
        raise AlertError("add what? --from-plan, --symbol ... --above/--below/--pct, --session-open, --at or --event")
    for r in new:
        verb = "Replaced" if add_rule(doc, r) else "Added"
        print("%s %s: %s" % (verb, r["id"], describe(r)))
    save_rules(a.rules, doc)
    print("%d alert%s in %s. Run alerts.py check on a /loop (every 1 to 5 minutes) to hear them." % (
        len(doc["rules"]), "" if len(doc["rules"]) == 1 else "s", a.rules))
    return 0


def describe(r):
    t = r["type"]
    if t in ("above", "below"):
        return "%s %s %s%s%s" % (r["symbol"], t, r["price"], " (re-arms)" if r.get("rearm") else "",
                                 (" on %s" % r["date"]) if r.get("date") else "")
    if t == "pct_move":
        return "%s moves %s%% %s" % (r["symbol"], r["pct"], r.get("direction", "either way"))
    if t == "session_open":
        return "the %s opens" % r["session"]
    if t == "time":
        return "%s %s: %s%s" % (r["at"], tc.zone_label(r.get("tz") or "UTC"), r.get("label", ""),
                                (" on %s" % r["date"]) if r.get("date") else "")
    return "%s minutes before %s news for %s" % (r.get("minutes"), "/".join(r.get("impact") or ["High"]),
                                                 ", ".join(r.get("currencies") or ["every currency"]))


def cmd_check(a):
    cfg = tc.load_config(a.config)
    now = tc.parse_now(a.now, cfg["timezone"])
    doc = load_rules(a.rules)
    rules = doc.get("rules", [])
    if not rules:
        print("No alerts set. Add some: alerts.py add --from-plan")
        return 1
    state = tc.read_json(a.state, "alert state", required=False) or {}
    syms = sorted({r["symbol"] for r in rules if r.get("symbol") and r["type"] in ("above", "below", "pct_move")})
    quotes, errors = {}, []
    for n, s in enumerate(syms):
        try:
            if n and not a.offline:
                tc.SLEEP(tc.PAUSE)
            quotes[s] = quote(tc.resolve(s, cfg), now if (a.offline or a.now) else None, a.offline)
        except tc.TraderError as e:
            errors.append("%s: %s" % (s, e))
    calendar = tc.read_json(a.calendar, "calendar", required=False)
    rang, new_state = evaluate(rules, state, now, quotes, calendar, cfg)
    if not a.dry_run:
        tc.write_json(a.state, new_state)
    for r, msg in rang:
        print("RING  %s  %s" % (r["id"], msg))
    for e in errors:
        print("quote failed: %s" % e)
    if not rang:
        print("Nothing rang at %s (%d alert%s watched)." % (tc.stamp(now, cfg["timezone"]), len(rules),
                                                           "" if len(rules) == 1 else "s"))
    return 0 if rang else 1


def cmd_list(a):
    doc = load_rules(a.rules)
    state = tc.read_json(a.state, "alert state", required=False) or {}
    if not doc.get("rules"):
        print("No alerts set.")
        return 1
    for r in doc["rules"]:
        f = (state.get("fired") or {}).get(r["id"])
        print("%-26s %s%s" % (r["id"], describe(r), ("   rang %s" % f) if f else ""))
    return 0


def cmd_reset(a):
    state = tc.read_json(a.state, "alert state", required=False) or {}
    hit = False
    for k in ("fired", "armed"):
        for key in list((state.get(k) or {}).keys()):
            if key == a.id or key.startswith(a.id + "|"):
                del state[k][key]
                hit = True
    tc.write_json(a.state, state)
    print("Re-armed %s." % a.id if hit else "%s had not rung; nothing to reset." % a.id)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Price alerts and the world market clock (trader-alerts).")
    sub = ap.add_subparsers(dest="cmd")

    def base(p):
        p.add_argument("--config", default="trader/config.json")
        p.add_argument("--rules", default=RULES)
        p.add_argument("--state", default=STATE)
    p = sub.add_parser("clock")
    base(p)
    p.add_argument("--now")
    p = sub.add_parser("quote")
    base(p)
    p.add_argument("symbols", nargs="*")
    p.add_argument("--holdings", action="store_true", help="the plan's symbol and your positions")
    p.add_argument("--rates", action="store_true", help="also the FX pairs that convert them to your account currency")
    p.add_argument("--write", action="store_true")
    p.add_argument("--out", default=PRICES)
    p.add_argument("--offline", metavar="DIR")
    p.add_argument("--now")
    p = sub.add_parser("add")
    base(p)
    p.add_argument("--from-plan", action="store_true")
    p.add_argument("--plan", default="trader/plan.json")
    p.add_argument("--symbol")
    p.add_argument("--above", type=float)
    p.add_argument("--below", type=float)
    p.add_argument("--pct", type=float)
    p.add_argument("--direction", choices=["up", "down"])
    p.add_argument("--rearm", action="store_true")
    p.add_argument("--session-open", help="a session name: london, ny, tokyo, us_cash ...")
    p.add_argument("--at", help="HH:MM")
    p.add_argument("--tz", help="the zone of --at (default: the config's)")
    p.add_argument("--label")
    p.add_argument("--event", action="store_true")
    p.add_argument("--currencies")
    p.add_argument("--impact", help="High (default), Medium ...")
    p.add_argument("--minutes", type=int, default=15)
    p.add_argument("--date", help="only on this date, YYYY-MM-DD")
    p.add_argument("--note")
    p.add_argument("--id")
    p = sub.add_parser("check")
    base(p)
    p.add_argument("--now")
    p.add_argument("--offline", metavar="DIR")
    p.add_argument("--calendar", default="trader/calendar.json")
    p.add_argument("--dry-run", action="store_true", help="ring but do not remember it")
    p = sub.add_parser("list")
    base(p)
    p = sub.add_parser("reset")
    base(p)
    p.add_argument("id")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        return {"clock": cmd_clock, "quote": cmd_quote, "add": cmd_add, "check": cmd_check, "list": cmd_list,
                "reset": cmd_reset}[a.cmd](a)
    except tc.TraderError as e:
        print("alerts.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
