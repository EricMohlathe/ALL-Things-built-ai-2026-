# 02 — The Asian Range Liquidity Sweep

The overnight session consolidates into a tight range. Breakout traders take
positions at its edges and leave their stops just beyond. The model waits for
price to run through one of those edges, and takes the *reversal*.

**EA preset:** `PRESET_ASIAN_ICT`
**Range timeframe:** M15 or M5 · **Entry timeframe:** M5 or M1
**Recommended instruments:** XAU/USD, GBP/USD, EUR/USD, NQ, ES.

---

## Read this before the rules

The 9:30 model in `01` trades a break *outward*. This model trades a break
*back inward*. Both are pointed at the same kind of level, and both have
sources full of winning screenshots.

They can both be right, and the reason is not mystical. Osler's research on
actual currency order books found two distinct clusters around any obvious
level:

- **Take-profit orders cluster *at* the level.** They are limit orders. They
  absorb the move and push price back. This is the reversal the Asian model is
  trading.
- **Stop-loss orders cluster *just beyond* the level.** They are market orders.
  They consume liquidity and accelerate price onward. This is the continuation
  the 9:30 model is trading.

Which cluster is larger on a given morning is not something you can read off
the chart in advance. The honest statement of what the sweep tells you is
this: **the sweep predicts volatility, not direction.** Everything below is an
attempt to constrain direction using something *other* than the sweep itself —
which is exactly what the higher-timeframe bias requirement is for, and why
skipping it is the most expensive mistake on this list.

---

## The rules

### Step 1 — Set the higher-timeframe bias, first

Before you mark anything, read the **daily and H4** structure: bullish, bearish,
or unclear. Write it down before the session, not after the sweep.

If the answer is unclear, **the day is a no-trade.** This is not optional
garnish. Without a bias, every sweep looks like a setup and roughly half of
them are the beginning of a trend, not the end of one. The source article lists
"no higher-timeframe bias" as its second-biggest recurring mistake, and its
author, asked directly whether the strategy always works on gold, answered:
"It works if you have a correct Daily Bias."

Bias determines *which* sweep you are waiting for:

| Bias | You are waiting for | You will trade |
|---|---|---|
| Bullish | Price to sweep **below** the Asian **low** | Long |
| Bearish | Price to sweep **above** the Asian **high** | Short |
| Unclear | Nothing | Nothing |

### Step 2 — Mark the Asian range

**19:00 – 00:00 New York local time.** Mark the **high** and the **low** of that
window and extend both forward.

Also mark the **midnight open** — the price at 00:00 NY. It is a reference level
in its own right, and it defines where the two entry options in Step 5 sit.

Note the window wraps midnight, so the range belongs to the trading day that
*follows* it.

### Step 3 — Wait for the sweep

Price must actually take out the level. Not approach it, not "basically tag"
it. Take it out.

The sweep usually lands at the **London open (03:00 NY)** or in the **early New
York AM (08:00–10:00 NY)**. The EA's entry window runs 02:00–11:00 NY to cover
both.

**No sweep means no trade.** Price does not sweep Asian liquidity every day.
Sundays, holiday weeks, and days where high-impact news lands inside the London
open frequently produce no tradeable range at all. Sitting out is a result.

### Step 4 — Wait for the market structure shift

This is the filter that carries the strategy. Drop to **M5 or M1** after the
sweep and wait for a **market structure shift** — price closing back inside the
range and then breaking the most recent opposing swing point in your intended
direction.

A wick through the Asian high with no MSS afterwards **is not a trade.** It is
the most common way people lose money on this model: they see the sweep, call
it confirmation, and enter into what turns out to be the first leg of a trend
that keeps going.

The EA implements this as `MODEL_SWEEP_MSS`:

```
InpReclaimBars      = 6    // sweep must close back inside within N bars
InpMSSFractalRight  = 2    // fractal confirmation bars for the MSS swing
InpMSSLookback      = 40   // bars scanned for the swing level
```

`InpReclaimBars` is the teeth of it. If price sweeps and does not reclaim the
level within six bars, it was not a sweep — it was a breakout, and you are on
the wrong side of it.

### Step 5 — Entry

Three entries, in descending order of price quality:

1. **At the midnight open.** In a bullish setup, buy below the midnight open
   price — but only *after* the Asian low has been taken. Never before.
2. **On the retracement.** Enter into the order block, fair value gap, or mean
   threshold left behind by the displacement leg that formed the MSS. This is
   the standard entry and the one the EA models.
3. **On the range re-cross.** If you missed the first two, buy when price
   reverses back above the Asian *high* (bullish) or falls back below the Asian
   *low* (bearish). Worst price, most confirmation.

### Step 6 — Stop loss

**10 to 20 pips beyond the MSS swing point** — below the MSS low on a long,
above the MSS high on a short.

