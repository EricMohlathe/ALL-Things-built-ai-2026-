# Strategy: RsiLevel

Plain RSI level strategy. Buy while RSI is below 30, sell while RSI is above 70.

Note the difference from `RsiReversal.md`, which trades the **cross** through the
same two levels. This one trades the **level itself**, so it can re-enter on
every bar the level holds. The daily entry cap is what bounds that.

## Market
- Symbol:                    EURUSDm
- Timeframe:                 H1
- Trading sessions, if restricted: none
- Days not to trade:         none

## Indicators
| Name | Parameters | Applied to | Purpose |
|---|---|---|---|
| RSI | Period 14 | Close price | Oversold below 30, overbought above 70 |

## Entry, long
1. Use only closed H1 candles.
2. Open buy when RSI(14) on the last closed bar is below 30.

## Entry, short
1. Use only closed H1 candles.
2. Open sell when RSI(14) on the last closed bar is above 70.

## Exit
- Stop loss:                 300 points
- Take profit:               600 points
- Early exit rule:           none
- Trailing stop:             no

## Position sizing
- Method:                    percent risk of account balance
- Risk per trade:            1%
- Max simultaneous positions: 1
- Max entries per day:       5

## Filters
- Max spread:                30 points
- Do not trade when:         spread is above 30 points, max positions is reached, or max daily entries is reached

## Bar timing
- Act on the closed bar, once per new H1 bar.

## Explicitly forbidden
- No averaging down.
- No pyramiding.
- No martingale.
- No opening more than one position at a time.

## Open questions

None blocking. The user described entry only and asked for a quick test, so the
values below were taken from the defaults already verified in this workspace
rather than left UNANSWERED. Every one of them is an EA input and can be changed
from a backtest run without recompiling.

| Assumed | Value | Change with |
|---|---|---|
| RSI period | 14 | `InpRsiPeriod` |
| Symbol and timeframe | EURUSDm H1 | backtest arguments |
| Bar timing | closed bar | not an input, code change |
| Stop loss | 300 points | `InpStopLossPoints` |
| Take profit | 600 points | `InpTakeProfitPoints` |
| Risk per trade | 1% of balance | `InpRiskPercent` |
| Max entries per day | 5 | `InpMaxTradesPerDay` |
