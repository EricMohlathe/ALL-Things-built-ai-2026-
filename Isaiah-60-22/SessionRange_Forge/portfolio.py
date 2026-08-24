#!/usr/bin/env python3
"""
portfolio.py — combine every stream into one measured result.

The reason this file exists:

    On ONE instrument, win rate and trade count move in opposite directions.
    Every filter that raises the win rate cuts the number of setups. You
    cannot tighten your way to more trades.

    Across MANY instruments, they do not. Ten uncorrelated streams at 40
    trades a year each is 400 trades a year at each stream's own quality.
    Breadth is the only lever that raises volume without lowering standards.

    But only if the streams are actually uncorrelated. Ten symbols that all
    break out together on the same New York open are not ten bets. They are
    one bet at ten times the size, and the portfolio statistics will lie to
    you about it in exactly the flattering direction.

So this script does three things: it aggregates, it checks correlation, and
it tells you which streams are carrying the result and which are diluting it.

    python3 portfolio.py journals/*.csv
    python3 portfolio.py journals/*.csv --min-trades 30 --plots pf.png
    python3 portfolio.py journals/*.csv --rank            # what to keep

Every journal written by any of the four Isaiah 60:22 EAs works as input,
on either platform. Streams are identified by (symbol, strategy, model,
run_tag), so one file containing several runs splits correctly.

Not financial advice. This is a measurement instrument.
"""

from __future__ import annotations

import argparse
import glob
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


# ─────────────────────────────────────────────────────────────────────
# Loading
# ─────────────────────────────────────────────────────────────────────

REQUIRED = ["ny_day", "r_realized"]
STREAM_KEYS = ["symbol", "preset", "model", "run_tag"]


def load_many(paths: list[str]) -> pd.DataFrame:
    frames = []
    for p in paths:
        try:
            df = pd.read_csv(p)
        except Exception as exc:
            print(f"  !! skipping {p}: {exc}")
            continue

        df.columns = [c.strip().lower() for c in df.columns]
        missing = [c for c in REQUIRED if c not in df.columns]
        if missing:
            print(f"  !! skipping {p}: missing {missing}")
            continue

        df["r_realized"] = pd.to_numeric(df["r_realized"], errors="coerce")
        df = df.dropna(subset=["r_realized"]).copy()
        df["ny_day"] = df["ny_day"].astype(str)

        for k in STREAM_KEYS:
            if k not in df.columns:
                df[k] = "unknown"
            df[k] = df[k].astype(str)

        df["_file"] = p
        frames.append(df)

    if not frames:
        sys.exit("No usable journals found.")
    return pd.concat(frames, ignore_index=True)


def stream_id(row) -> str:
    return f"{row['symbol']}|{row['preset']}|{row['model']}|{row['run_tag']}"


# ─────────────────────────────────────────────────────────────────────
# Stats
# ─────────────────────────────────────────────────────────────────────

def stats_for(r: np.ndarray, days: np.ndarray) -> dict:
    n = len(r)
    wins = int((r > 0).sum())
    gw = float(r[r > 0].sum()) if (r > 0).any() else 0.0
    gl = float(-r[r < 0].sum()) if (r < 0).any() else 0.0

    tmp = pd.DataFrame({"r": r, "d": days})
    day_r = tmp.groupby("d")["r"].mean().to_numpy()

    return {
        "trades": n,
        "sessions": int(pd.unique(days).size),
        "win_rate": wins / n if n else 0.0,
        "profit_factor": (gw / gl) if gl > 0 else float("inf"),
        "expectancy": float(r.mean()) if n else 0.0,
        "total_r": float(r.sum()),
        "day_r": day_r,
    }


def day_bootstrap(day_r: np.ndarray, n_boot: int = 10000) -> tuple[float, float, float]:
    n = len(day_r)
    if n < 2:
        return float("nan"), float("nan"), 1.0
    idx = RNG.integers(0, n, size=(n_boot, n))
    means = day_r[idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi), float((means <= 0).mean())


def pf_str(pf: float) -> str:
    if math.isinf(pf):
        return "inf"
    return f"{pf:.2f}"


# ─────────────────────────────────────────────────────────────────────
# Correlation — the part that decides whether breadth is real
# ─────────────────────────────────────────────────────────────────────

