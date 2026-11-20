---
name: trader-propfirm
description: >-
  Prop Firm Guardian. Runs a funded-account challenge (FTMO 2-step by
  default, or a generic 2-step or 1-step trailing preset, every number
  overridable) as numbers before every trade: the daily floor from the day's
  starting balance in the firm's own time zone, the overall floor static or
  trailing, the room left in money and in losing trades, the largest risk
  per trade that survives a losing streak with a buffer, progress to the
  target and the minimum trading days. Checks every proposed order against
  today's room, and simulates thousands of challenges from a setup's real
  backtest or journal trades to give the pass probability at each risk size.
  Use when the user says "FTMO", "prop firm", "funded account", "challenge",
  "daily loss limit", "how much can I risk", "max drawdown rule", "will I
  pass", or before sizing a trade on a prop account.
argument-hint: "[rules|init|update|status|check|sim] [--size 100000] [--preset ftmo_2step]"
---

# trader-propfirm

A prop challenge is lost on the rules, not on the market: one bad day past
the daily limit ends it whatever the balance. This skill keeps those limits
in front of every decision.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/propfirm.py" rules                                   # FTMO 2-step as numbers
python3 "${CLAUDE_SKILL_DIR}/propfirm.py" rules --preset generic_1step --size 50000
python3 "${CLAUDE_SKILL_DIR}/propfirm.py" init --size 100000 --preset ftmo_2step  # start tracking
python3 "${CLAUDE_SKILL_DIR}/propfirm.py" update --balance 101250 --equity 100980 --traded
python3 "${CLAUDE_SKILL_DIR}/propfirm.py" status --risk 500                       # floors, room, safe risk
python3 "${CLAUDE_SKILL_DIR}/propfirm.py" check                                   # trader/orders.json vs the room
python3 "${CLAUDE_SKILL_DIR}/propfirm.py" sim --trades trader/lab/EURUSD/GM01-M5.json   # pass odds by risk
python3 "${CLAUDE_SKILL_DIR}/propfirm.py" sim --journal trader/journal.csv --phase 2
```

## The presets

| Preset | Targets | Daily loss | Maximum loss | Min days | Day resets |
|---|---|---|---|---|---|
| `ftmo_2step` | 10 %, then 5 % | 5 % of the initial balance, from each day's start | 10 %, static | 4 | midnight Prague |
| `generic_2step` | 8 %, then 5 % | 5 % | 10 %, static | 3 | midnight UTC |
| `generic_1step` | 10 % | 4 % | 6 %, trailing the peak | 3 | midnight UTC |

Override any of it in trader/config.json:

```json
"prop_firm": {"preset": "ftmo_2step", "daily_loss_pct": 5, "max_loss_pct": 10, "min_days": 4}
```

Firms change their terms and differ by account type (swing, aggressive,
news rules on funded accounts). Check the firm's current rules page before
you rely on any number here.

## How the guardian counts

- The **daily floor** is the day's starting balance minus the daily limit of
  the INITIAL balance. The first `update` of a new day (in the firm's zone)
  takes the last balance as the day's start.
- The **overall floor** is the initial balance minus the maximum loss, or, on
  a trailing rule, the highest balance minus it.
- The **room** is equity minus whichever floor is higher. The **largest safe
  risk** is the room, less a buffer (20 % by default), divided by the losing
  streak you want to survive (4 by default).
- `check` fails any order whose loss at the stop is over that, and every order
  once the room is gone. trader-risk still checks your own limits as well.

## The pass probability

`sim` resamples whole trading days of a setup's real trades (from
`/trader-lab run ... --save` or your journal) in their real order, and plays
the phase thousands of times at each risk size: pass, busted on the daily
limit, busted on the maximum loss, or out of time. Risk is fixed to the
initial balance, as the firms measure it. Backtest trades are the best case;
your journal's are the honest one.

## Rules

- Stop for the day when the status says NO ROOM. Do not trade to win it back.
- Size from the guardian, not from the target: the target is reached by
  surviving, and the daily limit is the rule that ends most challenges.
- Nothing here places an order. Every trade still goes through trader-risk
  and your explicit yes for that one order in /trader-broker.

This is not financial advice. A simulated pass rate is not a promise.
