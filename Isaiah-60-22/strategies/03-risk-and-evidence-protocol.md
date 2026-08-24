# 03 — Risk and Evidence Protocol

This document is the part of the workspace that transfers. The two strategies
may or may not have an edge on your instrument. The protocol below works on
any strategy, including the next one somebody sells you.

---

## Part 1 — The risk kernel

These limits are enforced in code by all four EAs. They are not suggestions
and there is no input that turns the kernel off.

| Limit | Default | What it does |
|---|---|---|
| Risk per trade | 0.5% of equity | Position size is derived from the stop distance, never fixed. |
| Max daily loss | 2% of session-start equity | Halts entries for the rest of the NY session. |
| Max total drawdown | 10% from peak equity | Halts the EA permanently until you restart it deliberately. |
| Max trades per session | 2 (ORB) / 1 (sweep) | The second setup of a losing morning is revenge, not signal. |
| Max consecutive losses | 4 | Halts for the session. |
| Max spread | 30 points, or 10% of the stop | Rejects the entry outright. |
| Stop floor | 0.25 × ATR | Stops a freak-narrow range producing a stop the spread eats. |
| Stop ceiling | 3.0 × ATR | Rejects the day rather than taking an unmanageable position. |

### The sizing rule that matters most

All four EAs **refuse to round up to the broker minimum**. If one minimum lot
would risk more than your configured percent, the EA does not take the trade
and says so in the log:

```
Isaiah 60:22 | entry rejected: one minimum lot exceeds the configured risk
```

This is the single most common way small accounts die. A $200 account trading
a symbol whose minimum lot risks $18 on a normal stop is running 9% per trade
regardless of what the risk input says. The EA will not do it. If you see that
message constantly, your account is too small for that instrument — that is
information, not a bug to work around.

### What the kernel does not protect you from

- **Correlated positions.** Running the ORB bot on NQ and ES simultaneously is
  one bet at double size, and the per-EA daily loss limit will not see it.
- **Gap risk through a stop.** The stop is a price, not a guarantee.
- **Trading the same session by hand while the EA runs.** The EA only counts
  its own positions.

---

## Part 2 — The six gates

Run `srf_forensics.py` on the journal from every backtest. A strategy is
tradeable only when all six gates pass. This is the same script that grades
output from the MT5 and cTrader builds, because all four EAs write the same
CSV schema.

| Gate | Fails when |
|---|---|
| **Sample size** | Fewer than 100 distinct sessions. Trades are not the sample size — sessions are. Twenty trades on four days is four data points. |
| **Break-even gap** | Win rate at or below `1/(1+R)`. At a 2R target the payout demands 33.3% before you have made a single dollar. Clearing it is the minimum, not the achievement. |
| **Day-clustered CI** | The lower bound of the session-bootstrap confidence interval touches zero. Trades taken on the same morning are one bet, not many, and per-trade statistics flatter accordingly. |
| **Concentration** | The best two sessions carry over half the gross profit. That is two lucky days wearing a system's clothes. |
| **Cost survival** | Expectancy dies at or below the round-trip cost you actually pay. Note this one is measured against *your* observed spread, taken from the journal, not an assumption. |
| **Out of sample** | Held-out sessions fail at the Šidák-adjusted alpha for the number of variants you tried. |

### A failed gate is not a tuning prompt

Re-tuning until a gate passes is the mechanism by which a coin flip becomes a
backtest. Every parameter you change, every symbol you add, every timeframe
you try, and every entry model you switch increments the variant count, and
the correction gets harsher each time:

```
Šidák-adjusted alpha = 1 - (1 - 0.05)^(1/n)
```

At 1 variant you need p < 0.05. At 12 variants you need p < 0.00427. At 50
you need p < 0.001. Understating `--variants` is the most comfortable lie
available in this entire process, and the only person it fools is you.

Be honest with the count:

```bash
python3 srf_forensics.py I22_ORB_journal.csv --target-r 2.0 --variants 12
```

---

## Part 3 — The order of operations

Do these in order. Skipping a step does not save time, it just moves where you
find out.

**1. Verify the clock.** Set the broker GMT offset from the actual server clock
   (MT5 only — the cTrader build reads UTC directly). Backtest across one March
   and one November DST switch and confirm on the dashboard that the range
   still forms at the right NY time on both sides.

**2. Get a baseline.** Default model, bias off, 2R fixed target, one symbol,
   two years, real ticks, real spread. Do not touch a single parameter yet.
   This is variant 1.

**3. Grade the baseline.** Run the forensics. If the break-even gate fails at
   variant 1, the entry carries no directional information on this instrument
   and no amount of exit tuning will manufacture some.

**4. Run the falsification test.** For the ORB: re-run with `Retest` and
   compare. For the sweep: re-run with the bias filter off and compare. In both
   cases you are testing the claim the strategy is built on, on your own data.

**5. Change one thing.** Count it. Re-grade.

**6. Forward-test on demo for 40+ sessions.** The forward test is the only
   sample nobody tuned on. Forty sessions is not enough to prove an edge, but
   it is enough to catch the execution problems a backtest cannot show you:
   requotes, weekend gaps, the broker's actual spread at 09:30, and whether
   you can leave it alone.

**7. Only then, live, at the smallest size the account allows.**

---

## Part 4 — Cross-platform validation

Building the same strategy on two platforms is not duplication, it is a test.
Both builds write the same journal schema deliberately.

```bash
python3 srf_forensics.py I22_ORB_journal.csv       --variants 2   # MT5
python3 srf_forensics.py I22_ORB_journal_ct.csv    --variants 2   # cTrader
```

Same symbol, same period, same model, same parameters. The trade *decisions*
should match closely; where they diverge you have found something real:

- **Different entry prices, same signals** — normal. Different feeds, different
  spreads. The size of the gap is your execution-cost estimate.
- **Different signals on the same bar** — a bar-alignment or clock problem.
  Check the NY conversion first; it is almost always the clock.
- **One platform trades a session the other skips** — usually the range filter
  hitting a slightly different ATR. Harmless, but worth confirming.
- **Wildly different results** — do not pick the better one. Find the bug.

A strategy whose result depends on which platform ran it did not have an edge;
it had a data artifact.

---

## Part 5 — The claims that should end a conversation

Keep these handy. They are arithmetic, not opinion.

**"80% win rate at 1:3."** Expectancy = 0.80(+3R) + 0.20(−1R) = **+2.20 R per
trade**. At 1% risk over 250 trades, $1,000 becomes about $223,000 in a year,
and about $49 million the year after. Nobody with that sells a PDF.

**"I made $18,500 last month."** Dollars are a statement about position size,
not about edge. A number in R, over a stated number of sessions, with the
losing months included, is a claim. A dollar figure with a screenshot is not.

**"This works on every pair."** A strategy that works everywhere usually works
nowhere; it means the tester ran many variants and reported the survivors.
That is exactly what the Šidák correction exists to catch.

**"The confirmation candle is the secret."** It was measured. It lowered the
win rate, 33.0% → 31.9% on holdout, p < 0.001, across 165,336 trades.

---

## Part 6 — The honest baseline

Two studies on complete exchange records found that **97% of persistent retail
day traders lost money**, and **under 1% were reliably profitable after fees**.
That is the population you are joining, not a cautionary tale about other
people.

Nothing in this workspace changes that base rate. What it changes is whether
you find out in a demo account with a failed gate, or in a live account over
eleven months. The instrument that does that is the forensics script, and it
is the only part of this repository that is guaranteed to be useful.
