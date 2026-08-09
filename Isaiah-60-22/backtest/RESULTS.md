# Backtest Results — first real data

Run date: 2026-08-09. This is the first time anything in this workspace has
been tested against real market data rather than reasoned about.

## What was tested

| | |
|---|---|
| **Data** | Dukascopy tick feed, decoded to M1 bars, **real bid-ask spread per minute** |
| **Period** | 2026-02-02 → 2026-08-01 (~125 trading sessions, spans the March DST change) |
| **Symbols** | 19 — FX majors and crosses, gold, silver, copper, WTI, Brent, Nasdaq, BTC, ETH |
| **Strategy** | 9:30 NY opening range, direct break (the default model) |
| **Targets** | 1.5R and 2.0R, structural stop at the opposite boundary |
| **Costs** | Real spread paid on entry and exit. No fixed-spread assumption. |
| **Intrabar** | Pessimistic — when a bar spans both stop and target, the **stop** is taken |

## The headline

Expanded to the full 19-symbol universe at 2R:

**18 runs. Only 3 had 100+ sessions. Of those 3: median profit factor 1.00,
median win rate 35.2%, mean expectancy +0.0058 R — statistically
indistinguishable from zero.**

The three deep-sample instruments all land on the same number:

| Symbol | Sessions | WR | Break-even | PF | E[R] |
|---|---|---|---|---|---|
| XAUUSD gold | 123 | 33.9% | 33.3% | 0.97 | −0.021 |
| Nasdaq | 114 | 38.4% | 33.3% | 1.06 | +0.037 |
| AUDJPY | 100 | 35.2% | 33.3% | 1.00 | +0.002 |

Profit factor 0.97, 1.06, 1.00. Every instrument with a real sample sits on
1.0. That is not three separate results; it is one result observed three
times.

Portfolio across all 12 streams that traded, at 2R:

```
trades (volume)      898
distinct sessions    129
win rate             33.9%
profit factor        0.90
expectancy           -0.0666 R per trade
p(mean <= 0)         0.7448
effective breadth    4.07 of 12 streams
```

The 9:30 opening-range breakout, as specified in the source material, **did
not show an edge on any instrument tested, after real costs.**

## Per-symbol

| Symbol | Tgt | Trades | Sess | WR | B/E | PF | E[R] |
|---|---|---|---|---|---|---|---|
| XAUUSD gold | 2.0 | 183 | **123** | 33.9% | 33.3% | 0.97 | −0.021 |
| XAUUSD gold | 1.5 | 195 | **123** | 39.0% | 40.0% | 0.97 | −0.015 |
| Nasdaq | 2.0 | 159 | **114** | 38.4% | 33.3% | 1.06 | +0.037 |
| Nasdaq | 1.5 | 166 | **114** | 42.2% | 40.0% | 0.98 | −0.011 |
| USDJPY | 2.0 | 125 | 81 | 31.2% | 33.3% | 0.84 | −0.110 |
| GBPUSD | 2.0 | 83 | 59 | 31.3% | 33.3% | 0.74 | −0.175 |
| XAGUSD silver | 2.0 | 59 | 50 | 37.3% | 33.3% | 0.84 | −0.096 |
| WTI oil | 2.0 | 67 | 49 | 20.9% | 33.3% | 0.53 | −0.365 |
| EURUSD | 2.0 | 69 | 48 | 31.9% | 33.3% | 0.87 | −0.086 |
| AUDUSD | 2.0 | 47 | 36 | 23.4% | 33.3% | 0.48 | −0.398 |
| Brent | 2.0 | 40 | 30 | 40.0% | 33.3% | 1.17 | +0.101 |
| BTCUSD | 2.0 | 33 | 26 | 45.5% | 33.3% | 1.36 | +0.189 |
| USDCHF | 1.5 | 24 | 23 | 62.5% | 40.0% | **2.41** | +0.529 |
| Copper | 2.0 | 9 | 7 | 33.3% | 33.3% | 0.80 | −0.137 |

Bold session counts clear the 100-session gate. Nothing else does.

## EURGBP: a 60% win rate that loses money

```
EURGBP  2.0R   5 trades   5 sessions   WR 60.0%   PF 0.70   E -0.121R
```

Sixty percent win rate. Profit factor **0.70**. It loses money.

Three of the five wins were small partial-credit exits and the two losses were
full stops, so the average win was far below the average loss. This single row
is the cleanest possible demonstration that **win rate on its own carries no
information about whether a system makes money.** Anyone quoting a win rate
without the payout and the sample size is quoting nothing.

## Read the USDCHF row again

