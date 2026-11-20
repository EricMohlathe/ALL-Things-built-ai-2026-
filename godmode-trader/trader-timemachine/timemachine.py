#!/usr/bin/env python3
"""Time Machine for trader-timemachine. Standard library only.

Replays a planned day trade on any forex pair, commodity, index or coin before
you risk a cent: 10,000 simulated runs of the rest of the session from your
entry, plus the same rule on every past session in the data. Long or short.

    python3 timemachine.py run                          # trader/plan.json, 10,000 replays, seed 19
    python3 timemachine.py run --write                  # also save trader/timemachine.json
    python3 timemachine.py run --until close            # hold to the session close instead of flat_by
    python3 timemachine.py run --seed 7 --replays 20000 --json
    python3 timemachine.py run --symbol XAUUSD --side sell --session comex --date 2026-11-16 \\
        --entry 4053.20 --stop 4058.75 --target 4042.10 --entry-time 08:50
    python3 timemachine.py chart                        # ASCII fan chart of the replays

How the replays work:
  1. Fetch 60 days of 5-minute bars (one Yahoo request, range=60d). Keep only
     FULL sessions of the plan's session before the plan's date: every bar
     from the open to the close in the session's own time zone (London 08:00
     to 17:00 is 108 bars, US cash 78, the crypto UTC day 288). Half days are
     left out. Forex and crypto feeds may skip up to 3 quiet bars a session;
     those are filled flat at the previous close and counted.
  2. The pool: for every bar slot 1..N-1 of the session, each past session's
     bar as ratios to the previous bar's close: (open, high, low, close) / prev.
  3. One replay starts at the entry price and walks the rest of the session.
     For bar i it picks slot j = i + randint(-window, window), kept in 1..N-1,
     then one past bar from pool[j] (random.choice), scaled to the current
     price. The stop is checked before the target in every bar, so a bar that
     touches both counts as the stop (the conservative call).
  4. Outcomes: "target" or "stop" (whichever first), or "neither" when the
     trade is still open at --until (default: the plan's flat_by). "green" =
     target first, or on the right side of the entry at --until. R = the
     target's R at the target, -1 at the stop, else the move at --until / risk.
  5. The price at --until: median and 5th to 95th percentile. The fan chart
     uses a second run of 2,000 paths, same seed.
  6. History: the plan's own rule (a range breakout with the same range length,
     side, stop rule and target R) re-run on every one of those past sessions,
     first close beyond the range inside the entry window = the entry.

The verdict compares the target's share of the replays that hit a side,
target / (target + stop), with the share that breaks even at the target's R,
1 / (1 + R): under 5 points "Close to a coin flip / break-even", 5 to 15
"Leans toward ...", 15 or more "Strongly toward ...".

Same plan, same data and same --seed give the same numbers on any machine. A
simulation built from the instrument's own recent bars is not a prediction:
central banks, data releases, weekend gaps and exchange hacks can do what the
last 60 days never did.

Data: https://query2.finance.yahoo.com/v8/finance/chart/<FEED>?range=60d&interval=5m
(unofficial and free, can lag). --offline PATH reads a saved chart instead.
"""

import argparse
import datetime
import json
import math
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "trader-core"))
import tradercore as tc  # noqa: E402

STEP = 300
MIN_SESSIONS = 20
SAMPLE_PATHS = 160
BAND_PATHS = 2000
BAND_Q = (0.05, 0.25, 0.5, 0.75, 0.95)
HIST_BINS = 24
COIN_FLIP = 0.05
STRONG = 0.15
MANY_NEITHER = 0.40
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


class TMError(tc.TraderError):
    pass


# ---------------------------------------------------------------- sessions from the data

def session_rows(by_ts, sinst, tolerance=0):
    """[bar per slot] of one session instance from {ts: bar}, or (None, missing) when not full."""
    sl = tc.slots(sinst, STEP)
    bars = []
    for i, s in enumerate(sl):
        b = by_ts.get(tc.ts_of(s))
        if b is not None:
            start = tc.utc_of(b["t"])
            bars.append(dict(b, slot=i, start=start, end=start + datetime.timedelta(seconds=STEP)))
    full, missing = tc.fill_gaps(bars, len(sl) - 1, tolerance)
    return full, missing


