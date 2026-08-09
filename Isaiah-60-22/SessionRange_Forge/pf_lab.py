#!/usr/bin/env python3
"""
pf_lab.py — raise profit factor without giving up win rate.

    PF = (WR x avgWin) / ((1 - WR) x avgLoss)

Three terms, and almost everybody only ever touches one of them. Pushing the
target out raises avgWin and lowers WR, and the two effects mostly cancel.
The term with the most slack in it is usually the DENOMINATOR: the average
loss. A full stop-out is 1.0R. Anything that turns some of those into 0.3R
or 0.0R raises profit factor with no cost to win rate at all.

    python3 pf_lab.py journal.csv
    python3 pf_lab.py journal.csv --min-win-rate 0.62
    python3 pf_lab.py journal.csv --min-win-rate 0.62 --plots pf.png

WHAT IT SEARCHES

  target        the R multiple the position aims at
  break-even    move the stop to entry once the trade is +b R in your favour
  runner        bank a fraction at target, trail the rest to the session end

WHAT IT CAN AND CANNOT KNOW

The journal stores mfe_r and mae_r — the best and worst excursions — but not
the ORDER in which they happened. That asymmetry matters, and this script is
careful about it rather than pretending otherwise:

  SOUND    A trade that ended as a stop-out has its mfe_r measured BEFORE
           the stop. So if mfe_r >= b, a break-even stop at b would have
           been triggered before the loss landed, and that -1.0R becomes
           0.0R. This direction is firm.

  BOUNDED  A trade that ended as a win might ALSO have been scratched by
           the same break-even stop, if its pullback came after the trigger.
           The journal cannot say. So the script reports a RANGE: an
           optimistic bound where no winner is lost, and a pessimistic bound
           where every winner whose drawdown could have reached entry is
           scratched.

Read the pessimistic column. If the policy still wins there, it is real.

Every policy on the grid counts as a variant. The Sidak-adjusted bar is
printed and applied.

Not financial advice. This is a measurement instrument.
"""

from __future__ import annotations

import argparse
import itertools
import math
import sys

import numpy as np
import pandas as pd

RNG = np.random.default_rng(20260809)

BAR = "─" * 78


def rule(title: str = "") -> None:
    if title:
        pad = BAR[: max(0, 76 - len(title))]
        print(f"\n{title} {pad}")
    else:
        print(BAR)


def pf_str(pf: float) -> str:
    return "inf" if math.isinf(pf) else f"{pf:.2f}"


# ─────────────────────────────────────────────────────────────────────
# The identity
# ─────────────────────────────────────────────────────────────────────

def profit_factor(r: np.ndarray) -> float:
    gw = float(r[r > 0].sum()) if (r > 0).any() else 0.0
    gl = float(-r[r < 0].sum()) if (r < 0).any() else 0.0
    return (gw / gl) if gl > 0 else float("inf")


def decompose(r: np.ndarray) -> dict:
    wins = r[r > 0]
    losses = r[r < 0]
    scratches = r[r == 0]

    n = len(r)
    wr = len(wins) / n if n else 0.0
    aw = float(wins.mean()) if len(wins) else 0.0
    al = float(-losses.mean()) if len(losses) else 0.0

    return {
        "n": n,
        "wins": len(wins),
        "losses": len(losses),
        "scratches": len(scratches),
        "win_rate": wr,
        "avg_win": aw,
        "avg_loss": al,
        "payoff": (aw / al) if al > 0 else float("inf"),
        "profit_factor": profit_factor(r),
        "expectancy": float(r.mean()) if n else 0.0,
        "total_r": float(r.sum()),
    }


