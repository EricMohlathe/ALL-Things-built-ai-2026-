#!/usr/bin/env python3
"""The Setup Lab: every GODMODE setup (GM01-GM26) and the claude-trader strategies, tested
one at a time on years of history, ranked honestly, stress-tested and sized for a prop
challenge. Standard library only.

    python3 lab.py list                                  # every setup, its family, its MT5 / cTrader files
    python3 lab.py run GM01 EURUSD                       # one setup on the cache (data.py get EURUSD first)
    python3 lab.py run GM03 XAUUSD --tf M15 --from 2023-01-01 --set target_r=3 --by hour
    python3 lab.py rank EURUSD XAUUSD                    # all setups x these markets, best first
    python3 lab.py rank EURUSD --family smc --save       # one family; save results for the desk/journal
    python3 lab.py optimize GM01 EURUSD                  # the grid, robustness, then walk-forward out of sample
    python3 lab.py mc GM14 US500 --risk 0.5              # Monte Carlo: drawdown and return percentiles
    python3 lab.py prop GM01 EURUSD --preset ftmo_2step  # pass probability at each risk size
    python3 lab.py tier GM07 BTCUSD                      # rolling on/off tiering (compendium 22.8)
    python3 lab.py portfolio EURUSD GBPUSD XAUUSD        # correlate daily R, keep the uncorrelated edges

Data: the trader-data cache by default (trader/data/<SYMBOL>/<TF>.csv, any finer timeframe
is resampled), --offline <folder or file> for a saved Yahoo chart (the test fixtures), or
--yahoo for the last 60 days of live 5-minute bars.

Costs are in every number: the instrument's typical spread (override --spread), slippage
(--slippage ticks) and commission (--commission per lot round turn). Results are in R.

Read every result as a hypothesis. A backtest is the best case: real fills, news spikes
and your own discipline only make it worse. Nothing here promises a profit.
"""

import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "trader-core"))
sys.path.insert(0, HERE)
import tradercore as tc  # noqa: E402
import engine  # noqa: E402
import stats  # noqa: E402
import prop  # noqa: E402
import history as hist  # noqa: E402
import setups as S  # noqa: E402
from bars import Bars, TF_NAME, tf_seconds  # noqa: E402

OUT = os.path.join("trader", "lab")
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


# ---------------------------------------------------------------- data and config

def _ts(text, end=False):
    if not text:
        return None
    d = datetime.date.fromisoformat(str(text)) if len(str(text)) == 10 else \
        datetime.date(int(str(text)[:4]), int(str(text)[5:7]) if len(str(text)) >= 7 else 1, 1)
    if end:
        d += datetime.timedelta(days=1)
    return tc.ts_of(datetime.datetime.combine(d, datetime.time()))


def load_bars(a, inst, tf):
    """The series for one instrument at `tf`, from the cache, an offline chart or Yahoo."""
    b, source = hist.series(inst, tf, a.data, a.offline, a.yahoo, _ts(a.frm), _ts(a.to, True))
    if len(b) < 200:
        raise tc.TraderError("only %d %s bars of %s: too few to test (download more with data.py get)"
                             % (len(b), TF_NAME.get(b.step, b.step), inst["symbol"]))
    return b, source


def engine_cfg(a, cfg, extra=None):
    out = {"spread": a.spread, "slippage_ticks": a.slippage, "commission_per_lot": a.commission,
           "sessions": cfg.get("sessions") or {}, "entry_cutoff_minutes": cfg.get("entry_cutoff_minutes", 30),
           "flat_by_minutes": cfg.get("flat_by_minutes", 5)}
    out.update(extra or {})
    return out


def parse_sets(items):
    out = {}
    for it in items or []:
        if "=" not in it:
            raise tc.TraderError("--set wants key=value, not %r" % it)
        k, v = it.split("=", 1)
        try:
            out[k.strip()] = json.loads(v)
        except ValueError:
            out[k.strip()] = v
    return out


def pick_setups(a):
    names = sorted(S.REGISTRY)
    if getattr(a, "setups", None):
        names = [S.get(x).name for x in a.setups.split(",") if x.strip()]
    if getattr(a, "family", None):
        names = [n for n in names if S.REGISTRY[n].family == a.family]
        if not names:
            raise tc.TraderError("no setups in family %r: %s" % (a.family, ", ".join(sorted(S.FAMILIES))))
    return names


def tf_for(a, setup):
    return a.tf or setup.tf


