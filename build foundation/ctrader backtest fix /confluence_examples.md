# Confluence Cascade — 5 Worked Examples

Each example traces what the operator sees as gates fire one by one. Brief §4 + §18.

## Example 1 — Absorption Bottom at VAL during London Main (Setup #01, Long)

**Context**: EURUSD M5, 11:42 SAST, London Main session, prior day was D-shape balanced.

```
Bar t-3: Price drifts down toward VAL at 1.0830, CVD has been rising for 8 bars.
Bar t-2: Price touches VAL.
   ▶ GATE 3 fires: N-A "VP VAL touch @ 1.0830" — yellow horizontal line drawn,
     single beep, dot ④ flips green.

Bar t-1: VolumeProfile.Recompute classifies shape as D (skewness 0.04, peak 2.3).
   ▶ GATE 2 fires: N-F "Shape D state 1" — dashboard tags BAL, dot ① flips green.

Bar t-1 continued: HTFAlignment reads H4 EMA(20) bull, D1 EMA(50) bull.
   ▶ GATE 4 fires: N-D "HTF aligned: BULL" — HTF✓ badge, dot ③ flips green.

Bar t-1 continued: cvd[0] = 14820, slope5 = +312, both rising.
   ▶ GATE 5 fires: N-E "CVD confirms LONG (CVD=14820)" — soft ↑ arrow,
     dot ⑤ flips green.

Bar t-0 closes: open=1.0833, close=1.0834, delta = -842 (negative!),
                volume Z = 2.4, |delta Z| = 1.8.
   FootprintAnalyzer.BullishAbsorption returns true (delta<0, volZ≥1.5, close≥open).
   AbsorptionStars.Compute(LONG):
     stars=1 (vol Z ≥ 1.0)
     +1 (vol Z ≥ 2.0)
     +1 (|delta Z| ≥ 2.0 — actually 1.8, no)
     +1 (lower wick = 0.45 of range, ≥ 0.40)
     = 3 stars (+ vol Z bonus = 4)

   Detect_Setup01_AbsBot returns SetupCandidate{
     dir=LONG, entry=ask=1.0834, sl=low-2pt=1.0822, tp=POC=1.0867,
     absStars=4, vpLoc=VAL
   }

   ▶ GATE 6 fires: N-G "Footprint setup ★4" — green star with "4" badge below bar,
     dot ⑥ flips green.

ConsiderCandidate scoring:
   loc=VAL  → +1
   volZ≥1.5 → +1
   bull div → +1 (price LL with cvd HL)
   absStars≥3 → +1
   session=LDN_MAIN → +1
   = score 5

GATE 7+8: rr = (1.0867 - 1.0834) / (1.0834 - 1.0822) = 0.0033 / 0.0012 = 2.75 ≥ MinRR
   priority = P1
   lots = (10000 × 0.01) / (12 × 1.0) = 8.33 → normalized to 8.0 lots (or
                                                appropriate broker step)

   ▶ GATE 8 fires: N-I "A+ READY LONG setup=1 score=5 R:R=2.8" —
     full-screen flash, popup, bell chime, dots ⑦ ⑧ flip green.

MODE_MANUAL: trade lines drawn, no order. Operator clicks Buy manually.
MODE_AUTO: TradeManager.OpenPosition fires, N-J "LONG 8.00 lots @ 1.0834
           SL 1.0822 TP 1.0867 [AUTO]" — confirmation chime.
```

This is the §18 user story end-to-end.

## Example 2 — VAH Fade during London Main (Setup #06, Short)

```
GATE 1: LDN_MAIN active, model = M2.
GATE 2: D-shape balanced, M2 ↔ BALANCED → pass.
GATE 3: Price 1.0892 touches VAH 1.0892 → N-A "VP VAH touch @ 1.0892", dot ④.
GATE 4: HTF neutral (H4 bull, D1 bear) — N-D fires only if both agree.
        Without alignment, HalfSize_OnHTFConflict=false → block here.

Result: SKIP. Notification N-A fires, but pipeline halts at GATE 4.
        Dot ③ stays grey, dashboard never reaches A+ ready.
```