def past_sessions(chart, sname, plan_date, n_slots, tolerance, cfg):
    """Full sessions before the plan's date, oldest first, and the ones left out."""
    by_ts = {b["t"]: b for b in chart["bars"] if b["t"] % STEP == 0}
    if not by_ts:
        return [], [], 0
    tz = tc.session_def(sname, cfg)["tz"]
    first = tc.to_local(tz, tc.utc_of(min(by_ts))).date()
    end = datetime.date.fromisoformat(plan_date)
    full, short, filled = [], [], 0
    d = first
    while d < end:
        sinst = tc.session_instance(sname, d, cfg)
        if sinst is not None:
            rows, missing = session_rows(by_ts, sinst, tolerance)
            if rows is not None and len(rows) == n_slots:
                full.append((d.isoformat(), rows))
                filled += missing
            else:
                have = sum(1 for s in tc.slots(sinst, STEP) if tc.ts_of(s) in by_ts)
                if have:
                    short.append({"date": d.isoformat(), "bars": have,
                                  "why": "half day" if sinst["early"] else "missing bars"})
        d += datetime.timedelta(days=1)
    return full, short, filled


# ---------------------------------------------------------------- the simulation

def build_pool(sessions, n):
    """pool[i] = every past session's bar i as (o, h, l, c) / bar i-1's close, in date order."""
    pool = [[] for _ in range(n)]
    for _, rows in sessions:
        for i in range(1, n):
            pc = rows[i - 1]["c"]
            pool[i].append((rows[i]["o"] / pc, rows[i]["h"] / pc, rows[i]["l"] / pc, rows[i]["c"] / pc))
    return pool


def pct(a, q):
    return a[min(len(a) - 1, int(q * len(a)))]


def simulate(pool, entry, stop, target, k, last, replays=10000, seed=19, window=2, side="buy", digits=2):
    """Monte Carlo replays of bars k+1..last."""
    n = len(pool)
    long = side == "buy"
    risk = (entry - stop) if long else (stop - entry)
    r_target = round(((target - entry) if long else (entry - target)) / risk, 4)

    def slot(rng, i):
        return i if window == 0 else min(n - 1, max(1, i + rng.randint(-window, window)))
    rng = random.Random(seed)
    choice = rng.choice
    outcomes, closes, paths = [], [], []
    for r in range(replays):
        p = entry
        outcome = None
        keep = r < SAMPLE_PATHS
        path = [entry]
        for i in range(k + 1, last + 1):
            o, h, l, c = choice(pool[slot(rng, i)])
            hi, lo, cl = p * h, p * l, p * c
            if outcome is None:
                if long:
                    if lo <= stop:
                        outcome = "stop"
                    elif hi >= target:
                        outcome = "target"
                else:
                    if hi >= stop:
                        outcome = "stop"
                    elif lo <= target:
                        outcome = "target"
            p = cl
            if keep:
                path.append(round(p, digits))
        outcomes.append(outcome or "close")
        closes.append(p)
        if keep:
            paths.append(path)
    cnt = {x: outcomes.count(x) for x in ("target", "stop", "close")}
    green = sum(1 for o, p in zip(outcomes, closes)
                if o == "target" or (o == "close" and (p > entry if long else p < entry)))
    Rs = [r_target if o == "target" else -1.0 if o == "stop" else ((p - entry) if long else (entry - p)) / risk
          for o, p in zip(outcomes, closes)]
    srt = sorted(closes)
    rng = random.Random(seed)
    choice = rng.choice
    allp = []
    for _ in range(BAND_PATHS):
        p = entry
        path = [entry]
        for i in range(k + 1, last + 1):
            o, h, l, c = choice(pool[slot(rng, i)])
            p = p * c
            path.append(p)
        allp.append(path)
    bands = []
    for j in range(last - k + 1):
        col = sorted(pp[j] for pp in allp)
        bands.append([round(pct(col, q), digits) for q in BAND_Q])
    lo_, hi_ = pct(srt, 0.01), pct(srt, 0.99)
    W = (hi_ - lo_) / HIST_BINS
    bins = [0] * HIST_BINS
    for c in srt:
        b = int((c - lo_) / W) if W > 0 else 0
        if 0 <= b < HIST_BINS:
            bins[b] += 1
    return {
        "replays": replays, "seed": seed, "window": window, "bars_left": last - k,
        "p_target": round(cnt["target"] / float(replays), 4), "p_stop": round(cnt["stop"] / float(replays), 4),
        "p_neither": round(cnt["close"] / float(replays), 4), "p_green": round(green / float(replays), 4),
        "median_close": round(pct(srt, 0.5), digits), "p5_close": round(pct(srt, 0.05), digits),
        "p95_close": round(pct(srt, 0.95), digits), "avg_R": round(statistics.mean(Rs), 3),
        "r_at_target": r_target, "band_paths": BAND_PATHS, "bands": bands, "sample_paths": paths,
        "hist": {"lo": round(lo_, digits), "hi": round(hi_, digits), "bins": bins},
    }


