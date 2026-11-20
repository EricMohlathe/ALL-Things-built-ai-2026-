#!/usr/bin/env python3
"""Exit Planner for trader-exit: sets the stop and the target BEFORE you enter,
long or short, on any forex pair, commodity, index or coin. Standard library only.
It never places an order.

    python3 exit.py plan                                     # from trader/entry.json: range-mid stop, 2R target
    python3 exit.py plan --stop range-mid --target 2R --write
    python3 exit.py plan --stop pips:15 --target pips:30     # distances in the instrument's pips / points
    python3 exit.py plan --symbol XAUUSD --side sell --entry 4053.20 --range-high 4062.4 --range-low 4055.1 \\
        --session comex --date 2026-11-16 --time 08:50
    python3 exit.py plan --stop atr:1.5 --offline tests/fixtures/charts   # ATR needs the session's bars
    python3 exit.py show                                     # the current trader/plan.json

Stops (rounded to the instrument's tick, AWAY from the entry: down for a long,
up for a short):
  range-mid   the opening range's midpoint (the default for a range entry)
  range-far   the far side of the range: its low for a long, its high for a short
  price:X     your price
  pct:X       X percent from the entry
  pips:N      N pips (forex, metals) or points (indices, crypto) or ticks
              (energy, grains, futures) from the entry
  atr:K       K times the 14-bar ATR of the session's bars up to the entry bar
  A level setup has no range to default to: give a stop.

Targets (rounded to the nearest tick):
  2R (default), 1R, 1.5R ...   entry +/- R x risk
  pips:N                       N pips / points from the entry
  price:X                      your price

Refused, with the reason: a stop on the wrong side, a target on the wrong side,
a risk smaller than 3 typical spreads or 0.03% of the price (the spread and
normal wiggle would stop you out), an entry.json that has not triggered
(unless you give --entry).

flat_by: from the entry (the session's close minus "flat_by_minutes", 5 by
default, or "sessions.<name>.flat_by" in trader/config.json), or --flat-by
HH:MM in the session's time zone. Out by then, win or lose.

A stop is a plan, not a guarantee: a gap, a weekend open or a fast market can
fill past it. Exit codes: plan 0 = a plan, 1 = refused or an error.
"""

import argparse
import datetime
import json
import os
import re
import sys
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "trader-core"))
import tradercore as tc  # noqa: E402

ATR_BARS = 14
MIN_RISK_PCT = Decimal("0.03")
MIN_SPREADS = 3
NOTE = "A stop is a plan, not a guarantee: a gap, a weekend open or a fast market can fill past it."
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}


class PlanError(tc.TraderError):
    pass


D = tc.D


def ratio(x):
    s = "%.2f" % float(x)
    return s[:-1] if s.endswith("0") else s


def parse_stop(text):
    t = str(text).strip().lower()
    if t in ("range-mid", "range_mid", "or-mid", "or_mid", "mid"):
        return "range_mid", None
    if t in ("range-far", "range_far", "or-low", "or_low", "or-high", "or_high", "far", "low", "high"):
        return "range_far", None
    m = re.match(r"^(price|pct|pips|points|ticks|atr):\s*\$?([0-9][0-9,]*\.?[0-9]*)$", t)
    if not m:
        raise PlanError("--stop is range-mid, range-far, price:X, pct:X, pips:N or atr:K (got %r)" % text)
    kind, val = m.group(1), D(m.group(2), "--stop")
    if kind in ("points", "ticks"):
        kind = "pips"
    if val <= 0:
        raise PlanError("--stop %s needs a number above 0" % kind)
    if kind == "pct" and val >= 100:
        raise PlanError("--stop pct:X needs X under 100")
    return kind, val


def parse_target(text):
    t = str(text).strip()
    m = re.match(r"^([0-9]*\.?[0-9]+)\s*[Rr]$", t)
    if m:
        r = D(m.group(1), "--target")
        if r <= 0:
            raise PlanError("--target needs an R multiple above 0, like 1R or 2R")
        return "r", r
    m = re.match(r"^(price|pips|points|ticks):\s*\$?([0-9][0-9,]*\.?[0-9]*)$", t.lower())
    if m:
        kind = "price" if m.group(1) == "price" else "pips"
        v = D(m.group(2), "--target")
        if v <= 0:
            raise PlanError("--target %s needs a number above 0" % kind)
        return kind, v
    raise PlanError("--target is 2R, 1R, 1.5R ..., pips:N or price:X (got %r)" % text)


