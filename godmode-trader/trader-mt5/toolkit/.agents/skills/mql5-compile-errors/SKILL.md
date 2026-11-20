---
name: mql5-compile-errors
description: Diagnose and fix MetaEditor compile errors in MQL5. Use whenever scripts/compile.ps1 reports errors, when an error code like 256 or 199 appears, or before writing MQL5 that uses OrderSend, indicator functions, or position loops. Covers the MQL4-to-MQL5 mistakes that cause almost every failed compile. Do not use for runtime or backtest problems, only compile-time.
---

# MQL5 compile errors

Every error code and message here was produced by a real compile on MetaEditor
build 5836. Nothing is guessed.

## Read the log correctly first

`scripts/compile.ps1` already does this. If you read a `.log` yourself:

- It is **UTF-16 LE**. `Get-Content -Encoding Unicode`, not the default.
- The **exit code is inverted**. A clean compile returns 1, a failed one
  returns 0. Never branch on it. Parse the `Result: N errors, M warnings` line.

## The single most useful line in the log

When you call a built-in function with the wrong signature, MetaEditor prints
the correct one:

```
info    built-in: bool OrderSend(const MqlTradeRequest&,MqlTradeResult&)
info    built-in: int iMA(const string,ENUM_TIMEFRAMES,int,int,ENUM_MA_METHOD,int)
info    built-in: bool OrderSelect(ulong)
```

`compile.ps1` collects these into the `hints` field. **Read hints before
guessing.** They tell you the exact fix.

## Fix top down, one at a time

Five real mistakes produced **22 error lines**. Most were knock-on noise from
the first one. Fix the earliest error, recompile, and the tail usually vanishes.

Do not try to fix every reported line at once. It wastes model usage and edits
code that was never broken.

## Error codes seen in practice

| Code | Message | Real cause |
|---|---|---|
| 256 | `undeclared identifier 'X'` | Most common by far. MQL4-only names: `Ask`, `Bid`, `OP_BUY`, `SELECT_BY_POS`, `MODE_TRADES`, `OrderClose`, `OrderTicket`. Or an invented function name |
| 199 | `wrong parameters count` | MQL4 signature for `OrderSend`, `iMA`, `OrderSelect`. **The correct signature is in the next log line** |
| 106 | `file '...' not found` | Broken `#include`. Not a code problem, a configuration one. See below |
| 149 | `'X' - unexpected token` | Knock-on from 256 or 199 |
| 157 | `')' - expression expected` | Knock-on |
| 152 | `'X' - some operator expected` | Knock-on |
| 154 | `'X' - semicolon expected` | Usually a type that does not exist because an include failed |
| warning 95 | `expression has no effect` | Knock-on |

Full before-and-after fixes: `references/errors.md`.

## Error 106 is not your fault

```
error 106: file 'C:\Users\...\Terminal\<hash>\MQL5\Include\Trade\Trade.mqh' not found
```

MetaEditor resolves `#include <...>` against **its own** data folder, derived
from a hash of the executable path, not from where the source file lives.

Do not remove the include or rewrite it as a relative path. Fix the invocation:
pass `/include:"<path to the MQL5 folder>"`. This is already set in
`config/paths.json`. If you see error 106, that config is wrong or missing.

## Before you write, avoid the top five

1. `OrderSend` takes **two** parameters: a filled `MqlTradeRequest` and an
   `MqlTradeResult`. Or use `CTrade` from `<Trade\Trade.mqh>`.
2. `Ask` and `Bid` do not exist. Use
   `SymbolInfoDouble(_Symbol, SYMBOL_ASK)` and `SYMBOL_BID`.
3. `iMA` and every other indicator function return a **handle**, not a value.
   Create it once in `OnInit`, read with `CopyBuffer`, release in `OnDeinit`.
4. Positions are not orders. Use `PositionsTotal`, `PositionGetTicket`,
   `PositionGetInteger`. `OrderSelect` in MQL5 takes a single ticket.
5. If you are not certain a function exists, say so instead of writing it.
   Compiling is the only way to find out, and each guess costs a full cycle.

Verified working code for all of these: skill `mql5-patterns`.

## After a new error

Add it to `references/errors.md` with the original message, the cause and the
fix. This file is the reason the next session is faster than this one. Skipping
it means repeating today's mistakes tomorrow.
