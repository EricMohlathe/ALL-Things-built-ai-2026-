# GODMODE Master EA Library (MT5 / MQL5)

A library of **mechanical strategy EAs**, each an isolated, individually-backtestable trading edge, sharing one engine (`Include/GODMODE/GODMODE_Core.mqh`). Built to grow small accounts ($10–$100) with strict survival rules and a journal that lets you *prove* which edges actually work on your data.

> **Read this first — the honest frame.** Your own build brief (§21, Appendix A) and one of your own attached scripts (*"Proof that iFVGs have no edge"*) say it plainly: **sustained 80–100% win rates are not real** at retail volume. Renaissance Medallion runs ~71%. The money in flipping a small account comes from **asymmetric R:R (2–5R) + survival + many uncorrelated setups compounding**, *not* a magic hit rate. This library is built to find and exploit the *real* edges and to keep you alive long enough to compound them. Anything promising 95% is selling the survivor's story.

---

## 1. What's built — 26 ARCHETYPES COMPLETE

| File | Archetype | Status |
|------|-----------|--------|
| `Include/GODMODE/GODMODE_Core.mqh` | Shared engine: sizing, sessions, guards, trade mgmt, journal, OB/FVG helpers | ✅ |
| `Experts/GODMODE/GM01_OpeningRangeBreakout.mq5` | Opening Range Breakout (ORB) | ✅ |
| `Experts/GODMODE/GM02_SessionSweepReversal.mq5` | Liquidity Sweep → Reclaim (Judas / CRT / Power-of-3) | ✅ |
| `Experts/GODMODE/GM03_FVGEntry.mq5` | Fair Value Gap mitigation (trend-aligned) | ✅ |
| `Experts/GODMODE/GM04_OrderBlockReturn.mq5` | Order Block return | ✅ |
| `Experts/GODMODE/GM05_ICTUnicorn.mq5` | Unicorn — Order Block + FVG overlap | ✅ |
| `Experts/GODMODE/GM06_WyckoffSpring.mq5` | Wyckoff Spring / Upthrust | ✅ |
| `Experts/GODMODE/GM07_VWAPMeanReversion.mq5` | VWAP / Value-Area band fade (AMT) | ✅ |
| `Experts/GODMODE/GM08_MomentumDisplacement.mq5` | No-wick / displacement continuation | ✅ |
| `Experts/GODMODE/GM09_OrderFlowAbsorption.mq5` | CVD divergence + absorption (TICK DATA ONLY) | ✅ |
| `Experts/GODMODE/GM10_PowerOfThree_CRT.mq5` | Power-of-3 / CRT with CISD confirmation + SD target | ✅ |
| `Experts/GODMODE/GM11_SilverBullet.mq5` | ICT Silver Bullet (macro window + sweep + FVG) | ✅ |
| `Experts/GODMODE/GM12_OTE.mq5` | Optimal Trade Entry (Fib 0.62–0.79, trend) | ✅ |
| `Experts/GODMODE/GM13_PriceAction.mq5` | Pin bar / engulfing / inside-bar (Nial Fuller) | ✅ |
| `Experts/GODMODE/GM14_TurtleSoupSFP.mq5` | Turtle Soup / Swing Failure Pattern (sweep + reclaim) | ✅ |
| `Experts/GODMODE/GM15_SupplyDemand.mq5` | Supply & Demand zones (RBR/DBR/DBD/RBD base return) | ✅ |
| `Experts/GODMODE/GM16_MarketStructure.mq5` | Market structure BOS (continuation) / CHoCH (reversal) | ✅ |
| `Experts/GODMODE/GM17_InitialBalance.mq5` | Initial Balance breakout (market-profile IB extension) | ✅ |
| `Experts/GODMODE/GM18_Harmonic.mq5` | Harmonic XABCD (Gartley / Bat / Butterfly / Crab) | ✅ |
| `Experts/GODMODE/GM19_RSI2MeanReversion.mq5` | Connors RSI(2) pullback in long-EMA trend | ✅ |
| `Experts/GODMODE/GM20_GapFade.mq5` | Opening-gap fade-to-close **or** gap-and-go | ✅ |
| `Experts/GODMODE/GM21_PrevDayLevels.mq5` | Prev-day/week H/L sweep + reclaim (stop-hunt fade) | ✅ |
| `Experts/GODMODE/GM22_EMAPullback.mq5` | EMA-stack trend, pullback-and-reclaim continuation | ✅ |
| `Experts/GODMODE/GM23_OpeningGapCE.mq5` | ICT NDOG/NWOG gap midpoint (consequent encroachment) | ✅ |
| `Experts/GODMODE/GM24_SMTDivergence.mq5` | SMT divergence vs a correlated pair | ✅ |
| `Experts/GODMODE/GM25_BreakoutRetest.mq5` | Range break, enter on the retest that holds | ✅ |
| `Experts/GODMODE/GM26_ConfluenceStack.mq5` | **Meta-edge:** fire only when N layers agree (4–5 floor) | ✅ |

