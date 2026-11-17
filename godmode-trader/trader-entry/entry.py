#!/usr/bin/env python3
"""Entry Timer for trader-entry: watches a setup bar by bar on any forex pair,
commodity, index or coin and says the moment to get in, long or short.
Standard library only. It never places an order.

    python3 entry.py check EURUSD                         # London range breakout, both sides, 5m bars
    python3 entry.py check XAUUSD --session comex --side short
    python3 entry.py check BTCUSD --session utc --range-minutes 60
    python3 entry.py check US500 --setup level --level 6850 --side buy
    python3 entry.py check EURUSD --now "2026-11-16 08:45 London" --offline tests/fixtures/charts --write
    python3 entry.py watch GBPUSD --every 30 --until 15:00   # one line per closed bar, stops on the trigger
    python3 entry.py watchlist                            # every hit in trader/watchlist.json

Setups:
  range  a session range breakout. The range is the high and low of the first
         --range-minutes of the session (London 30, New York 30, Tokyo 30,
         US cash 15, COMEX 15, the crypto UTC day 60, the Asian range 420 ...
         see tradercore.py sessions). It triggers on the first COMPLETED bar
         after the range that CLOSES above the high (long) or below the low
         (short). --side buy or sell watches one side only. A wick through the
         level is not a trigger, and neither is a close exactly on it.
  level  the first completed bar that closes above --level (--side buy) or
         below it (--side sell): a 20-day high from trader-scanner, a round
         number, yesterday's low.
  --min-volume-x X  the trigger bar also needs X times the range bars' average
         volume. Forex feeds carry no volume (OTC): there it is skipped and said.

A trigger's time is the trigger bar's CLOSE time in the session's own time
zone (the 08:40 bar closes at 08:45 London) and its price is that close. Only
bars on the interval grid count (Yahoo's live tick is dropped) and a bar counts
only once it has closed and Yahoo has caught up to its close.

Statuses: triggered; waiting (not open yet, range still forming, or no close
beyond the level yet); expired (no trigger by no_entries_after, by default 30
minutes before the session's close); no-data (the session does not trade
today, or the feed sent no bars).

trader/config.json (optional): "entry_cutoff_minutes" (30), "flat_by_minutes"
(5), and per session overrides in "sessions", e.g.
{"london": {"range": 60, "no_entries_after": "15:00"}} (session-local times).

Exit codes: check 0 = triggered, 1 = anything else or an error. watch 0 on a
trigger, 1 otherwise. watchlist 0 when at least one symbol triggered.
"""

import argparse
import datetime
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "trader-core"))
import tradercore as tc  # noqa: E402

GRACE = 2        # seconds after a bar closes before watch asks for it
PAUSE = 0.5
LABEL = {"triggered": "TRIGGERED", "waiting": "WAITING", "expired": "EXPIRED", "no-data": "NO DATA"}
PHASE_LABEL = {"pre-open": "NOT OPEN YET", "forming": "RANGE FORMING", "closed": "MARKET CLOSED"}
SIDE_WORDS = {"buy": "long", "sell": "short", "both": "both sides"}


class EntryError(tc.TraderError):
    pass


def _r(x, inst):
    return None if x is None else round(float(x), inst["digits"]) + 0.0


def _p(x, inst):
    return tc.fmt_price(x, inst)


def _local(utc, tz):
    return tc.to_local(tz, utc)


def _side(text):
    t = str(text or "both").lower()
    if t in ("both", "any", "either"):
        return "both"
    return tc.side_word(t)


# ---------------------------------------------------------------- the rule

