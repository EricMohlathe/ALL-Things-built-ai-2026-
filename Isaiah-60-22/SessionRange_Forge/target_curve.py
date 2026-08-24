#!/usr/bin/env python3
"""
target_curve.py — where to sit on the win-rate / payout curve.

Win rate and profit factor are the same dial turned in opposite directions.
You do not choose them independently; you choose a TARGET, and the target
decides both. This script finds where that dial should sit on YOUR data,
instead of on a number somebody put in a thumbnail.

    python3 target_curve.py journal.csv
    python3 target_curve.py journal.csv --want-win-rate 0.60
    python3 target_curve.py journal.csv --cost-r 0.05 --plots curve.png
    python3 target_curve.py --feasible 0.60          # no data: just the algebra

THE ALGEBRA, ONCE

    break-even win rate   WR0 = 1 / (1 + R)
    profit factor         PF  = WR x R / (1 - WR)
    expectancy            E   = WR x R - (1 - WR)          [in R, before cost]

So a 60% win rate is worth PF 1.50 at a 1:1 target and PF 4.50 at 3:1 — and
the second one implies +1.40 R per trade, which compounds a $1,000 account
into eight figures inside two years. High win rate AND high payout is not a
harder version of the same goal. It is a different, unavailable goal.

HOW THE RECONSTRUCTION WORKS

The journal records mfe_r: how far the trade ran in your favour, measured
BEFORE it exited. That means for any candidate target X we can ask "did this
trade reach X before it resolved?" and get a sound answer:

    mfe_r >= X   ->  the trade would have paid +X at target X
    mfe_r <  X   ->  the trade would have gone on to hit the stop, -1

This is valid DOWNWARD only. If the run used a fixed 2R target, no trade was
ever allowed to show an MFE above 2R, so the data cannot tell you what a 3R
target would have done. That censoring is detected and reported rather than
silently extrapolated.

    To explore targets ABOVE your current one, re-run the EA with
    InpExitMode = I22_EXIT_TIME_ONLY (MT5) / Exit = TimeOnly (cTrader).
    That records the full uncensored excursion.

THE HONESTY TAX

Scanning a grid of targets and keeping the best one is optimisation, and
optimisation inflates results exactly the way tuning does. Every target on
the grid counts as a variant, and the Sidak correction is applied on that
basis. The number this script prints as "recommended" has already paid that
tax; the number you would have got by eyeballing the peak has not.

Not financial advice. This is a measurement instrument.
"""

from __future__ import annotations

import argparse
import math
import sys

import numpy as np
import pandas as pd

RNG = np.random.default_rng(20260809)

BAR = "─" * 74


def rule(title: str = "") -> None:
    if title:
        pad = BAR[: max(0, 72 - len(title))]
        print(f"\n{title} {pad}")
    else:
        print(BAR)


# ─────────────────────────────────────────────────────────────────────
# The algebra
# ─────────────────────────────────────────────────────────────────────

def breakeven_win_rate(target_r: float) -> float:
    return 1.0 / (1.0 + target_r)


def profit_factor(win_rate: float, target_r: float) -> float:
    losses = (1.0 - win_rate)
    if losses <= 0:
        return float("inf")
    return (win_rate * target_r) / losses


def expectancy(win_rate: float, target_r: float, cost_r: float = 0.0) -> float:
    return win_rate * target_r - (1.0 - win_rate) * 1.0 - cost_r


