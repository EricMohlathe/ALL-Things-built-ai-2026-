# GODMODE Trader: the multi-asset trader skill

11 Claude skills for trading forex, commodities, indices and crypto: scan every
session, track the news and the economic calendar, time every entry and exit
long or short, and replay every outcome before you risk a cent.

Free, MIT, no signup, no API key. The tools are plain Python (3.8 or newer,
nothing to pip install) that read free public data: Yahoo Finance charts and
headlines, the Forex Factory calendar export and the CFTC's Commitments of
Traders report.

One scans 70+ instruments for setups in their own sessions: the London open on
EURUSD, the COMEX open on gold, the NYMEX open on oil, the US cash open on the
S&P, Xetra on the DAX, the UTC day on bitcoin. One watches a setup bar by bar
and tells you the moment to get in, long or short. Another sets your stop and
your target in pips before you do. The Time Machine replays the rest of the
session 10,000 times from the instrument's own recent bars and tells you the
honest odds. The Budget Manager sizes it in lots, contracts or coins, in your
account's currency, under your leverage and margin limits. The Risk Manager
blocks anything over your limits, including two trades that are both short the
dollar, and anything opened in the half hour around a central banker.

And no trade goes through until you say yes. Nothing in this pack can place an
order on its own. Paper trading is the default.

> This is a refactor of [Jake Schincariol's day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill)
> (MIT), which day-trades US stocks. Its design (one job per skill, a shared
> `trader/` folder, a fingerprinted risk check and an explicit yes before any
> order) is kept whole. Everything that assumed US stocks (the 9:30 to 4:00
> New York session, long-only shares, dollars a share, SEC filings, Congress's
> trades) is rebuilt for 24-hour, two-way, leveraged, multi-currency markets.

## Install

In Claude Code, as a plugin from this repository:

```
/plugin marketplace add <owner>/<this-repo>
/plugin install godmode-trader@godmode-trader
```

Or copy the folders (keep `trader-core` with them: every tool imports it):

```bash
git clone https://github.com/<owner>/<this-repo>.git
cp -r <this-repo>/trader-* ~/.claude/skills/
```

Then make your config:

```bash
mkdir -p trader && cp ~/.claude/skills/trader-budget/config.example.json trader/config.json
```

Set `account_currency`, `balance`, `timezone`, `broker` and your limits in it.

## The eleven

| command | job | what it does |
| --- | --- | --- |
| `/trader-scanner` | Chart Scanner | Daily setups (breakouts, flags, RSI, squeezes) and session-range breakouts, long and short, across forex, commodities, indices and crypto. |
| `/trader-news` | News Monitor | Headlines tagged by what moves these markets, the day's calendar events and the move in pips. |
| `/trader-calendar` | Economic Calendar | The week's releases and central-bank events by impact, and a news blackout trader-risk enforces. |
| `/trader-entry` | Entry Timer | Watches a session range or a level bar by bar and calls the moment to get in, long or short. |
| `/trader-exit` | Exit Planner | Stop and target in pips or points before the entry, rounded to the tick, away from the entry. |
| `/trader-timemachine` | Time Machine | 10,000 replays of the rest of the session plus every past session where the rule fired. |
| `/trader-budget` | Budget Manager | Lots, contracts or coins to your max loss, converted to your currency, under leverage and margin limits. |
| `/trader-risk` | Risk Manager | PASS or BLOCK: max loss, daily loss, leverage, margin, currency exposure, the session window, news. |
| `/trader-broker` | Order Executor | The ticket and the exact call for OANDA, Alpaca (crypto), MT5, cTrader or IBKR, never without your yes. |
| `/trader-alerts` | Price Alerts | The world market clock, quotes, and alerts on levels, stops, targets, session opens and news. |
| `/trader-cot` | COT Tracker | Where the big speculators stand in each market's futures, and which trades are crowded. |
| `/trader-data` | Market Data | Years of free history into a local cache: Dukascopy M1 and ticks, Binance with taker delta, HistData, Yahoo, Stooq, FRED macro. |
| `/trader-lab` | Setup Lab | Every GODMODE setup (GM01-GM26) and the claude-trader strategies backtested one at a time, ranked with multiple-testing correction, walk-forward, Monte Carlo, FTMO odds. |
| `/trader-structure` | Market Structure | The SMC / ICT read on several timeframes: BOS, CHoCH, FVGs, order blocks, liquidity, premium / discount, OTE, key levels, killzones, labelled order flow. |
| `/trader-propfirm` | Prop Firm Guardian | FTMO-style rules as numbers: daily and overall floors, room, the largest safe risk, an order check, pass odds by risk size. |
| `/trader-macro` | Macro Backdrop | CPI, core PCE, jobs, the Fed, yields, the curve, real yields, the dollar compass, rate differentials, Fear & Greed, central-bank news. |
| `/trader-dex` | DEX Research | DEX Screener snapshots with pool-identity checks, WATCH / REVIEW / SKIP labels, analyst and reviewer prompts. Paper mode only. |
| `/trader-journal` | Trading Journal | Decisions before outcomes, results in R after costs, a dashboard, an HTML page and a lessons file. |
| `/trader-mt5` | MetaTrader 5 | The terminal's account and history into the pack, one approved order out, and the MT5 Agent Toolkit for building EAs. |
| `/trader-desk` | Desk Brief | Every skill's latest output for your markets on one page, ideas ranked by tested evidence. |

## What it trades

`python3 trader-core/tradercore.py instruments` lists them all (100 with the
futures). Each has its feed, tick, pip, contract size, lot step, quote currency,
default session, a typical spread and its leverage cap.

| class | instruments |
| --- | --- |
| forex | 43 pairs: the majors, the crosses (EURJPY, GBPJPY, EURGBP, AUDNZD ...) and exotics (USDZAR, USDMXN, USDTRY, USDSEK ...). Futures: 6E, 6B, 6J, 6A, 6C, 6S |
| commodities | XAUUSD, XAGUSD, XPTUSD, XPDUSD, USOIL, UKOIL, NATGAS, COPPER. Futures: GC, MGC, SI, SIL, HG, CL, MCL, NG, ZC, ZW, ZS |
| indices | US500, US100, US30, US2000, GER40, UK100, FRA40, EU50, JPN225, HK50, AUS200. Futures: ES, MES, NQ, MNQ, YM, MYM, RTY, M2K |
| crypto | BTCUSD, ETHUSD, SOLUSD, XRPUSD, BNBUSD, ADAUSD, DOGEUSD, LTCUSD, AVAXUSD, LINKUSD, DOTUSD. Futures: BTC, MBT |

Your broker's names and sizes differ? Override any field (`broker_symbol`,
`contract`, `lot_step`, `spread`, `session`, `feed` ...) or add an instrument in
`trader/config.json` under `instruments`, or in `trader/instruments.json` (see
`trader-core/instruments.example.json`).

