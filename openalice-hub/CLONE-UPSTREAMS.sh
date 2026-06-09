#!/bin/bash
# Re-clone the 18 upstream trading repos the hub orchestrates.
# They are NOT vendored into this repo (their own licenses). Run once after cloning.
set -e
DST="$(cd "$(dirname "$0")/.." && pwd)/repos"
mkdir -p "$DST"; cd "$DST"
export GIT_LFS_SKIP_SMUDGE=1
clone(){ d="${2:-$(basename "$1")}"; [ -d "$d/.git" ] || git clone --depth 1 "https://github.com/$1.git" "$d"; }
clone TraderAlice/OpenAlice
clone HKUDS/AI-Trader
clone brokermr810/QuantDinger
clone daydy-dev/moon-dev-ai-agents-for-trading
clone tradesdontlie/tradingview-mcp
clone 0xemmkty/QuantMuse
clone zubair-trabzada/ai-trading-claude
clone Netanelshoshan/freqAI-LSTM
clone mnemox-ai/tradememory-protocol
clone Opselon/ForexTradingBot
clone Gifted87/TradingBot
clone TheSnowGuru/Market-Swarm-Agents- Market-Swarm-Agents
clone fortesenselabs/trade_flow
clone kacf/Forex-Trading-AI
clone Viajante80/forex-ai-trader
clone naimkatiman/tradeclaw
clone Cortex-AI-Network/crypto-arbitrage-bot-automated-trading crypto-arbitrage-bot
clone l3lackcurtains/trading-ops
echo "done -> $DST"
