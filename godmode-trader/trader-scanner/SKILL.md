---
name: trader-scanner
description: >-
  Chart Scanner. Scans forex pairs, metals, energy, stock indices and crypto
  for setups, long and short. Daily mode reads closes and flags 20-day
  breakouts and breakdowns, bull and bear flags, 20-day average reclaims and
  losses, overbought and oversold RSI, fades and bounces, and volatility
  squeezes, every threshold scaled to each instrument's own volatility.
  Range mode finds session-range breakouts so far today, each instrument in
  its own session: London for forex, COMEX for gold, NYMEX for oil, the US
  cash session for the S&P, Xetra for the DAX, the UTC day for bitcoin.
  Writes trader/watchlist.json. Use when the user says "scan the market",
  "what's breaking out", "find me a setup", "scan forex", "scan gold and
  oil", "scan crypto", "London breakout", "what moved at the open", or to
  start a trading day.
argument-hint: "[daily|range] [--class forex,commodity,index,crypto] [--session london]"
---

# trader-scanner

The Chart Scanner reads charts so you do not have to. It looks at the whole
registry (forex majors, crosses and exotics, metals and energy, cash indices,
crypto; CME futures with `--futures`) and returns only the charts where a rule
fired. A scan is a list of charts that match a rule, not a list of trades.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/scan.py" universe                       # the registry -> trader/universe.txt
python3 "${CLAUDE_SKILL_DIR}/scan.py" daily                          # daily setups, every class
python3 "${CLAUDE_SKILL_DIR}/scan.py" daily --class forex,commodity  # or --symbols EURUSD,XAUUSD,BTCUSD
python3 "${CLAUDE_SKILL_DIR}/scan.py" range                          # range breakouts so far, both sides
python3 "${CLAUDE_SKILL_DIR}/scan.py" range --class forex --session london
python3 "${CLAUDE_SKILL_DIR}/scan.py" range --side sell              # shorts only
```

Other flags: `--futures` (add ES, NQ, GC, CL, 6E ...), `--limit N`, `--json`,
`--no-write`, `--offline PATH` (saved charts), `--now "2026-11-16 09:00 London"`.

## The two modes

**daily** reads six months of daily closes (Yahoo spark, 20 symbols a
request) and drops today's bar until its session closes. Each threshold is in
the instrument's own sigma (the standard deviation of its daily returns), so
the same rule fits EURUSD at 0.4 % a day and SOLUSD at 4 %:

| setup | rule | bias |
| --- | --- | --- |
| breakout_20d / breakdown_20d | the last close beyond every close of the 20 before | long / short |
| bull_flag / bear_flag | a 10-session run of 2 sigma or more, then 5 tight closes | long / short |
| reclaim_ma20 / lose_ma20 | crossed back over the 20-day average | long / short |
| oversold / overbought | RSI 14 (Wilder) under 30 / over 70 | long / short |
| oversold_bounce / overbought_fade | that yesterday, and today turned | long / short |
| squeeze | 20-day Bollinger width within 10 % of its 60-day low | neutral |

**range** runs the Entry Timer's exact rule on every instrument: the first
completed 5-minute bar after the session's opening range that CLOSED above its
high (long) or below its low (short), inside the entry window. Each instrument
uses its own session unless you pass `--session`.

| class | default session | range |
| --- | --- | --- |
| forex | London 08:00-17:00 London | 30 min |
| gold, silver, platinum | COMEX 08:20-13:30 New York | 15 min |
| oil, gas | NYMEX 09:00-14:30 New York | 15 min |
| US indices | US cash 09:30-16:00 New York | 15 min |
| DAX, Euro Stoxx / FTSE / CAC | Xetra / LSE / Euronext | 15 min |
| Nikkei / Hang Seng / ASX | TSE / HKEX / ASX (lunch breaks handled) | 15 min |
| crypto | the UTC day 00:00-24:00 | 60 min |

`python3 trader-core/tradercore.py sessions` lists them all, including Tokyo,
Sydney, New York and the Asian range (`asia_london`: the 00:00-07:00 London
range, broken after London opens).

## Steps

1. Before the sessions open: `scan.py daily`. Say how many charts were
   scanned, how many matched, and the top few with their bias and setups.
2. After an opening range is set: `scan.py range`. Say which instruments broke
   out, which way, at what time and price, and which sessions are not open yet.
3. Hand the user one chart at a time: `/trader-news SYMBOL` and
   `/trader-calendar` (a data release can swamp any setup), then
   `/trader-entry SYMBOL`.

## Rules

- A hit is a chart that matched a rule. Never call it a buy or a sell.
- Forex feeds carry no volume (it is an over-the-counter market): volume is
  never used to rank or filter forex.
- Yahoo's feeds are free, unofficial and can lag. Say so when a minute matters.
- Gold and silver come from the COMEX futures feed (GC=F, SI=F) and US indices
  from the cash index: your broker's CFD price can sit a little away from them.
  The plans work in distances (pips, points), so the size and risk carry over.

## Safety

- Education and tooling, not financial advice. A scan hit is a rules match, not a recommendation.
- Paper trading by default (`"paper": true`). Going live is the user's own decision, in their own config.
- Nothing in this pack places an order except trader-broker, and only when all three hold: trader-risk
  passed that exact order today, the user typed an explicit yes for that one order in the chat, and the
  user clicked Allow once on Claude's own card where a connector places it. Never set an order tool to
  "Always allow". This skill never places anything.
- Leveraged products (forex, CFDs, futures) can lose money fast; most retail CFD accounts lose money.