## Sessions

A session is a window in its own time zone, so "London 08:00" stays 08:00
London through both DST changes. The time zones are built in (US, EU, Sydney
and Auckland DST rules, checked hour by hour against the IANA database in the
tests), so no tz database is needed.

| session | hours | range | used by default for |
| --- | --- | --- | --- |
| `london` | 08:00-17:00 London | 30 min | forex |
| `ny`, `tokyo`, `sydney` | 08:00-17:00 NY, 09:00-18:00 Tokyo, 07:00-16:00 Sydney | 30 min | (choose with --session) |
| `asia_london` | 00:00-17:00 London | 420 min | the Asian range broken in London |
| `comex`, `comex_copper` | 08:20-13:30, 08:10-13:00 NY | 15 min | metals |
| `nymex` | 09:00-14:30 NY | 15 min | oil, gas |
| `cbot` | 08:30-13:20 Chicago | 15 min | grains |
| `us_cash` | 09:30-16:00 NY, NYSE holidays and early closes | 15 min | US indices |
| `xetra`, `lse`, `euronext` | 09:00-17:30 Frankfurt, 08:00-16:30 London, 09:00-17:30 Paris | 15 min | DAX, Euro Stoxx; FTSE; CAC |
| `tse`, `hkex`, `asx` | Tokyo, Hong Kong (lunch breaks handled), Sydney | 15 min | Nikkei, Hang Seng, ASX 200 |
| `utc`, `crypto_ny` | the UTC day; 09:30-16:00 NY every day | 60, 15 min | crypto |

## How to use it