# ---------------------------------------------------------------- the history replay

def away(x, inst, long):
    return float(tc.stop_tick(x, inst["tick"], long))


def rule_stop(rule, oh, ol, entry, long, inst):
    r = rule["stop_rule"]
    if r == "range_mid":
        return away((oh + ol) / 2.0, inst, long)
    if r == "range_far":
        return away(ol if long else oh, inst, long)
    if r == "pips":
        d = rule["stop_pips"] * inst["pip"]
        return away(entry - d if long else entry + d, inst, long)
    frac = rule["stop_pct"] / 100.0
    return away(entry * (1 - frac) if long else entry * (1 + frac), inst, long)


def history_replay(sessions, rule, last, last_entry, inst, side="buy"):
    """The plan's rule on every past full session."""
    long = side == "buy"
    n = rule["range_bars"]
    trades = []
    for d, rows in sessions:
        oh = max(b["h"] for b in rows[:n])
        ol = min(b["l"] for b in rows[:n])
        kk = next((i for i in range(n, min(last_entry, last) + 1)
                   if (rows[i]["c"] > oh if long else rows[i]["c"] < ol)), None)
        if kk is None:
            continue
        e = float(tc.to_tick(rows[kk]["c"], inst["tick"]))
        s = rule_stop(rule, oh, ol, e, long, inst)
        risk = (e - s) if long else (s - e)
        if risk <= 0:
            continue
        t = float(tc.to_tick(e + rule["target_r"] * risk if long else e - rule["target_r"] * risk, inst["tick"]))
        oc = None
        for b in rows[kk + 1:last + 1]:
            if (b["l"] <= s) if long else (b["h"] >= s):
                oc = "stop"
                break
            if (b["h"] >= t) if long else (b["l"] <= t):
                oc = "target"
                break
        cl = rows[last]["c"]
        R = ((t - e) if long else (e - t)) / risk if oc == "target" else -1.0 if oc == "stop" else \
            ((cl - e) if long else (e - cl)) / risk
        trades.append({"date": d, "time": tc.hm(tc.to_local(rule["tz"], rows[kk]["end"])), "entry": e, "stop": s,
                       "target": t, "outcome": oc or "close", "R": round(R, 2)})
    return {
        "sessions": len(sessions), "triggered": len(trades),
        "target": sum(1 for x in trades if x["outcome"] == "target"),
        "stop": sum(1 for x in trades if x["outcome"] == "stop"),
        "close": sum(1 for x in trades if x["outcome"] == "close"),
        "green": sum(1 for x in trades if x["R"] > 0),
        "avg_R": round(statistics.mean(x["R"] for x in trades), 3) if trades else None,
        "rule": rule, "trades": trades,
    }


# ---------------------------------------------------------------- the plan

def _num(v, what):
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise TMError("the plan needs a number for %s, got %r" % (what, v))
    if not x > 0 or math.isinf(x):
        raise TMError("the plan's %s must be a positive price, got %r" % (what, v))
    return x


def load_plan(a, cfg, now_utc):
    if a.symbol:
        missing = [f for f in ("entry", "stop", "target", "entry_time") if getattr(a, f) is None]
        if missing:
            raise TMError("with --symbol also give %s" % ", ".join("--" + m.replace("_", "-") for m in missing))
        inst = tc.resolve(a.symbol, cfg)
        sname = a.session or inst["session"]
        tz = tc.session_def(sname, cfg)["tz"]
        raw = {"symbol": inst["symbol"], "side": a.side, "date": a.date or tc.to_local(tz, now_utc).date().isoformat(),
               "entry": a.entry, "stop": a.stop, "target": a.target, "entry_time": a.entry_time, "session": sname,
               "setup": a.setup, "opening_range": {"minutes": a.range_minutes} if a.range_minutes else None,
               "stop_rule": a.stop_rule, "interval": "5m"}
        src = "flags"
    else:
        raw = tc.read_json(a.plan, "plan (run /trader-exit first, or pass --symbol --date --entry --stop --target "
                                   "--entry-time)")
        if not isinstance(raw, dict):
            raise TMError("%s is not a plan" % a.plan)
        src = a.plan
    return normalize_plan(raw, cfg, src)


