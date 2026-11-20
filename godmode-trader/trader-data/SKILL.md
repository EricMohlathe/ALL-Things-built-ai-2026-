---
name: trader-data
description: >-
  Market Data. Downloads years of free history into a local cache so every
  other skill can test on far more than 60 days: Dukascopy M1 candles and raw
  ticks for forex, metals, indices and oil (ticks give real spreads and a
  tick-rule delta), Binance klines with the real taker-buy volume for crypto
  (aggressor delta), monthly bulk files from data.binance.vision, HistData
  forex M1 by the year, Yahoo for every class, Stooq dailies going back
  decades, and FRED macro series (CPI, core PCE, payrolls, yields, the dollar
  index, VIX). Merges every download into trader/data/<SYMBOL>/<TF>.csv,
  builds bigger timeframes from smaller ones without look-ahead, checks the
  data for gaps, flat bars and bad jumps, and imports your own MT5 or cTrader
  CSV exports. Use when the user says "download history", "get more data",
  "get years of EURUSD", "tick data", "order flow data", "CPI", "FRED",
  "import my MT5 history", or before /trader-lab.
argument-hint: "[get|info|quality|resample|import|fred] SYMBOL [--from 2022-01-01] [--tf 1m]"
---

# trader-data

Sixty days of 5-minute bars is enough to look at a chart and nowhere near
enough to prove a setup. This skill fills a local cache with years of free
history, one file per symbol and timeframe, so the Setup Lab, the Time Machine
and the scanner can work on real samples.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/data.py" get EURUSD --from 2022-01-01 --to 2025-12-31   # Dukascopy M1, every day
python3 "${CLAUDE_SKILL_DIR}/data.py" get EURUSD --from 2026-11-01 --ticks             # M1 from raw ticks (+ delta, spread)
python3 "${CLAUDE_SKILL_DIR}/data.py" get XAUUSD --from 2020                           # gold, M1, from 2020
python3 "${CLAUDE_SKILL_DIR}/data.py" get BTCUSD --tf 5m --from 2024-01-01             # Binance, taker delta
python3 "${CLAUDE_SKILL_DIR}/data.py" get ETHUSD --tf 1h --from 2021-01 --source binance_vision
python3 "${CLAUDE_SKILL_DIR}/data.py" get GBPUSD --source histdata --year 2024         # one year of M1
python3 "${CLAUDE_SKILL_DIR}/data.py" get US500 --tf 1d --source stooq                 # decades of dailies
python3 "${CLAUDE_SKILL_DIR}/data.py" info                                             # what is cached
python3 "${CLAUDE_SKILL_DIR}/data.py" quality EURUSD --tf M1                           # gaps, flat bars, jumps
python3 "${CLAUDE_SKILL_DIR}/data.py" resample EURUSD --to H1                          # save a bigger timeframe
python3 "${CLAUDE_SKILL_DIR}/data.py" fred CPIAUCSL CPILFESL PCEPILFE PAYEMS UNRATE DGS2 DGS10
python3 "${CLAUDE_SKILL_DIR}/data.py" import EURUSD --csv export.csv --tf M15 --tz MT5
```

Add `--json` for machine-readable output and `--root` for another cache folder.

## Sources

| Source | Markets | Depth | What it adds |
|---|---|---|---|
| dukascopy | forex, metals, indices, oil, BTC/ETH CFDs | M1 back to the 2000s | `--ticks`: bid/ask ticks, real spread, tick-rule delta |
| binance | crypto | any timeframe, 1,000 bars a request | taker-buy volume: measured aggressor delta |
| binance_vision | crypto | monthly bulk zips | the same, fast for years |
| histdata | forex | M1 a year per file | a second forex source (times are EST, UTC-5, no DST) |
| yahoo | every class | 5m for 60 days, 1h for 2 years, daily for decades | the feed the live skills use |
| stooq | indices, metals | daily for decades | long daily history |
| fred | macro | the whole series | CPI, PCE, payrolls, rates, the dollar, VIX for /trader-macro |

`--source auto` (the default) picks Binance for spot crypto, Yahoo for daily
bars, Dukascopy for intraday on anything it carries, and Yahoo otherwise.

## The cache

`trader/data/<SYMBOL>/<TF>.csv` with `time,open,high,low,close,volume,delta`
(time is the bar's start, unix seconds UTC). Every download merges into what
is there, so you can grow a series a month at a time. A bigger timeframe is
built from the finest one cached, and a bar is only kept when the source
covers its whole span, so a still-forming bar can never leak into a test.

## Delta, honestly labelled

Order-flow tools need to know who was aggressive. The cache stores the best
delta each source can give, and every tool that reads it says which one it
used:

1. **measured**: Binance taker-buy volume (buyers minus sellers who crossed the spread);
2. **tick rule**: from Dukascopy ticks, each tick signed by its move;
3. **CLV proxy**: when there is nothing else, where the bar closed in its range times volume.

Forex has no central volume: Dukascopy and Yahoo "volume" is tick count. Treat
forex delta as an estimate, and say so.

## Rules

- Every source here is free and unofficial or semi-official. Each can change,
  throttle or disappear without notice. Data is for research: check anything
  that matters against your broker's own history before you rely on it.
- Run `quality` after a big download. A weekend gap is normal; a two-day hole
  on a Wednesday, a run of flat bars or a 20-sigma jump is not.
- Broker exports (MT5, cTrader) are in the broker's server time. Most MT5
  servers run "New York close" time (UTC+2 in winter, UTC+3 in summer, switching
  on the US dates): pass `--tz MT5`. Otherwise pass the server's IANA zone
  (`--tz Europe/Athens`, `--tz Europe/Prague`) so the cache stays in UTC.
- Downloads are polite and sequential. A full year of Dukascopy M1 is about 260
  requests; ticks are one request per hour of data, so keep tick ranges short.

## Where it goes next

- `/trader-lab` tests every GODMODE setup on the cache.
- `/trader-macro` reads the FRED series.
- `/trader-structure` reads the cached bars for SMC, ICT and order-flow levels.

This is not financial advice. Historical data does not predict the future.
