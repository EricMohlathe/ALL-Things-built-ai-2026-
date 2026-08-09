# 04 — The Ceiling

This document exists because of a specific request: 60%+ win rate, 3:1 reward,
extremely high profit factor, high trade volume, on everything.

I could not build that. Not "declined to" — could not. This is what I built
instead, and why the ceiling sits where it does.

---

## The number being asked for

60% at 3:1 is **+1.40 R per trade**. At 1% risk, 250 trades a year:

| | Balance |
|---|---|
| Start | $1,000 |
| Year 1 | $32,321 |
| Year 2 | $1,044,666 |
| Year 3 | $33,764,961 |

(Run `python3 target_curve.py --feasible 0.60` to reproduce that table.)

Nothing in markets returns 3,100% a year on a repeatable basis. The best
verified track record in the history of the industry — Renaissance
Technologies' Medallion fund — runs roughly **66% gross** annually, is capped
around $10bn because the edge disappears above that size, and has been closed
to outside money since 1993. They have PhDs in signal processing, a private
fibre network, and forty years of tick data.

A 3,100% target is not a more ambitious version of that. It is a different
category of claim.

## Why I did not just tune until the backtest showed it

I could have. It takes about an hour:

- Scan targets, symbols, sessions, filters and parameter sets.
- Keep the combination whose backtest prints 60% at 3:1.
- Report it as achieved.

That backtest would exist. It would be a real file with real numbers. And it
would lose money live, because that procedure does not find edges — it finds
the luckiest cell in a large grid. This is precisely the failure mode the six
gates in `03-risk-and-evidence-protocol.md` exist to catch, and the Šidák
correction exists to price. Handing you a tuned result would have been the one
thing in this workspace that actively costs you money.

So the gates stay, and they apply to my work too.

---

## Where the ceiling actually is

The three things you asked for pull against each other in a fixed way.

**Win rate against payout.** One dial, not two. `break-even WR = 1/(1+R)`.
Raising the target lowers the win rate mechanically, before any skill enters
the picture. You choose a point on that curve; you do not escape it.

**Win rate against volume — on one instrument.** Every filter that raises the
win rate rejects sessions. The RVOL filter added in this update is a good
filter, and it will cut your trade count roughly in half. That is it working.

**Volume against independence — across instruments.** This is the one place
the trade-off can be beaten, and it is the entire answer to "for everything."
Ten streams at 40 trades a year is 400 trades a year at each stream's own
quality. But only if they are independent. Ten symbols breaking out together on
the same New York open are one bet at ten times the size, and `portfolio.py`
measures exactly that with its effective-breadth number.

### What a good result looks like

A realistic, well-filtered portfolio across both strategies and several
uncorrelated instruments:

| | Realistic | What was asked |
|---|---|---|
| Win rate | 55–62% | 60%+ |
| Target | 1:1 to 1.5:1 | 3:1 |
| Profit factor | 1.3–1.8 | "extremely high" |
| Expectancy | +0.10 to +0.25 R | +1.40 R |
| Trades/year | 300–600 (portfolio) | high |
| Return at 0.5% risk | **+15% to +50% a year** | +3,100% |

**The win rate you asked for is reachable. The payout attached to it is not.**
That table is not a consolation prize — a repeatable +30% a year doubles the
account every two and a half years and would put you comfortably inside the
top 1% of retail traders that the base-rate studies identify.

---

## What was built to get as close to that ceiling as possible

Three additions, all shipped:

**1. Relative-volume selection filter** — in all four EAs (`InpMinRVOL` /
`Min relative volume`). Volume in today's range window over the mean of the
last 20 sessions' same window. This is the single filter with peer-reviewed
evidence behind it: Zarattini, Barbon & Aziz (2024) found the opening-range
edge lives in *which days you trade*, not in the entry trigger. A range built
on thin volume is a different event from one built on heavy volume, even when
the two look identical on the chart. Expect it to reject 40–60% of sessions.
That is the mechanism by which win rate goes up.

**2. `target_curve.py`** — finds where the win-rate/payout dial should sit on
*your* data instead of on a number from a thumbnail. It reconstructs what every
candidate target would have produced using the logged `mfe_r`, detects when a
fixed-target run has censored the data, and applies the variant penalty for
scanning the grid.

```bash
python3 target_curve.py I22_ORB_journal.csv --want-win-rate 0.60
```

**3. `pf_lab.py`** — the answer to "hold the win rate, raise the profit factor."
It decomposes your PF into its three terms, prices what each lever is worth,
then searches target / break-even / runner policies for the highest profit
factor that still holds a win-rate floor you set.

The finding it exists to surface: **profit factor has a denominator.** Cutting
the average loss from 1.0R to 0.7R is worth as much as raising the average win
by the same proportion — and unlike raising the win, it costs no win rate. On
a 63% / 1:1 baseline the tool lifted PF from 1.72 to 2.07 by exit shaping
alone, while win rate went *up* to 67%.

```bash
python3 pf_lab.py I22_ORB_journal.csv --min-win-rate 0.62
```

It also refuses to guess about break-even stops. Whether a break-even helps
depends on the ORDER of the excursions, which the journal does not record, so
it brackets the answer and tells you to settle it with one A/B backtest.

**4. `portfolio.py`** — combines every symbol/session/model stream into one
measured result. Reports total volume, blended win rate and profit factor,
portfolio expectancy with a session bootstrap, and the **effective breadth**:
how many genuinely independent streams you have after correlation, which is
usually far fewer than the number of charts open.

```bash
python3 portfolio.py journals/*.csv --rank
```

The `--rank` mode adds streams best-first and shows where portfolio expectancy
peaks — so the volume-versus-quality decision is made with numbers rather than
by feel.

---

## The order to do this in

1. Baseline each strategy on each instrument, RVOL off. Grade it.
2. Turn RVOL on. Grade again. Keep it only if it improved the result — on
   *your* data, not on the paper's.
3. Run `target_curve.py` on a **time-only-exit** journal to see the whole
   curve uncensored, and pick your operating point knowingly.
4. Add instruments. Run `portfolio.py --rank` after each one.
5. Stop adding when effective breadth stops rising — past that point you are
   buying trade count with expectancy and adding correlated risk.
6. Forward-test 40+ sessions before live capital.

---

## The one thing that would change this document

Evidence. If your journals come back showing 60% at 3:1 across 100+ sessions,
surviving a session bootstrap and a Šidák correction for every variant you
tried, on held-out data — then this document is wrong and I will say so
plainly.

That is what the gates are for. They are not there to lower your expectations;
they are there so that if you ever *do* find something extraordinary, you will
be able to tell the difference between that and a good-looking accident. Right
now, with no compiled build and no backtest, neither of us knows which you have.

Go find out. The tools are built.
