# GODMODE_OFEA — MASTER COMPENDIUM & SPLIT THESIS

A complete functional teardown of `GODMODE_OFEA..cs` (1,573 lines, single-file cTrader cBot), written so that each concept can be lifted out and rebuilt as its own standalone EA. Read this top-to-bottom once; thereafter use Part 7 (the split map) as your build worksheet.

---

## PART 0 — WHY THIS DOCUMENT EXISTS

`GODMODE_OFEA` is not one strategy. It is **~40 distinct edge-detection ideas** wired into a single decision pipeline that fires at most one trade per bar. Because every idea shares one score counter, one set of gates, one risk model and one position slot, the backtest cannot tell you *which idea made or lost money*. A losing setup and a winning setup are blended into a single equity curve. That is the core reason the backtest "went horribly wrong": you optimised and judged 40 things as if they were one.

The fix is **decomposition**: rebuild each setup (or each tightly-correlated cluster of setups) as its own EA with its own log, so each can be backtested, win-rated, and ranked in isolation. This document gives you (a) the full functional spec of every component, and (b) a concrete cut-list for the split.

> **Source authority.** The EA was built from `CLAUDE_CODE_BUILD_BRIEF.pdf` (24 pages, "GODMODE Order Flow Mastery skill v3.0 synthesis"). The brief's §0 explicitly mandated *"a single, indivisible build specification… Do not split it."* — i.e. the monolith was intentional. **Your current task reverses that mandate**, and you are correct to: §0's "indivisible" rule is what makes the backtest un-diagnosable. The brief also already contains the analytical scaffolding the split needs (see Part 10): documented per-setup win rates (§6), the survivorship-trap warning (§21.3), per-setup rolling-win-rate auto-disable (§22.8), and a cross-symbol/cross-setup correlation filter (§23.3).

---

## PART 1 — FILE TOPOLOGY (3 NAMESPACES)

The file is one `.cs` with three namespaces, intentionally layered:

| Namespace | Role | Lines (approx) |
|---|---|---|
| `GodmodeOfea.Enhanced` | Self-contained analytics primitives (no cTrader dependency except `Symbol`). CVD math, VWAP, regime HMM, Kelly sizing, price-action structs, probability scorer. | 18–282 |
| `GodmodeOfea` | The trading engine: order-flow, volume profile, footprint, sessions, HTF, risk, trade management, the 25 setup detectors, and the "god-level" ICT/SMC confluence modules. | 287–1187 |
| `GodmodeOfeaFinal` | The actual `Robot` (`GODMODE_OFEA_FINAL`). Holds all parameters, instantiates every module, runs `OnTick`/`OnBar`, scores setups, fires trades. | 1192–1573 |

**Dependency direction:** `Final` → `GodmodeOfea` → `GodmodeOfea.Enhanced`. The Enhanced layer is the most portable; the Final layer is the least.

---

## PART 2 — THE ENHANCED LAYER (analytics primitives)

These are stateless-ish helpers. Each is a candidate **shared library** that every split-out EA will reference (do **not** duplicate these per-EA — keep one copy).

### 2.1 `DeltaEnhanced` (lines 22–90)
Rolling buy/sell delta engine over a ring buffer of `lookback` bars (default 20).
- Maintains cumulative volume delta `Cvd`, normalised `CvdSlope`, and a z-score `ZScore` of the latest bar's delta vs. the window.
- `Climax`: true when `|ZScore| ≥ climaxThr` (default 2.0) — an exhaustion spike.
- `DeltaFlipped`: true when the latest bar's delta sign opposes any of the prior `flipBars` (default 3) bars — momentum reversal.
- `ClassifyRegime`: emits a `CvdRegime` enum — `TrendConfirming` (price & CVD move together), `Divergent` (opposite), `InverseDivergent` (flat price, strong CVD), `Neutral`.

**Edge it encodes:** order-flow momentum and price/flow divergence. This is the backbone of every CVD- and absorption-based setup.