def r_label(r):
    n = int(r) if r == r.to_integral_value() else None
    return "%sR (%s times the risk)" % (tc.num(r), WORDS.get(n, tc.num(r)))


def compute(inst, side, entry, stop_rule, stop_param, target_rule, target_param, range_high=None, range_low=None,
            atr=None, atr_bars=None):
    """The stop, the target and the risk, to the tick. Raises PlanError with the reason."""
    long = tc.side_word(side) == "buy"
    sgn = 1 if long else -1
    tick, pip = D(inst["tick"]), D(inst["pip"])
    e = tc.to_tick(entry, tick)
    if e <= 0:
        raise PlanError("the entry price must be above 0")
    p = lambda x: tc.fmt_price(x, inst)  # noqa: E731
    detail = ""
    if stop_rule in ("range_mid", "range_far"):
        if range_high is None or range_low is None:
            raise PlanError("a %s stop needs the opening range (--range-high and --range-low)"
                            % stop_rule.replace("_", "-"))
        rh, rl = D(range_high), D(range_low)
        if rh <= rl:
            raise PlanError("the range high %s must be above its low %s" % (p(rh), p(rl)))
        if stop_rule == "range_mid":
            raw = (rh + rl) / 2
            label = "range midpoint"
            detail = "(%s + %s) / 2 = %s" % (p(rh), p(rl), tc.num(raw))
        else:
            raw = rl if long else rh
            label = "range %s" % ("low" if long else "high")
    elif stop_rule == "price":
        raw, label = stop_param, "your price"
    elif stop_rule == "pct":
        raw = e * (1 - sgn * stop_param / 100)
        label = "%s%% %s the entry" % (tc.num(stop_param), "under" if long else "over")
    elif stop_rule == "pips":
        raw = e - sgn * stop_param * pip
        label = "%s %s %s the entry" % (tc.num(stop_param), inst["pip_label"], "under" if long else "over")
    elif stop_rule == "atr":
        if atr is None:
            raise PlanError("an atr stop needs the session's bars")
        a = D(round(atr, 8))
        raw = e - sgn * stop_param * a
        label = "%s x ATR(%d) %s the entry" % (tc.num(stop_param), atr_bars, "under" if long else "over")
        detail = "ATR %s over the %d bars to the entry%s" % (
            tc.fmt_dist(a, inst), atr_bars, " (fewer than 14 so far)" if atr_bars < ATR_BARS else "")
    else:
        raise PlanError("unknown stop rule %r" % stop_rule)
    stop = tc.stop_tick(raw, tick, long)
    if stop != D(raw) and not detail:
        detail = "%s rounded %s to the tick" % (tc.num(raw), "down" if long else "up")
    elif stop != D(raw):
        detail += ", rounded %s to the tick" % ("down" if long else "up")
    if (long and stop >= e) or (not long and stop <= e):
        raise PlanError("the stop %s (%s) is %s the entry %s: a %s's stop goes %s it" % (
            p(stop), label, "at or above" if long else "at or below", p(e), "long" if long else "short",
            "under" if long else "over"))
    if stop <= 0:
        raise PlanError("the stop works out to %s: pick a stop above 0" % p(stop))
    risk = (e - stop) * sgn
    floor = max(e * MIN_RISK_PCT / 100, D(inst.get("spread") or 0) * MIN_SPREADS)
    if risk < floor:
        raise PlanError("the stop is %s from the entry, under the %s floor (the larger of 3 typical spreads, %s, "
                        "and 0.03%% of the price, %s): the spread and normal wiggle would stop you out. Widen it." % (
                            tc.fmt_dist(risk, inst), tc.fmt_dist(floor, inst),
                            tc.fmt_dist(D(inst.get("spread") or 0) * MIN_SPREADS, inst),
                            tc.fmt_dist(e * MIN_RISK_PCT / 100, inst)))
    if target_rule == "r":
        target = tc.to_tick(e + sgn * target_param * risk, tick)
        t_label = r_label(target_param)
    elif target_rule == "pips":
        target = tc.to_tick(e + sgn * target_param * pip, tick)
        t_label = "%s %s from the entry" % (tc.num(target_param), inst["pip_label"])
    else:
        target = tc.to_tick(target_param, tick)
        t_label = None
    if (long and target <= e) or (not long and target >= e):
        raise PlanError("the target %s is %s the entry %s: a %s's target goes %s it" % (
            p(target), "at or below" if long else "at or above", p(e), "long" if long else "short",
            "above" if long else "below"))
    reward = (target - e) * sgn
    rr = (reward / risk).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if t_label is None:
        t_label = "your price (%sR)" % ratio(rr)
    elif target_rule == "pips":
        t_label += " (%sR)" % ratio(rr)
    return {"entry": e, "stop": stop, "stop_label": label, "stop_detail": detail, "target": target,
            "target_r": target_param if target_rule == "r" else rr, "target_label": t_label,
            "risk": risk, "reward": reward, "reward_risk": rr}


