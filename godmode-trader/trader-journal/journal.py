#!/usr/bin/env python3
"""The trading journal for trader-journal: every decision written down BEFORE the outcome,
the later observation recorded separately, results in R with costs, a dashboard and a
lessons file the next session reads. Standard library only.

    python3 journal.py add --symbol EURUSD --decision PAPER --side buy --entry 1.16285 \\
        --stop 1.16160 --target 1.16535 --costs 0.8pips --setup GM01 --horizon "to 16:55 London"
    python3 journal.py from-plan                     # the current trader/plan.json (and its order) as a decision
    python3 journal.py from-dex --labels WATCH REVIEW   # the last DEX scan's rows as research decisions
    python3 journal.py observe 7 --price 1.16535 --outcome target
    python3 journal.py list --open
    python3 journal.py stats                         # the dashboard: scans, pairs, decisions, outcomes, R, quality
    python3 journal.py html                          # trader/journal.html, a page you can open in a browser
    python3 journal.py lesson "Skip London breakouts the day before CPI" --tag news
    python3 journal.py lessons

trader/journal.csv opens in any spreadsheet. Its columns follow the AI Flow Lab paper
guide (Timestamp | Chain | Pair address | Snapshot price | Decision | Hypothetical entry |
Stop assumption | Target assumption | Costs/slippage assumption | Later observed price |
Simulated outcome | Notes) with the pack's own additions (ID, Symbol, Side, Setup, Source,
Horizon, Observed at, R).

The rules it enforces:
  1. The entry, stop, target, horizon and costs are written before the later price is seen.
  2. No credible cost estimate, or no stop: the outcome is "incomplete" and carries no R.
  3. An observation dated before its decision is refused.
  4. A later price is not proof a hypothetical order would have filled there.
"""

import argparse
import csv
import datetime
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "trader-core"))
import tradercore as tc  # noqa: E402

JOURNAL = os.path.join("trader", "journal.csv")
LESSONS = os.path.join("trader", "lessons.md")
COLUMNS = ["ID", "Timestamp", "Chain", "Symbol", "Pair address", "Snapshot price", "Decision", "Side", "Setup",
           "Source", "Hypothetical entry", "Stop assumption", "Target assumption", "Costs/slippage assumption",
           "Horizon", "Later observed price", "Observed at", "Simulated outcome", "R", "Notes"]
DECISIONS = ("WATCH", "REVIEW", "SKIP", "PAPER", "LIVE")


class JournalError(tc.TraderError):
    pass


def read_rows(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_rows(path, rows):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLUMNS})
    os.replace(tmp, path)


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def cost_in_price(text, entry, inst):
    """'0.8pips', '0.1%', '0.25' (price units) -> price distance, or None when unknown."""
    if text in (None, "") or str(text).strip().lower() in ("unknown", "none", "?"):
        return None
    t = str(text).strip().lower().replace(" ", "")
    m = re.match(r"^([0-9.]+)(pips?|points?|%|bps)?$", t)
    if not m:
        return None
    v, unit = float(m.group(1)), m.group(2) or ""
    if unit.startswith(("pip", "point")):
        return v * (inst["pip"] if inst else 0.0001)
    if unit == "%":
        return entry * v / 100.0 if entry else None
    if unit == "bps":
        return entry * v / 10000.0 if entry else None
    return v


def outcome_r(row, inst):
    """(gross R, net R) from the row's own assumptions, or (None, None)."""
    e, s, p = fnum(row["Hypothetical entry"]), fnum(row["Stop assumption"]), fnum(row["Later observed price"])
    if e is None or s is None or p is None or e == s:
        return None, None
    risk = abs(e - s)
    long = row["Side"] == "buy" or (row["Side"] == "" and s < e)
    gross = ((p - e) if long else (e - p)) / risk
    cost = cost_in_price(row["Costs/slippage assumption"], e, inst)
    if cost is None:
        return gross, None
    return gross, gross - cost / risk


def inst_of(sym, cfg):
    try:
        return tc.resolve(sym, cfg)
    except tc.TraderError:
        return None


def next_id(rows):
    return str(max([int(r["ID"]) for r in rows if str(r.get("ID", "")).isdigit()] or [0]) + 1)