# ---------------------------------------------------------------- one run

def run_one(a, cfg, name, symbol, params=None, extra_cfg=None, bars_cache=None):
    setup = S.get(name)
    inst = tc.resolve(symbol, cfg)
    if inst["class"] not in setup.classes:
        return {"setup": setup.name, "symbol": inst["symbol"], "skipped": "not designed for %s" % inst["class"]}
    tf = tf_for(a, setup)
    key = (inst["symbol"], tf)
    if bars_cache is not None and key in bars_cache:
        b, source = bars_cache[key]
    else:
        b, source = load_bars(a, inst, tf)
        if bars_cache is not None:
            bars_cache[key] = (b, source)
    ecfg = engine_cfg(a, cfg, extra_cfg)
    if setup.name == "GM24" and getattr(a, "with_", None):
        ob, _ = load_bars(a, tc.resolve(a.with_, cfg), tf)
        ecfg["smt_bars"] = ob
    res = engine.run(b, setup, inst, params, ecfg)
    m = stats.metrics(res["trades"], risk_pct=a.risk)
    reasons = {}
    for s_ in res["signals"]:
        if not s_["taken"]:
            reasons[s_["reason"]] = reasons.get(s_["reason"], 0) + 1
    return {"setup": setup.name, "title": setup.title, "family": setup.family, "symbol": inst["symbol"],
            "tf": TF_NAME.get(b.step, str(b.step)), "source": source, "params": res["params"],
            "span": [tc.iso(tc.utc_of(x))[:10] if x else None for x in res["span"]], "bars": res["bars"],
            "signals": len(res["signals"]), "taken": sum(1 for s_ in res["signals"] if s_["taken"]),
            "not_taken": reasons, "metrics": m, "trades": res["trades"], "files": files_of(setup),
            "note": setup.note or None, "_bars": b, "_inst": inst, "_ecfg": ecfg}


def safe_run(a, cfg, name, symbol, cache):
    """run_one for the batch commands: a market without enough data is noted, not fatal."""
    try:
        return run_one(a, cfg, name, symbol, bars_cache=cache)
    except tc.TraderError as e:
        return {"setup": S.get(name).name, "symbol": symbol.upper(), "skipped": str(e).split(":")[0]}


def files_of(setup):
    out = {}
    for k, rel in setup.files().items():
        if rel:
            out[k] = {"path": rel, "exists": os.path.exists(os.path.join(REPO, rel))}
    return out


def public(r, with_trades=False):
    d = {k: v for k, v in r.items() if not k.startswith("_") and (with_trades or k != "trades")}
    return d


def save(r):
    path = os.path.join(OUT, r["symbol"], "%s-%s.json" % (r["setup"], r["tf"]))
    tc.write_json(path, public(r, with_trades=True))
    summ_path = os.path.join(OUT, "summary.json")
    summ = tc.read_json(summ_path, "lab summary", required=False) or {}
    m = r["metrics"]
    summ["%s:%s:%s" % (r["setup"], r["symbol"], r["tf"])] = {
        "setup": r["setup"], "symbol": r["symbol"], "tf": r["tf"], "family": r["family"], "span": r["span"],
        "trades": m["trades"], "win_rate": m.get("win_rate"), "expectancy_r": m.get("expectancy_r"),
        "profit_factor": m.get("profit_factor"), "p_value": m.get("p_value"), "p_adjusted_in_run": m.get("p_adjusted"),
        "max_dd_r": m.get("max_dd_r"),
        "verdict": m["verdict"], "params": r["params"], "saved": tc.iso(tc.utc_now())}
    tc.write_json(summ_path, summ)
    return path


# ---------------------------------------------------------------- printing

def fr(x, plus=True):
    if x is None:
        return "-"
    return ("%+.3fR" if plus else "%.3fR") % x


def fnum(x, fmt="%.2f"):
    return "-" if x is None else fmt % x


