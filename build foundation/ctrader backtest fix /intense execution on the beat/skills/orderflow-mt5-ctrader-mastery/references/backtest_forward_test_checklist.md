# Backtest + Forward-Test Checklist

The user must walk away knowing exactly how to validate the EA. This file is the test plan.

## A. MT5 Strategy Tester

1. Symbol: `<symbol>` — match broker spread profile.
2. Period: at least 12 months of M5/M15 + 24 months of H1 for trend filter.
3. Modeling: **Every tick based on real ticks** (only this gives valid order-flow results).
4. Initial deposit: 10 000 (account currency).
5. Leverage: match live account.
6. Optimization passes: never optimise on full data. Walk-forward: 70% in-sample / 30% out-of-sample, stride 3 months.

### Sanity checks
- Equity curve starts roughly flat — no spike on bar 1 (would indicate look-ahead).
- Trade count consistent with playbook expectation (e.g. 1–4 trades/day for tick-driven).
- Max drawdown ≤ 2× per-trade risk × max consecutive losses observed.

## B. cAlgo backtester

1. Time period: same window as MT5 run for parity.
2. Data source: tick (preferred) or m1.
3. Commission + spread: match live account.
4. Currency conversion: enable.

### Optimisation
- Genetic + walk-forward via the `Optimisation` tab.
- Save the best-by-OOS-Sharpe set, not best-by-net-profit.

## C. Forward-test plan (4-week minimum)

| Week | Goal | Risk |
|---|---|---|
| 1 | Demo, observe only — no auto-trades | 0% (manual confirm) |
| 2 | Demo, micro lots, full automation | 0.1% |
| 3 | Live cent / 1-cent prop sub-account | 0.25% |
| 4 | Full live | full configured `InpRiskPct` |

## D. Parity checks (when shipping both MQL5 + cAlgo)

1. Same data window, same symbol, same tick source if possible.
2. Trade-count diff ≤ 5%.
3. Net P&L diff ≤ 10% (commission + spread asymmetry causes the rest).
4. Drawdown profile shape similar (eyeball the equity curves).

If any check fails, the porting is broken — do not ship.

## E. Failure-mode tests

Force each scenario in a small offline harness or by editing inputs:
- Spread spike (set `InpMaxSpread` very low) → EA should pause, dashboard should show `WIDE_SPREAD`.
- Daily loss exceeded → EA should freeze, alert fired once.
- Connection drop → EA should not place orders during reconnect; existing positions left untouched.
- News window → EA should skip entries within the configured blackout.

## F. Live-monitoring metrics

Once live, log + chart:
- Hit rate (last 50, last 200).
- Avg R-multiple.
- Avg time-in-trade.
- Slippage (signal → fill).
- Drawdown vs configured halt.
- Consecutive losses streak.

