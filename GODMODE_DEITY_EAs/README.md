# GODMODE DEITY EAs — MT5 + cTrader

The validated winners. Selected from a **288-config cross-market scan** (39 strategies ×
8 markets, exit-optimized) — only configs passing **all** integrity guards survived:
**profit factor ≥ 1.2 · ≥ 40 trades · positive full-period return · positive out-of-sample**.
4 EAs made the cut. Each ships for **MetaTrader 5** (`.mq5`) and **cTrader** (`.cs`), fully
self-contained (no external libraries — drop in and compile).

> **Honesty contract.** Every number below is from a real backtest on real data
> (OpenAlice stdlib engine: no-lookahead, signal on bar close, fill next open, fees on,
> 70/30 train-test split). They are **edge evidence, not a live guarantee.** The single
> source of truth for live behaviour is **your broker's Strategy Tester** — run it before
> risking a cent. See *Why live ≠ backtest* below.

---

## The roster (best validated config per EA)

| EA | Concept (orderflow/liquidity/PA) | Best market | PF | Win % | Trades | Return | **OOS PF** |
|----|----------------------------------|-------------|----|-------|--------|--------|-----------|
| **GM14_Spring**   | Wyckoff spring / liquidity-sweep reclaim | SILVER | **5.74** | 71.7% | 53 | +323% | **8.96** |
| **GM11_StackBull**| Footprint buy-delta stacking (3-bar)     | GOLD   | **3.38** | 75.9% | 58 | +39%  | **6.48** |
| **GM16_SOS**      | Wyckoff Sign of Strength (demand expansion) | NQ  | **2.92** | 64.4% | 59 | +97%  | 2.31 |
| **GM22_AMD**      | ICT Accumulation-Manipulation-Distribution | YM  | **2.83** | 79.3% | 58 | +72%  | **5.20** |

OOS PF = profit factor on the held-out final 30% the optimizer never saw. OOS ≥ full-period
PF (e.g. GM14 8.96 > 5.74) = the edge held **out of sample**, the opposite of overfitting.

### Full validated preset table (set these inputs per market)

| EA | Market | StopATR | TpATR | TrailATR | PF | WR | OOS PF |
|----|--------|---------|-------|----------|----|----|--------|
| GM14_Spring | SILVER | 0 | 0 | 0 (hold-only) | 5.74 | 71.7% | 8.96 |
| GM14_Spring | YM | 4 | 1.5 | 0 | 2.48 | 81.0% | 2.01 |
| GM14_Spring | GOLD *(default)* | 3 | 1 | 0 | 2.29 | 75.5% | 2.78 |
| GM14_Spring | ES | 4 | 1.5 | 0 | 1.72 | 78.0% | 1.26 |
| GM11_StackBull | GOLD *(default)* | 3 | 1 | 0 | 3.38 | 75.9% | 6.48 |
| GM16_SOS | NQ *(default)* | 2 | 4 | 3 | 2.92 | 64.4% | 2.31 |
| GM16_SOS | ES | 3 | 1 | 0 | 2.87 | 83.6% | 1.81 |
| GM16_SOS | YM | 0 | 0 | 0 | 2.38 | 58.2% | 1.83 |
| GM16_SOS | SILVER | 1.5 | 3 | 2 | 1.83 | 57.1% | 2.91 |
| GM22_AMD | YM *(default)* | 4 | 1.5 | 0 | 2.83 | 79.3% | 5.20 |

All use **LB=20, K=1.0, Hold=10, ATR=14, Risk=1%** (the validated defaults). Only the
ATR exits change per market. Defaults baked into each file = the *(default)* row.

---

## Broker symbol mapping (important)

Backtests used continuous-futures daily data (Yahoo: `SI=F GC=F NQ=F YM=F ES=F`).
On your broker, attach each EA to the equivalent instrument, **Daily (D1)** timeframe:

| Validated market | Typical broker symbol(s) |
|------------------|--------------------------|
| SILVER | `XAGUSD`, `SILVER` |
| GOLD | `XAUUSD`, `GOLD` |
| NQ (NASDAQ-100) | `NAS100`, `USTEC`, `NQ` |
| YM (US30 / Dow) | `US30`, `DJ30`, `WS30` |
| ES (S&P 500) | `US500`, `SPX500`, `ES` |

---

## Install

**MT5:** copy `MT5/*.mq5` → `MQL5/Experts/GODMODE/`, open MetaEditor → **Compile** (F7),
attach to a **D1** chart of the mapped symbol, set the preset inputs, enable AutoTrading.

**cTrader:** in cTrader Automate → **New cBot** → paste a `cTrader/*.cs` file →
**Build**, attach to a **D1** chart, set parameters, run on a demo first.

---

## GODMODE_DeityController (one EA, all markets) — the "more trades" answer

`GODMODE_DeityController.{mq5,cs}` runs **all 4 setups across all their markets from one EA**
— the honest way to raise activity: ~20–30 validated trades/year aggregate, each from a proven
edge (vs ~1000 cost-losing intraday trades — see `../GODMODE_HIFREQ_EAs/`).