def report_decomposition(d: dict) -> None:
    rule("WHERE YOUR PROFIT FACTOR COMES FROM")
    print(f"  trades               {d['n']}")
    print(f"  wins / losses        {d['wins']} / {d['losses']}"
          + (f"  ({d['scratches']} scratched)" if d["scratches"] else ""))
    print()
    print(f"  win rate       WR    {d['win_rate']:.2%}")
    print(f"  average win    aW    {d['avg_win']:.3f} R")
    print(f"  average loss   aL    {d['avg_loss']:.3f} R   <- the term with the slack")
    print(f"  payoff ratio   aW/aL {d['payoff']:.3f}")
    print()
    print(f"  PF = (WR x aW) / ((1-WR) x aL)")
    print(f"     = ({d['win_rate']:.4f} x {d['avg_win']:.3f}) / "
          f"({1-d['win_rate']:.4f} x {d['avg_loss']:.3f})")
    print(f"     = {pf_str(d['profit_factor'])}")
    print()
    print(f"  expectancy           {d['expectancy']:+.4f} R per trade")

    # sensitivity: what each 10% improvement in a term is worth
    if d["avg_loss"] > 0 and d["win_rate"] < 1:
        base = d["profit_factor"]
        pf_al = (d["win_rate"] * d["avg_win"]) / ((1 - d["win_rate"]) * d["avg_loss"] * 0.9)
        pf_aw = (d["win_rate"] * d["avg_win"] * 1.1) / ((1 - d["win_rate"]) * d["avg_loss"])
        wr2 = min(0.99, d["win_rate"] + 0.03)
        pf_wr = (wr2 * d["avg_win"]) / ((1 - wr2) * d["avg_loss"])

        rule("WHAT EACH LEVER IS WORTH")
        print(f"  current PF                        {pf_str(base)}")
        print(f"  cut the average LOSS by 10%       {pf_str(pf_al)}   "
              f"({pf_al - base:+.2f})")
        print(f"  raise the average WIN by 10%      {pf_str(pf_aw)}   "
              f"({pf_aw - base:+.2f})")
        print(f"  add 3 points of win rate          {pf_str(pf_wr)}   "
              f"({pf_wr - base:+.2f})")
        print()
        print("  Cutting losses and raising wins are worth the same in the")
        print("  algebra — but cutting losses does not cost you win rate, and")
        print("  raising wins almost always does. That is why the stop side is")
        print("  where the cheap profit factor lives.")


# ─────────────────────────────────────────────────────────────────────
# Policy reconstruction
# ─────────────────────────────────────────────────────────────────────

# TRAIL CAPTURE
# A trailing stop never exits at the excursion peak — it gives back the
# trail distance. Assuming peak capture is the single easiest way to make a
# runner look better than it is, so the runner is credited with only this
# fraction of the move beyond target.
TRAIL_CAPTURE = 0.60


def apply_policy(df: pd.DataFrame, target: float, be_trigger: float,
                 runner_frac: float, cost_r: float,
                 pessimistic: bool) -> np.ndarray:
    """
    Rebuild each trade's result under a candidate exit policy.

    target       R multiple the position aims at
    be_trigger   move stop to ENTRY once mfe_r >= this (0 = no break-even)
    runner_frac  fraction of the position left to run past target, trailed
                 (0 = flat at target)
    pessimistic  worst-case ordering of the excursions — see below

    Ordering. The journal stores how far the trade ran each way but not in
    which order. Two cases, handled differently and honestly:

      Losers   mfe_r is measured before the stop-out, so "did the trade
               reach the trigger before it died" is answerable. Firm.

      Winners  a break-even stop sits at ENTRY once armed, so it scratches
               the trade only if price returned to entry AFTER arming. Any
               mae_r > 0 means price was below entry at some point, but not
               when. The pessimistic bound assumes the worst — every armed
               winner that ever traded below entry gets scratched.
    """
    mfe = df["mfe_r"].to_numpy()
    mae = df["mae_r"].to_numpy()

    out = np.empty(len(df), dtype=float)

    for i in range(len(df)):
        f, a = mfe[i], mae[i]

        if f >= target:
            if runner_frac > 0:
                banked = (1.0 - runner_frac) * target
                captured = target + TRAIL_CAPTURE * max(0.0, f - target)
                res = banked + runner_frac * captured
            else:
                res = target

            # worst-case: the pullback came after the stop was armed at entry
            if pessimistic and be_trigger > 0 and f >= be_trigger and a > 0.0:
                res = 0.0

        else:
            # failed to reach target, went on to the stop
            if be_trigger > 0 and f >= be_trigger:
                res = 0.0            # FIRM: mfe precedes the stop-out
            else:
                res = -1.0

        out[i] = res - cost_r

    return out


