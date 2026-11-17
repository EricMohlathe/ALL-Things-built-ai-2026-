---
name: trader-lab
description: >-
  Setup Lab. Tests every GODMODE setup (GM01-GM26: opening-range breakout,
  session sweep, FVG, order block, ICT Unicorn, Wyckoff spring, VWAP
  reversion, displacement, order-flow absorption, CRT / power of three,
  Silver Bullet, OTE, price action, turtle soup, supply and demand, market
  structure, initial balance, harmonics, RSI(2), gap fade, previous-day
  levels, EMA pullback, opening-gap CE, SMT divergence, breakout-retest,
  confluence stack) plus the claude-trader SMC-trend and Ichimoku strategies,
  one at a time, on years of history with spread, slippage and commission,
  no look-ahead, stop before target. Ranks them with multiple-testing
  correction, breaks results down by hour, weekday, side and regime, runs a
  grid with walk-forward out-of-sample testing, Monte Carlo drawdowns, FTMO
  pass probability by risk size, rolling tiering and an uncorrelated
  portfolio. Each setup links to its MT5 Expert Advisor and cTrader cBot.
  Use when the user says "backtest", "which setup works", "rank the setups",
  "win rate", "past trades", "percentages", "walk-forward", "Monte Carlo",
  "FTMO odds", "optimize", or "build a portfolio of setups".
argument-hint: "[list|run|rank|optimize|mc|prop|tier|portfolio] SETUP SYMBOL [--tf M15] [--from 2023-01-01]"
---

# trader-lab

The compendium's first rule: you cannot judge a setup inside a pooled score.
The Setup Lab runs each setup on its own, on one market, one position at a
time, with every cost in, and reports what happened in R (multiples of the
risk), the trades it did not take and why, and how much of it could be luck.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/lab.py" list                                    # every setup, family, MT5 / cTrader file
python3 "${CLAUDE_SKILL_DIR}/lab.py" run GM01 EURUSD --by hour --by side      # one setup on the cache
python3 "${CLAUDE_SKILL_DIR}/lab.py" run GM11 US500 --tf M5 --from 2024-01-01 --set target_r=3 --trades 20
python3 "${CLAUDE_SKILL_DIR}/lab.py" rank EURUSD GBPUSD XAUUSD US500 BTCUSD --save   # the whole matrix
python3 "${CLAUDE_SKILL_DIR}/lab.py" rank EURUSD --family smc                 # one family
python3 "${CLAUDE_SKILL_DIR}/lab.py" optimize GM03 XAUUSD                     # grid, robustness, walk-forward
python3 "${CLAUDE_SKILL_DIR}/lab.py" mc GM14 US500 --risk 0.5                 # Monte Carlo drawdowns
python3 "${CLAUDE_SKILL_DIR}/lab.py" prop GM01 EURUSD --preset ftmo_2step     # pass odds at each risk size
python3 "${CLAUDE_SKILL_DIR}/lab.py" tier GM07 BTCUSD                         # rolling on/off (compendium 22.8)
python3 "${CLAUDE_SKILL_DIR}/lab.py" portfolio EURUSD GBPUSD XAUUSD           # keep uncorrelated edges
python3 "${CLAUDE_SKILL_DIR}/lab.py" run GM24 EURUSD --with GBPUSD            # SMT needs a correlated market
```

Data comes from the trader-data cache (`/trader-data get EURUSD --from 2022`
first). `--offline <file or folder>` reads a saved Yahoo chart, `--yahoo` the
last 60 days live. `--spread`, `--slippage` (ticks) and `--commission` (per lot
round turn) set costs; global options can go before or after the command.

## How a backtest works here

1. The setup looks at each bar's CLOSE and may return a signal: side, stop,
   target, market or limit entry. It sees only what was known then; higher
   timeframes are read from their last closed bar.
2. A market entry fills at the next bar's open plus half the spread and the
   slippage. A limit waits `expiry_bars` and fills at the limit (or a better open).
3. Inside a bar the stop is checked before the target: a bar that touches both
   is a loss. A gap through the stop fills at the open, worse than the stop.
4. Exits: stop, target, break-even, trailing, time, the session's flat-by time,
   the setup's own rule (RSI(2) leaves when price reclaims its 5-bar mean), or
   the end of the data.
5. Every signal is logged, the ones not taken too (already in a trade, limit not
   filled, filtered, wrong side): the denominator a monolith never shows.

## Reading the numbers

- **Expectancy (R)**: the average trade after costs. The only number that pays.
- **p and P(ADJ)**: the chance a zero-edge setup looks this good. Test 28
  setups on 6 markets and about 8 will show p < 0.05 by luck alone; P(ADJ) is
  Holm-corrected for every test in the table and is the one to read.
- **SQN, profit factor, payoff, max drawdown, losing streak, MAE / MFE** (how
  far trades went against you and for you).
- **Walk-forward**: pick the best parameters on each training window, keep only
  the next unseen window's trades. Only the out-of-sample line counts; an
  efficiency under 0.5 means the in-sample result was mostly fit to noise.
- **Robustness**: a lone best parameter surrounded by losers is a curve fit.
- **Monte Carlo**: plan for the 95th-percentile drawdown, not the median.
- **Prop**: whole real trading days resampled into thousands of challenges at
  each risk size, with the firm's daily and maximum loss rules and minimum days.

## The setups and the platform files

`list` prints each setup's MT5 Expert Advisor
(`MT5_MasterLibrary/Experts/GODMODE/GMxx_*.mq5`) and cTrader cBot
(`cTrader_MasterLibrary/GMxx_*.cs`). The Python rules are clean-room bar-based
versions of the same ideas, made to be tested on years of free data; where an
EA needs a footprint or real ticks, the note says what stands in for it (the
delta source of `/trader-data`). Prove an edge here, then run the EA in the
MT5 Strategy Tester on "Every tick based on real ticks" before going live.

CT01 and CT02 follow the claude-trader agents (MIT): the H4 EMA stack with a
rising ADX entered at an H1 FVG or order block, and the Ichimoku trend agent.

## Rules

- A backtest is the best case. Real fills, news spikes, platform outages and
  your own discipline only make it worse. Halve what you see before you plan.
- Fewer than 100 trades says almost nothing. Fewer than 30 says nothing.
- Never pick parameters on the full history and then quote the full history.
  Use `optimize` and read the out-of-sample line.
- `--save` writes `trader/lab/<SYMBOL>/<SETUP>-<TF>.json` (every trade) and
  `trader/lab/summary.json`, which `/trader-desk` and `/trader-journal` read.
- No setup here is a recommendation. "No edge on this data" is a valid,
  useful result: do not trade what the numbers do not support.

This is not financial advice. Past results do not predict future results.
