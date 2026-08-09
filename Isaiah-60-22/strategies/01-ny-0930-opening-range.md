# 01 — The 9:30 New York Opening Range

The US equities cash open at 09:30 NY produces the highest volume and the
widest spread of the day within a few minutes of the bell. The model marks the
first five minutes as a reference range and takes a position when price leaves
it.

**EA preset:** `PRESET_NY_ORB_0930`
**Range timeframe:** M5 · **Entry timeframe:** M1
**Recommended instruments:** NQ, ES, US30, XAU/USD. Spot FX majors only with
your eyes open — see the instrument note in `00-session-clock.md`.

---

## The rules

### Step 1 — Mark the opening range

Set the chart to **5-minute**. Wait for the candle that opens at **09:30 NY**
to close at **09:35 NY**. Draw a horizontal line at its **high** and another at
its **low**. Extend both to the right. Those two lines are the entire
roadmap for the session.

Do not adjust them later. Do not use the 09:25 candle because it "looks
cleaner." The range is defined by the clock, not by taste.

### Step 2 — Wait for the break

Drop to the **1-minute** chart for execution.

A break is a **body close** beyond a boundary line, not a wick through it. The
EA enforces this with `InpRequireBodyClose = true`. A wick that pokes the level
and closes back inside is not a break — it is the setup for a different model
(see `MODEL_TRAP` below).

Direction is decided mechanically by which side breaks first. Long above the
range high, short below the range low. There is no "but the trend looks
bearish" override at this stage — if you want a directional filter, configure
one deliberately in Step 5 and let it apply to every trade equally.

### Step 3 — Enter

Enter on the close of the breaking candle. Not on a retest.

This is a deliberate departure from how the strategy is usually taught, and it
is the most important choice in this document. Read the next section before you
override it.

### Step 4 — Stop loss

Place the stop at the **opposite boundary of the opening range**, plus a buffer
for spread. On a long: the stop goes below the range low. On a short: above
the range high.

The EA applies floors and ceilings so a freak-narrow or freak-wide range does
not produce an unmanageable position:

```
InpMinStopATR = 0.25     // stop is at least 0.25 x ATR(14)
InpMaxStopATR = 3.0      // if the structural stop exceeds 3 x ATR, skip the day
```

### Step 5 — Take profit and exit

Default is a fixed **2R** target (`InpExitMode = EXIT_FIXED_R`,
`InpTargetR = 2.0`).

Two other exits are worth testing, and the published research favours the
second:

| Mode | Behaviour |
|---|---|
| `EXIT_FIXED_R` | 2R target, 1R stop. The taught version. |
| `EXIT_R_THEN_TIME` | 2R target if it gets there, otherwise flatten at the session end. |
| `EXIT_TIME_ONLY` | Stop only, hold to the force-flat time. This is what the peer-reviewed version does. |
| `EXIT_ATR_TRAIL` | 1.5 × ATR trailing stop, flatten at session end. |

### Step 6 — The time window

Entries only between **09:35 and 10:30 NY**. After 10:30 the setup has expired;
do not take it at 11:15 because it "finally looks good." The EA closes the
window for you (`InpTradeEndHH/MM`), and `InpMaxTradesPerDay = 2` stops the
session from turning into a revenge-trading window.

---

## Why there is no retest in the default

Every video teaching this strategy includes the same three steps: break, wait
for the pullback to retest the broken level, wait for a rejection candle, then
enter. It is presented as the discipline that separates the professional from
the person who chases.

It was tested. Across 165,336 trades, the retest-and-confirm variant produced a
**lower** win rate than entering directly on the break — 31.9% versus 33.0% on
held-out data, p < 0.001. The mechanism is not mysterious:

1. You enter later, so you pay away part of the move you were trying to catch.
2. Your stop is measured from a worse price, so it has to be wider for the same
   structural invalidation, which lowers your R.
3. The days that run hardest never retest at all. Waiting for the pullback
   systematically filters out the best trades in the sample and keeps the ones
   that stalled.

Meanwhile the **published, peer-reviewed** opening-range strategy that does
show an edge — Zarattini, Barbon & Aziz (2024), over 7,000 stocks, 2016–2023 —
has no retest, no confirmation candle, mechanical direction, a hold to the
close, and a hard filter on relative volume. Its edge is in *which days it
trades* and *how it exits*, not in the entry trigger.

