"""stats: how good is an edge, really? Standard library only.

  metrics        trades, win rate, payoff, expectancy (R), profit factor, max drawdown
                 (R and compounded %), Sharpe and Sortino per trade, SQN, the longest losing
                 streak, MAE/MFE, a t-statistic and p-value for "the mean R is above zero"
  breakdown      the same per hour, weekday, side, regime, tag ...
  monte_carlo    resample the trade sequence: the drawdown and return you should EXPECT,
                 not the one history happened to deal, and the odds of a deep drawdown
  walk_forward   optimise on a window, trade the next unseen one, roll on: only the unseen
                 results count; plus the in-sample vs out-of-sample decay
  tiering        the compendium's adaptive tiering (Brief 22.8): a rolling window per
                 setup, switched off when its rolling edge decays, back on when it returns
  correlation    daily R series of several setups, their correlation and drawdown overlap,
                 and a greedy pick of setups that are each positive and do not lose together

The honesty contract (compendium, Brief A.6): >= 100-200 trades before a number means much,
one change at a time, and some setups will have no edge. These functions say so in their
verdicts instead of hiding it.
"""

import math
import random


def _mean(x):
    return sum(x) / len(x) if x else 0.0


def _std(x):
    if len(x) < 2:
        return 0.0
    m = _mean(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))


def p_value(t, df):
    """Two-sided p-value of a t-statistic. Student's t for small df (series), normal above 30."""
    t = abs(t)
    if df < 1:
        return 1.0
    if df >= 30:
        return math.erfc(t / math.sqrt(2))
    x = df / (df + t * t)
    return _betainc(df / 2.0, 0.5, x)


