# OpenAlice Hub × GODMODE Trading OS

The hub is now **configured with** your repo
[`EricMohlathe/ALL-Things-built-ai-2026-`](https://github.com/EricMohlathe/ALL-Things-built-ai-2026-)
(GODMODE Trading OS). A local reference clone lives at `~/ai-tools/trading/godmode-repo`
(`config.json → godmode_repo`).

## What got wired in
- **26 GODMODE EAs** (GM01–GM26) registered as strategy modules (`kind: godmode-ea`,
  `lang: csharp`). `python3 hub.py strategies` lists them. Each `run_hint` points at the
  cBot + `EA_BACKTEST_OPTIMIZATION_MANUAL.md`.
- **Platform connectors** added: `ctrader` (26 cBots, cAlgo), `mt5` (GODMODE Experts/
  Indicators), `tradingview-godmode` (the Pine dashboard). Plus the already-wired live
  `tradingview-mcp`. `python3 hub.py connectors` shows them.
- `config.json` records `platforms: [binance, yahoo, mt5, ctrader, tradingview]`.

## Honesty contract — shared
Your brief says *"Never display fabricated win rates. All performance numbers come from
real backtests or live broker fills."* The hub enforces exactly this:
- backtests use **real data, no lookahead, fees**, every fill logged through the paper gate;
- the optimizer reports **out-of-sample** decay so in-sample overfit can't masquerade as edge;
- live orders need a **human-typed per-order token** — no fabricated fills, no autopilot.

## How execution maps (paper-safe today)
| Platform | Today | To go live |
|---|---|---|
| Binance / Yahoo | backtest + paper now | — (data only here) |
| cTrader (GM01–26) | optimize in cAlgo Strategy Tester; reference in hub | wire cTrader Open API behind `ExecutionGate`; flip `live_enabled` + token per order |
| MT5 | reference GODMODE Experts | bridge Python `MetaTrader5` pkg behind `ExecutionGate` |
| TradingView | read/analyze via `tradingview-mcp` (Desktop) | — (read only) |

> The hub does **not** re-implement your 26 C# EAs — they run in cTrader/MT5. The hub
> indexes, references, and (when you wire a broker bridge) routes their orders through the
> single gated path. The Python backtester/optimizer is for fast research on data the hub
> can fetch directly.

## Push this into your repo
Nothing is pushed yet (needs your GitHub auth). A staged branch is prepared — see the
commands the assistant printed, or:
```bash
gh auth login
cd ~/ai-tools/trading/godmode-repo
git checkout -b openalice-hub-integration
cp -R ~/ai-tools/trading/openalice-hub ./openalice-hub
git add openalice-hub && git commit -m "Add OpenAlice Hub (orchestration + backtest/optimizer, paper-gated)"
git push -u origin openalice-hub-integration
# then open a PR into godmode-ofea-workspace or main
```
