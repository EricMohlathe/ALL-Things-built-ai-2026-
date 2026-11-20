---
name: mt5-backtest-report
description: Read and judge an MT5 Strategy Tester report. Use after running scripts/backtest.ps1 or build.ps1, when the user asks whether a backtest result is good, or when explaining metrics like profit factor, drawdown, recovery factor or win rate. Also covers the traps that make a backtest look better than reality. Do not use for writing MQL5 or for choosing a strategy.
---

# Reading a backtest report

Your job is to report what the numbers say, and to point out when they cannot
be trusted. Not to decide whether the strategy is worth trading. That is the
account owner's decision.

## Read in this order

Do not start with profit. Start with whether the test was valid at all.

### 1. History Quality

Anything below 100% invalidates everything else on the page. The tester filled
gaps in the price data with its own approximations, so the trades shown may
never have been possible.

Below 100%: say so first, before quoting any other number. Tell the user to
download more history for that symbol and run it again.

`backtest.ps1` already raises a warning for this.

### 2. Total Trades

- **Zero**: the EA never entered. Not a bad strategy, a broken one. Check the
  entry conditions, the spread filter, and that the symbol name is right.
- **Under about 30**: too few to mean anything. Any conclusion is noise.
  Extend the date range.
- **Thousands over a short period**: probably entering every tick rather than
  once per bar. Check the new-bar guard.

### 3. Profit Factor

Gross profit divided by gross loss.

| Value | Meaning |
|---|---|
| Below 1.0 | Loses money |
| 1.0 to 1.2 | Barely above break-even. Commission and slippage will erase it |
| 1.3 to 1.6 | Reasonable |
| Above 2.0 | Good, and worth checking for overfitting or a data problem |
| Above 5.0 | Almost always a mistake somewhere, not a discovery |

### 4. Maximum Equity Drawdown

The worst peak-to-trough fall in account value. Use the **equity** figure, not
the balance figure. Balance drawdown only counts closed trades and hides how
bad an open position got.

Ask the user directly: could you have kept the EA running through a fall this
large? Most people stop a system at half the drawdown their backtest shows.

### 5. Recovery Factor and Sharpe Ratio

Recovery Factor is net profit divided by maximum drawdown. It answers "was the
profit worth the pain". Below 1.0 means the worst drawdown was larger than
everything the strategy earned.

Sharpe Ratio below zero means the returns were worse than doing nothing.

## The win rate trap

Never lead with the win rate. It is the most misleading number on the page.

A real measured example from this project, the stock MetaQuotes MACD Sample on
EURUSDm H1 over three months:

```
Total Trades       12
Profit Trades      9 (75.00%)
Total Net Profit   12.18       on a 10,000 deposit
Profit Factor      1.08
Recovery Factor    0.06
Largest profit trade    49.00
Largest loss trade     -77.00
```

Seventy-five percent of trades won, and the account gained 0.12% in three
months. The losers were bigger than the winners.

Win rate without average win versus average loss says nothing.

## Four reasons a backtest lies

State whichever of these apply. Do not let a good-looking result pass without
checking them.

**1. Commission and swap were not set.**
The tester uses the symbol's configured costs. If they are zero, every result
is inflated. Compare the symbol specification against the live account.

**2. The modelling mode was too coarse.**
`Model=1` (one minute OHLC) is fast and fine for strategies acting on closed
bars. It is meaningless for anything that reacts intrabar, uses tight stops, or
scalps. Those need `Model=4`, real ticks, and real tick history downloaded.

**3. Spread was not realistic.**
The tester can use the current spread rather than the historical one. Spread
widens sharply at session opens and around news, which is exactly when many
strategies trade.

**4. The parameters were fitted to this exact period.**
If the numbers were tuned until the chart looked good, the result describes the
past and predicts nothing. Test an untouched date range before believing it.

## Before trusting any comparison between two runs

MetaTrader saves the inputs used by the last test into
`MQL5\Profiles\Tester\<ExpertName>.set` and silently reuses that file whenever
the run does not name one. A changed default in the source, recompiled, then
tested, reproduces the **old** numbers with a freshly built `.ex5` on disk and
no warning anywhere.

Measured: the same binary gave 8 trades with no set file and 26 with a set file
that named one unrelated input.

`backtest.ps1` writes a set file on every run, which is what makes a result a
function of the source. If a backtest is ever run by another route, check that
the inputs shown at the top of the report are the ones intended. Two runs whose
input lists differ are not a comparison.

## When there is no report at all

A missing report is not a strategy problem and must not be diagnosed as one.
Work down this list before touching any EA code.

| Symptom | Cause | Fix |
|---|---|---|
| Script exits in about a second, tester log gains **no new lines** | MetaTrader is already open. Windows hands `/config:` to the running instance, which ignores it, and the launcher returns 0 | Close MetaTrader. `backtest.ps1` now refuses to start in this case rather than letting it look like a data fault |
| Tester log says `symbol ... not exist` | Wrong suffix | Exness is `EURUSDm`, not `EURUSD`. Read Market Watch |
| `tester not started because the account is not specified` | No saved login, or a BOM in the `.ini` | Log in once by hand, and never write the `.ini` with `Set-Content -Encoding utf8` |
| Agent connects then disconnects within a millisecond | Another program holds port 3000 | `backtest.ps1` scans for a free port already |
| Report path was absolute | Silently ignored | The report name must be relative to the data folder |
| A backtest that *just* succeeded is followed by one that refuses to start | The previous run's terminal is still shutting down | Wait, then run again. See below |

The first row is by far the most common in daily use, because a trader keeps
MetaTrader open all day. It also produces the least evidence: exit code zero,
empty logs, no report. Check it first.

## The terminal outlives the script that started it

`backtest.ps1` returns as soon as the process it launched exits, and that is
**not** the same moment the terminal is gone. `ShutdownTerminal=1` fires once
testing completes, but before the process actually ends the terminal finishes
loading the normal profile: it reconnects to the broker, opens the saved charts,
initialises whatever EAs are attached to them, and only then shuts down.

Measured 2026-08-08, build 5836. A run that produced its report at 15:42:10 left
a terminal alive until `exit with code 0` at 15:43:25, about 75 seconds after the
script had already returned a fully parsed result. A second backtest started in
that window hit the "MetaTrader 5 is already running" guard and failed.

This matters because the failure lands on the *next* run, not the one that caused
it, so it reads as an unrelated problem. Two things follow:

- Back-to-back backtests are not reliably back-to-back. Check for a running
  `terminal64` and wait for it to disappear before starting the next one.
- The lingering process is genuinely a leftover of the automation, not the user's
  own MetaTrader. Confirm with its start time and the terminal log before killing
  anything: closing a terminal a human is using is far worse than waiting.

## What to say back to the user

Give them, in this order: whether the test was valid, how many trades, profit
factor, worst equity drawdown, and any of the four traps above that apply.

Then stop. Do not recommend trading it, do not suggest parameter changes to
improve the numbers, and do not compare it to a target return. Implementing and
measuring the strategy is the job; judging it is not.
