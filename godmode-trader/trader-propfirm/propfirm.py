#!/usr/bin/env python3
"""Prop-firm challenges for trader-propfirm: the rules, a live guardian that turns them into
numbers before every trade, an order check, and the pass probability of a setup's real
trades at each risk size. Standard library only.

    python3 propfirm.py rules                                      # FTMO 2-step (default) as numbers
    python3 propfirm.py rules --preset generic_1step
    python3 propfirm.py init --size 100000 --preset ftmo_2step     # start tracking a challenge
    python3 propfirm.py update --balance 101250 --equity 100980 --traded
    python3 propfirm.py status                                     # floors, room, the largest safe risk
    python3 propfirm.py check                                      # every order in trader/orders.json vs the room
    python3 propfirm.py sim --trades trader/lab/EURUSD/GM01-M5.json   # pass odds at each risk size
    python3 propfirm.py sim --journal trader/journal.csv --phase 2

The state lives in trader/propfirm.json. The day resets at midnight in the firm's zone
(Prague for FTMO): the first update of a new day takes the last balance as that day's start,
and the daily floor is that start minus the daily limit of the INITIAL balance.

Every number is a preset you can override under "prop_firm" in trader/config.json, and every
firm changes its terms: check the current rules on the firm's site before you rely on them.
"""

import argparse
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "trader-core"))
import tradercore as tc  # noqa: E402
import prop  # noqa: E402

STATE = os.path.join("trader", "propfirm.json")


def rules_for(a, cfg, state=None):
    pc = dict(cfg.get("prop_firm") or {})
    if state and state.get("preset"):
        pc["preset"] = state["preset"]
    if getattr(a, "preset", None):
        pc["preset"] = a.preset
    return prop.rules(pc)


def firm_day(rl, now_utc):
    return tc.to_local(rl["day_zone"], now_utc).date().isoformat()


def load_state(path):
    st = tc.read_json(path, "prop-firm state", required=False)
    if not st:
        raise tc.TraderError("no challenge tracked yet: propfirm.py init --size 100000")
    return st


def guardian_of(st, rl, equity=None, risk=None, streak=4, buffer_pct=20.0):
    days = st.get("days") or {}
    today = st.get("today")
    start = (days.get(today) or {}).get("start", st["balance"])
    traded = sum(1 for d in days.values() if d.get("traded"))
    return prop.guardian(rl, st["size"], st["balance"], equity if equity is not None else st.get("equity", st["balance"]),
                         start, st.get("peak"), st.get("phase", 1), traded, risk, streak, buffer_pct)


def money(x, cur):
    return tc.money(x, cur)


def cmd_rules(a, cfg):
    rl = rules_for(a, cfg)
    if a.json:
        print(json.dumps(rl, indent=2))
        return 0
    size = a.size or 100000.0
    cur = cfg["account_currency"]
    print("%s (%s)" % (rl["label"], rl["preset"]))
    for k, t in enumerate(rl["targets_pct"], 1):
        print("  phase %d target: +%.1f%% (%s on %s)" % (k, t, money(size * t / 100.0, cur), money(size, cur)))
    print("  maximum daily loss: %.1f%% of the initial balance (%s), measured from each day's starting balance"
          % (rl["daily_loss_pct"], money(size * rl["daily_loss_pct"] / 100.0, cur)))
    print("  maximum loss: %.1f%% of the initial balance (%s), %s" % (
        rl["max_loss_pct"], money(size * rl["max_loss_pct"] / 100.0, cur),
        "TRAILING the highest balance" if rl["trailing"] else "static: the floor is %s" % money(
            size * (1 - rl["max_loss_pct"] / 100.0), cur)))
    print("  minimum trading days: %s; the day resets at midnight %s" % (rl["min_days"], rl["day_zone"]))
    if rl.get("news_minutes"):
        print("  news: no new trades %d minutes either side of high-impact releases on funded accounts "
              "(check your account type)" % rl["news_minutes"])
    print("  source: %s" % rl["source"])
    print("Rules change. Check them on the firm's site before you trade, and set overrides under \"prop_firm\" in "
          "trader/config.json.")
    return 0


def cmd_init(a, cfg):
    rl = rules_for(a, cfg)
    now = tc.parse_now(a.now, cfg["timezone"])
    day = firm_day(rl, now)
    st = {"preset": rl["preset"], "size": float(a.size), "currency": cfg["account_currency"], "phase": a.phase,
          "balance": float(a.size), "equity": float(a.size), "peak": float(a.size), "started": day, "today": day,
          "days": {day: {"start": float(a.size), "low": float(a.size), "traded": False}}, "log": []}
    tc.write_json(a.state, st)
    print("Tracking %s phase %d on %s from %s. Floors: daily %s, overall %s." % (
        rl["label"], a.phase, money(a.size, st["currency"]), day,
        money(a.size * (1 - rl["daily_loss_pct"] / 100.0), st["currency"]),
        money(a.size * (1 - rl["max_loss_pct"] / 100.0), st["currency"])))
    return 0