So: the default is `MODEL_BREAK_DIRECT`. The retest is available as
`MODEL_RETEST` and you should run it, once, on your own instrument, with
everything else identical. Replicating the finding yourself costs you one
backtest and buys you permanent immunity to the next person who tells you the
retest is the secret.

---

## The five entry models

All five sit behind one dropdown (`InpModel`) so the taught version and the
restated version are the same code, the same risk kernel, and the same journal.
Anything that differs between two runs is the model, not the plumbing.

| Model | Trigger |
|---|---|
| `MODEL_BREAK_DIRECT` | Body close beyond the boundary. Enter at that close. **Default.** |
| `MODEL_BREAK_FVG` | Break, then enter on a fair value gap left inside the displacement leg. |
| `MODEL_TRAP` | Break out → close back inside → close back out. A failed-failure. |
| `MODEL_RETEST` | Break → pullback to the boundary → rejection close. The taught version. |
| `MODEL_SWEEP_MSS` | Sweep of the range extreme → market structure shift. The ICT reading. |

`MODEL_SWEEP_MSS` is the same logic as the Asian-range model in `02`, pointed at
the 9:30 range instead of the overnight one. If it works on one range and not
the other, that is information.

---

## Configuration

Starting point for a first backtest. Change one thing at a time, and count
every change as a variant.

```
=== 1. PRESET & MODEL ===
InpPreset              = PRESET_NY_ORB_0930
InpModel               = MODEL_BREAK_DIRECT
InpRangeTF             = PERIOD_M5
InpEntryTF             = PERIOD_M1

=== 2. CLOCK ===
InpBrokerGMTOffset     = <your broker's winter offset — verify it>
InpAutoGMTOffset       = true

=== 3. SIGNAL RULES ===
InpRequireBodyClose    = true
InpMaxBarsToTrigger    = 60
InpMaxRangeATR         = 3.0      // skip days where the open range is abnormally wide

=== 4. BIAS ===
InpBiasMode            = BIAS_OFF   // add a filter only after you have a baseline

=== 5. STOPS & TARGETS ===
InpExitMode            = EXIT_FIXED_R
InpTargetR             = 2.0
InpMinStopATR          = 0.25
InpMaxStopATR          = 3.0

=== 6. RISK ===
InpRiskPercent         = 0.5
InpMaxDailyLossPct     = 2.0
InpMaxTradesPerDay     = 2
InpMaxSpreadVsStop     = 10.0

=== 7. JOURNAL ===
InpWriteJournal        = true
InpRunTag              = "orb_direct_v1"     // change this every single run
```

Strategy Tester: **"Every tick based on real ticks"**, two years minimum, and
**real spread**. A backtest on fixed spread at the New York open is a backtest
of a market that does not exist — the open is precisely when spreads widen.

---

## Grading the run

```bash
# The journal lands in MQL5/Files/SRF_journal.csv
python3 srf_forensics.py SRF_journal.csv --target-r 2.0 --variants 1 --plots orb.png
```

Then re-run the identical backtest with `InpModel = MODEL_RETEST` and compare.
That is finding C-1.1 replicated on your instrument, at your costs.

Every additional parameter, symbol, timeframe or model you try increments
`--variants`. Be honest about the count. The Šidák correction is brutal by
design, and understating the number is the most comfortable way to lie to
yourself in this entire process.

---

## What kills this strategy

- **Wide spread at the open.** The 09:30–09:35 window is the widest spread of
  the day on most instruments. `InpMaxSpreadVsStop = 10.0` rejects an entry
  where the spread exceeds 10% of the intended stop. If that filter is
  rejecting most of your entries, the strategy is not viable at your broker,
  and no parameter will fix that.
- **A range that is too narrow.** A tight opening candle gives a tight stop,
  which looks like great R until you notice the spread is now a third of it.
  `InpMinRangePts` and `InpMinStopATR` exist for this.
- **News at 10:00.** US data releases land at 08:30 and 10:00 NY. A 10:00
  release inside your entry window is not a trade, it is a coin flip with a
  wider spread. Check the calendar before the session.
- **Trading it on spot FX because the video did.** There is no 09:30 cash open
  in spot FX. The structure the model is exploiting may simply not be present.
