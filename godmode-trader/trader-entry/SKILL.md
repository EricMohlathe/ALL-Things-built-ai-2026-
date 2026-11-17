---
name: trader-entry
description: >-
  Entry Timer. Watches a setup bar by bar on any forex pair, commodity, index
  or coin and tells you the moment to get in, long or short. Builds the
  session's opening range in the session's own time zone (the London 30
  minutes for EURUSD, the COMEX 15 minutes for gold, the US cash 15 minutes for
  the S&P, the first UTC hour for bitcoin) and calls the entry on the first
  completed bar that CLOSES above the range high (long) or below the range low
  (short), or beyond a level you give it. Says waiting and how many pips away,
  triggered with the time, side and price, expired, or not open yet, and writes
  trader/entry.json for /trader-exit. It never places an order. Use when the
  user says "tell me when to get in", "watch EURUSD", "has gold broken out",
  "did it break the London range", "entry signal", "time my entry", "check my
  watchlist", or after /trader-scanner and /trader-news, before /trader-exit.
argument-hint: "[SYMBOL] [--session london] [--side both|buy|sell] [--setup range|level]"
---

# trader-entry

The Entry Timer turns a setup into one moment: the bar that confirms it. It
waits for each bar to finish. A price that pokes through the range in the
middle of a bar is not an entry. A bar that CLOSES through it is. Then it says
the time, the side and the price, writes them down for the Exit Planner, and
stops. It never trades. Most people who day trade lose money, and a clean
signal does not change that.

`${CLAUDE_SKILL_DIR}` below is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/entry.py" check EURUSD                    # London range, both sides
python3 "${CLAUDE_SKILL_DIR}/entry.py" check EURUSD --write            # also save trader/entry.json
python3 "${CLAUDE_SKILL_DIR}/entry.py" check XAUUSD --side sell        # COMEX range, shorts only
python3 "${CLAUDE_SKILL_DIR}/entry.py" check USDJPY --session tokyo    # another session
python3 "${CLAUDE_SKILL_DIR}/entry.py" check GBPUSD --session asia_london   # the Asian range, broken in London
python3 "${CLAUDE_SKILL_DIR}/entry.py" check US500 --setup level --level 6850 --side buy
python3 "${CLAUDE_SKILL_DIR}/entry.py" watch EURUSD --until 15:00      # one line per closed bar, stops on the trigger
python3 "${CLAUDE_SKILL_DIR}/entry.py" watchlist                       # every hit in trader/watchlist.json
```

Other flags: `--range-minutes N`, `--interval 5m|1m|15m`, `--min-volume-x X`,
`--json`, `--offline PATH`, `--now "2026-11-16 08:45 London"` (a zone word at
the end, or the session's zone by default). `watch` with `--now` or
`--offline` replays the session on a simulated clock without waiting.

## What it reads and writes

| file | what |
| --- | --- |
| `trader/watchlist.json` | the scanner's hits, with their sessions, for `watchlist` |
| `trader/config.json` | `entry_cutoff_minutes` (30), `flat_by_minutes` (5), per session overrides in `sessions` |
| Yahoo chart API | the session's bars: free, unofficial, can lag |
| `trader/entry.json` | symbol, session, side, status, time (session-local and UTC), bar, price, range |

## The rule

- **The range** is the high and low of the session's first minutes, in the
  session's own zone: London 08:00-08:30 London, COMEX 08:20-08:35 New York,
  US cash 09:30-09:45 New York, the crypto UTC day 00:00-01:00 UTC. DST never
  shifts it: London 08:00 stays 08:00 London.
- **The trigger** is the first completed bar after the range that CLOSES above
  the high (long) or below the low (short). `--side buy` or `--side sell`
  watches one side. A wick through is not a trigger; a close on the level is not
  through it.
- **The time** is the trigger bar's close, session-local (the 08:40 bar closes
  at 08:45 London). The price is its close.
- **Only closed bars count**, and only once the feed has caught up to that
  bar's close. Yahoo's live tick is never a bar.
- **The window.** No entries before the range ends or after
  `entry_cutoff_minutes` (30) before the session's close. On an early close
  the window moves up with it.
- **Volume** (`--min-volume-x`) works where the feed has volume (futures,
  indices, crypto). Forex has none, and the tool says so instead of guessing.
- **Missing bars.** Forex and crypto feeds skip a quiet 5 minutes now and
  then; up to 3 missing range bars are tolerated and said.

## Steps

1. Get the symbol from the user, or run `entry.py watchlist` after the scanner.
   Check `/trader-news` and `/trader-calendar` first: a High-impact release in
   the next half hour blocks the entry anyway (trader-risk).
2. Run `entry.py check SYMBOL`. Say the status in one line: waiting and how
   many pips or points from each level, triggered (long or short, time, price),
   or expired.
3. To wait, run `entry.py watch SYMBOL` in the background, or `check --write`
   on a `/loop` every 5 minutes. Keep the computer awake while it watches.
4. On a trigger: the time, the side, the price, and that nothing was placed.
   If the trigger is more than a bar old, say a late entry is a different trade.
5. Hand off to `/trader-exit` to set the stop and target BEFORE anything is traded.

## Example (test fixture, synthetic bars)

EURUSD, Monday 2026-11-16, London session. The range 08:00-08:30 is 1.16080 to
1.16240. The 08:30 bar wicks to 1.16255 but closes 1.16230: no trigger. At 08:45:

```
Range 08:00-08:30 London: high 1.16240, low 1.16080, 16.0 pips wide (6 of 6 bars).
TRIGGERED LONG 08:45 London at 1.16285: the 08:40 bar (bar 8) closed above the range high 1.16240 (4.5 pips beyond).
This is the moment to get in, if you take the trade. Nothing was placed.
```

Gold the same morning: COMEX range 4055.10 to 4062.40, and the 08:45 New York
bar closes 4053.20, below the low: TRIGGERED SHORT 08:50 New York.

## What it never does

It never places an order, never sizes, never sets the stop (that is
`/trader-exit`), never moves a level after the fact, never counts an open bar,
and never runs `/trader-broker` from a background watch: nobody is there to say yes.

## Safety

- Education and tooling, not financial advice. A trigger is a rules match, not a recommendation.
- Paper trading by default (`"paper": true`). Going live is the user's own decision, in their own config.
- Nothing in this pack places an order except trader-broker, and only when all three hold: trader-risk
  passed that exact order today, the user typed an explicit yes for that one order in the chat, and the
  user clicked Allow once on Claude's own card where a connector places it. Never set an order tool to
  "Always allow".
- Leveraged products (forex, CFDs, futures) can lose money fast; most retail CFD accounts lose money.
