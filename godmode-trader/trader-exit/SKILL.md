---
name: trader-exit
description: >-
  Exit Planner. Sets the stop and the target BEFORE you enter, long or short,
  on any forex pair, commodity, index or coin, so you know when to get out.
  Stops at the range midpoint or its far side, a price, a percent, a number of
  pips or points, or an ATR multiple, rounded to the instrument's own tick and
  AWAY from the entry (down for a long, up for a short). Targets in R
  multiples, pips or price. Refuses a stop on the wrong side, a target on the
  wrong side, or a stop so tight the spread would take it. Sets the flat-by
  time from the session's close. Writes trader/plan.json. Use when the user
  says "where's my stop", "set a stop and target", "exit plan", "how many pips
  am I risking", "plan the trade", "2R target", or right after /trader-entry
  triggers, before /trader-timemachine and /trader-budget.
argument-hint: "[--stop range-mid|range-far|pips:N|atr:K] [--target 2R|pips:N]"
---

# trader-exit

The Exit Planner decides how a trade ends before it begins: where you are
wrong (the stop), where you take the money (the target), and the time you are
out either way (flat by). It works for a long and for a short, and in the
instrument's own units: pips on EURUSD, pips of 0.1 on gold, points on the
S&P and bitcoin, ticks on oil. It never places an order.

`${CLAUDE_SKILL_DIR}` below is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/exit.py" plan                              # from trader/entry.json: range-mid stop, 2R
python3 "${CLAUDE_SKILL_DIR}/exit.py" plan --stop range-mid --target 2R --write
python3 "${CLAUDE_SKILL_DIR}/exit.py" plan --stop pips:15 --target pips:30
python3 "${CLAUDE_SKILL_DIR}/exit.py" plan --stop atr:1.5 --target 1.5R
python3 "${CLAUDE_SKILL_DIR}/exit.py" plan --symbol XAUUSD --side sell --entry 4053.20 \
    --range-high 4062.4 --range-low 4055.1 --session comex --date 2026-11-16 --time 08:50
python3 "${CLAUDE_SKILL_DIR}/exit.py" show
```

## The stops

| --stop | where | long | short |
| --- | --- | --- | --- |
| `range-mid` (default for a range entry) | the opening range's midpoint | under | over |
| `range-far` | the far side of the range | the low | the high |
| `pips:N` | N pips / points / ticks from the entry | under | over |
| `pct:X` | X percent from the entry | under | over |
| `atr:K` | K x the 14-bar ATR of the session up to the entry bar | under | over |
| `price:X` | your price | must be under | must be over |

Every stop is rounded to the instrument's tick, away from the entry. Targets:
`2R` (default), `1R`, `1.5R` ..., `pips:N`, `price:X`, rounded to the nearest tick.

## What it refuses

- A stop on the wrong side of the entry, or a target on the wrong side.
- A stop closer than the larger of 3 typical spreads and 0.03 % of the price:
  the spread and normal wiggle would take it.
- An entry.json that has not triggered (give `--entry` and `--side` to plan ahead).
- A flat-by at or before the entry time, or after the session's close.

It warns (and trader-risk enforces): a reward:risk under `min_reward_risk`, a
spread bigger than a quarter of the risk, a Friday forex or commodity trade
(a Monday gap can jump a stop), a plan for another day.

## Steps

1. After `/trader-entry` triggers, run `exit.py plan` (it reads trader/entry.json).
2. Say the plan in plain words: entry, stop and why, target and its R, the risk
   in pips or points, and the flat-by time with its time zone.
3. If the user wants a different stop or target, rerun with the flag. Never
   widen a stop after the entry.
4. `exit.py plan --write`, then `/trader-timemachine` to replay it and
   `/trader-budget` to size it.

## Example (test fixture, synthetic bars)

```
Exit plan: EURUSD long, Mon 2026-11-16, London session range breakout on 5-minute bars
  Entry         1.16285 at 08:45 London (bar 8)
  Stop          1.16160  range midpoint: (1.16240 + 1.16080) / 2 = 1.1616
  Target        1.16535  2R (two times the risk)
  Risk a unit   0.00125 = 12.5 pips (0.107% of the entry)
  Reward:risk   2.0
  Flat by       16:55 London, win or lose: no overnight or weekend hold
```

The gold short from the same morning: entry 4053.20, stop 4058.75 (the range
midpoint, above the entry), target 4042.10 (2R below), risk 55.5 pips.

## Safety

- Education and tooling, not financial advice. A plan is arithmetic, not a recommendation.
- A stop is a plan, not a guarantee: a gap, a weekend open or a fast market can fill past it.
- Paper trading by default (`"paper": true`). Going live is the user's own decision, in their own config.
- Nothing in this pack places an order except trader-broker, and only when all three hold: trader-risk
  passed that exact order today, the user typed an explicit yes for that one order in the chat, and the
  user clicked Allow once on Claude's own card where a connector places it. Never set an order tool to
  "Always allow".
- Leveraged products (forex, CFDs, futures) can lose money fast; most retail CFD accounts lose money.
