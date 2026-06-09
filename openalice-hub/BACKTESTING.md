# Backtesting

The hub has a built-in, pure-stdlib backtester. **Real market data, no API keys.**

## Run one
```bash
cd ~/ai-tools/trading/openalice-hub
python3 hub.py backtest sma_cross BTCUSDT            # crypto (Binance)
python3 hub.py backtest donchian  BTCUSDT
python3 hub.py backtest rsi2      ETHUSDT
python3 hub.py backtest sma_cross AAPL --source yahoo   # stocks (Yahoo)
python3 hub.py backtest donchian  SPY  --source yahoo --interval 1d
python3 hub.py backtest sma_cross MYDATA.csv --source csv   # your own data
```

## Data sources (no keys)
| source | use for | example symbols |
|--------|---------|-----------------|
| `binance` (default) | crypto | BTCUSDT, ETHUSDT, SOLUSDT |
| `yahoo` | stocks / ETF / FX | AAPL, SPY, MSFT, EURUSD=X |
| `csv` | your own | path to a CSV with date,open,high,low,close,volume |

Check data first: `python3 hub.py data BTCUSDT` / `python3 hub.py data AAPL --source yahoo`.

## Built-in strategies
- `sma_cross` — 20/50 SMA trend follow
- `rsi2` — Connors RSI(2) mean-reversion above the 200-SMA
- `donchian` — 20/10 channel breakout

## What the tearsheet reports
Total return, **buy & hold benchmark + alpha**, CAGR, Sharpe, Sortino, max drawdown,
annual vol, trade count, win-rate, profit factor.

## Honesty guarantees (by construction)
- Signals use data only **up to bar i's close**; trades **fill at bar i+1's open** → no lookahead.
- Fees charged on traded notional (`--fee` bps, default 10).
- Every simulated fill routes through the **paper ExecutionGate** and is written to `logs/audit.log`.
- **Past performance ≠ future results.** These are simple baselines; good backtest ≠ good live.

## Add your own strategy
Drop a class in `openalice_hub/strategies/builtin.py` implementing
`positions(self, bars) -> list[int]` (1=long, 0=flat, -1=short) and add it to `REGISTRY`.

## Upstream engines (optional, heavier)
- **freqAI-LSTM** → run via [freqtrade](https://www.freqtrade.io): copy `repos/freqAI-LSTM`
  strategy into a freqtrade `user_data/strategies/` dir and `freqtrade backtesting`.
- **trade_flow / QuantMuse** → have their own backtest tooling; see their READMEs.
The hub's own engine above needs none of them.
