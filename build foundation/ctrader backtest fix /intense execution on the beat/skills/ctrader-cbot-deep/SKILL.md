---
name: ctrader-cbot-deep
description: Deep-dive cTrader / cAlgo (C#) reference for order-flow cBots and indicators. Use when the user is committed to cTrader only — Symbol.MarketDepth, ExecuteMarketOrder, IndicatorDataSeries, Chart.Draw*, cBot lifecycle. Triggers on "cTrader only", "cAlgo only", "C# trading bot", "cBot", "Symbol.MarketDepth", "ExecuteMarketOrder", "build me a cTrader robot", "convert this Pine to cTrader", "convert MQL5 to cTrader".
---

# cTrader / cAlgo Deep Reference

This skill is the platform-pinned sibling of `orderflow-mt5-ctrader-mastery`. Use it when the user explicitly does not need MT5 output.

## When to use vs the master skill
- Master skill → ship MT5 + cTrader together.
- This skill → user pinned cTrader only; do NOT emit MQL5 code.

## Procedure
1. Load `references/ctrader_calgo_patterns.md` from master skill.
2. Load `references/orderflow_signal_logic.md` (cAlgo column only).
3. Load `templates/ctrader_cbot_template.cs` and `templates/ctrader_indicator_template.cs`.
4. Apply user's playbook into the marked SIGNAL LOGIC region.
5. Emit `<EaName>.cs` (and a `.params` file with default settings).

## cAlgo-specific best practices
- Always use `Symbol.NormalizeVolumeInUnits(..., RoundingMode.Down)` before `ExecuteMarketOrder`.
- Always pass a unique `label` so `Positions.FindAll(label, SymbolName)` can isolate EA trades.
- Always handle `TradeResult.IsSuccessful == false` with `Print(r.Error)`.
- Always wire `Positions.Closed` event for cooldown tracking.
- Always use `Server.Time` (UTC) for session logic, not `DateTime.Now`.
- For depth: `Symbol.MarketDepth.Updated += handler;` in `OnStart`, unregister in `OnStop`.
- Use `IndicatorDataSeries` (not raw arrays) for indicator outputs so they bind to chart.

## Output contract
Same as master skill, but the MQL5 column is omitted.
