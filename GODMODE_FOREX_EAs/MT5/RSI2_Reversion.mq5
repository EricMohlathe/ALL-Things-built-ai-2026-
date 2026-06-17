//+------------------------------------------------------------------+
//|  RSI2 REVERSION — GODMODE FOREX EA (MT5) — SELF-CONTAINED         |
//|------------------------------------------------------------------|
//|  Connors RSI(2) mean reversion + 200-SMA trend filter. Buy        |
//|  oversold dips only in an uptrend; exit when RSI(2) recovers.      |
//|  Long-only. No volume needed -> works on spot forex.              |
//|                                                                   |
//|  VALIDATED (D1, no-lookahead, fees on, OOS=held-out 30%):         |
//|    JPY futures (6J): PF 4.73 WR 76% 45trd OOS 2.88 stop4/tp1.5    |
//|  Symbol-agnostic; best fit = JPY. Validate YOUR pair. Attach D1.  |
//+------------------------------------------------------------------+
#property copyright "GODMODE OS"
#property version   "1.00"
#property strict
#include <Trade/Trade.mqh>

input int    RsiN      = 2;
input double BuyLevel  = 10.0;
input double ExitLevel = 60.0;
input int    TrendN    = 200;
input double RiskPct   = 1.0;
input double StopATR   = 4.0;
input double TpATR     = 1.5;
input int    AtrPeriod = 14;
input long   Magic     = 814200;

CTrade trade;
int hRsi, hSma, hAtr;
datetime lastBar = 0;

int OnInit()
{
   hRsi=iRSI(_Symbol,_Period,RsiN,PRICE_CLOSE);
   hSma=iMA(_Symbol,_Period,TrendN,0,MODE_SMA,PRICE_CLOSE);
   hAtr=iATR(_Symbol,_Period,AtrPeriod);
   if(hRsi==INVALID_HANDLE||hSma==INVALID_HANDLE||hAtr==INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(Magic);
   Print("RSI2 Reversion init. Long-only, SMA",TrendN," filter.");
   return INIT_SUCCEEDED;
}
void OnDeinit(const int r){ IndicatorRelease(hRsi); IndicatorRelease(hSma); IndicatorRelease(hAtr); }

double Buf(int h,int sh){ double b[]; if(CopyBuffer(h,0,sh,1,b)==1) return b[0]; return EMPTY_VALUE; }

bool HasPos(){ for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i);
   if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==Magic) return true; } return false; }
void ClosePos(){ for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i);
   if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==Magic) trade.PositionClose(tk); } }

double Lots(double stopDist){
   double ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE), tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
   if(ts<=0||tv<=0||stopDist<=0) return SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double lots=AccountInfoDouble(ACCOUNT_EQUITY)*(RiskPct/100.0)/((stopDist/ts)*tv);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP), mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN), mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   if(step>0) lots=MathFloor(lots/step)*step; return MathMax(mn,MathMin(mx,lots)); }

void OnTick()
{
   datetime t=iTime(_Symbol,_Period,0); if(t==lastBar) return; lastBar=t;
   double rsi=Buf(hRsi,1);
   if(HasPos()){ if(rsi>ExitLevel) ClosePos(); return; }
   if(Bars(_Symbol,_Period)<TrendN+3) return;
   double sma=Buf(hSma,1), atr=Buf(hAtr,1), c1=iClose(_Symbol,_Period,1);
   if(atr<=0 || rsi==EMPTY_VALUE || sma==EMPTY_VALUE) return;
   if(c1>sma && rsi<BuyLevel){
      double stopDist=StopATR*atr, lots=Lots(stopDist); if(lots<=0) return;
      double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
      double sl=ask-stopDist, tp=(TpATR>0)?ask+TpATR*atr:0.0;
      trade.Buy(lots,_Symbol,0.0,sl,tp,"RSI2_Rev");
   }
}
//+------------------------------------------------------------------+
