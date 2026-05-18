# GODMODE_OFEA — Enhanced Edition

This folder is the v2 enhancement of the base MT5 / cTrader / TradingView builds.
Concepts integrated are drawn exclusively from the GODMODE Confluence Thesis
package (Bokgabane / AEGO, 2026-05-18) and from the Jansen ML4T + Aronson/Masters
references that 100% align with — and never contradict — the existing F1-F5 gate
stack, the 8-row dashboard, or the brief §0-§24 hard prohibitions.

## What is added (vs. base build)

| # | Concept | Source | Files |
|---|---------|--------|-------|
| 1 | **VWAP** + bands (session-anchor + rolling) | classical AMT | `OF_VWAP.mqh`, `VWAP.cs`, Pine |
| 2 | **Bid-Ask spread** monitor + cost-aware gate | microstructure | `OF_BidAsk.mqh`, `BidAsk.cs`, Pine |
| 3 | **Delta** enhanced — confirmed: 3-state regime (trend / divergent / inverse-divergent), z-score, climax detection | PDF Ch.2, Ch.15 | `OF_DeltaEnhanced.mqh`, `DeltaEnhanced.cs`, Pine |
| 4 | **Price-Action concepts** — 100%-aligned only: BOS/CHoCH (initiative rotation), Equal H/L (engineered stop cluster), FVG (single-print/LVN) | PDF Ch.9 Rosetta table | `OF_PriceAction.mqh`, `PriceAction.cs`, Pine |
| 5 | **4-state Regime classifier** (HMM-lite): Init-Buy, Init-Sell, Absorption, Rotation | PDF Ch.14 Hidden Markov | `OF_RegimeHMM.mqh`, `RegimeHMM.cs`, Pine |
| 6 | **6-precondition Sweep detector** (equal-level + HTF + session + momentum + absorption + delta-flip) | PDF Ch.6 (V06) | `OF_SweepDetector.mqh`, `SweepDetector.cs`, Pine |
| 7 | **Pool resilience** = refilled/consumed ratio | PDF Ch.3 (V06) | `OF_PoolResilience.mqh`, `PoolResilience.cs` |
| 8 | **Kelly fractional + vol-target sizing** (κ ∈ {0.25, 0.5}) | PDF Ch.11 | `OF_KellySizer.mqh`, `KellySizer.cs` |
| 9 | **Probability Score** (0-100% setup grade) — composite of all gates | this build | `OF_ProbabilityScore.mqh`, `ProbabilityScore.cs`, Pine |
| 10 | **3-tier TP / SL** (TP1, TP2, TP3 / SL1, SL2, SL3) — ATR-projected + VP-anchored | this build | indicator + risk module |
| 11 | **HTF Strength meter** per timeframe (M5 / M15 / H1 / H4 / D1) | this build | `GODMODE_HTFStrength.mq5`, Pine |
| 12 | **Session Light** — current session colour-coded on chart | this build | `GODMODE_SessionLight.mq5`, Pine |

## Hard prohibitions preserved

- RiskPct still hard-capped at 2.0 (brief §12 rule 2)
- No SL at obvious swing extremes (1-2 ticks beyond aggression candle, brief §15)
- No exits beyond POC in Model 2
- Behavioural mirror between MQL5 and cAlgo preserved
- No ONNX / Python sidecar, no RL agent (out of scope for retail MT5/cTrader)

## Folder layout

```
Enhanced/
├── MT5/
│   ├── Experts/GODMODE_OFEA_Enhanced/   ← drop in MT5\MQL5\Experts\
│   ├── Include/                          ← drop in MT5\MQL5\Include\
│   └── Indicators/                       ← drop in MT5\MQL5\Indicators\
├── cTrader/
│   ├── Normal/                           ← C# source for Visual Studio / cTrader IDE
│   │   ├── GODMODE_OFEA_Enhanced.cs
│   │   └── Modules/*.cs
│   └── algo/                             ← packaging notes for .algo distribution
└── TradingView/                          ← 7 v2 Pine indicators
```

## Install summary

**MT5**: copy `MT5/Experts/...` to `MQL5\Experts\`, `MT5/Include/*.mqh` to
`MQL5\Include\` (loose, not in a subfolder), and `MT5/Indicators/*.mq5` to
`MQL5\Indicators\GODMODE\`. F7 compile, attach EA to chart, drag each indicator on.

**cTrader**: open `cTrader/Normal/GODMODE_OFEA_Enhanced.cs` in cTrader's
"Add new cBot" editor, paste, paste each `Modules/*.cs` in turn, build, attach.

**TradingView**: paste each `TradingView/*.pine` into a new indicator and save.
Use the "GODMODE_Enhanced" template to load all seven at once.

See per-build README in each subfolder.
