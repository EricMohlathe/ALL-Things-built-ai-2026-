# Pine Script v5 → MQL5 + cAlgo C# Conversion Guide

A concept-by-concept mapping that lets you take a TradingView indicator/strategy and emit working MT5 / cTrader equivalents.

## 1. Series + history access

| Pine v5 | MQL5 | cAlgo |
|---|---|---|
| `close` | `iClose(_Symbol,_Period,0)` | `Bars.LastBar.Close` |
| `close[1]` | `iClose(_Symbol,_Period,1)` | `Bars[Bars.Count-2].Close` |
| `bar_index` | `Bars(_Symbol,_Period)-1` | `Bars.Count - 1` |
| `time` | `iTime(_Symbol,_Period,0)` | `Bars.LastBar.OpenTime` |
| `volume` | `iVolume(_Symbol,_Period,0)` | `Bars.LastBar.TickVolume` |

## 2. Built-ins

| Pine | MQL5 | cAlgo |
|---|---|---|
| `ta.sma(close, n)` | `iMA(_Symbol,_Period,n,0,MODE_SMA,PRICE_CLOSE)` (then CopyBuffer) | `Indicators.SimpleMovingAverage(Bars.ClosePrices, n).Result.LastValue` |
| `ta.ema` | `iMA(... MODE_EMA ...)` | `Indicators.ExponentialMovingAverage(...)` |
| `ta.rsi` | `iRSI` | `Indicators.RelativeStrengthIndex(...)` |
| `ta.atr` | `iATR` | `Indicators.AverageTrueRange(...)` |
| `ta.crossover(a,b)` | manual: `a[1]<b[1] && a[0]>b[0]` | `a.HasCrossedAbove(b, 0)` |
| `math.abs / max / min` | `MathAbs / MathMax / MathMin` | `Math.Abs / Math.Max / Math.Min` |

## 3. Strategy primitives

| Pine | MQL5 (CTrade) | cAlgo |
|---|---|---|
| `strategy.entry("L", strategy.long)` | `trade.Buy(lots,_Symbol,0,sl,tp,InpComment)` | `ExecuteMarketOrder(TradeType.Buy,Symbol.Name,units,label,slPips,tpPips)` |
| `strategy.exit("X","L",stop=sl,limit=tp)` | already on entry, or `trade.PositionModify` | already on entry, or `ModifyPosition` |
| `strategy.close_all()` | loop `PositionsTotal()` + `trade.PositionClose` | `foreach (var p in Positions) ClosePosition(p);` |

## 4. Plotting → on-chart text/objects

| Pine | MQL5 | cAlgo |
|---|---|---|
| `plot(value)` | `ObjectCreate` / `ObjectSetDouble` (line objects) or set buffer in indicator | `Chart.DrawTrendLine(...)` |
| `plotshape` | `ObjectCreate(name, OBJ_ARROW_BUY, ...)` | `Chart.DrawIcon(...)` |
| `bgcolor` | `ObjectCreate(... OBJ_RECTANGLE ...)` | `Chart.DrawRectangle(...)` |
| `label.new` | `ObjectCreate(... OBJ_TEXT ...)` | `Chart.DrawText(...)` |

## 5. Pine `var` (initialise once)

Pine `var x = 0` ≈ a class field initialised once.
- MQL5: declare globally outside `OnTick`; init once in `OnInit`.
- cAlgo: a class field; initialise in `OnStart`.

## 6. Repainting & non-repainting

Pine code that uses `barstate.isconfirmed` ≈ "act only on closed bars". Mirror with:
- MQL5: bar-close gate (`IsNewBar()` from `mql5_orderflow_patterns.md`).
- cAlgo: `OnBar` instead of `OnTick`, or `IsNewBar()`.

## 7. Order-flow specific Pine patterns

| Pine pattern | MQL5 / cAlgo equivalent |
|---|---|
| Cumulative delta via `volume * sign(close-open)` | Same: `signedVolume = volume * (close>open?1:close<open?-1:0)` |
| Footprint approximation via `request.security("",timeframe.period,...)` looping | Per-tick classifier (preferred) — see `mql5_orderflow_patterns.md §3` / `ctrader_calgo_patterns.md §3` |
| `ta.linreg(cvd, lookback)` for CVD slope | Linear regression manually over the last N CVD points |
| `box.new` to mark imbalance zones | `OBJ_RECTANGLE` (MQL5) / `Chart.DrawRectangle` (cAlgo) |

## 8. Signal-emission style

Pine uses `alertcondition`. Replace with:
- MQL5: `Alert(...)` / `SendNotification(...)` / push.
- cAlgo: `Notifications.PlaySound(...)` / `Notifications.SendEmail(...)`.

## 9. Conversion checklist

1. Identify all `var` and `varip` — these are persistent state.
2. Identify all `ta.*` calls and replace with native indicator calls.
3. Identify all `request.security` cross-TF calls and replace with `iCustom`/`MarketData.GetBars`.
4. Identify all `[1]` history references — port to inverted indexing in cAlgo.
5. Compile, then run a **side-by-side bar test** with the same data window. Trade lists should match within 1–2 bars of slack.