def evaluate(chart, inst, now_utc, session=None, setup="range", range_minutes=None, interval="5m", level=None,
             side="both", min_volume_x=None, cfg=None):
    """Pure function: the setup's status at now_utc from the instrument's bars."""
    cfg = cfg if cfg is not None else tc.load_config(None)
    if interval not in tc.INTERVALS:
        raise EntryError("--interval is %s" % ", ".join(tc.INTERVALS))
    step = tc.INTERVALS[interval]
    if setup not in ("range", "level"):
        raise EntryError("--setup is range or level")
    side = _side(side)
    if setup == "level":
        if level is None:
            raise EntryError("--setup level needs --level PRICE (for example a 20-day high from trader-scanner)")
        if side == "both":
            raise EntryError("--setup level needs --side buy (a close above) or --side sell (a close below)")
    sname = session or inst["session"]
    sdef = tc.session_def(sname, cfg)
    rmin = int(range_minutes if range_minutes is not None else sdef["range"])
    if rmin <= 0 or (rmin * 60) % step:
        raise EntryError("--range-minutes must be a whole number of %s bars" % interval)
    n_or = rmin * 60 // step
    sides = ("buy", "sell") if side == "both" else (side,)
    res = {"symbol": inst["symbol"], "class": inst["class"], "session": sname, "session_label": sdef["label"],
           "tz": sdef["tz"], "setup": setup, "side": side, "interval": interval, "range_minutes": rmin,
           "status": "waiting", "phase": "", "reason": "", "range": None, "levels": None, "trigger": None,
           "last": None, "forming": None, "min_volume_x": min_volume_x, "notes": [], "_bars": [],
           "now": tc.to_local(sdef["tz"], now_utc).strftime("%Y-%m-%d %H:%M:%S"), "source": chart.get("source")}
    dt = chart.get("data_time")
    res["data_time"] = tc.to_local(sdef["tz"], tc.utc_of(dt)).strftime("%Y-%m-%d %H:%M:%S") if dt else None
    sinst, phase = tc.locate(sname, now_utc, cfg)
    if sinst is None:
        nxt = tc.next_open(sname, now_utc, cfg)
        res.update(status="no-data", phase="closed", date=tc.to_local(sdef["tz"], now_utc).date().isoformat(),
                   reason="the %s does not trade today (%s)" % (sdef["label"], phase),
                   next_open=tc.stamp(nxt["open_utc"], nxt["tz"]) if nxt else None)
        return res
    tz = sinst["tz"]
    local = _local(now_utc, tz)
    win = tc.windows(sinst, cfg, rmin)
    res.update(date=sinst["date"], opens=tc.hm(sinst["open_local"]), closes=tc.hm(sinst["close_local"]),
               early_close=sinst["early"], calendar_known=sinst["calendar_known"],
               no_entries_before=tc.hm(win["no_entries_before_local"]),
               no_entries_after=tc.hm(win["no_entries_after_local"]), flat_by=tc.hm(win["flat_by_local"]),
               flat_by_utc=tc.iso(win["flat_by"]))
    if not sinst["calendar_known"]:
        res["notes"].append("the %s holiday calendar is not modeled: no bars on a weekday means a holiday"
                            % tc.CALENDAR_LABEL.get(sinst["calendar"], sinst["calendar"]))
    if phase == "pre-open":
        res.update(phase="pre-open", reason="the %s opens at %s %s%s" % (
            sinst["label"], res["opens"], tc.zone_label(tz),
            " and the %d-minute range is set at %s" % (rmin, tc.hm(win["range_end_local"])) if setup == "range" else ""))
        return res

    sb = tc.session_bars(chart, sinst, step, now_utc)
    bars = sb["bars"]
    pending = sb["pending"]
    if pending is not None:
        res["forming"] = {"bar_start": tc.hm(_local(pending["start"], tz)), "closes": tc.hm(_local(pending["end"], tz)),
                          "price": _r(pending["c"], inst)}
        res["lag_note"] = ("the feed's last trade is %s, before the %s bar's close: it counts once the feed catches "
                           "up (a minute at most)" % (tc.to_local(tz, tc.utc_of(dt)).strftime("%H:%M:%S"),
                                                     tc.hm(_local(pending["start"], tz))))
    elif sb["forming"] is not None:
        f = sb["forming"]
        res["forming"] = {"bar_start": tc.hm(_local(f["start"], tz)), "closes": tc.hm(_local(f["end"], tz)),
                          "price": _r(f["c"], inst)}
    res["_bars"] = bars
    res["bars_closed"] = len(bars)

    or_bars = [b for b in bars if b["slot"] < n_or]
    vols = [b["v"] for b in or_bars]
    avg_vol = (sum(vols) / float(len(vols))) if vols and inst.get("volume") else None
    if or_bars:
        hi, lo = max(b["h"] for b in or_bars), min(b["l"] for b in or_bars)
        res["range"] = {"high": _r(hi, inst), "low": _r(lo, inst), "mid": _r((hi + lo) / 2.0, inst),
                        "minutes": rmin, "bars": len(or_bars), "of": n_or,
                        "start": res["opens"], "end": tc.hm(win["range_end_local"]),
                        "complete": now_utc >= win["range_end"], "width_pips": round(tc.pips(hi - lo, inst), 1),
                        "avg_volume": int(round(avg_vol)) if avg_vol else None}
    if setup == "range":
        if now_utc < win["range_end"]:
            res.update(phase="forming", reason="%d of %d range bars closed; the range is set at %s %s" % (
                len(or_bars), n_or, tc.hm(win["range_end_local"]), tc.zone_label(tz)))
            return res
        missing = n_or - len(or_bars)
        if not or_bars or or_bars[0]["slot"] != 0 or missing > inst.get("gap_tolerance", 0):
            res.update(status="no-data", phase="open",
                       reason="the feed sent %d of the %d range bars for %s: no fair range to break"
                       % (len(or_bars), n_or, sinst["date"]))
            return res
        if missing:
            res["notes"].append("%d range bar%s missing from the feed (quiet minutes); the range uses the rest"
                                % (missing, "" if missing == 1 else "s"))
        long_lvl, short_lvl = hi, lo
    else:
        long_lvl = short_lvl = float(level)
    res["levels"] = {"buy": _r(long_lvl, inst) if "buy" in sides else None,
                     "sell": _r(short_lvl, inst) if "sell" in sides else None}
    if min_volume_x and not inst.get("volume"):
        res["notes"].append("--min-volume-x skipped: the %s feed has no volume (OTC)" % inst["symbol"])

    first_slot = n_or if setup == "range" else 0
    trig, thin = None, []
    for b in bars:
        if b["slot"] < first_slot or b["end"] < win["no_entries_before"] or b["end"] > win["no_entries_after"]:
            continue
        for s in sides:
            if (b["c"] > long_lvl) if s == "buy" else (b["c"] < short_lvl):
                vx = (b["v"] / avg_vol) if avg_vol else None
                if min_volume_x and inst.get("volume") and (vx is None or vx < min_volume_x):
                    thin.append((b, s))
                    continue
                trig = (b, s)
                break
        if trig:
            break
    last = bars[-1] if bars else None
    if last:
        res["last"] = {"bar_start": tc.hm(_local(last["start"], tz)), "close": _r(last["c"], inst),
                       "vs_buy_pips": round(tc.pips(last["c"] - long_lvl, inst), 1) if "buy" in sides else None,
                       "vs_sell_pips": round(tc.pips(short_lvl - last["c"], inst), 1) if "sell" in sides else None}
    if trig:
        b, s = trig
        lvl = long_lvl if s == "buy" else short_lvl
        vx = (b["v"] / avg_vol) if avg_vol else None
        res.update(status="triggered", phase="open" if now_utc < sinst["close_utc"] else "after-close",
                   reason="the %s bar closed %s %s" % (tc.hm(_local(b["start"], tz)), "above" if s == "buy" else "below",
                                                        ("the range " + ("high" if s == "buy" else "low"))
                                                        if setup == "range" else "the level"))
        res["trigger"] = {"side": s, "direction": tc.direction(s), "time": tc.hm(_local(b["end"], tz)),
                          "time_utc": tc.iso(b["end"]), "bar_start": tc.hm(_local(b["start"], tz)),
                          "bar_index": b["slot"], "price": _r(b["c"], inst), "level": _r(lvl, inst),
                          "beyond_pips": round(abs(tc.pips(b["c"] - lvl, inst)), 1),
                          "volume": b["v"], "volume_x": round(vx, 2) if vx is not None else None,
                          "filled": bool(b.get("filled"))}
        res["minutes_since"] = int((now_utc - b["end"]).total_seconds() // 60)
        if dt and tc.utc_of(dt) < b["end"]:
            res["data_note"] = ("the feed's last trade is %s, before this bar closed: its close can still move a tick"
                                % tc.to_local(tz, tc.utc_of(dt)).strftime("%H:%M:%S"))
        return res
    if not bars:
        res.update(status="no-data", phase="open", reason="the feed sent no bars for %s yet" % sinst["date"])
        return res
    cutoff = win["no_entries_after"]
    if now_utc >= cutoff and not (pending is not None and pending["end"] <= cutoff):
        res.update(status="expired", phase="after-close" if now_utc >= sinst["close_utc"] else "after-cutoff",
                   reason="no close %s by %s %s, the last time for a new entry%s" % (
                       _wanted(res, inst), res["no_entries_after"], tc.zone_label(tz),
                       " (early close today: %s)" % sinst["early"] if sinst["early"] else ""))
        return res
    res["phase"] = "open"
    lb = last
    if thin and thin[-1][0] is lb:
        res["reason"] = "the %s bar closed beyond the level at %s but on %.2fx the range's volume, under your %.2fx" % (
            tc.hm(_local(lb["start"], tz)), _p(lb["c"], inst), (lb["v"] / avg_vol) if avg_vol else 0, min_volume_x)
    elif lb["end"] < win["no_entries_before"]:
        res["reason"] = "last close %s (%s bar), but no entries before %s" % (
            _p(lb["c"], inst), tc.hm(_local(lb["start"], tz)), res["no_entries_before"])
    else:
        parts = []
        if "buy" in sides:
            gap = long_lvl - lb["c"]
            parts.append("%s %s the %s %s" % (tc.fmt_dist(gap, inst), "under" if gap >= 0 else "over",
                                              "range high" if setup == "range" else "level", _p(long_lvl, inst)))
        if "sell" in sides:
            gap = lb["c"] - short_lvl
            parts.append("%s %s the %s %s" % (tc.fmt_dist(gap, inst), "over" if gap >= 0 else "under",
                                              "range low" if setup == "range" else "level", _p(short_lvl, inst)))
        res["reason"] = "last close %s (%s bar): %s" % (_p(lb["c"], inst), tc.hm(_local(lb["start"], tz)),
                                                        ", ".join(parts))
    return res


def _wanted(res, inst):
    lv = res.get("levels") or {}
    out = []
    if lv.get("buy") is not None:
        out.append("above %s" % _p(lv["buy"], inst))
    if lv.get("sell") is not None:
        out.append("below %s" % _p(lv["sell"], inst))
    return " or ".join(out) or "beyond the level"


def public(res):
    return {k: v for k, v in res.items() if not k.startswith("_")}


def entry_doc(res, now_utc):
    """trader/entry.json: what trader-exit plans from."""
    t = res.get("trigger") or {}
    rg = res.get("range")
    return {"created_by": "trader-entry", "symbol": res["symbol"], "class": res["class"], "session": res["session"],
            "tz": res["tz"], "setup": res["setup"], "side": t.get("side") or res["side"],
            "date": res.get("date"), "status": res["status"], "time": t.get("time"), "time_utc": t.get("time_utc"),
            "bar_start": t.get("bar_start"), "bar_index": t.get("bar_index"), "price": t.get("price"),
            "level": t.get("level"), "interval": res["interval"],
            "opening_range": {"high": rg["high"], "low": rg["low"], "mid": rg["mid"], "minutes": rg["minutes"]}
            if rg else None, "flat_by": res.get("flat_by"), "flat_by_utc": res.get("flat_by_utc"),
            "source": res.get("source"), "checked_at": tc.iso(now_utc), "reason": res.get("reason")}


# ---------------------------------------------------------------- words

def setup_name(res, inst):
    if res["setup"] == "range":
        return "%s range breakout (%d-minute range, %s)" % (res["session_label"], res["range_minutes"],
                                                             SIDE_WORDS[res["side"]])
    lv = res.get("levels") or {}
    if res["side"] == "buy":
        return "close above %s" % _p(lv.get("buy"), inst)
    return "close below %s" % _p(lv.get("sell"), inst)


def describe(res, inst):
    when = datetime.datetime.strptime(res["now"], "%Y-%m-%d %H:%M:%S")
    zl = tc.zone_label(res["tz"])
    head = "%s  %s %s  %s on %s bars (%s)" % (res["symbol"], when.strftime("%a %Y-%m-%d %H:%M"), zl, setup_name(res, inst),
                                              {"5m": "5-minute", "1m": "1-minute", "15m": "15-minute"}[res["interval"]],
                                              res.get("source") or "yahoo")
    out = [head]
    rg = res.get("range")
    if rg and res["setup"] == "range":
        out.append("Range %s-%s %s: high %s, low %s, %s wide (%d of %d bars%s)." % (
            rg["start"], rg["end"], zl, _p(rg["high"], inst), _p(rg["low"], inst),
            tc.fmt_dist(rg["high"] - rg["low"], inst), rg["bars"], rg["of"], "" if rg["complete"] else ", still forming"))
    label = PHASE_LABEL.get(res["phase"]) or LABEL.get(res["status"], res["status"].upper())
    t = res.get("trigger")
    if t:
        out.append("TRIGGERED %s %s %s at %s: the %s bar (bar %d) closed %s %s %s (%s beyond%s)." % (
            t["direction"].upper(), t["time"], zl, _p(t["price"], inst), t["bar_start"], t["bar_index"],
            "above" if t["side"] == "buy" else "below",
            ("the range " + ("high" if t["side"] == "buy" else "low")) if res["setup"] == "range" else "the level",
            _p(t["level"], inst), tc.fmt_dist(t["price"] - t["level"], inst),
            (", %.2fx the range's volume" % t["volume_x"]) if res.get("min_volume_x") and t.get("volume_x") else ""))
        step = tc.INTERVALS[res["interval"]] // 60
        late = res.get("minutes_since", 0) > step
        if late and res.get("last"):
            out.append("That was %d minutes ago; the last close is %s (%s bar). A late entry is a different trade: "
                       "the price, the stop distance and the odds have moved." % (
                           res["minutes_since"], _p(res["last"]["close"], inst), res["last"]["bar_start"]))
        if res.get("data_note"):
            out.append(res["data_note"] + ".")
        out.append("Nothing was placed." if late else
                   "This is the moment to get in, if you take the trade. Nothing was placed.")
        out.append("Next: set the stop and target BEFORE you trade: /trader-exit (exit.py plan --from "
                   "trader/entry.json). Flat by %s %s." % (res.get("flat_by"), zl))
    else:
        out.append("%s  %s." % (label, res["reason"]))
        f = res.get("forming")
        if res.get("lag_note") and res["status"] == "waiting":
            out.append(res["lag_note"] + ".")
        elif f and res["status"] == "waiting" and res["phase"] in ("open", "forming"):
            out.append("The %s bar is still forming (%s so far, closes %s); it does not count until it closes." % (
                f["bar_start"], _p(f["price"], inst), f["closes"]))
        if res["status"] == "expired":
            out.append("No entry on this setup today. Nothing was placed.")
        if res.get("next_open"):
            out.append("Next session: %s." % res["next_open"])
    if res.get("early_close"):
        out.append("Early close today (%s): no new entries after %s %s." % (res["early_close"],
                                                                           res["no_entries_after"], zl))
    for n in res.get("notes") or []:
        out.append("Note: %s." % n)
    return out


def bar_line(b, res, inst):
    tz = res["tz"]
    start = tc.hm(_local(b["start"], tz))
    rg = res.get("range") or {}
    lv = res.get("levels") or {}
    t = res.get("trigger")
    n_or = rg.get("of") or 0
    if res["setup"] == "range" and b["slot"] < n_or:
        seen = [x for x in res["_bars"] if x["slot"] <= b["slot"]]
        note = "range so far %s to %s" % (_p(min(x["l"] for x in seen), inst), _p(max(x["h"] for x in seen), inst))
        if b["slot"] == n_or - 1 and rg:
            note = "range set: high %s, low %s" % (_p(rg["high"], inst), _p(rg["low"], inst))
    elif t and t["bar_index"] == b["slot"]:
        note = "TRIGGERED %s: closed %s %s. Get in now if you take it: %s, %s" % (
            t["direction"].upper(), "above" if t["side"] == "buy" else "below", _p(t["level"], inst), t["time"],
            _p(t["price"], inst))
    else:
        parts = []
        if lv.get("buy") is not None:
            d = b["c"] - lv["buy"]
            parts.append("%s %s %s" % (tc.fmt_dist(d, inst), "over" if d > 0 else "under", _p(lv["buy"], inst)))
        if lv.get("sell") is not None:
            d = b["c"] - lv["sell"]
            parts.append("%s %s %s" % (tc.fmt_dist(d, inst), "over" if d >= 0 else "under", _p(lv["sell"], inst)))
        note = ", ".join(parts)
    return "%5s bar  closed %s  %s" % (start, _p(b["c"], inst), note)


# ---------------------------------------------------------------- watch

class SimClock(object):
    """A clock that moves only when it sleeps: replays a day without waiting."""

    def __init__(self, start):
        self.t = start

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.t += datetime.timedelta(seconds=max(1, int(round(seconds))))


def watch_loop(provider, clock, sleep, emit, inst, opts, every=30, until=None, max_errors=5, on_trigger=None):
    """Poll bar by bar until a trigger (0), expiry, the close or --until (1).
    provider(now_utc) -> chart, clock() -> naive UTC, sleep(seconds), emit(line)."""
    cfg = opts.get("cfg")
    step = tc.INTERVALS[opts.get("interval", "5m")]
    sname = opts.get("session") or inst["session"]
    printed, errors, said_pre, first = -1, 0, False, True
    next_fetch = None
    while True:
        now = clock()
        if next_fetch is not None and now < next_fetch:
            sleep(max(1, min(every, (next_fetch - now).total_seconds())))
            continue
        sinst, phase = tc.locate(sname, now, cfg)
        if sinst is None:
            emit("%s: the %s does not trade today (%s). Nothing to watch." % (
                inst["symbol"], tc.SESSIONS[sname]["label"], phase))
            return 1, None
        tz = sinst["tz"]
        local = _local(now, tz)
        if phase == "closed":
            emit("%s %s  the %s is over for today. Nothing to watch." % (tc.hm(local), tc.zone_label(tz),
                                                                        sinst["label"]))
            return 1, None
        first_close = sinst["open_utc"] + datetime.timedelta(seconds=step)
        if now < first_close:
            if not said_pre:
                emit("%s %s  %s: watching from the first bar's close at %s." % (
                    tc.hm(local), tc.zone_label(tz), "not open yet" if now < sinst["open_utc"] else "open, no bar closed yet",
                    tc.hm(_local(first_close, tz))))
                said_pre = True
            next_fetch = first_close + datetime.timedelta(seconds=GRACE)
            continue
        try:
            chart = provider(now)
            errors = 0
        except tc.TraderError as e:
            errors += 1
            emit("%s %s  could not read bars: %s" % (local.strftime("%H:%M:%S"), tc.zone_label(tz), e))
            if errors >= max_errors:
                emit("Stopping after %d failed reads in a row." % errors)
                return 1, None
            next_fetch = now + datetime.timedelta(seconds=every)
            continue
        res = evaluate(chart, inst, now, **opts)
        bars = res["_bars"]
        lines = describe(res, inst)
        fresh = first
        if first:
            emit(lines[0])
            if len(lines) > 1 and lines[1].startswith("Range"):
                emit(lines[1])
            if bars and not res.get("trigger"):
                emit(bar_line(bars[-1], res, inst))
            printed = bars[-1]["slot"] if bars else -1
            first = False
        else:
            for b in bars:
                if b["slot"] > printed:
                    emit(bar_line(b, res, inst))
                    printed = b["slot"]
        if res["status"] == "triggered":
            for line in lines[1:]:
                if line.startswith("Range") or (line.startswith("TRIGGERED") and not fresh):
                    continue
                emit(line)
            if on_trigger:
                on_trigger(res, now)
            return 0, res
        if res["status"] == "expired" or now >= sinst["close_utc"]:
            emit("EXPIRED  %s." % (res["reason"] or "the session closed without a trigger"))
            return 1, res
        if until and now >= until:
            emit("Stopped at --until %s without a trigger. %s." % (tc.hm(_local(until, tz)), res["reason"]))
            return 1, res
        sl = tc.slots(sinst, step)
        done = [i for i, s in enumerate(sl) if s + datetime.timedelta(seconds=step) <= now]
        expected = done[-1] if done else -1
        if not bars or bars[-1]["slot"] < expected:
            wait = every
        else:
            later = [s + datetime.timedelta(seconds=step) for s in sl if s + datetime.timedelta(seconds=step) > now]
            wait = ((later[0] if later else sinst["close_utc"]) - now).total_seconds() + GRACE
        cutoff = tc.windows(sinst, cfg, opts.get("range_minutes"))["no_entries_after"]
        for stop_at in (until, cutoff, sinst["close_utc"]):
            if stop_at and stop_at > now:
                wait = min(wait, (stop_at - now).total_seconds())
        next_fetch = now + datetime.timedelta(seconds=max(1, wait))


# ---------------------------------------------------------------- commands

def _opts(a, cfg):
    side = _side(a.side)
    if a.setup == "range" and a.level is not None:
        raise EntryError("--level is for --setup level (a range's levels are its high and low)")
    if a.min_volume_x is not None and a.min_volume_x <= 0:
        raise EntryError("--min-volume-x must be above 0")
    if a.level is not None and a.level <= 0:
        raise EntryError("--level must be a price above 0")
    if a.setup == "level" and side == "both":
        side = "buy"
    if a.session:
        tc.session_def(a.session, cfg)
    return {"session": a.session, "setup": a.setup, "range_minutes": a.range_minutes, "interval": a.interval,
            "level": a.level, "side": side, "min_volume_x": a.min_volume_x, "cfg": cfg}


def _chart(a, inst, now=None):
    if a.offline:
        return tc.get_chart(inst, a.interval, offline=a.offline)
    days = 0 if now is None else max(0, (tc.utc_now() - now).days + 1)
    return tc.get_chart(inst, a.interval, tc.chart_range(days, a.interval))


def _load(a, inst):
    """(chart, now). An offline file without --now is read as of its own time."""
    cfg_zone = tc.session_def(a.session or inst["session"])["tz"]
    if a.now:
        now = tc.parse_now(a.now, cfg_zone)
        return _chart(a, inst, now), now
    ch = _chart(a, inst)
    if a.offline and ch.get("data_time"):
        return ch, tc.utc_of(ch["data_time"])
    return ch, tc.utc_now()


def cmd_check(a):
    cfg = tc.load_config(a.config)
    opts = _opts(a, cfg)
    inst = tc.resolve(a.symbol, cfg)
    chart, now = _load(a, inst)
    res = evaluate(chart, inst, now, **opts)
    if a.write:
        tc.write_json(a.write, entry_doc(res, now))
    if a.json:
        print(json.dumps(public(res), indent=2, default=str))
    else:
        for line in describe(res, inst):
            print(line)
        if a.write:
            print("Wrote %s (status %s)." % (a.write, res["status"]))
    return 0 if res["status"] == "triggered" else 1


def cmd_watch(a):
    cfg = tc.load_config(a.config)
    opts = _opts(a, cfg)
    inst = tc.resolve(a.symbol, cfg)
    if a.every <= 0:
        raise EntryError("--every must be above 0 seconds")
    zone = tc.session_def(a.session or inst["session"], cfg)["tz"]
    start = tc.parse_now(a.now, zone) if a.now else None
    if a.offline or start is not None:
        if start is None:
            start = _load(a, inst)[1]
        clock = SimClock(start)
        now_fn, sleep_fn = clock.now, clock.sleep
    else:
        now_fn, sleep_fn = tc.utc_now, time.sleep

    def provider(now):
        return _chart(a, inst, now)
    until = None
    if a.until:
        sinst, _ = tc.locate(a.session or inst["session"], now_fn(), cfg)
        if sinst:
            day = sinst["open_local"].date()
            t = datetime.datetime.combine(day, datetime.time()) + datetime.timedelta(minutes=tc.parse_hhmm(a.until, "--until"))
            until = tc.to_utc(zone, t if t >= sinst["open_local"] else t + datetime.timedelta(days=1))

    def on_trigger(res, now):
        tc.write_json(a.out, entry_doc(res, now))
        print("Wrote %s." % a.out, flush=True)

    def emit(line):
        print(line, flush=True)
    code, _ = watch_loop(provider, now_fn, sleep_fn, emit, inst, opts, every=a.every, until=until,
                         on_trigger=on_trigger)
    return code


def cmd_watchlist(a):
    cfg = tc.load_config(a.config)
    opts = _opts(a, cfg)
    doc = tc.read_json(a.watchlist, "watchlist (run /trader-scanner first, it writes the hits there)")
    hits = [h for h in (doc.get("hits") or []) if isinstance(h, dict) and h.get("symbol")]
    if not hits:
        raise EntryError("no hits in %s: the scanner found nothing to watch" % a.watchlist)
    rows = []
    for i, h in enumerate(hits):
        o = dict(opts)
        if not a.session and h.get("session"):
            o["session"] = h["session"]
        if a.setup == "level" and o["level"] is None:
            o["level"] = h.get("level")
        try:
            inst = tc.resolve(h["symbol"], cfg)
            if a.setup == "level" and o["level"] is None:
                raise EntryError("needs a level: --level PRICE or a \"level\" in the watchlist")
            if i and not a.offline:
                tc.SLEEP(PAUSE)
            zone = tc.session_def(o["session"] or inst["session"], cfg)["tz"]
            if a.now:
                now = tc.parse_now(a.now, zone)
                chart = _chart(a, inst, now)
            else:
                chart = _chart(a, inst)
                now = tc.utc_of(chart["data_time"]) if a.offline and chart.get("data_time") else tc.utc_now()
            rows.append((inst, evaluate(chart, inst, now, **o), None))
        except tc.TraderError as e:
            rows.append(({"symbol": str(h["symbol"]).upper()}, None, str(e)))
    if a.json:
        print(json.dumps([{"symbol": i["symbol"], "result": public(r) if r else None, "error": e} for i, r, e in rows],
                         indent=2, default=str))
    else:
        print("%-8s %-10s %-10s %-6s %-12s %-12s %s" % ("SYMBOL", "SESSION", "STATUS", "TIME", "PRICE", "LAST", "WHY"))
        for inst, r, e in rows:
            if e:
                print("%-8s error: %s" % (inst["symbol"], e))
                continue
            t = r.get("trigger") or {}
            last = r.get("last") or {}
            st = ("%s %s" % ("long" if t["side"] == "buy" else "short", "trig")) if t else \
                {"pre-open": "not open", "forming": "forming", "closed": "closed"}.get(r["phase"], r["status"])
            print("%-8s %-10s %-10s %-6s %-12s %-12s %s" % (
                inst["symbol"], r["session"], st[:10], t.get("time") or "-",
                _p(t["price"], inst) if t else "-", _p(last["close"], inst) if last else "-", r["reason"][:70]))
        n = sum(1 for _, r, _ in rows if r and r["status"] == "triggered")
        print("%d of %d triggered. Pick one, then: entry.py check <SYMBOL> --write, and /trader-exit." % (n, len(rows)))
        print("Free Yahoo bars, unofficial and can lag. Nothing was placed.")
    return 0 if any(r and r["status"] == "triggered" for _, r, _ in rows) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Entry Timer (trader-entry): a setup, bar by bar, long or short.")
    sub = ap.add_subparsers(dest="cmd")

    def common(p):
        p.add_argument("--session", help="london, ny, tokyo, sydney, asia_london, us_cash, comex, nymex, cbot, "
                                         "xetra, lse, euronext, tse, hkex, asx, utc, crypto_ny (default: the instrument's)")
        p.add_argument("--setup", choices=["range", "level"], default="range")
        p.add_argument("--range-minutes", "--or-minutes", dest="range_minutes", type=int,
                       help="opening range length (default: the session's)")
        p.add_argument("--interval", choices=list(tc.INTERVALS), default="5m")
        p.add_argument("--level", type=float, help="the price to close beyond (--setup level)")
        p.add_argument("--side", default="both", help="both (default), buy/long or sell/short")
        p.add_argument("--min-volume-x", type=float, help="trigger bar volume vs the range bars' average")
        p.add_argument("--now", help='pretend it is this time: "2026-11-16 08:45" (session zone) or add a zone')
        p.add_argument("--offline", metavar="PATH", help="saved Yahoo chart JSON (.json/.json.gz) or a folder")
        p.add_argument("--config", default="trader/config.json")

    p = sub.add_parser("check", help="the setup's status right now")
    p.add_argument("symbol")
    common(p)
    p.add_argument("--write", nargs="?", const="trader/entry.json", metavar="PATH",
                   help="save the result (default trader/entry.json)")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("watch", help="poll bar by bar until it triggers or expires")
    p.add_argument("symbol")
    common(p)
    p.add_argument("--every", type=float, default=30, help="seconds between polls while the feed is behind")
    p.add_argument("--until", help="stop at this session-local time (HH:MM)")
    p.add_argument("--out", default="trader/entry.json", help="where a trigger is written")
    p = sub.add_parser("watchlist", help="check every hit in trader/watchlist.json")
    common(p)
    p.add_argument("--watchlist", default="trader/watchlist.json")
    p.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        return {"check": cmd_check, "watch": cmd_watch, "watchlist": cmd_watchlist}[a.cmd](a)
    except tc.TraderError as e:
        print("entry.py: %s" % e, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("entry.py: stopped.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
