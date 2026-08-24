# 00 — The Session Clock

Every rule in this workspace is anchored to **New York local time**. Not GMT,
not broker time, not your local time. This document exists because that
distinction is the single most common way a correctly-coded session strategy
ends up trading the wrong window for four months of every year.

---

## Why this is not a fixed offset

New York observes daylight saving. Under the current US rule, EDT runs from
the **second Sunday in March** to the **first Sunday in November**; the rest of
the year is EST.

| | UTC offset | In force |
|---|---|---|
| EST (winter) | UTC−5 | early Nov → mid Mar |
| EDT (summer) | UTC−4 | mid Mar → early Nov |

Your broker's server clock is usually a **fixed** offset — commonly GMT+2 or
GMT+3, sometimes with its own DST rule that follows *European* dates, which
change on different Sundays than the US ones. So the gap between broker time
and New York time is not constant, and there are two or three weeks each year
where Europe has switched and the US has not.

A strategy that hard-codes "09:30 is 16:30 on my broker" is correct for part
of the year and one hour wrong for the rest. One hour is the entire opening
range.

Not one of the six source documents mentions this. One commenter on the ICT
article noticed it on their own and asked whether the Asian range had "changed
now that New York has become UTC−5"; the answer they got did not address it.

---

## How the EA handles it

`GODMODE_SessionRange_Forge.mq5` converts broker time to New York time using
the real US DST rule, so the windows stay correct across both switches. You
give it one number:

```
InpBrokerGMTOffset = <your broker's WINTER GMT offset, in hours>
InpAutoGMTOffset   = true   // attempts detection at init; live accounts only
```

**Check that number, do not guess it.** In MT5, compare the server clock in
Market Watch against a known UTC source during January or February. Auto-detect
does not work in the Strategy Tester, so for backtests the input value is the
one that counts.

---

## The windows

All times New York local. These are the values the EA's presets set, and the
values every rule document in `strategies/` refers to.

### `PRESET_NY_ORB_0930` — the 9:30 opening range

| Phase | Window (NY) |
|---|---|
| Range forms | 09:30 – 09:35 |
| Entries allowed | 09:35 – 10:30 |
| Force flat | 15:55 |

The range is the first 5-minute candle of the US equities cash open. The entry
window closes at 10:30 because that is where the opening volume surge decays;
the sources that give a window at all say 10:30 or 11:00. Force-flat at 15:55
exists so a time-based exit can hold to the close without carrying into the
auction.

### `PRESET_ASIAN_ICT` — the Asian range

| Phase | Window (NY) |
|---|---|
| Range forms | 19:00 – 00:00 (wraps midnight) |
| Entries allowed | 02:00 – 11:00 |
| Force flat | 12:00 |

19:00–00:00 NY is the ICT definition and the one this workspace uses. The
range-forming window wraps midnight, which means the session's range belongs
to the *following* trading day — the EA handles this, but it matters if you
are marking levels by hand.

The **midnight open** (00:00 NY) is a level in its own right, not just the end
of the range. See `02-asian-range-liquidity-sweep.md`.

The entry window opens at 02:00 to cover the London open and runs to 11:00 to
cover the New York AM session, because the sweep can happen at either. Most
of the sources say the sweep "almost always" lands at the London open or early
NY-AM; the article's own author, asked whether to wait for London, said yes.

### `PRESET_LONDON_ORB` — the London opening range

| Phase | Window (NY) |
|---|---|
| Range forms | 03:00 – 03:15 |
| Entries allowed | 03:15 – 06:00 |
| Force flat | 11:00 |

Included as a control. If a 15-minute range at the London open behaves like
your 5-minute range at the New York open, that tells you something about
whether you have found a market structure or a calendar coincidence.

---

## The source documents disagree, and here is the reconciliation

| Source | Asian range stated as | In NY local terms |
|---|---|---|
| ICT / innercircletrader | 19:00 – 00:00 NY | 19:00 – 00:00 ✔ (the reference) |
| FXM "Ultimate Guide" | 22:00 – 08:00 GMT | 17:00 – 03:00 EST / 18:00 – 04:00 EDT |
| FXM "Goldmine" | "20–45 min after Tokyo open" | ~19:20 – 19:45 (Tokyo opens 19:00 EST) |
| FXM Goldmine step 1 | 22:00 – 00:00 GMT | 17:00 – 19:00 EST |

Four descriptions of "the Asian session" that overlap but do not agree, two of
them from the same author in different articles. Two are given in GMT with no
DST note, which means they drift an hour against New York twice a year.

**This workspace uses 19:00–00:00 NY.** If you want to test another definition,
use `PRESET_CUSTOM` and the raw `InpRangeStart*` / `InpRangeEnd*` inputs — and
count it as a variant in the forensics, because it is one.

---

## Instrument note

The clock is anchored to New York because that is where the liquidity events
are. That does not mean every instrument respects it:

- **FX majors and gold** trade continuously; the windows are real but soft.
- **NQ / ES futures** have a genuine 09:30 cash open with a volume signature
  you can see. The 9:30 model was born on these.
- **Spot FX at 09:30 NY** has no equivalent structural event. It is being
  borrowed from equities. That is worth remembering when the backtest is
  disappointing — it may be telling you the truth.

---

## Before you trade a single session

1. Confirm your broker's winter GMT offset from the server clock, in writing.
2. Set `InpBrokerGMTOffset` to that number.
3. Run one backtest across a **March** and a **November** DST switch and check
   the EA's dashboard shows the range forming at 09:30 NY on both sides of the
   switch.
4. Only then move on to `01` or `02`.