def print_metrics(m):
    if not m["trades"]:
        print("  no trades")
        return
    print("  %d trades, %.1f%% winners, expectancy %s a trade (95%% CI %s to %s), total %s" % (
        m["trades"], m["win_rate"], fr(m["expectancy_r"]), fr(m["ci95_expectancy"][0]), fr(m["ci95_expectancy"][1]),
        fr(m["total_r"])))
    print("  profit factor %s, payoff %s, SQN %s, t %s, p %s (one-sided: mean > 0)" % (
        fnum(m["profit_factor"]), fnum(m["payoff"]), fnum(m["sqn"]), fnum(m["t_stat"]), fnum(m["p_value"], "%.4f")))
    print("  max drawdown %s (%.1f%% at the --risk you gave), longest losing streak %d, average hold %.1f bars" % (
        fr(m["max_dd_r"], False), m["max_dd_pct"], m["longest_losing_streak"], m["avg_bars"]))
    print("  average heat (MAE) %s, average best (MFE) %s; exits %s" % (
        fr(m["avg_mae_r"], False), fr(m["avg_mfe_r"], False),
        ", ".join("%s %d" % kv for kv in m["outcomes"].items())))
    print("  verdict: %s" % m["verdict"])


def print_breakdown(trades, key, label):
    rows = stats.breakdown(trades, key)
    if not rows:
        return
    print("\n  by %s:" % label)
    print("    %-10s %6s %6s %9s %8s %6s" % ("", "TRADES", "WIN%", "EXP", "TOTAL", "PF"))
    for r in rows:
        print("    %-10s %6d %6.1f %9s %8.2f %6s" % (str(r["key"])[:10], r["trades"], r["win_rate"],
                                                    fr(r["expectancy_r"]), r["total_r"], fnum(r["profit_factor"])))


# ---------------------------------------------------------------- commands

def cmd_list(a, cfg):
    rows = []
    for n in pick_setups(a):
        c = S.REGISTRY[n]
        f = files_of(c)
        rows.append({"setup": n, "family": c.family, "tf": c.tf, "title": c.title, "classes": list(c.classes),
                     "grid": c.grid, "defaults": c.defaults, "files": f, "note": c.note or None})
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    for r in rows:
        print("%-5s %-14s %-4s %s" % (r["setup"], r["family"], r["tf"], r["title"]))
        for k, f in r["files"].items():
            print("      %-7s %s%s" % (k, f["path"], "" if f["exists"] else "  (not in this checkout)"))
        if r["note"]:
            print("      note: %s" % r["note"])
    print("\n%d setups in %d families: %s" % (len(rows), len(S.FAMILIES), ", ".join(sorted(S.FAMILIES))))
    return 0


def cmd_run(a, cfg):
    r = run_one(a, cfg, a.setup, a.symbol, parse_sets(a.set))
    if "skipped" in r:
        raise tc.TraderError("%s on %s: %s" % (r["setup"], r["symbol"], r["skipped"]))
    if a.save:
        r["saved"] = save(r)
    if a.json:
        print(json.dumps(public(r, with_trades=a.trades > 0), indent=2, default=str))
        return 0
    print("%s on %s %s (%s): %s" % (r["setup"], r["symbol"], r["tf"], r["source"], r["title"]))
    print("  %s to %s, %s bars; params %s" % (r["span"][0], r["span"][1], "{:,}".format(r["bars"]),
                                              json.dumps(r["params"], sort_keys=True)))
    print("  %d signals, %d taken; not taken: %s" % (r["signals"], r["taken"], ", ".join(
        "%s %d" % kv for kv in sorted(r["not_taken"].items(), key=lambda kv: -kv[1])) or "none"))
    print_metrics(r["metrics"])
    for by in a.by or []:
        print_breakdown(r["trades"], {"hour": "hour_ny", "weekday": "weekday", "side": "side", "regime": "regime",
                                      "outcome": "outcome", "tag": "tag"}.get(by, by), by + (" (New York)" if by == "hour" else ""))
    if a.trades:
        print("\n  last %d trades:" % a.trades)
        for t in r["trades"][-a.trades:]:
            print("    %s %-4s %-14s entry %-12g stop %-12g exit %-12g %-6s %s" % (
                tc.iso(tc.utc_of(t["entry_t"]))[:16], t["side"], (t["tag"] or "")[:14], t["entry"], t["stop"],
                t["exit"], t["outcome"], fr(t["r"])))
    for k, f in r["files"].items():
        print("  %s: %s" % (k, f["path"]))
    if r["note"]:
        print("  note: %s" % r["note"])
    if a.save:
        print("  saved %s" % r["saved"])
    return 0


