# Order-Flow Primitives — Definitions & Implementation Notes

This file is the single source of truth for what each primitive means, how to compute it, and what assumption-traps to avoid. Used by `orderflow-mt5-ctrader-mastery` and inherited from `godmode-orderflow-mastery`.

## 1. Delta

**Definition.** `Delta = AggressiveBuyVolume − AggressiveSellVolume` over a window.
A buy is "aggressive" when it lifts the ask. A sell is "aggressive" when it hits the bid.

**Per-tick classification (the only honest way on retail data).**
- `tick.price >= ask_at_tick` → aggressive buy (+volume)
- `tick.price <= bid_at_tick` → aggressive sell (−volume)
- `tick.price` between → uncertain → **discard or split 50/50** (be explicit which).

**MQL5 hook.** Inside `OnTick()`: `SymbolInfoTick(_Symbol, &tick)`; classify against last bid/ask snapshot.
**cAlgo hook.** Inside `OnTick()`: `Symbol.Bid`, `Symbol.Ask`. Classify against the previous tick's quote.

**Common mistake.** Using `Volume[i]` (tick volume) and signing it by candle direction (`close > open ? +V : −V`). This is *signed volume*, not true delta. Document this approximation if used.

## 2. Cumulative Delta (CVD)

**Definition.** Running sum of delta. `CVD_t = CVD_{t-1} + delta_t`.

**Reset policy.** Choose one and document it:
- Session reset (default for futures-style intraday).
- Daily reset (forex).
- Never reset (long-horizon CVD).

**Divergence rule.** Price makes new extreme, CVD does not → divergence.
- Bear: `price.high > prev.high && CVD.high < prev.CVD.high`
- Bull: `price.low  < prev.low  && CVD.low  > prev.CVD.low`

## 3. Footprint / Cluster / Bid-Ask grid

**Definition.** Per-bar histogram of volume at each price level, split into bid-side vs ask-side.

**Storage shape.** `Dictionary<priceLevel, (bid, ask)>` per bar. Round prices to `tickSize`.

**Imbalance print.** A level where `ask >= 3 * bid_atDiagonal` (bullish) or `bid >= 3 * ask_atDiagonal` (bearish). The diagonal is *one tick lower for bullish, one tick higher for bearish*. This is the standard 3:1 stacked imbalance.

**Stacked imbalance.** ≥ 3 consecutive imbalance prints in the same direction = strong initiative or stop run.

## 4. POC — Point of Control

**Definition.** Price level with the maximum traded volume in a window (bar, session, or selected range).

**Use cases.**
- Magnetism — price tends to revisit the developing POC.
- Acceptance vs rejection — closing above/below the POC signals which side wins the auction.

## 5. POI — Point of Imbalance (low-volume node)

**Definition.** Inverse of POC — the price level with the lowest traded volume inside a window. Also called LVN (Low Volume Node).

**Use cases.**
- Sweep targets — price moves through POI fast (no resistance).
- Edge of value area — a POI flanking a high-volume node often acts as a fence.

## 6. Value Area (VA)

**Definition.** The contiguous price range that contains 70% of session volume, centered on the session POC.
- VAH = Value Area High, VAL = Value Area Low.

**Trades.** Outside VA = "out of value", reversion to VA is a common mean-reversion edge. Acceptance above VAH = bullish breakout.

## 7. Initiative vs Responsive activity (AMT)

- **Initiative** — aggressive volume that pushes price *out of* prior value. New range-extending buyers/sellers.
- **Responsive** — passive/aggressive volume that defends prior value. Fade-the-edge crowd.

## 8. Absorption (effort vs result)

**Definition.** High aggressive volume into a level + low/zero price displacement = passive limit orders absorbing the aggression.

**Detection rules.**
- Per-candle: positive delta + bearish close (sellers absorbed buyers) → bearish absorption.
- Repeated: ≥ 2 attempts at the same level with similar volume and no progress.

## 9. Exhaustion (effort dropping while price still moving)

**Definition.** Price keeps making new highs/lows but volume and delta decline.
- Bull exhaustion: rising highs + declining volume + declining delta over N bars.
- Bear exhaustion: falling lows + declining volume + declining delta over N bars.
- Optional contrarian imbalance at the extreme strengthens the signal.

## 10. Initiative Auction

**Definition.** High aggressive volume + price displacement aligned with delta sign + above-average bar volume.
- Bull: strong + delta, candle closes up, volume ≥ avg × 1.5.
- Bear: strong − delta, candle closes down, volume ≥ avg × 1.5.

## 11. Book Sweep

**Definition.** Price moves through multiple orderbook levels with low resting volume — a vacuum.
- Detect via tracking level consumptions per second.
- ≥ N levels consumed in < T seconds, with low average resting volume per level.

## 12. Stop Run / Liquidity Grab

**Definition.** Price spikes through a known liquidity pool (prior swing high/low) then reverses inside the same bar.
- Confirm with absorption on the reversal leg.
- Confirm with delta divergence on the spike.

## 13. AMT phase enums (for godmode-orderflow-mastery alignment)

```
enum AMT_Phase {
  Balance,        // rotating inside value
  Imbalance,      // breaking out of value
  Discovery,      // trend extension
  Acceptance,     // building new value
  Failed_Auction  // fake breakout, mean reversion
};
```

## 14. Wyckoff 2.0 events (cheat sheet)

- **PS / SC** — preliminary supply / selling climax
- **AR** — automatic rally
- **ST** — secondary test
- **Spring / UTAD** — terminal shakeout / upthrust after distribution
- **SOS / SOW** — sign of strength / sign of weakness

These map onto: absorption + initiative for SOS, exhaustion + divergence for UTAD, etc.

## 15. Tick-size handling

Always normalize prices to the symbol's tick size:
- MQL5: `SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE)` and `NormalizeDouble(price, _Digits)`.
- cAlgo: `Symbol.TickSize`, `Symbol.Digits`, `Symbol.NormalizePrice(price)`.

Failure to normalize causes order-rejected errors and footprint bins that drift.
