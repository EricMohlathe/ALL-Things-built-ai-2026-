---
name: mql5-patterns
description: Verified MQL5 code for MetaTrader 5 Expert Advisors. Use before writing any EA logic, and whenever you need order sending, lot sizing, position lookup, indicator handles, new-bar detection, broker capability detection, or restart-safe state. Every snippet here has been compiled successfully. Reuse these instead of writing from memory. Do not use for MQL4, for indicator development, or for strategy design decisions.
---

# Verified MQL5 patterns

Every snippet referenced here comes from a file that compiled with zero errors
on MetaEditor build 5836. Prefer these over anything recalled from training.

Start from `templates/EA_Template.mq5` rather than an empty file.

## What is where

| File | Covers |
|---|---|
| `references/lifecycle.md` | `OnInit` / `OnTick` / `OnDeinit`, indicator handles, new-bar detection |
| `references/broker-adaptation.md` | Filling mode, netting vs hedging, symbol suffix, volume and stop constraints |
| `references/state-and-restart.md` | Position lookup by magic number, trade result codes, surviving a restart |
| `references/entry-exit.md` | Sending and closing orders, trailing stop, break even, multiple positions |
| `references/filters.md` | Server time, trading hours, day of week, spread, connection loss, news |
| `references/risk-sizing.md` | Lot from percent risk, and the two rails that stop a tight stop becoming a huge position |
| `references/diagnosing-no-trades.md` | What to do when the backtest reports zero trades |

Read only the file you need. Do not load all of them by reflex.

## Five rules that override anything you remember

**1. Indicator functions return a handle, not a value.**
Create the handle once in `OnInit`, read values with `CopyBuffer`, release in
`OnDeinit`. Calling `iMA` inside `OnTick` leaks a handle every tick.

**2. Detect the broker, never assume it.**
Filling mode, symbol suffix, lot step, stop level and account margin mode all
vary between brokers and even between account types at the same broker. Read
them at runtime. A hardcoded `EURUSD` fails on any account whose symbol is
`EURUSDm`.

**3. Every order must be normalised before sending.**
Round volume to `SYMBOL_VOLUME_STEP`, clamp to min and max, normalise prices to
the symbol's digits, and respect `SYMBOL_TRADE_STOPS_LEVEL`. Unnormalised
orders are rejected by the broker, not by the compiler.

**4. Check `retcode` on every trade operation.**
Never fire and assume. At minimum handle requote, not enough money, invalid
stops, market closed, and unsupported filling mode.

**5. Rebuild state from the account, never from memory.**
The terminal runs on a home PC and will be restarted, sometimes mid-position.
Every global variable resets; the positions do not. Count open positions with
`PositionsTotal`, count today's activity with `HistorySelect`. An EA that caps
daily entries with a counter variable will blow through the cap after a midday
restart.

## Required in every EA

- A `MagicNumber` input, and every position operation filtered by it
- Risk expressed as a percentage of balance, never a hardcoded lot size
- A maximum spread filter
- A cap on simultaneously open positions
- Logging that says which EA acted, why it entered, and why it exited

## After a snippet proves itself

When you write something that compiles and behaves correctly in the Strategy
Tester, add it to the matching reference file with a one-line note on when to
use it and the date it was verified. That is what makes this repository better
over time.
