# High-Frequency Intraday — FINDINGS (no tradeable EA shipped)

**Verdict: a 4–5 trades/day edge does NOT exist in this strategy family once realistic
costs are applied. Every high-frequency config tested loses money on adequate data.**
No EA is shipped here on purpose — shipping a known money-loser would be dishonest.

## What was tested

Goal: find a config doing ~4–5 trades/day that keeps profit factor > 1.3 and survives
out-of-sample. Scanned the order-flow/liquidity strategy family on BTC/ETH at 5m & 15m,
hold and ATR-exit swept, on **crypto only** (the one market with free intraday data + real
order-flow; metals/indices/forex intraday cannot be validated without a paid data vendor).

## What the data showed (the trap)

Short windows looked great. They were mirages — as the sample grew, the edge evaporated and
the **net return went deeply negative**, because at 5–7 trades/day **fees + spread compound
faster than the thin gross edge**:

| config | 21–83 days | ~167 days | ~270 days |
|--------|-----------|-----------|-----------|
| gm16_sos ETH 5m (h5, stop3/tp1) | PF 1.40 / ret **−19%** | PF 1.20 / ret **−41%** | PF 1.01 / ret **−60%** |
| gm18_liqsweep BTC 15m (h8, stop4/tp1.5) | PF 1.21 / ret **−50%** | PF 1.16 / ret **−75%** | PF 0.93 / ret **−93%** |

Note the tell: **profit factor > 1 while total return is negative.** PF measures gross
win/loss; the negative return is what's left after costs. At high frequency, costs win.

## The honest conclusion

- **High frequency ≠ more money here. It's a cost furnace.** The genuine edge in these
  strategies lives on the **Daily** timeframe (`../GODMODE_DEITY_EAs/`, PF 3–9, ~5 trades/year).
- Want *more* activity without faking an edge: **run the 4 D1 deity EAs across all their
  validated markets at once** (SILVER, GOLD, NQ, ES, YM) → ~20–30 real trades/year aggregate,
  each from a validated edge — instead of ~1000 break-even-or-worse intraday trades.
- A true daily-frequency edge would require genuinely different alpha (tick-level order-flow
  with a paid real-time feed), which cannot be honestly built or validated on free data.

If you still want to experiment intraday, do it on **demo**, on your exact symbol, with your
broker's real spread modeled — and only keep a config that stays net-**positive** out-of-sample
*after costs*, not just PF > 1. The table above is why that bar matters.