def atr_of(bars, n=ATR_BARS):
    """Average true range of the last n bars (all of them if fewer). The session's first
    bar uses its own high - low."""
    trs, prev = [], None
    for b in bars:
        tr = b["h"] - b["l"]
        if prev is not None:
            tr = max(tr, abs(b["h"] - prev), abs(b["l"] - prev))
        trs.append(tr)
        prev = b["c"]
    use = trs[-n:]
    return sum(use) / len(use), len(use)


# ---------------------------------------------------------------- plan

def gather(a, cfg):
    """The entry facts, from trader/entry.json or the flags."""
    if a.symbol and a.from_path:
        raise PlanError("use --from or --symbol, not both")
    if a.symbol:
        inst = tc.resolve(a.symbol, cfg)
        if a.entry is None:
            raise PlanError("--symbol needs --entry PRICE")
        if (a.range_high is None) != (a.range_low is None):
            raise PlanError("give both --range-high and --range-low, or neither")
        info = {"symbol": inst["symbol"], "side": tc.side_word(a.side or "buy"), "entry": a.entry,
                "setup": a.setup or ("range" if a.range_high is not None else "level"),
                "session": a.session or inst["session"], "date": a.date, "entry_time": a.time,
                "entry_bar": a.entry_bar, "interval": a.interval or "5m", "range_high": a.range_high,
                "range_low": a.range_low, "range_minutes": a.range_minutes, "flat_by": None, "source": "flags"}
    else:
        path = a.from_path or "trader/entry.json"
        doc = tc.read_json(path, "entry (run /trader-entry first, or give --symbol and --entry)")
        inst = tc.resolve(doc.get("symbol"), cfg)
        side = doc.get("side")
        if a.side:
            side = a.side
        if str(side).lower() == "both":
            raise PlanError("%s has not picked a side yet (status %s): give --side buy or --side sell to plan ahead"
                            % (path, doc.get("status")))
        if doc.get("status") != "triggered" and a.entry is None:
            raise PlanError("%s says %s is %s, not triggered: plan once it triggers, or give --entry PRICE "
                            "(and --side) to plan ahead" % (path, doc.get("symbol"), doc.get("status") or "unknown"))
        orr = doc.get("opening_range") or {}
        info = {"symbol": inst["symbol"], "side": tc.side_word(side), "entry": a.entry if a.entry is not None
                else doc.get("price"), "setup": a.setup or doc.get("setup") or "range",
                "session": a.session or doc.get("session") or inst["session"], "date": a.date or doc.get("date"),
                "entry_time": a.time or (doc.get("time") if a.entry is None else None),
                "entry_bar": a.entry_bar if a.entry_bar is not None else (doc.get("bar_index") if a.entry is None else None),
                "interval": a.interval or doc.get("interval") or "5m",
                "range_high": a.range_high if a.range_high is not None else orr.get("high"),
                "range_low": a.range_low if a.range_low is not None else orr.get("low"),
                "range_minutes": orr.get("minutes") or a.range_minutes, "source": path}
        if info["entry"] is None:
            raise PlanError("%s has no price" % path)
    if info["interval"] not in tc.INTERVALS:
        raise PlanError("interval is %s" % ", ".join(tc.INTERVALS))
    return inst, info


