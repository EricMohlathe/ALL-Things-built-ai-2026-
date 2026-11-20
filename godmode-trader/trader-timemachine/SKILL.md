---
name: trader-timemachine
description: >-
  Time Machine. Replays a planned trade before you risk a cent, on any forex
  pair, commodity, index or coin, long or short: 10,000 simulated runs of the
  rest of the session, each bar drawn from the instrument's own 5-minute bars
  at the same time of day in the same session over its last 60 days, plus the
  same rule re-run on every one of those past sessions. Reports target first,
  stop first, neither, the price at your flat-by time, the average R, and a
  plain verdict (coin flip, leans, strongly toward the target or the stop),
  with an ASCII fan chart. Same seed, same numbers. Use when the user says
  "what are the odds", "replay this trade", "simulate it", "backtest this
  setup", "how often does this work", "time machine", or after /trader-exit
  and before /trader-budget.
argument-hint: "[run|chart] [--seed 19] [--replays 10000] [--until close]"
---

# trader-timemachine

Before you risk a cent, the Time Machine plays the rest of the session 10,000
times from your entry, using only what this instrument actually did at this
time of day in this session over the last 60 days. Then it re-runs your exact
rule on every one of those real sessions. The answer is a reality check, not a
promise.

`${CLAUDE_SKILL_DIR}` below is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/timemachine.py" run                    # trader/plan.json, 10,000 replays, seed 19
python3 "${CLAUDE_SKILL_DIR}/timemachine.py" run --write            # also save trader/timemachine.json
python3 "${CLAUDE_SKILL_DIR}/timemachine.py" run --until close      # hold to the close instead of flat_by
python3 "${CLAUDE_SKILL_DIR}/timemachine.py" chart --from           # the fan chart of the saved run
python3 "${CLAUDE_SKILL_DIR}/timemachine.py" run --symbol XAUUSD --side sell --session comex \
    --date 2026-11-16 --entry 4053.20 --stop 4058.75 --target 4042.10 --entry-time 08:50
```

## How it works

1. One request: 60 days of 5-minute bars. Only FULL sessions of the plan's
   session before the plan's date count (London 08:00-17:00 is 108 bars, US
   cash 78, the crypto UTC day 288). Half days are left out. Forex and crypto
   feeds may skip up to 3 quiet bars a session: those are filled flat and
   counted in the report.
2. The pool: for every bar slot of the session, each past session's bar as
   ratios to the bar before it.
3. One replay walks the rest of the session from the entry, drawing each bar
   from the same slot (+-2 bars) of a random past session. The stop is checked
   before the target inside every bar: a bar that touches both is a loss.
4. Outcomes: target first, stop first, or neither by `--until` (default: the
   plan's flat-by). R = the target's R, -1, or the move at `--until` / risk.
5. History: the same range rule, same side, same stop rule, same target R, on
   every past session. The first close beyond the range inside the entry
   window is the entry.

The verdict compares the target's share of the replays that hit a side with
the break-even share at the plan's R (50 % at 1R, 33 % at 2R): under 5 points
"close to a coin flip / break-even", 5 to 15 "leans", 15 or more "strongly".

## Steps

1. After `/trader-exit` writes the plan: `timemachine.py run --write`.
2. Say the four numbers (target first, stop first, neither, green), the price
   range at the flat-by time, the history line, and the verdict in one line.
3. If more than 40 % hit neither, say the flat-by price decides those.
4. Offer `timemachine.py chart --from` for the fan chart.
5. Then `/trader-budget`. A leaning-toward-the-stop verdict is a good reason to
   skip the trade; say so plainly, but it is the user's call.

## Rules

- Never call it a prediction. It is built from the last 60 days of this
  instrument: a central bank, a CPI print, a weekend gap or an exchange hack
  can do what those days never did.
- Same plan, same data, same seed: same numbers. Say the seed.
- Fewer than 20 full sessions in the data is a plain refusal.

## Safety

- Education and tooling, not financial advice. A simulation is not a forecast.
- Paper trading by default (`"paper": true`). Going live is the user's own decision, in their own config.
- Nothing in this pack places an order except trader-broker, and only when all three hold: trader-risk
  passed that exact order today, the user typed an explicit yes for that one order in the chat, and the
  user clicked Allow once on Claude's own card where a connector places it. Never set an order tool to
  "Always allow".
- Leveraged products (forex, CFDs, futures) can lose money fast; most retail CFD accounts lose money.