**62.5% win rate at 1.5R, profit factor 2.41. At 2.0R: 54.2% and PF 2.12.**

That is, almost exactly, the result requested at the start of this project —
a win rate above 60% with a much higher profit factor. It is also built on
**23 sessions and 24 trades**, which is nothing. Twenty-four coin flips
produce a run like this often enough that it carries no information.

This row is the single most useful output of the whole exercise, because it
is precisely the screenshot a vendor would sell you. Same data, same engine,
same everything as the rows above and below it — and those say the strategy
loses money. The only thing different about USDCHF is that it had the fewest
observations.

That is what the sample-size gate is for, and this is what it caught.

## The mechanism of failure, on gold

Gold had the deepest sample (123 sessions) so it gives the clearest read.

The forensics run on the 2R journal:

```
[ PASS ]  Sample size                105+ sessions
[ PASS ]  Win rate beats payout      34.18% vs 33.33% required
[ FAIL ]  Positive after clustering  lower CI bound -0.1195 R per session
[ FAIL ]  Survives real costs        dies at 0.110 R, you pay ~0.130 R
[ FAIL ]  Holds out of sample        OOS p=0.3789 vs required 0.01021
```

**Expectancy at zero cost is +0.108 R. The edge dies at 0.110 R of cost. The
real spread costs 0.130 R.** There is a faint raw edge and the spread eats all
of it and a little more. That is the whole story.

## The target curve — the definitive picture

Run on a **time-only exit** journal so the excursions are uncensored, gold:

| Target | Win rate | Break-even | Edge |
|---|---|---|---|
| 0.25R | 80.0% | 80.0% | +0.0pp |
| 0.50R | 66.0% | 66.7% | −0.7pp |
| 0.75R | 60.7% | 57.1% | +3.5pp |
| 1.00R | 50.0% | 50.0% | +0.0pp |
| 1.50R | 42.0% | 40.0% | +2.0pp |
| 2.00R | 30.7% | 33.3% | −2.7pp |
| 3.00R | 19.3% | 25.0% | −5.7pp |
| 5.00R | 4.7% | 16.7% | −12.0pp |

The win rate tracks `1/(1+R)` at **every single target**. The edge column
oscillates around zero and then goes decisively negative as costs compound
over more attempts.

This is the signature of an entry that carries **no directional information**.
The payout is setting the win rate; the signal is not.

And note where a 60% win rate actually lives: **0.75R, profit factor 1.16.**
Not 3:1. Not "extremely high."

## A data-quality caveat, stated plainly

Dukascopy rate-limits under sustained load. The fetch log for the later
symbols shows failures climbing — 149 of 1,200 hourly files failed after
retries on the last symbol in the queue. Missing hours mean missing bars,
which means some sessions never formed a range and were skipped.

That is part of why several symbols show far fewer sessions than gold's 123.
It does **not** bias the direction of the result — a missing hour removes a
session, it does not tilt the ones that remain — but it does mean the thin
rows are thinner than the calendar alone would explain. Re-running the fetch
for those symbols alone, at lower concurrency, would fill them in.

## The RVOL filter tested — and a defect in the shipped defaults

The EAs shipped with `InpMinRVOL = 1.5` (ORB) and `1.3` (sweep) turned ON by
default. Backtesting that exact configuration exposed a bug: **it does not
filter, it annihilates.**

```
RVOL >= 1.5, 20 symbols:   gold NO TRADES (from 183)
                           silver NO TRADES (from 59)
                           Nasdaq 1 trade (from 159)
```

The reason is that the opening-window RVOL distribution is far tighter than
the threshold assumed:

| Symbol | median | p75 | p90 | p95 | % of sessions >= 1.5 |
|---|---|---|---|---|---|
| XAUUSD | 1.00 | 1.11 | 1.19 | 1.24 | **0.0%** |
| Nasdaq | 1.02 | 1.07 | 1.11 | 1.22 | 0.9% |
| EURUSD | 0.79 | 1.03 | 1.32 | 1.79 | 8.0% |

A 1.5 gate sits beyond the 95th percentile on the liquid instruments. Anyone
running the shipped defaults would have watched the EA sit on its hands for
months and concluded the code was broken. It was the default that was broken.

Calibrated down so it actually triggers, the filter still does not replicate:

| Symbol | RVOL off | RVOL 1.05 | RVOL 1.10 |
|---|---|---|---|
| XAUUSD | PF 0.97 (123 sess) | PF 1.06 (49) | PF 1.31 (34) |
| Nasdaq | PF 1.06 (114 sess) | PF 0.98 (41) | PF 0.92 (13) |
| AUDJPY | PF 1.00 (100 sess) | PF 0.76 (39) | PF 0.88 (34) |

