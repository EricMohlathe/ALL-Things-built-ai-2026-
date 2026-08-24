# Isaiah 60:22

> *"A little one shall become a thousand, and a small one a strong nation:
> I the LORD will hasten it in his time."*

A session-range trading workspace. Two strategy families, one execution
engine, one evidence standard.

The directory is named `Isaiah-60-22` rather than `Isaiah 60:22` because a
colon is an illegal path character on Windows and would break the checkout on
any Windows machine or MT5 data folder. The name of the project is
Isaiah 60:22; the folder spells it safely.

---

## What is in here

| Path | What it is |
|---|---|
| `strategies/00-session-clock.md` | The clock. Read this before anything else — every rule below is anchored to New York local time, and that is not a fixed GMT offset. |
| `strategies/01-ny-0930-opening-range.md` | The 9:30 AM New York opening-range model. Mark the first 5-minute candle, trade the break. |
| `strategies/02-asian-range-liquidity-sweep.md` | The Asian-range / 10:00 AM liquidity-sweep model. Mark the overnight range, trade the sweep and the structure shift. |
| `strategies/03-risk-and-evidence-protocol.md` | Position sizing, the daily kill-switches, and the six gates a variant must clear before it sees live money. |
| `strategies/04-the-ceiling.md` | What win rate, payout, profit factor and trade volume can actually be had at the same time — and the three tools built to get as close to that ceiling as the market allows. |
| `MT5/` | The MetaTrader 5 build: two Expert Advisors over one shared core (`Isaiah6022_Core.mqh`). |
| `cTrader/` | The cTrader build: the same two strategies as self-contained cBots. Reads UTC directly, so there is no broker-offset input to get wrong. |
| `SessionRange_Forge/` | The measurement half. `srf_forensics.py` grades any journal against six gates; `target_curve.py` finds where the win-rate/payout dial should sit on your data; `pf_lab.py` raises profit factor while holding a win-rate floor; `portfolio.py` combines every stream and reports effective breadth. Plus the original five-model research EA. |
| `journal/` | The manual trade log and the pre-flight checklist, for the sessions you trade by hand. |
| `sources/` | The source documents these rules were extracted from, archived as PDFs, with a note on what each one actually claims and what none of them mention. |

### The four robots

| Strategy | MT5 | cTrader |
|---|---|---|
| 01 — 9:30 NY opening range | `MT5/Experts/Isaiah6022_NY0930_ORB.mq5` | `cTrader/Isaiah6022_NY0930_ORB.cs` |
| 02 — Asian range liquidity sweep | `MT5/Experts/Isaiah6022_AsianSweep.mq5` | `cTrader/Isaiah6022_AsianSweep.cs` |

All four write **the same journal CSV schema**, so one forensics script grades
every run and you can diff the two platforms against each other. Where they
disagree, you have found either an execution cost or a bug — and both are
worth knowing. See Part 4 of `strategies/03`.

---

## The one-paragraph version

Both strategies trade the same structure: a **reference range** formed in a
known time window, and a **directional decision** made when price leaves it.
The 9:30 model uses a five-minute range at the New York equities open and
trades the break. The Asian model uses a five-hour overnight range and trades
the *reversal* after price pokes through it. They are opposite reactions to
the same event, which is the first thing worth knowing about them — see
`strategies/02` for why both can show winning screenshots.

---

## Start here

```bash
# 1. Read the clock document. Twenty minutes now saves months of trading
#    the wrong window.
open strategies/00-session-clock.md

# 2. Watch the forensics tool correctly refuse to certify a known coin flip.
#    If it passes something later, that means something.
cd SessionRange_Forge
pip install numpy pandas matplotlib
python3 srf_forensics.py --demo --variants 12 --plots demo.png

# 3. Read the audit file — the full rule extraction and the evidence behind
#    the choices baked into the EA defaults.
open SessionRange_Forge/SRF-2026-01-audit-file.html

# 4. Install the robot for your platform and get a baseline.
open MT5/README.md          # or cTrader/README.md
```

Then pick one strategy, one instrument, and one entry model. Backtest it,
journal it, and run the journal through the forensics script before you
change a single parameter. The number of variants you try is an input to the
statistics, and it only goes up.

Each strategy ships with a **falsification run** — the second backtest you
should do, before any tuning, which tests the claim the strategy is built on.
For the opening range it is the retest; for the sweep it is the bias filter.
Both are one parameter change away and both are described in the strategy
documents.

---

## What the evidence already says

These are findings from the audit file, reproduced here so nobody has to be
told twice:

- **The retest rule costs money.** Break → retest → confirmation candle, the
  step every tutorial calls the secret, measurably *lowered* the win rate in
  testing (33.0% → 31.9% on holdout, p < 0.001). It makes you enter later, at
  a worse price, with a wider stop. The EA ships with `MODEL_BREAK_DIRECT` as
  the default for that reason. `MODEL_RETEST` is included so you can replicate
  the finding on your own instrument rather than take anyone's word for it.
- **A published opening-range strategy does work** (Zarattini, Barbon & Aziz
  2024, >7,000 stocks, 2016–2023) — but it deletes the retest, deletes the
  confirmation candle, sets direction mechanically, holds to the close, and
  filters hard on relative volume. The edge lives in *selection and exit*, not
  in the entry trigger.
- **The two Asian-range sources trade the same level in opposite directions**
  and both publish winning screenshots. Osler's order-book research explains
  how: take-profit orders cluster *at* a round level and reverse price, stop
  orders cluster *just beyond* it and accelerate price. The sweep predicts
  volatility, not direction.
- **The vendor "80% win rate at 1:3" claim refutes itself.** That implies
  +2.20 R per trade. At 1% risk over 250 trades it turns $1,000 into roughly
  $223,000 in a year. Nobody selling a $40 PDF has that.

---

## Not financial advice

Two studies on complete exchange records found that 97% of persistent retail
day traders lost money, and under 1% were reliably profitable after fees. The
durable asset in this repository is not either strategy — it is the evidence
standard in `strategies/03`, which works on any strategy, including the next
one somebody sells you.
