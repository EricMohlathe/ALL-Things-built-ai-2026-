# Entry, exit, trailing stop, multiple positions

Verified by compile on 2026-08-05, MetaEditor build 5836.

`templates/EA_Template.mq5` already contains the market entry and the simple
exit. This file covers what to add beyond that.

---

## Market entry with CTrade

The short form. `EA_Template.mq5` has the full version with lot sizing and
stops-level handling.

```cpp
trade.SetExpertMagicNumber(InpMagic);
trade.SetTypeFilling(PickFillingMode());   // see broker-adaptation.md
trade.SetDeviationInPoints(10);

bool ok = trade.Buy(lot, _Symbol, 0.0, sl, tp, InpComment);
if(!ok || trade.ResultRetcode() != TRADE_RETCODE_DONE)
   PrintFormat("Order rejected: %s", RetcodeText(trade.ResultRetcode()));
```

Price `0.0` means market price. Passing an explicit price to a market order
invites requotes for no benefit.

---

## Market entry with MqlTradeRequest

Use this when `CTrade` does not expose what you need. Zero the struct first:
uninitialised fields are a common source of rejections that look random.

```cpp
MqlTradeRequest request;
MqlTradeResult  result;
ZeroMemory(request);
ZeroMemory(result);

request.action       = TRADE_ACTION_DEAL;
request.symbol       = _Symbol;
request.volume       = lot;
request.type         = ORDER_TYPE_BUY;      // ORDER_TYPE, never POSITION_TYPE
request.price        = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
request.sl           = sl;
request.tp           = tp;
request.deviation    = 10;
request.magic        = InpMagic;            // the field is 'magic', not 'magicnumber'
request.type_filling = PickFillingMode();
request.comment      = InpComment;

if(!OrderSend(request, result) || result.retcode != TRADE_RETCODE_DONE)
   PrintFormat("OrderSend failed: %s", RetcodeText(result.retcode));
```

---

## Closing

```cpp
// One position
trade.PositionClose(ticket);

// All of this EA's positions on this symbol
void CloseAllMine()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)   // downwards
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;

      if(!trade.PositionClose(ticket))
         PrintFormat("Close failed for #%I64u: %s", ticket, RetcodeText(trade.ResultRetcode()));
   }
}
```

Iterate downwards. Closing inside an ascending loop shifts the remaining
indices and silently skips positions.

---

## Trailing stop

Two rules that make the difference between a trailing stop that works and one
that fills the log with errors.

- Only ever move the stop in the profitable direction. Never loosen it.
- Respect `SYMBOL_TRADE_FREEZE_LEVEL`. Inside that distance the broker refuses
  modification, and retrying produces a stream of rejections.

```cpp
void UpdateTrailingStop(int trailPoints, int stepPoints)
{
   double point       = _Point;
   long   stopsLevel  = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   long   freezeLevel = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);

   if(trailPoints < stopsLevel)
      trailPoints = (int)stopsLevel + 1;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;

      long   type    = PositionGetInteger(POSITION_TYPE);
      double openPr  = PositionGetDouble(POSITION_PRICE_OPEN);
      double curSL   = PositionGetDouble(POSITION_SL);
      double curTP   = PositionGetDouble(POSITION_TP);
      double bid     = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double ask     = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

      if(type == POSITION_TYPE_BUY)
      {
         if(bid - openPr < trailPoints * point) continue;      // not in profit enough
         if((bid - curSL) < (freezeLevel + 1) * point) continue; // too close to modify

         double newSL = NormalizeDouble(bid - trailPoints * point, _Digits);
         if(newSL > curSL + stepPoints * point)                 // only ever upward
            if(!trade.PositionModify(ticket, newSL, curTP))
               PrintFormat("Modify failed #%I64u: %s", ticket, RetcodeText(trade.ResultRetcode()));
      }
      else if(type == POSITION_TYPE_SELL)
      {
         if(openPr - ask < trailPoints * point) continue;
         if((curSL - ask) < (freezeLevel + 1) * point) continue;

         double newSL = NormalizeDouble(ask + trailPoints * point, _Digits);
         if(curSL == 0.0 || newSL < curSL - stepPoints * point) // only ever downward
            if(!trade.PositionModify(ticket, newSL, curTP))
               PrintFormat("Modify failed #%I64u: %s", ticket, RetcodeText(trade.ResultRetcode()));
      }
   }
}
```

`stepPoints` exists so the stop is not rewritten on every single tick. Without
it the EA sends thousands of modifications a day.

---

## Break even

A special case of trailing: move the stop to entry once the trade is far enough
ahead, then leave it.

```cpp
if(type == POSITION_TYPE_BUY && bid - openPr >= triggerPoints * _Point)
{
   double be = NormalizeDouble(openPr + lockPoints * _Point, _Digits);
   if(curSL < be)
      trade.PositionModify(ticket, be, curTP);
}
```

`lockPoints` should cover the spread and commission, otherwise "break even"
still closes at a small loss.

---

## Multiple positions on a netting account

On a netting account the platform keeps one net position per symbol. Sending a
second buy adds to it rather than creating a second position, and
`PositionsTotal()` still returns one.

Any strategy that needs several independent positions must check first:

```cpp
if(!isHedging && InpMaxPositions > 1)
{
   Print("This EA needs a hedging account. This account is netting.");
   return(INIT_FAILED);
}
```

Refusing to start is correct. Running anyway produces position sizes nobody
asked for.

---

## Level versus cross, and why it is not a detail

"Buy when RSI is below 30" and "buy when RSI crosses up through 30" are two
different strategies. Descriptions almost never say which one is meant, and the
generated EA silently picks one. Ask.

```cpp
// LEVEL. True on every bar the condition holds.
bool ShouldOpenLong() { return(rsi[1] < InpBuyLevel); }

// CROSS. True only on the bar the boundary is broken.
bool ShouldOpenLong() { return(rsi[2] <= InpBuyLevel && rsi[1] > InpBuyLevel); }
```

A level rule keeps firing for as long as the level holds, so it re-enters the
moment the previous position closes. What actually limits it is
`InpMaxPositions` and `InpMaxTradesPerDay`, not the signal. Under a level rule
those two inputs stop being safety rails and become part of the strategy: raise
the daily cap and you have a materially different system.

Both were built from the same template with identical risk settings and measured
on the same window, EURUSDm H1, 2024.01.01 to 2024.12.31, model 1, 100% history
quality, 1% risk, SL 300, TP 600, max 1 position, max 5 entries per day.
Measured 2026-08-08.

| | `RsiLevel` (level) | `RsiReversal` (cross) |
|---|---|---|
| Total trades | 145 | 116 |
| Win rate | 36.55% | 36.21% |
| Payoff ratio | 1.90 | 1.89 |
| Profit factor | 1.09 | 1.07 |
| Net profit | 997.21 | 621.88 |
| Max equity drawdown | 2 440.54 (19.13%) | 1 409.07 (11.71%) |
| Recovery factor | 0.41 | 0.44 |

Same edge per trade, and the win rate and payoff are almost identical, which is
what you would expect from the same signal source. The level rule simply takes
25% more of the same trades. It earned 60% more and drew down 73% more for it,
and its recovery factor is slightly worse.

Neither of those profit factors is far enough above 1.0 to survive commission
and slippage. The point of the table is the mechanical difference between the
two rules, not either result.
