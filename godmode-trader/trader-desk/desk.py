#!/usr/bin/env python3
"""The desk for trader-desk: one brief that puts every skill's latest output side by side
for your markets and ranks today's ideas by what has been PROVEN, not by what looks good.
Standard library only.

    python3 desk.py brief                                  # your config's symbols (or the majors), everything known
    python3 desk.py brief EURUSD XAUUSD US500 BTCUSD --write   # also save trader/brief.md
    python3 desk.py brief --offline tests/fixtures/charts  # structure from saved charts

What it reads (each part is optional: a missing input is named, never guessed):
  clock         which sessions are open now and which open next (trader-core)
  calendar      the next High-impact releases for each market's currencies (trader/calendar.json)
  macro         the dollar compass and the regime line (trader/data/macro/fred.json)
  positioning   COT crowding per market (trader/cot.json)
  structure     SMC / ICT bias, timeframe alignment, nearest levels, the killzone (trader-structure)
  lab           the setups with a tested record on each market (trader/lab/summary.json)
  prop firm     today's room and the largest safe risk (trader/propfirm.json)
  journal       your own record and the latest lessons (trader/journal.csv, trader/lessons.md)

An idea needs a setup with a positive, tested record on that market (30+ trades,
p < 0.10). Structure, macro and positioning can raise or lower its place in the list;
they cannot create one. Without a tested setup, a market is "watch only".
"""

import argparse
import datetime
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "trader-core"))
import tradercore as tc  # noqa: E402
import history as hist  # noqa: E402

DEFAULT = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US500", "BTCUSD"]