def normalize_plan(raw, cfg, src="flags"):
    inst = tc.resolve(raw.get("symbol"), cfg)
    side = tc.side_word(raw.get("side") or "buy")
    if str(raw.get("interval") or "5m") != "5m":
        raise TMError("5-minute bars only: Yahoo keeps 60 days of 5-minute bars, enough sessions for a fair pool")
    sname = raw.get("session") or inst["session"]
    sinst = tc.instance_on(sname, raw.get("date"), cfg)
    tz = sinst["tz"]
    entry, stop, target = (_num(raw.get(k), k) for k in ("entry", "stop", "target"))
    long = side == "buy"
    if long and not stop < entry < target:
        raise TMError("a buy needs stop < entry < target (got stop %s, entry %s, target %s)" % (stop, entry, target))
    if not long and not target < entry < stop:
        raise TMError("a sell needs target < entry < stop (got target %s, entry %s, stop %s)" % (target, entry, stop))
    sl = tc.slots(sinst, STEP)
    ends = {tc.hm(tc.to_local(tz, s + datetime.timedelta(seconds=STEP))): i for i, s in enumerate(sl)}
    k = None
    if raw.get("entry_time"):
        key = str(raw["entry_time"]).strip()[:5].zfill(5)
        if key not in ends:
            raise TMError("entry_time %s is not the close of a 5-minute bar in the %s on %s"
                          % (raw["entry_time"], sinst["label"], sinst["date"]))
        k = ends[key]
    if raw.get("entry_bar") is not None:
        kb = int(raw["entry_bar"])
        if k is not None and kb != k:
            raise TMError("the plan disagrees with itself: entry_bar %d but entry_time %s is bar %d"
                          % (kb, raw["entry_time"], k))
        k = kb
    if k is None:
        raise TMError("the plan needs entry_time (the trigger bar's close, session-local) or entry_bar")
    if not 0 <= k <= len(sl) - 2:
        raise TMError("the entry must leave at least one bar of the session to replay")
    orng = raw.get("opening_range") or {}
    rmin = int(orng.get("minutes") or tc.session_def(sname, cfg)["range"])
    risk = (entry - stop) if long else (stop - entry)
    return {
        "symbol": inst["symbol"], "class": inst["class"], "side": side, "date": sinst["date"], "session": sname,
        "tz": tz, "setup": str(raw.get("setup") or "range"), "entry": entry,
        "entry_time": tc.hm(tc.to_local(tz, sl[k] + datetime.timedelta(seconds=STEP))), "entry_bar": k,
        "stop": stop, "target": target, "risk_per_unit": round(risk, inst["digits"] + 2),
        "risk_pips": round(tc.pips(risk, inst), 2),
        "target_r": round(((target - entry) if long else (entry - target)) / risk, 2),
        "opening_range": dict(orng, minutes=rmin), "stop_rule": str(raw.get("stop_rule") or "auto"),
        "interval": "5m", "flat_by": raw.get("flat_by"), "flat_by_utc": raw.get("flat_by_utc"), "from": src,
    }


def resolve_rule(plan, entry_rows, inst, tz):
    """The rule the history replay uses: a range breakout, the plan's range length, its stop
    rule (range_mid, range_far, pips, or 'pct' = the plan's stop distance as a percent of
    the entry) and its target R. 'auto' works the rule out from the plan day's own range."""
    if plan["setup"].lower() != "range":
        return None
    long = plan["side"] == "buy"
    n = plan["opening_range"]["minutes"] * 60 // STEP
    rule = {"setup": "range", "range_minutes": plan["opening_range"]["minutes"], "range_bars": n,
            "stop_rule": plan["stop_rule"], "target_r": plan["target_r"], "tz": tz,
            "stop_pct": round(100.0 * plan["risk_per_unit"] / plan["entry"], 5),
            "stop_pips": plan["risk_pips"]}
    if rule["stop_rule"] in ("auto", "price", "atr", "level"):
        rule["stop_rule"] = "pct"
        if all(i in entry_rows for i in range(n)):
            oh = max(entry_rows[i]["h"] for i in range(n))
            ol = min(entry_rows[i]["l"] for i in range(n))
            half = inst["tick"] / 2.0
            if abs(away((oh + ol) / 2.0, inst, long) - plan["stop"]) < half:
                rule["stop_rule"] = "range_mid"
            elif abs(away(ol if long else oh, inst, long) - plan["stop"]) < half:
                rule["stop_rule"] = "range_far"
    elif rule["stop_rule"] not in ("range_mid", "range_far", "pips", "pct"):
        rule["stop_rule"] = "pct"
    if rule["stop_rule"] != "pct":
        del rule["stop_pct"]
    if rule["stop_rule"] != "pips":
        del rule["stop_pips"]
    return rule


