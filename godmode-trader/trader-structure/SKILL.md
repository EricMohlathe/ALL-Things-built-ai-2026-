---
name: trader-structure
description: >-
  Market Structure. The Smart Money Concepts and ICT read of one market on
  several timeframes at once: swing highs and lows, break of structure and
  change of character, trend per timeframe and whether they line up, open
  fair value gaps, order blocks and breaker blocks above and below, equal
  highs and lows (resting liquidity) and the last sweep, premium or discount
  in the dealing range, OTE zones, previous day and week highs and lows, the
  day open, the New York midnight open, the Asian range, round numbers, the
  killzone and Silver Bullet window right now, and an order-flow summary
  (CVD, volume profile POC / VAH / VAL, VWAP z-score, divergence, absorption)
  with its delta source always labelled. Use when the user says "market
  structure", "SMC", "ICT", "where is liquidity", "order blocks", "FVG",
  "premium or discount", "key levels", "bias", "order flow", "is it aligned",
  or before planning an entry.
argument-hint: "[read|levels] SYMBOL [--tf M15] [--htf H1,H4,D1] [--write]"
---

# trader-structure

Where is price in its range, which way did structure last break, where are
the stops resting, and what is still unfilled? This skill answers those
questions for any instrument in the registry, as of the last CLOSED bar,
on the base timeframe and every higher one you name.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/structure.py" read EURUSD                      # M15 + H1, H4, D1
python3 "${CLAUDE_SKILL_DIR}/structure.py" read XAUUSD --tf M5 --htf H1,H4   # a faster base
python3 "${CLAUDE_SKILL_DIR}/structure.py" read BTCUSD --write               # trader/structure/BTCUSD.json
python3 "${CLAUDE_SKILL_DIR}/structure.py" levels US500                      # key levels, nearest first
python3 "${CLAUDE_SKILL_DIR}/structure.py" --yahoo read GBPUSD               # live: the last 60 days of 5m bars
python3 "${CLAUDE_SKILL_DIR}/structure.py" --offline tests/fixtures/charts read EURUSD
```

Data comes from the trader-data cache by default (`/trader-data get EURUSD`).
`--yahoo` reads live 5-minute bars; `--offline` a saved chart.

## What it reads

| Part | What | Known when |
|---|---|---|
| Swings | a high (low) with two lower highs (higher lows) each side | 2 bars after the swing |
| BOS / CHoCH | a close beyond the last swing; CHoCH when it reverses the trend | at that close |
| FVG | the gap between candle 1's wick and candle 3's wick, open until filled | candle 3's close |
| Order block | the last opposite candle before the leg that broke structure | at the break |
| Breaker | an order block closed through: it flips side | at that close |
| Liquidity | equal highs / lows within 0.1 ATR: where stops rest | the second touch |
| Sweep | a wick through a pool that closes back: a stop hunt | at that close |
| Premium / discount | above or below 50 % of the last 50-bar range | now |
| OTE | 0.62 to 0.79 of the last swing leg, both ways | now |
| Levels | PDH / PDL / PDC, PWH / PWL, day open, NY midnight open, Asian range, round numbers | now |
| Killzones | Asia, London open, NY AM, London close, NY PM; Silver Bullet 3-4, 10-11, 14-15 NY | now |

Everything is computed from bars that had closed: nothing in a read uses a
bar that had not finished yet.

## Order flow, honestly labelled

The delta behind CVD, divergence and absorption is the best the data allows:
measured (Binance taker volume, or Dukascopy and MT5 ticks by the tick rule)
or, when there is nothing else, a proxy from where each bar closed in its
range. The read always says which. Forex has no central volume: treat any
forex "order flow" as an estimate.

## Reading the result

- **Bias** is a count of facts (structure, the last break, premium / discount,
  sitting in an FVG or at an order block, a recent sweep, displacement), not a
  forecast. Two or more one way reads bullish or bearish.
- **Alignment** compares the trend on every timeframe. "Aligned up" means each
  one last broke up. "Mixed" is the normal state of a market.
- **Invalidation** is the swing that would end the read: a close beyond it.
- Draw on liquidity is a hypothesis: price often reaches for the nearest
  untouched pool, and often does not.

## Where it goes next

1. `/trader-lab` tests the setups that use these facts (GM03 FVG, GM04 order
   block, GM05 Unicorn, GM11 Silver Bullet, GM12 OTE, GM14 turtle soup, GM16
   structure, GM21 previous-day levels, GM24 SMT): trade only what has a record.
2. `/trader-entry` and `/trader-exit` turn a level into an entry, stop and target.
3. `/trader-desk` puts this read beside the calendar, macro, COT and the lab.

This is a structure read, not a signal. Not financial advice.
