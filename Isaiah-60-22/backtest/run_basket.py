#!/usr/bin/env python3
"""
run_basket.py — backtest every downloaded symbol and summarise honestly.

    python3 run_basket.py --targets 1.5 2.0
    python3 run_basket.py --targets 2.0 --min-rvol 1.5

Prints one row per symbol/target and a summary that separates results with
enough sessions to mean something from results without. A symbol with 26
sessions and a profit factor of 1.4 is not a finding; it is noise with a
flattering label, and the table says so.
"""

from __future__ import annotations

import argparse
import glob
import math
import os

import pandas as pd

import engine

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "journals")

MIN_SESSIONS = 100          # the forensics gate


def stats(df: pd.DataFrame) -> dict:
    r = pd.to_numeric(df["r_realized"])
    wins, losses = r[r > 0], r[r < 0]
    gl = -losses.sum()
    return {
        "trades": len(r),
        "sessions": df["ny_day"].nunique(),
        "win_rate": len(wins) / len(r) if len(r) else 0.0,
        "profit_factor": (wins.sum() / gl) if gl > 0 else float("inf"),
        "expectancy": float(r.mean()) if len(r) else 0.0,
        "total_r": float(r.sum()),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", nargs="+", type=float, default=[1.5, 2.0])
    ap.add_argument("--strategy", default="orb", choices=["orb", "sweep"])
    ap.add_argument("--model", default="break_direct")
    ap.add_argument("--min-rvol", type=float, default=0.0)
    ap.add_argument("--exit", dest="exit_mode", default="fixed_r")
    args = ap.parse_args()

    symbols = sorted(os.path.basename(p).replace("_M1.csv.gz", "")
                     for p in glob.glob(os.path.join(DATA, "*_M1.csv.gz")))
    if not symbols:
        raise SystemExit("No data. Run fetch_dukascopy.py first.")

    os.makedirs(OUT, exist_ok=True)
    rows = []

    print(f"\n  {args.strategy.upper()} / {args.model} / exit={args.exit_mode}"
          f"{'  RVOL>=' + str(args.min_rvol) if args.min_rvol else ''}")
    print(f"  {len(symbols)} symbols x {len(args.targets)} targets\n")
    print(f"  {'symbol':<15} {'tgt':>5} {'trades':>7} {'sess':>5} "
          f"{'WR':>7} {'B/E':>6} {'PF':>6} {'E[R]':>8} {'totR':>8}")
    print(f"  {'-'*15} {'-'*5} {'-'*7} {'-'*5} {'-'*7} {'-'*6} "
          f"{'-'*6} {'-'*8} {'-'*8}")

    for sym in symbols:
        for t in args.targets:
            tag = (f"{args.strategy}_{args.model}_{args.exit_mode}_t{t}"
                   f"{'_rvol' + str(args.min_rvol) if args.min_rvol else ''}")
            try:
                df = engine.run(sym, args.strategy, args.model, t,
                                args.exit_mode, args.min_rvol,
                                0.0, 0.0, 50.0, 0.5, tag)
            except SystemExit:
                continue
            if df.empty:
                print(f"  {sym:<15} {t:>5.2f} {'-':>7} {'-':>5}   no trades")
                continue

            df.to_csv(os.path.join(OUT, f"{sym}_{tag}.csv"), index=False)
            s = stats(df)
            s.update(symbol=sym, target=t)
            rows.append(s)

            be = 1.0 / (1.0 + t)
            pf = "inf" if math.isinf(s["profit_factor"]) else f"{s['profit_factor']:.2f}"
            thin = "  thin" if s["sessions"] < MIN_SESSIONS else ""
            print(f"  {sym:<15} {t:>5.2f} {s['trades']:>7} {s['sessions']:>5} "
                  f"{s['win_rate']:>6.1%} {be:>5.1%} {pf:>6} "
                  f"{s['expectancy']:>+7.3f}R {s['total_r']:>+7.1f}R{thin}")

    if not rows:
        return

    res = pd.DataFrame(rows)
    deep = res[res["sessions"] >= MIN_SESSIONS]
    thin = res[res["sessions"] < MIN_SESSIONS]

    print(f"\n  {'='*72}")
    print(f"  SUMMARY")
    print(f"  {'='*72}")
    print(f"  runs                      {len(res)}")
    print(f"  with {MIN_SESSIONS}+ sessions        {len(deep)}"
          f"   <- the only ones that can mean anything")
    print(f"  below {MIN_SESSIONS} sessions       {len(thin)}")

    if len(deep):
        pos = deep[deep["expectancy"] > 0]
        print()
        print(f"  Of the {len(deep)} statistically eligible runs:")
        print(f"    positive expectancy     {len(pos)}")
        print(f"    median profit factor    {deep['profit_factor'].median():.2f}")
        print(f"    median win rate         {deep['win_rate'].median():.1%}")
        print(f"    mean expectancy         {deep['expectancy'].mean():+.4f} R")

    if len(thin):
        best_thin = thin.loc[thin["expectancy"].idxmax()]
        print()
        print(f"  Best THIN result: {best_thin['symbol']} @ {best_thin['target']:.2f}R "
              f"-> PF {best_thin['profit_factor']:.2f} on only "
              f"{int(best_thin['sessions'])} sessions.")
        print("  That is not a finding. It is the run you would have shown a")
        print("  customer, and it is why the sample-size gate exists.")

    res.to_csv(os.path.join(HERE, "basket_summary.csv"), index=False)
    print(f"\n  summary -> {os.path.join(HERE, 'basket_summary.csv')}\n")


if __name__ == "__main__":
    main()
