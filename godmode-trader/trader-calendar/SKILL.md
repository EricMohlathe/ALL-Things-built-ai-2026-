---
name: trader-calendar
description: >-
  Economic Calendar. Lists the week's data releases and central-bank events
  that move forex, gold, oil, stock indices and crypto (NFP, CPI, retail
  sales, PMIs, rate decisions, FOMC minutes, ECB and BoE speakers, oil
  inventories) with their impact, forecast and previous, in your time zone,
  filtered to the currencies your instruments move on. Says the next events
  for one instrument and whether you are inside a news blackout right now, and
  writes trader/calendar.json so trader-risk blocks new entries around
  High-impact releases. Use when the user says "what's on the calendar", "any
  news this week", "when is NFP", "is there CPI today", "what moves EURUSD
  today", "economic calendar", "is it safe to trade now", or at the start of
  the week and before /trader-entry.
argument-hint: "[week|next|blackout] [--symbol EURUSD] [--impact high] [--write]"
---

# trader-calendar

The Economic Calendar is the forex trader's earnings season, every week: the
scheduled moments when a number or a central banker can move a pair 50 pips
in a minute and jump any stop. This skill knows when they are, and makes sure
no new trade is opened right on top of one.

`${CLAUDE_SKILL_DIR}` below is this skill's folder. The tool is named
`econ.py` (a file named calendar.py would hide Python's own calendar module).

```bash
python3 "${CLAUDE_SKILL_DIR}/econ.py" week                         # this week, High + Medium, your currencies
python3 "${CLAUDE_SKILL_DIR}/econ.py" week --write                 # save trader/calendar.json for trader-risk
python3 "${CLAUDE_SKILL_DIR}/econ.py" week --impact high --currencies USD,EUR,GBP,JPY
python3 "${CLAUDE_SKILL_DIR}/econ.py" week --which both --write    # this week and next
python3 "${CLAUDE_SKILL_DIR}/econ.py" next --symbol XAUUSD --hours 48
python3 "${CLAUDE_SKILL_DIR}/econ.py" blackout --symbol EURUSD     # exit 1 inside a blackout
```

## Source

The free weekly export of the Forex Factory calendar
(`https://nfs.faireconomy.media/ff_calendar_thisweek.json` and
`_nextweek.json`): title, currency, time, impact (High, Medium, Low, Holiday),
forecast and previous. It is unofficial and asks to be polled gently, so the
answer is cached in `trader/state/calendar-cache.json` for an hour.

## The blackout

`news_blackout_minutes` (30) and `news_blackout_impact` (["High"]) in
trader/config.json: no new entries that many minutes before or after an event
of that impact for a currency the instrument moves on. trader-risk reads
trader/calendar.json and blocks inside the window; exits are never blocked.
`alerts.py add --event --currencies USD,EUR --minutes 15` rings before each one.

## Steps

1. On Sunday or Monday: `econ.py week --which both --write`. Tell the user the
   High-impact events of the week by day, in their time zone.
2. Each morning: `econ.py week --write` again (the cache keeps it gentle).
3. Before an entry: `econ.py next --symbol SYMBOL`. If an event is due within
   the blackout, say so: trader-risk will block a new entry until it passes.
4. For holidays (impact "Holiday"), say liquidity will be thin and spreads wide.

## Rules

- A calendar says WHEN, never which way. Do not predict the number or the move.
- Forecasts are consensus estimates, not facts. Say "forecast".
- Times can change and events can be added at short notice: say so on a
  central-bank day.

## Safety

- Education and tooling, not financial advice.
- Paper trading by default (`"paper": true`). Going live is the user's own decision, in their own config.
- Nothing in this pack places an order except trader-broker, and only with trader-risk's PASS and the
  user's explicit yes for that one order. This skill never places anything.