def build_plan(a, now_utc, cfg):
    inst, info = gather(a, cfg)
    long = info["side"] == "buy"
    stop_text = a.stop
    if not stop_text:
        if info["setup"] != "range":
            raise PlanError("a %s setup has no range to default to: give --stop price:X, pips:N, pct:X or atr:K"
                            % info["setup"])
        stop_text = "range-mid"
    stop_rule, stop_param = parse_stop(stop_text)
    target_rule, target_param = parse_target(a.target or "2R")
    sname = info["session"]
    sdef = tc.session_def(sname, cfg)
    tz = sdef["tz"]
    if info["date"]:
        sinst = tc.instance_on(sname, info["date"], cfg)
    else:
        sinst, phase = tc.locate(sname, now_utc, cfg)
        if sinst is None:
            raise PlanError("the %s does not trade today (%s): give --date" % (sdef["label"], phase))
    day = sinst["date"]
    win = tc.windows(sinst, cfg, info["range_minutes"])
    entry_utc = None
    if info["entry_time"]:
        mins = tc.parse_hhmm(str(info["entry_time"]).replace(" AM", "").replace(" PM", ""), "the entry time")
        t = datetime.datetime.combine(sinst["open_local"].date(), datetime.time()) + datetime.timedelta(minutes=mins)
        if t < sinst["open_local"]:
            t += datetime.timedelta(days=1)
        entry_utc = tc.to_utc(tz, t)
    flat_utc = win["flat_by"]
    flat_note = ""
    if a.flat_by:
        t = datetime.datetime.combine(sinst["open_local"].date(), datetime.time()) + \
            datetime.timedelta(minutes=tc.parse_hhmm(a.flat_by, "--flat-by"))
        if t < sinst["open_local"]:
            t += datetime.timedelta(days=1)
        if t > sinst["close_local"]:
            raise PlanError("--flat-by %s is after the %s closes at %s %s" % (
                a.flat_by, sinst["label"], tc.hm(sinst["close_local"]), tc.zone_label(tz)))
        flat_utc = tc.to_utc(tz, t)
    elif sinst["early"]:
        flat_note = "early close today (%s)" % sinst["early"]
    if entry_utc and entry_utc >= flat_utc:
        raise PlanError("the entry at %s is at or after your flat-by %s %s: there is no time left to hold it"
                        % (tc.hm(tc.to_local(tz, entry_utc)), tc.hm(tc.to_local(tz, flat_utc)), tc.zone_label(tz)))
    atr = atr_n = None
    if stop_rule == "atr":
        step = tc.INTERVALS[info["interval"]]
        days = max(0, (tc.utc_now() - sinst["open_utc"]).days + 1)
        chart = tc.get_chart(inst, info["interval"], tc.chart_range(days, info["interval"]) if not a.offline else "",
                             offline=a.offline)
        upto = entry_utc if entry_utc else (tc.parse_now(a.now, tz) if a.now else now_utc)
        bars = [b for b in tc.session_bars(chart, sinst, step, upto)["bars"]
                if info["entry_bar"] is None or b["slot"] <= info["entry_bar"]]
        if len(bars) < 3:
            raise PlanError("an atr stop needs at least 3 closed %s bars of %s on %s by the entry; found %d"
                            % (info["interval"], inst["symbol"], day, len(bars)))
        atr, atr_n = atr_of(bars)
    c = compute(inst, info["side"], info["entry"], stop_rule, stop_param, target_rule, target_param,
                info["range_high"], info["range_low"], atr, atr_n)
    rng = None
    if info["range_high"] is not None and info["range_low"] is not None:
        rng = {"high": float(D(info["range_high"])), "low": float(D(info["range_low"])),
               "minutes": int(info["range_minutes"] or win["range_minutes"])}
    plan = {"created_by": "trader-exit", "symbol": inst["symbol"], "class": inst["class"], "side": info["side"],
            "direction": tc.direction(info["side"]), "date": day, "session": sname, "tz": tz,
            "setup": info["setup"], "entry": float(c["entry"]),
            "entry_time": tc.hm(tc.to_local(tz, entry_utc)) if entry_utc else None,
            "entry_time_utc": tc.iso(entry_utc) if entry_utc else None, "entry_bar": info["entry_bar"],
            "interval": info["interval"], "opening_range": rng,
            "stop": float(c["stop"]), "stop_rule": stop_rule, "stop_label": c["stop_label"],
            "stop_detail": c["stop_detail"], "target": float(c["target"]), "target_r": float(c["target_r"]),
            "target_label": c["target_label"], "risk_per_unit": float(c["risk"]),
            "risk_pips": round(tc.pips(c["risk"], inst), 2), "reward_pips": round(tc.pips(c["reward"], inst), 2),
            "pip_label": inst["pip_label"], "reward_risk": float(c["reward_risk"]),
            "flat_by": tc.hm(tc.to_local(tz, flat_utc)), "flat_by_utc": tc.iso(flat_utc),
            "spread": inst.get("spread"), "created_at": tc.iso(now_utc), "note": NOTE}
    if atr is not None:
        plan["atr"] = round(atr, 8)
        plan["atr_bars"] = atr_n
    warnings = []
    if flat_note:
        warnings.append("Flat by %s: %s." % (plan["flat_by"], flat_note))
    mrr = cfg.get("min_reward_risk")
    if mrr is not None and c["reward_risk"] < D(mrr):
        warnings.append("Reward:risk %s is under your min_reward_risk %s in the config: trader-risk checks that."
                        % (ratio(c["reward_risk"]), tc.num(D(mrr))))
    spread = D(inst.get("spread") or 0)
    if spread and spread * 4 > c["risk"]:
        warnings.append("The typical spread (%s) is more than a quarter of the risk: costs eat a big slice of every R."
                        % tc.fmt_dist(spread, inst))
    today = tc.to_local(tz, now_utc).date().isoformat()
    if day != today:
        warnings.append("This plan is for %s, not today (%s)." % (day, today))
    if inst["class"] in ("forex", "commodity") and datetime.date.fromisoformat(day).weekday() == 4:
        warnings.append("It is Friday: be flat before the weekend close, or a Monday gap can jump the stop.")
    return inst, plan, warnings


