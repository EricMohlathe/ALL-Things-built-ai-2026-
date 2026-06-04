//+------------------------------------------------------------------+
//|        Absorption EA — Example for MT5 (MQL5)                    |
//|        Detects bearish absorption: + delta + bearish close        |
//|        with small range, then enters short on confirmation        |
//+------------------------------------------------------------------+
#property copyright "OrderFlow Mastery Skill — Example"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>
CTrade trade;

input double InpRiskPct       = 0.5;
input int    InpMagic         = 20260430;
input string InpComment       = "ABS_EA";
input int    InpMaxSpreadPts  = 30;
input int    InpSlippagePts   = 10;

input double InpMinSignedDelta= 1500;   // approximation; tune per symbol
input double InpMaxRangeATR   = 0.5;    // bar range ≤ 0.5 × ATR(14)
input int    InpATRPeriod     = 14;

datetime g_lastBarTime = 0;

int OnInit()
{
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippagePts);
   return INIT_SUCCEEDED;
}

bool IsNewBar()
{
   datetime t = iTime(_Symbol,_Period,0);
   if(t==g_lastBarTime) return false;
   g_lastBarTime = t; return true;
}

double GetATR(int shift)
{
   int h = iATR(_Symbol,_Period,InpATRPeriod);
   double buf[]; if(CopyBuffer(h,0,shift,1,buf)<=0) return 0;
   return buf[0];
}

bool IsAbsorptionBearish(int shift)
{
   double o = iOpen(_Symbol,_Period,shift), c = iClose(_Symbol,_Period,shift);
   double h = iHigh(_Symbol,_Period,shift), l = iLow(_Symbol,_Period,shift);
   long   v = iVolume(_Symbol,_Period,shift);
   double signedDelta = (c >= o) ? (double)v : -(double)v;   // approximation
   double range = h - l;
   double atr = GetATR(shift);
   if(atr<=0) return false;
   return (signedDelta >= InpMinSignedDelta && c < o && range <= atr*InpMaxRangeATR);
}

double LotByRisk(double slPoints)
{
   double bal=AccountInfoDouble(ACCOUNT_BALANCE);
   double tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
   double ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   double pt=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double pointValue=tv*(pt/ts);
   if(pointValue<=0||slPoints<=0) return 0;
   double lots = bal*InpRiskPct/100.0/(slPoints*pointValue);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   double minL=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   lots = MathFloor(lots/step)*step;
   return MathMax(lots, minL);
}

void OnTick()
{
   if(!IsNewBar()) return;
   if((long)SymbolInfoInteger(_Symbol,SYMBOL_SPREAD) > InpMaxSpreadPts) return;

   if(IsAbsorptionBearish(1) && PositionsTotal()==0)
   {
      double pt=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
      double atr=GetATR(1); double slPts=MathMax(200, atr/pt*1.2);
      double price=SymbolInfoDouble(_Symbol,SYMBOL_BID);
      double sl=price+slPts*pt, tp=price-2*slPts*pt;
      double lots = LotByRisk(slPts);
      if(lots>0) trade.Sell(lots,_Symbol,price,sl,tp,InpComment);
   }
}
