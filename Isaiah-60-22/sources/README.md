# Sources

The material these rules were extracted from, archived so the extraction can
be checked. Read this before assuming any rule in `strategies/` is the
author's invention — and before assuming any of it is established fact.

## The documents

| File | What it is | What was taken from it |
|---|---|---|
| `pdf/930am-Forex-EA-spec_MQL5-job-220387.pdf` | An MQL5 freelance job posting (June 2024) requesting a 9:30 EA | The mechanical framing: 5-minute range at a configurable session time, trend decided by comparing the current candle against the previous one, timeframe and pair selectable. |
| `pdf/ICT-Asian-Range-Liquidity-Sweep_innercircletrader.pdf` | Tutorial article, Ayub Rana, innercircletrader.net | The whole of Strategy 02: the 19:00–00:00 NY range, the midnight open as a reference, the sweep, the MSS requirement, the 10–20 pip stop buffer, the LRLR target, the common-mistakes list. |
| `pdf/Goldmine-Asian-Session-Strategy_medium-FXM.pdf` | Medium article, "FXM Brand (Stephen M.)", Coinmonks, June 2025 | The Tokyo-consolidation framing and the tight-stop / 1:3 target convention. Also the "$18,500" and "80% win rate" claims analysed in Strategy 02. |
| `pdf/Asian-Session-Ultimate-Guide_medium-FXM.pdf` | Medium article, same author, September 2025 | A second, *different* session definition (22:00–08:00 GMT) from the same author, plus the five-step "Goldmine" sequence. |

## The video sources

Referenced in the original brief; not archived here because they are not mine
to redistribute. They are the same 9:30 and Asian-range material in video form
and were used only to corroborate the written rules:

```
https://youtu.be/C1Yzux4xo5Q          9:30 model
https://youtube.com/shorts/Mf7wSP7ybGo
https://youtu.be/RhsIR90KffM
https://youtu.be/wOllmfvfjx0
https://youtu.be/hMl4Gdl7jBA          Asian range / liquidity sweep
https://youtu.be/GfxScm82JHM
```

## What the sources agree on

- A reference range formed in a fixed time window, marked by its high and low.
- Execution dropped to a lower timeframe (M1–M5).
- A structural stop, placed at a level rather than a fixed distance.
- A fixed reward-to-risk target, usually 2:1 or 3:1.
- A hard time window, after which the setup has expired.

Those five points are the strategy. They survived into the code unchanged.

## What the sources disagree on, and how it was resolved

**Session times.** Four descriptions of "the Asian session" across the
documents, two of them from the same author, given variously in NY local time
and in GMT with no daylight-saving note. Resolved in favour of the ICT
definition, 19:00–00:00 NY, with the disagreement tabulated in
`../strategies/00-session-clock.md` and every alternative reachable through the
raw time inputs.

**Direction.** The 9:30 material trades the break *outward*. The Asian material
trades the reversal *inward*. Same kind of level, opposite trades, both with
winning screenshots. Resolved by not resolving it: both are implemented, the
mechanism that lets both appear to work is explained in `strategies/02`, and
the direction question is pushed onto an explicit, testable bias filter.

**The retest.** Every source teaches break → retest → confirmation candle as
the disciplined entry. Testing across 165,336 trades found it lowered the win
rate (33.0% → 31.9% on holdout, p < 0.001). Resolved by making the direct
break the default and shipping the retest as a selectable model, so the finding
can be replicated rather than believed.

## What none of the sources mention

Worth listing, because these are the things that decide whether the strategy
works and not one document raises them:

1. **Daylight saving.** Every source anchors to New York and none notes that
   this shifts twice a year against a fixed-offset broker. One commenter
   noticed independently and got an answer that did not address it.
2. **Spread at the open.** The 09:30–09:35 window is the widest spread of the
   day on most instruments. No source states a cost assumption, so no result
   in any of them can be checked.
3. **What the sample size is.** Trades are reported; sessions are not. Twenty
   trades over four mornings is four data points.
4. **How many variants were tried** before the published one.
5. **The losing months.**

Those five omissions are why the forensics script exists, and why its gates
are the ones they are.

## On reading vendor material

Two of the four documents sell something — an eBook, a broker referral, a
course. That does not make their observations wrong; the Asian-range structure
is real and the tight-overnight-consolidation description is accurate. It does
mean every *number* in them is marketing until your own journal produces a
different one.

The arithmetic on the headline claim is in `../strategies/02`, and it takes one
line: 80% at 1:3 is +2.20 R per trade, which compounds a $1,000 account past
$220,000 inside a year. The claim refutes itself without anyone needing to
doubt the author's honesty.
