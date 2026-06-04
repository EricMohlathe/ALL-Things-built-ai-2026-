# MQL5 ↔ C# (cAlgo) — Idiom Conversion Table

The single lookup any agent needs when porting between MetaTrader 5 and cTrader. Entries are arranged as **MQL5 → cAlgo** and **cAlgo → MQL5** for round-tripping.

## 1. Bars / candles

| Concept | MQL5 | cAlgo |
|---|---|---|
| Open of bar `i` | `iOpen(_Symbol,_Period,i)` | `Bars[Bars.Count-1-i].Open` |
| Close of bar `i` | `iClose(_Symbol,_Period,i)` | `Bars[Bars.Count-1-i].Close` |
| High / Low | `iHigh / iLow` | `Bars[..].High / .Low` |
| Time of bar | `iTime(_Symbol,_Period,i)` | `Bars[..].OpenTime` |
| Volume of bar | `iVolume(_Symbol,_Period,i)` | `Bars[..].TickVolume` |
| Bar count | `Bars(_Symbol,_Period)` | `Bars.Count` |

> **Indexing direction.** MQL5 uses *0 = newest, increasing back in time*. cAlgo uses *Count−1 = newest, decreasing back in time*. Convert via `i_calgo = Bars.Count − 1 − i_mql5`.

## 2. Symbol / quote

| MQL5 | cAlgo |
|---|---|
| `SymbolInfoDouble(_Symbol,SYMBOL_BID)` | `Symbol.Bid` |
| `SymbolInfoDouble(_Symbol,SYMBOL_ASK)` | `Symbol.Ask` |
| `SymbolInfoDouble(_Symbol,SYMBOL_POINT)` | `Symbol.TickSize` (≈ point) / `Symbol.PipSize` |
| `_Digits` | `Symbol.Digits` |
| `SymbolInfoInteger(_Symbol,SYMBOL_SPREAD)` (points) | `(Symbol.Ask − Symbol.Bid) / Symbol.PipSize` |
| `SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE)` | `Symbol.PipValue * Symbol.PipSize / Symbol.TickSize` (approx) |
| `NormalizeDouble(p, _Digits)` | `Symbol.NormalizePrice(p)` |

## 3. Account

| MQL5 | cAlgo |
|---|---|
| `AccountInfoDouble(ACCOUNT_BALANCE)` | `Account.Balance` |
| `AccountInfoDouble(ACCOUNT_EQUITY)` | `Account.Equity` |
| `AccountInfoDouble(ACCOUNT_MARGIN_FREE)` | `Account.FreeMargin` |
| `AccountInfoString(ACCOUNT_CURRENCY)` | `Account.Asset.Name` |

## 4. Time

| MQL5 | cAlgo |
|---|---|
| `TimeCurrent()` (server time) | `Server.Time` |
| `TimeLocal()` | `DateTime.Now` |
| `MqlDateTime mt; TimeToStruct(t, mt); mt.hour;` | `t.Hour` (DateTime) |

## 5. Orders / positions

| MQL5 (CTrade) | cAlgo |
|---|---|
| `trade.Buy(lots, _Symbol, 0, sl, tp, comment);` | `ExecuteMarketOrder(TradeType.Buy, Symbol.Name, units, label, slPips, tpPips);` |
| `trade.Sell(...)` | `ExecuteMarketOrder(TradeType.Sell, ...)` |
| `PositionsTotal()` / `PositionGetSymbol(i)` / `PositionGetTicket(i)` | `Positions` collection (LINQ-friendly) |
| `trade.PositionClose(ticket)` | `ClosePosition(position)` |
| `trade.PositionModify(ticket, sl, tp)` | `ModifyPosition(position, slPrice, tpPrice)` |

## 6. Volume / lot units

- **MQL5** trades in *lots* (1.0 = 100 000 units on most FX pairs).
- **cAlgo** trades in *units* (1.0 lot ≈ 100 000 units; use `Symbol.LotSize`).
- Convert lots → units: `units = lots * Symbol.LotSize`.

## 7. Stop loss / take profit semantics

| MQL5 | cAlgo |
|---|---|
| Pass *price* to `Buy(... sl, tp ...)` | Pass *pip distance* to `ExecuteMarketOrder` |
| Modify with *price* | Modify with *price* (`ModifyPosition`) |

The most common porting bug. When converting MQL5 SL price to cAlgo SL pips:
```
slPips = (entryPrice - slPrice) / Symbol.PipSize    // for buy
slPips = (slPrice - entryPrice) / Symbol.PipSize    // for sell
```

## 8. Indicator calls

| MQL5 | cAlgo |
|---|---|
| `int h = iCustom(_Symbol,_Period,"name",p1,p2);` | `var ind = Indicators.GetIndicator<MyIndicator>(p1,p2);` |
| `CopyBuffer(h, 0, shift, count, buf)` | `ind.Result.Last(shift)` / `ind.Buffer[idx]` |

## 9. DOM / market depth

| MQL5 | cAlgo |
|---|---|
| `MarketBookAdd(_Symbol)` + `OnBookEvent` + `MarketBookGet` | `Symbol.MarketDepth.Updated += handler` + `BidEntries / AskEntries` |

## 10. Logging / alerts

| MQL5 | cAlgo |
|---|---|
| `Print("...")` / `Comment("...")` | `Print("...")` / `Chart.DrawStaticText` |
| `Alert("...")` | `Notifications.SendEmail(...)` / `Notifications.PlaySound(...)` |

## 11. Numerical helpers

| MQL5 | cAlgo |
|---|---|
| `MathAbs / MathMax / MathMin / MathRound / MathFloor / MathCeil / MathSqrt / MathPow / MathLog` | `Math.Abs / Math.Max / Math.Min / Math.Round / Math.Floor / Math.Ceiling / Math.Sqrt / Math.Pow / Math.Log` |

## 12. Common pitfalls when porting

1. **Indexing inversion** — fix at the boundary, not inside detector code.
2. **Pips vs points** — MT5 uses *points* (5-digit broker: 1 pip = 10 points). cAlgo uses pips natively.
3. **Volume unit mismatch** — lots (MQL5) vs units (cAlgo). Convert at the order-call boundary.
4. **Server time vs UTC** — MT5 server time is broker-set; cAlgo `Server.Time` is UTC. Normalize to UTC inside the EA for any session logic.
5. **Symbol-info granularity** — `Symbol.PipSize`, `Symbol.TickSize`, `Symbol.PipValue`, `Symbol.LotSize` are distinct in cAlgo; MQL5 conflates them under `SYMBOL_POINT/_TICK_SIZE/_TRADE_TICK_VALUE`. Always use the cAlgo-named property that semantically matches.
6. **Bar volume.** MT5 `iVolume` returns `long` tick-count by default. cAlgo `TickVolume` is also tick-count. Real volume (`Real Volume` / `Volume`) only exists with venue-feed brokers — guard accordingly.
7. **OnTick frequency.** MT5 `OnTick` fires per quote update. cAlgo `OnTick` fires per quote update. Both can fire mid-bar; the bar-close gate matters in both.

## 13. Translation discipline (parity rule)

When porting any EA:
1. Author the **logic-only** module (signal detection) language-agnostic in pseudocode.
2. Implement the logic identically in MQL5 + C# — do not let one drift.
3. Test both with the same `.set` / `[Parameter]` defaults on the same symbol/timeframe.
4. Diff the trade lists. Any divergence ≥ 5% of trades → translation bug.

