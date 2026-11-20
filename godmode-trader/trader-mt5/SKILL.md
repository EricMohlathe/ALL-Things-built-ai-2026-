---
name: trader-mt5
description: >-
  MetaTrader 5 Bridge and EA Workshop. Reads a running MetaTrader 5 terminal
  (account, balance, equity, margin, open positions, pending orders), lists
  the broker's symbol names and contract sizes for the config, exports the
  broker's own bars and ticks into the trader-data cache with server time
  converted to UTC, and sends ONE order that trader-risk passed and you
  approved today, as a dry run with MetaTrader's order_check unless you add
  --live. Bundles the MT5 Agent Toolkit (MIT): verified MQL5 patterns, the
  compile-error reference, strategy intake, the backtest-report guide, EA
  templates and the PowerShell compile and Strategy Tester scripts, to build,
  compile and test the GODMODE Expert Advisors. Use when the user says "MT5",
  "MetaTrader", "Expert Advisor", "EA", "MQL5", "compile", "strategy
  tester", "export my MT5 history", or "send it to MT5".
argument-hint: "[status|symbols|export|ticks|send --index N] [--live]"
---

# trader-mt5

Two jobs: connect the pack to a MetaTrader 5 terminal, and build Expert
Advisors that compile the first time.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

## The bridge (Windows, MetaTrader 5 running, `pip install MetaTrader5`)

```bash
python3 "${CLAUDE_SKILL_DIR}/bridge.py" status                          # account, positions, pending orders
python3 "${CLAUDE_SKILL_DIR}/bridge.py" symbols --match XAU             # broker names and contract sizes
python3 "${CLAUDE_SKILL_DIR}/bridge.py" export EURUSD --tf M15 --from 2024-01-01   # broker bars -> trader/data
python3 "${CLAUDE_SKILL_DIR}/bridge.py" ticks EURUSD --from 2026-11-16 --hours 2   # ticks -> M1 + delta, spread
python3 "${CLAUDE_SKILL_DIR}/bridge.py" send --index 1                  # dry run + order_check
python3 "${CLAUDE_SKILL_DIR}/bridge.py" send --index 1 --live           # only when every gate is open
```

Bar times from MetaTrader are the broker's server time. `--server-tz MT5`
(the default) is the common "New York close" server clock, UTC+2 in winter
and UTC+3 in summer on the US dates; pass the server's IANA zone otherwise.

## The gates on `send --live`

Every one, every time, or nothing is sent and the output names the gate:

1. `"broker": "mt5"` in trader/config.json;
2. trader-risk PASSED this exact order today (same fingerprint);
3. the user gave an explicit yes for that one order in the chat today,
   recorded by `ticket.py approve`, and it has not been sent, declined or
   reported since;
4. `"paper": false`, or the terminal is logged in to a DEMO account
   (paper trading by default: a real-money account stays untouched while
   paper is on);
5. MetaTrader's own `order_check` accepts the request.

The result is written to trader/state/broker.json, so the same approval can
never send twice. Then set the alerts (`/trader-alerts add --from-plan`).
Claude never adds `--live` on its own: only after the user has said yes to
that one order, in this conversation, after seeing the ticket.

## The EA workshop (the bundled toolkit)

`toolkit/` is the MT5 Agent Toolkit by Giang Vuong Hoang (MIT, see
`toolkit/LICENSE` and `toolkit/NOTICE.md`), unchanged. Copy it to the Windows
machine, run `scripts/setup.ps1`, then:

| Job | Read first |
|---|---|
| Turn a described strategy into a full spec before any code | `toolkit/.agents/skills/mql5-strategy-intake/SKILL.md` |
| Write EA logic: orders, sizing, positions, indicators, new bar, restart-safe state | `toolkit/.agents/skills/mql5-patterns/SKILL.md` and its `references/` |
| Fix a failed compile (error codes like 256, 199) | `toolkit/.agents/skills/mql5-compile-errors/SKILL.md` |
| Judge a Strategy Tester report and its traps | `toolkit/.agents/skills/mt5-backtest-report/SKILL.md` |
| Start a new EA | `toolkit/templates/EA_Template.mq5` or `EA_Template_Structural.mq5` |
| Compile, backtest, both | `toolkit/scripts/compile.ps1`, `backtest.ps1`, `build.ps1` |

The GODMODE EAs live in `MT5_MasterLibrary/Experts/GODMODE/` of the parent
repository (GM01 to GM26, one per setup). Prove a setup in `/trader-lab`
first, then run its EA in the Strategy Tester on "Every tick based on real
ticks" with your broker's spread and commission, then on a demo account.

## Rules

- The bridge is for one approved order at a time. It does not run strategies,
  loop, or trade on a signal.
- Real-money accounts need `"paper": false` and the same explicit yes for
  that one order as every other broker in the pack.
- Read `/trader-mt5 status` after any send: what MetaTrader shows is the truth.

This is not financial advice. Leveraged trading can lose more than you expect.
