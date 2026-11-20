#!/usr/bin/env python3
"""COT tracker for trader-cot: how the big speculators are positioned in the
futures behind your forex pairs, metals, oil, indices and bitcoin, from the
CFTC's weekly Commitments of Traders report. Standard library only.

    python3 cot.py latest                        # every mapped market, this week's report
    python3 cot.py latest --symbols EURUSD,USDJPY,XAUUSD
    python3 cot.py history --symbol EURUSD --weeks 52
    python3 cot.py latest --write                # also save trader/cot.json
    python3 cot.py latest --offline tests/fixtures/cot/legacy-futures.json.gz

The data: the CFTC's Legacy "Futures Only" report on its public reporting site,
  https://publicreporting.cftc.gov/resource/6dca-aqww.json
filtered by contract market code (Euro FX 099741, Japanese yen 097741, gold
088691, WTI crude 067651, E-mini S&P 500 13874A, Bitcoin 133741 ...). Each row
is one market on one Tuesday; the CFTC publishes it the Friday after, at 3:30
p.m. New York. Free and official, no key.

What it reports, per market:
  net          non-commercial (speculator) longs minus shorts, in contracts
  change       this week's net minus last week's
  COT index    where this week's net sits in its own range over the lookback
               (--weeks, 156 = three years): 0 = the most short, 100 = the
               most long. 90 or more is "crowded long", 10 or less "crowded
               short": a crowded trade can unwind hard, it is not a signal
               on its own
  commercials  the hedgers' net, usually the other side
  For a pair quoted the other way round (USDJPY, USDCHF, USDCAD, USDMXN,
  USDZAR) the bias is flipped: speculators long yen futures are short USDJPY.

Positioning is a weekly, three-day-old picture. Leads, not signals.
"""

import argparse
import datetime
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "trader-core"))
import tradercore as tc  # noqa: E402

URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
CROWDED = 90


class CotError(tc.TraderError):
    pass


def _i(row, key):
    v = row.get(key)
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def parse_rows(rows):
    """Socrata rows -> {code: [week dicts, oldest first]}."""
    out = {}
    for r in rows:
        code = str(r.get("cftc_contract_market_code") or "").strip().upper()
        date = str(r.get("report_date_as_yyyy_mm_dd") or "")[:10]
        nl, ns = _i(r, "noncomm_positions_long_all"), _i(r, "noncomm_positions_short_all")
        if not code or not date or nl is None or ns is None:
            continue
        cl, cs = _i(r, "comm_positions_long_all"), _i(r, "comm_positions_short_all")
        out.setdefault(code, {})[date] = {
            "date": date, "name": str(r.get("market_and_exchange_names") or code).strip(),
            "open_interest": _i(r, "open_interest_all"), "spec_long": nl, "spec_short": ns, "spec_net": nl - ns,
            "comm_net": (cl - cs) if cl is not None and cs is not None else None}
    return {k: [v[d] for d in sorted(v)] for k, v in out.items()}


def fetch(codes, weeks, now):
    since = (now.date() - datetime.timedelta(weeks=weeks + 2)).isoformat()
    where = "cftc_contract_market_code in(%s) AND report_date_as_yyyy_mm_dd >= '%sT00:00:00'" % (
        ",".join("'%s'" % c for c in codes), since)
    q = urllib.parse.urlencode({"$where": where, "$order": "report_date_as_yyyy_mm_dd ASC",
                                "$limit": str(len(codes) * (weeks + 5))})
    try:
        text = tc.http_get(URL + "?" + q, timeout=30, headers={"Accept": "application/json"})
        rows = json.loads(text)
    except (ValueError, OSError, tc.urllib.error.URLError) as e:
        raise CotError("the CFTC reporting site did not answer (%s): try again later" % getattr(e, "reason", e))
    if not isinstance(rows, list):
        raise CotError("the CFTC answer is not a list of rows: %s" % str(rows)[:200])
    return rows


def analyse(weeks_rows, lookback):
    """One market's history -> the latest week's numbers."""
    if not weeks_rows:
        return None
    use = weeks_rows[-lookback:]
    last = use[-1]
    nets = [w["spec_net"] for w in use]
    lo, hi = min(nets), max(nets)
    idx = 100.0 * (last["spec_net"] - lo) / (hi - lo) if hi > lo else 50.0
    prev = use[-2] if len(use) >= 2 else None
    out = dict(last, change=(last["spec_net"] - prev["spec_net"]) if prev else None, cot_index=round(idx, 1),
               weeks=len(use), range_low=lo, range_high=hi)
    out["crowded"] = "long" if idx >= CROWDED else "short" if idx <= 100 - CROWDED else None
    if last["open_interest"]:
        out["net_pct_oi"] = round(100.0 * last["spec_net"] / last["open_interest"], 1)
    return out


def view(inst, a):
    """The market's numbers read in the instrument's direction."""
    sign = inst.get("cot_sign") or 1
    bias = "long" if a["spec_net"] * sign > 0 else "short" if a["spec_net"] * sign < 0 else "flat"
    idx = a["cot_index"] if sign > 0 else round(100 - a["cot_index"], 1)
    crowded = a["crowded"]
    if crowded and sign < 0:
        crowded = "short" if crowded == "long" else "long"
    return {"symbol": inst["symbol"], "bias": bias, "cot_index": idx, "crowded": crowded, "inverted": sign < 0}