All are standalone refactors of the families in `GODMODE_OFEA_MASTER_COMPENDIUM.md` Part 7 (plus the ICT/SMC/PA concepts from the supplied PDFs & scripts), each individually testable. **GM09 requires real tick data** (synthetic ticks make delta/CVD meaningless — the #1 cause of the original GODMODE backtest failure).

### Standard-deviation trading
- **GM07** fades *true statistical* VWAP std-dev bands (mean-reversion).
- **GM10** offers an **SD / measured-move projection** target (`TP Type = 1`, `SD Mult`) — projecting a multiple of the manipulation range beyond the opposite edge (Quarterly-Theory / Lumi style). The helper `GM_SDExtension()` in the engine is reusable as a TP basis in any EA.

### ChartFanatics / Roboquant / Casper / social creators
Their published systems *are* the attached scripts and PDFs, already mechanized: ORB (GM01), session sweep / CRT / PO3 (GM02, GM10), FVG/iFVG (GM03, GM11), Order Block (GM04), Unicorn (GM05), Wyckoff (GM06), VWAP (GM07), no-wick momentum (GM08), order flow (GM09), Silver Bullet (GM11), OTE (GM12), classic price action (GM13). TikTok/IG/YouTube creators teach these same edges — paste a *specific* rule set and it slots into the relevant EA. No fabricated per-person systems.

---

## 3. The 150-trader → archetype map (nothing is lost)

The big list of traders is **not 150 distinct edges**. Mechanically they collapse into the 9 archetypes above. Here's where each name's *actual mechanical method* lives. (Names marked ⚠ are **discretionary / fundamental / instrument-specific** and have no mechanizable intraday rule set — they're listed for honesty, not because an EA can faithfully reproduce them.)

**GM01 Opening Range Breakout** — Casper SMC, Ginger, JDUB, RP Profits, TomTrades, Trade With PAT, Patrick Wieland, Ross Cameron (ORB side), Qullamaggie (breakout/episodic pivot logic, adapted).

**GM02 Sweep → Reclaim (Judas/CRT/PO3/AMD)** — TJR (Tyler Riches), Michael J. Huddleston (ICT), ICT Inner Circle / ICT2022 students, Smart Money Mavericks, A.M. Trades, FX Evolution, Photon Trading, Justin Werlein, T Trades, Sir Pickle, Hydra Thahmid, Chadio, Trader Yush, ICT Tradervic, Tori Trades, Riley Coleman.

**GM03 FVG / iFVG** — ICT FVG model, Casper FCR-FVG, Jdun Trades, The Trading Geek, LuxAlgo (FVG tooling), imbalance educators.

**GM04 Order Block return** — Astro FX (Aman Natt / Shaun Lee), Akil Stokes, Etienne Crete, most generic "SMC" educators, Train and Trade.

**GM05 ICT Unicorn (Breaker+FVG)** — ICT advanced students, Bao The Whale, Will Sebastian.

**GM06 Wyckoff Spring/Upthrust** — Wyckoff 2.0 (Villahermosa), Tom Crown, Gareth Soloway (reversal/level reclaim side), Rader Trader.

**GM07 VWAP / Value-Area mean reversion** — Fabio Valentini (AMT), Carmine Rosato (LVN/VP context), SMB Capital (Mike Bellafiore, Merritt Black — VWAP/level reclaim), Andrea Cimi, Vincent Desiano.

**GM08 Momentum / displacement continuation** — No-Wick momentum, Oliver Velez, Adam Khoo (trend-following side), Rayner Teo (momentum/pullback), Trading Rush, The Moving Average, Steven Hart (Trading Channel), UKspreadbetting.

**GM09 Order-flow absorption / CVD** — GODMODE_OFEA core, Carmine (order flow), ATAS/Bookmap-style footprint educators, ChartFanatics order-flow cohort.

**⚠ Not mechanizable into a faithful intraday EA** (discretionary macro, fundamentals, penny-stock microcaps, or pure market-commentary):
George Soros, Stanley Druckenmiller, Bill Lipschutz, Andrew J. Krieger, Peter Brandt (discretionary classical charting — partially GM01/GM06), Raoul Pal, Anton Kreil, Jason Stapleton (macro/education); Tim Sykes, Steven Dux, Tim Grittani, Alex Temiz, Nathan Michaud, Kunal Desai, Cameron Fous, Ricky Gutierrez, Stock Moe, Kyle Dennis, Jeff Bishop, Ben Sturgill (US small-cap/penny momentum — needs equities + Level 2, not FX/index EAs); Roaring Kitty, Davey Day Trader, Meet Kevin, Graham Stephan, Andrei Jikh (positions/commentary, not systems); and the crypto-call channels (Crypto Banter, BitBoy, Altcoin Daily, Lark Davis, MMCrypto, Pentoshi, GCR, James Wynn, Andrew Kang, Coin Bureau, DataDash, Benjamin Cowen, CryptoCred, Wolf of All Streets, Anthony Pompliano, Krown's Crypto Cave, Jacob Crypto Bury, Sheldon Evans, etc. — discretionary directional calls). Their *risk discipline* is folded into the shared guards; their *entries* are not a fixed rule set.

> Bottom line: **9 EAs faithfully mechanize the tradeable methods of the entire list.** Building "150 separate EAs" would mean building the same 9 edges 150 times with cosmetic renames — which is exactly the un-diagnosable mess the compendium warns against.

---

## 4. Risk modes (set per EA via `InpRiskMode`)

| Mode | Default risk % | Use |
|------|----------------|-----|
| `RISK_CONSERVATIVE` | 1% | Default. Capital protection first. |
| `RISK_AGGRESSIVE` | 3% | Faster compounding, meaningful drawdowns. |
| `RISK_FLIP` | 8% | $10→big attempts. **Relaxes the min-lot guard. Expect frequent blow-ups.** |

**$10-account reality:** on most brokers the minimum lot (0.01) risks far more than 1% of $10. `GM_CalcLots` *rejects* such trades in Conservative/Aggressive mode (logged as `SKIP_SIZE`). Flip mode lets them through. This is the honest mechanics of micro-account trading — consider a cent/micro account or a broker with nano-lots.

---

## 5. Install (MT5)

1. In MT5: **File → Open Data Folder**.
2. Copy `Include/GODMODE/GODMODE_Core.mqh` → `MQL5/Include/GODMODE/`.
3. Copy `Experts/GODMODE/*.mq5` → `MQL5/Experts/GODMODE/`.
4. In MetaEditor, **Compile** each `.mq5` (must be zero errors).
5. Attach one EA per chart. Set `InpMagic` unique per EA per symbol. Enable **Algo Trading**.
6. Set session-hour inputs to *your broker's server time* (check the clock in Market Watch).

CSV journals are written to the **common** files folder: `File → Open Data Folder → ... → Terminal/Common/Files/GODMODE_GMxx_*_log.csv`.

---

## 6. Backtest protocol (do this before trading a cent)

Per the compendium Part 10 and brief §14/§21.3:

1. **One EA, one symbol, tick data, ≥6 months**, Conservative mode. MT5 Strategy Tester → "Every tick based on real ticks."
2. Require **≥200 trades** before trusting any win-rate number (smaller samples are noise — §21.3 survivorship trap).
3. Record per EA: trades, win %, avg R, **profit factor (target ≥1.5)**, max DD, recovery factor.
4. **Rank by expectancy and profit factor, NOT win rate** (§21.4): a 60%/+1.5R system beats an 80%/+0.6R one.
5. Check **drawdown correlation** between EAs (compendium Part 10 / brief §23.3). Only run multiple EAs together if they *don't* lose at the same time.
6. Retire any archetype that can't clear PF 1.3 on your data. Some will fail — that's the point of testing (remember: *"iFVGs have no edge"*).

---

## 7. Path to growing a small account (the realistic version)

- Trade the 2–3 archetypes that **prove out** on *your* symbol/broker, not all 9.
- Keep R:R ≥ 2. Let the trade manager bank partials and trail.
- Compound: risk a fixed % of *current* equity (already how `GM_CalcLots` works) — never martingale.
- Accept variance. Even a real 65%/+2R edge has losing streaks that feel like the strategy is broken.
- Flip mode is a *lottery ticket*, not a plan. If you use it, use money you can lose entirely.