- **Roster input** (editable): `SYMBOL:SETUP:stopATR:tpATR:trailATR`, slots separated by `;`.
  Default = the validated winners. **Edit the symbols to match your broker** (XAGUSD/XAUUSD/
  NAS100/US500/US30 shown — yours may differ).
- Setups: `SPRING`=GM14 · `STACKBULL`=GM11 · `SOS`=GM16 · `AMD`=GM22.
- Attach to **one D1 chart** of any symbol; it pulls each roster symbol's own D1 bars and trades
  them independently, risk%-sized per slot. Backtest one symbol at a time in the Strategy Tester
  (both platforms only model the chart symbol in-tester — live runs all slots).

### Default roster — 14 D1 winners (breadth scan: PF≥1.5, ≥30 trades, net+ full AND OOS)

| slot (broker symbol) | setup | PF | WR | trades(10yr) | OOS PF |
|---|---|---|---|---|---|
| XAGUSD (silver) | SPRING | 6.18 | 72% | 53 | 10.6 |
| XAUUSD (gold) | AMD | 9.90 ⚠ | 94% ⚠ | 35 | 99 ⚠ |
| XAUUSD | STACKBULL | 3.38 | 76% | 58 | 6.5 |
| XAUUSD | SPRING | 2.29 | 76% | 49 | 2.8 |
| XAGUSD | AMD | 2.64 | 77% | 30 | 5.0 |
| XAGUSD | SOS | 1.83 | 57% | 49 | 2.9 |
| NAS100 (NQ) | SOS | 2.90 | 64% | 59 | 2.3 |
| US500 (ES) | SOS | 2.87 | 84% | 61 | 1.8 |
| US30 (YM) | AMD | 2.83 | 79% | 58 | 5.2 |
| US30 | SPRING | 2.48 | 81% | 58 | 2.0 |
| US30 | SOS | 2.39 | 58% | 67 | 1.9 |
| NAS100 | STACKBULL | 1.68 | 51% | 90 | 2.5 |
| US500 | SPRING | 1.72 | 78% | 50 | 1.2 |
| NAS100 | SPRING | 1.67 | 78% | 50 | 1.2 |

⚠ **XAUUSD/AMD (PF 9.90, WR 94%)**: only 35 trades over 10yr, OOS shows ~no losers — that is a
**small sample**. Treat the 94%/9.90 as *flattering, not reliable*. It's in the roster because it
passed the guards, but size it like any other slot — do NOT bet the account on a 94% win rate.

Aggregate ≈ ~800 trades / 10yr ≈ **~80/year (~0.3/day, ~1–2 per week)** across the 14 slots —
the honest "more trades" lift, every one from a validated edge.

**Asset-class note:** the edge in this family lives in **metals + indices**. Spot/futures **forex**
mostly failed the guards (only GBP via gm24 passed) — forex needs a different approach, not these
setups. Crypto intraday and all <D1 timeframes failed cost-adjusted (see `../GODMODE_HIFREQ_EAs/`).

## Audit summary (what was checked)

- ✅ **Logic parity** — each EA's entry condition matches its Python detector **1:1**
  (cross-checked term by term; see header comments).
- ✅ **Static lint** — brace/paren balanced; all required API calls present
  (`CTrade`/`CopyTickVolume`/`iATR` for MT5; `ExecuteMarketOrder`/`AverageTrueRange` for cTrader).
- ✅ **No-lookahead** — signal read on the **closed** bar (shift 1 / `Last(1)`), order on the new bar.
- ✅ **Risk management** — every trade sized to **RiskPct of equity** via the ATR stop distance;
  ATR stop-loss + take-profit + optional ratcheting trail; time-exit after `Hold` bars.
- ✅ **Long-only** — only the long side was validated; no short entries (verified — by design).
- ⛔ **Not yet done (only you can):** compile in MetaEditor / cTrader and run the **Strategy
  Tester** on your broker's data. That is the final truth. I cannot compile MQL5/C# on this machine.

## Why live ≠ backtest (read this)

1. **Delta proxy.** Metals/indices have no public taker-buy feed, so delta = *signed volume*
   (+volume on up-close bars, −volume on down). The EA uses **tick volume**; the backtest used
   daily volume. Close in spirit, not identical → expect different fill counts.
2. **Symbol & spread.** Your broker's CFD price, spread, and contract size differ from the
   continuous-futures series the backtest used.
3. **Trend-aligned, long-only.** These buy springs/sweeps inside **uptrending** assets. In a
   sustained downtrend they will underperform. Honest, not a defect.
4. **Daily timeframe, LOW frequency.** Backtest span = **10 years** (2016–2026, ~2513 D1 bars).
   50–67 trades over 10yr = **~5–6 trades per YEAR each** (≈ 1 every 6–9 weeks, ~0.02/day),
   holding ~10 trading days per trade. These are slow swing EAs — not day-traders. For more
   action, run all 4 across all their validated markets at once (≈ 20–30 signals/yr aggregate);
   don't force them onto lower timeframes without re-validating (the edge is proven on D1 only).

**Trade demo first. Risk only what you can lose. No EA is a money printer — these are edges, not certainties.**
