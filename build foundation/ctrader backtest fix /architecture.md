# Architecture

How the gates compose, where each module lives, and why the wiring is the way it is.

## Module Map (1:1 across both builds)

```
MT5 Include/                              cTrader Modules/
├─ OF_Common.mqh                          ├─ OFCommon.cs
├─ OF_Logger.mqh                          ├─ TradeLogger.cs
├─ OF_DeltaEngine.mqh                     ├─ DeltaEngine.cs
├─ OF_VolumeProfile.mqh                   ├─ VolumeProfile.cs
├─ OF_FootprintAnalyzer.mqh               ├─ FootprintAnalyzer.cs
├─ OF_AbsorptionStars.mqh                 ├─ AbsorptionStars.cs (in FootprintAnalyzer.cs)
├─ OF_SessionGate.mqh                     ├─ SessionGate.cs
├─ OF_HTFAlignment.mqh                    ├─ HTFAlignment.cs
├─ OF_RiskManager.mqh                     ├─ RiskManager.cs
├─ OF_TradeManager.mqh                    ├─ TradeManager.cs
├─ OF_NotificationCenter.mqh              ├─ NotificationCenter.cs
├─ OF_Dashboard.mqh                       ├─ Dashboard.cs
├─ OF_ChartViz.mqh                        ├─ ChartViz.cs
└─ OF_SetupDetectors.mqh                  └─ SetupDetectors.cs
```

Module names match one-to-one. Public method signatures match one-to-one. Different syntax, identical behaviour.

## Data Flow

```
Tick arrives
  │
  ▼
DeltaEngine.OnTickAccumulate
  │ (TICK_FLAG_BUY → tickBuy; TICK_FLAG_SELL → tickSell, MT5)
  │ (TickType.Ask → tickBuy; TickType.Bid → tickSell, cTrader)
  ▼
[is new bar?]
  │
  ├─ no → return; refresh dashboard if 250ms elapsed
  │
  └─ yes → DeltaEngine.OnBarClose
            │ snapshot bar_delta = tickBuy - tickSell
            │ shift series, append cvd[0] = cvd[1] + bar_delta
            │ reset tickBuy = tickSell = 0
            ▼
          RiskManager.SampleSpread (rolling 100-bar median)
            ▼
          VolumeProfile.Recompute (50-bin POC/VAH/VAL + shape classifier)
            ▼
          RunBarClose pipeline (gates 0..8)
```

## Gate Pipeline (brief §5)

```
GATE 0 — Kill Switches
  │ daily DD ≥ MaxDDPct?         → fail: NL_KillSwitch + flatten + halt day
  │ spread > median × mult?       → fail: NL_KillSwitch
  │ consec losses ≥ MaxConsec?    → fail: NL_KillSwitch + halt day
  ▼ pass
GATE 1 — F2 Session
  │ classify SAST minute          → ASIAN | LDN_OPEN | LDN_MAIN | NY_OPEN | NY_MAIN | AFTER
  │ session enabled in inputs?    → fail: skip
  │ NY-Open blackout window?      → fail: skip
  │ model = M2 if LDN_MAIN, M1 if NY_MAIN/LDN_OPEN
  ▼ pass
GATE 2 — F5 State
  │ vp.Shape (D | P | b | THIN)
  │ vp.State (BALANCED | IMBALANCED)
  │ M2 ↔ BALANCED / M1 ↔ IMBALANCED?  → mismatch: skip
  ▼ pass
GATE 3 — F1.A Location
  │ |close - POC/VAH/VAL/LVN/HVN| < tol?  → fire N-A
  │ no key level near close?              → skip
  ▼ pass
GATE 4 — F3 HTF Alignment
  │ H4 EMA(20) bias + D1 EMA(50) bias
  │ both agree with intended dir?         → fire N-D, full size
  │ HalfSize_OnHTFConflict=true?          → half size
  │ neither?                               → block
  ▼
GATE 5 — F4 CVD Confirmation
  │ cvd slope (last 5 bars), bull/bear divergence
  │ matches direction?                    → fire N-E
  │ otherwise                              → skip
  ▼ pass
GATE 6 — F1.B Footprint Signal
  │ iterate 25 setup detectors
  │ each returns SetupCandidate or null
  │ score each via ConsiderCandidate (0..5)
  │ pick best                              → fire N-G with star count
  │ if vol Z ≥ AggressionZThreshold        → fire N-H
  ▼ pass
GATE 7 — Trigger Confirmation
  │ implicit in detectors — each enforces
  │ its own trigger pattern (M5 CHOCH,
  │ aggression candle, etc.)
  ▼ pass
GATE 8 — Score & Size
  │ score = vp_loc + delta_z + divergence + abs_stars + session
  │ priority = P1 if score≥5, P2 if ≥4, else P3
  │ rr = |TP - entry| / |entry - SL|
  │ rr < MinRR?                            → skip
  │ lots = riskAmount / (slPips × pipValue) (brief §11.8)
  │ fire N-I (A+ entry ready)
  ▼
EXECUTE
  │ MODE_AUTO  → place order, log ENTRY, fire N-J
  │ MODE_MANUAL → draw trade lines, log SKIP_F1, no order
```