Everything lands in a `trader/` folder in your project, and each skill reads
what the last one wrote:

```
calendar -> scanner -> news -> entry -> exit -> timemachine -> budget -> risk -> broker   (one trade)
alerts: stop, target, flat-by, news                                                       (while it is open)
calendar / cot / news                                                                     (on a schedule)
```

An example, end to end, from the test fixtures (synthetic bars with a hand-made
setup, so every number below is reproducible offline; none of it is a claim
about a real market). Monday 2026-11-16, a $5,000 USD account, $50 max loss:

1. **`/trader-calendar`**: the ECB President speaks at 10:00 London (High,
   EUR), US retail sales Tuesday 13:30 London (High, USD).
2. **`/trader-scanner`** at 09:00 London: of the charts in session, three broke
   out: BTCUSD short at 01:15 UTC, GBPUSD short at 08:40 London, EURUSD long at
   08:45 London. Gold and the S&P are not open yet.
3. **`/trader-news`**: "Euro firms as traders weigh ECB rate path ahead of
   Lagarde remarks" (07:40, central bank); EURUSD +18.9 pips on the day.
4. **`/trader-entry`** watched EURUSD's London range, 1.16080 to 1.16240. The
   08:30 bar wicked to 1.16255 but closed inside. At 08:45: TRIGGERED LONG, the
   08:40 bar closed 1.16285, 4.5 pips above the high.
5. **`/trader-exit`**: stop at the range midpoint 1.16160 (12.5 pips), target
   2R 1.16535 (25 pips), flat by 16:55 London.
6. **`/trader-timemachine`** replayed the rest of the session 10,000 times from
   40 past London sessions (seed 19): target first 14.7 %, stop first 53.5 %,
   neither 31.8 %. History: the same rule fired 29 times, 6 targets, 23 stops.
   Verdict: leans toward the stop. On a random walk, that is the honest answer.
7. **`/trader-budget`**: $50 / 0.00125 = 40,000 units = 0.40 lots, $50.00 at the
   stop, notional $46,514 (9.30x), margin $1,550 at 30:1. One bracket order.
8. **`/trader-risk`** at 08:45: PASS, with a warning that the ECB speaks in 75
   minutes. The same order at 09:45 is BLOCKED by the 30-minute news blackout.
9. **`/trader-broker`** shows the ticket and the exact OANDA body, MT5 request,
   cTrader call or IBKR bracket. You type yes for that order. "yes GBPUSD",
   "yes to all", "sure" and "yes but" are all refused.
10. **`/trader-alerts`** rings below 1.16160, above 1.16535, at 16:55 London,
    and 15 minutes before the next High-impact EUR or USD release.

The same morning on gold: the COMEX range 4055.10 to 4062.40 broke DOWN at 08:50
New York (4053.20); the plan put the stop ABOVE at 4058.75 and the target
below at 4042.10; 0.09 lots risked $49.95.

## The tools

All standard-library Python. The data tools read public endpoints and are
polite about it (a pause between requests, a back-off on HTTP 429, caching).

```bash
python3 trader-core/tradercore.py instruments --class forex        # the registry
python3 trader-core/tradercore.py clock                            # which sessions are open
python3 trader-scanner/scan.py daily                               # daily setups, every class
python3 trader-scanner/scan.py range                               # session-range breakouts so far
python3 trader-calendar/econ.py week --write                       # the week's events -> trader/calendar.json
python3 trader-news/news.py --symbols EURUSD XAUUSD                # headlines, events, moves
python3 trader-entry/entry.py check EURUSD                         # waiting / triggered / expired
python3 trader-entry/entry.py watch XAUUSD --side sell             # bar by bar until it triggers
python3 trader-exit/exit.py plan --stop range-mid --target 2R --write
python3 trader-timemachine/timemachine.py run --write              # 10,000 replays + the history
python3 trader-budget/size.py --write                              # -> trader/orders.json
python3 trader-risk/check.py                                       # PASS / BLOCK per order
python3 trader-broker/ticket.py show                               # the tickets, READY or not
python3 trader-alerts/alerts.py add --from-plan                    # stop, target, flat-by
python3 trader-alerts/alerts.py check                              # rings what hit, once
python3 trader-cot/cot.py latest                                   # speculators' positioning
```

