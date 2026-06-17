# GODMODE FOREX EAs — MT5 + cTrader

Forex needs a **different toolkit** than metals/indices. The footprint/delta setups
(`../GODMODE_DEITY_EAs/`) rely on volume — and **spot forex has ~no usable volume** — so they
don't fit. A dedicated forex hunt (price-only structure + mean-reversion + breakout families,
across 9 spot majors + 5 FX futures, D1, cost-adjusted) found these real edges:

## Validated forex edges (PF ≥ 1.4, ≥25 trades, net+ full AND out-of-sample)

| strategy | market | PF | WR | trades | OOS PF | shipped as |
|----------|--------|----|----|--------|--------|-----------|
| **RSI2** (mean reversion) | JPY (6J) | **4.73** | 76% | 45 | 2.88 | `RSI2_Reversion` ✅ |
| gm14 spring | EURJPY | 2.55 | 75% | 59 | 1.87 | use `../DEITY/GM14_Spring` on EURJPY, stop0/tp0 |
| gm14 spring | GBPJPY | 1.99 | 72% | 54 | 1.79 | same, on GBPJPY |
| gm24 poorhl | GBP (6B) | 1.65 | 47% | 43 | 2.40 | (logic only — not shipped as EA) |
| **archon ORB** (breakout) | EUR (6E) | 1.62 | 50% | **90** | 3.58 | `ArchonORB_Breakout` ✅ |
| archon ORB | EURJPY | 1.58 | 47% | **108** | 2.04 | same, stop1/tp2/trail1.5 |
| gm15 upthrust | NZDUSD | 1.52 | 61% | 61 | 1.40 | (logic only) |
| archon tsmom | EURJPY | 1.51 | 53% | 45 | 1.37 | (logic only) |
| gm18 liqsweep | AUDUSD | 1.47 | 68% | **101** | 2.27 | use intraday EA logic on AUDUSD **D1** |

## Shipped EAs (MT5 + cTrader)

### RSI2_Reversion  (mean reversion, long-only)
Connors RSI(2): buy oversold dips only above the 200-SMA (uptrend), exit when RSI(2) > 60.
Default exits stop4/tp1.5. Strongest forex PF (4.73 on JPY). No volume needed.

### ArchonORB_Breakout  (volatility breakout, long + short)
Break of the prior 20-bar close-range by a K·ATR buffer, in the 50-SMA trend direction.
Default = EUR(6E) preset stop3/tp6. Highest forex trade volume (90–108/run). No volume needed.

## Presets per market

| EA | market | StopATR | TpATR | TrailATR | notes |
|----|--------|---------|-------|----------|-------|
| RSI2_Reversion | USDJPY / JPY | 4 | 1.5 | – | validated on 6J |
| ArchonORB | EUR / EURUSD | 3 | 6 | 0 | validated on 6E |
| ArchonORB | EURJPY | 1 | 2 | 1.5 | 108 trades |
| GM14_Spring (deity pack) | EURJPY, GBPJPY | 0 | 0 | 0 | raw / hold-only |

## Honest notes

- **Broker symbols:** 6J≈USDJPY (inverted), 6E≈EURUSD, 6B≈GBPUSD. The EA logic is symbol-agnostic
  — attach to your pair's **D1** chart and **re-validate in the Strategy Tester** before trusting.
  Validated instance ≠ guaranteed on every pair.
- **Frequency:** still Daily — ~5–11 trades/year per pair (RSI2 45, ORB 90–108 over ~10–20yr).
  Run several pairs to stack activity. Intraday forex still fails cost-adjusted (no free data to
  prove otherwise; wire `POLYGON_API_KEY` to test it yourself).
- **Long-only RSI2 / both-way ORB**, risk%-sized via ATR stop, demo first. No EA wins 100%.
