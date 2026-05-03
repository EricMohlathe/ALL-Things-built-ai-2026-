# GODMODE_OFEA

Production-grade order-flow trading EA delivered as two behaviourally-identical, parameter-mirrored builds:

- **MetaTrader 5** — `mt5/GODMODE_OFEA/Experts/GODMODE_OFEA/GODMODE_OFEA.mq5` (MQL5)
- **cTrader / cAlgo** — `ctrader/GODMODE_OFEA/GODMODE_OFEA.cs` (C#)

Same trading thesis, same parameters, same numbers. Different syntax, identical behaviour.

## What it does

Trades the institutional order-flow thesis articulated in the build brief — react to state-change signatures (absorption, stacked imbalances, CVD divergence, aggression prints) at high-probability volume-profile locations during high-probability sessions, with HTF alignment.

Implementation enforces the **5-gate confluence stack** (brief §2):

| Gate | Filter | Failure action |
|------|--------|----------------|
| F1 | Triple Confluence (VP + Footprint + Kill Zone) | Skip |
| F2 | Kill Zone Discipline (LDN Main 11:00–15:30 SAST or NY Main 17:30–21:00 SAST) | Skip |
| F3 | HTF Alignment (H4 EMA(20) + D1 EMA(50)) | Skip or half-size |
| F4 | CVD Confirmation | Skip |
| F5 | Profile-State Check (D-shape → M2, b/P/Thin → M1) | Skip |

…routed across the **25-setup catalogue** (brief §6) covering Absorption Reversals, VP Setups, Stacked Imbalances, Wyckoff 2.0 (Spring/Upthrust/SOS/LPSY), ICT/SMC fusion (LiqSweep/OB Return/SMT/Breaker/AMD), and Microstructure (UnfAuc/PoorHL/Iceberg).

## Modes

- **MODE_MANUAL** (default for first 30 days) — full notification cascade fires, dashboard updates, chart markers draw — but no orders are placed. Operator validates the EA's "thinking" against live market behaviour.
- **MODE_AUTO** — same cascade, plus order placement when all gates pass.

The user-story acceptance test in brief §18 is reproducible end-to-end on a demo chart in either mode.

## Install

### MetaTrader 5

1. Open MetaTrader 5 → File → Open Data Folder → `MQL5/`.
2. Copy `mt5/GODMODE_OFEA/Include/*.mqh` into `MQL5/Include/` (create a `GODMODE_OFEA/` subfolder there if you want clean namespacing).
3. Copy `mt5/GODMODE_OFEA/Experts/GODMODE_OFEA/GODMODE_OFEA.mq5` into `MQL5/Experts/`.
4. Open MetaEditor → compile `GODMODE_OFEA.mq5`. Expect zero warnings, zero errors.
5. In MT5, drag `GODMODE_OFEA` onto an EURUSD M5 chart. Confirm dashboard appears top-right and `OperatingMode = MANUAL` in the inputs panel.
6. Allow Algo Trading. Watch one bar of London Main or NY Main session. Verify notifications fire and dots flip.

### cTrader

1. Open cTrader → Automate.
2. New cBot → paste `ctrader/GODMODE_OFEA/GODMODE_OFEA.cs` and the contents of `ctrader/GODMODE_OFEA/Modules/*.cs` into a single project (or use an external editor and reference all files in your `.algoproject`).
3. Build. Expect zero warnings.
4. Add a new cBot instance to an EURUSD m5 chart. Configure parameters (defaults match the brief §7 schema).
5. Start. Verify dashboard renders and notifications fire on session entry.

## Configure

Brief §7 is the canonical input schema. All parameter names are byte-identical across MT5 and cTrader.

Critical defaults to verify before going live:

| Parameter | Default | Why |
|-----------|---------|-----|
| `OperatingMode` | MANUAL | First 30 days, watch only |
| `RiskPct` | 1.0 | Hard-capped at 2.0 by RiskManager (brief §12 rule 2) |
| `MaxDDPct` | 5.0 | Day halts when daily loss hits this |
| `MaxConsecLosses` | 3 | Day halt after this many consecutive losses |
| `MinAbsorptionStars` | 3 | Brief §11.4 — 5-component confidence formula |
| `SAST_OffsetFromBroker` | 0 | Adjust if broker time ≠ UTC |
| `MagicNumber` | 202604 | Position-iteration filter — change per account |

The marginal-gain stack (M1–M6) defaults to OFF — earn enablement via 100+ logged trades per brief §22 / Appendix A.

## Run

The EA is event-driven. No `Sleep()` or busy-wait anywhere. Lifecycle:

```
OnTick (per tick):
  ├─ accumulate tick-level buy/sell volumes
  ├─ refresh dashboard if 250ms elapsed
  └─ manage open position (partial close, BE move, ATR trail, POC exit)

OnBar / new-bar guard (per bar close):
  ├─ snapshot bar delta, update CVD
  ├─ recompute volume profile
  ├─ run gate pipeline 0 → 8 (brief §5)
  ├─ score 25 setups, pick highest priority
  └─ execute (AUTO) or notify (MANUAL)
```

Logs append to `MyDocuments/GODMODE_OFEA_log.csv` (cTrader) or `MQL5/Files/GODMODE_OFEA_log.csv` (MT5). Schema per brief §13 — operator-readable in plain Excel.

## Testing

See [TESTING.md](TESTING.md) for the full §14 acceptance protocol. Summary:

- 6-month minimum backtest on EURUSD M5, "every tick based on real ticks" mode.
- Acceptance: Profit Factor ≥ 1.5, Recovery Factor ≥ 2.0, Max DD ≤ 12%.
- Forward-test 2 weeks demo at 0.25× size before live.
- A/B both builds simultaneously, compare fill prices and signal agreement.

## Operating ceiling (honest)

Brief §21 + §24 sets the realistic ceiling: **76–78% sustained win rate, +1.85R/trade expectancy, 5–15 trades/day distributed across 3–6 symbols** when the marginal-gain stack is enabled. Rolling 50-trade samples may touch 80–82% in favourable regimes — but win rate is a downstream consequence of disciplined gate enforcement, not a tuning target. Capital protection > expectancy > win rate.

## Source authority

The brief is the sovereign specification. Brief content synthesised from: Fabio Valentini AMT Strategy Guide, Wyckoff 2.0 (Villahermosa), Mind Math Money 83-min OFT course, Darius FX foundations, Fractal Flow Volume Profile masterclass, Chart Fanatics live sessions, JacobS369 Absorption Signals, ICT/SMC integration, Trader Dale Volume Profile Insider Guide, plus the 69+ document research corpus referenced in Order Flow Dive 2.0.

See `docs/architecture.md` for module-level wiring, `docs/confluence_examples.md` for five worked notification cascades, and `docs/parameter_tuning.md` for the optimisation order.
