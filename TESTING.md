# GODMODE Master Library — Testing & Validation Protocol

This is the filter that turns 9 *candidate* edges into the 2–3 that actually make you money. **Do not trade a cent of real capital until an EA has cleared this.** Both platforms (MT5 + cTrader) follow the same protocol; settings for each are below.

> The single most important rule, from your own brief §21.4: **rank by expectancy and profit factor, not win rate.** A 60% / +1.8R system beats an 80% / +0.5R one. Win rate is the vanity metric that blows accounts.

---

## 0. Why most of these will (and should) fail

You have 9 archetypes. On any given symbol/timeframe, expect maybe **2–4 to show real edge** and the rest to be break-even or negative. That is the *correct, healthy* outcome — your own folder contains *"Proof that iFVGs have no edge."* The job of testing is to find the survivors, not to make all 9 "work." Forcing a losing archetype to pass by curve-fitting parameters is how you lose money slowly.

---

## 1. Data quality (non-negotiable)

| EA | Data needed |
|----|-------------|
| GM01–GM08 | M1/M5/M15 OHLC; "real ticks" preferred but bar data acceptable for a first pass |
| **GM09 (Order Flow)** | **Real tick data ONLY.** On synthetic/bar-modelled ticks the delta & CVD are meaningless — this was the #1 cause of the original GODMODE_OFEA backtest blow-up. If you can't get real ticks, do not deploy GM09. |

- **MT5:** Strategy Tester → Modelling = **"Every tick based on real ticks."** Download history first (the more, the better).
- **cTrader:** Backtesting → Data = **"Tick data (accurate)"** (m1-bars-from-server is NOT enough for GM09).

---

## 2. The protocol (run per EA, in isolation)

1. **One EA, one symbol, one timeframe.** Never test the portfolio first — you can't attribute results.
2. **Risk Mode = Conservative (1%).** Always validate on Conservative. Aggressive/Flip only change sizing, not the edge.
3. **Period ≥ 6 months** (12+ preferred), spanning different regimes (trend + range).
4. **Initial deposit:** test at a realistic size first (e.g. $1,000) to judge the *edge* cleanly, THEN re-test at $10–$100 to see how the min-lot guard throttles trade count (see §6).
5. **≥ 200 trades** before you trust any number (brief §21.3 — fewer is noise; a 30-trade 80% is a coin-flip dressed up).
6. Record the scorecard (§4). Move to the next EA.

---

## 3. Acceptance criteria (a survivor must clear ALL)

| Metric | Threshold | Why |
|--------|-----------|-----|
| Trades | ≥ 200 | statistical validity |
| Profit Factor | ≥ 1.5 | gross win / gross loss |
| Expectancy / trade | > 0 (target ≥ +0.3R) | the actual edge |
| Max Drawdown | ≤ 20% | survivability |
| Recovery Factor | ≥ 2.0 | net profit / max DD |
| Win rate | *reported, not a gate* | sanity only |

If an EA misses any, it's **benched** — not deleted, not curve-fitted to pass. Re-test it on a different symbol/session before giving up on it (some archetypes only work on specific instruments — see §7).

---

## 4. Per-EA scorecard (copy one block per EA per symbol)

```
EA:            GM0_  (name)
Symbol / TF:   ______ / ____
Period tested: ____ to ____   (months: __)
Risk mode:     Conservative 1%
Data mode:     real ticks? Y/N

Trades:            ____      (>=200?  Y/N)
Win rate:          ____ %    (reported only)
Profit Factor:     ____      (>=1.5?  Y/N)
Avg win / avg loss: __R / __R
Expectancy/trade:  ____ R    (>0?  Y/N)
Max Drawdown:      ____ %    (<=20%? Y/N)
Recovery Factor:   ____      (>=2.0? Y/N)

VERDICT:   SURVIVOR / BENCH / RETEST-ELSEWHERE
Notes:     ____________________________________
```

Keep the EA's own CSV journal (`GODMODE_GMxx_*_log.csv`, in MT5 Common/Files or cTrader My Documents) — it logs **skips too**, so you can see how often a setup *almost* fired (the denominator) and why it was rejected (`SKIP_SIZE`, `SKIP_RR`, `SKIP_SPREAD`).

