# NinjaTrader 8 (NT8) C# → cAlgo C# Conversion

Why this matters: order-flow tooling has a long C# heritage (Bookmap, OrderFlowKit, Wyckoff renders). Most retail order-flow code in the wild is NT8 C#. cTrader's cAlgo is also C# — porting is *95% renames* if you know the API differences.

## 1. Class skeleton

| NT8 | cAlgo |
|---|---|
| `public class MyInd : Indicator` | `[Indicator(...)] public class MyInd : Indicator` |
| `protected override void OnStateChange()` (with `State.Configure`, `State.DataLoaded`) | `protected override void Initialize()` |
| `protected override void OnBarUpdate()` | `public override void Calculate(int index)` |
| `protected override void OnRender(ChartControl, ChartScale)` | `protected override void OnPaint()` (limited) — most NT8 OnRender chart drawing is replaced with `Chart.Draw*` calls |

## 2. Bar / price access

| NT8 | cAlgo |
|---|---|
| `Close[i]` (i = bars ago) | `Bars[Bars.Count - 1 - i].Close` |
| `Open[i] / High[i] / Low[i]` | analogous |
| `Volume[i]` | `Bars[Bars.Count - 1 - i].TickVolume` |
| `Time[i]` | `Bars[Bars.Count - 1 - i].OpenTime` |
| `CurrentBar` | `Bars.Count - 1` |

## 3. Order-flow / volume

NT8 exposes per-trade tick info via `OnMarketData` and bar-level bid/ask volume via `BarsRequest` / `OrderFlowVolumetric` (paid). cAlgo equivalents:

| NT8 | cAlgo |
|---|---|
| `OnMarketData(MarketDataEventArgs e)` (with `MarketDataType.Last/Bid/Ask`) | inside `OnTick`, classify against `Symbol.Bid/Ask` |
| `Bars.GetBar(i).BidVolume` (volumetric) | reconstruct via tick classifier (see `ctrader_calgo_patterns.md §3`) |
| Level-2 via `OnRender` of DOM | `Symbol.MarketDepth.Updated` |

## 4. Drawing / rendering

| NT8 (`OnRender`) | cAlgo |
|---|---|
| `RenderTarget.DrawText(...)` | `Chart.DrawText(...)` / `Chart.DrawStaticText(...)` |
| `RenderTarget.DrawLine(...)` | `Chart.DrawTrendLine(...)` |
| `RenderTarget.FillRectangle(...)` | `Chart.DrawRectangle(...)` |

cAlgo's chart drawing API is higher-level — you don't manage Direct2D resources.

## 5. Strategy / order helpers

| NT8 (`Strategy`) | cAlgo (`Robot`) |
|---|---|
| `EnterLong(quantity, signalName)` | `ExecuteMarketOrder(TradeType.Buy, Symbol.Name, units, label, slPips, tpPips)` |
| `ExitLong()` | `foreach(var p in Positions.Where(...)) ClosePosition(p)` |
| `Position.Quantity / Position.MarketPosition` | `Positions.FindAll(label, Symbol.Name)` |

## 6. Direct C# parity (no API layer)

Pure C# (LINQ, `List<T>`, `Dictionary<TK,TV>`, struct, `async`, lambdas) ports cleanly. The OrderFlowKit primitives in `CSharp-NT8-OrderFlowKit-main/OrderFlow.cs` (cluster reconstruction, POC/POI computation, imbalance detection, heatmap painting math) can be lifted nearly verbatim into a cAlgo indicator, with the API renames above and `Chart.Draw*` replacing the SharpDX render calls.

## 7. Gotchas

1. **Tick replay** — NT8 can replay tick-by-tick historicals; cAlgo backtesting uses tick or bar data depending on broker. Document the assumption.
2. **State machine** — NT8 has explicit lifecycle states (`Configure`, `DataLoaded`, `Realtime`); cAlgo just has `Initialize` / `OnStart` and a runtime flag (`IsBacktesting`).
3. **DataSeries class** — NT8 uses `DataSeries`/`Series<T>`. cAlgo uses `IndicatorDataSeries`. Set values via `Result[index] = value`.

