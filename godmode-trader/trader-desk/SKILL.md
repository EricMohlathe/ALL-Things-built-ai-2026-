---
name: trader-desk
description: >-
  Trading Desk Brief. One page that puts every skill's latest output side by
  side for your markets: the session clock, the next High-impact releases
  for each market's currencies, the macro dollar compass and regime, COT
  crowding, the SMC / ICT structure read with timeframe alignment, nearest
  levels and the killzone, the setups with a tested record from the Setup
  Lab (corrected for how many tests were run), the prop-firm room and the
  largest safe risk, and your journal record and latest lessons. Ranks
  today's ideas by evidence: an idea needs a tested setup on that market;
  structure, macro and positioning only move it up or down, and everything
  else is watch only. Names every missing input instead of guessing. Use when
  the user says "morning brief", "what's on today", "desk", "game plan",
  "what should I watch", "best setups today", or to start a session.
argument-hint: "[brief] [SYMBOL ...] [--write]"
---

# trader-desk

The desk is the morning meeting: what is open, what is due, what the
backdrop says, and which ideas have evidence behind them. It reads what the
other skills saved; it calls nothing that can trade.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/desk.py" brief                                  # config "symbols", or the majors
python3 "${CLAUDE_SKILL_DIR}/desk.py" brief EURUSD GBPUSD XAUUSD US500 BTCUSD --write   # + trader/brief.md
python3 "${CLAUDE_SKILL_DIR}/desk.py" --yahoo brief XAUUSD                   # structure from live bars
python3 "${CLAUDE_SKILL_DIR}/desk.py" --offline tests/fixtures/charts --now "2026-11-16 07:00 London" brief
```

## Before the brief: refresh the inputs

```bash
python3 trader-calendar/econ.py week --write          # trader/calendar.json
python3 trader-macro/macro.py refresh                 # weekly is enough
python3 trader-cot/cot.py latest --write              # Fridays
python3 trader-data/data.py get EURUSD --from 2023-01-01   # history for the structure read and the lab
python3 trader-lab/lab.py rank EURUSD XAUUSD US500 --save  # what has a record
```

A part that is missing is listed under "Not included" with the command that
fills it.

## How ideas are ranked

1. **A tested setup first.** A market enters the idea list only when a setup
   has 30 or more backtested trades on it with a positive expectancy and a p
   under 0.10 after a Holm correction across every test saved in
   trader/lab/summary.json. The more you test, the stronger a result must be.
2. **Then the context.** Timeframe alignment and being inside a killzone raise
   the score; a dollar compass that agrees with a USD idea raises it, one that
   disagrees lowers it. COT crowding is shown, not scored.
3. Everything else is **watch only**, with its structure, nearest levels and
   the next High-impact release.

An idea is a setup worth watching for today, not an order. The trade still
goes `/trader-entry` (the trigger) -> `/trader-exit` (stop and target) ->
`/trader-timemachine` -> `/trader-budget` (and `/trader-propfirm check` on a
prop account) -> `/trader-risk` -> `/trader-broker`, and nothing is placed
without the user's explicit yes for that one order.

## Using the agents

With the pack installed as a plugin, the desk's specialists can run in
parallel: the smc-analyst on structure, the macro-analyst on the backdrop,
the quant-researcher on the lab, the risk-skeptic against every idea, and
the strategist to write the plan. See the `agents/` folder.

## Rules

- No tested setup, no idea. "Watch only" is a complete answer.
- Read the calendar line before every idea: a High-impact release inside the
  session changes the trade, and trader-risk blocks entries around it.
- The brief is written in the config's time zone; calendar times are UTC.

This is not financial advice. Nothing here can place an order.