def feasibility_table(want_wr: float, cost_r: float = 0.0) -> None:
    """What a given win rate is worth at each payout, and what it demands."""
    rule(f"WHAT A {want_wr:.0%} WIN RATE MEANS AT EACH TARGET")
    print(f"  {'target':>8}  {'break-even':>11}  {'edge needed':>12}  "
          f"{'profit factor':>14}  {'expectancy':>11}")
    print(f"  {'':>8}  {'win rate':>11}  {'over B/E':>12}  {'':>14}  {'per trade':>11}")
    print(f"  {'-'*8}  {'-'*11}  {'-'*12}  {'-'*14}  {'-'*11}")

    for r in (0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0):
        we = breakeven_win_rate(r)
        edge_pp = (want_wr - we) * 100.0
        pf = profit_factor(want_wr, r)
        e = expectancy(want_wr, r, cost_r)
        flag = ""
        if edge_pp <= 0:
            flag = "  <- loses money"
        elif e > 1.0:
            flag = "  <- self-refuting"
        elif e > 0.5:
            flag = "  <- implausible"
        elif e > 0.25:
            flag = "  <- exceptional"
        print(f"  {r:>7.2f}R  {we:>10.1%}  {edge_pp:>+10.1f}pp  "
              f"{pf:>14.2f}  {e:>+10.2f}R{flag}")

    print()
    print("  'Edge over B/E' is the number that has to come from the strategy.")
    print("  Everything above about +15pp has, in published testing, been a")
    print("  selection artifact rather than a repeatable edge.")

    # what a claim compounds to
    best = expectancy(want_wr, 3.0, cost_r)
    if best > 0:
        bal, y2, y3 = 1000.0, 0.0, 0.0
        for i in range(750):                      # three 250-trade years
            bal *= (1.0 + 0.01 * best)
            if i == 249:
                y1 = bal
            elif i == 499:
                y2 = bal
        y3 = bal
        print()
        print(f"  Sanity check: {want_wr:.0%} at 3:1 is {best:+.2f}R per trade.")
        print(f"  At 1% risk, 250 trades a year, $1,000 becomes:")
        print(f"    year 1  ${y1:>14,.0f}")
        print(f"    year 2  ${y2:>14,.0f}")
        print(f"    year 3  ${y3:>14,.0f}")
        print("  If those numbers look wrong, the win rate is the thing that is wrong.")


# ─────────────────────────────────────────────────────────────────────
# Journal handling
# ─────────────────────────────────────────────────────────────────────

REQUIRED = ["ny_day", "r_realized", "mfe_r"]


