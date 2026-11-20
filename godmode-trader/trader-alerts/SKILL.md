---
name: trader-alerts
description: >-
  Price Alerts and the world market clock. Shows which sessions are open right
  now (Sydney, Tokyo, London, New York, the exchanges, the FX week, crypto),
  the London and New York overlap, and what opens or closes next in each
  market's own time. Quotes any forex pair, commodity, index or coin into
  trader/prices.json, with the FX rates needed to convert them. Rings when a
  price crosses a level, a stop or a target (long or short), a move passes a
  percent, a session opens, the flat-by time arrives, or a High-impact data
  release is minutes away. Use when the user says "alert me", "tell me if gold
  hits", "is London open", "what's open now", "market hours", "set my stop
  alert", "remind me to close by", "warn me before NFP", or after a trade is
  placed.
argument-hint: "[clock|quote|add|check|list|reset]"
---

# trader-alerts

Alerts watch so the user does not have to stare at a chart. The clock says
which markets are trading right now, in their own time zones, across both DST
changes. Nothing here places an order.

`${CLAUDE_SKILL_DIR}` below is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/alerts.py" clock                               # what is open, what opens next
python3 "${CLAUDE_SKILL_DIR}/alerts.py" quote EURUSD XAUUSD --write         # -> trader/prices.json
python3 "${CLAUDE_SKILL_DIR}/alerts.py" quote --holdings --rates --write    # plan + positions + conversion pairs
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --from-plan                     # stop, target, flat-by (long or short)
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --symbol XAUUSD --below 4040 --rearm
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --symbol BTCUSD --pct 3
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --session-open london
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --at 16:55 --tz London --label "flat by"
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --event --currencies USD,EUR --minutes 15
python3 "${CLAUDE_SKILL_DIR}/alerts.py" check                               # rings what hit, once
python3 "${CLAUDE_SKILL_DIR}/alerts.py" list
python3 "${CLAUDE_SKILL_DIR}/alerts.py" reset eurusd-plan-stop
```

## Rule types

| type | rings when |
| --- | --- |
| `above` / `below` | the price is at or above / at or below `price`. From a plan, a long's stop is `below` and its target `above`; a short's are the other way round |
| `pct_move` | the price moved `pct` percent from the previous close (`direction` up or down optional), once a day |
| `session_open` | the named session opened, once per session day |
| `time` | the clock passed `at` in `tz`, once a day (a rule with `date` only that day) |
| `event` | a High-impact (or chosen) calendar event for `currencies` is `minutes` away or less, once per event |

A price alert rings once, then stays quiet until reset, unless it has
`"rearm": true` (it re-arms when the price crosses back).

## Steps

1. After a fill: `alerts.py add --from-plan`. Say the three alerts in plain
   words, with the stop on the right side for a long or a short.
2. Run `alerts.py check` on a `/loop` every 1 to 5 minutes while the trade is
   open. Exit 0 means something rang: tell the user what and when.
3. When the flat-by alert rings, go to `/trader-broker` (`ticket.py flatten`).
4. Before sizing a trade quoted in another currency (DAX, FTSE, Nikkei, a
   cross), run `alerts.py quote --holdings --rates --write` so trader-budget
   and trader-risk can convert.

## Rules

- Quotes are free and delayed (Yahoo, unofficial). They are for alerts and for
  sizing checks, never for timing an order: the broker's price is the price.
- An alert is a nudge, not an order. A stop alert does not close anything; the
  broker's stop-loss order does.

## Safety

- Education and tooling, not financial advice.
- Paper trading by default (`"paper": true`). Going live is the user's own decision, in their own config.
- Nothing in this pack places an order except trader-broker, and only when all three hold: trader-risk
  passed that exact order today, the user typed an explicit yes for that one order in the chat, and the
  user clicked Allow once on Claude's own card where a connector places it. Never set an order tool to
  "Always allow". An alert never runs trader-broker on its own: nobody is there to say yes.