# ---------------------------------------------------------------- the run

def lean(mc):
    pt, ps = mc["p_target"], mc["p_stop"]
    if pt + ps <= 0:
        return None
    r = mc.get("r_at_target") or 1.0
    share, even = pt / (pt + ps), 1.0 / (1.0 + r)
    return share - even, share, even


def verdict(mc):
    pt, ps = mc["p_target"], mc["p_stop"]
    lv = lean(mc)
    until = mc.get("until_label", mc.get("until"))
    if lv is None:
        return "No replay reached the target or the stop by %s: the price at %s decides every one." % (until, until)
    d, share, even = lv
    r = mc.get("r_at_target") or 1.0
    one_r = abs(r - 1.0) < 0.005
    if abs(d) < COIN_FLIP:
        head = "Close to a coin flip" if one_r else "Close to break-even"
    elif abs(d) < STRONG:
        head = "Leans toward the target" if d > 0 else "Leans toward the stop"
    else:
        head = "Strongly toward the target" if d > 0 else "Strongly toward the stop"
    odds = "target first %.1f %% vs stop first %.1f %%" % (100 * pt, 100 * ps)
    if one_r:
        return "%s: %s." % (head, odds)
    return ("%s: at %gR the target has to come first in %.0f %% of the replays that hit one side; "
            "it did in %.0f %% (%s)." % (head, round(r, 2), 100 * even, 100 * share, odds))


def verdict_notes(mc):
    notes = []
    until = mc.get("until_label", mc.get("until"))
    pn = mc.get("p_neither", 0)
    if pn > MANY_NEITHER and lean(mc) is not None:
        notes.append("%.1f %% of the replays hit neither by %s; the price at %s decides those." % (100 * pn, until, until))
    lv = lean(mc)
    avg = mc.get("avg_R")
    if lv and abs(lv[0]) >= COIN_FLIP and avg is not None and avg != 0 and (avg > 0) != (lv[0] > 0):
        notes.append("Average R is %+.3f all the same: the replays that hit neither pull it the other way." % avg)
    return notes


