---
name: mql5-strategy-intake
description: Turn a spoken or written trading strategy description into a complete specification file before any MQL5 is written. Use when the user describes a strategy in conversation, asks for a new EA, or points at a file in strategies/ that is incomplete. Produces strategies/<name>.md and asks about anything missing. Do not use for editing an EA that already has a specification.
---

# Strategy intake

Vague descriptions are the number one cause of wrong generated code. This skill
exists to make the gaps visible before a single line of MQL5 is written.

## Process

1. Write what the user gave you into `strategies/<name>.md` using the template
   below. Leave gaps marked `UNANSWERED`.
2. Ask about the gaps. Ask all of them in one message, not one at a time.
3. Only after every `UNANSWERED` is filled, copy `templates/EA_Template.mq5`
   to `src/Experts/<name>.mq5` and implement the STRATEGY section.

Never guess a missing rule. A guessed entry condition produces an EA that
trades real money on something the user never asked for.

## What counts as vague

"Buy when RSI is oversold" is missing five things:

- RSI period
- The threshold
- Crossing up through it, or simply being below it
- Measured on the closed bar or the forming one
- What closes the trade

Ask. Do not pick defaults.

## Template for strategies/<name>.md

```markdown
# Strategy: <name>

## Market
- Symbol:                    (exact broker name, check the suffix, e.g. EURUSDm)
- Timeframe:
- Trading sessions, if restricted:
- Days not to trade:

## Indicators
| Name | Parameters | Applied to | Purpose |
|---|---|---|---|
|  |  |  |  |

## Entry, long
1.
2.

## Entry, short
1.
2.

## Exit
- Stop loss:                 (fixed points, ATR multiple, structure)
- Take profit:               (or none)
- Early exit rule:           (or none)
- Trailing stop:             (yes or no, and the exact rule)

## Position sizing
- Method:                    (fixed lot, % risk of balance, other)
- Risk per trade:
- Max simultaneous positions:
- Max entries per day:

## Filters
- Max spread:
- Do not trade when:

## Bar timing
- Act on the closed bar, or on every tick:

## Explicitly forbidden
(e.g. no averaging down, no martingale, no hedging)

## Open questions
- UNANSWERED: ...
```

## Two questions people always forget

**Closed bar or forming bar.** Acting on the forming bar means the signal can
appear and disappear within the same bar. Almost every strategy means the
closed bar. Confirm it rather than assuming.

**What closes the trade.** Many descriptions cover entry in detail and say
nothing about exit. An EA with no exit rule holds until stop loss or take
profit, which is often not what was meant.

## Symbol names

Ask for the exact symbol as it appears in the user's Market Watch. Brokers add
suffixes: Exness uses `EURUSDm`, not `EURUSD`. A wrong name does not warn, it
aborts the whole backtest.
