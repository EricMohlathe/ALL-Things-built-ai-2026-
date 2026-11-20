<div align="center">

# MT5 Agent Toolkit

**Turn a written trading strategy into a MetaTrader 5 Expert Advisor, using an AI coding agent.**

Headless MQL5 compile, headless Strategy Tester, and a knowledge base that stops
the agent writing MQL4 by mistake.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D6.svg)](#requirements)
[![MetaTrader 5](https://img.shields.io/badge/MetaTrader%205-build%205836%20%7C%206140-orange.svg)](#requirements)
[![PowerShell](https://img.shields.io/badge/PowerShell-5.1%2B-5391FE.svg)](#requirements)
[![Agents](https://img.shields.io/badge/agents-Claude%20Code%20%7C%20Codex-8A2BE2.svg)](#which-ai-agents-work-with-this)

</div>

---

You describe a strategy in plain language. The agent writes the MQL5, compiles
it, reads its own compiler errors, fixes them, runs a backtest, and reports the
numbers. You read the numbers and decide.

You do not need to know MQL5.

```powershell
.\scripts\compile.ps1  -File "src\Experts\MyEA.mq5" -Json
.\scripts\backtest.ps1 -Expert "MyEA.ex5" -Symbol EURUSD -From 2024.01.01 -To 2024.12.31 -Json
```

Both return JSON. That is the whole interface an agent needs.

## Contents

- [Why this exists](#why-this-exists)
- [The nine silent failures](#the-nine-silent-failures-of-the-mt5-command-line)
- [Quick start](#quick-start)
- [What is inside](#what-is-inside)
- [How the loop works](#how-the-loop-works)
- [FAQ](#faq)
- [Requirements](#requirements)
- [Limits](#limits)
- [Contributing](#contributing)
- [Disclaimer](#disclaimer)

## Why this exists

Two problems. The second is the expensive one.

**MQL5 is a niche language and language models write MQL4 by mistake.** They
reach for `OrderSend` with eight parameters, `OrderSelect`, `OrderClose`,
`OP_BUY`, bare `Ask` and `Bid`, `#property strict`. None of it compiles against
MetaTrader 5. Without grounding, you watch an agent rediscover the same errors
for an hour and conclude the tool is useless.

**MetaTrader's command line does not fail loudly. It fails silently.** Nearly
every way to drive MetaEditor and the Strategy Tester headlessly has a failure
mode that returns exit code zero and produces output that looks correct.

This repository is the grounding, plus a workaround for each of those failures,
plus the two commands above.

## The nine silent failures of the MT5 command line

Every one was found by experiment on MetaTrader 5 build 5836, not by reading
documentation. Every one returns exit code zero.

| # | What actually happens | What you observe |
|---|---|---|
| 0 | MetaTrader is already running when you launch a test | Windows hands `/config:` to the running instance, which ignores it. Exit 0, no report, **not one line in any log** |
| 1 | Another program holds TCP port 3000 | Tester agent connects to the stranger, is refused, abandons the run after 1 ms |
| 2 | Report path given as an absolute path | Silently ignored. It must be relative to the terminal data folder |
| 3 | `.ini` written with PowerShell `Set-Content -Encoding utf8` | The BOM corrupts `[Common]`, and MT5 reports *tester not started because the account is not specified* |
| 4 | `terminal64.exe` is a GUI application | Returns immediately unless you wait on the process |
| 5 | Report and logs are UTF-16 LE | Read as UTF-8 and you get mojibake |
| 6 | No account is logged in | Tester refuses to start even with complete local history |
| 7 | EA inputs cannot be passed on the command line | They require a `.set` file named by `Tester/ExpertParameters` |
| 8 | **No `.set` file passed** | **The tester ignores your compiled defaults and silently reuses the previous run's inputs** |
| 9 | The terminal outlives the process you waited on | Report written, then about 75 seconds of profile reload before it truly exits, which breaks the *next* run |

MetaEditor has its own. The most important: **its exit code is inverted.** A
clean compile returns 1 and a compile with 22 errors returns 0.

### Number 8 deserves its own paragraph

MetaTrader saves the inputs from every test into
`MQL5\Profiles\Tester\<ExpertName>.set` and silently reuses that file when a run
does not name a parameter file.

Change a default in your source. Recompile. Test again. You get the **old**
numbers, with a freshly built `.ex5` sitting on disk and no warning anywhere.

Measured here: **the same binary produced 8 trades with no set file and 26 with
one.** The only difference was a set file naming one unrelated input.

Without a fix for this, the edit, compile, test loop is fiction. You can ship an
Expert Advisor to a live account having never once tested the code you believe
you tested. `scripts/backtest.ps1` therefore writes a set file on every run.

## Quick start

```powershell
git clone https://github.com/smizxe/mt5-agent-toolkit.git
cd mt5-agent-toolkit
.\scripts\setup.ps1
```

`setup.ps1` scans `%APPDATA%\MetaQuotes\Terminal` for your data folder, reads the
install path, detects the logged-in account, and writes `config\paths.json`.
Full walkthrough in [SETUP.md](SETUP.md), about 30 minutes on a new machine.

Then open your agent in this folder and describe what you want:

> An EA for EURUSD on H1. Buy when RSI crosses up through 30, sell when it
> crosses down through 70. Stop loss 300 points, take profit 600 points, risk
> 1% per trade, one position at a time.

The agent asks about anything you left out, writes the specification into
`strategies/`, copies a template, fills in the strategy section, compiles, fixes
its own errors, and backtests. One command does build and test together:

```powershell
.\scripts\build.ps1 -File "src\Experts\MyEA.mq5" -Symbol EURUSD -Period H1 -From 2024.01.01 -To 2024.12.31
```

Real output from the `RsiReversal` example that ships in this repository:

```
BUILD OK
  EURUSDm H1  2024.01.01 to 2024.06.30
  history quality 100%   57 trades   1563.31 net profit
  profit factor 1.45   recovery 2.1   max equity drawdown 744.86 (6.80%)
```

With `-Json` you also get win rate, wins and losses, average win, average loss,
payoff ratio, largest win, largest loss and the longest losing streak. Win rate
alone is the most misleading number in a backtest report; paired with the payoff
ratio it becomes usable.

Change a parameter without touching the source:

```powershell
.\scripts\backtest.ps1 -Expert "MyEA.ex5" -Symbol EURUSD -Period H1 -From 2024.01.01 -To 2024.12.31 -Inputs @{ InpRiskPercent = 0.5 }
```

## What is inside

```
.agents/skills/     knowledge the agent reads before writing code
scripts/            compile, backtest, build, setup
templates/          two EA starting points, both compile and trade as shipped
src/Experts/        worked examples
strategies/         one specification per EA, written before the code
```

### Skills

Loaded on demand rather than all at once, so a large knowledge base does not
cost tokens on every request. The directory name follows the Codex convention,
but the files are plain Markdown and work with any agent.

| Skill | Covers |
|---|---|
| `mql5-patterns` | Verified MQL5 for orders, lot sizing, indicator handles, broker detection, restart-safe state, risk rails, and debugging an EA that never trades |
| `mql5-compile-errors` | A growing table of real compiler errors with cause and fix |
| `mql5-strategy-intake` | Forces a vague strategy description to become precise before any code is written |
| `mt5-backtest-report` | How to read a report without fooling yourself, and what to check when there is no report |

### Templates

`EA_Template.mq5` for market entries with a fixed stop distance.
`EA_Template_Structural.mq5` for pending limit orders whose entry, stop and
target are computed from market structure.

Both ship with risk sizing derived from the real stop distance, broker
capability detection, filling mode negotiation, price normalisation to tick
size, and state rebuilt from the account so the EA survives a terminal restart.

The structural template also caps position size against free margin, and that is
not decoration. Lot size is risk divided by stop distance, so a stop that comes
out far smaller than intended does not produce a small loss, it produces an
enormous position. A real bug caught here computed a stop of 0.4 pip and asked
for **6.24 lots on a 10,000 account nominally risking 0.25%**, and the
percentage was obeyed exactly. Percent-of-balance sizing cannot catch that
alone.

## How the loop works

```
describe strategy  ->  agent writes MQL5  ->  compile
                                                |
                        error? -> recorded in the compile-errors skill
                                                |
                       compiles -> backtest -> report -> demo -> your decision
```

A compile error met once is written down, so the next session does not meet it
again. A snippet that compiles and behaves correctly becomes a pattern. The
repository is designed to get better with use.

`compile.ps1` returns a `hints` field carrying the correct signature of any
built-in the agent called wrongly, which is usually enough to fix an error in
one pass instead of three.

## FAQ

### Why does MetaEditor return exit code 1 when compilation succeeded?

Because its exit code is inverted. A clean compile returns 1 and a compile with
22 errors returns 0. Reproduced twice on build 5836. Never branch on MetaEditor's
exit code. Parse the `Result: N errors, M warnings` line from the log instead and
cross-check that the `.ex5` exists. `scripts/compile.ps1` does both.

### Why does my MT5 command line backtest produce no report?

Usually one of four things, in order of likelihood: MetaTrader is already
running, the report path was absolute rather than relative, another program holds
TCP port 3000, or the symbol name is wrong. All four exit with code 0, and the
first leaves no trace in any log at all. See
[the table above](#the-nine-silent-failures-of-the-mt5-command-line).

### Why does the Strategy Tester ignore the input defaults I compiled?

Because MetaTrader reuses `MQL5\Profiles\Tester\<ExpertName>.set` from your
previous run whenever `Tester/ExpertParameters` is absent from the `.ini`. Pass a
`.set` file on every run, even one containing nothing but a comment, and the
compiled defaults are used. Failure number 8 above.

### Why does the tester say the account is not specified?

Either no account is logged into the terminal, or your `.ini` has a UTF-8 BOM.
PowerShell 5.1's `Set-Content -Encoding utf8` writes one, and it corrupts the
`[Common]` section header so MT5 cannot find the login. Write the file with
`UTF8Encoding($false)` instead.

### Why does my EA never trade in the backtest?

Zero trades and zero orders are different problems. In MetaTrader a *trade* is a
position that opened; a pending order that was placed and expired unfilled counts
as nothing at all. Count orders in the log separately before touching entry
logic. Then instrument each condition with a counter and print the tally on
deinit, so the run tells you which filter refused rather than leaving you to
guess. See `.agents/skills/mql5-patterns/references/diagnosing-no-trades.md`.

### Why does the tester say my symbol does not exist?

Brokers add suffixes. Exness uses `EURUSDm`, not `EURUSD`. A wrong name does not
warn, it aborts the whole run. Read the exact name from Market Watch.

### Can I run this on macOS?

No. MetaEditor and the Strategy Tester agent are Windows only. MetaTrader on a
Mac runs under Wine, and the tester agent does not run there at all. The agent
writing the code can run anywhere; the compile and the backtest cannot.

### Which AI agents work with this?

Any agent that can read files and run PowerShell. Tested with Claude Code and
Codex CLI. `AGENTS.md` and `CLAUDE.md` point at the same rules, so the repository
is not tied to one vendor.

### Do I need to know MQL5?

No. You need to know your strategy precisely enough to answer questions about it.
The intake skill exists to drag those answers out of you before code is written,
because a guessed entry condition produces an EA that trades real money on
something you never asked for.

### Does this design trading strategies?

No, and the agent is instructed not to try. It converts a strategy you already
have into code, tests it, and reports honestly. Whether the strategy is any good
is your decision and nobody else's.

## Requirements

- Windows 10 or 11
- MetaTrader 5, with an account logged in at least once
- PowerShell 5.1 or later
- Git
- An AI coding agent, optional but the point of the whole thing

Traps reproduced on build **5836**. The compile path re-verified on build
**6140**. Other builds are untested, and a build that fixes one of these traps
will not announce it.

## Limits

- Windows only, for the reason given above.
- If something on your machine keeps MetaTrader running in the background, a
  headless backtest cannot start at all. That is failure number 0.
- The MetaTrader economic calendar returns nothing inside the Strategy Tester, so
  a news filter cannot be backtested honestly. There is no fake one here.
- The agent writes code. It does not design strategies and should not be asked
  to. If a description is ambiguous it is supposed to ask you, not guess.

## Contributing

The most useful contribution is a real compile error or a verified pattern.

- **A compile error** goes in
  `.agents/skills/mql5-compile-errors/references/errors.md` with the original
  message, the cause, and the fix.
- **A pattern** goes in the matching file under
  `.agents/skills/mql5-patterns/references/`, and must have compiled with zero
  errors before it is added.
- **A new MT5 command line trap** is the most valuable of all. Include what you
  observed, what the exit code was, and what the logs said.

Please do not submit strategies or performance claims. This repository is
infrastructure, deliberately.

## Disclaimer

This software builds programs that can place orders with real money.

Nothing here is financial advice, an investment recommendation, or a claim that
any strategy is profitable. Backtest results describe the past and predict
nothing. Every Expert Advisor produced with these tools must be backtested, run
on a demo account, and approved by the account owner before it goes anywhere near
a funded account.

You are responsible for every order your software sends.

## License

[MIT](LICENSE).

## Contact

Built by [@smizxe](https://github.com/smizxe). Questions, bug reports and new
traps are welcome as
[issues](https://github.com/smizxe/mt5-agent-toolkit/issues).

Available for work on MetaTrader 5 automation, MQL5 development, and setting this
pipeline up on your own machine and broker: **yangaidev@gmail.com**