---

## 5. Parameter tuning — do it right, or not at all

Over-optimisation is the fastest way to a backtest that lies. Rules:

1. **Tune ≤ 2 parameters at a time.** For most EAs the meaningful ones are: `RR`, the SL basis (ATR mult / padding), session hours, and the archetype's core threshold (e.g. `DispMult`, `BandSD`, `RangeATRMult`, `VolZThr`).
2. **Walk-forward, not in-sample.** Optimise on months 1–6, validate on months 7–12 *without re-touching*. If it falls apart out-of-sample, the "edge" was curve-fit.
3. Prefer **robust plateaus** over sharp peaks: a setting that works across a *range* of values beats a single magic number.
4. Don't optimise `RiskMode`/risk % for returns — that's sizing, it doesn't create edge (and the optimiser will always pick the riskiest = most fragile).

---

## 6. The $10-account reality check

After an EA is a SURVIVOR at $1,000, re-test at **$10, $50, $100**:

- Watch the trade count drop — the min-lot guard (`GM_CalcLots`) **skips** trades where the broker minimum lot would over-risk the account (logged `SKIP_SIZE`). This is *correct* behaviour, not a bug.
- If almost everything is skipped at $10: you need a **cent/micro account** or a broker with **nano-lots**, or you accept the guard and trade only the setups it allows.
- **Flip mode** (`RISK_FLIP`, 8%) relaxes the guard so trades fire. Understand what this means: a handful of losses in a row ends the account. Backtest Flip mode honestly and look at the **worst-case losing streak** in the results — that's your blow-up scenario, and it *will* happen eventually.

**Compounding math (honest):** growing $10→$5,000 is a 500× move. Even a genuine +0.5R/trade edge at 2 trades/day compounds over *months*, not a week — and only if you never hit the streak that ruins you. The library maximises your *real* odds; it cannot make 500× in a week anything other than a lottery ticket.

---

## 7. Suggested starting configs (then test, don't trust)

These are sensible *starting points* to test, matched to where each edge tends to live. Set `Offset Hours` so the session inputs match your intent (SAST = UTC+2; NY 09:30 = 14:30 UTC in winter).

| EA | Symbol(s) to try first | TF | Session focus |
|----|------------------------|----|----|
| GM01 ORB | US100, US500, XAUUSD | M5 | NY open (09:30 NY) |
| GM02 Sweep/Judas | EURUSD, GBPUSD, XAUUSD | M5/M15 | Asian range → London |
| GM03 FVG | XAUUSD, US100 | M5 | London + NY |
| GM04 Order Block | EURUSD, GBPUSD | M15 | London + NY |
| GM05 Unicorn | XAUUSD, US100 | M5/M15 | NY |
| GM06 Wyckoff | EURUSD, XAUUSD | M15 | any kill zone |
| GM07 VWAP fade | US100, US500 | M5 | NY (range days) |
| GM08 Momentum | XAUUSD, US100, US30 | M5 | London + NY |
| GM09 Order Flow | EURUSD, XAUUSD | M1/M5 | London + NY (TICK DATA) |

---

## 8. Building the portfolio (only after individual validation)

1. Take only the **SURVIVORS** from §3.
2. Compute **drawdown correlation** between them (do two survivors lose on the same days? compare their journals/equity curves). Two strategies that draw down together aren't diversification — they're one bet with extra commission.
3. Run **2–4 uncorrelated survivors** together, each with its own `Magic`/`Label` so they never touch each other's trades.
4. Total risk across all running EAs should respect the same daily-DD ceiling — consider lowering per-EA risk % when running several at once.
5. Re-validate the *combined* equity curve forward on demo for **2+ weeks at 0.25× size** before live.

---

## 9. One-line summary

Test each EA alone on tick data, demand ≥200 trades and PF ≥ 1.5, keep only survivors, never curve-fit a loser into a "winner," size for survival, and let uncorrelated edges compound. That is the entire difference between a library that grows an account and one that decorates a blown one.
