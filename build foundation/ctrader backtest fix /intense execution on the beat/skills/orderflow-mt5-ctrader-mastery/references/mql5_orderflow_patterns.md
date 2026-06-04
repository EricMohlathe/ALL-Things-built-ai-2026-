# MQL5 — Order-Flow Implementation Patterns

Authoritative MQL5 idioms for every order-flow concept. Use these verbatim inside the MT5 EA template.

## 1. Tick-by-tick classification

```mql5
MqlTick lastTick;
double  prevAsk = 0, prevBid = 0;
double  curDelta = 0;

void OnTick()
{
   if(!SymbolInfoTick(_Symbol, lastTick)) return;

   if(prevAsk == 0) { prevAsk = lastTick.ask; prevBid = lastTick.bid; return; }

   double sign = 0;
   if(lastTick.last >= prevAsk)      sign =  1.0; // aggressive buy
   else if(lastTick.last <= prevBid) sign = -1.0; // aggressive sell
   curDelta += sign * (double)lastTick.volume;

   prevAsk = lastTick.ask;
   prevBid = lastTick.bid;
}
```

> If the broker doesn't stream `last` or `volume`, fall back to `(ask+bid)/2` as `last` and tick-count as volume; flag this approximation in the EA dashboard.

## 2. Cumulative delta per bar

```mql5
double cvdPerBar[];      // index parallel to bars
datetime lastBarTime = 0;

void OnTick()
{
   datetime t = iTime(_Symbol, _Period, 0);
   if(t != lastBarTime)
   {
      // new bar opened
      ArrayResize(cvdPerBar, ArraySize(cvdPerBar)+1);
      cvdPerBar[ArraySize(cvdPerBar)-1] = 0;
      lastBarTime = t;
   }
   // ...classify tick...
   cvdPerBar[ArraySize(cvdPerBar)-1] += signedTickVolume;
}
```

## 3. Footprint reconstruction (level → bid/ask volume)

```mql5
struct FpLevel { double price; long bidVol; long askVol; };
FpLevel curBarFp[];

void AddTickToFootprint(double price, long vol, int signFlag)
{
   double tick = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double rounded = MathRound(price/tick) * tick;
   for(int i=0;i<ArraySize(curBarFp);i++)
      if(MathAbs(curBarFp[i].price - rounded) < tick/2)
      {
         if(signFlag>0) curBarFp[i].askVol += vol;
         else if(signFlag<0) curBarFp[i].bidVol += vol;
         return;
      }
   FpLevel n; n.price=rounded; n.bidVol=(signFlag<0?vol:0); n.askVol=(signFlag>0?vol:0);
   ArrayResize(curBarFp, ArraySize(curBarFp)+1);
   curBarFp[ArraySize(curBarFp)-1] = n;
}
```

## 4. POC + POI per bar

```mql5
void ComputePocPoi(FpLevel &fp[], double &pocPrice, double &poiPrice)
{
   long maxV = -1, minV = LONG_MAX;
   for(int i=0;i<ArraySize(fp);i++)
   {
      long total = fp[i].bidVol + fp[i].askVol;
      if(total > maxV) { maxV = total; pocPrice = fp[i].price; }
      if(total < minV) { minV = total; poiPrice = fp[i].price; }
   }
}
```

## 5. Stacked imbalance detection

```mql5
bool HasBullStackedImbalance(FpLevel &fp[], int needed=3, double ratio=3.0)
{
   ArrayPrint(fp); // debug
   int run = 0;
   for(int i=1;i<ArraySize(fp);i++)
   {
      // diagonal: ask of level vs bid of level below
      if(fp[i].askVol >= ratio * fp[i-1].bidVol && fp[i-1].bidVol > 0) run++;
      else run = 0;
      if(run >= needed) return true;
   }
   return false;
}
```

## 6. Level-2 (DOM) hooks

```mql5
int OnInit()
{
   if(!MarketBookAdd(_Symbol)) Print("MarketBookAdd failed: ", GetLastError());
   return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){ MarketBookRelease(_Symbol); }

void OnBookEvent(const string &symbol)
{
   if(symbol != _Symbol) return;
   MqlBookInfo book[];
   if(!MarketBookGet(_Symbol, book)) return;
   // book[i].type ∈ {BOOK_TYPE_SELL, BOOK_TYPE_BUY, BOOK_TYPE_SELL_MARKET, BOOK_TYPE_BUY_MARKET}
}
```

## 7. CTrade order helper (recommended)

```mql5
#include <Trade/Trade.mqh>
CTrade trade;

int OnInit()
{
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippagePts);
   trade.SetMarginMode();
   trade.LogLevel(LOG_LEVEL_ALL);
   return INIT_SUCCEEDED;
}
```

## 8. Risk-based lot sizing

```mql5
double LotByRisk(double slPoints, double riskPct)
{
   double balance   = AccountInfoDouble(ACCOUNT_BALANCE);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double point     = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double riskMoney = balance * riskPct/100.0;
   double pointValue= tickValue * (point/tickSize);
   double lots      = riskMoney / (slPoints * pointValue);
   double minLot    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double step      = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   lots = MathFloor(lots/step)*step;
   if(lots < minLot) lots = minLot;
   return lots;
}
```

## 9. Spread + session guard

```mql5
bool TradeAllowedNow()
{
   double sp = (SymbolInfoInteger(_Symbol, SYMBOL_SPREAD));
   if(sp > InpMaxSpreadPts) return false;
   datetime t = TimeCurrent(); MqlDateTime mt; TimeToStruct(t, mt);
   int minutes = mt.hour*60 + mt.min;
   return (minutes >= InpSessionStartMin && minutes <= InpSessionEndMin);
}
```

## 10. Daily-loss kill switch

```mql5
double dayStartEquity = 0;
datetime dayKey = 0;

bool DailyLossOk()
{
   datetime t = iTime(_Symbol, PERIOD_D1, 0);
   if(t != dayKey) { dayKey = t; dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY); }
   double dd = (dayStartEquity - AccountInfoDouble(ACCOUNT_EQUITY)) / dayStartEquity * 100.0;
   return dd < InpMaxDailyLossPct;
}
```

## 11. iCustom for footprint indicator

```mql5
int handleFp = iCustom(_Symbol, _Period, "OrderFlow_Footprint",
                       InpVolMode, InpStyle);
double pocBuf[];
if(CopyBuffer(handleFp, 0, 1, 1, pocBuf) <= 0) /* error */;
```

## 12. New-bar gate

```mql5
bool IsNewBar()
{
   static datetime last = 0;
   datetime t = iTime(_Symbol, _Period, 0);
   if(t == last) return false;
   last = t;
   return true;
}
```
