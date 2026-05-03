# GODMODE_OFEA — Testing Protocol

Per brief §14, with §23.7 multi-symbol acceptance addendum.

## Phase 1 — Compilation

| Build | Tool | Acceptance |
|-------|------|------------|
| MT5 | MetaEditor 5 | Zero warnings, zero errors with `#property strict` |
| cTrader | cAlgo IDE | Zero warnings, zero errors |

If either build emits a warning, fix the warning before proceeding. No exceptions.

## Phase 2 — Visual Test Checklist

Load on a live EURUSD M5 demo chart during London Main (11:00–15:30 SAST).

- [ ] Dashboard panel renders in top-right corner with all 8 checklist rows visible
- [ ] Magenta POC line visible
- [ ] Dodgerblue VAH and VAL dashed lines visible
- [ ] Translucent blue session shading covers London Main window
- [ ] On price touching VAL: yellow horizontal line appears, N-A toast fires, single beep, dot ④ flips green
- [ ] Profile shape classification appears in dashboard ("BAL" / "IMB" / "UNK")
- [ ] H4/D1 EMA bias renders in HTF row
- [ ] CVD direction reflects in dashboard row ⑤
- [ ] On bullish absorption: green star ★ appears below the bar with star count badge
- [ ] On all 8 gates green: full-screen flash + N-I "A+ ENTRY READY" popup
- [ ] In MODE_MANUAL: trade lines (entry/SL/TP) draw but no order is placed
- [ ] In MODE_AUTO: order fires within 2 seconds of N-I, N-J chime confirms
- [ ] Position management — at 1R: 50% partial close, BE+1pip stop move, N-K toast
- [ ] Position management — POC reached (Model 2): 100% close, N-K toast
- [ ] At 21:00 SAST (NY Main close − 5min): all positions flatten, N-L red banner

## Phase 3 — MT5 Backtest Protocol

1. Open Strategy Tester (Ctrl+R).
2. Configure:
   - Expert: `GODMODE_OFEA`
   - Symbol: EURUSD
   - Timeframe: M5
   - Period: last 6 months
   - Modeling: **"Every tick based on real ticks"**
   - Initial deposit: 10,000 USD
   - Leverage: 1:100
   - `OperatingMode = AUTO`
3. Start.
4. Acceptance criteria:
   - Profit Factor ≥ **1.5**
   - Win Rate ≥ **65%** on filtered (gate-passing) trades
   - Max Drawdown ≤ **12%**
   - Recovery Factor ≥ **2.0**
   - Expected trades: 600–1500 over 6 months (5–15/day × ~120 trading days)

If acceptance fails, do **not** ship. Re-tune parameters per `docs/parameter_tuning.md`, then re-test.

## Phase 4 — cTrader Backtest Protocol

1. Open cBot project → Backtesting.
2. Configure:
   - Symbol: EURUSD
   - Period: last 6 months
   - Mode: **Tick data from server**
   - Initial deposit: 10,000 USD
   - `OperatingMode = Auto`
3. Run.
4. Same acceptance metrics as Phase 3.

## Phase 5 — Forward Test

After both backtests pass acceptance:

1. Deploy both builds to demo accounts (one MT5, one cTrader, same broker if possible).
2. `OperatingMode = AUTO` on both.
3. `RiskPct = 0.25` (quarter size during forward test).
4. Run 2 weeks minimum.
5. Verify:
   - No spurious trades outside session windows
   - No trades during NY Open blackout (15:30–15:50 SAST)
   - Stops placed 1–2 ticks beyond aggression candle (not at swing extremes)
   - Position closes at POC for Model 2 trades
   - All positions flatten by 21:00 SAST

## Phase 6 — A/B Comparison

Run both builds simultaneously on demo accounts with identical parameters.

| Metric | Acceptance |
|--------|------------|
| Signal agreement rate | ≥ 95% (allow 5% for tick-data quality differences) |
| Fill price difference (per trade) | ≤ 0.5 pips |
| Slippage (rolling 20-trade avg) | ≤ 0.3 pips |
| Net P&L deviation | ≤ 5% over 2 weeks |

If signal agreement < 95%, the builds have functionally diverged — do not ship until aligned.

## Phase 7 — Multi-Symbol Acceptance (when MultiSymbol_Enable=true)

Per brief §23.7:

- 6 months backtest across `MultiSymbol_List` (default: EURUSD, GBPUSD, USDJPY, XAUUSD, US100, US500).
- Verify trade count averages 8–12/day (within 5–15 target).
- Verify no day exceeds `MultiSymbol_MaxPerDay` (default 12).
- Verify no symbol exceeds `MultiSymbol_MaxPerSymbol_PerDay` (default 4).
- Verify correlation filter blocks the expected pairs (EURUSD/GBPUSD, USDJPY/USDCHF, XAUUSD/XAGUSD, US100/US500).
- Verify aggregated win rate falls in the 76–78% sustained range with isolated 50-trade windows reaching 80%+.

> **Note**: Multi-symbol scanning is documented as Phase-2 in CHANGELOG.md — the §23 architecture is described in the brief but the parallel-symbol dispatcher is not in the v1.0 build. v1.0 is single-symbol; v1.1 will add the multi-symbol layer.

## Phase 8 — Operator Acceptance

The §18 user story is the truth condition. End-to-end on a live demo chart:

1. Attach EA to EURUSD M5 during London Main.
2. Watch the dashboard fill in: state classified, kill zone tagged, HTF aligned, VP loc set, CVD confirms, footprint signal fires, SL defined, R:R computed.
3. All 8 dots green → N-I full-screen flash → "A+ ENTRY READY" popup with score and direction.
4. In MANUAL: nothing fires, but every notification fires visibly, every dot transitions, every chart marker draws.
5. In AUTO: trade fires within 2 seconds of N-I.
6. Position is managed: partial at 1R, BE move, trail, POC exit.

If the EA does not behave this way end-to-end, it isn't done.