def time_machine(chart, plan, inst, cfg, now_utc, replays=10000, seed=19, window=2, until=None, source="yahoo"):
    if not 1 <= replays <= 1000000:
        raise TMError("--replays must be between 1 and 1,000,000")
    if not 0 <= window <= 10:
        raise TMError("--window must be between 0 and 10 bars")
    sname, tz = plan["session"], plan["tz"]
    sinst = tc.instance_on(sname, plan["date"], cfg)
    sl = tc.slots(sinst, STEP)
    n = len(sl)
    k = plan["entry_bar"]
    win = tc.windows(sinst, cfg, plan["opening_range"]["minutes"])
    def local_hhmm(text, what):
        t = datetime.datetime.combine(sinst["open_local"].date(), datetime.time()) + \
            datetime.timedelta(minutes=tc.parse_hhmm(text, what))
        return tc.to_utc(tz, t + datetime.timedelta(days=1) if t < sinst["open_local"] else t)
    if until == "close":
        until_utc = sinst["close_utc"]
    elif until not in (None, "", "flat_by", "flat-by"):
        until_utc = local_hhmm(until, "--until")
    elif plan.get("flat_by_utc"):
        until_utc = tc.parse_utc(plan["flat_by_utc"])
    elif plan.get("flat_by"):
        until_utc = local_hhmm(plan["flat_by"], "the plan's flat_by")
    else:
        until_utc = win["flat_by"]
    ends = [s + datetime.timedelta(seconds=STEP) for s in sl]
    done = [i for i, e in enumerate(ends) if e <= until_utc]
    if not done or until_utc > sinst["close_utc"]:
        raise TMError("--until must fall inside the %s (%s to %s %s)" % (
            sinst["label"], tc.hm(sinst["open_local"]), tc.hm(sinst["close_local"]), tc.zone_label(tz)))
    last = done[-1]
    if last <= k:
        raise TMError("--until %s leaves nothing to replay after the %s entry" % (
            tc.hm(tc.to_local(tz, until_utc)), plan["entry_time"]))
    by_ts = {b["t"]: b for b in chart["bars"] if b["t"] % STEP == 0}
    as_of = now_utc
    if chart.get("data_time") and tc.utc_of(chart["data_time"]) < as_of:
        as_of = tc.utc_of(chart["data_time"])
    entry_rows = {}
    for i, s in enumerate(sl):
        b = by_ts.get(tc.ts_of(s))
        if b and s + datetime.timedelta(seconds=STEP) <= as_of:
            entry_rows[i] = dict(b, slot=i, start=s, end=s + datetime.timedelta(seconds=STEP))
    if k not in entry_rows:
        raise TMError("the entry is not in the data: no complete bar closing %s %s on %s for %s"
                      % (plan["entry_time"], tc.zone_label(tz), plan["date"], plan["symbol"]))
    warn = []
    eb = entry_rows[k]
    slack = inst["tick"] * 2
    if not eb["l"] - slack <= plan["entry"] <= eb["h"] + slack:
        warn.append("the plan's entry %s is outside that bar's range %s to %s" % (
            tc.fmt_price(plan["entry"], inst), tc.fmt_price(eb["l"], inst), tc.fmt_price(eb["h"], inst)))
    sessions, short, filled = past_sessions(chart, sname, plan["date"], n, inst.get("gap_tolerance", 0), cfg)
    if len(sessions) < MIN_SESSIONS:
        raise TMError("only %d full %s session(s) of %s before %s in the data; the time machine needs at least %d"
                      % (len(sessions), sname, plan["symbol"], plan["date"], MIN_SESSIONS))
    pool = build_pool(sessions, n)
    digits = inst["digits"]
    mc = simulate(pool, plan["entry"], plan["stop"], plan["target"], k, last, replays, seed, window, plan["side"],
                  digits)
    until_local = tc.hm(tc.to_local(tz, ends[last]))
    mc = dict(mc, until=until_local, until_label="%s %s" % (until_local, tc.zone_label(tz)), until_utc=tc.iso(ends[last]),
              pool_sessions=len(sessions), pool_from=sessions[0][0], pool_to=sessions[-1][0], filled_bars=filled,
              band_times=[tc.hm(tc.to_local(tz, ends[j])) for j in range(k, last + 1)])
    rule = resolve_rule(plan, entry_rows, inst, tz)
    plan_out = {kk: v for kk, v in plan.items() if v is not None}
    if rule:
        plan_out["stop_rule"] = rule["stop_rule"]
        last_entry = max(i for i, e in enumerate(ends) if e <= win["no_entries_after"])
        history = history_replay(sessions, rule, last, last_entry, inst, plan["side"])
    else:
        history = {"sessions": len(sessions), "triggered": 0, "rule": None, "trades": [],
                   "note": "skipped: the history replay knows the range breakout only, this plan's setup is %r"
                           % plan["setup"]}
    last_bar = chart["bars"][-1] if chart["bars"] else None
    return {
        "created_by": "trader-timemachine", "created_at": tc.iso(now_utc), "source": source,
        "data": {"symbol": plan["symbol"], "feed": inst["feed"], "interval": "5m", "range": "60d",
                 "last_bar": tc.stamp(tc.utc_of(last_bar["t"]), tz) if last_bar else None,
                 "session_bars": n, "short_sessions_left_out": short},
        "plan": plan_out, "mc": mc, "history": history, "verdict": verdict(mc), "verdict_notes": verdict_notes(mc),
        "warnings": warn,
        "note": ("A simulation built from %s's own last %d full %s sessions. It is not a prediction: central banks, "
                 "data releases, weekend gaps and hacks can do things those sessions never did. Same seed, same "
                 "numbers." % (plan["symbol"], len(sessions), sname)),
    }


# ---------------------------------------------------------------- output

def pc(x):
    return "%.1f %%" % (100.0 * x)