def stamp(now):
    return tc.iso(now)


def new_row(rows, **kw):
    r = {k: "" for k in COLUMNS}
    r.update({k: ("" if v is None else v) for k, v in kw.items()})
    r["ID"] = next_id(rows)
    return r


# ---------------------------------------------------------------- commands

def cmd_add(a, cfg):
    rows = read_rows(a.journal)
    now = tc.parse_now(a.now, cfg["timezone"])
    dec = a.decision.upper()
    if dec not in DECISIONS:
        raise JournalError("--decision is one of %s" % ", ".join(DECISIONS))
    inst = inst_of(a.symbol, cfg)
    if dec in ("PAPER", "LIVE") and (a.entry is None or a.stop is None):
        raise JournalError("a PAPER or LIVE decision needs --entry and --stop written down now, before the outcome")
    if a.entry is not None and a.stop is not None and a.side:
        if (a.side == "buy" and a.stop >= a.entry) or (a.side == "sell" and a.stop <= a.entry):
            raise JournalError("the stop is on the wrong side of the entry for a %s" % a.side)
    r = new_row(rows, Timestamp=stamp(now), Chain=a.chain or (inst["class"] if inst else ""),
                Symbol=(inst["symbol"] if inst else a.symbol.upper()), **{
                    "Pair address": a.pair_address, "Snapshot price": a.price, "Decision": dec, "Side": a.side,
                    "Setup": a.setup, "Source": a.source or "manual", "Hypothetical entry": a.entry,
                    "Stop assumption": a.stop, "Target assumption": a.target, "Costs/slippage assumption": a.costs,
                    "Horizon": a.horizon, "Notes": a.notes})
    rows.append(r)
    write_rows(a.journal, rows)
    print("Journal #%s: %s %s %s%s written at %s, before any outcome." % (
        r["ID"], dec, r["Symbol"], a.side or "", " (no cost estimate: its result will be incomplete)"
        if dec in ("PAPER", "LIVE") and cost_in_price(a.costs, a.entry, inst) is None else "", r["Timestamp"][:16]))
    return 0


def cmd_from_plan(a, cfg):
    plan = tc.read_json(a.plan, "plan (run trader-exit first)")
    orders = tc.read_json(a.orders, "orders", required=False) or {}
    rows = read_rows(a.journal)
    now = tc.parse_now(a.now, cfg["timezone"])
    inst = inst_of(plan["symbol"], cfg)
    spread = (inst or {}).get("spread")
    o = (orders.get("orders") or [{}])[0] if isinstance(orders, dict) else {}
    dec = "PAPER" if cfg.get("paper", True) else "LIVE"
    r = new_row(rows, Timestamp=stamp(now), Chain=plan.get("class", ""), Symbol=plan["symbol"], Decision=dec,
                Side=plan["side"], Setup=a.setup or plan.get("setup", ""), Source="trader-exit plan", **{
                    "Snapshot price": plan.get("entry"), "Hypothetical entry": plan.get("entry"),
                    "Stop assumption": plan.get("stop"), "Target assumption": plan.get("target"),
                    "Costs/slippage assumption": a.costs or (repr(spread) if spread else ""),
                    "Horizon": "flat by %s" % plan.get("flat_by") if plan.get("flat_by") else "",
                    "Notes": ("%s lots; " % o.get("lots") if o.get("lots") else "") + (a.notes or "")})
    rows.append(r)
    write_rows(a.journal, rows)
    print("Journal #%s: %s %s %s from %s (entry %s, stop %s, target %s)." % (
        r["ID"], dec, plan["symbol"], plan["side"], a.plan, plan.get("entry"), plan.get("stop"), plan.get("target")))
    return 0


def cmd_from_dex(a, cfg):
    doc = tc.read_json(a.dex, "the last DEX scan (dex.py scan)")
    rows = read_rows(a.journal)
    added = 0
    for d in doc.get("rows", []):
        if d.get("label") not in a.labels:
            continue
        rows.append(new_row(rows, Timestamp=d["timestamp_utc"], Chain=d["chain"],
                            Symbol="%s/%s" % (d["base_symbol"], d["quote_symbol"]), Decision=d["label"],
                            Source="dex scan", Notes=d.get("flags", ""), **{
                                "Pair address": d["pair_address"], "Snapshot price": d.get("price_usd")}))
        added += 1
    write_rows(a.journal, rows)
    print("Added %d research decisions from %s (labels %s). They are not trades: add a PAPER row with an entry, stop "
          "and costs before you look at what happened next." % (added, doc.get("file", a.dex), "/".join(a.labels)))
    return 0