The buffer is not negotiable, and the reason is the whole premise of the
strategy: stops parked exactly at an obvious swing are precisely the liquidity
that gets taken on the second test. You cannot build a strategy around hunting
other people's stops and then leave yours at the obvious price.

On gold, 20–30 pips. On JPY pairs, 10–20.

### Step 7 — Take profit

Target the **next low-resistance liquidity run** in the trade direction —
typically the previous session's high or low, or the next external liquidity
pool. In R terms this usually lands between 2R and 4R.

If you are running the EA on a fixed target, 2R is the default and 3R is worth
testing. Do not set 3R because a vendor promised 1:3 — set it because your own
journal's MFE distribution says the move gets there often enough.

---

## About the "80% win rate at 1:3" claim

One of the source documents sells a gold Asian-session system on an 80% win
rate at 1:3 risk-reward. Take that claim at face value for a moment:

```
Expectancy = 0.80 × (+3R) + 0.20 × (−1R) = +2.20 R per trade
```

At 1% risk per trade over 250 trades — one trading year — that compounds
$1,000 into roughly **$223,000**. In year two it clears $49 million.

The claim refutes itself. Anyone with +2.20 R per trade does not sell a PDF;
they take outside capital, or they take none and stay quiet. The same document
also advertises a broker referral link and reports its results in dollars
rather than R, which makes the numbers unfalsifiable — $6,315 in 41 minutes
tells you the position size, not the edge.

This is not a reason to dismiss the Asian-range structure. It is a reason to
treat every number attached to it as marketing until your own journal produces
a different one.

---

## Configuration

```
=== 1. PRESET & MODEL ===
InpPreset              = PRESET_ASIAN_ICT
InpModel               = MODEL_SWEEP_MSS
InpRangeTF             = PERIOD_M15
InpEntryTF             = PERIOD_M5

=== 2. CLOCK ===
InpBrokerGMTOffset     = <your broker's winter offset — verify it>

=== 3. SIGNAL RULES ===
InpRequireBodyClose    = true
InpReclaimBars         = 6
InpMSSFractalRight     = 2
InpMSSLookback         = 40
InpMaxBarsToTrigger    = 60
InpMaxRangeATR         = 2.5      // a wide overnight range is not a consolidation

=== 4. BIAS  — NOT optional on this strategy ===
InpBiasMode            = BIAS_HTF_EMA
InpBiasTF              = PERIOD_H4
InpBiasEMAPeriod       = 50
InpBiasBlocksCounter   = true

=== 5. STOPS & TARGETS ===
InpExitMode            = EXIT_FIXED_R
InpTargetR             = 2.0
InpStopBufferPts       = <10-20 pips in points for your symbol>
InpMinStopATR          = 0.25
InpMaxStopATR          = 3.0

=== 6. RISK ===
InpRiskPercent         = 0.5
InpMaxDailyLossPct     = 2.0
InpMaxTradesPerDay     = 1        // one sweep per session; the second is revenge
InpMaxConsecLosses     = 4

=== 7. JOURNAL ===
InpWriteJournal        = true
InpRunTag              = "asian_sweep_v1"
```

`BIAS_HTF_EMA` is a mechanical stand-in for the discretionary daily bias the
sources describe. It is not the same thing, and it is almost certainly worse
than a skilled read — but it is *testable*, and a discretionary bias is not.
If your manual bias beats the EMA filter over 100 sessions, you have measured
something real about your own skill. That is worth more than the backtest.

---

## The test that matters most here

Run the strategy twice on the same data, changing only the bias:

```bash
# With the bias filter
python3 srf_forensics.py asian_with_bias.csv --target-r 2.0 --variants 2 --plots bias_on.png

# With InpBiasMode = BIAS_OFF, everything else identical
python3 srf_forensics.py asian_no_bias.csv --target-r 2.0 --variants 2 --plots bias_off.png
```

If the bias filter does not improve the result, then either your bias
definition is wrong or the sweep genuinely carries no directional information
on this instrument — and in the second case the strategy has no premise left.
That is the single most informative backtest in this folder.

---

## Common mistakes, from the sources and from the math

1. **Pre-positioning before the sweep.** The sweep is the trigger. An entry
   placed before the level is taken is a breakout trade wearing a costume.
2. **Skipping the bias.** Covered above. The strategy has no directional
   premise without it.
3. **Treating a wick as confirmation.** No MSS, no trade.
4. **Stops at the obvious swing.** The 10–20 pip buffer is the price of not
   being the liquidity.
5. **Trading every session.** A range that is too wide is not a consolidation,
   and there is nothing to sweep. `InpMaxRangeATR` enforces this; do the same
   by hand.
6. **Wrong instrument for the window.** Trading an Asian-range setup on a
   US-only instrument during the actual Asian session produces nothing. Wait
   for the London or NY open before acting on the sweep.
7. **Assuming direction from the sweep alone.** Both source families point at
   this level and trade it in opposite directions. Whichever one you have read
   most recently is not evidence.
