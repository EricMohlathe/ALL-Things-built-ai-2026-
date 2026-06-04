---
name: mql5-orderflow-deep
description: Deep-dive MQL5 reference for order-flow EAs and indicators. Use when the user is committed to MetaTrader 5 only and wants a full-fat MQL5 implementation — OnTick, OnBookEvent, MqlBookInfo, CTrade, iCustom, ChartObjects, OBJ_RECTANGLE for value areas. Triggers on "MQL5 only", "MetaTrader 5 EA", "MetaEditor", ".mq5", "MarketBookAdd", "OnBookEvent", "MQL5 footprint", "MQL5 cumulative delta", "build me an MT5 robot", "convert this Pine to MT5".
---

# MQL5 Order-Flow Deep Reference

This skill is the platform-pinned sibling of `orderflow-mt5-ctrader-mastery`. Use it when the user explicitly does not need cTrader output.

## When to use vs the master skill
- Master skill (`orderflow-mt5-ctrader-mastery`) → ship MT5 + cTrader together.
- This skill → user pinned MT5 only; do NOT emit cAlgo code.

## Procedure
1. Load `references/mql5_orderflow_patterns.md` from the master skill (canonical idioms).
2. Load `references/orderflow_signal_logic.md` from the master skill (only the MQL5 column).
3. Load the master skill's `templates/mt5_ea_template.mq5` and `templates/mt5_indicator_template.mq5`.
4. Apply the user's playbook into the marked SIGNAL LOGIC region.
5. Emit `<EaName>.mq5` + `<EaName>.set`.

## MQL5-specific best practices
- Always use `CTrade` (`<Trade/Trade.mqh>`) — never `OrderSend` directly.
- Always set `MagicNumber`, `Deviation`, `TypeFilling` once in `OnInit`.
- Always validate `iATR`, `iCustom` handles before `CopyBuffer`.
- Always wrap `MarketBookAdd` in error-checking and release in `OnDeinit`.
- Always call `IsStopped()` checks in long loops to allow tester abort.
- Always `ChartRedraw()` after `Comment()` if running headless.

## Output contract
Same as master skill, but the cAlgo column is omitted from the input-mapping table.
