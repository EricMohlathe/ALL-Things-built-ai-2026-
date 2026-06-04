# Intense Execution on the Beat

This folder is the deliverable for the order-flow EA mastery build. It contains a fully-wired skill suite that turns Claude Code into a production-grade order-flow EA author for **MetaTrader 5 (MQL5)** and **cTrader (cAlgo / C#)**.

## What's in here

```
intense execution on the beat/
└── skills/
    ├── orderflow-mt5-ctrader-mastery/        ★ PRIMARY SKILL
    │   ├── SKILL.md
    │   ├── references/   (11 reference files, ~1330 lines of curated knowledge)
    │   ├── templates/    (4 production scaffolds — MT5 EA + indicator, cTrader cBot + indicator)
    │   └── examples/     (4 worked examples — absorption + CVD divergence on both platforms)
    ├── mql5-orderflow-deep/                  ── platform-pinned MT5 sibling
    ├── ctrader-cbot-deep/                    ── platform-pinned cTrader sibling
    ├── mql5-csharp-language-bridge/          ── MQL5 ↔ C# (cAlgo / NT8) translator
    ├── orderflow-corpus-index/               ── master index of every repo in agents skill builds/
    ├── orderflow-pdf-research-corpus/        ── pointer to the SSRN + arXiv PDFs
    └── orderflow-images-visual-grammar/      ── pointer to the NT8 OrderFlowKit images
```

## How to use this with Claude Code

1. Either drop the entire `skills/` folder into Claude Code's user-skills directory, or invoke the primary skill name directly: `orderflow-mt5-ctrader-mastery`.
2. Ask Claude Code to build any order-flow EA for MT5, cTrader, or both. Examples:
   - *"Build an absorption EA for MT5 and cTrader on EURUSD M5 with 0.5% risk."*
   - *"Convert this Pine Script absorption indicator to MQL5 and cAlgo."*
   - *"Audit my existing MT5 EA and produce a cTrader port with parity verification."*
3. The skill will:
   - Clarify the playbook (Phase 1).
   - Map primitives to Wyckoff/AMT phases (Phase 2).
   - Pick the right architecture (Phase 3).
   - Drop into the production templates (Phase 4).
   - Run the cross-platform parity check (Phase 5).
   - Emit backtest scaffolding + a "first-tick sanity test" (Phase 6).

## Source corpus assimilated

The skill was distilled from the user's `agent skill builds/` workspace, including:

- **NT8 OrderFlowKit** (C#) — Bookmap, OrderFlow/footprint, VolumeAnalysisProfile, VolumeFilter, MarketVolume, Wyckoff renderers.
- **OrderFlow-Analysis-Pro** (Python) — algorithmic detectors for absorption, exhaustion, initiative, sweep, divergence.
- **Horus Flow MCP** — institutional L2 microstructure intelligence reference.
- **mt5_AI_trading_bot** — multi-agent A2C reference, EUR_USD price data for offline replay.
- **trade_flow** — full framework + SSRN paper + arXiv preprint.
- **claude-trading-skills** — strategy-framework template that informs Phase 1.
- **Pine Script / cTrader** indicators in the workspace — used as conceptual basis for the conversion guide.

## Key features of the primary skill

- **Compilable code, both platforms.** Templates compile on MetaEditor (MT5) and cTrader Automate without modification.
- **Risk-first architecture.** Every EA wires daily-loss halt, total-DD halt, spread guard, session filter, cooldown, max-positions, magic-isolation **before** any signal logic.
- **Order-flow primitives only.** Delta, CVD, footprint, POC/POI, value area, absorption, exhaustion, initiative, sweep, divergence, AMT phase machine, Wyckoff 2.0 events.
- **Translation discipline.** MQL5 ↔ C# idiom table covers indexing direction, lots-vs-units, pips-vs-points, server-time vs UTC, SL/TP semantics.
- **Token-disciplined.** Reference files are loaded only when the routing table fires. Templates load only when emitting code. Examples load on explicit request.

## Provenance

Every concept is traceable: `orderflow-corpus-index/SKILL.md` lists exactly which file in the workspace inspired which section of the skill.