def cmd_update(a, cfg):
    st = load_state(a.state)
    rl = rules_for(a, cfg, st)
    now = tc.parse_now(a.now, cfg["timezone"])
    day = a.date or firm_day(rl, now)
    days = st.setdefault("days", {})
    if day not in days:
        days[day] = {"start": st["balance"], "low": st["equity"], "traded": False}
    st["today"] = day
    if a.balance is not None:
        st["balance"] = float(a.balance)
    st["equity"] = float(a.equity) if a.equity is not None else st["balance"]
    st["peak"] = max(st.get("peak", st["size"]), st["balance"])
    d = days[day]
    d["low"] = min(d.get("low", st["equity"]), st["equity"])
    if a.traded or abs(st["balance"] - d["start"]) > 1e-9:
        d["traded"] = True
    if a.phase:
        st["phase"] = a.phase
    st.setdefault("log", []).append({"at": tc.iso(now), "day": day, "balance": st["balance"], "equity": st["equity"]})
    tc.write_json(a.state, st)
    g = guardian_of(st, rl)
    print("Updated %s: balance %s, equity %s. %s" % (day, money(st["balance"], st["currency"]),
                                                    money(st["equity"], st["currency"]), g["status"]))
    return 0 if not g["breached"] else 1


def cmd_status(a, cfg):
    st = load_state(a.state)
    rl = rules_for(a, cfg, st)
    g = guardian_of(st, rl, a.equity, a.risk, a.streak, a.buffer)
    if a.json:
        print(json.dumps(dict(g, rules=rl["preset"], day=st.get("today")), indent=2))
        return 0 if not g["breached"] else 1
    cur = st["currency"]
    eq = a.equity if a.equity is not None else st["equity"]
    print("%s phase %d, day %s: equity %s on %s." % (rl["label"], st.get("phase", 1),
                                                    st.get("today"), money(eq, cur), money(st["size"], cur)))
    print("  daily floor %s, overall floor %s: the %s floor binds; room %s (%.2f%% of the initial balance)" % (
        money(g["daily_floor"], cur), money(g["overall_floor"], cur), g["binding_floor"], money(g["room"], cur),
        g["room_pct_initial"]))
    if g["target"]:
        way = "%s%% of the way" % g["progress_pct"] if (g["progress_pct"] or 0) >= 0 else "below the starting balance"
        print("  target %s: %s to go (%s), trading days %d of at least %d" % (
            money(g["target"], cur), money(max(0, g["to_target"]), cur), way, g["trading_days"], g["min_days"]))
    print("  largest risk per trade that survives %d losses in a row with a %.0f%% buffer: %s" % (
        g["streak_assumed"], g["buffer_pct"], money(g["max_risk_per_trade"], cur)))
    if a.risk:
        print("  at %s a trade, %s losses reach the floor" % (money(a.risk, cur), g["losses_to_floor"]))
    print("  status: %s" % g["status"])
    return 0 if not g["breached"] else 1


def cmd_check(a, cfg):
    st = load_state(a.state)
    rl = rules_for(a, cfg, st)
    g = guardian_of(st, rl, None, None, a.streak, a.buffer)
    doc = tc.read_json(a.orders, "orders (run trader-budget first)")
    orders = doc.get("orders", doc) if isinstance(doc, dict) else doc
    cur = st["currency"]
    bad, rows = 0, []
    for k, o in enumerate(orders, 1):
        plan = o.get("plan") or {}
        loss = o.get("max_loss") or plan.get("max_loss")
        if loss is None:
            rows.append((k, o.get("symbol"), None, "UNKNOWN: the order carries no max loss at the stop"))
            bad += 1
            continue
        loss = float(loss)
        if g["breached"] or g["status"].startswith("NO ROOM"):
            verdict = "BLOCK: %s" % g["status"]
        elif loss > g["max_risk_per_trade"]:
            verdict = "TOO BIG: %s at the stop is over the %s that %d losses in a row allow today" % (
                money(loss, cur), money(g["max_risk_per_trade"], cur), g["streak_assumed"])
        else:
            verdict = "OK: %s at the stop, %s of room left after a loss" % (money(loss, cur), money(g["room"] - loss, cur))
        if not verdict.startswith("OK"):
            bad += 1
        rows.append((k, o.get("symbol"), loss, verdict))
    if a.json:
        print(json.dumps([{"index": k, "symbol": s, "max_loss": l, "verdict": v} for k, s, l, v in rows], indent=2))
    else:
        print("%s: room %s, largest safe risk %s." % (rl["label"], money(g["room"], cur), money(g["max_risk_per_trade"], cur)))
        for k, s, l, v in rows:
            print("  order %d %s: %s" % (k, s, v))
    return 1 if bad else 0


