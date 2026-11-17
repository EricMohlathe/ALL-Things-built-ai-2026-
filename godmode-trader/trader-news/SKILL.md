---
name: trader-news
description: >-
  News Monitor. Tracks breaking headlines for every forex pair, commodity,
  index and coin you watch, tags each one with what moves these markets
  (central banks and rate decisions, inflation, jobs, growth, yields,
  intervention, OPEC and inventories, metals and ETF flows, geopolitics,
  crypto ETF flows, hacks and exploits, regulation, risk mood), lists the
  calendar events due for each instrument's currencies, and shows how far it
  has moved on the day in pips or points. Only what is new since the last
  check. Use when the user says "any news on EURUSD", "what's moving gold",
  "why is bitcoin down", "check the headlines", "news on my positions", or
  after /trader-scanner and before /trader-entry.
argument-hint: "[--symbols EURUSD XAUUSD BTCUSD] [--hours 24] [--all]"
---

# trader-news

The News Monitor reads the headlines so the user does not trade blind into a
central banker, a data release or an exchange hack. It shows each headline
once, newest first, tagged, next to the instrument's move on the day and its
calendar events.

`${CLAUDE_SKILL_DIR}` below is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/news.py"                                # your watchlist, plan and positions
python3 "${CLAUDE_SKILL_DIR}/news.py" --symbols EURUSD XAUUSD BTCUSD
python3 "${CLAUDE_SKILL_DIR}/news.py" --symbols USDJPY --all --hours 72
python3 "${CLAUDE_SKILL_DIR}/news.py" --no-calendar --no-moves
```

## Sources

| source | what |
| --- | --- |
| Yahoo Finance headline RSS | per instrument feed (EURUSD=X, GC=F, ^GSPC, BTC-USD) |
| `trader/calendar.json` | High and Medium events for the instrument's currencies (run `/trader-calendar` first) |
| Yahoo chart | the last price against the previous close |
| `trader/state/news.json` | what you have already seen (30 days), so each item shows once |

Which currencies an instrument moves on: a pair its two (EURUSD: EUR and USD);
gold, oil, US indices and crypto USD; the DAX and CAC EUR; the FTSE GBP; the
Nikkei JPY; the Hang Seng HKD and CNY; the ASX AUD.

## Steps

1. `news.py` (or `--symbols ...`). Lead with anything tagged central bank,
   inflation, jobs, intervention, OPEC, crypto risk or regulation, and with a
   High-impact calendar event in the next hours.
2. Say each in one line: the time in the user's zone, the headline, the tag.
   Then the move on the day in pips or points.
3. If a High-impact event is due within the hour, say that trader-risk will
   block new entries around it (the news blackout).
4. Then `/trader-entry SYMBOL`, or nothing: a quiet tape is also an answer.

## Rules

- Headlines are leads, not facts: say "the headline says", and open the story
  before acting on it.
- Never infer a direction from a headline alone. The same CPI print can move
  EURUSD either way depending on what was expected.
- Free feeds can lag minutes behind the wire services.

## Safety

- Education and tooling, not financial advice. Nothing here is a reason to trade on its own.
- Paper trading by default (`"paper": true`). Going live is the user's own decision, in their own config.
- Nothing in this pack places an order except trader-broker, and only with trader-risk's PASS and the
  user's explicit yes for that one order. This skill never places anything.