### 2.2 `VWAP` (lines 92–114)
Session-anchored VWAP with standard-deviation bands. Resets each calendar day (`IsNewSession`). Provides `Value`, `Sd`, `Upper(k)`, `Lower(k)`, and `ZScore(price)`. Used as a mean-reversion reference and as gate **g8** in the composite probability.

### 2.3 `RegimeHMM` (lines 118–142)
A *pseudo*-HMM (it is actually a deterministic threshold classifier, not a probabilistic HMM). Maps `{cvdSlope, footImb, profileSkew, volZ}` to one of `{InitBuy, InitSell, Absorption, Rotation}` and tracks state-dwell time + transitions. Exposes `ExhaustionLongFromAbsorption` / `…Short…` — the prized "absorption after an aggressive push" reversal trigger.
**Caveat for splitters:** in the live code it's fed `_reg.Update(_dE.CvdSlope, 0, 0, _dE.ZScore)` — `footImb` and `profileSkew` are hard-wired to 0 (line 1361). So Absorption/Rotation classification is effectively running on half its inputs. Fix this when you split.

### 2.4 `KellySizer` (lines 144–158)
Full Kelly `f = (p(b+1)−1)/b`, fractional Kelly (× kappa, default 0.25), and `RiskPctFromKelly` capped at 2%. **Currently vestigial** — `EnhancedFireTradeIfReady` only *prints* the Kelly risk; it never sizes a real trade (lines 1379–1384). Live sizing uses fixed `RiskPct`.

### 2.5 `BidAskMonitor` (lines 160–182)
Rolling spread z-score over a 120-tick window. `SpreadAcceptable(maxZ)` is a live execution gate (line 1401). Keep this in every split EA — it's cheap insurance.

### 2.6 `PriceAction` (lines 186–224)
Swing-high/low detection, BOS/CHoCH structure enum, equal-high/low clusters, and FVG (fair-value-gap) detection. Note: `Structure` only ever sets `BosUp`/`BosDown` — CHoCH is declared in the enum but never assigned. Feeds composite-probability gates g1 and g9.

### 2.7 `ProbabilityWeights` + `ProbabilityScore` (lines 226–250)
12 weighted factors (F1–F12, weights summing to 100) → `Total` 0–100 → letter grade A+→F. This is the "Enhanced" decision path's confidence number. **Important:** this scorer is *separate* from the integer `score` used by the real trade trigger (`Consider`, Part 6). Two parallel scoring systems exist and they do not agree.

### 2.8 `SweepDetector` (lines 258–270) & `PoolResilience` (272–281)
`SweepDetector` counts how many of 6 sweep preconditions passed and maps that to a hard-coded `ExpectedR()` and `EmpiricalWinRate()` table (e.g. 6/6 → 1.18R, 67% win). **These numbers are assumptions baked into source, not measured** — they drive the (dormant) Kelly path. `PoolResilience` computes liquidity-pool exploitability but **is never called** anywhere in the robot. Dead code.

---

## PART 3 — THE TRADING ENGINE (`GodmodeOfea`)

### 3.1 Enums & DTOs (lines 289–330)
`SetupId` (25 named setups + None) is the master catalogue — **this enum is your split index**. `SetupCandidate` is the universal trade proposal (id, direction, entry, SL, TP, score, stars, location, priority, reason). `GateResult` is a pass/fail+reason struct used by the risk gates.