def report(doc, inst):
    p, m, h = doc["plan"], doc["mc"], doc["history"]
    long = p["side"] == "buy"
    fp = lambda x: tc.fmt_price(x, inst)  # noqa: E731
    zl = tc.zone_label(p["tz"])
    wd = WEEKDAYS[datetime.date.fromisoformat(p["date"]).weekday()]
    lines = [
        "%s %s, %s %s, %s: entry %s at %s %s (bar %d), stop %s, target %s (%gR, risk %s)."
        % (p["symbol"], "long" if long else "short", wd, p["date"], p["session"], fp(p["entry"]), p["entry_time"],
           zl, p["entry_bar"], fp(p["stop"]), fp(p["target"]), p["target_r"], tc.fmt_dist(p["risk_per_unit"], inst)),
        "%s replays of the rest of the session, %s to %s %s (%d five-minute bars), seed %d."
        % ("{:,}".format(m["replays"]), p["entry_time"], m["until"], zl, m["bars_left"], m["seed"]),
        "Each bar is drawn whole from %s's own 5-min bars at the same time of the %s session (+-%d bars) over its "
        "last %d full sessions (%s to %s)%s." % (
            p["symbol"], p["session"], m["window"], m["pool_sessions"], m["pool_from"], m["pool_to"],
            ("; %d quiet bars filled flat" % m["filled_bars"]) if m.get("filled_bars") else ""),
        "",
        "  target first   %s" % pc(m["p_target"]),
        "  stop first     %s" % pc(m["p_stop"]),
        "  neither        %-8s still open at %s" % (pc(m["p_neither"]), m["until"]),
        "  green          %-8s target first, or %s the entry at %s" % (pc(m["p_green"]), "above" if long else "below",
                                                                       m["until"]),
        "",
        "  Price at %s: median %s, 90 %% of replays between %s and %s." % (
            m["until"], fp(m["median_close"]), fp(m["p5_close"]), fp(m["p95_close"])),
        "  Average R: %+.3f (R = the %s risk: +%gR at the target, -1R at the stop)." % (
            m["avg_R"], tc.fmt_dist(p["risk_per_unit"], inst), m["r_at_target"]),
        "",
    ]
    if h.get("rule"):
        ru = h["rule"]
        stop_words = {"range_mid": "range midpoint", "range_far": "far side of the range",
                      "pips": "%s %s from the entry" % (ru.get("stop_pips"), inst["pip_label"])}.get(
            ru["stop_rule"], "%.3f %% from the entry" % ru.get("stop_pct", 0))
        if h["triggered"]:
            lines.append("History: the same rule (%d-min range, %s side, stop at the %s, %gR target) on each of "
                         "those %d real sessions fired %d times: %d target, %d stop, %d neither. Average R %+.3f."
                         % (ru["range_minutes"], "long" if long else "short", stop_words, ru["target_r"],
                            h["sessions"], h["triggered"], h["target"], h["stop"], h["close"], h["avg_R"]))
        else:
            lines.append("History: the same rule never fired in those %d sessions." % h["sessions"])
    else:
        lines.append("History: " + h.get("note", "skipped."))
    lines += ["", doc["verdict"]] + list(doc.get("verdict_notes") or []) + [""]
    for w in doc.get("warnings") or []:
        lines.append("Note: " + w + ".")
    left = doc["data"]["short_sessions_left_out"]
    if left:
        lines.append("Left out %d short session(s) (half days or gaps): %s." % (
            len(left), ", ".join(x["date"] for x in left[:8]) + (" ..." if len(left) > 8 else "")))
    lines.append(doc["note"] + " Repeat this run with --seed %d." % m["seed"])
    return lines