```bash
python3 -m unittest discover -s tests -v
```

The tests run offline on the fixtures in `tests/fixtures` (synthetic, made by
`make_fixtures.py` from fixed seeds) and check every number in the example above.

## Brokers

`"broker"` in trader/config.json: `paper` (the default), `oanda`, `alpaca`
(crypto spot), `mt5`, `ctrader` or `ibkr`. The ticket shows the exact call for
each. Claude places an order only through a connector you have set up for that
broker, with the tool set to "Needs approval". For MT5 and cTrader the ticket
gives you exactly what to enter (or the code for your EA or cBot).

## Fine print

**Not financial advice.** This is software that reads public data and does
arithmetic. It does not know your situation and it cannot see the future.
Most people who day trade lose money, and most retail CFD accounts lose money.
You can lose money, and with leverage you can lose it fast. Decide for yourself,
and talk to a licensed professional if you need advice.

**No trade goes through until you say yes.** Only `/trader-broker` can lead to
an order, and only after `/trader-risk` passes that exact order and you type
yes for it in the chat. Set your broker tool to "Needs approval" in Claude,
never "Always allow".

**Paper first.** `"paper": true` and `"broker": "paper"` are the defaults. Keys
live in environment variables or the connector's settings, never in the chat.

**Leverage is capped twice.** Each instrument carries the ESMA retail cap (30:1
major forex, 20:1 other forex, gold and major indices, 10:1 other commodities
and indices, 2:1 crypto; futures about the exchange margin), your broker's and
your own config's can only lower it, and `max_account_leverage` and
`max_margin_use_pct` cap the whole account.

**The Time Machine is a simulation, not a prediction.** It is built from the
instrument's own last 60 days of 5-minute bars. The future can do things those
days never did: a central-bank surprise, a CPI print, a weekend gap, an
exchange hack.

**A stop is a plan, not a guarantee.** In a fast market, over a data release or
across the weekend, a stop can fill well past its price. The max loss shown is
the loss at the stop price.

**The data is free and unofficial.** Yahoo's endpoints can lag, change or
rate-limit you. Gold and silver come from the COMEX futures feed and US indices
from the cash index, so your broker's CFD price can sit a little away from
them; plans work in distances, so sizes and risk carry over. Check anything
that matters against your broker before you act.

**Holidays.** The NYSE calendar (2026 and 2027), the FX market's closed days,
and the LSE, Xetra and Euronext holidays are built in. Tokyo, Hong Kong and
Sydney holidays are not: the tools say so and trust the feed (no bars on a
weekday means closed).

**Positioning and headlines are context.** A crowded COT reading can stay
crowded for months; a headline is a lead, not a fact.

## Files

```
trader-core/        tradercore.py: instruments, sessions, time zones, data, money (every tool imports it)
trader-scanner/     SKILL.md, scan.py
trader-news/        SKILL.md, news.py
trader-calendar/    SKILL.md, econ.py
trader-entry/       SKILL.md, entry.py
trader-exit/        SKILL.md, exit.py
trader-timemachine/ SKILL.md, timemachine.py
trader-budget/      SKILL.md, size.py, config.example.json
trader-risk/        SKILL.md, check.py
trader-broker/      SKILL.md, ticket.py, claude_desktop_config.example.json
trader-alerts/      SKILL.md, alerts.py, alerts.example.json
trader-cot/         SKILL.md, cot.py
trader-data/        SKILL.md, data.py: the history cache (trader-core/history.py, bars.py)
trader-lab/         SKILL.md, lab.py, setups.py: the Setup Lab (trader-core/engine.py, stats.py, prop.py)
trader-structure/   SKILL.md, structure.py
trader-propfirm/    SKILL.md, propfirm.py
trader-macro/       SKILL.md, macro.py
trader-dex/         SKILL.md, dex.py
trader-journal/     SKILL.md, journal.py
trader-mt5/         SKILL.md, bridge.py, toolkit/ (the MT5 Agent Toolkit, MIT)
trader-desk/        SKILL.md, desk.py
tests/              unittest suite + synthetic offline fixtures
```

MIT. Original day-trader-skill by [Jake Schincariol](https://opusjake.ai); the
multi-asset refactor by the GODMODE Trader contributors.