### 3.2 `DeltaEngine` (lines 353–420) — the LIVE delta engine
Distinct from `DeltaEnhanced`. This one subscribes to `Symbol.Tick` and classifies each tick as buy/sell by **mid-price direction** (line 372: `mid > prevMid` → buy). On bar close it shifts ring buffers for bar-delta, volume, CVD. Exposes `VolumeZ`, `DeltaZ`, `CvdSlope5`, and `BullishDivergence`/`BearishDivergence` (price makes new extreme, CVD doesn't).

**Critical fidelity warning:** mid-price tick classification is a *proxy*, not true bid/ask aggressor volume. In backtest, tick granularity depends on the data mode; with bar data the tick stream is synthetic and CVD is largely meaningless. **This is a prime suspect for the backtest divergence.** Any CVD-based split EA must be validated on tick data only.

### 3.3 `VolumeProfile` (lines 422–495)
Bins the last `VPLength` bars (default 100) into `VPBins` (50) price buckets by tick volume. Computes POC, VAH, VAL (value-area expansion to `VAValueAreaPct`=70%), flags LVN/HVN bins, and classifies profile **Shape** (D/P/b/Thin) → **MarketState** (Balanced/Imbalanced/Unknown). `LocationAt(price, tol)` returns where price sits (POC/VAH/VAL/LVN/HVN/None) — the spatial anchor for ~half the setups.

### 3.4 `FootprintAnalyzer` (497–513) & `AbsorptionStars` (515–529)
Footprint approximations from bar OHLC + delta: bullish/bearish absorption (delta opposes close direction on high volume), stacked imbalances, unfinished auction. `AbsorptionStars.Compute` returns a 0–5 quality score from volZ, deltaZ, and wick fraction. Drives setups 01/02 and the `AbsStars` field.

### 3.5 `SessionGate` (531–554)
SAST-offset session clock. Maps minute-of-day → `Session` (Asian/LdnOpen/LdnMain/NyOpen/NyMain/After), enable flags per session, NY-open blackout, NY-main-end approach, and crucially **`ModelForSession`**: LdnMain→M2 mean-reversion, NyMain/LdnOpen→M1 trend. **This is the strategic spine** — the EA changes its whole personality by session. Any split must decide which session(s) it lives in.

### 3.6 `HtfAlignment` (556–571) & `MultiTimeframeStructure` (1165–1186)
H4(EMA20)+D1(EMA50) bias (`HtfAlignment`) and M15+H1(EMA20) bias (`MultiTimeframeStructure`). `IsAligned` requires H4==D1==direction. `AlignmentScore` returns 0–4. Used as confluence, not hard gate.

### 3.7 `RiskManager` (573–630)
Per-day equity anchor, daily-DD gate, spread-median gate, consecutive-loss gate, and `ComputeVolume` (risk-% → lots from SL distance). Contains a **blown-account guard** (line 627): rejects the trade if the minimum lot inflates effective risk >3× target. Risk-% is hard-capped at 2%.

### 3.8 `TradeManager` (632–673)
Opens market orders (SL/TP in pips), and `ManagePosition` does partial close at R, break-even move, ATR trailing stop, and exit-at-POC. One position per label (`"GODMODE"`).

### 3.9 Support classes
`NotificationCenter` (675–700, de-duped per-bar alerts N-A…N-L), `Dashboard` (702–713, on-chart panel), `ChartViz` (715–723), `TradeLogger` (725–743, **CSV with full feature row per trade** — this is your win-rate goldmine), `AutoRiskReward` (745–780, draws RR boxes).

### 3.10 The 25 Setup Detectors (`SetupDetectors`, 782–849)
Each is a static method returning a `SetupCandidate` or `null`. `Build` (784–791) sets entry=ask/bid, SL=aggressor bar extreme ±2 ticks, TP=target level (POC/VAH/VAL). **This is the heart of the split** — each method is a self-contained entry rule. Full catalogue in Part 5.

### 3.11 The "God-Level" ICT/SMC modules (856–1186)
`PremiumDiscountZone`, `OTECalculator` (Fib 61.8–79%), `DisplacementDetector` (+FVG), `InducementDetector`, `StructureQuality`, `TriggerCandleDetector` (pin/engulf/doji/inside), `InstitutionalLevels` (PDH/PDL/PDC/weekly open/London range/round numbers), `ADXFilter`, `VolumeClockFilter`, `M1DeltaAggregator`. **None of these gate or veto** — they only add +1 to the integer score each (Part 6). They are confluence sweeteners, not independent strategies.

---

## PART 4 — THE LIVE DECISION PIPELINE (`RunBarClose`, 1395–1454)

Order of operations every closed bar:

1. **Hard risk gates** (any fail → no trade / halt): daily DD, spread blowout, consecutive losses, bid/ask spread z.
2. **Session gate**: must be an enabled session and not NY-open blackout.
3. **Model select**: `ModelForSession`. If model's enable-flag is off → return.
4. **Profile-state gate** (1411–1414): M2 fires in any state; M1 needs Imbalanced (Unknown allowed as fallback).
5. **Location gate**: price must be at a VP level (`loc != None`), tol = `LocTolATR*10` pips.
6. **CVD direction** computed for confluence.
7. **`ScoreAllSetups`** (1456–1484): every enabled detector runs; each candidate goes through `Consider`.
8. **SL floor**: enforce ≥0.5×ATR (1427–1432).
9. **R:R gate**: `rr < MinRR` (default 2.0) → reject.
10. **Priority** from score (≥5→P1, ≥4→P2, else P3).
11. **Size** via RiskManager; if 0 → reject.
12. **Fire** (Auto) or draw+log (Manual). Pyramiding blocked unless enabled.

There is a **second, parallel path**: `RunEnhancedBarClose` (1354–1368) computes the 12-factor probability and, if Auto and ≥ threshold, calls `EnhancedFireTradeIfReady` — which **only prints**. So the Enhanced probability system is currently a logger, not a trader.

---

## PART 5 — THE 25 SETUPS, ANNOTATED (the split catalogue)

Format: **ID · Name · Dir · Trigger logic · VP location req · OF requirement · Native family · Session model**

| ID | Name | Dir | Core trigger | Loc req | Order-flow req | Family | Model |
|----|------|-----|--------------|---------|----------------|--------|-------|
| 01 | AbsBot | Long | Bullish absorption candle | VAL/LVN | delta<0, volZ≥thr, close≥open, stars≥min | Absorption | M2 |
| 02 | AbsTop | Short | Bearish absorption | VAH/HVN | delta>0, volZ≥thr, close≤open | Absorption | M2 |
| 03 | CvdBear | Short | Bearish CVD divergence | any | price HH, CVD not | Divergence | either |
| 04 | CvdBull | Long | Bullish CVD divergence | any | price LL, CVD not | Divergence | either |
| 05 | ValBnc | Long | Bounce off VAL | VAL | close>open, delta≥0 | Mean-rev | M2 |
| 06 | VahFade | Short | Fade off VAH | VAH | close<open, delta≤0 | Mean-rev | M2 |
| 07 | PocRet | dir=delta | Return to POC | POC | sign of delta | Mean-rev | M2 |
| 08 | LvnLong | Long | Acceleration through LVN | LVN | delta>0, volZ≥1 | Breakout | M1 |
| 09 | LvnShort | Short | Acceleration through LVN | LVN | delta<0, volZ≥1 | Breakout | M1 |
| 10 | HvnRej | dir=delta | Rejection at HVN | HVN | delta sign | Mean-rev | M2 (default OFF) |
| 11 | StackBull | Long | Stacked bull imbalance + CVD slope>0 | any | stacked rows, cvdSlope5>0 | Momentum | M1 |
| 12 | StackBear | Short | Stacked bear imbalance + CVD slope<0 | any | stacked, cvdSlope5<0 | Momentum | M1 |
| 13 | PullStack | dir | 3-bar delta run, price within 5 pips of zone | any | consecutive delta | Pullback | M1 |
| 14 | Spring | Long | Wyckoff spring (sweep low, close back, bull div) | any | bullish div | Wyckoff | M2 |
| 15 | Upthrust | Short | Wyckoff upthrust (sweep high, close back, bear div) | any | bearish div | Wyckoff | M2 |
| 16 | Sos | Long | Sign-of-strength: cvdSlope5>0 & volZ≥1 | any | momentum | Wyckoff/trend | M1 |
| 17 | Lpsy | Short | Last-point-of-supply: cvdSlope5<0 & volZ≥1 | any | momentum | Wyckoff/trend | M1 |
| 18 | LiqSweep | dir | Sweep 50-bar extreme then close back inside | any | none (pure PA) | Liquidity | either |
| 19 | ObReturn | dir | Return to order block (old opposing candle) | any | cvdSlope5 sign | SMC | M1 |
| 20 | SmtDiv | dir | SMT divergence vs correlated symbol slope | any | slope vs corr | Inter-market | either |
| 21 | Breaker | dir | Breaker block (failed swing flip) | any | cvdSlope5 sign | SMC | M1 |
| 22 | Amd | dir | Accumulation-manipulation-distribution range break | any | deltaZ>1.5 | SMC | M1 |
| 23 | UnfAuc | dir | Unfinished auction (poor high/low) | any | none | Auction | either |
| 24 | PoorHL | dir | Poor high/low vs prior bar + delta | any | delta sign | Auction | either |
| 25 | Iceberg | dir | High vol, tiny range, tiny delta at VP level | any VP | volZ≥2, |dz|<0.5, range<0.6ATR | Absorption | M2 |

**SMT (20) is broken:** `corrCvdSlope` is passed as a literal `0.0` (line 1478), so `mySlope*0 >= 0` is always true → the function always returns null. Setup 20 never fires. Fix: wire a real correlated-symbol delta engine before splitting it out.

### 5.1 Documented (target) win rates — Brief §6
These are the **literature/target** win rates from the build brief, NOT measured results. Treat them as priors to rank your split EAs against — if a split EA backtests far below its documented rate, the edge either decayed or was never real on your data. Per §21.3 you need ≥200 trades before trusting any measured rate.

| ID | Setup | Doc. win rate | ID | Setup | Doc. win rate |
|----|-------|---------------|----|-------|---------------|
| 01 | AbsBot | 74–78% | 14 | Spring | 75–80% (highest) |
| 02 | AbsTop | 74–78% | 15 | Upthrust | 74–78% |
| 03 | CvdBear | 72–76% | 16 | SOS | 70–74% |
| 04 | CvdBull | 72–76% | 17 | LPSY | 68–73% |
| 05 | ValBnc | 73–77% | 18 | LiqSweep | 74–78% |
| 06 | VahFade | 73–77% | 19 | ObReturn | 72–76% |
| 07 | PocRet | 68–72% | 20 | SMTDiv | 73–77% |
| 08 | LvnLong | 70–74% | 21 | Breaker | 70–74% |
| 09 | LvnShort | 70–74% | 22 | AMD | 75–79% |
| 10 | HVNRej | 65–69% (OFF) | 23 | UnfAuc | 71–75% |
| 11 | StackBull | 73–77% | 24 | PoorHL | 70–74% |
| 12 | StackBear | 73–77% | 25 | Iceberg | 73–77% |
| 13 | PullStack | 70–74% | | | |

Brief's own honest ceiling (§21–22): base 5-gate ≈72–78%; full marginal stack ≈76–78% sustained; 80%+ "treat with suspicion." Optimise for **expectancy and profit factor, not win rate** (§21.4) — a 60%/+1.5R system beats an 80%/+0.6R one.

---

## PART 6 — THE `Consider` SCORE (1486–1562): why backtest results are uninterpretable

Every candidate accumulates an integer `score`. **Two things only are hard vetoes** here: `cvdOk` (line 1513) and (upstream) the location/RR/risk gates. Everything else is +1/−1:

- +1 each: location is a VP level, volZ≥thr, any divergence, stars≥min, prime session, regime matches direction.
- −1: HTF counter-trend.
- +1 each (god-level): M1 CVD sign, premium/discount aligned, OTE zone, displacement, FVG, inducement, structure quality≥0.6, near institutional level, near round number, ADX confirms (session-specific), volume clock active, +0–2 MTF alignment, trigger candle.

Max possible ≈ 20. The single highest-scoring candidate across **all 25 setups** wins the bar (`if score > bestScore`). 

**The fatal consequence for analysis:** the winning trade's `SetupId` is logged, but the *decision* to fire was driven by a score that pooled 25 setups + ~14 confluence factors. Two different setups with identical scores are resolved by iteration order (01 first). So your backtest equity curve is a blend where:
- You cannot attribute P&L to any single setup.
- Setups that *never win the max* (because another setup always out-scores them in their session) contribute nothing yet inflate apparent complexity.
- A globally optimised parameter (e.g. `VolZThreshold`) is simultaneously helping some setups and hurting others.

This is the structural reason to split. **Until each setup has its own EA and its own log, win rates per setup are unknowable.**

---

## PART 7 — THE SPLIT MAP (your build worksheet)

### 7.1 Principle
One EA = one **family** (correlated setups that share entry logic, session, and order-flow dependency). Splitting to 25 EAs is too granular (many share identical plumbing); splitting by family gives ~7 testable EAs. Each gets its own `TradeLogger` path and its own label so positions never collide.

### 7.2 Recommended EAs

**EA-1 · Absorption Reversal** — setups 01, 02, 25.
M2/any-state, location-anchored (VAL/VAH/LVN/HVN), depends on `DeltaEngine`+`FootprintAnalyzer`+`AbsorptionStars`. Highest conceptual edge; isolate first.

**EA-2 · CVD Divergence** — setups 03, 04.
Location-agnostic, depends only on `DeltaEngine` divergence. **Validate on tick data** (CVD fidelity risk). Cleanest to test.

**EA-3 · Value-Area Mean-Reversion** — setups 05, 06, 07, 10.
Pure VP-location logic, M2/LdnMain. Minimal order-flow. Likely the most robust in backtest because it's least dependent on synthetic CVD.

**EA-4 · LVN/Stack Momentum (Trend)** — setups 08, 09, 11, 12, 13, 16, 17.
M1/NyMain, needs Imbalanced state + positive CVD slope. This is the "trend" engine. Group because they all key off delta-slope continuation.

**EA-5 · Wyckoff Spring/Upthrust** — setups 14, 15.
Sweep + close-back + divergence. Distinct enough to test alone; clear, rule-based, tick-data tolerant.

**EA-6 · SMC/ICT Structure** — setups 18, 19, 21, 22, (+20 once fixed).
Liquidity sweeps, order blocks, breakers, AMD. Pure price-structure; pairs naturally with the god-level ICT modules as *gates* here rather than score-bumps.

**EA-7 · Auction Anomaly** — setups 23, 24.
Unfinished auction / poor highs-lows. Low frequency; test for novelty value.

### 7.3 What each split EA keeps vs. drops
- **Keep (shared lib):** `DeltaEngine`, `VolumeProfile`, `SessionGate`, `RiskManager`, `TradeManager`, `TradeLogger`, `BidAskMonitor`, ATR. Put these in one shared `.cs` or duplicate verbatim.
- **Convert score-bumps to explicit gates:** in the monolith, ICT/SMC factors only nudge score. In a single-setup EA you can afford to make 2–3 of them *hard requirements* (e.g. EA-6 requires inducement + displacement). This is what makes per-EA win rates meaningful.
- **Drop the dual scoring system:** pick ONE — either the integer `Consider` score or the 12-factor `ProbabilityScore`. Running both is what made the monolith inscrutable.
- **Drop dead code per EA:** `PoolResilience`, the dormant Kelly path, unused enums.

### 7.4 Per-EA test protocol (so the split actually pays off)
1. One setup-family enabled, Auto mode, tick data, single symbol, single session.
2. Log every signal (including skipped) via `TradeLogger` — the CSV already carries setup_id, score, all features.
3. Compute per-setup: trades, win%, avg R, expectancy, max DD, profit factor.
4. **Only then** rank by win rate × expectancy and study correlation between families (do EA-3 and EA-4 lose at the same time? if so they share a hidden regime dependency).
5. Recombine only the families that are individually profitable AND uncorrelated in drawdown.

---

## PART 8 — KNOWN DEFECTS TO FIX DURING THE SPLIT

1. **CVD on synthetic ticks** (`DeltaEngine.OnTick`, mid-price proxy): meaningless on bar-based backtest. Use tick data; consider replacing with `M1DeltaAggregator` bar-proxy for consistency between live and test.
2. **SMT (setup 20) always null** — `corrCvdSlope=0.0` hard-coded (line 1478).
3. **RegimeHMM half-blind** — `footImb` and `profileSkew` passed as 0 (line 1361).
4. **Two scoring systems** that don't agree (`Consider` int score vs. `ProbabilityScore`).
5. **Enhanced/Kelly path is a no-op** — prints but never trades (line 1383).
6. **CHoCH never set** in `PriceAction.Structure`.
7. **Hard-coded win-rate/R tables** in `SweepDetector` masquerade as empirical — replace with measured values once you have per-setup logs.
8. **`PoolResilience` dead code.**

---

## PART 10 — ANALYTICAL SCAFFOLDING THE BRIEF ALREADY SPECIFIES (use it for the split)

The brief contains three pieces of infrastructure that are *purpose-built* for the win-rate/correlation analysis you want — but in the monolith they are diluted or unbuilt. In the split, make them first-class:

1. **Per-setup rolling win rate + auto-disable (Brief §22.8, "M8 Adaptive Setup Tiering").** Maintain a rolling 200-trade sample *per `SetupId`*; auto-disable any setup whose rolling win rate < 60% over >50 of its own trades. In the monolith this was never implemented. In each split EA it becomes trivial — one setup, one rolling stat. **This is literally the per-setup win-rate ranking you asked for**, and the brief already designed the thresholds.

2. **Correlation filter (Brief §23.3).** The brief defines which symbols/setups are correlated and must not stack (e.g. EURUSD↔GBPUSD↔DXY). For your split, the analogous question is: *do EA-3 (mean-reversion) and EA-4 (trend) draw down together?* Compute pairwise drawdown correlation across your split EAs; only recombine families that are uncorrelated. Re-use the §23.3 spec as the template.

3. **The CSV journal (Brief §13 / `TradeLogger`).** The log row already carries `setup_id, score, priority, session, market_state, htf_bias, profile_shape, cvd, vol_z, delta_z, abs_stars, mode`. The brief's intended event types include `SKIP_F1…F5`, `KILL_*` — i.e. it was meant to log *rejections too*. Make sure each split EA logs skips (the monolith only logs `ENTRY` and `SKIP_F1`), because per-setup hit-rate needs the denominator (signals fired), not just the numerator (trades taken).

**Honesty contract (Brief §A.6), applied to the split:** measure each split EA's edge from its *own* CSV, one change at a time, ≥100–200 trades before trusting a number; accept that some of the 25 setups will prove to have no edge on your data and should be retired, not rescued.

## PART 9 — ONE-PARAGRAPH EXECUTIVE SUMMARY

GODMODE_OFEA bins price into a volume profile, reads order-flow via a (synthetic) CVD/delta engine, switches between a trend model (NY) and a mean-reversion model (London) by session, and runs 25 entry detectors whose signals are merged into a single per-bar integer score; the highest-scoring candidate that clears the risk/RR gates is traded. Because all 25 setups, ~14 confluence factors, and two parallel scoring systems collapse into one equity curve through one position slot, the backtest cannot attribute performance to any individual edge — which is why it failed to be diagnosable. The remedy is to split along the seven setup families in Part 7, give each its own log and its own hard gates, backtest them in isolation on tick data, fix the eight defects in Part 8, and recombine only the families that prove individually profitable and uncorrelated in drawdown.
