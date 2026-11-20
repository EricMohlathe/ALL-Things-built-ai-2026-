# AGENTS.md

Rules for any AI coding agent working in this repository.

Read this file completely before writing any code. Keep it short: it is loaded
into context on every request, so detail lives in skills, not here.

---

## 1. What this repository is

A workspace for turning written trading strategy descriptions into MetaTrader 5
Expert Advisors in MQL5.

You write MQL5 code. You do not design trading strategies. If a strategy
description is ambiguous, ask instead of guessing.

## 2. Where the knowledge is

Skills are checked into `.agents/skills/`. Load the one you need; do not load
all of them by reflex.

| Skill | Load it when |
|---|---|
| `mql5-patterns` | Before writing any EA logic. Verified code for orders, lot sizing, indicators, broker detection, trailing stops, filters, restart safety |
| `mql5-compile-errors` | Whenever `compile.ps1` reports errors |
| `mql5-strategy-intake` | When the user describes a strategy, or a file in `strategies/` is incomplete |
| `mt5-backtest-report` | After a backtest, when explaining or judging the numbers |

## 3. Start from a template, never from an empty file

Both templates compile and both already contain risk sizing, broker detection
and the safety scaffolding. Pick one, copy it to `src/Experts/<name>.mq5`, and
fill in the marked STRATEGY section. Do not rewrite anything outside it unless
asked.

| Template | Use when the strategy |
|---|---|
| `templates/EA_Template.mq5` | Enters **at market** with a stop a fixed number of points away. Smaller, simpler. Fill in four boolean functions |
| `templates/EA_Template_Structural.mq5` | Places a **pending limit** at a price it computes, with a stop and target that come from structure. Fill in one function returning a `TradeSetup` |

If a strategy says "place a limit at the gap", "stop below the swing", "target
the previous high", or gives a minimum reward to risk, it is the structural one.

Writing an EA from scratch reintroduces every mistake the templates prevent.

## 4. Hard rules

### MQL5 only, never MQL4

The single most common failure. Every one of these is MQL4 and will not compile:

`OrderSend` with more than two parameters, `OrderSelect(index, SELECT_BY_POS, MODE_TRADES)`,
`OrderClose`, `OrderTicket`, `OrdersTotal` in its MT4 form, bare `Ask` / `Bid` /
`Bars` used as variables, `OP_BUY` and friends, `#property strict`, and any
indicator function used as if it returned a price.

In MQL5, indicator functions return a **handle**. Create it once in `OnInit`,
read values with `CopyBuffer`, release with `IndicatorRelease` in `OnDeinit`.

### Detect the broker, never assume it

Symbol names carry suffixes (`EURUSDm`, not `EURUSD`). Filling mode, lot step,
stops level and netting-versus-hedging all vary by broker. Read them at
runtime. The template already does.

### Check every trade result

Never fire an order and assume success. Check `retcode`.

### Never invent function names

If you are not certain a function exists, say so instead of writing it.
Compiling is the only way to find out, and each guess costs a full cycle.

### Edit files with your file editing tool, never through the shell

Do not use PowerShell `-replace`, `[regex]::Replace`, `sed` or any other shell
command to modify source files. Use your own read and edit tools.

This is not a style preference. Multi-line replacement strings in PowerShell
require several layers of quoting, and getting one layer wrong produces a parse
error rather than an edit. A single attempt to patch an EA this way burned
42,000 tokens across five failed commands and never modified the file.

Use the shell for what it is for: running `build.ps1`, `git`, and copying a
file. To start a new EA, copy the template as a whole file, then edit the copy
with your editing tool.

### No AVX-512

EX5 files compiled with AVX-512 do not run on the MetaQuotes VPS.

## 5. Workflow

One change at a time.

```powershell
.\scripts\compile.ps1  -File "src\Experts\<name>.mq5" -Json
.\scripts\backtest.ps1 -Expert "<name>.ex5" -Symbol <symbol> -From 2024.01.01 -To 2024.12.31 -Json
```

`compile.ps1` returns errors with line numbers, plus a `hints` field containing
the correct signature of any built-in you called wrongly. Read `hints` first.

Fix the earliest error, then recompile. Later errors are usually knock-on noise.

## 6. Record what you learn

**These steps are not optional.**

1. A compile error you have not seen before goes into
   `.agents/skills/mql5-compile-errors/references/errors.md`, with the original
   message, the cause and the fix.
2. A snippet that compiles and behaves correctly in the Strategy Tester goes
   into the matching file under `.agents/skills/mql5-patterns/references/`.

The value of this repository is that it gets better over time. Skipping this
means the next session repeats today's mistakes.

## 7. Never do

- Modify anything in `reports/` or `logs/`. Generated output.
- Commit `.ex5` files. Build artifacts.
- Commit anything in `config/` except the `.example.json` files. They contain
  account numbers and local paths.
- Change risk management logic unless explicitly asked. It is the safety layer.
- Deploy to a live account. Deployment is always a human decision.

## 8. Disclaimer

This repository produces trading software that operates on real money. Nothing
here is financial advice and no result is guaranteed. Every EA must be
backtested, run on a demo account, and approved by the account owner before it
touches a live account.
