# OpenAlice Hub

An orchestration layer over [OpenAlice](https://github.com/TraderAlice/OpenAlice) and
17 other trading/AI repos. **It does not merge them into one binary** — they're
heterogeneous (Python strategies, an LSTM freqtrade strat, agent swarms, MCP
servers). Instead the hub gives them one control surface, a pluggable connector/AI
layer, and a hard safety gate.

## ⚠️ Safety first (read this)
- **No profit is promised or possible to guarantee. Automated trading can lose money.**
- **Default mode is PAPER** — orders are simulated, nothing is sent to any exchange.
- **LIVE orders cannot fire autonomously.** Every real order must pass `ExecutionGate`,
  which requires a *human-typed, per-order, 120-second token*. No AI/agent can self-confirm.
- This is not financial advice.

## Layers
1. **Connectors** (`registry/connectors.json`) — trading-platform MCPs. Ships wired:
   `tradingview-mcp` (read/analyze your TradingView Desktop charts). Add any platform:
   `python3 hub.py add-connector --name X --mcp "npx -y X-mcp" --exec`
2. **AI backends** (`registry/ai_backends.json`) — `claude` (native), `hermes-9router`
   (Hermes / any model via the local 9router gateway), and a slot for **your own**
   OpenAI-compatible AIs: `python3 hub.py add-ai --name mybrain --base-url ... --model ...`
3. **Strategy modules** (`registry/strategies.json`) — the 18 repos behind one adapter
   interface. Deep-wired incrementally; `hub.py strategies` shows what's present.
4. **Execution gate** (`openalice_hub/core/execution_gate.py`) — the single choke point.
5. **Dashboard + DMG** — `build_hub_dashboard.py` → `dashboard/`; `build_hub_app.sh` → `.dmg`.

## Use
```bash
python3 hub.py status          # safety banner + counts
python3 hub.py connectors      # platform MCPs (+ the claude mcp add line)
python3 hub.py ai              # AI backends + reachability
python3 hub.py strategies      # the 18 modules
python3 hub.py analyze BTCUSDT
python3 hub.py paper BTCUSDT buy 0.1 --price 65000   # simulated fill
python3 hub.py live-arm BTCUSDT buy 0.1              # shows the human-confirm gate (locked by default)
```

## Setup from a fresh clone
```bash
bash CLONE-UPSTREAMS.sh         # re-fetch the 18 upstream repos (not vendored here)
python3 build_hub_dashboard.py  # regenerate dashboard
```

## Attaching Hermes
Hermes (Nous agent) attaches via the `hermes-9router` AI backend — point it at the
local 9router gateway (`http://127.0.0.1:20128/v1`). Set it up later; the slot is ready.

## Upstreams (18)
OpenAlice · AI-Trader · QuantDinger · moon-dev-ai-agents · tradingview-mcp · QuantMuse ·
ai-trading-claude · freqAI-LSTM · tradememory-protocol · ForexTradingBot · TradingBot ·
Market-Swarm-Agents · trade_flow · Forex-Trading-AI · forex-ai-trader · tradeclaw ·
crypto-arbitrage-bot · trading-ops. Each remains under its own license.
