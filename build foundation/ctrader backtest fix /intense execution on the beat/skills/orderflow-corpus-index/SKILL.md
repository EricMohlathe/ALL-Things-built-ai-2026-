---
name: orderflow-corpus-index
description: Master index of the user's order-flow project workspace ("agent skill builds"). Catalogues every repository in the workspace and explains what to lift from each. Use when starting a fresh task, when the user says "look at my whole project", "use everything in the directory", "what resources do I have", "scan the workspace".
---

# Order-Flow Corpus Index

This skill is the table of contents for the user's local project. Other skills load this file once to know which folder holds which capability.

## Inventory (relative to workspace root `agent skill builds/`)

### Order-flow indicators / kits
- `CSharp-NT8-OrderFlowKit-main/` — NT8 C# OrderFlow indicators (Bookmap, OrderFlow, VolumeProfile, VolumeFilter, MarketVolume + AddOns/WyckoffRender, AddOns/SE). Reference for cTrader cAlgo since both are C#.
- `OrderFlow-Analysis-Pro-master/` — Python order-flow analytics: footprint engine, delta engine, orderbook tracker; pattern detectors for absorption, exhaustion, initiative, sweep, divergence. Authoritative *logic* source.
- `mev-aware-orderflow-viz-main/` — order-flow visualisation with MEV awareness (crypto-flavoured but visual primitives transfer).
- `horus-flow-mcp-main/` — MCP server exposing institutional L2 microstructure intelligence (spoofing, momentum, 5-second deltas). Useful as live data feed for an EA via MCP.

### Trading systems / agents
- `Market-Swarm-Agents--main/` — multi-agent market simulation (with `tests/testdata/orderflow` test corpus).
- `TradingAgents-AShare-main/` — A-share trading agent system.
- `ai-trading-agent-main/` — AI trading agent reference.
- `mt5_AI_trading_bot-main/` — MT5 + reinforcement-learning bot, includes weights and EUR_USD CSVs (price data for offline replay).
- `trade_flow-main/` — full trade-flow framework with `docs/books/` PDFs (academic backing).
- `tradememory-protocol-master/` — trade-memory protocol (relevant for journaling / postmortem).
- `claude-code-trading-terminal-main/` — terminal-based Claude trading commands, has `slash-commands/`.
- `claude-enterprise-openclaw-trading-main/` — enterprise-flavoured trading skill set.
- `claude-trading-skills-main/` — existing Claude trading skill examples (strategy framework, ta-lib, backtrader, sybil-detection, jito-bundles, tax-liability-tracking).
- `QuantDinger-main/` — quant trading (additional reference).

### Lift list (what to copy idea-for-idea into our skill output)

| Source | Concept | Land in our skill at |
|---|---|---|
| `CSharp-NT8-OrderFlowKit-main/OrderFlow.cs` | Cluster reconstruction, POC/POI rendering | `references/ctrader_calgo_patterns.md` + `references/nt8_to_ctrader_csharp.md` |
| `CSharp-NT8-OrderFlowKit-main/VolumeAnalysisProfile.cs` | Value area + horizontal volume profile | `references/orderflow_primitives.md §6` |
| `OrderFlow-Analysis-Pro-master/orderflow_system/patterns/absorption.py` | Absorption rule (effort vs result) | `references/orderflow_signal_logic.md §A` |
| `OrderFlow-Analysis-Pro-master/orderflow_system/patterns/exhaustion.py` | Exhaustion rule (declining vol + delta) | `references/orderflow_signal_logic.md §B` |
| `OrderFlow-Analysis-Pro-master/orderflow_system/patterns/initiative.py` | Initiative rule | `references/orderflow_signal_logic.md §C` |
| `OrderFlow-Analysis-Pro-master/orderflow_system/patterns/sweep.py` | Book sweep rule | `references/orderflow_signal_logic.md §D` |
| `OrderFlow-Analysis-Pro-master/orderflow_system/patterns/divergence.py` | Delta divergence rule | `references/orderflow_signal_logic.md §E` |
| `horus-flow-mcp-main/SKILL.md` | MCP-fed live microstructure | optional ingestion in the EA via Claude Code MCP integration |
| `claude-trading-skills-main/skills/strategy-framework/SKILL.md` | Strategy template structure | informs `orderflow-mt5-ctrader-mastery` Phase 1 |
| `mt5_AI_trading_bot-main/real_net/ma2c/price_data/EUR_USD.csv` | Offline replay data | use for parity / sanity tests |
| `trade_flow-main/docs/books/ssrn-4697929.pdf` | Academic basis | indexed in `orderflow-pdf-research-corpus` |
| `trade_flow-main/docs/books/1911.10107v1.pdf` | Academic basis (RL/agents) | indexed in `orderflow-pdf-research-corpus` |

## How to read this file
Other skills (especially `orderflow-mt5-ctrader-mastery`) load this once at the start of a session. It saves them re-scanning the workspace and lets them point the user back to existing artefacts instead of regenerating from scratch.

## Maintenance
When new repos land in `agent skill builds/`, append a row to the inventory and a row to the lift list.