## Why this order

The gate sequence is intentional and non-negotiable per brief §19 rule 6. Reasoning:

- **Kill switches first** — never run setup detection if we've already breached daily DD or spread thresholds. Cheap check, eliminates downstream work.
- **Session before state** — session determines model (M1 vs M2). State determines whether we trade at all in that model. Wrong order = waste profile recomputation work for trades we'd reject anyway.
- **Location before alignment** — if price isn't at a VP level, we don't care what HTF says. Cheaper check.
- **HTF before CVD** — HTF is computed from cached EMA handles, no work per bar. CVD direction needs slope from current accumulator. Cheap-then-expensive ordering.
- **Footprint last** — most expensive (iterates 25 detectors). Only run after all upstream gates pass.

This ordering is what keeps the EA fast enough for 5–15 trades/day across 3–6 symbols (brief §23.6 — once multi-symbol lands in v1.1).

## Notification Cascade Wiring

Each gate calls into `NotificationCenter.NX_*` on FALSE→TRUE edge transitions. The center's `ShouldFire` method tracks `Dictionary<string, datetime>` keyed on tag — once per bar per tag. This is brief §4's "rate-limiting via state dictionary."

```
GATE 0 fail   → NL_KillSwitch
GATE 1 entry  → NC_KillZone (on session change to LDN_MAIN/NY_MAIN)
GATE 2 done   → NF_ProfileState
GATE 3 pass   → NA_VpLevel
GATE 4 pass   → ND_HTFAligned
GATE 5 pass   → NE_CvdConfirm
GATE 6 pass   → NG_FootprintSignal + NH_Aggression (if vol Z spikes)
GATE 8 pass   → NI_AplusReady
EXECUTE       → NJ_TradeFired (AUTO) or chart-only (MANUAL)
TradeManager  → NK_PositionEvent (partial, BE, trail, POC exit)
Session end   → NL_KillSwitch (NY_MAIN_END)
```

## State Management (brief §10)

Three layers of state, each with explicit lifetime:

| Layer | Reset trigger | Lives in |
|-------|---------------|----------|
| Tick-level (tickBuy, tickSell, spread_pips) | New bar | DeltaEngine, RiskManager |
| Bar-level (delta[], cvd[], poc, vah, val, shape) | Per-bar shift | DeltaEngine series, VolumeProfile cache |
| Daily (start_equity, trades_today, consec_losses, day_halted) | Day rollover (UTC date change) | RiskManager, main robot |
| Notification (last_fired_bar per tag) | Per bar (edge-detected) | NotificationCenter dictionary |

The lifetimes never overlap. Day rollover doesn't touch tick-level state. Bar close doesn't touch daily state. This is enforced by where each `Reset` lives.

## Risk Discipline

`RiskManager` is the single arbiter. No other module touches sizing, daily state, or kill switches. Brief §12 rules 1–8 all enforced here:

- **Rule 1** — `TradeManager.CloseAll` called from main robot when `_sess.ApproachingNyMainEnd(5)`.
- **Rule 2** — `RiskPct` clamped to 2.0 in `RiskManager.Init`.
- **Rule 3** — `CheckDailyDrawdown` returns failed GateResult ≤ -MaxDDPct; main robot calls `HaltDay()` and `_trade.CloseAll()`.
- **Rule 4** — `CheckConsecLosses` returns failed when ≥ MaxConsecLosses.
- **Rule 5** — Session discipline enforced in Gate 1.
- **Rule 6** — News blackout via `CheckNewsBlackout` (JSON loader is Phase-2; the gate exists, the loader stubs).
- **Rule 7** — TradeManager filters by `Label == "GODMODE"` on every position iteration.
- **Rule 8** — `CheckSpread` returns failed when current > median × MaxSpreadMult.

## Mirror Discipline

Per brief §19 rule 7, no platform-divergent logic. Where MQL5 has a feature C# doesn't (e.g. `iATR` returning a buffered handle), the C# side simulates it (`Indicators.AverageTrueRange`). Where C# has a cleaner API (e.g. `Symbol.Ticks.Subscribe`), the MQL5 side reads the same data through `MqlTick.flags & TICK_FLAG_BUY`. The numbers come out the same.

The acceptance test for mirror discipline is `TESTING.md` Phase 6 A/B comparison — signal agreement ≥ 95%.