It helps gold and hurts the other two. Two of three worse is noise, not a
filter — and gold's improvement costs 72% of its sessions, leaving 34, which
is below the gate anyway.

**The default is now 0 (off) in all four EAs**, with the distribution numbers
recorded in the source so the next person does not re-derive this. The
Zarattini result stands, but it was US equities with a different RVOL
definition; it does not transfer to a 5-minute FX/metals opening window
unexamined.

## Strategy 02, the Asian sweep — now tested as designed

MSS, the higher-timeframe bias and the midnight-open filter are implemented in
the engine, so the EA's actual default configuration can be measured. Gold,
overnight hours, filters added one at a time:

| Configuration | Trades | Sessions | WR | PF | E[R] |
|---|---|---|---|---|---|
| Reclaim only | 90 | 90 | 24.4% | 0.54 | −0.348 |
| + MSS | 89 | 89 | 25.8% | 0.59 | −0.307 |
| + MSS + bias | 40 | 40 | 25.0% | 0.52 | −0.362 |
| + MSS + bias + midnight open (**EA default**) | 38 | 38 | 28.9% | 0.65 | −0.250 |

Break-even at 2R is 33.3%. The best configuration reaches 28.9% — **4.4 points
short, with every variant deeply negative.** The full stack of filters moved
profit factor from 0.54 to 0.65 and never crossed 1.0.

### The MSS filter barely filtered

Adding the market structure shift removed **one trade out of ninety**.

The source material calls the MSS *"the single most important filter for this
strategy"* and *"the confirmation that price has rejected the swept level."*
As implemented here it is very nearly a no-op, and the reason is mechanical:
on M1 bars with a 2-bar fractal, confirmed swings print constantly and price
breaks one within a few bars almost every time. A filter that passes 99% of
candidates is not selecting anything.

**Caveat that cuts the other way:** the EA defaults the sweep's entry
timeframe to **M5**, and this engine runs the signal on **M1**. On M5 the
swings are fewer and further apart, so MSS would bite harder and could behave
quite differently. That is the single most important untested detail left in
Strategy 02, and it is a data-resampling change rather than new logic.

### The bias filter cut the sample in half and did not help

Requiring a higher-timeframe bias took 89 trades to 40 and moved profit factor
from 0.59 to 0.52 — slightly worse. `strategies/02` predicted the opposite,
on the reasoning that the sweep predicts volatility rather than direction so
direction must come from elsewhere. On this sample it did not.

That is the falsification run the strategy document asked for, and the answer
came back negative. Per `strategies/02`: *"if the bias filter does not improve
the result, the strategy has no premise left."*

## What this does and does not prove

**Does:** the 9:30 opening-range break, taken mechanically at 1.5R or 2R with
a structural stop, across 19 instruments and ~125 sessions of real
spread-aware data, does not have a positive expectancy. The portfolio p-value
is 0.74 — nowhere near significance in the favourable direction. Every
instrument with a 100+ session sample returned a profit factor of 1.0.

**Does not:** prove the strategy family is worthless everywhere and forever.
Six months is one regime. Specifically untested here:

- The sweep on an **M5 entry timeframe** rather than M1, which is the EA
  default and the one change most likely to make MSS behave differently.
- **Break-even stops and runners** — `pf_lab.py` says these are the biggest
  untested lever, and they cannot be settled from these journals.
- **Longer history** — 125 sessions is the minimum, not a comfortable sample.
- **US equities**, where the published Zarattini result actually lives. The
  9:30 open is a real structural event for stocks. For spot FX it is borrowed.

## What comes next

1. Re-run with `--min-rvol 1.5`. If selection is where the edge lives, this is
   where it shows up — at the cost of roughly half the trades.
2. Fetch overnight hours and test the Asian sweep, which has a different
   premise (reversal, not continuation).
3. Extend to 2+ years so the sample stops being the binding constraint.
4. Test break-even and runner policies directly, since the journals cannot
   settle them.

## Reproduce it

```bash
cd backtest
python3 fetch_dukascopy.py --symbols XAUUSD EURUSD USATECHIDXUSD \
        --start 2026-02-02 --end 2026-08-01 --hours 12-22
python3 run_basket.py --targets 1.5 2.0
python3 ../SessionRange_Forge/portfolio.py "journals/*_t2.0.csv"
```

Raw M1 data is gitignored because it is large and reproducible. The journals
in `journals/` are committed — they are the evidence, and they are what every
claim above was computed from.