def day_bootstrap_p(r: np.ndarray, days: np.ndarray, n_boot: int = 4000) -> float:
    tmp = pd.DataFrame({"r": r, "d": days})
    day_r = tmp.groupby("d")["r"].mean().to_numpy()
    n = len(day_r)
    if n < 2:
        return 1.0
    idx = RNG.integers(0, n, size=(n_boot, n))
    return float((day_r[idx].mean(axis=1) <= 0).mean())


def sidak_alpha(alpha: float, k: int) -> float:
    return 1.0 - (1.0 - alpha) ** (1.0 / max(1, k))


# ─────────────────────────────────────────────────────────────────────
# Search
# ─────────────────────────────────────────────────────────────────────

def search(df: pd.DataFrame, targets, be_triggers, runners,
           cost_r: float, min_wr: float) -> list[dict]:
    days = df["ny_day"].to_numpy()
    rows = []

    for t, b, f in itertools.product(targets, be_triggers, runners):
        if b > 0 and b >= t:
            continue                      # a BE trigger at or past target is moot

        opt = apply_policy(df, t, b, f, cost_r, pessimistic=False)
        pes = apply_policy(df, t, b, f, cost_r, pessimistic=True)

        d_opt = decompose(opt)
        d_pes = decompose(pes)

        rows.append({
            "target": t, "be": b, "runner": f,
            "wr_opt": d_opt["win_rate"], "pf_opt": d_opt["profit_factor"],
            "e_opt": d_opt["expectancy"],
            "wr_pes": d_pes["win_rate"], "pf_pes": d_pes["profit_factor"],
            "e_pes": d_pes["expectancy"],
            "avg_loss_pes": d_pes["avg_loss"], "avg_win_pes": d_pes["avg_win"],
            "p_pes": day_bootstrap_p(pes, days),
            "_r_pes": pes,
        })

    return rows


def report_search(rows: list[dict], min_wr: float, alpha: float,
                  extra_variants: int, base_pf: float) -> dict | None:
    n_var = len(rows) + extra_variants
    a = sidak_alpha(alpha, n_var)

    # the constraint is on the PESSIMISTIC win rate — the bound that has to hold
    eligible = [r for r in rows if r["wr_pes"] >= min_wr and not math.isinf(r["pf_pes"])]

    rule(f"POLICIES THAT HOLD WIN RATE >= {min_wr:.0%}  (pessimistic bound)")
    if not eligible:
        best_wr = max(rows, key=lambda r: r["wr_pes"])
        print(f"  None. The highest pessimistic win rate on the grid is "
              f"{best_wr['wr_pes']:.1%}")
        print(f"  at target {best_wr['target']:.2f}R / BE {best_wr['be']:.2f}R.")
        print("  Lower --min-win-rate, or accept that this entry does not")
        print("  support the win rate you are asking it to hold.")
        return None

    eligible.sort(key=lambda r: -r["pf_pes"])

    print(f"  {'target':>7} {'BE at':>7} {'runner':>7}   "
          f"{'WR':>7} {'aWin':>6} {'aLoss':>6} {'PF':>7} {'E[R]':>8} {'p':>8}")
    print(f"  {'-'*7} {'-'*7} {'-'*7}   {'-'*7} {'-'*6} {'-'*6} "
          f"{'-'*7} {'-'*8} {'-'*8}")

    for r in eligible[:15]:
        star = "  <-" if r is eligible[0] else ""
        print(f"  {r['target']:>6.2f}R {r['be']:>6.2f}R {r['runner']:>6.0%}   "
              f"{r['wr_pes']:>6.1%} {r['avg_win_pes']:>6.2f} "
              f"{r['avg_loss_pes']:>6.2f} {pf_str(r['pf_pes']):>7} "
              f"{r['e_pes']:>+7.3f}R {r['p_pes']:>8.4f}{star}")

    best = eligible[0]

    rule("THE POLICY")
    print(f"  target               {best['target']:.2f} R")
    print(f"  break-even stop at   "
          + (f"{best['be']:.2f} R" if best["be"] > 0 else "off"))
    print(f"  runner               "
          + (f"{best['runner']:.0%} of the position left to trail"
             if best["runner"] > 0 else "off"))
    print()
    print(f"  {'':22}{'pessimistic':>13} {'optimistic':>13}")
    print(f"  win rate          {best['wr_pes']:>12.1%} {best['wr_opt']:>13.1%}")
    print(f"  profit factor     {pf_str(best['pf_pes']):>12} "
          f"{pf_str(best['pf_opt']):>13}")
    print(f"  expectancy        {best['e_pes']:>+11.3f}R {best['e_opt']:>+12.3f}R")
    print()
    print(f"  average win          {best['avg_win_pes']:.3f} R")
    print(f"  average loss         {best['avg_loss_pes']:.3f} R")
    print()
    if base_pf > 0 and not math.isinf(base_pf):
        print(f"  profit factor moved  {pf_str(base_pf)} -> "
              f"{pf_str(best['pf_pes'])}  "
              f"({best['pf_pes'] - base_pf:+.2f} on the pessimistic bound)")
    print(f"  p(mean <= 0)         {best['p_pes']:.4f}")
    print(f"  Sidak bar            {a:.5f}  ({n_var} policies searched)")
    print(f"  clears the bar       {'YES' if best['p_pes'] < a else 'NO'}")

    return best


