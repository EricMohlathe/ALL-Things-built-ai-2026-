---
name: mql5-csharp-language-bridge
description: Bidirectional translator between MQL5 and C# (cAlgo / NinjaTrader 8). Use whenever the user asks to convert, port, mirror, or audit parity between an MT5 EA and a cTrader cBot. Triggers on "convert MQL5 to C#", "port MT5 EA to cTrader", "convert NT8 to cAlgo", "translate this MQL5 file", "make this work on cTrader too", "parity check between MT5 and cTrader".
---

# MQL5 ↔ C# (cAlgo / NT8) Language Bridge

This skill is the conversion engine. Where the master skill teaches the *concepts*, this skill teaches the *syntax mappings* and the porting workflow.

## Core lookup tables (load on demand)
Use the master skill's references — do not duplicate:
- `language_conversion_mql5_csharp.md` — MQL5 ↔ cAlgo idiom table.
- `nt8_to_ctrader_csharp.md` — NinjaTrader 8 → cAlgo C# (helps with order-flow code lifted from NT8 packages).
- `pinescript_to_mt5_ctrader.md` — when source is Pine instead of MT5.

## Conversion procedure
1. **Audit source.** Read the source file end-to-end. Tag every line that touches: bars/series, symbol, account, time, orders, indicators, drawing, DOM.
2. **Resolve persistent state.** Anything declared once and updated across bars (Pine `var`, MQL5 globals, cAlgo class fields) gets mapped to the equivalent persistence container in target.
3. **Resolve indexing direction.** Decide upfront: target uses MQL5-style (0 = newest) or cAlgo-style (Count−1 = newest). Convert at boundary.
4. **Resolve volume units.** lots vs units vs contracts. Pin at the order-call boundary.
5. **Resolve SL/TP semantics.** price (MQL5) vs pips (cAlgo). Convert at the order-call boundary.
6. **Resolve time semantics.** server-broker time (MQL5) vs UTC (cAlgo). Normalize to UTC inside logic.
7. **Emit target code.** Drop into the master skill's templates.
8. **Parity test.** Run both on the same window; trade-list diff ≤ 5%.

## Anti-patterns
- Translating line-by-line with a regex. Always preserve the *logical* meaning, not the literal characters.
- Forgetting indexing inversion → trades fire one bar early/late.
- Forgetting unit conversion → 100x lot-size errors.
- Forgetting timezone normalization → session filter fires at wrong hours.

## Output contract
Emit:
1. The translated source.
2. A 5-row diff table of "what changed and why" for the trickiest transforms.
3. A parity-test instruction block.