def render_chart(doc, inst, height=17):
    p, m = doc["plan"], doc["mc"]
    bands, times = m["bands"], m["band_times"]
    stride = max(1, int(math.ceil(len(bands) / 96.0)))
    bands, times = bands[::stride], times[::stride]
    lo = min([b[0] for b in bands] + [p["stop"], p["target"]])
    hi = max([b[4] for b in bands] + [p["stop"], p["target"]])
    pad = (hi - lo) * 0.04 or inst["tick"]
    lo, hi = lo - pad, hi + pad
    step = (hi - lo) / (height - 1)

    def row(price):
        return max(0, min(height - 1, int(round((hi - price) / step))))
    grid = [[" "] * len(bands) for _ in range(height)]
    for j, b in enumerate(bands):
        r5, r25, r50, r75, r95 = [row(x) for x in b]
        for r in range(r95, r5 + 1):
            grid[r][j] = "."
        for r in range(r75, r25 + 1):
            grid[r][j] = ":"
        grid[r50][j] = "*"
    marks = {row(p["target"]): "target", row(p["stop"]): "stop"}
    if row(p["entry"]) not in marks:
        marks[row(p["entry"])] = "entry"
    for r in (row(p["target"]), row(p["stop"])):
        grid[r] = ["-" if ch == " " else ch for ch in grid[r]]
    w = max(len(tc.fmt_price(hi, inst)), len(tc.fmt_price(lo, inst))) + 1
    out = ["%s %s, %s replay paths from the %s %s entry (seed %d)%s" % (
        p["symbol"], p["date"], "{:,}".format(m.get("band_paths", BAND_PATHS)), p["entry_time"],
        tc.zone_label(p["tz"]), m["seed"], (", one column per %d bars" % stride) if stride > 1 else "")]
    for r in range(height):
        label = marks.get(r)
        price = {"target": p["target"], "stop": p["stop"], "entry": p["entry"]}.get(label, hi - r * step)
        left = (("%" + str(w) + "s |") % tc.fmt_price(price, inst)) if (label or r in (0, height - 1)) else \
            " " * w + " |"
        out.append(left + "".join(grid[r]) + ("  " + label if label else ""))
    axis = [" "] * len(bands)
    for j in sorted({0, len(bands) // 2, len(bands) - 1}):
        lab = times[j]
        s = max(0, min(j, len(bands) - len(lab)))
        axis[s:s + len(lab)] = list(lab)
    out.append(" " * w + " +" + "-" * len(bands))
    out.append(" " * (w + 2) + "".join(axis))
    out.append("* median   : middle half of the paths   . 90 % of the paths   - stop and target")
    return out


# ---------------------------------------------------------------- commands

def compute(a):
    cfg = tc.load_config(a.config)
    now = tc.parse_now(a.now, cfg["timezone"])
    plan = load_plan(a, cfg, now)
    inst = tc.resolve(plan["symbol"], cfg)
    if a.offline:
        chart = tc.get_chart(inst, "5m", offline=a.offline, tag="60d5m")
        source = chart["source"]
    else:
        chart = tc.get_chart(inst, "5m", "60d")
        source = "yahoo"
    return time_machine(chart, plan, inst, cfg, now, a.replays, a.seed, a.window, a.until, source), inst


def cmd_run(a):
    doc, inst = compute(a)
    if a.write:
        tc.write_json(a.write, doc, indent=1)
    if a.json:
        slim = dict(doc, mc={k: v for k, v in doc["mc"].items() if k != "sample_paths"})
        print(json.dumps(slim, indent=2))
    else:
        print("\n".join(report(doc, inst)))
        if a.write:
            print("Wrote %s." % a.write)
        print("Next: /trader-budget sizes it to your account and your max loss per trade.")
    return 0


def cmd_chart(a):
    if a.from_file:
        doc = tc.read_json(a.from_file, "time machine result (run timemachine.py run --write first)")
        try:
            doc["mc"]["bands"]
        except (KeyError, TypeError):
            raise TMError("%s is not a time machine result" % a.from_file)
        inst = tc.resolve(doc["plan"]["symbol"], tc.load_config(a.config))
    else:
        doc, inst = compute(a)
    print("\n".join(render_chart(doc, inst)))
    print("\n".join([doc.get("verdict", "")] + list(doc.get("verdict_notes") or [])))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Time Machine: replay a planned day trade (trader-timemachine).")
    sub = ap.add_subparsers(dest="cmd")

    def common(p):
        p.add_argument("--plan", default="trader/plan.json", help="the plan from trader-exit")
        p.add_argument("--config", default="trader/config.json")
        p.add_argument("--symbol", help="or give the plan as flags")
        p.add_argument("--side", default="buy", help="buy/long or sell/short")
        p.add_argument("--session", help="the session (default: the instrument's)")
        p.add_argument("--date", help="the plan's session date, YYYY-MM-DD")
        p.add_argument("--entry", type=float)
        p.add_argument("--stop", type=float)
        p.add_argument("--target", type=float)
        p.add_argument("--entry-time", help="the trigger bar's close, session-local HH:MM")
        p.add_argument("--setup", default="range")
        p.add_argument("--range-minutes", type=int)
        p.add_argument("--stop-rule", default="auto", choices=["auto", "range_mid", "range_far", "pips", "pct"])
        p.add_argument("--replays", type=int, default=10000)
        p.add_argument("--seed", type=int, default=19)
        p.add_argument("--window", type=int, default=2, help="draw from the same time of day +- this many bars")
        p.add_argument("--until", help="HH:MM session-local, 'close', or 'flat_by' (the default)")
        p.add_argument("--offline", metavar="PATH", help="a saved Yahoo chart JSON or a folder, no network")
        p.add_argument("--now", help='pretend it is this time, e.g. "2026-11-16 09:00 London"')

    p = sub.add_parser("run", help="replay the plan: 10,000 simulated sessions plus the history")
    common(p)
    p.add_argument("--json", action="store_true")
    p.add_argument("--write", nargs="?", const="trader/timemachine.json", metavar="PATH")
    p = sub.add_parser("chart", help="ASCII fan chart of the replays")
    common(p)
    p.add_argument("--from", dest="from_file", nargs="?", const="trader/timemachine.json", metavar="PATH")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        return {"run": cmd_run, "chart": cmd_chart}[a.cmd](a)
    except tc.TraderError as e:
        print("timemachine.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