def report_settings(best: dict) -> None:
    rule("HOW TO SET THIS IN THE EAs")

    if best["runner"] > 0:
        print("  MT5")
        print(f"    InpExitMode       = I22_EXIT_R_THEN_TIME")
        print(f"    InpTargetR        = {best['target']:.2f}")
        print(f"    InpPartialAtR     = {best['target']:.2f}")
        print(f"    InpPartialPercent = {(1 - best['runner']) * 100:.0f}")
        if best["be"] > 0:
            print(f"    InpBreakevenAtR   = {best['be']:.2f}")
        print()
        print("  cTrader")
        print(f"    Exit mode         = RThenTime")
        print(f"    Target in R       = {best['target']:.2f}")
        print(f"    Partial at R      = {best['target']:.2f}")
        print(f"    Partial percent   = {(1 - best['runner']) * 100:.0f}")
        if best["be"] > 0:
            print(f"    Break-even at R   = {best['be']:.2f}")
    else:
        print("  MT5")
        print(f"    InpExitMode       = I22_EXIT_FIXED_R")
        print(f"    InpTargetR        = {best['target']:.2f}")
        if best["be"] > 0:
            print(f"    InpBreakevenAtR   = {best['be']:.2f}")
        print()
        print("  cTrader")
        print(f"    Exit mode         = FixedR")
        print(f"    Target in R       = {best['target']:.2f}")
        if best["be"] > 0:
            print(f"    Break-even at R   = {best['be']:.2f}")

    print()
    print("  Then RE-RUN the backtest with these settings and grade the real")
    print("  journal. This search reconstructs from excursions; the live path")
    print("  is the only thing that settles it. Carry the policy count into")
    print("  --variants when you do.")


def report_breakeven_verdict(rows: list[dict], min_wr: float) -> None:
    """
    Break-even is the one lever this data cannot settle, because it turns on
    excursion ORDER. Say so, and quantify how much is at stake either way.
    """
    be_rows = [r for r in rows if r["be"] > 0]
    if not be_rows:
        return

    best_opt = max(be_rows, key=lambda r: r["pf_opt"])
    best_pes = max(be_rows, key=lambda r: r["pf_pes"])

    survives = [r for r in be_rows if r["wr_pes"] >= min_wr]

    rule("BREAK-EVEN STOPS — THE ONE THING THIS DATA CANNOT SETTLE")
    print("  A break-even stop helps by converting stop-outs that first went")
    print("  your way into scratches, and hurts by scratching winners that")
    print("  dipped after arming. Which dominates depends on the ORDER of the")
    print("  excursions, and the journal does not record order.")
    print()
    print(f"  best BE policy, optimistic    BE {best_opt['be']:.2f}R  ->  "
          f"PF {pf_str(best_opt['pf_opt'])}  at {best_opt['wr_opt']:.1%} win rate")
    print(f"  best BE policy, pessimistic   BE {best_pes['be']:.2f}R  ->  "
          f"PF {pf_str(best_pes['pf_pes'])}  at {best_pes['wr_pes']:.1%} win rate")
    print()

    if not survives:
        print(f"  No break-even policy holds the {min_wr:.0%} floor under the worst")
        print("  case, so none was recommended above. That is the bound being")
        print("  cautious, NOT evidence that break-even hurts.")
    else:
        print(f"  {len(survives)} break-even policies hold the floor even under the")
        print("  worst case. Those are worth testing first.")

    print()
    print("  Settle it properly — it is one backtest:")
    print(f"    MT5       InpBreakevenAtR = {best_opt['be']:.2f}   (else 0)")
    print(f"    cTrader   Break-even at R = {best_opt['be']:.2f}   (else 0)")
    print("  Run it twice, once with and once without, everything else fixed,")
    print("  and compare the two journals. The live path resolves the ordering")
    print("  that this reconstruction has to bracket.")