def trades_from(a):
    if a.trades:
        doc = tc.read_json(a.trades, "lab result (lab.py run ... --save)")
        tr = doc.get("trades") if isinstance(doc, dict) else doc
        return [{"date": t["date"], "r": float(t["r"])} for t in tr or []], a.trades
    if a.journal:
        out = []
        with open(a.journal, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                r = row.get("R") or row.get("r")
                if r not in (None, ""):
                    out.append({"date": (row.get("Timestamp") or row.get("timestamp") or "")[:10], "r": float(r)})
        return out, a.journal
    raise tc.TraderError("give --trades trader/lab/<SYMBOL>/<SETUP>-<TF>.json or --journal trader/journal.csv")


def cmd_sim(a, cfg):
    rl = rules_for(a, cfg)
    trades, src = trades_from(a)
    if len(trades) < 20:
        raise tc.TraderError("only %d trades in %s: too few to simulate a challenge honestly" % (len(trades), src))
    risks = [float(x) for x in a.risks.split(",")]
    res = prop.best_risk(trades, rl, risks, sims=a.sims, phase=a.phase)
    if a.json:
        print(json.dumps(res, indent=2))
        return 0
    days = res["rows"][0]["trading_days_in_sample"]
    print("%s phase %d from %d real trades on %d trading days (%s), %d challenges each:" % (
        rl["label"], a.phase, len(trades), days, src, a.sims))
    print("  %-6s %7s %11s %9s %8s %12s" % ("RISK%", "PASS", "DAILY BUST", "MAX BUST", "TIMEOUT", "MEDIAN DAYS"))
    for row in res["rows"]:
        print("  %-6.2f %6.1f%% %10.1f%% %8.1f%% %7.1f%% %12s" % (
            row["risk_pct"], 100 * row["pass"], 100 * row["fail_daily"], 100 * row["fail_max"], 100 * row["timeout"],
            row["median_days"] or "-"))
    b = res["best"]
    print("Best: %.2f%% a trade passes %.1f%% of the time. Whole days are resampled in their real order, so a bad "
          "day stays a bad day; trades from a backtest are the best case." % (b["risk_pct"], 100 * b["pass"]))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Prop-firm rules, guardian and pass odds (trader-propfirm).")
    ap.add_argument("--config", default="trader/config.json")
    ap.add_argument("--state", default=STATE)
    ap.add_argument("--now", help="the clock (default now), e.g. '2026-11-16 08:45 London'")
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("rules")
    p.add_argument("--preset", choices=sorted(prop.PRESETS))
    p.add_argument("--size", type=float)
    p = sub.add_parser("init")
    p.add_argument("--size", type=float, required=True)
    p.add_argument("--preset", choices=sorted(prop.PRESETS))
    p.add_argument("--phase", type=int, default=1)
    p = sub.add_parser("update")
    p.add_argument("--balance", type=float)
    p.add_argument("--equity", type=float)
    p.add_argument("--traded", action="store_true", help="count today as a trading day")
    p.add_argument("--date", help="the firm's date (default: today in its zone)")
    p.add_argument("--phase", type=int)
    for name in ("status", "check"):
        p = sub.add_parser(name)
        p.add_argument("--streak", type=int, default=4, help="losses in a row to survive (default 4)")
        p.add_argument("--buffer", type=float, default=20.0, help="%% of the room kept back (default 20)")
        if name == "status":
            p.add_argument("--equity", type=float, help="the equity right now (default: the last update)")
            p.add_argument("--risk", type=float, help="your risk per trade in money")
        else:
            p.add_argument("--orders", default="trader/orders.json")
    p = sub.add_parser("sim")
    p.add_argument("--trades", help="a saved lab result: trader/lab/<SYMBOL>/<SETUP>-<TF>.json")
    p.add_argument("--journal", help="trader/journal.csv (rows with an R)")
    p.add_argument("--preset", choices=sorted(prop.PRESETS))
    p.add_argument("--phase", type=int, default=1)
    p.add_argument("--risks", default="0.25,0.5,0.75,1.0,1.5,2.0")
    p.add_argument("--sims", type=int, default=2000)
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        cfg = tc.load_config(a.config)
        return {"rules": cmd_rules, "init": cmd_init, "update": cmd_update, "status": cmd_status, "check": cmd_check,
                "sim": cmd_sim}[a.cmd](a, cfg)
    except (tc.TraderError, ValueError, OSError) as e:
        print("propfirm.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