def cmd_observe(a, cfg):
    rows = read_rows(a.journal)
    row = next((r for r in rows if r["ID"] == str(a.id)), None)
    if row is None:
        raise JournalError("no journal entry #%s" % a.id)
    now = tc.parse_now(a.now, cfg["timezone"])
    if stamp(now) < row["Timestamp"]:
        raise JournalError("the observation (%s) is before the decision (%s)" % (stamp(now), row["Timestamp"]))
    inst = inst_of(row["Symbol"], cfg)
    price = a.price
    if a.outcome == "target" and row["Target assumption"]:
        price = fnum(row["Target assumption"])
    elif a.outcome == "stop" and row["Stop assumption"]:
        price = fnum(row["Stop assumption"])
    if price is None:
        raise JournalError("give --price (or --outcome target / stop on a row that has them)")
    row["Later observed price"] = repr(float(price))
    row["Observed at"] = stamp(now)
    gross, net = outcome_r(row, inst)
    if row["Decision"] in ("WATCH", "REVIEW", "SKIP"):
        row["Simulated outcome"] = "observed (research only)"
        row["R"] = ""
    elif net is None:
        row["Simulated outcome"] = "incomplete: %s" % ("no stop or entry" if gross is None else "no cost estimate")
        row["R"] = ""
    else:
        row["Simulated outcome"] = a.outcome or ("win" if net > 0 else "loss")
        row["R"] = "%.3f" % net
    if a.notes:
        row["Notes"] = (row["Notes"] + "; " if row["Notes"] else "") + a.notes
    write_rows(a.journal, rows)
    print("Journal #%s: observed %s at %s -> %s%s." % (row["ID"], row["Later observed price"], row["Observed at"][:16],
                                                      row["Simulated outcome"], " (%s R)" % row["R"] if row["R"] else ""))
    print("A later price is not proof the hypothetical order would have filled there.")
    return 0


def cmd_list(a, cfg):
    rows = read_rows(a.journal)
    if a.open:
        rows = [r for r in rows if not r["Observed at"]]
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    for r in rows[-a.last:]:
        print("#%-4s %s %-7s %-12s %-4s %-6s entry %-10s stop %-10s target %-10s %s %s" % (
            r["ID"], r["Timestamp"][:16], r["Decision"], r["Symbol"][:12], r["Side"], r["Setup"][:6],
            r["Hypothetical entry"] or "-", r["Stop assumption"] or "-", r["Target assumption"] or "-",
            r["Simulated outcome"] or "open", r["R"] and "(%s R)" % r["R"] or ""))
    return 0


def dashboard(a):
    import glob
    rows = read_rows(a.journal)
    snaps = sorted(glob.glob(os.path.join(a.dex_dir, "snapshot-*.csv")))
    pairs, missing, stale = set(), 0, 0
    for f in snaps:
        with open(f, newline="", encoding="utf-8") as fh:
            for d in csv.DictReader(fh):
                pairs.add((d["chain"], d["pair_address"]))
                missing += d["price_usd"] in ("", None)
    dec = {k: sum(1 for r in rows if r["Decision"] == k) for k in DECISIONS}
    done = [r for r in rows if r["R"] not in ("", None)]
    rs = [float(r["R"]) for r in done]
    incomplete = sum(1 for r in rows if r["Simulated outcome"].startswith("incomplete"))
    open_ = sum(1 for r in rows if r["Decision"] in ("PAPER", "LIVE") and not r["Observed at"])
    by_setup = {}
    for r in done:
        by_setup.setdefault(r["Setup"] or "(none)", []).append(float(r["R"]))
    no_costs = sum(1 for r in rows if r["Decision"] in ("PAPER", "LIVE") and not r["Costs/slippage assumption"])
    wins = [x for x in rs if x > 0]
    return {"total_scans": len(snaps), "reviewed_pairs": len(pairs), "decisions": dec, "entries": len(rows),
            "simulated_outcomes": len(done), "open": open_, "incomplete": incomplete,
            "win_rate": round(100.0 * len(wins) / len(rs), 1) if rs else None,
            "expectancy_r": round(sum(rs) / len(rs), 3) if rs else None, "total_r": round(sum(rs), 3) if rs else None,
            "by_setup": {k: {"trades": len(v), "expectancy_r": round(sum(v) / len(v), 3),
                             "win_rate": round(100.0 * sum(1 for x in v if x > 0) / len(v), 1)}
                         for k, v in sorted(by_setup.items())},
            "data_quality": {"snapshot_rows_missing_price": missing, "decisions_without_costs": no_costs,
                             "incomplete_results": incomplete, "stale": stale}}


