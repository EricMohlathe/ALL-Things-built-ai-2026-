#!/usr/bin/env python3
"""Market structure for trader-structure: the SMC / ICT and order-flow read of one market,
on several timeframes at once. Standard library only.

    python3 structure.py read EURUSD                         # M15 read + H1, H4, D1 bias, levels, order flow
    python3 structure.py read XAUUSD --tf M5 --htf H1,H4      # a faster base timeframe
    python3 structure.py read BTCUSD --write                  # also save trader/structure/BTCUSD.json
    python3 structure.py levels US500                         # the key levels only, nearest first
    python3 structure.py read GBPUSD --offline tests/fixtures/charts

What it reads, as of the last CLOSED bar (nothing that had not happened yet):
  structure    swings, break of structure (BOS), change of character (CHoCH), trend per timeframe
  imbalances   open fair value gaps above and below, order blocks, breaker blocks
  liquidity    equal highs and lows (resting stops), the last sweep and whether price closed back
  location     the dealing range, premium or discount, the OTE (0.62-0.79) zones both ways
  levels       previous day and week high / low / close, the day open, the New York midnight open,
               the Asian range, round numbers
  clock        the ICT killzone and Silver Bullet window right now (New York time)
  order flow   the delta source (measured, tick rule or the CLV proxy, always labelled), CVD
               slope, volume profile (POC, VAH, VAL), VWAP z-score, divergence, absorption

The bias is a count of these facts, not a forecast. Use it to frame a plan (/trader-entry,
/trader-exit), and test any rule you take from it in /trader-lab first.
"""

import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "trader-core"))
import tradercore as tc  # noqa: E402
import history as hist  # noqa: E402
import smc  # noqa: E402
import orderflow as of  # noqa: E402
from bars import TF_NAME, tf_seconds  # noqa: E402

DAY, WEEK = 86400, 7 * 86400


def day_offset(inst):
    return 0 if inst["class"] == "crypto" else 22 * 3600


def key_levels(b, inst):
    """Previous day / week, day open, New York midnight open, Asian range, round numbers."""
    off = day_offset(inst)
    i = len(b) - 1
    t_now = b.end(i)
    out = []

    def add(name, price, why):
        if price is not None:
            out.append({"name": name, "price": price, "why": why})
    day_key = lambda t: (t - off) // DAY  # noqa: E731
    week_base = (3 if inst["class"] != "crypto" else 4) * DAY + off   # Sunday 22:00 UTC (FX) / Monday 00:00 (crypto)
    week_key = lambda t: (t - week_base) // WEEK  # noqa: E731
    today, this_week = day_key(b.t[i]), week_key(b.t[i])
    prev_day = [k for k in range(i, -1, -1) if day_key(b.t[k]) < today]
    if prev_day:
        pd = day_key(b.t[prev_day[0]])
        idx = [k for k in prev_day[:2000] if day_key(b.t[k]) == pd]
        add("PDH", max(b.h[k] for k in idx), "previous day high")
        add("PDL", min(b.l[k] for k in idx), "previous day low")
        add("PDC", b.c[idx[0]], "previous day close")
    first_today = next((k for k in range(i, -1, -1) if day_key(b.t[k]) < today), -1) + 1
    add("DO", b.o[first_today], "today's open")
    prev_week = [k for k in range(i, -1, -1) if week_key(b.t[k]) == this_week - 1]
    if prev_week:
        add("PWH", max(b.h[k] for k in prev_week), "previous week high")
        add("PWL", min(b.l[k] for k in prev_week), "previous week low")
    ny_now = tc.to_local("America/New_York", tc.utc_of(t_now))
    mid = tc.ts_of(tc.to_utc("America/New_York", datetime.datetime.combine(ny_now.date(), datetime.time())))
    k_mid = next((k for k in range(max(0, i - 3000), i + 1) if b.t[k] >= mid), None)
    if k_mid is not None:
        add("NYMO", b.o[k_mid], "New York midnight open (ICT)")
    a0 = tc.ts_of(tc.to_utc("America/New_York", datetime.datetime.combine(ny_now.date() - datetime.timedelta(days=1),
                                                                          datetime.time(20))))
    asia = [k for k in range(max(0, i - 3000), i + 1) if a0 <= b.t[k] < mid]
    if asia:
        add("ASIA_H", max(b.h[k] for k in asia), "Asian range high (20:00-00:00 New York)")
        add("ASIA_L", min(b.l[k] for k in asia), "Asian range low")
    price = b.c[i]
    seen = set()
    for every in (50, 100):
        r = smc.round_number(price, inst["pip"] * (10 if inst["class"] == "crypto" else 1), every)
        if round(r, 8) not in seen:
            seen.add(round(r, 8))
            add("RN%d" % every, r, "round number (%d-pip grid)" % every)
    for lv in out:
        lv["distance"] = lv["price"] - price
        lv["pips"] = round(tc.pips(abs(lv["distance"]), inst), 1)
        lv["side"] = "above" if lv["distance"] > 0 else "below" if lv["distance"] < 0 else "at"
    out.sort(key=lambda x: abs(x["distance"]))
    return out


