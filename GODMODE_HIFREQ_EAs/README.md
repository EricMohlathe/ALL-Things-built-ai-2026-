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

## Follow-up: did a DIFFERENT strategy family help? (No.)

Tested conceptually different families intraday on BTC/ETH (15m + 1h, large samples), with the
cost-adjusted bar: pass only if **net-positive full-period AND out-of-sample AND ≥1 trade/day**.

| family | strategies | result |
|--------|-----------|--------|
| Mean reversion | rsi2, archon_vwaprev | net −37% to −42% (fail) |
| Momentum | archon_tsmom | +23% full but OOS ~0 (breakeven), 0.6/day (fail) |
| Trend | sma_cross, donchian | net −3% to −56% (fail) |
| Volatility breakout | archon_orb, deity_vol, archon_spike | best OOS +15% but negative full-period & <1/day (fail) |

**0 of 13 strategies × 4 families passed.** Configs with positive OOS were negative full-period
and below daily frequency; configs that traded daily were net losers. There is no honest
daily-frequency intraday edge in this universe on validatable (crypto) data.

## Follow-up 2: does H4 / H1 help? (Also no.)

The deity D1 setups (which earn PF 3–9 on Daily) were re-tested on **H4 and H1** crypto with the
same cost-adjusted bar. **0 of 48 configs passed.** Between the noise of 5m/15m and the edge of D1
there is no sweet spot — H4/H1 also fail net-positive-after-cost. The edge is a *Daily* edge.

If you still want to experiment intraday, do it on **demo**, on your exact symbol, with your
broker's real spread modeled — and only keep a config that stays net-**positive** out-of-sample
*after costs*, not just PF > 1. The tables above are why that bar matters. To validate intraday on
metals/indices/forex you need a paid feed — a Polygon.io adapter is wired (`source=polygon`, set
`POLYGON_API_KEY`); the free Yahoo feed has no usable intraday history for those.
