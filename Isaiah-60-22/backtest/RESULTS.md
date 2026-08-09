# Backtest Results — first real data

Run date: 2026-08-09. This is the first time anything in this workspace has
been tested against real market data rather than reasoned about.

## What was tested

| | |
|---|---|
| **Data** | Dukascopy tick feed, decoded to M1 bars, **real bid-ask spread per minute** |
| **Period** | 2026-02-02 → 2026-08-01 (~125 trading sessions, spans the March DST change) |
| **Symbols** | 13 — FX majors, gold, silver, copper, WTI, Brent, Nasdaq, BTC, ETH |
| **Strategy** | 9:30 NY opening range, direct break (the default model) |
| **Targets** | 1.5R and 2.0R, structural stop at the opposite boundary |
| **Costs** | Real spread paid on entry and exit. No fixed-spread assumption. |
| **Intrabar** | Pessimistic — when a bar spans both stop and target, the **stop** is taken |

## The headline

**24 runs. Only 4 had 100+ sessions. Of those 4: median profit factor 0.98,
median win rate 38.7%, mean expectancy −0.0027 R.**

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

## Read the USDCHF row again

**62.5% win rate. Profit factor 2.41. Expectancy +0.53 R.**

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

## What this does and does not prove

**Does:** the 9:30 opening-range break, taken mechanically at 1.5R or 2R with
a structural stop, across 13 instruments and ~125 sessions of real spread-aware
data, does not have a positive expectancy. The portfolio p-value is 0.74 —
nowhere near significance in the favourable direction.

**Does not:** prove the strategy family is worthless everywhere and forever.
Six months is one regime. Specifically untested here:

- The **RVOL filter** — the one selection filter with published evidence
  behind it. Not applied in this run.
- The **Asian sweep** strategy — needs overnight hours that were not fetched.
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