def cmd_rank(a, cfg):
    cache, rows, skipped = {}, [], []
    for sym in a.symbols:
        for n in pick_setups(a):
            r = safe_run(a, cfg, n, sym, cache)
            if "skipped" in r:
                skipped.append(r)
                continue
            rows.append(r)
    rows.sort(key=lambda r: -stats.score(r["metrics"], a.min_trades))
    adj = stats.holm({i: r["metrics"].get("p_value") for i, r in enumerate(rows) if r["metrics"]["trades"]})
    for i, r in enumerate(rows):
        r["metrics"]["p_adjusted"] = adj.get(i)
        if a.save:
            save(r)
    if a.json:
        print(json.dumps({"ranked": [public(r) for r in rows], "not_applicable": skipped}, indent=2, default=str))
        return 0
    print("%-5s %-8s %-4s %-13s %6s %6s %9s %6s %7s %7s %6s %8s %5s" % (
        "SETUP", "SYMBOL", "TF", "FAMILY", "TRADES", "WIN%", "EXP", "PF", "P", "P(ADJ)", "SQN", "MAXDD", "SKIP"))
    for r in rows:
        m = r["metrics"]
        print("%-5s %-8s %-4s %-13s %6d %6s %9s %6s %7s %7s %6s %8s %5d" % (
            r["setup"], r["symbol"], r["tf"], r["family"][:13], m["trades"], fnum(m.get("win_rate"), "%.1f"),
            fr(m.get("expectancy_r")), fnum(m.get("profit_factor")), fnum(m.get("p_value"), "%.3f"),
            fnum(m.get("p_adjusted"), "%.3f"), fnum(m.get("sqn")), fr(m.get("max_dd_r"), False),
            sum(r["not_taken"].values())))
    tested = sum(1 for r in rows if r["metrics"]["trades"])
    lucky = [r for r in rows if r["metrics"]["trades"] >= 30 and (r["metrics"].get("expectancy_r") or 0) > 0
             and r["metrics"].get("p_value", 1) < 0.05]
    edges = [r for r in lucky if (r["metrics"].get("p_adjusted") or 1) < 0.05]
    print("\nRanked by expectancy x sqrt(trades) / stdev (fewer than %d trades sink to the bottom)." % a.min_trades)
    print("%d tests: about %.1f would show p < 0.05 by luck alone, so P(ADJ) (Holm) is the one to read."
          % (tested, 0.05 * tested))
    if edges:
        print("Edges that survive the correction (30+ trades, adjusted p < 0.05): %s. Next: optimize, then "
              "walk-forward." % ", ".join("%s@%s" % (r["setup"], r["symbol"]) for r in edges))
    elif lucky:
        print("Raw p < 0.05 but not after the correction (could be luck): %s. Test them on more history."
              % ", ".join("%s@%s" % (r["setup"], r["symbol"]) for r in lucky))
    else:
        print("No setup shows a significant positive edge on this data. That is a result, not a failure: "
              "do not trade what the numbers do not support.")
    why = {}
    for r in skipped:
        why.setdefault(r["skipped"], []).append("%s@%s" % (r["setup"], r["symbol"]))
    for reason, names in sorted(why.items()):
        print("Not run, %s: %s" % (reason, ", ".join(names)))
    return 0