def read(inst, bars, htfs, source):
    i = len(bars) - 1
    t_end = bars.end(i)
    ny = tc.to_local("America/New_York", tc.utc_of(t_end))
    base = smc.analyze(bars, ny.hour * 60 + ny.minute)
    frames = []
    for tf in htfs:
        step = tf_seconds(tf)
        if step <= bars.step:
            continue
        hb = bars.resample(tf, day_offset(inst) if step >= DAY else 0)
        if len(hb) < 30:
            frames.append({"tf": TF_NAME[step], "trend": None, "bias": None, "note": "only %d bars" % len(hb)})
            continue
        r = smc.analyze(hb)
        frames.append({"tf": TF_NAME[step], "trend": r["trend"], "bias": r["bias"], "score": r["score"],
                       "last_event": r["last_event"] and {"kind": r["last_event"]["kind"], "dir": r["last_event"]["dir"],
                                                          "level": r["last_event"]["level"]},
                       "premium_discount": r["premium_discount"]})
    keys = [(bars.t[k] - day_offset(inst)) // DAY for k in range(len(bars))]
    n = min(len(bars), 400)
    flow = of.summary(bars.slice(len(bars) - n, len(bars)), keys[-n:])
    ups = sum(1 for f in frames if f.get("trend") == "up") + (base["trend"] == "up")
    downs = sum(1 for f in frames if f.get("trend") == "down") + (base["trend"] == "down")
    total = len([f for f in frames if f.get("trend") is not None]) + (base["trend"] is not None)
    align = "aligned up" if total and ups == total else "aligned down" if total and downs == total else \
        "mixed (%d up, %d down of %d)" % (ups, downs, total)
    return {"symbol": inst["symbol"], "tf": TF_NAME[bars.step], "source": source, "as_of": tc.iso(tc.utc_of(t_end)),
            "ny_time": ny.strftime("%Y-%m-%d %H:%M"), "base": base, "frames": frames, "alignment": align,
            "levels": key_levels(bars, inst), "flow": flow, "digits": inst["digits"]}


def fp(x, d):
    return "-" if x is None else ("%." + str(d) + "f") % x


def zone_text(z, d):
    return "%s %s-%s" % (z["side"], fp(z["bottom"], d), fp(z["top"], d))


def render(r, inst):
    d, b = r["digits"], r["base"]
    lines = ["%s %s at %s (%s UTC, %s New York, %s): bias %s (score %+d)" % (
        r["symbol"], r["tf"], fp(b["price"], d), r["as_of"][:16].replace("T", " "), r["ny_time"][11:], r["source"],
        b["bias"].upper(), b["score"])]
    if b["reasons"]:
        lines.append("  " + "; ".join(b["reasons"]))
    fr = ["%s %s" % (f["tf"], f["trend"] or "-") + (" (%s %+d)" % (f["bias"], f["score"]) if f.get("bias") else "")
          for f in r["frames"]]
    lines.append("Timeframes: %s | %s %s -> %s" % (" | ".join(fr), r["tf"], b["trend"] or "-", r["alignment"]))
    ev = b["last_event"]
    if ev:
        lines.append("Last break: %s %s through %s" % (ev["kind"], ev["dir"], fp(ev["level"], d)))
    liq = ["%s %s (%d touches)" % (p["kind"], fp(p["level"], d), p["count"]) for p in b["liquidity_above"]]
    liq2 = ["%s %s (%d touches)" % (p["kind"], fp(p["level"], d), p["count"]) for p in b["liquidity_below"]]
    lines.append("Liquidity above: %s; below: %s" % (", ".join(liq) or "none resting", ", ".join(liq2) or "none resting"))
    if b["recent_sweep"]:
        s = b["recent_sweep"]
        lines.append("Swept %s %s %d bars ago, %s" % (s["kind"], fp(s["level"], d), s["bars_ago"],
                                                    "closed back (a stop hunt)" if s["closed_back"] else "held beyond"))
    lines.append("FVGs above: %s; below: %s" % (", ".join(zone_text(z, d) for z in b["fvgs_above"]) or "none",
                                               ", ".join(zone_text(z, d) for z in b["fvgs_below"]) or "none"))
    lines.append("Order blocks above: %s; below: %s" % (", ".join(zone_text(z, d) for z in b["obs_above"]) or "none",
                                                       ", ".join(zone_text(z, d) for z in b["obs_below"]) or "none"))
    if b["breakers"]:
        lines.append("Breakers: %s" % ", ".join(zone_text(z, d) for z in b["breakers"]))
    lo, hi = b["dealing_range"]
    lines.append("Dealing range %s-%s, price in %s (%.0f%%); OTE long %s-%s, OTE short %s-%s" % (
        fp(lo, d), fp(hi, d), b["premium_discount"], 100 * b["range_position"], fp(b["ote_long"][0], d),
        fp(b["ote_long"][1], d), fp(b["ote_short"][0], d), fp(b["ote_short"][1], d)))
    lv = ["%s %s (%s %.1f pips)" % (x["name"], fp(x["price"], d), x["side"], x["pips"]) for x in r["levels"][:8]]
    lines.append("Levels, nearest first: %s" % ", ".join(lv))
    clock = b["killzone"] or "outside the killzones"
    if b["silver_bullet"]:
        clock += ", Silver Bullet window %s" % b["silver_bullet"]
    lines.append("Clock (New York %s): %s" % (r["ny_time"][11:], clock))
    f = r["flow"]
    p = f["profile"]
    src = {"measured": "measured delta", "clv": "CLV proxy delta, an estimate: no aggressor data"}.get(
        f["delta_source"], f["delta_source"])
    lines.append("Order flow, %s: CVD %s over 10 bars, %s (POC %s, VAH %s, VAL %s), VWAP z %+.2f%s%s%s" % (
        src, "rising" if f["cvd_slope_10"] > 0 else "falling" if f["cvd_slope_10"] < 0 else "flat", f["location"],
        fp(p["poc"], d), fp(p["vah"], d), fp(p["val"], d), f["vwap_z"],
        ", %s divergence" % f["divergence"] if f["divergence"] else "",
        ", %s absorption %d bars ago" % (f["absorption"]["side"], f["absorption"]["bars_ago"]) if f["absorption"] else "",
        "" if f["volume_real"] else "; no volume in this feed"))
    lines.append("Invalidation: a close below %s ends the bullish read, a close above %s the bearish one." % (
        fp(b["swing_low"], d), fp(b["swing_high"], d)))
    lines.append("This is a structure read, not a signal. Test any rule you take from it in /trader-lab first. "
                 + tc.NOTE_ADVICE)
    return "\n".join(lines)


def load(a, cfg):
    inst = tc.resolve(a.symbol, cfg)
    bars, source = hist.series(inst, a.tf, a.data, a.offline, a.yahoo)
    if len(bars) < 60:
        raise tc.TraderError("only %d %s bars of %s: download more with data.py get" % (len(bars), a.tf, inst["symbol"]))
    return inst, bars, source


def cmd_read(a, cfg):
    inst, bars, source = load(a, cfg)
    r = read(inst, bars, [x.strip() for x in a.htf.split(",") if x.strip()], source)
    if a.write:
        path = os.path.join(a.write, "%s.json" % inst["symbol"])
        tc.write_json(path, r)
    if a.json:
        print(json.dumps(r, indent=2, default=str))
    else:
        print(render(r, inst))
        if a.write:
            print("Saved %s." % os.path.join(a.write, "%s.json" % inst["symbol"]))
    return 0


def cmd_levels(a, cfg):
    inst, bars, source = load(a, cfg)
    lv = key_levels(bars, inst)
    if a.json:
        print(json.dumps(lv, indent=2))
        return 0
    print("%s key levels at %s (%s):" % (inst["symbol"], fp(bars.c[-1], inst["digits"]), source))
    for x in lv:
        print("  %-7s %-12s %-6s %7.1f pips  %s" % (x["name"], fp(x["price"], inst["digits"]), x["side"], x["pips"], x["why"]))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="SMC / ICT and order-flow structure (trader-structure).")
    ap.add_argument("--config", default="trader/config.json")
    ap.add_argument("--data", default=hist.CACHE)
    ap.add_argument("--offline", help="a saved Yahoo chart file or folder")
    ap.add_argument("--yahoo", action="store_true", help="the last 60 days of live 5-minute bars")
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    for name in ("read", "levels"):
        p = sub.add_parser(name)
        p.add_argument("symbol")
        p.add_argument("--tf", default="M15", help="the base timeframe (default M15)")
        if name == "read":
            p.add_argument("--htf", default="H1,H4,D1", help="higher timeframes for the bias (default H1,H4,D1)")
            p.add_argument("--write", nargs="?", const="trader/structure", metavar="FOLDER")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        cfg = tc.load_config(a.config)
        return {"read": cmd_read, "levels": cmd_levels}[a.cmd](a, cfg)
    except (tc.TraderError, ValueError) as e:
        print("structure.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