def cmd_stats(a, cfg):
    d = dashboard(a)
    if a.json:
        print(json.dumps(d, indent=2))
        return 0
    print("TOTAL SCANS %d | REVIEWED PAIRS %d | ENTRIES %d" % (d["total_scans"], d["reviewed_pairs"], d["entries"]))
    print("DECISIONS   %s" % ", ".join("%s %d" % kv for kv in d["decisions"].items()))
    print("OUTCOMES    %d complete (with costs), %d open, %d incomplete" % (d["simulated_outcomes"], d["open"],
                                                                         d["incomplete"]))
    if d["simulated_outcomes"]:
        print("RESULTS     %.1f%% winners, expectancy %+.3f R, total %+.2f R" % (d["win_rate"], d["expectancy_r"],
                                                                            d["total_r"]))
        for k, v in d["by_setup"].items():
            print("  %-8s %3d trades, %5.1f%% winners, %+.3f R a trade" % (k, v["trades"], v["win_rate"], v["expectancy_r"]))
    q = d["data_quality"]
    print("DATA        %d snapshot rows without a price, %d decisions without a cost estimate, %d incomplete" % (
        q["snapshot_rows_missing_price"], q["decisions_without_costs"], q["incomplete_results"]))
    if d["simulated_outcomes"] < 30:
        print("Fewer than 30 complete outcomes: too few to judge anything yet. Keep the rules unchanged and keep going.")
    return 0