This is the brief §2 F3 gate doing its job — counter-HTF entries are blocked unless explicitly half-sized.

## Example 3 — Wyckoff Spring at session POC (Setup #14, Long)

```
GATE 1: 09:45 SAST, LDN_OPEN, model = M1.
GATE 2: Profile shape THIN (skewness 0.05, peak 1.1) — IMBALANCED.
        M1 ↔ IMBALANCED → pass.
GATE 3: Price 1.0805 touches LVN 1.0805 → N-A "VP LVN touch @ 1.0805", dot ④.

Setup_14_Spring detection:
   swingLow over last 30 bars = 1.0808
   curL = 1.0803 (below swingLow → fake-out below)
   curC = 1.0810 (above swingLow → reclaim)
   BullishDivergence: price[0].low LL, cvd[0] > cvd_LL → TRUE

   ▶ N-G "Footprint setup ★0" (Spring doesn't compute stars but the detector fires)
   Builds candidate: dir=LONG, entry=ask, sl=swingLow_low-2pt, tp=POC

GATE 5: cvd slope = +89, dir = LONG → matches. N-E.
GATE 8: score 4 (loc + volZ + divergence + session — no abs stars), priority P2.

   ▶ N-I "A+ READY LONG setup=14 score=4 R:R=4.2" — bell chime.

MODE_AUTO: order fires.
TradeManager will partial 50% at 1R, BE+1pip at 1R, trail by 1×ATR.
For Wyckoff Spring this is a high R:R setup — typical 4:1 to 8:1 per the source authority.
```

## Example 4 — NY Main Liquidity Sweep + Reversal (Setup #18, Short)

```
GATE 1: 18:15 SAST, NY_MAIN, model = M1.
GATE 2: P-shape (skewness +0.28) — IMBALANCED. M1 ↔ IMBALANCED → pass.

Bar t-1: Price runs up through prior swing high at 1.0905 — sweeps BSL.
Bar t-0 close: cur high = 1.0908, cur close = 1.0902 (back below sweep level).

Detect_Setup18_LiqSweep:
   swingHigh over last 50 bars = 1.0905
   cH > sH (1.0908 > 1.0905), cC < sH (1.0902 < 1.0905) → dir=SHORT
   Builds candidate at LVN location.

   ▶ N-G "Footprint setup ★0", dot ⑥ flips.

GATE 4: HTF bear, intended SHORT → aligned → N-D.
GATE 5: cvd slope = -1820 (strongly falling), dir = SHORT → matches → N-E.
GATE 8: score 5 (loc + volZ + divergence + session + cvd), priority P1.

   ▶ N-H "Aggression vol Z=2.7" — large arrow with print size.
   ▶ N-I "A+ READY SHORT setup=18 score=5 R:R=3.4" — bell.

MODE_AUTO: order fires. Stop is 2 ticks beyond sweep high (1.0908+2pt), not at 1.0910
           (the obvious swing extreme — Fabio §15 rule).
```

## Example 5 — Spread Blowout Mid-Session (Kill Switch)

```
14:25 SAST, LDN_MAIN, dashboard shows 7/8 confluences with VAL bounce setup pending.

Tick arrives: spread = 0.0005 (5 pips). Rolling 100-bar median = 0.00018 (1.8 pips).
RiskManager.CheckSpread: 0.0005 > 0.00018 × 2.0 → fail.

Bar closes:
   ▶ GATE 0 — CheckSpread returns failed GateResult.
   ▶ NL_KillSwitch("SPREAD_BLOWOUT") — red banner across top of chart,
     timeout chime, push notification.
   Pipeline halts immediately. No setup detection runs.

This is brief §12 rule 8 doing its job — spread guard is the last line of defense
before paying the cost of execution into a degraded broker condition.
```

The cascade is the operator's interface. Whether you're in MANUAL or AUTO, the EA's "thinking" is visible at every stage.