def cmd_optimize(a, cfg):
    setup = S.get(a.setup)
    keys = a.keys.split(",") if a.keys else None
    grid = S.grid_of(setup, keys)
    base = run_one(a, cfg, setup.name, a.symbol)
    if "skipped" in base:
        raise tc.TraderError(base["skipped"])
    b, inst, ecfg = base["_bars"], base["_inst"], base["_ecfg"]
    results = []
    for p in grid:
        res = engine.run(b, S.get(setup.name), inst, p, ecfg)
        results.append((p, stats.metrics(res["trades"])))
    results.sort(key=lambda pm: -stats.score(pm[1], a.min_trades))
    rob = stats.robustness(results)
    days = (b.t[-1] - b.t[0]) / 86400.0
    test_days = a.test_days or max(5, int(days // 8))
    train_days = a.train_days or 3 * test_days

    def window(p, t0, t1):
        return engine.run(b, S.get(setup.name), inst, p, ecfg, start=t0, end=t1)["trades"]
    wf = stats.walk_forward(window, grid, b.t[0], b.t[-1] + b.step, train_days, test_days, min_trades=a.min_trades)
    doc = {"setup": setup.name, "symbol": inst["symbol"], "tf": base["tf"], "grid_size": len(grid),
           "top": [{"params": p, "trades": m["trades"], "expectancy_r": m.get("expectancy_r"),
                    "profit_factor": m.get("profit_factor"), "p_value": m.get("p_value")} for p, m in results[:10]],
           "robustness": rob, "walk_forward": {k: v for k, v in wf.items() if k != "oos_trades"},
           "train_days": train_days, "test_days": test_days}
    if a.json:
        print(json.dumps(doc, indent=2, default=str))
        return 0
    print("%s on %s %s: %d parameter sets" % (setup.name, inst["symbol"], base["tf"], len(grid)))
    for row in doc["top"]:
        print("  %-44s %5d trades  %9s  PF %-5s p %s" % (json.dumps(row["params"], sort_keys=True)[:44], row["trades"],
                                                       fr(row["expectancy_r"]), fnum(row["profit_factor"]),
                                                       fnum(row["p_value"], "%.3f")))
    print("\nRobustness: %s of %s tested sets are profitable; best %s, median %s.%s" % (
        rob.get("profitable_share"), rob.get("tested", 0), fr(rob.get("best")), fr(rob.get("median")),
        " WARNING: " + rob["warning"] if rob.get("warning") else ""))
    print("\nWalk-forward (%d-day train, %d-day test, %d folds): out-of-sample %d trades, expectancy %s "
          "(in-sample mean %s, efficiency %s)." % (
              train_days, test_days, len(wf["folds"]), wf["oos"]["trades"], fr(wf["oos_expectancy"]),
              fr(wf["is_mean_expectancy"]), fnum(wf["efficiency"])))
    for f in wf["folds"]:
        print("  test %s to %s: %-40s train %s (%d) -> test %s (%d)" % (
            tc.iso(tc.utc_of(f["test"][0]))[:10], tc.iso(tc.utc_of(f["test"][1]))[:10],
            json.dumps(f["params"], sort_keys=True)[:40], fr(f["train_expectancy"]), f["train_trades"],
            fr(f["test_expectancy"]), f["test_trades"]))
    print("  out-of-sample verdict: %s" % wf["oos"]["verdict"])
    print("Only the out-of-sample line counts. An efficiency under 0.5, or a negative out-of-sample "
          "expectancy, means the in-sample result was mostly fit to noise.")
    return 0


def cmd_mc(a, cfg):
    r = run_one(a, cfg, a.setup, a.symbol, parse_sets(a.set))
    rs = [t["r"] for t in r.get("trades") or []]
    if not rs:
        raise tc.TraderError("no trades to resample")
    mc = stats.monte_carlo(rs, a.sims, a.n or len(rs), a.risk, ruin_dd_pct=a.ruin)
    if a.json:
        print(json.dumps(mc, indent=2))
        return 0
    print("%s on %s: %d trades resampled %d times, %d trades a run, %.2f%% risk a trade" % (
        r["setup"], r["symbol"], len(rs), mc["sims"], mc["trades_per_sim"], a.risk))
    d, ret = mc["max_dd_pct"], mc["return_pct"]
    print("  max drawdown: median %.1f%%, 90th %.1f%%, 95th %.1f%%, 99th %.1f%%" % (d["p50"], d["p90"], d["p95"], d["p99"]))
    print("  return: 5th %.1f%%, median %.1f%%, 95th %.1f%%; a losing run %.1f%% of the time" % (
        ret["p5"], ret["p50"], ret["p95"], 100 * mc["p_loss"]))
    print("  a drawdown of %.0f%% or worse: %.1f%% of runs" % (a.ruin, 100 * mc["p_dd_over"]["probability"]))
    print("Plan for the 95th-percentile drawdown, not the median. Shuffling assumes trades are independent; "
          "real losing streaks cluster.")
    return 0


def cmd_prop(a, cfg):
    r = run_one(a, cfg, a.setup, a.symbol, parse_sets(a.set))
    trades = r.get("trades") or []
    if not trades:
        raise tc.TraderError("no trades to simulate")
    pcfg = dict(cfg.get("prop_firm") or {})
    if a.preset:
        pcfg["preset"] = a.preset
    rl = prop.rules(pcfg)
    risks = [float(x) for x in a.risks.split(",")]
    best = prop.best_risk(trades, rl, risks, sims=a.sims, phase=a.phase)
    if a.json:
        print(json.dumps({"rules": rl, "result": best}, indent=2))
        return 0
    print("%s on %s, %s phase %d (target %s%%, daily %s%%, max %s%%%s, min %s days): %d trading days of real trades" % (
        r["setup"], r["symbol"], rl["label"], a.phase, rl["targets_pct"][min(a.phase, len(rl["targets_pct"])) - 1],
        rl["daily_loss_pct"], rl["max_loss_pct"], " trailing" if rl["trailing"] else "", rl["min_days"],
        best["rows"][0]["trading_days_in_sample"]))
    print("  %-6s %7s %11s %9s %8s %12s" % ("RISK%", "PASS", "DAILY BUST", "MAX BUST", "TIMEOUT", "MEDIAN DAYS"))
    for row in best["rows"]:
        print("  %-6.2f %6.1f%% %10.1f%% %8.1f%% %7.1f%% %12s" % (
            row["risk_pct"], 100 * row["pass"], 100 * row["fail_daily"], 100 * row["fail_max"], 100 * row["timeout"],
            row["median_days"] or "-"))
    b = best["best"]
    print("Best pass rate at %.2f%% risk a trade: %.1f%%. Rules: %s. Sizing is fixed to the initial balance, "
          "as the firms measure it." % (b["risk_pct"], 100 * b["pass"], rl["source"]))
    if b["pass"] < 0.5:
        print("Under a coin flip at every size: this setup does not yet carry a challenge.")
    return 0


def cmd_tier(a, cfg):
    r = run_one(a, cfg, a.setup, a.symbol, parse_sets(a.set))
    tr = stats.tiering(r.get("trades") or [], a.window, a.min_trades, a.min_expectancy)
    if a.json:
        print(json.dumps(tr, indent=2, default=str))
        return 0
    ma, mt = tr["metrics_all"], tr["metrics_taken"]
    print("%s on %s, rolling %d trades (on after %d): took %d, sat out %d" % (
        r["setup"], r["symbol"], a.window, a.min_trades, tr["taken"], tr["skipped"]))
    print("  every trade: %d, expectancy %s, max DD %s" % (ma["trades"], fr(ma.get("expectancy_r")), fr(ma.get("max_dd_r"), False)))
    print("  tiered:      %d, expectancy %s, max DD %s" % (mt["trades"], fr(mt.get("expectancy_r")), fr(mt.get("max_dd_r"), False)))
    for s_ in tr["switches"][:20]:
        k = "off" if "off_at" in s_ else "on"
        print("  switched %-3s %s (rolling %s)" % (k, tc.iso(tc.utc_of(s_.get("off_at") or s_.get("on_at")))[:10],
                                                   fr(s_["rolling_expectancy"])))
    return 0


def cmd_portfolio(a, cfg):
    cache, cands, series = {}, {}, {}
    for sym in a.symbols:
        for n in pick_setups(a):
            r = safe_run(a, cfg, n, sym, cache)
            if "skipped" in r or not r["trades"]:
                continue
            key = "%s@%s" % (n, r["symbol"])
            cands[key] = r["metrics"]
            series[key] = stats.daily_r(r["trades"])
    adj = stats.holm({k: m.get("p_value") for k, m in cands.items()})
    for k, m in cands.items():
        m["p_raw"], m["p_value"] = m.get("p_value"), adj[k]
    out = stats.combine(cands, series, a.max_corr, a.min_p)
    kept = out["portfolio"]
    corr = stats.correlate({k: series[k] for k in kept}) if len(kept) >= 2 else None
    if a.json:
        print(json.dumps({"combine": out, "correlation": corr}, indent=2))
        return 0
    print("%d setup-market pairs tested; p-values are Holm-adjusted for that many tests." % len(cands))
    if kept:
        print("Kept (positive, adjusted p < %.2f, daily R correlation under %.2f with each other):" % (a.min_p, a.max_corr))
        for k in kept:
            m = cands[k]
            print("  %-14s %d trades, expectancy %s, p %.3f (raw %.3f)" % (k, m["trades"], fr(m["expectancy_r"]),
                                                                         m["p_value"], m["p_raw"]))
        if corr:
            for p in corr["pairs"]:
                print("  corr %s / %s: %s, in drawdown together %s" % (p["a"], p["b"], p["corr"], p["dd_overlap"]))
    else:
        print("Nothing qualifies: no pair is a significant, positive edge on this data.")
    rejected = [n for n in out["notes"] if not n["kept"] and "correlates" in n["why"]]
    for n in rejected[:10]:
        print("  dropped %s: %s" % (n["setup"], n["why"]))
    return 0


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description="The Setup Lab: test, rank and stress every GODMODE setup.")
    common = argparse.ArgumentParser(add_help=False)

    def globals_(p, real):
        d = (lambda v: v) if real else (lambda v: argparse.SUPPRESS)
        p.add_argument("--config", default=d("trader/config.json"))
        p.add_argument("--data", default=d(hist.CACHE), help="the trader-data cache (default trader/data)")
        p.add_argument("--offline", default=d(None), help="a saved Yahoo chart file or folder instead of the cache")
        p.add_argument("--yahoo", action="store_true", default=d(False), help="the last 60 days of live 5-minute bars")
        p.add_argument("--tf", default=d(None), help="timeframe (default: each setup's own, e.g. M5, M15, H1)")
        p.add_argument("--from", dest="frm", default=d(None))
        p.add_argument("--to", default=d(None))
        p.add_argument("--spread", type=float, default=d(None), help="override the typical spread (price units)")
        p.add_argument("--slippage", type=float, default=d(0.0), help="ticks of slippage on market entries and stops")
        p.add_argument("--commission", type=float, default=d(0.0), help="commission per lot, round turn")
        p.add_argument("--risk", type=float, default=d(1.0), help="%% of the account a trade risks (equity, MC)")
        p.add_argument("--min-trades", dest="min_trades", type=int, default=d(30))
        p.add_argument("--json", action="store_true", default=d(False))
    globals_(ap, True)
    globals_(common, False)
    sub = ap.add_subparsers(dest="cmd")

    def setups_opts(p):
        p.add_argument("--setups", help="comma list, e.g. GM01,GM03,CT01")
        p.add_argument("--family", help="one family, e.g. smc, liquidity, breakout")

    p = sub.add_parser("list", parents=[common])
    setups_opts(p)
    for name in ("run", "mc", "prop", "tier"):
        p = sub.add_parser(name, parents=[common])
        p.add_argument("setup")
        p.add_argument("symbol")
        p.add_argument("--set", action="append", help="a parameter, key=value (repeat)")
        p.add_argument("--with", dest="with_", help="GM24: the correlated market, e.g. GBPUSD")
        if name == "run":
            p.add_argument("--by", action="append", choices=["hour", "weekday", "side", "regime", "outcome", "tag"])
            p.add_argument("--trades", type=int, default=0, help="print the last N trades")
            p.add_argument("--save", action="store_true", help="write trader/lab/<SYMBOL>/<SETUP>-<TF>.json")
        if name == "mc":
            p.add_argument("--sims", type=int, default=2000)
            p.add_argument("--n", type=int, help="trades per simulated run (default: as many as tested)")
            p.add_argument("--ruin", type=float, default=20.0, help="the drawdown %% you could not live with")
        if name == "prop":
            p.add_argument("--preset", choices=sorted(prop.PRESETS))
            p.add_argument("--risks", default="0.25,0.5,0.75,1.0,1.5,2.0")
            p.add_argument("--phase", type=int, default=1)
            p.add_argument("--sims", type=int, default=2000)
        if name == "tier":
            p.add_argument("--window", type=int, default=100)
            p.add_argument("--min-expectancy", dest="min_expectancy", type=float, default=0.0)
    p = sub.add_parser("rank", parents=[common])
    p.add_argument("symbols", nargs="+")
    setups_opts(p)
    p.add_argument("--save", action="store_true")
    p.add_argument("--with", dest="with_")
    p = sub.add_parser("optimize", parents=[common])
    p.add_argument("setup")
    p.add_argument("symbol")
    p.add_argument("--keys", help="only vary these grid keys (comma list)")
    p.add_argument("--train-days", dest="train_days", type=int)
    p.add_argument("--test-days", dest="test_days", type=int)
    p.add_argument("--with", dest="with_")
    p = sub.add_parser("portfolio", parents=[common])
    p.add_argument("symbols", nargs="+")
    setups_opts(p)
    p.add_argument("--max-corr", dest="max_corr", type=float, default=0.3)
    p.add_argument("--min-p", dest="min_p", type=float, default=0.10)
    p.add_argument("--with", dest="with_")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        cfg = tc.load_config(a.config)
        return {"list": cmd_list, "run": cmd_run, "rank": cmd_rank, "optimize": cmd_optimize, "mc": cmd_mc,
                "prop": cmd_prop, "tier": cmd_tier, "portfolio": cmd_portfolio}[a.cmd](a, cfg)
    except (tc.TraderError, ValueError) as e:
        print("lab.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