def _betainc(a, b, x):
    """Regularized incomplete beta I_x(a, b) by continued fraction (Numerical Recipes)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b + lbeta)
    if x > (a + 1) / (a + b + 2):
        return 1.0 - _betainc(b, a, 1 - x)
    f, c, d = 1.0, 1.0, 0.0
    for i in range(200):
        m = i // 2
        if i == 0:
            num = 1.0
        elif i % 2 == 0:
            num = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            num = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + num * d
        d = 1.0 / (d if abs(d) > 1e-30 else 1e-30)
        c = 1.0 + num / (c if abs(c) > 1e-30 else 1e-30)
        f *= c * d
        if abs(1.0 - c * d) < 1e-12:
            break
    return front * (f - 1.0) / a


def drawdown(equity):
    """(max drawdown in units, max drawdown fraction of the peak) of an equity path."""
    peak, mdd, mdd_pct = equity[0] if equity else 0.0, 0.0, 0.0
    for e in equity:
        peak = max(peak, e)
        mdd = max(mdd, peak - e)
        if peak > 0:
            mdd_pct = max(mdd_pct, (peak - e) / peak)
    return mdd, mdd_pct


def metrics(trades, risk_pct=1.0, start=10000.0):
    """The scorecard of a list of trades (each with 'r')."""
    rs = [t["r"] for t in trades]
    n = len(rs)
    out = {"trades": n}
    if not n:
        return dict(out, verdict="no trades")
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    gross_win, gross_loss = sum(wins), -sum(losses)
    m, s = _mean(rs), _std(rs)
    eq_r, cum = [0.0], 0.0
    eq_c = [start]
    streak = worst = 0
    for r in rs:
        cum += r
        eq_r.append(cum)
        eq_c.append(eq_c[-1] * (1 + risk_pct / 100.0 * r))
        streak = streak + 1 if r <= 0 else 0
        worst = max(worst, streak)
    dd_r, _ = drawdown([x + 1e9 for x in eq_r])
    _, dd_pct = drawdown(eq_c)
    downside = [min(0.0, r) for r in rs]
    dd = math.sqrt(sum(x * x for x in downside) / n)
    t = m / (s / math.sqrt(n)) if s > 0 else 0.0
    p = p_value(t, n - 1) / 2.0 if t > 0 else 1.0 - p_value(t, n - 1) / 2.0   # one-sided: mean > 0
    out.update({
        "wins": len(wins), "win_rate": round(100.0 * len(wins) / n, 2),
        "avg_win_r": round(_mean(wins), 3) if wins else 0.0, "avg_loss_r": round(_mean(losses), 3) if losses else 0.0,
        "payoff": round(_mean(wins) / -_mean(losses), 3) if wins and losses and _mean(losses) < 0 else None,
        "expectancy_r": round(m, 4), "stdev_r": round(s, 4), "total_r": round(sum(rs), 3),
        "profit_factor": round(gross_win / gross_loss, 3) if gross_loss > 0 else None,
        "max_dd_r": round(dd_r, 3), "max_dd_pct": round(100 * dd_pct, 2),
        "final_equity": round(eq_c[-1], 2), "return_pct": round(100 * (eq_c[-1] / start - 1), 2),
        "sharpe_trade": round(m / s, 4) if s > 0 else None, "sortino_trade": round(m / dd, 4) if dd > 0 else None,
        "sqn": round(math.sqrt(min(n, 100)) * m / s, 3) if s > 0 else None,
        "t_stat": round(t, 3), "p_value": round(p, 4),
        "ci95_expectancy": [round(m - 1.96 * s / math.sqrt(n), 4), round(m + 1.96 * s / math.sqrt(n), 4)],
        "longest_losing_streak": worst,
        "avg_bars": round(_mean([t.get("bars", 0) for t in trades]), 1),
        "avg_mae_r": round(_mean([t.get("mae_r", 0) for t in trades]), 3),
        "avg_mfe_r": round(_mean([t.get("mfe_r", 0) for t in trades]), 3),
        "outcomes": {k: sum(1 for t in trades if t.get("outcome") == k) for k in
                     sorted({t.get("outcome") for t in trades if t.get("outcome")})},
    })
    out["verdict"] = verdict(out)
    return out


def verdict(m):
    """One honest line from the numbers."""
    n = m["trades"]
    if n < 30:
        return "too few trades (%d) to say anything; collect at least 100-200" % n
    if m["expectancy_r"] <= 0:
        return "no edge: the average trade loses %.3f R after costs" % -m["expectancy_r"]
    sig = m["p_value"] < 0.05
    if n < 100:
        return ("promising but thin: +%.3f R a trade over %d trades (p = %.3f); keep collecting" %
                (m["expectancy_r"], n, m["p_value"]))
    if not sig:
        return "positive but not significant: +%.3f R a trade, p = %.3f; could be luck" % (m["expectancy_r"], m["p_value"])
    return "an edge on this data: +%.3f R a trade over %d trades, p = %.4f, PF %s; now prove it out of sample" % (
        m["expectancy_r"], n, m["p_value"], m["profit_factor"])


def breakdown(trades, key, min_n=1):
    groups = {}
    for t in trades:
        k = t.get(key) if not callable(key) else key(t)
        groups.setdefault(k, []).append(t)
    out = []
    for k, ts in groups.items():
        if len(ts) < min_n:
            continue
        rs = [t["r"] for t in ts]
        gw, gl = sum(r for r in rs if r > 0), -sum(r for r in rs if r <= 0)
        out.append({"key": k, "trades": len(ts), "win_rate": round(100.0 * sum(1 for r in rs if r > 0) / len(rs), 1),
                    "expectancy_r": round(_mean(rs), 3), "total_r": round(sum(rs), 2),
                    "profit_factor": round(gw / gl, 2) if gl > 0 else None})
    return sorted(out, key=lambda x: (str(type(x["key"])), x["key"] if x["key"] is not None else ""))


def monte_carlo(rs, sims=2000, n_trades=None, risk_pct=1.0, seed=7, ruin_dd_pct=20.0):
    """Bootstrap the R sequence. Percentiles of max drawdown (%) and return (%), and the odds of a
    drawdown worse than ruin_dd_pct."""
    if not rs:
        return None
    rng = random.Random(seed)
    n = n_trades or len(rs)
    dds, rets, ruined = [], [], 0
    for _ in range(sims):
        eq = 1.0
        peak = 1.0
        mdd = 0.0
        for _k in range(n):
            eq *= 1 + risk_pct / 100.0 * rng.choice(rs)
            if eq > peak:
                peak = eq
            mdd = max(mdd, (peak - eq) / peak)
        dds.append(100 * mdd)
        rets.append(100 * (eq - 1))
        if 100 * mdd >= ruin_dd_pct:
            ruined += 1
    dds.sort()
    rets.sort()
    q = lambda a, p: a[min(len(a) - 1, int(p * len(a)))]  # noqa: E731
    return {"sims": sims, "trades_per_sim": n, "risk_pct": risk_pct, "seed": seed,
            "max_dd_pct": {"p50": round(q(dds, .5), 2), "p90": round(q(dds, .9), 2), "p95": round(q(dds, .95), 2),
                           "p99": round(q(dds, .99), 2)},
            "return_pct": {"p5": round(q(rets, .05), 2), "p50": round(q(rets, .5), 2), "p95": round(q(rets, .95), 2)},
            "p_dd_over": {"threshold_pct": ruin_dd_pct, "probability": round(ruined / float(sims), 4)},
            "p_loss": round(sum(1 for r in rets if r < 0) / float(sims), 4)}


def daily_r(trades):
    out = {}
    for t in trades:
        out[t["date"]] = out.get(t["date"], 0.0) + t["r"]
    return out


def walk_forward(run_window, grid, t0, t1, train_days, test_days, objective=None, min_trades=10):
    """run_window(params, a, b) -> trades for bars in [a, b). Rolls (train, test) windows across
    [t0, t1): picks the best params on each train window, keeps only the TEST trades.
    Returns {folds, oos_trades, oos, is_mean_expectancy, oos_expectancy, efficiency}."""
    objective = objective or score
    folds, oos, is_exp = [], [], []
    a = t0
    day = 86400
    while a + (train_days + test_days) * day <= t1:
        b, c = a + train_days * day, a + (train_days + test_days) * day
        best, best_s, best_m = None, -1e18, None
        for p in grid:
            tr = run_window(p, a, b)
            mm = metrics(tr)
            s = objective(mm, min_trades)
            if s > best_s:
                best, best_s, best_m = p, s, mm
        test = run_window(best, b, c)
        tm = metrics(test)
        folds.append({"train": [a, b], "test": [b, c], "params": best, "train_expectancy": best_m.get("expectancy_r"),
                      "train_trades": best_m["trades"], "test_expectancy": tm.get("expectancy_r"),
                      "test_trades": tm["trades"]})
        oos.extend(test)
        if best_m.get("expectancy_r") is not None:
            is_exp.append(best_m["expectancy_r"])
        a += test_days * day
    om = metrics(oos)
    ism = _mean(is_exp) if is_exp else None
    eff = (om.get("expectancy_r", 0) / ism) if ism and ism > 0 and om["trades"] else None
    return {"folds": folds, "oos_trades": oos, "oos": om, "is_mean_expectancy": round(ism, 4) if ism is not None else None,
            "oos_expectancy": om.get("expectancy_r"), "efficiency": round(eff, 3) if eff is not None else None}


def holm(pvals):
    """Holm-Bonferroni: {name: p} -> {name: adjusted p}. Test 28 setups on 6 markets and about
    8 of the 168 will show p < 0.05 by luck alone; the adjusted p is what survives that."""
    items = sorted(((p if p is not None else 1.0), k) for k, p in pvals.items())
    m, out, run = len(items), {}, 0.0
    for j, (p, k) in enumerate(items):
        run = max(run, min(1.0, (m - j) * p))
        out[k] = round(run, 4)
    return out


def score(m, min_trades=10):
    """The optimiser's objective: expectancy weighted by sample size (a t-stat-like score), with
    too-few-trade results thrown out. Never raw net profit, never win rate."""
    if m["trades"] < min_trades or m.get("stdev_r") in (None, 0):
        return -1e9
    return m["expectancy_r"] * math.sqrt(m["trades"]) / max(m["stdev_r"], 1e-9)


def robustness(results):
    """Across a parameter grid's results [(params, metrics)]: the share of combinations that
    are profitable and the spread between the best and the median: a lone best surrounded by
    losers is a curve fit."""
    exps = sorted(m.get("expectancy_r", -1) for _, m in results if m["trades"] >= 10)
    if not exps:
        return {"combos": len(results), "profitable_share": None}
    med = exps[len(exps) // 2]
    return {"combos": len(results), "tested": len(exps),
            "profitable_share": round(sum(1 for e in exps if e > 0) / float(len(exps)), 3),
            "best": exps[-1], "median": med,
            "warning": "the best is far above the median: likely a curve fit" if exps[-1] > 0 and
            (med <= 0 or exps[-1] > 3 * med) else None}


def tiering(trades, window=200, min_trades=50, min_expectancy=0.0, min_win_rate=None):
    """Compendium Brief 22.8, adaptive tiering: the setup trades while its rolling window
    (the last `window` trades it WOULD have taken, simulated) shows expectancy above
    min_expectancy (and win rate above min_win_rate, if given) once min_trades exist.
    Returns {taken, skipped, switch_offs, metrics_all, metrics_taken}."""
    hist, taken, switches, on = [], [], [], True
    for t in trades:
        if on:
            taken.append(t)
        hist.append(t["r"])
        w = hist[-window:]
        if len(w) >= min_trades:
            ok = _mean(w) > min_expectancy
            if min_win_rate is not None:
                ok = ok and 100.0 * sum(1 for r in w if r > 0) / len(w) >= min_win_rate
            if on and not ok:
                switches.append({"off_at": t["entry_t"], "rolling_expectancy": round(_mean(w), 3)})
            elif not on and ok:
                switches.append({"on_at": t["entry_t"], "rolling_expectancy": round(_mean(w), 3)})
            on = ok
    return {"taken": len(taken), "skipped": len(trades) - len(taken), "switches": switches,
            "metrics_all": metrics(trades), "metrics_taken": metrics(taken)}


def correlate(series_by_name):
    """{name: {date: R}} -> pairwise correlation of daily R, and of being in drawdown together."""
    names = sorted(series_by_name)
    days = sorted(set(d for s in series_by_name.values() for d in s))
    vec = {n: [series_by_name[n].get(d, 0.0) for d in days] for n in names}
    under = {}
    for n in names:
        cum, peak, u = 0.0, 0.0, []
        for x in vec[n]:
            cum += x
            peak = max(peak, cum)
            u.append(1.0 if cum < peak else 0.0)
        under[n] = u
    import indicators as ind
    pairs = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            pairs.append({"a": a, "b": b, "corr": _r(ind.correlation(vec[a], vec[b])),
                          "dd_overlap": _r(_overlap(under[a], under[b]))})
    return {"names": names, "days": len(days), "pairs": pairs}


def _r(x):
    return None if x is None else round(x, 3)


def _overlap(a, b):
    both = sum(1 for x, y in zip(a, b) if x and y)
    either = sum(1 for x, y in zip(a, b) if x or y)
    return both / float(either) if either else 0.0


def combine(candidates, series_by_name, max_corr=0.3, min_p=0.10):
    """Greedy recombination (compendium 7.4 step 5): take setups in order of t-stat, keep each
    one that is positive with p < min_p and whose daily R correlates under max_corr with every
    setup already kept."""
    import indicators as ind
    keep, notes = [], []
    for name, m in sorted(candidates.items(), key=lambda kv: -(kv[1].get("t_stat") or -1e9)):
        if m["trades"] < 30 or m.get("expectancy_r", 0) <= 0 or m.get("p_value", 1) >= min_p:
            notes.append({"setup": name, "kept": False, "why": "not a significant positive edge"})
            continue
        days = sorted(set(series_by_name[name]) | set(d for k in keep for d in series_by_name[k]))
        clash = None
        for k in keep:
            c = ind.correlation([series_by_name[name].get(d, 0.0) for d in days],
                                [series_by_name[k].get(d, 0.0) for d in days])
            if c is not None and c > max_corr:
                clash = (k, c)
                break
        if clash:
            notes.append({"setup": name, "kept": False, "why": "correlates %.2f with %s" % (clash[1], clash[0])})
        else:
            keep.append(name)
            notes.append({"setup": name, "kept": True, "why": "positive, significant and uncorrelated"})
    return {"portfolio": keep, "notes": notes}