def describe(plan, inst):
    day = datetime.date.fromisoformat(plan["date"])
    setup = {"range": "%s range breakout" % tc.SESSIONS.get(plan["session"], {}).get("label", plan["session"]),
             "level": "close beyond a level"}.get(plan["setup"], plan["setup"])
    zl = tc.zone_label(plan["tz"])
    p = lambda x: tc.fmt_price(x, inst)  # noqa: E731
    e = D(plan["entry"])
    risk = D(plan["risk_per_unit"])
    pct = (risk / e * 100).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    when = ""
    if plan.get("entry_time"):
        when = " at %s %s" % (plan["entry_time"], zl)
        if plan.get("entry_bar") is not None:
            when += " (bar %d)" % plan["entry_bar"]
    out = ["Exit plan: %s %s, %s, %s on %s bars" % (
        plan["symbol"], plan["direction"], day.strftime("%a %Y-%m-%d"), setup,
        {"5m": "5-minute", "1m": "1-minute", "15m": "15-minute"}[plan["interval"]])]
    out.append("  Entry         %s%s" % (p(plan["entry"]), when))
    out.append("  Stop          %s  %s%s" % (p(plan["stop"]), plan["stop_label"],
                                             (": " + plan["stop_detail"]) if plan.get("stop_detail") else ""))
    out.append("  Target        %s  %s" % (p(plan["target"]), plan["target_label"]))
    out.append("  Risk a unit   %s = %s (%s%% of the entry)" % (
        tc.num(D(plan["risk_per_unit"])), tc.fmt_dist(plan["risk_per_unit"], inst), pct))
    out.append("  Reward        %s" % tc.fmt_dist(D(plan["reward_pips"]) * D(inst["pip"]), inst))
    out.append("  Reward:risk   %s" % ratio(plan["reward_risk"]))
    out.append("  Flat by       %s %s, win or lose: no overnight or weekend hold" % (plan["flat_by"], zl))
    out.append("Set before the entry. If price hits the stop, you are out; never move it further away.")
    out.append(NOTE)
    return out