def write_plots(rows: list[dict], min_wr: float, path: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print(f"\n  (matplotlib not installed — skipping {path})")
        return

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))

    wr = [r["wr_pes"] * 100 for r in rows]
    pf = [min(r["pf_pes"], 8) for r in rows]
    be = [r["be"] for r in rows]

    sc = ax[0].scatter(wr, pf, c=be, cmap="viridis", s=28)
    ax[0].axvline(min_wr * 100, color="crimson", linestyle="--",
                  label=f"{min_wr:.0%} floor")
    ax[0].set_xlabel("win rate (%)"); ax[0].set_ylabel("profit factor (capped 8)")
    ax[0].set_title("Every policy — colour is the break-even trigger")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)
    fig.colorbar(sc, ax=ax[0], label="BE trigger (R)")

    keep = [r for r in rows if r["wr_pes"] >= min_wr]
    if keep:
        al = [r["avg_loss_pes"] for r in keep]
        pf2 = [min(r["pf_pes"], 8) for r in keep]
        ax[1].scatter(al, pf2, color="darkgreen", s=28)
        ax[1].set_xlabel("average loss (R)"); ax[1].set_ylabel("profit factor")
        ax[1].set_title("Profit factor against the average loss")
        ax[1].grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"\n  charts -> {path}")


# ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Raise profit factor while holding a win-rate floor.")
    ap.add_argument("csv", help="path to the EA's CSV journal")
    ap.add_argument("--min-win-rate", type=float, default=0.62,
                    help="win-rate floor the policy must hold (default 0.62)")
    ap.add_argument("--cost-r", type=float, default=0.0,
                    help="round-trip cost in R, subtracted from every trade")
    ap.add_argument("--max-target", type=float, default=3.0)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--variants", type=int, default=0,
                    help="variants tried BEFORE this search; the grid adds its own")
    ap.add_argument("--plots", default=None)
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    df.columns = [c.strip().lower() for c in df.columns]

    need = ["ny_day", "r_realized", "mfe_r", "mae_r"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        sys.exit(f"Journal is missing required columns: {missing}\n"
                 f"Found: {list(df.columns)}\n"
                 f"pf_lab needs mfe_r AND mae_r — the excursions are what make "
                 f"the reconstruction possible.")

    for c in ("r_realized", "mfe_r", "mae_r"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=need).copy()
    df["ny_day"] = df["ny_day"].astype(str)

    print()
    print("  pf_lab.py — profit factor has a denominator")
    rule()
    print(f"  file        {args.csv}")
    print(f"  trades      {len(df)}")
    print(f"  sessions    {df['ny_day'].nunique()}")
    if args.cost_r > 0:
        print(f"  cost        {args.cost_r:.3f} R per trade, applied")

    base = decompose(df["r_realized"].to_numpy())
    report_decomposition(base)

    targets = [round(x, 2) for x in np.arange(0.75, args.max_target + 1e-9, 0.25)]
    be_triggers = [0.0, 0.3, 0.5, 0.75, 1.0]
    runners = [0.0, 0.25, 0.5]

    rows = search(df, targets, be_triggers, runners, args.cost_r, args.min_win_rate)
    best = report_search(rows, args.min_win_rate, args.alpha,
                         args.variants, base["profit_factor"])

    if best:
        report_settings(best)
        report_breakeven_verdict(rows, args.min_win_rate)

    if args.plots:
        write_plots(rows, args.min_win_rate, args.plots)

    print()


if __name__ == "__main__":
    main()