def cmd_html(a, cfg):
    d = dashboard(a)
    rows = read_rows(a.journal)
    esc = html.escape
    cards = [("Total scans", d["total_scans"]), ("Reviewed pairs", d["reviewed_pairs"]), ("Entries", d["entries"]),
             ("Complete outcomes", d["simulated_outcomes"]), ("Win rate", "-" if d["win_rate"] is None else "%s%%" % d["win_rate"]),
             ("Expectancy", "-" if d["expectancy_r"] is None else "%+.3f R" % d["expectancy_r"])]
    body = "".join('<div class="card"><div class="k">%s</div><div class="v">%s</div></div>' % (esc(k), esc(str(v)))
                   for k, v in cards)
    head = "".join("<th>%s</th>" % esc(c) for c in COLUMNS)
    trs = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % esc(str(r.get(c, ""))) for c in COLUMNS) for r in rows[::-1])
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trading Journal</title><style>
:root{--bg:#fafaf9;--fg:#1c1917;--mut:#78716c;--card:#fff;--line:#e7e5e4}
@media (prefers-color-scheme:dark){:root{--bg:#1c1917;--fg:#f5f5f4;--mut:#a8a29e;--card:#292524;--line:#44403c}}
body{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,sans-serif}
h1{font-size:20px;margin:0 0 4px}.sub{color:var(--mut);margin-bottom:16px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-bottom:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px}.k{color:var(--mut);font-size:12px}
.v{font-size:20px;font-variant-numeric:tabular-nums}.wrap{overflow-x:auto}table{border-collapse:collapse;font-size:12px}
th,td{border-bottom:1px solid var(--line);padding:4px 8px;text-align:left;white-space:nowrap}</style></head><body>
<h1>Trading Journal</h1><div class="sub">Generated %s. Paper decisions and observations; not financial advice.</div>
<div class="cards">%s</div><div class="wrap"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div></body></html>
""" % (esc(tc.iso(tc.utc_now())), body, head, trs)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(page)
    print("Wrote %s (%d entries)." % (a.out, len(rows)))
    return 0


def cmd_lesson(a, cfg):
    now = tc.parse_now(a.now, cfg["timezone"])
    new = not os.path.exists(a.lessons)
    os.makedirs(os.path.dirname(a.lessons) or ".", exist_ok=True)
    with open(a.lessons, "a", encoding="utf-8") as fh:
        if new:
            fh.write("# Lessons\n\nWhat the journal taught. The desk and the reflector read this before each session.\n\n")
        fh.write("- %s%s: %s\n" % (tc.iso(now)[:10], " [%s]" % a.tag if a.tag else "", " ".join(a.text.split())))
    print("Saved to %s." % a.lessons)
    return 0


def cmd_lessons(a, cfg):
    if not os.path.exists(a.lessons):
        print("No lessons yet: journal.py lesson \"...\"")
        return 1
    with open(a.lessons, encoding="utf-8") as fh:
        lines = [x.rstrip() for x in fh if x.startswith("- ")]
    if a.tag:
        lines = [x for x in lines if "[%s]" % a.tag in x]
    print("\n".join(lines[-a.last:]) if lines else "No lessons with that tag.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="The trading journal (trader-journal).")
    ap.add_argument("--config", default="trader/config.json")
    ap.add_argument("--journal", default=JOURNAL)
    ap.add_argument("--lessons", default=LESSONS)
    ap.add_argument("--now", help="the clock (default now)")
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("add")
    p.add_argument("--symbol", required=True)
    p.add_argument("--decision", required=True, help="WATCH, REVIEW, SKIP, PAPER or LIVE")
    p.add_argument("--side", choices=["buy", "sell"])
    p.add_argument("--entry", type=float)
    p.add_argument("--stop", type=float)
    p.add_argument("--target", type=float)
    p.add_argument("--costs", help="spread + slippage + fees: 0.8pips, 0.1%%, 12bps or a price distance")
    p.add_argument("--horizon")
    p.add_argument("--setup", help="the GM code or rule, e.g. GM01")
    p.add_argument("--price", type=float, help="the snapshot price when you decided")
    p.add_argument("--chain", help="for DEX pairs: the chain")
    p.add_argument("--pair-address", dest="pair_address")
    p.add_argument("--source")
    p.add_argument("--notes")
    p = sub.add_parser("from-plan")
    p.add_argument("--plan", default="trader/plan.json")
    p.add_argument("--orders", default="trader/orders.json")
    p.add_argument("--setup")
    p.add_argument("--costs")
    p.add_argument("--notes")
    p = sub.add_parser("from-dex")
    p.add_argument("--dex", default=os.path.join("trader", "dex", "latest.json"))
    p.add_argument("--labels", nargs="*", default=["WATCH", "REVIEW"])
    p = sub.add_parser("observe")
    p.add_argument("id")
    p.add_argument("--price", type=float)
    p.add_argument("--outcome", choices=["target", "stop", "time", "manual"])
    p.add_argument("--notes")
    p = sub.add_parser("list")
    p.add_argument("--open", action="store_true")
    p.add_argument("--last", type=int, default=30)
    for name in ("stats", "html"):
        p = sub.add_parser(name)
        p.add_argument("--dex-dir", dest="dex_dir", default=os.path.join("trader", "dex"))
        if name == "html":
            p.add_argument("--out", default=os.path.join("trader", "journal.html"))
    p = sub.add_parser("lesson")
    p.add_argument("text")
    p.add_argument("--tag")
    p = sub.add_parser("lessons")
    p.add_argument("--tag")
    p.add_argument("--last", type=int, default=20)
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        cfg = tc.load_config(a.config)
        return {"add": cmd_add, "from-plan": cmd_from_plan, "from-dex": cmd_from_dex, "observe": cmd_observe,
                "list": cmd_list, "stats": cmd_stats, "html": cmd_html, "lesson": cmd_lesson,
                "lessons": cmd_lessons}[a.cmd](a, cfg)
    except (tc.TraderError, ValueError, OSError) as e:
        print("journal.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
