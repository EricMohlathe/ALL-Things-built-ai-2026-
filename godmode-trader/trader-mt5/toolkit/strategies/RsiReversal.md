# Strategy: RsiReversal

## Market
- Symbol:                    EURUSDm
- Timeframe:                 H1
- Trading sessions, if restricted: none
- Days not to trade:         none

## Indicators
| Name | Parameters | Applied to | Purpose |
|---|---|---|---|
| RSI | Period 14 | Close price | Detect reversal crosses at 30 and 70 |

## Entry, long
1. Use only closed H1 candles.
2. Open buy when RSI(14) crosses up through 30: previous closed bar RSI <= 30 and latest closed bar RSI > 30.

## Entry, short
1. Use only closed H1 candles.
2. Open sell when RSI(14) crosses down through 70: previous closed bar RSI >= 70 and latest closed bar RSI < 70.

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
- None.
