# MT5 build — Isaiah 60:22

Two Expert Advisors over one shared core.

| File | Install to | Strategy |
|---|---|---|
| `Include/Isaiah6022_Core.mqh` | `MQL5/Include/` | Shared engine — clock, range, risk kernel, journal. Not attachable itself. |
| `Experts/Isaiah6022_NY0930_ORB.mq5` | `MQL5/Experts/` | Strategy 01 — the 9:30 NY opening range |
| `Experts/Isaiah6022_AsianSweep.mq5` | `MQL5/Experts/` | Strategy 02 — the Asian range liquidity sweep |

## Install

1. MetaTrader 5 → **File → Open Data Folder**.
2. Copy `Isaiah6022_Core.mqh` into `MQL5/Include/`.
3. Copy both `.mq5` files into `MQL5/Experts/`.
4. Open either EA in MetaEditor and press **F7**. The include is resolved by
   name, so the core must be in place first or the compile fails on line 1.
5. Attach to any chart of the symbol you want to trade. The EA reads its own
   timeframes via the `InpRangeTF` / `InpEntryTF` inputs, so the chart's own
   timeframe does not matter.

## Before the first run — set the clock

This is the only input you must get right by hand, and the EA cannot check it
for you in the Strategy Tester.

```
InpBrokerGMTOffset = <your broker's WINTER offset from GMT, in hours>
```

Find it by comparing the MT5 server clock against a known UTC source **during
January or February**. Common values are 2.0 and 3.0. Auto-detection
(`InpAutoGMTOffset`) works on a live connection only.

Everything downstream is anchored to New York local time, and the EA applies
the real US daylight-saving rule on top of your winter offset. Get this number
wrong and you trade a window one hour off for eight months of the year. See
`../strategies/00-session-clock.md`.

## Strategy Tester settings

Anything less than this produces a backtest of a market that does not exist:

- **Modelling:** Every tick based on real ticks
- **Period:** two years minimum
- **Spread:** Real — *not* fixed. The 09:30 open is precisely when spreads widen,
  and a fixed-spread test hides the cost that kills this family of strategies.
- **Deposit / leverage:** whatever you will actually trade

## First run

```
InpModel        = ORB_BREAK_DIRECT     (or SWEEP_MSS)
InpBiasMode     = I22_BIAS_OFF         (ORB: get a baseline before filtering)
InpRiskPercent  = 0.5
InpTargetR      = 2.0
InpWriteJournal = true
InpRunTag       = "orb_direct_v1"      ← change this every single run
```

The journal lands in `MQL5/Files/I22_ORB_journal.csv` (or
`I22_Sweep_journal.csv`). Rows append across runs, which is why the run tag
matters — it is how you tell one variant from another afterwards.

```bash
python3 ../SessionRange_Forge/srf_forensics.py I22_ORB_journal.csv \
        --target-r 2.0 --variants 1 --plots orb.png
```

## The falsification run

Do this second, before you tune anything.

**ORB:** re-run with `InpModel = ORB_RETEST`, everything else identical. You
are replicating the finding that the retest lowers the win rate — on your
instrument, at your costs.

**Sweep:** re-run with `InpBiasMode = I22_BIAS_OFF`, everything else identical.
If the bias filter does not improve the result, the sweep carries no
directional information here and the strategy has no premise left.

## Reading the log

The EA narrates its decisions, including the ones where it refuses to trade:

```
Isaiah 60:22 | 2025-03-14 range set  H=2652.40 L=2649.15  (325 pts, 1.55 x ATR)
Isaiah 60:22 | upside break of 2652.40 at 2652.85
Isaiah 60:22 | entry rejected: spread is 14.2% of the stop, max 10.0%
```

That third line is the EA working correctly. A rejected entry is a decision,
not a failure — and it is written to the log rather than silently skipped
precisely so you can count how often your broker's spread is the reason you
are not trading.

## Notes

- **Magic numbers** are 60221 (ORB) and 60222 (sweep). Run both on the same
  account without them fighting over each other's positions.
- **The dashboard** uses `Comment()` rather than a chart label, so it renders
  all its lines. It clears itself on removal.
- **On an M1 Mac:** MT5 has a native macOS build and the Strategy Tester works.
  Multi-core optimisation is limited — use a Windows-on-ARM VM for long
  optimisation runs, native for single backtests.
