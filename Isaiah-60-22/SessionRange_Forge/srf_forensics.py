#!/usr/bin/env python3
"""
srf_forensics.py — Session-Range Forge trade-journal forensics.

Runs the five tests that separate a real edge from a coin flip with a
flattering equity curve. Reads the CSV written by GODMODE_SessionRange_Forge.mq5
(or any CSV with the same column names) and returns a pass/fail verdict.

    python3 srf_forensics.py journal.csv
    python3 srf_forensics.py journal.csv --target-r 2.0 --oos 0.3 --variants 12
    python3 srf_forensics.py --demo            # synthetic coin flip, to see the tool bite

The tests, in the order they can kill a strategy:

  T1  BREAK-EVEN GAP     Is the win rate above 1/(1+R), the payout-implied
                         break-even? Tested per-trade AND per-day.
  T2  DAY CLUSTERING     Trades on the same session are one bet, not many.
                         Block-bootstrap over days, not over trades.
  T3  EXCURSION SYMMETRY If mean MFE ~ mean MAE, the entry carries no
                         directional information — the payout, not the
                         signal, is producing the win rate.
  T4  COST SURVIVAL      Sweep round-trip cost upward. Where does the edge
                         die? If that number is near your real spread, the
                         edge is an artifact.
  T5  SELECTION HAIRCUT  Adjust the p-value for how many variants you tried.
                         Sidak, not hope.

Not financial advice. This is a measurement instrument.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

RNG = np.random.default_rng(20260809)

# ─────────────────────────────────────────────────────────────────────
# Presentation helpers
# ─────────────────────────────────────────────────────────────────────

BAR = "─" * 74


def rule(title: str = "") -> None:
    if title:
        pad = BAR[: max(0, 72 - len(title))]
        print(f"\n{title} {pad}")
    else:
        print(BAR)


def verdict_tag(passed: bool | None) -> str:
    if passed is None:
        return "  N/A "
    return " PASS " if passed else " FAIL "


# ─────────────────────────────────────────────────────────────────────
# Loading
# ─────────────────────────────────────────────────────────────────────

REQUIRED = ["ny_day", "r_realized"]
OPTIONAL = ["mfe_r", "mae_r", "risk_points", "spread_pts_entry", "model",
            "direction", "entry_time_ny", "symbol", "run_tag", "exit_reason"]


def load_journal(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        sys.exit(f"Journal is missing required columns: {missing}\n"
                 f"Found: {list(df.columns)}")

    for c in ["r_realized", "mfe_r", "mae_r", "risk_points", "spread_pts_entry"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=["r_realized"]).copy()
    df["ny_day"] = df["ny_day"].astype(str)

    # Chronological order matters for the out-of-sample split.
    sort_key = "entry_time_ny" if "entry_time_ny" in df.columns else "ny_day"
    df = df.sort_values(sort_key, kind="stable").reset_index(drop=True)
    return df


def make_demo(n_days: int = 420, per_day: int = 2, target_r: float = 2.0) -> pd.DataFrame:
    """A pure coin flip with a 2:1 payout, plus realistic day clustering.

    Win probability is set exactly at the payout break-even. A correct
    forensics engine must refuse to call this an edge.
    """
    rows = []
    p_be = 1.0 / (1.0 + target_r)
    start = pd.Timestamp("2024-01-01")
    for d in range(n_days):
        day = (start + pd.Timedelta(days=d)).strftime("%Y-%m-%d")
        # Day-level regime shock: trades on the same day are correlated.
        shock = RNG.normal(0, 0.35)
        for k in range(per_day):
            p = np.clip(p_be + shock * 0.10, 0.05, 0.95)
            win = RNG.random() < p
            r = target_r if win else -1.0
            # Excursions are bounded by the exits: a winner never touched the
            # stop, a loser never reached the target. Within those barriers a
            # directionless path wanders roughly uniformly.
            if win:
                mfe = target_r
                mae = -float(np.clip(RNG.beta(1.6, 1.6), 0.02, 0.98))
            else:
                mfe = float(np.clip(RNG.beta(1.6, 1.6) * target_r, 0.0, target_r * 0.98))
                mae = -1.0
            rows.append(dict(
                run_tag="demo", symbol="DEMO", model="MODEL_BREAK_DIRECT",
                ny_day=day, entry_time_ny=f"{day} 09:{36 + k * 7:02d}:00",
                direction="LONG" if RNG.random() < 0.5 else "SHORT",
                r_realized=r, mfe_r=round(mfe, 3), mae_r=round(mae, 3),
                risk_points=180.0, spread_pts_entry=12.0,
                exit_reason="TARGET" if win else "STOP",
            ))
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────
# Statistics
# ─────────────────────────────────────────────────────────────────────

def breakeven_win_rate(target_r: float) -> float:
    return 1.0 / (1.0 + target_r)


def day_means(df: pd.DataFrame, col: str = "r_realized") -> np.ndarray:
    """One number per session. This is the unit of independent evidence."""
    return df.groupby("ny_day")[col].mean().to_numpy()


def block_bootstrap(df: pd.DataFrame, n_boot: int = 20000,
                    col: str = "r_realized") -> tuple[np.ndarray, float, float, float]:
    """Resample whole DAYS with replacement. Returns (dist, lo95, hi95, p_one_sided)."""
    dm = day_means(df, col)
    n = len(dm)
    if n < 2:
        return np.array([dm.mean() if n else 0.0]), 0.0, 0.0, 1.0
    idx = RNG.integers(0, n, size=(n_boot, n))
    dist = dm[idx].mean(axis=1)
    lo, hi = np.percentile(dist, [2.5, 97.5])
    p = float((dist <= 0).mean())          # P(mean R <= 0) under resampling
    return dist, float(lo), float(hi), p


def binom_p_greater(k: int, n: int, p0: float) -> float:
    """One-sided binomial: P(X >= k | n, p0). Normal approx with continuity
    correction for large n, exact-ish sum for small n."""
    if n == 0:
        return 1.0
    if n <= 2000:
        from math import comb
        return float(sum(comb(n, i) * p0 ** i * (1 - p0) ** (n - i) for i in range(k, n + 1)))
    mu = n * p0
    sd = math.sqrt(n * p0 * (1 - p0))
    z = (k - 0.5 - mu) / sd if sd > 0 else 0.0
    return 0.5 * math.erfc(z / math.sqrt(2))


def sidak_alpha(alpha: float, k_variants: int) -> float:
    k = max(1, k_variants)
    return 1.0 - (1.0 - alpha) ** (1.0 / k)


def effective_sample(df: pd.DataFrame) -> tuple[int, int, float]:
    n_trades = len(df)
    n_days = df["ny_day"].nunique()
    return n_trades, n_days, (n_trades / n_days if n_days else 0.0)


def concentration(df: pd.DataFrame, top: int = 2) -> tuple[float, list[tuple[str, float]]]:
    """Share of GROSS session profit produced by the best `top` days.

    Measured against the sum of winning sessions rather than the net, so the
    number stays defined and comparable when the net is zero or negative.
    This is the 11-Mondays test: hundreds of trades that trace back to two
    good sessions are two bets, not hundreds.
    """
    by_day = df.groupby("ny_day")["r_realized"].sum().sort_values(ascending=False)
    gross = float(by_day[by_day > 0].sum())
    best = by_day.head(top)
    share = float(best[best > 0].sum() / gross) if gross > 0 else float("nan")
    return share, [(str(d), float(v)) for d, v in best.items()]


def cost_sweep(df: pd.DataFrame, max_cost_r: float = 0.30,
               steps: int = 31) -> tuple[np.ndarray, np.ndarray, float]:
    """Subtract a fixed round-trip cost, expressed in R, from every trade.

    cost_in_R = round_trip_points / risk_points. If the journal carries
    risk_points and spread we anchor the sweep to the observed spread.
    """
    grid = np.linspace(0.0, max_cost_r, steps)
    r = df["r_realized"].to_numpy()
    days = df["ny_day"].to_numpy()
    means = []
    for c in grid:
        adj = r - c
        s = pd.Series(adj).groupby(days).mean()
        means.append(s.mean())
    means = np.asarray(means)
    # First cost level at which expectancy turns non-positive
    dead = float("nan")
    below = np.where(means <= 0)[0]
    if len(below):
        dead = float(grid[below[0]])
    return grid, means, dead


def observed_cost_in_r(df: pd.DataFrame) -> float | None:
    """Estimate the real round-trip cost in R from spread and stop distance."""
    if "spread_pts_entry" not in df.columns or "risk_points" not in df.columns:
        return None
    sub = df[["spread_pts_entry", "risk_points"]].dropna()
    sub = sub[sub["risk_points"] > 0]
    if sub.empty:
        return None
    # One spread in, one out, plus a conservative half-spread of slippage.
    return float((sub["spread_pts_entry"] * 2.5 / sub["risk_points"]).mean())


def excursion_diagnostics(df: pd.DataFrame, target_r: float) -> dict | None:
    """Cap-free excursion statistics.

    Raw mean MFE and mean MAE are NOT comparable: a winner's MFE is truncated
    at the take profit and a loser's MAE is truncated at the stop, so the
    exit rule manufactures the asymmetry. The two quantities that are free to
    vary are:

        MFE given the trade LOST   — capped only by a target it never reached
        |MAE| given the trade WON  — capped only by a stop it never reached

    Read as fractions of their own ceiling, these say how much of the trade
    was noise. A high wasted-favour figure on losers means the entry was
    early or the target too far. A high wasted-risk figure on winners means
    the entry was late or the stop too tight. When both sit near half their
    ceiling the path is behaving like a random walk between two barriers,
    which is what a directionless entry looks like.
    """
    if "mfe_r" not in df.columns or "mae_r" not in df.columns:
        return None
    sub = df[["mfe_r", "mae_r", "r_realized"]].dropna()
    if sub.empty:
        return None

    losers = sub[sub["r_realized"] <= 0]
    winners = sub[sub["r_realized"] > 0]
    if len(losers) < 10 or len(winners) < 10:
        return None

    mfe_loss = float(losers["mfe_r"].abs().mean())
    mae_win = float(winners["mae_r"].abs().mean())

    return dict(
        raw_mfe=float(sub["mfe_r"].abs().mean()),
        raw_mae=float(sub["mae_r"].abs().mean()),
        mfe_given_loss=mfe_loss,
        mae_given_win=mae_win,
        wasted_favour=mfe_loss / target_r if target_r > 0 else float("nan"),
        wasted_risk=mae_win,          # ceiling is 1.0 R by construction
        n_losers=len(losers),
        n_winners=len(winners),
    )


# ─────────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────────

@dataclass
class Gate:
    name: str
    passed: bool | None
    detail: str


@dataclass
class Report:
    gates: list[Gate] = field(default_factory=list)

    def add(self, name: str, passed: bool | None, detail: str) -> None:
        self.gates.append(Gate(name, passed, detail))

    def render(self) -> bool:
        rule("VERDICT")
        hard_fail = False
        for g in self.gates:
            print(f"  [{verdict_tag(g.passed)}]  {g.name:<26} {g.detail}")
            if g.passed is False:
                hard_fail = True
        print()
        if hard_fail:
            print("  RESULT: NOT TRADEABLE on this evidence.")
            print("  At least one gate failed. A failed gate is not a tuning prompt —")
            print("  re-tuning until it passes is how a coin flip becomes a backtest.")
        else:
            print("  RESULT: SURVIVES every gate on this sample.")
            print("  Survival is not proof. Re-run on a fresh period before risking size,")
            print("  and size to the lower bound of the confidence interval, not the mean.")
        return not hard_fail


def analyse(df: pd.DataFrame, target_r: float, oos_frac: float,
            variants: int, alpha: float, max_cost: float,
            plots: str | None) -> bool:

    rep = Report()
    n_trades, n_days, per_day = effective_sample(df)

    rule("SAMPLE")
    print(f"  trades                {n_trades}")
    print(f"  distinct sessions     {n_days}")
    print(f"  trades per session    {per_day:.2f}")
    if "model" in df.columns:
        for m, g in df.groupby("model"):
            print(f"    · {m:<24} {len(g):>6} trades   "
                  f"{g['ny_day'].nunique():>5} days   mean {g['r_realized'].mean():+.4f} R")
    if "symbol" in df.columns and df["symbol"].nunique() > 1:
        print(f"  symbols               {df['symbol'].nunique()}")

    # Sessions, not trades, are the sample size that matters.
    enough = n_days >= 100
    rep.add("Sample size", enough,
            f"{n_days} independent sessions (need 100+; you have {n_trades} trades, "
            f"which is not the same thing)")

    # ── T1  break-even gap ────────────────────────────────────────────
    rule("T1  BREAK-EVEN GAP")
    wins = int((df["r_realized"] > 0).sum())
    wr = wins / n_trades if n_trades else 0.0
    be = breakeven_win_rate(target_r)
    p_binom = binom_p_greater(wins, n_trades, be)
    print(f"  payout                {target_r:.2f} R")
    print(f"  break-even win rate   {be * 100:.2f}%")
    print(f"  actual win rate       {wr * 100:.2f}%   ({wins}/{n_trades})")
    print(f"  gap                   {(wr - be) * 100:+.2f} pp")
    print(f"  binomial p (naive)    {p_binom:.4f}   ← ignores day clustering, so it flatters")
    rep.add("Win rate beats payout", wr > be,
            f"{wr * 100:.2f}% vs {be * 100:.2f}% required")

    # ── T2  day-clustered inference ───────────────────────────────────
    rule("T2  DAY-CLUSTERED INFERENCE")
    dist, lo, hi, p_day = block_bootstrap(df)
    mean_r = float(df["r_realized"].mean())
    mean_day = float(day_means(df).mean())
    print(f"  mean R per trade      {mean_r:+.4f}")
    print(f"  mean R per session    {mean_day:+.4f}")
    print(f"  95% CI (day bootstrap)[{lo:+.4f}, {hi:+.4f}]")
    print(f"  p(mean R <= 0)        {p_day:.4f}")
    share, best = concentration(df, top=2)
    print(f"  top-2 session share   {share * 100:.1f}% of total R")
    for d, v in best:
        print(f"    · {d}   {v:+.2f} R")
    rep.add("Positive after clustering", (lo > 0),
            f"lower CI bound {lo:+.4f} R per session")
    rep.add("Not day-concentrated", (share < 0.50) if not math.isnan(share) else None,
            f"best 2 sessions carry {share * 100:.1f}% of the result "
            f"(over 50% means you have 2 lucky days, not a system)")

    # ── T3  excursion diagnostics (not a gate) ────────────────────────
    rule("T3  EXCURSION DIAGNOSTICS   [diagnostic only, not a gate]")
    ex = excursion_diagnostics(df, target_r)
    if ex is None:
        print("  mfe_r / mae_r absent, or too few trades on one side.")
        print("  Re-run the EA with the journal switched on to populate these.")
    else:
        print(f"  raw mean MFE          {ex['raw_mfe']:.3f} R")
        print(f"  raw mean MAE          {ex['raw_mae']:.3f} R")
        print("  Those two are NOT comparable — the exits truncate both. Use these:")
        print(f"  MFE given a loss      {ex['mfe_given_loss']:.3f} R"
              f"   = {ex['wasted_favour'] * 100:.0f}% of the {target_r:.1f}R target"
              f"   (n={ex['n_losers']})")
        print(f"  |MAE| given a win     {ex['mae_given_win']:.3f} R"
              f"   = {ex['wasted_risk'] * 100:.0f}% of the 1.0R stop"
              f"   (n={ex['n_winners']})")
        print()
        if ex["wasted_favour"] > 0.45:
            print("  Losers ran most of the way to target before failing: the target")
            print("  is too far for this entry, or the entry is too early.")
        if ex["wasted_risk"] > 0.55:
            print("  Winners dug deep into the stop first: the entry is late, which is")
            print("  exactly what a 'wait for strong confirmation' rule produces.")
        if ex["wasted_favour"] <= 0.45 and ex["wasted_risk"] <= 0.55:
            print("  Excursions look tight on both sides — entries are landing close")
            print("  to the turn. That is what an entry with real timing looks like.")

    # ── T4  cost survival ─────────────────────────────────────────────
    rule("T4  COST SURVIVAL")
    grid, means, dead = cost_sweep(df, max_cost_r=max_cost)
    obs = observed_cost_in_r(df)
    print(f"  expectancy at 0 cost  {means[0]:+.4f} R")
    if math.isnan(dead):
        print(f"  edge survives to      {max_cost:.3f} R of round-trip cost (end of sweep)")
    else:
        print(f"  edge dies at          {dead:.3f} R of round-trip cost")
    if obs is not None:
        print(f"  your observed cost    ~{obs:.3f} R  (2.5 x mean spread / mean stop)")
        margin = (dead - obs) if not math.isnan(dead) else (max_cost - obs)
        print(f"  margin                {margin:+.3f} R")
        rep.add("Survives real costs", margin > 0.02,
                f"dies at {dead if not math.isnan(dead) else max_cost:.3f} R, "
                f"you pay ~{obs:.3f} R")
    else:
        print("  spread / risk_points not in journal — cannot anchor to your real cost.")
        rep.add("Survives real costs", None, "no spread or risk_points columns")

    # ── T5  out-of-sample + selection haircut ─────────────────────────
    rule("T5  OUT OF SAMPLE & SELECTION HAIRCUT")
    days_sorted = sorted(df["ny_day"].unique())
    cut = int(len(days_sorted) * (1 - oos_frac))
    in_days = set(days_sorted[:cut])
    ins = df[df["ny_day"].isin(in_days)]
    oos = df[~df["ny_day"].isin(in_days)]
    a = sidak_alpha(alpha, variants)
    print(f"  in-sample             {len(ins)} trades / {ins['ny_day'].nunique()} days   "
          f"mean {ins['r_realized'].mean():+.4f} R")
    if len(oos) and oos["ny_day"].nunique() >= 2:
        _, olo, ohi, op = block_bootstrap(oos)
        print(f"  out-of-sample         {len(oos)} trades / {oos['ny_day'].nunique()} days   "
              f"mean {oos['r_realized'].mean():+.4f} R")
        print(f"  OOS 95% CI            [{olo:+.4f}, {ohi:+.4f}]   p={op:.4f}")
        print(f"  variants you tried    {variants}")
        print(f"  Sidak-adjusted alpha  {a:.5f}  (from {alpha:.2f})")
        print("  Every parameter set, symbol and timeframe you tested counts as a variant.")
        rep.add("Holds out of sample", (op < a) and (olo > 0),
                f"OOS p={op:.4f} vs required {a:.5f}")
    else:
        print("  out-of-sample slice too small to test.")
        rep.add("Holds out of sample", None, "insufficient held-out sessions")

    if plots:
        write_plots(df, grid, means, target_r, plots)
        print(f"\n  charts written to     {plots}")

    print()
    return rep.render()


# ─────────────────────────────────────────────────────────────────────
# Charts
# ─────────────────────────────────────────────────────────────────────

def write_plots(df: pd.DataFrame, grid, means, target_r: float, path: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ink, tick, pad_c, verify = "#16211C", "#C8102E", "#E9EFE3", "#1F5C3A"
    fig, ax = plt.subplots(2, 2, figsize=(13, 8.5), facecolor=pad_c)
    for a in ax.flat:
        a.set_facecolor(pad_c)
        for s in a.spines.values():
            s.set_color(ink)
        a.tick_params(colors=ink, labelsize=8)
        a.grid(True, color="#A9C1A4", lw=0.6, alpha=0.7)

    # 1 — equity in R by session
    by_day = df.groupby("ny_day")["r_realized"].sum().sort_index()
    ax[0, 0].plot(np.arange(len(by_day)), by_day.cumsum().to_numpy(), color=ink, lw=1.4)
    ax[0, 0].axhline(0, color=tick, lw=1.0, ls="--")
    ax[0, 0].set_title("Cumulative R by session", color=ink, fontsize=10, loc="left")
    ax[0, 0].set_xlabel("session", color=ink, fontsize=8)

    # 2 — bootstrap distribution of mean R per session, against zero
    dist, lo, hi, _ = block_bootstrap(df, n_boot=8000)
    ax[0, 1].hist(dist, bins=60, color="#A9C1A4", edgecolor=ink, linewidth=0.4)
    ax[0, 1].axvline(0, color=tick, lw=1.4, ls="--")
    ax[0, 1].axvline(lo, color=verify, lw=1.0, ls=":")
    ax[0, 1].axvline(hi, color=verify, lw=1.0, ls=":")
    ax[0, 1].set_title(f"Mean R per session, day-block bootstrap\n"
                       f"95% CI [{lo:+.3f}, {hi:+.3f}] — red line is zero",
                       color=ink, fontsize=10, loc="left")
    ax[0, 1].set_xlabel("mean R per session", color=ink, fontsize=8)

    # 3 — session PnL concentration
    top = df.groupby("ny_day")["r_realized"].sum().sort_values(ascending=False)
    n = min(25, len(top))
    cols = [tick if i < 2 else ink for i in range(n)]
    ax[1, 0].bar(np.arange(n), top.head(n).to_numpy(), color=cols)
    ax[1, 0].set_title("Best 25 sessions — red bars are the two that could be luck",
                       color=ink, fontsize=10, loc="left")

    # 4 — cost survival
    ax[1, 1].plot(grid, means, color=ink, lw=1.6)
    ax[1, 1].axhline(0, color=tick, lw=1.0, ls="--")
    obs = observed_cost_in_r(df)
    if obs is not None:
        ax[1, 1].axvline(obs, color=verify, lw=1.2, ls=":")
        ax[1, 1].text(obs, ax[1, 1].get_ylim()[1] * 0.9, " your cost",
                      color=verify, fontsize=8)
    ax[1, 1].set_title("Expectancy vs round-trip cost (R)", color=ink, fontsize=10, loc="left")
    ax[1, 1].set_xlabel("round-trip cost in R", color=ink, fontsize=8)

    fig.suptitle("Session-Range Forge — trade journal forensics",
                 color=ink, fontsize=13, x=0.02, ha="left")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(path, dpi=150, facecolor=pad_c)
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Forensics on a Session-Range Forge trade journal.")
    ap.add_argument("csv", nargs="?", help="path to the EA's CSV journal")
    ap.add_argument("--demo", action="store_true", help="run on a synthetic coin flip instead")
    ap.add_argument("--target-r", type=float, default=2.0, help="payout in R (default 2.0)")
    ap.add_argument("--oos", type=float, default=0.30, help="held-out fraction of sessions")
    ap.add_argument("--variants", type=int, default=1,
                    help="how many parameter sets / symbols / timeframes you tested")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--max-cost", type=float, default=0.30, help="top of the cost sweep, in R")
    ap.add_argument("--plots", default=None, help="write charts to this PNG path")
    args = ap.parse_args()

    if args.demo:
        df = make_demo(target_r=args.target_r)
        print("\n  DEMO MODE — synthetic 2:1 coin flip with day clustering.")
        print("  A working forensics engine must refuse to certify this.")
    elif args.csv:
        df = load_journal(args.csv)
    else:
        ap.error("give a CSV path, or --demo")

    ok = analyse(df, args.target_r, args.oos, args.variants,
                 args.alpha, args.max_cost, args.plots)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
