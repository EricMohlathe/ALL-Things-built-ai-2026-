# GODMODE Master cBot Library (cTrader / cAlgo, C#)

The cTrader port of the MT5 master library — the **same 26 mechanical archetypes** sharing one engine (`GODMODE_Core.cs`). For the full strategy explanations, the **150-trader → archetype map**, risk-mode table, and the honest win-rate framing, see **`../MT5_MasterLibrary/README.md`** (it applies identically here).

> **Honest frame (unchanged):** sustained 80–100% win rates aren't real (your own brief §21 + the *"Proof that iFVGs have no edge"* script). Small accounts grow via asymmetric R:R + survival + uncorrelated edges + compounding + backtesting to keep only what works.

## Files

| File | Archetype |
|------|-----------|
| `GODMODE_Core.cs` | Shared engine (sizing, sessions, guards, trade mgmt, journal, FVG/OB helpers) — **not a cBot**, library code |
| `GM01_OpeningRangeBreakout.cs` | Opening Range Breakout |
| `GM02_SessionSweepReversal.cs` | Liquidity Sweep → Reclaim (Judas/CRT/PO3) |
| `GM03_FVGEntry.cs` | Fair Value Gap mitigation |
| `GM04_OrderBlockReturn.cs` | Order Block return |
| `GM05_ICTUnicorn.cs` | Unicorn (OB + FVG overlap) |
| `GM06_WyckoffSpring.cs` | Wyckoff Spring / Upthrust |
| `GM07_VWAPMeanReversion.cs` | VWAP band fade (AMT) |
| `GM08_MomentumDisplacement.cs` | No-wick / displacement continuation |
| `GM09_OrderFlowAbsorption.cs` | CVD divergence + absorption (**tick data only**) |
| `GM10_PowerOfThree_CRT.cs` | Power-of-3 / CRT with CISD + SD target |
| `GM11_SilverBullet.cs` | ICT Silver Bullet (macro window + sweep + FVG) |
| `GM12_OTE.cs` | Optimal Trade Entry (Fib 0.62–0.79) |
| `GM13_PriceAction.cs` | Pin bar / engulfing / inside-bar (Nial Fuller) |
| `GM14_TurtleSoupSFP.cs` | Turtle Soup / Swing Failure Pattern (sweep + reclaim) |
| `GM15_SupplyDemand.cs` | Supply & Demand zones (RBR/DBR/DBD/RBD base return) |
| `GM16_MarketStructure.cs` | Market structure BOS (continuation) / CHoCH (reversal) |
| `GM17_InitialBalance.cs` | Initial Balance breakout (market-profile IB extension) |
| `GM18_Harmonic.cs` | Harmonic XABCD (Gartley / Bat / Butterfly / Crab) |
| `GM19_RSI2MeanReversion.cs` | Connors RSI(2) pullback in long-EMA trend |
| `GM20_GapFade.cs` | Opening-gap fade-to-close **or** gap-and-go |
| `GM21_PrevDayLevels.cs` | Prev-day/week H/L sweep + reclaim (stop-hunt fade) |
| `GM22_EMAPullback.cs` | EMA-stack trend, pullback-and-reclaim continuation |
| `GM23_OpeningGapCE.cs` | ICT NDOG/NWOG gap midpoint (consequent encroachment) |
| `GM24_SMTDivergence.cs` | SMT divergence vs a correlated pair |
| `GM25_BreakoutRetest.cs` | Range break, enter on the retest that holds |
| `GM26_ConfluenceStack.cs` | **Meta-edge:** fire only when N layers agree (4–5 floor) |

**Standard deviation:** GM07 fades statistical VWAP std-dev bands; GM10 offers an SD/measured-move projection target (`TP Type = 1`). Helper `GMStruct.SDExtension()` is reusable. **ChartFanatics/Roboquant/Casper & social creators** = the same archetypes already mechanized above — paste a specific rule set to extend.

## Install (cAlgo) — IMPORTANT

C# has no `#include`. The shared `GODMODE_Core.cs` must be part of each cBot's compilation. Two ways:

**Option A — one cBot at a time (simplest):**
1. In cAlgo: **New cBot**, name it e.g. `GM01_OpeningRangeBreakout`, paste that file's contents.
2. In the cBot's code editor, **add `GODMODE_Core.cs` to the same project**: the cAlgo editor lets you add additional source files to a cBot (the Solution panel → right-click → Add). Paste `GODMODE_Core.cs` there.
3. Build. Repeat per cBot.

**Option B — shared across all (cleaner):** put `GODMODE_Core.cs` once and reference it from each cBot project, or compile it into a referenced library. If your cAlgo version doesn't expose multi-file projects easily, just paste the contents of `GODMODE_Core.cs` at the top of each cBot file *inside the same `cAlgo.Robots` file* (remove the duplicate `using` lines) — it will compile as one unit.

> The `GODMODE.Core` namespace keeps all shared types out of the way; each cBot already has `using GODMODE.Core;`.

## Key cTrader differences vs MT5

- **Volume is in UNITS** (not lots). `GMUtil.CalcVolume` sizes via `Symbol.PipValue` and `NormalizeVolumeInUnits`, with the same min-volume risk guard for tiny accounts.
- Logic runs in **`OnBar`** (new closed bar); position management in **`OnTick`**.
- Positions are tracked by **`Label`** (each cBot uses its own, e.g. `"GM01"`) — set a unique label/instance per chart so cBots don't touch each other's trades.
- Session hours use **`Server.Time` + `Offset Hours`** (cBots run in UTC timezone). Set `Offset Hours` and the hour inputs to frame your sessions (e.g. SAST = UTC+2).
- Journals write to **My Documents** (`GODMODE_GMxx_*_log.csv`).

## Backtest protocol (same as MT5 README §6)
One cBot, one symbol, **tick data**, ≥6 months, ≥200 trades before trusting any win rate. Rank by **profit factor / expectancy, not win rate**. GM09 needs **tick-data backtesting** (m1-bar-from-server makes delta/CVD synthetic). Keep only the archetypes that prove out on your data; run uncorrelated survivors together.