def load_tool(folder, name):
    spec = importlib.util.spec_from_file_location("desk_%s_%s" % (folder.replace("-", "_"), name),
                                                  os.path.join(HERE, "..", folder, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def currencies(inst):
    if inst["class"] == "forex":
        return {str(inst["base"]).upper(), str(inst["quote"]).upper()}
    if inst["class"] == "crypto":
        return {"USD"}
    return {str(inst["quote"]).upper()}


def part_clock(now, cfg):
    rows = []
    for k in tc.FX_SESSIONS + ("us_cash", "xetra", "comex", "nymex"):
        inst, phase = tc.locate(k, now, cfg)
        if inst and phase == "open":
            rows.append("%s open until %s" % (k, tc.stamp(inst["close_utc"], inst["tz"])))
        else:
            nxt = tc.next_open(k, now, cfg)
            rows.append("%s opens %s" % (k, tc.stamp(nxt["open_utc"], nxt["tz"]) if nxt else "?"))
    return rows


def part_calendar(path, insts, now, hours=36):
    cal = tc.read_json(path, "calendar", required=False)
    if not cal:
        return None, "no calendar: run econ.py week --write"
    out = {}
    horizon = now + datetime.timedelta(hours=hours)
    for e in cal.get("events", []):
        if e.get("impact") != "High":
            continue
        t = tc.parse_utc(e["time_utc"])
        if not now <= t <= horizon:
            continue
        for inst in insts:
            if e.get("currency") in currencies(inst):
                out.setdefault(inst["symbol"], []).append("%s %s %s" % (
                    tc.iso(t)[5:16].replace("T", " "), e["currency"], e["title"]))
    return out, None


def part_macro(data_root):
    try:
        macro = load_tool("trader-macro", "macro")
        data = macro.load_fred(data_root)
        c = macro.dollar_compass(data)
        d = macro.dashboard(data)
        return {"dollar": "%s (%+d of 4)" % (c["read"], c["score"]), "dollar_score": c["score"],
                "regime": "; ".join(d["regime"])}, None
    except (tc.TraderError, KeyError, IndexError, ValueError) as e:
        return None, "no macro: %s" % e


def part_cot(path):
    doc = tc.read_json(path, "COT", required=False)
    if not doc:
        return {}, "no COT: run cot.py latest --write"
    out = {}
    for m in doc.get("markets", []):
        v = m.get("view") or {}
        out[m["symbol"]] = "COT %s%s" % (v.get("bias", "?"), ", crowded %s" % v["crowded"] if v.get("crowded") else "")
    return out, None


def part_lab(path):
    """Saved lab results by symbol, each with a Holm-adjusted p across EVERY saved test: the more
    setups and markets you have tried, the stronger a result must be to count."""
    import stats
    doc = tc.read_json(path, "lab summary", required=False)
    if not doc:
        return {}, "no lab results: run lab.py rank <symbols> --save"
    adj = stats.holm({k: r.get("p_value") for k, r in doc.items() if r.get("trades")})
    out = {}
    for k, row in doc.items():
        out.setdefault(row["symbol"], []).append(dict(row, p_adjusted=adj.get(k, 1.0), tests=len(adj)))
    return out, None


def proven(rows, min_trades=30, max_p=0.10):
    good = [r for r in rows if r.get("trades", 0) >= min_trades and (r.get("expectancy_r") or 0) > 0
            and r.get("p_adjusted", 1.0) < max_p]
    return sorted(good, key=lambda r: (r.get("p_adjusted", 1.0), -(r.get("expectancy_r") or 0)))


def part_structure(a, inst, cfg):
    try:
        st = load_tool("trader-structure", "structure")
        bars, source = hist.series(inst, "M15", a.data, a.offline, a.yahoo)
        cut = bars.last_closed_at(tc.ts_of(a.now_utc))            # only bars that had closed by the desk's clock
        bars = bars.slice(0, cut + 1)
        r = st.read(inst, bars, ["H1", "H4", "D1"], source)
        b = r["base"]
        lv = ["%s %s" % (x["name"], tc.fmt_price(x["price"], inst)) for x in r["levels"][:3]]
        return {"bias": b["bias"], "score": b["score"], "alignment": r["alignment"], "levels": lv,
                "killzone": b["killzone"], "price": b["price"], "as_of": r["as_of"],
                "premium_discount": b["premium_discount"]}, None
    except (tc.TraderError, ValueError) as e:
        return None, str(e)


def part_prop(path, cfg):
    st = tc.read_json(path, "prop state", required=False)
    if not st:
        return None
    pf = load_tool("trader-propfirm", "propfirm")
    import prop
    rl = prop.rules(dict(cfg.get("prop_firm") or {}, preset=st.get("preset", "ftmo_2step")))
    g = pf.guardian_of(st, rl)
    return "%s: room %s, largest safe risk %s, %s" % (rl["label"], tc.money(g["room"], st["currency"]),
                                                     tc.money(g["max_risk_per_trade"], st["currency"]), g["status"])


def part_journal(journal_path, lessons_path):
    out = {}
    if os.path.exists(journal_path):
        jr = load_tool("trader-journal", "journal")
        rows = jr.read_rows(journal_path)
        rs = [float(r["R"]) for r in rows if r.get("R")]
        out["record"] = "%d entries, %d complete outcomes%s" % (
            len(rows), len(rs), ", %+.3f R a trade" % (sum(rs) / len(rs)) if rs else "")
    if os.path.exists(lessons_path):
        with open(lessons_path, encoding="utf-8") as fh:
            out["lessons"] = [x.strip()[2:] for x in fh if x.startswith("- ")][-3:]
    return out


def rank_ideas(insts, lab, struct, cot, macro):
    ideas, watch = [], []
    for inst in insts:
        sym = inst["symbol"]
        edges = proven(lab.get(sym, []))
        s = struct.get(sym)
        if not edges:
            watch.append(sym)
            continue
        top = edges[0]
        score = min(3.0, (top.get("expectancy_r") or 0) * (top.get("trades") or 0) ** 0.5)
        notes = ["%s on %s: %+.3f R over %d trades, p %.3f, %.3f after %d tests (%s)" % (
            top["setup"], top["tf"], top["expectancy_r"], top["trades"], top["p_value"], top["p_adjusted"],
            top["tests"], top.get("family", ""))]
        lean = None
        if s:
            if s["alignment"].startswith("aligned"):
                score += 0.5
                lean = "long" if "up" in s["alignment"] else "short"
            notes.append("structure %s, %s, %s" % (s["bias"], s["alignment"], s["premium_discount"]))
            if s["killzone"]:
                score += 0.25
                notes.append("in the %s killzone now" % s["killzone"])
        if sym in cot:
            notes.append(cot[sym])
        if macro and lean and inst["class"] == "forex" and "USD" in currencies(inst):
            usd_up = macro["dollar_score"] >= 2
            usd_down = macro["dollar_score"] <= -2
            usd_long = (lean == "long") == (str(inst["base"]).upper() == "USD")
            if (usd_up and usd_long) or (usd_down and not usd_long):
                score += 0.25
                notes.append("macro agrees (%s)" % macro["dollar"])
            elif usd_up or usd_down:
                score -= 0.25
                notes.append("macro disagrees (%s)" % macro["dollar"])
        ideas.append({"symbol": sym, "setup": top["setup"], "tf": top["tf"], "lean": lean, "score": round(score, 2),
                      "notes": notes, "others": [e["setup"] for e in edges[1:4]]})
    ideas.sort(key=lambda x: -x["score"])
    return ideas, watch


def brief(a, cfg):
    now = tc.parse_now(a.now, cfg["timezone"])
    a.now_utc = now
    syms = a.symbols or cfg.get("symbols") or DEFAULT
    insts = [tc.resolve(s, cfg) for s in syms]
    missing = []
    cal, why = part_calendar(a.calendar, insts, now)
    missing += [why] if why else []
    macro, why = part_macro(a.data)
    missing += [why] if why else []
    cot, why = part_cot(a.cot)
    missing += [why] if why else []
    lab, why = part_lab(a.lab)
    missing += [why] if why else []
    struct, struct_err = {}, {}
    for inst in insts:
        s, why = part_structure(a, inst, cfg)
        if s:
            struct[inst["symbol"]] = s
        else:
            struct_err[inst["symbol"]] = why
    ideas, watch = rank_ideas(insts, lab, struct, cot, macro)
    return {"at": tc.iso(now), "local": tc.stamp(now, cfg["timezone"]), "symbols": [i["symbol"] for i in insts],
            "clock": part_clock(now, cfg), "calendar": cal or {}, "macro": macro, "cot": cot, "structure": struct,
            "structure_missing": struct_err, "ideas": ideas, "watch_only": watch,
            "prop": part_prop(a.prop, cfg), "journal": part_journal(a.journal, a.lessons), "missing": missing}


def render(d, md=False):
    h = (lambda t: "## " + t) if md else (lambda t: t.upper())
    L = ["# Desk brief, %s" % d["local"] if md else "DESK BRIEF %s" % d["local"], ""]
    L += [h("Clock"), "; ".join(d["clock"]), ""]
    if d["macro"]:
        L += [h("Macro"), "Dollar: %s. %s." % (d["macro"]["dollar"], d["macro"]["regime"]), ""]
    L += [h("Ideas (a tested setup first)")]
    if not d["ideas"]:
        L.append("None today: no market here has a setup with a tested positive record (30+ trades, p < 0.10 "
                 "after correcting for every test saved). Run lab.py rank on more history before trading any of them.")
    for k, i in enumerate(d["ideas"], 1):
        L.append("%d. %s %s %s%s, score %.2f" % (k, i["symbol"], i["setup"], i["tf"],
                                                ", leaning %s" % i["lean"] if i["lean"] else "", i["score"]))
        for n in i["notes"]:
            L.append("   - %s" % n)
        if d["calendar"].get(i["symbol"]):
            L.append("   - High impact next (UTC): %s" % "; ".join(d["calendar"][i["symbol"]][:3]))
        if i["others"]:
            L.append("   - also tested positive: %s" % ", ".join(i["others"]))
    L.append("")
    L += [h("Watch only (no tested setup)")]
    for sym in d["watch_only"]:
        s = d["structure"].get(sym)
        if s:
            L.append("- %s: %s, %s; nearest %s%s" % (sym, s["bias"], s["alignment"], ", ".join(s["levels"]),
                                                    "; %s killzone" % s["killzone"] if s["killzone"] else ""))
        else:
            L.append("- %s: no structure read (%s)" % (sym, d["structure_missing"].get(sym, "?")))
        if d["calendar"].get(sym):
            L.append("  High impact next (UTC): %s" % "; ".join(d["calendar"][sym][:3]))
    L.append("")
    if d["prop"]:
        L += [h("Prop firm"), d["prop"], ""]
    if d["journal"]:
        L += [h("Journal")]
        if d["journal"].get("record"):
            L.append(d["journal"]["record"])
        for x in d["journal"].get("lessons", []):
            L.append("- lesson: %s" % x)
        L.append("")
    if d["missing"]:
        L += [h("Not included"), "; ".join(d["missing"]), ""]
    L.append("The brief ranks evidence; it places nothing. Every trade still goes plan -> budget -> risk -> your yes. "
             + tc.NOTE_ADVICE)
    return "\n".join(L)


def cmd_brief(a, cfg):
    d = brief(a, cfg)
    if a.json:
        print(json.dumps(d, indent=2, default=str))
    else:
        print(render(d))
    if a.write:
        os.makedirs(os.path.dirname(a.write) or ".", exist_ok=True)
        with open(a.write, "w", encoding="utf-8") as fh:
            fh.write(render(d, md=True) + "\n")
        if not a.json:
            print("\nSaved %s." % a.write)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="The desk brief (trader-desk).")
    ap.add_argument("--config", default="trader/config.json")
    ap.add_argument("--data", default=hist.CACHE)
    ap.add_argument("--offline", help="saved charts for the structure read")
    ap.add_argument("--yahoo", action="store_true", help="live 5-minute bars for the structure read")
    ap.add_argument("--now")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--calendar", default="trader/calendar.json")
    ap.add_argument("--cot", default="trader/cot.json")
    ap.add_argument("--lab", default=os.path.join("trader", "lab", "summary.json"))
    ap.add_argument("--prop", default=os.path.join("trader", "propfirm.json"))
    ap.add_argument("--journal", default=os.path.join("trader", "journal.csv"))
    ap.add_argument("--lessons", default=os.path.join("trader", "lessons.md"))
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("brief")
    p.add_argument("symbols", nargs="*")
    p.add_argument("--write", nargs="?", const="trader/brief.md", metavar="PATH")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        cfg = tc.load_config(a.config)
        return {"brief": cmd_brief}[a.cmd](a, cfg)
    except (tc.TraderError, ValueError) as e:
        print("desk.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