def daily_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Rows = NY sessions, columns = streams, values = mean R that session."""
    return df.pivot_table(index="ny_day", columns="_stream",
                          values="r_realized", aggfunc="mean")


def correlation_report(mat: pd.DataFrame, threshold: float = 0.5) -> list[tuple]:
    cols = list(mat.columns)
    if len(cols) < 2:
        return []

    hot = []
    for a, b in itertools.combinations(cols, 2):
        pair = mat[[a, b]].dropna()
        if len(pair) < 20:
            continue
        c = pair[a].corr(pair[b])
        if pd.notna(c) and abs(c) >= threshold:
            hot.append((a, b, float(c), len(pair)))

    hot.sort(key=lambda t: -abs(t[2]))
    return hot


def effective_breadth(mat: pd.DataFrame) -> float:
    """
    How many INDEPENDENT streams you really have.

    With k streams of average pairwise correlation rho, the variance of the
    equally-weighted average behaves like a portfolio of

        k_eff = k / (1 + (k-1) * rho)

    independent streams. At rho = 0 you keep all k. At rho = 1 you have one
    bet no matter how many symbols are on the screen.
    """
    cols = list(mat.columns)
    k = len(cols)
    if k < 2:
        return float(k)

    corrs = []
    for a, b in itertools.combinations(cols, 2):
        pair = mat[[a, b]].dropna()
        if len(pair) < 20:
            continue
        c = pair[a].corr(pair[b])
        if pd.notna(c):
            corrs.append(c)

    if not corrs:
        return float(k)

    rho = float(np.mean(corrs))
    denom = 1.0 + (k - 1) * rho
    if denom <= 0:
        return float(k)
    return k / denom


# ─────────────────────────────────────────────────────────────────────
# Reporting
# ─────────────────────────────────────────────────────────────────────

def report_streams(df: pd.DataFrame, min_trades: int) -> pd.DataFrame:
    rule("STREAMS")
    print(f"  {'stream':<44} {'trades':>7} {'sess':>6} {'WR':>7} "
          f"{'PF':>7} {'E[R]':>8} {'total R':>9}")
    print(f"  {'-'*44} {'-'*7} {'-'*6} {'-'*7} {'-'*7} {'-'*8} {'-'*9}")

    rows = []
    for sid, g in df.groupby("_stream"):
        s = stats_for(g["r_realized"].to_numpy(), g["ny_day"].to_numpy())
        s["stream"] = sid
        rows.append(s)

    rows.sort(key=lambda s: -s["expectancy"])

    for s in rows:
        thin = "  (thin)" if s["trades"] < min_trades else ""
        label = s["stream"] if len(s["stream"]) <= 44 else s["stream"][:41] + "..."
        print(f"  {label:<44} {s['trades']:>7} {s['sessions']:>6} "
              f"{s['win_rate']:>6.1%} {pf_str(s['profit_factor']):>7} "
              f"{s['expectancy']:>+7.3f}R {s['total_r']:>+8.1f}R{thin}")

    return pd.DataFrame(rows)


def report_portfolio(df: pd.DataFrame, mat: pd.DataFrame) -> dict:
    rule("PORTFOLIO — all streams, equally weighted per session")

    s = stats_for(df["r_realized"].to_numpy(), df["ny_day"].to_numpy())
    lo, hi, p = day_bootstrap(s["day_r"])

    k = mat.shape[1]
    k_eff = effective_breadth(mat)

    print(f"  streams              {k}")
    print(f"  trades (volume)      {s['trades']}")
    print(f"  distinct sessions    {s['sessions']}")
    print(f"  trades per session   {s['trades'] / max(1, s['sessions']):.2f}")
    print()
    print(f"  win rate             {s['win_rate']:.1%}")
    print(f"  profit factor        {pf_str(s['profit_factor'])}")
    print(f"  expectancy           {s['expectancy']:+.4f} R per trade")
    print(f"  total                {s['total_r']:+.1f} R")
    print()
    print(f"  95% CI (sessions)    [{lo:+.4f}, {hi:+.4f}]")
    print(f"  p(mean <= 0)         {p:.4f}")
    print()
    print(f"  effective breadth    {k_eff:.2f} of {k} streams")

    if k >= 2:
        ratio = k_eff / k
        if ratio >= 0.75:
            print("                       Genuinely diversified. The trade count is real.")
        elif ratio >= 0.45:
            print("                       Partly correlated. Some of the volume is double-counted.")
        else:
            print("                       HEAVILY correlated. You do not have "
                  f"{k} bets, you have about {k_eff:.1f}.")
            print("                       The trade count flatters; the risk does not shrink.")

    s["p"] = p
    s["k_eff"] = k_eff
    s["k"] = k
    return s


def report_correlation(mat: pd.DataFrame, threshold: float) -> None:
    hot = correlation_report(mat, threshold)
    if not hot:
        return

    rule(f"CORRELATED PAIRS  (|r| >= {threshold:.2f} on shared sessions)")
    for a, b, c, n in hot[:15]:
        sa = a if len(a) <= 34 else a[:31] + "..."
        sb = b if len(b) <= 34 else b[:31] + "..."
        print(f"  {c:+.2f}  ({n:>4} sessions)  {sa}")
        print(f"                        {sb}")
    if len(hot) > 15:
        print(f"  ... and {len(hot) - 15} more pairs")
    print()
    print("  Correlated streams are one bet wearing several names. Size them")
    print("  as one, or drop all but the best of each cluster.")


def report_ranking(streams: pd.DataFrame, df: pd.DataFrame, min_trades: int) -> None:
    """Greedy: add streams best-expectancy-first, watch the portfolio move."""
    rule("WHAT TO KEEP  (added best-first; watch where the portfolio peaks)")

    eligible = streams[streams["trades"] >= min_trades].copy()
    if eligible.empty:
        print(f"  No stream has {min_trades}+ trades. Nothing to rank.")
        return

    eligible = eligible.sort_values("expectancy", ascending=False)

    print(f"  {'kept':>5} {'added stream':<40} {'trades':>7} {'WR':>7} "
          f"{'PF':>7} {'E[R]':>8} {'p':>8}")
    print(f"  {'-'*5} {'-'*40} {'-'*7} {'-'*7} {'-'*7} {'-'*8} {'-'*8}")

    chosen: list[str] = []
    best = None
    for _, row in eligible.iterrows():
        chosen.append(row["stream"])
        sub = df[df["_stream"].isin(chosen)]
        s = stats_for(sub["r_realized"].to_numpy(), sub["ny_day"].to_numpy())
        _, _, p = day_bootstrap(s["day_r"], n_boot=4000)

        label = row["stream"] if len(row["stream"]) <= 40 else row["stream"][:37] + "..."
        star = ""
        if best is None or s["expectancy"] > best[1]:
            best = (len(chosen), s["expectancy"], list(chosen))
            star = "  <-"
        print(f"  {len(chosen):>5} {label:<40} {s['trades']:>7} "
              f"{s['win_rate']:>6.1%} {pf_str(s['profit_factor']):>7} "
              f"{s['expectancy']:>+7.3f}R {p:>8.4f}{star}")

    if best:
        print()
        print(f"  Portfolio expectancy peaks at {best[0]} stream(s), "
              f"{best[1]:+.4f} R per trade.")
        print("  Adding streams past that point buys trade count with expectancy.")
        print("  Whether that is a good trade depends on whether you need the")
        print("  volume — it is a real choice, not an obvious one.")


def write_plots(streams: pd.DataFrame, df: pd.DataFrame, path: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print(f"\n  (matplotlib not installed — skipping {path})")
        return

    fig, ax = plt.subplots(1, 3, figsize=(16, 4.4))

    s = streams.sort_values("expectancy")
    labels = [x.split("|")[0] + "/" + x.split("|")[2][:10] for x in s["stream"]]
    ax[0].barh(labels, s["expectancy"], color="steelblue")
    ax[0].axvline(0, color="grey", linestyle="--")
    ax[0].set_xlabel("expectancy (R/trade)")
    ax[0].set_title("Per-stream expectancy")
    ax[0].tick_params(labelsize=7)

    ax[1].scatter(s["trades"], s["win_rate"] * 100, s=40, color="darkgreen")
    ax[1].set_xlabel("trades"); ax[1].set_ylabel("win rate (%)")
    ax[1].set_title("Volume vs win rate — the trade-off, per stream")
    ax[1].grid(alpha=0.3)

    eq = df.sort_values("ny_day").groupby("ny_day")["r_realized"].mean().cumsum()
    ax[2].plot(range(len(eq)), eq.to_numpy(), color="darkorange")
    ax[2].axhline(0, color="grey", linestyle="--")
    ax[2].set_xlabel("session"); ax[2].set_ylabel("cumulative R")
    ax[2].set_title("Portfolio equity, per session")
    ax[2].grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"\n  charts -> {path}")


# ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Aggregate many journals into one portfolio result.")
    ap.add_argument("csvs", nargs="+", help="journal CSVs (globs are fine)")
    ap.add_argument("--min-trades", type=int, default=30,
                    help="a stream below this is flagged thin and excluded from ranking")
    ap.add_argument("--corr-threshold", type=float, default=0.5)
    ap.add_argument("--rank", action="store_true",
                    help="show the greedy keep/drop ranking")
    ap.add_argument("--plots", default=None)
    args = ap.parse_args()

    paths: list[str] = []
    for pattern in args.csvs:
        hits = glob.glob(pattern)
        paths.extend(hits if hits else [pattern])

    print()
    print("  portfolio.py — breadth is the only lever that raises volume")
    print("                 without lowering standards")
    rule()
    print(f"  files       {len(paths)}")

    df = load_many(paths)
    df["_stream"] = df.apply(stream_id, axis=1)

    streams = report_streams(df, args.min_trades)
    mat = daily_matrix(df)
    port = report_portfolio(df, mat)
    report_correlation(mat, args.corr_threshold)

    if args.rank:
        report_ranking(streams, df, args.min_trades)

    rule("THE HONEST READ")
    print(f"  You have {port['trades']} trades across {port['k']} streams, which is")
    print(f"  worth about {port['k_eff']:.1f} independent streams once correlation is")
    print("  taken into account.")
    print()
    if port["expectancy"] > 0 and port["p"] < 0.05:
        print(f"  Portfolio expectancy {port['expectancy']:+.4f} R is positive and survives the")
        print(f"  session bootstrap (p = {port['p']:.4f}).")
        print("  Now feed the combined journal through srf_forensics.py with an")
        print("  HONEST variant count — every symbol, model and parameter set you")
        print("  tried to get here counts, including the ones you discarded.")
    else:
        print(f"  Portfolio expectancy {port['expectancy']:+.4f} R at p = {port['p']:.4f}.")
        print("  This does not clear the bar. Adding more streams will raise the")
        print("  trade count and will not fix that — volume is not edge.")
    print()


if __name__ == "__main__":
    main()