def cmd_plan(a):
    cfg = tc.load_config(a.config)
    now = tc.parse_now(a.now, cfg["timezone"])
    inst, plan, warnings = build_plan(a, now, cfg)
    if a.write:
        tc.write_json(a.write, plan)
    if a.json:
        print(json.dumps(dict(plan, warnings=warnings), indent=2))
        return 0
    for line in describe(plan, inst):
        print(line)
    for w in warnings:
        print("Note: " + w)
    if a.write:
        print("Wrote %s." % a.write)
    print("Next: /trader-timemachine replays it, then /trader-budget sizes it to your max loss. Nothing was placed.")
    return 0


def cmd_show(a):
    cfg = tc.load_config(a.config)
    if not os.path.exists(a.plan):
        print("No plan at %s yet. Make one: exit.py plan --write" % a.plan)
        return 1
    plan = tc.read_json(a.plan, "plan")
    for k in ("symbol", "side", "date", "entry", "stop", "target", "risk_per_unit", "reward_risk", "flat_by",
              "session", "tz"):
        if plan.get(k) is None:
            raise PlanError("%s is missing %r: make a new plan with exit.py plan --write" % (a.plan, k))
    inst = tc.resolve(plan["symbol"], cfg)
    if a.json:
        print(json.dumps(plan, indent=2))
        return 0
    for line in describe(dict({"setup": "range", "interval": "5m", "stop_label": "", "target_label": ""}, **plan), inst):
        print(line)
    today = tc.to_local(plan["tz"], tc.parse_now(a.now, plan["tz"])).date().isoformat()
    if plan["date"] != today:
        print("Note: this plan is for %s, not today (%s)." % (plan["date"], today))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Exit Planner (trader-exit): the stop and target before the entry.")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("plan", help="set the stop and target")
    p.add_argument("--from", dest="from_path", metavar="PATH", help="entry.json to plan from (default trader/entry.json)")
    p.add_argument("--symbol")
    p.add_argument("--side", help="buy/long or sell/short (default: the entry's)")
    p.add_argument("--entry", type=float, help="entry price (or a plan-ahead price with --from)")
    p.add_argument("--range-high", "--or-high", dest="range_high", type=float)
    p.add_argument("--range-low", "--or-low", dest="range_low", type=float)
    p.add_argument("--range-minutes", "--or-minutes", dest="range_minutes", type=int)
    p.add_argument("--setup", choices=["range", "level"])
    p.add_argument("--session", help="the session (default: the entry's, or the instrument's)")
    p.add_argument("--date", help="session date YYYY-MM-DD (default: the entry's, or today)")
    p.add_argument("--time", help="entry time HH:MM, session-local (the trigger bar's close)")
    p.add_argument("--entry-bar", type=int)
    p.add_argument("--interval", choices=list(tc.INTERVALS))
    p.add_argument("--stop", help="range-mid (range default), range-far, price:X, pct:X, pips:N, atr:K")
    p.add_argument("--target", help="2R (default), 1R, 1.5R, pips:N, price:X")
    p.add_argument("--flat-by", help="HH:MM in the session's zone (default: close minus flat_by_minutes)")
    p.add_argument("--config", default="trader/config.json")
    p.add_argument("--offline", metavar="PATH", help="saved Yahoo chart JSON or folder, for an atr stop")
    p.add_argument("--now", help='pretend it is this time, e.g. "2026-11-16 08:45 London"')
    p.add_argument("--write", nargs="?", const="trader/plan.json", metavar="PATH",
                   help="save the plan (default trader/plan.json)")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("show", help="print the current plan")
    p.add_argument("--plan", default="trader/plan.json")
    p.add_argument("--config", default="trader/config.json")
    p.add_argument("--now")
    p.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        return {"plan": cmd_plan, "show": cmd_show}[a.cmd](a)
    except tc.TraderError as e:
        print("exit.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