def pick(a, cfg):
    reg = tc.registry(cfg)
    if a.symbols:
        insts = [tc.resolve(s, cfg, reg) for s in re.split(r"[,\s]+", a.symbols) if s]
    else:
        insts = [i for i in tc.universe(None, cfg, ("spot", "cfd")) if i.get("cot")]
    out, codes = [], []
    for i in insts:
        if not i.get("cot"):
            raise CotError("%s has no COT market mapped (set \"cot\" in the config's instruments)" % i["symbol"])
        out.append(i)
        if i["cot"] not in codes:
            codes.append(i["cot"])
    return out, codes


def load(a, codes, weeks, now):
    if a.offline:
        rows = tc.read_json(a.offline, "offline COT rows")
    else:
        rows = fetch(codes, weeks, now)
    data = parse_rows(rows)
    return {c: data.get(c, []) for c in codes}


def cmd_latest(a):
    cfg = tc.load_config(a.config)
    now = tc.parse_now(a.now, cfg["timezone"])
    insts, codes = pick(a, cfg)
    data = load(a, codes, a.weeks, now)
    rows, missing = [], []
    for inst in insts:
        an = analyse(data.get(inst["cot"]), a.weeks)
        if an is None:
            missing.append(inst["symbol"])
            continue
        rows.append((inst, an, view(inst, an)))
    doc = {"created_by": "trader-cot", "created_at": tc.iso(now), "lookback_weeks": a.weeks,
           "source": "offline" if a.offline else URL,
           "markets": [dict(an, symbol=inst["symbol"], code=inst["cot"], view=v) for inst, an, v in rows]}
    if a.write:
        tc.write_json(a.write, doc)
    if a.json:
        print(json.dumps(doc, indent=2))
        return 0 if rows else 1
    if rows:
        print("Commitments of Traders, speculators (non-commercial), report of %s; COT index over %d weeks." % (
            max(an["date"] for _, an, _ in rows), a.weeks))
    print("%-8s %-24s %10s %9s %6s  %-14s %s" % ("SYMBOL", "MARKET", "SPEC NET", "CHANGE", "INDEX", "READ", "NOTE"))
    for inst, an, v in rows:
        note = []
        if v["crowded"]:
            note.append("crowded %s" % v["crowded"])
        if v["inverted"]:
            note.append("flipped: %s futures vs %s" % (inst["quote"] if inst["base"] == "USD" else inst["base"],
                                                       inst["symbol"]))
        print("%-8s %-24s %10s %9s %6.1f  %-14s %s" % (
            inst["symbol"], an["name"].split(" - ")[0][:24], "{:+,}".format(an["spec_net"]),
            "{:+,}".format(an["change"]) if an["change"] is not None else "-", v["cot_index"],
            "specs %s" % v["bias"], ", ".join(note)))
    for m in missing:
        print("%-8s no rows in the report for its market" % m)
    if a.write:
        print("Wrote %s." % a.write)
    print("A weekly, three-day-old picture of positioning. Crowded can stay crowded: leads, not signals.")
    return 0 if rows else 1


def cmd_history(a):
    cfg = tc.load_config(a.config)
    now = tc.parse_now(a.now, cfg["timezone"])
    a.symbols = a.symbol
    insts, codes = pick(a, cfg)
    inst = insts[0]
    data = load(a, codes, a.weeks, now)
    hist = data.get(inst["cot"]) or []
    if not hist:
        raise CotError("no COT rows for %s (%s)" % (inst["symbol"], inst["cot"]))
    use = hist[-a.weeks:]
    if a.json:
        print(json.dumps({"symbol": inst["symbol"], "code": inst["cot"], "weeks": use}, indent=2))
        return 0
    lo, hi = min(w["spec_net"] for w in use), max(w["spec_net"] for w in use)
    print("%s (%s), speculators' net, last %d weeks:" % (inst["symbol"], use[-1]["name"], len(use)))
    width = 40
    for w in use[-a.show:]:
        pos = int(round((w["spec_net"] - lo) / float(hi - lo) * width)) if hi > lo else width // 2
        print("  %s %10s |%s*%s|" % (w["date"], "{:+,}".format(w["spec_net"]), " " * pos, " " * (width - pos)))
    an = analyse(hist, a.weeks)
    v = view(inst, an)
    print("COT index %.1f for %s (%s range %s to %s)%s.%s" % (
        v["cot_index"], inst["symbol"], "%d-week" % an["weeks"], "{:+,}".format(lo), "{:+,}".format(hi),
        (", read through the %s futures above, flipped" % (inst["quote"] if inst["base"] == "USD" else inst["base"]))
        if v["inverted"] else "", (" Crowded %s." % v["crowded"]) if v["crowded"] else ""))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="CFTC Commitments of Traders positioning (trader-cot).")
    sub = ap.add_subparsers(dest="cmd")

    def common(p):
        p.add_argument("--config", default="trader/config.json")
        p.add_argument("--weeks", type=int, default=156, help="lookback for the COT index (default 156, 3 years)")
        p.add_argument("--offline", metavar="FILE", help="saved rows (.json or .json.gz)")
        p.add_argument("--now")
        p.add_argument("--json", action="store_true")
    p = sub.add_parser("latest")
    common(p)
    p.add_argument("--symbols", help="EURUSD,XAUUSD,... (default: every mapped market)")
    p.add_argument("--write", nargs="?", const="trader/cot.json", metavar="PATH")
    p = sub.add_parser("history")
    common(p)
    p.add_argument("--symbol", required=True)
    p.add_argument("--show", type=int, default=26, help="weeks to draw")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    if a.weeks < 4:
        print("cot.py: --weeks must be at least 4", file=sys.stderr)
        return 1
    try:
        return {"latest": cmd_latest, "history": cmd_history}[a.cmd](a)
    except tc.TraderError as e:
        print("cot.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