def load_journal(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        sys.exit(f"Journal is missing required columns: {missing}\n"
                 f"Found: {list(df.columns)}\n"
                 f"This tool needs mfe_r — it is what makes the reconstruction possible.")

    for c in ("r_realized", "mfe_r", "mae_r"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=["r_realized", "mfe_r"]).copy()
    df["ny_day"] = df["ny_day"].astype(str)
    return df


def detect_censoring(df: pd.DataFrame) -> tuple[float | None, float]:
    """
    A fixed-R run truncates MFE at the target. Detect it by looking for a
    pile-up of winners at one MFE value.

    Returns (censor_level, fraction_of_trades_at_that_level).
    """
    wins = df[df["r_realized"] > 0]
    if len(wins) < 10:
        return None, 0.0

    rounded = wins["mfe_r"].round(2)
    mode_val = rounded.mode()
    if mode_val.empty:
        return None, 0.0

    level = float(mode_val.iloc[0])
    share = float((rounded == level).mean())

    # a real distribution does not put a third of its mass on one value
    if share >= 0.30 and level > 0:
        return level, share
    return None, share


# ─────────────────────────────────────────────────────────────────────
# The curve
# ─────────────────────────────────────────────────────────────────────

def reconstruct(df: pd.DataFrame, target_r: float, cost_r: float) -> dict:
    """
    What this strategy would have produced at a target of `target_r`,
    holding the entry and the stop constant.
    """
    reached = df["mfe_r"].to_numpy() >= target_r
    r = np.where(reached, target_r, -1.0) - cost_r

    n = len(r)
    wins = int(reached.sum())
    wr = wins / n if n else 0.0

    gross_win = float(r[r > 0].sum()) if (r > 0).any() else 0.0
    gross_loss = float(-r[r < 0].sum()) if (r < 0).any() else 0.0
    pf = (gross_win / gross_loss) if gross_loss > 0 else float("inf")

    # per-session means: trades on one morning are one bet, not many
    tmp = df.copy()
    tmp["_r"] = r
    day_r = tmp.groupby("ny_day")["_r"].mean().to_numpy()

    return {
        "target_r": target_r,
        "n": n,
        "wins": wins,
        "win_rate": wr,
        "breakeven_wr": breakeven_win_rate(target_r),
        "edge_pp": (wr - breakeven_win_rate(target_r)) * 100.0,
        "profit_factor": pf,
        "expectancy": float(r.mean()),
        "day_r": day_r,
        "total_r": float(r.sum()),
    }


def day_bootstrap_ci(day_r: np.ndarray, n_boot: int = 10000) -> tuple[float, float, float]:
    """Resample SESSIONS, not trades. Returns (lo, hi, p(mean<=0))."""
    n = len(day_r)
    if n < 2:
        return (float("nan"), float("nan"), 1.0)
    idx = RNG.integers(0, n, size=(n_boot, n))
    means = day_r[idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    p = float((means <= 0).mean())
    return float(lo), float(hi), p


def sidak_alpha(alpha: float, k: int) -> float:
    k = max(1, k)
    return 1.0 - (1.0 - alpha) ** (1.0 / k)


def scan(df: pd.DataFrame, grid: np.ndarray, cost_r: float) -> list[dict]:
    return [reconstruct(df, float(t), cost_r) for t in grid]


# ─────────────────────────────────────────────────────────────────────
# Reporting
# ─────────────────────────────────────────────────────────────────────

def report_curve(rows: list[dict], censor: float | None, want_wr: float,
                 alpha: float, extra_variants: int) -> dict | None:
    rule("THE CURVE ON YOUR DATA")
    print(f"  {'target':>8}  {'win rate':>9}  {'B/E':>7}  {'edge':>8}  "
          f"{'PF':>7}  {'E[R]':>8}  {'total R':>9}")
    print(f"  {'-'*8}  {'-'*9}  {'-'*7}  {'-'*8}  {'-'*7}  {'-'*8}  {'-'*9}")

    for row in rows:
        mark = ""
        if censor is not None and row["target_r"] > censor + 1e-9:
            mark = "  (censored)"
        pf = row["profit_factor"]
        pf_s = "inf" if math.isinf(pf) else f"{pf:.2f}"
        print(f"  {row['target_r']:>7.2f}R  {row['win_rate']:>8.1%}  "
              f"{row['breakeven_wr']:>6.1%}  {row['edge_pp']:>+7.1f}pp  "
              f"{pf_s:>7}  {row['expectancy']:>+7.3f}R  "
              f"{row['total_r']:>+8.1f}R{mark}")

    usable = [r for r in rows
              if censor is None or r["target_r"] <= censor + 1e-9]
    if not usable:
        print("\n  Every target on the grid is above the censoring level.")
        print("  Re-run with a time-only exit before trusting any of this.")
        return None

    # ── where the money actually is
    best_e = max(usable, key=lambda r: r["expectancy"])

    # ── the requested win rate: report the LARGEST payout that still clears
    # ── it, since that is the most reward the requested floor allows
    hits_wr = [r for r in usable if r["win_rate"] >= want_wr]
    at_wr = max(hits_wr, key=lambda r: r["target_r"]) if hits_wr else None

    n_variants = len(rows) + extra_variants
    a = sidak_alpha(alpha, n_variants)

    rule("WHERE THE DIAL SHOULD SIT")

    lo, hi, p = day_bootstrap_ci(best_e["day_r"])
    pf = best_e["profit_factor"]
    pf_s = "inf" if math.isinf(pf) else f"{pf:.2f}"
    print(f"  Highest expectancy   {best_e['target_r']:.2f}R target")
    print(f"    win rate           {best_e['win_rate']:.1%}   "
          f"(break-even {best_e['breakeven_wr']:.1%}, edge {best_e['edge_pp']:+.1f}pp)")
    print(f"    profit factor      {pf_s}")
    print(f"    expectancy         {best_e['expectancy']:+.3f} R per trade")
    print(f"    95% CI (sessions)  [{lo:+.4f}, {hi:+.4f}]   p(mean<=0) = {p:.4f}")
    print(f"    survives haircut   {'YES' if p < a else 'NO'}   "
          f"(need p < {a:.5f} for {n_variants} variants)")

    print()
    if at_wr is not None:
        lo2, hi2, p2 = day_bootstrap_ci(at_wr["day_r"])
        pf2 = at_wr["profit_factor"]
        pf2_s = "inf" if math.isinf(pf2) else f"{pf2:.2f}"
        print(f"  Your {want_wr:.0%} win-rate request lands at "
              f"{at_wr['target_r']:.2f}R")
        print(f"    win rate           {at_wr['win_rate']:.1%}")
        print(f"    profit factor      {pf2_s}")
        print(f"    expectancy         {at_wr['expectancy']:+.3f} R per trade")
        print(f"    95% CI (sessions)  [{lo2:+.4f}, {hi2:+.4f}]   p(mean<=0) = {p2:.4f}")

        cost = best_e["expectancy"] - at_wr["expectancy"]
        if cost > 1e-6:
            print(f"    price of the ask   {cost:.3f} R per trade given up to buy "
                  f"{(at_wr['win_rate'] - best_e['win_rate'])*100:+.1f}pp of win rate")
        elif cost < -1e-6:
            print("    this target is ALSO the expectancy peak — no trade-off here.")
    else:
        top = max(usable, key=lambda r: r["win_rate"])
        print(f"  A {want_wr:.0%} win rate does not occur anywhere on this grid.")
        print(f"  The highest reachable is {top['win_rate']:.1%} at "
              f"{top['target_r']:.2f}R (PF {top['profit_factor']:.2f}, "
              f"E {top['expectancy']:+.3f}R).")
        print("  Lowering the target further raises the win rate and lowers the")
        print("  payout; below the break-even line that is a losing system with")
        print("  a pretty hit rate.")

    return best_e


def report_censoring(censor: float | None, share: float) -> None:
    if censor is None:
        return
    rule("CENSORING WARNING")
    print(f"  {share:.0%} of winning trades show an MFE of exactly {censor:.2f}R.")
    print("  That is a fixed target truncating the excursion, not a market")
    print("  phenomenon. Nothing above that level can be reconstructed from")
    print("  this file — those rows are marked (censored) and excluded from")
    print("  the recommendation.")
    print()
    print("  To see the whole curve, re-run with:")
    print("    MT5       InpExitMode = I22_EXIT_TIME_ONLY")
    print("    cTrader   Exit        = TimeOnly")
    print("  then bring that journal back here.")


def write_plots(rows: list[dict], censor: float | None, want_wr: float, path: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print(f"\n  (matplotlib not installed — skipping {path})")
        return

    t = [r["target_r"] for r in rows]
    wr = [r["win_rate"] * 100 for r in rows]
    be = [r["breakeven_wr"] * 100 for r in rows]
    pf = [min(r["profit_factor"], 10) for r in rows]
    e = [r["expectancy"] for r in rows]

    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))

    ax[0].plot(t, wr, marker="o", label="your win rate")
    ax[0].plot(t, be, linestyle="--", label="break-even 1/(1+R)")
    ax[0].axhline(want_wr * 100, color="crimson", linestyle=":", label=f"{want_wr:.0%} requested")
    ax[0].set_xlabel("target (R)"); ax[0].set_ylabel("win rate (%)")
    ax[0].set_title("Win rate is a function of target")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)

    ax[1].plot(t, pf, marker="o", color="darkgreen")
    ax[1].axhline(1.0, color="grey", linestyle="--")
    ax[1].set_xlabel("target (R)"); ax[1].set_ylabel("profit factor (capped at 10)")
    ax[1].set_title("Profit factor")
    ax[1].grid(alpha=0.3)

    ax[2].plot(t, e, marker="o", color="darkorange")
    ax[2].axhline(0.0, color="grey", linestyle="--")
    ax[2].set_xlabel("target (R)"); ax[2].set_ylabel("expectancy (R/trade)")
    ax[2].set_title("Expectancy — the only one that pays")
    ax[2].grid(alpha=0.3)

    if censor is not None:
        for a in ax:
            a.axvspan(censor, max(t), color="red", alpha=0.08)

    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"\n  charts -> {path}")


# ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Find where the win-rate / payout dial should sit on your data.")
    ap.add_argument("csv", nargs="?", help="path to the EA's CSV journal")
    ap.add_argument("--feasible", type=float, default=None, metavar="WR",
                    help="skip the data, just print the algebra for this win rate")
    ap.add_argument("--want-win-rate", type=float, default=0.60,
                    help="the win rate you are aiming for (default 0.60)")
    ap.add_argument("--cost-r", type=float, default=0.0,
                    help="round-trip cost in R, subtracted from every trade")
    ap.add_argument("--min-r", type=float, default=0.25)
    ap.add_argument("--max-r", type=float, default=5.0)
    ap.add_argument("--step-r", type=float, default=0.25)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--variants", type=int, default=0,
                    help="variants you already tried BEFORE this scan; the grid "
                         "adds its own on top")
    ap.add_argument("--plots", default=None)
    args = ap.parse_args()

    print()
    print("  target_curve.py — win rate and payout are one dial, not two")
    rule()

    if args.feasible is not None:
        feasibility_table(args.feasible, args.cost_r)
        print()
        return

    if not args.csv:
        feasibility_table(args.want_win_rate, args.cost_r)
        print()
        print("  Pass a journal CSV to see where your own strategy actually sits.")
        print()
        return

    df = load_journal(args.csv)
    n_days = df["ny_day"].nunique()

    print(f"  file        {args.csv}")
    print(f"  trades      {len(df)}")
    print(f"  sessions    {n_days}")
    if "model" in df.columns and df["model"].nunique() == 1:
        print(f"  model       {df['model'].iloc[0]}")
    if args.cost_r > 0:
        print(f"  cost        {args.cost_r:.3f} R per trade, applied")

    if n_days < 100:
        print()
        print(f"  NOTE: {n_days} sessions is below the 100 the forensics script")
        print("  requires. Read the curve as a direction, not a decision.")

    feasibility_table(args.want_win_rate, args.cost_r)

    censor, share = detect_censoring(df)
    report_censoring(censor, share)

    grid = np.arange(args.min_r, args.max_r + 1e-9, args.step_r)
    rows = scan(df, grid, args.cost_r)

    best = report_curve(rows, censor, args.want_win_rate, args.alpha, args.variants)

    rule("WHAT TO DO WITH THIS")
    if best is None:
        print("  Re-run with a time-only exit, then come back.")
    else:
        print(f"  1. The expectancy peak is at {best['target_r']:.2f}R. That is the")
        print("     target this entry earns, not the one you wish it earned.")
        print("  2. Raising the win rate means lowering the target. That is a")
        print("     legitimate choice — it trades expectancy for smoother equity")
        print("     and easier psychology. Make it knowingly.")
        print("  3. This scan was an optimisation. Feed the chosen target back")
        print("     through srf_forensics.py on HELD-OUT sessions before")
        print("     believing it:")
        print(f"       python3 srf_forensics.py {args.csv} "
              f"--target-r {best['target_r']:.2f} --variants {len(rows) + args.variants}")
    print()

    if args.plots:
        write_plots(rows, censor, args.want_win_rate, args.plots)
        print()


if __name__ == "__main__":
    main()
