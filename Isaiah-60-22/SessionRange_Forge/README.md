# Session-Range Forge

Three artifacts. One question: does the 9:30 / Asian-range family of strategies
have an edge on *your* instrument at *your* costs.

| File | What it is |
|---|---|
| `SRF-2026-01-audit-file.html` | The compendium. Rule extraction from all six sources, the evidence, and the opinion. **Read this first.** |
| `GODMODE_SessionRange_Forge.mq5` | MT5 Expert Advisor. Five entry models behind one dropdown, so the taught version and the restated version are the same code. Writes a forensic CSV. |
| `srf_forensics.py` | Reads that CSV and runs the five gates that separate an edge from a coin flip. |

---

## The short version of the findings

- The strategy **as taught** — break, retest, wait for a confirmation candle,
  fixed 2:1 — tested across 165,336 trades produces a win rate that tracks the
  payout-implied break-even at every target size from 1:1 to 10:1. That is the
  signature of no directional information.
- The **confirmation candle rule** — the thing every video calls the secret —
  measurably lowered the win rate (33.0% → 31.9% on holdout, p < 0.001). It makes
  you enter later at a worse price with a wider stop.
- A **published, peer-reviewed** opening-range strategy does work (Zarattini,
  Barbon & Aziz 2024, >7,000 stocks, 2016–2023). It deletes the retest, deletes
  the confirmation, sets direction mechanically, holds to the close, and filters
  hard on relative volume. The edge lives in selection and exit, not entry.
- The two Asian-range sources trade the same level in **opposite directions**.
  Osler's order-book research explains why both can show winners: take-profit
  orders cluster *at* a level and reverse price, stop-losses cluster *just beyond*
  it and accelerate price. The sweep predicts volatility, not direction.
- The vendor "80% win rate at 1:3" claim implies +2.20 R per trade — at 1% risk
  over 250 trades that turns $1,000 into $223,000 in a year. The claim refutes
  itself.

---

## Run order

```bash
# 1. Watch the tool correctly refuse to certify a known coin flip.
python3 srf_forensics.py --demo --variants 12 --plots demo.png
```

```
# 2. MT5 → File → Open Data Folder → MQL5/Experts/
#    Drop in the .mq5, compile with F7, attach to a chart.
#
#    InpPreset          = PRESET_NY_ORB_0930
#    InpModel           = MODEL_BREAK_DIRECT      ← the restated version
#    InpBrokerGMTOffset = your broker's WINTER offset (check it, don't guess)
#    InpRiskPercent     = 0.5
#    InpWriteJournal    = true
#    InpRunTag          = "orb_direct_v1"          ← change every run
#
#    Strategy Tester: "Every tick based on real ticks", 2+ years, REAL spread.
```

```bash
# 3. Journal lands in MQL5/Files/SRF_journal.csv. Test it.
python3 srf_forensics.py SRF_journal.csv --target-r 2.0 --variants 1 --plots out.png
```

```
# 4. Now re-run step 2 with InpModel = MODEL_RETEST, everything else identical.
#    You are replicating finding C-1.1 on your own market. If retest is worse,
#    you have your own evidence and you can stop taking anyone's word for it.
```

```bash
# 5. Every additional variant you try — parameter, symbol, timeframe, model —
#    increments the count. Be honest about it; the correction is brutal by design.
python3 srf_forensics.py SRF_journal.csv --variants 12
```

Then forward-test on demo for 40+ sessions before any live capital. The forward
test is the only sample nobody tuned on.

---

## The five gates

| Gate | Fails when |
|---|---|
| **Sample size** | Fewer than 100 distinct sessions. Trades are not the sample size — sessions are. |
| **Break-even gap** | Win rate at or below `1/(1+R)`. The payout sets the bar; the entry has to clear it. |
| **Day-clustered CI** | Lower bound of the session-bootstrap confidence interval touches zero. |
| **Concentration** | The best two sessions carry over half the gross profit. Two lucky days, not a system. |
| **Cost survival** | Expectancy dies at or below the cost you actually pay. |
| **Out of sample** | Held-out sessions fail at the Šidák-adjusted alpha for the number of variants you tried. |

A failed gate is not a prompt to keep tuning. Tuning until it passes is the
mechanism by which a coin flip becomes a backtest.

---

## Notes

- **Clock.** The EA converts broker time to New York time with the real US DST
  rule. Every source anchors to New York; none mention that this shifts twice a
  year against a fixed-offset broker. A backtest that ignores it trades the wrong
  window for months of every year.
- **On the M1 Mac.** MT5 has a native macOS build and the Strategy Tester works.
  Multi-core optimisation is limited — use the Windows-on-ARM VM for long
  optimisation runs, native for single backtests.
- **Not financial advice.** Two studies on complete exchange records found 97% of
  persistent retail day traders lost money and under 1% were reliably profitable
  after fees. The transferable asset here is the evidence standard, which works
  on any strategy — including the next one somebody sells you.
