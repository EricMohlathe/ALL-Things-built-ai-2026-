# GODMODE HIGH-FREQUENCY EAs — MT5 + cTrader

For when you want **trades every day**, not every few weeks. These are intraday EAs.
Different beast from the D1 deity set (`../GODMODE_DEITY_EAs/`) — read the warning.

> **The honest tradeoff.** On these strategies, frequency and edge are *inversely* related.
> The D1 deity EAs trade ~5×/year at PF 3–9. To trade ~5×/**day** you drop to a 15-minute
> chart, and the profit factor falls to ~**1.2**. That is a *thin, grinding* edge — real, but
> fragile. Do not expect deity numbers at day-trading frequency. Nobody honest can give you both.

---

## GM18_LiqSweep_HiFreq

Liquidity-sweep reversal, **both directions**: price sweeps the prior swing-low (of closes,
LB) then closes in the upper half of its range → long; mirror for short.

**Validated** (real backtest, BTC 15m, ~8000 bars / ~83 days, no-lookahead, fees on, OOS = held-out 30%):

| Config | PF | Win % | Trades/day | OOS PF |
|--------|----|-------|-----------|--------|
| BTC 15m · Hold 8 · stopATR 4 · tpATR 1.5 | **1.21** | 65% | **~5.0** | **1.13** |

Defaults in the file = this config. Attach to a **15-minute** chart.

---

## ⚠️ Read before trading

1. **Thin edge (PF ~1.2) = spread-sensitive.** My backtest models fees but **not your broker's
   spread**. At ~5 trades/day, a wide spread compounds fast and can push this **below break-even**.
   Backtest on YOUR symbol *with realistic spread/commission* in the Strategy Tester before going live.
2. **Validated on crypto only.** BTC is the only market with free intraday data + real order-flow,
   so it's the only one I could honestly validate. The **logic runs on any symbol** you attach —
   the best forex pairs, metals (XAUUSD/XAGUSD), indices (NAS100/US30/US500), other crypto — but
   you **must re-validate per-symbol** in your platform's backtester. The edge is **not guaranteed
   to transfer** across asset classes. Treat each symbol as its own test.
3. **It trades both directions** and flips on opposite signals. Risk-sized to RiskPct of equity per
   trade via the ATR stop. Optional `MaxSpread` filter blocks entries when spread is too wide — use it.
4. **This is a grinder, not a printer.** ~5/day × thin edge = many small trades, slim aggregate.
   Position size conservatively (default 1%). Demo first, for weeks, on the exact symbol you'll trade.

## How to validate per-symbol (the only honest way to trust it elsewhere)

1. Attach to a **M15** chart of your target symbol (e.g. `XAUUSD`, `NAS100`, `EURUSD`).
2. Run the Strategy Tester over 1–2 years with **real spread** modeling.
3. Keep it only if it shows **PF > 1.2 AND positive on the out-of-sample (last 30%)** with your costs.
4. Tune `StopATR / TpATR / Hold` per symbol if needed — but always re-check OOS, don't curve-fit.

A deeper crypto hunt (BTC/ETH/SOL × 5m/15m/1h) is part of this build; any config that beats
gm18 (higher PF at ≥3 trades/day, positive OOS) gets added here as it's found.
