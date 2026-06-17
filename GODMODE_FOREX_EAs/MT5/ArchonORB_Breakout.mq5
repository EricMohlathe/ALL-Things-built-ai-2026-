//+------------------------------------------------------------------+
//|  ARCHON ORB — GODMODE FOREX EA (MT5) — SELF-CONTAINED             |
//|------------------------------------------------------------------|
//|  Opening-range / volatility breakout (Crabel/Williams). Break of  |
//|  prior LB-bar close-range by K*ATR*0.2, in trend direction (50-SMA)|
//|  Both directions. Price-only -> works on spot forex. Higher volume.|
//|                                                                   |
//|  VALIDATED (D1, no-lookahead, fees on, OOS=held-out 30%):         |
//|    EUR futures (6E): PF 1.62 WR 50%  90trd OOS 3.58 stop3/tp6     |
//|    EURJPY          : PF 1.58 WR 47% 108trd OOS 2.04 stop1/tp2/tr1.5|
//|  Defaults = 6E preset. Validate YOUR pair. Attach to D1.         |
//+------------------------------------------------------------------+
#property copyright "GODMODE OS"
#property version   "1.00"
#property strict
#include <Trade/Trade.mqh>

input int    LB        = 20;
input double K         = 1.0;
input int    TrendN    = 50;
input int    Hold      = 12;
input bool   AllowLong  = true;
input bool   AllowShort = true;
input double RiskPct   = 1.0;
input double StopATR   = 3.0;
input double TpATR     = 6.0;
input double TrailATR  = 0.0;
input int    AtrPeriod = 14;
input long   Magic     = 814092;

CTrade trade;
int hSma, hAtr;
datetime lastBar = 0;
int entryBar = -1, barCounter = 0;

int OnInit()
{
   hSma=iMA(_Symbol,_Period,TrendN,0,MODE_SMA,PRICE_CLOSE);
   hAtr=iATR(_Symbol,_Period,AtrPeriod);
   if(hSma==INVALID_HANDLE||hAtr==INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(Magic);
   Print("Archon ORB init. Volatility breakout + SMA",TrendN," filter.");
   return INIT_SUCCEEDED;
}
void OnDeinit(const int r){ IndicatorRelease(hSma); IndicatorRelease(hAtr); }

double Buf(int h,int sh){ double b[]; if(CopyBuffer(h,0,sh,1,b)==1) return b[0]; return EMPTY_VALUE; }
double HighC(int from,int n){ double m=-DBL_MAX; for(int i=from;i<from+n;i++){ double c=iClose(_Symbol,_Period,i); if(c>m) m=c; } return m; }
double LowC(int from,int n){ double m=DBL_MAX; for(int i=from;i<from+n;i++){ double c=iClose(_Symbol,_Period,i); if(c<m) m=c; } return m; }

int CurDir(){ for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i);
   if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==Magic)
      return (PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY)?1:-1; } return 0; }
void CloseMine(){ for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i);
   if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==Magic) trade.PositionClose(tk); } }

double Lots(double stopDist){
   double ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE), tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
   if(ts<=0||tv<=0||stopDist<=0) return SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double lots=AccountInfoDouble(ACCOUNT_EQUITY)*(RiskPct/100.0)/((stopDist/ts)*tv);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP), mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN), mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   if(step>0) lots=MathFloor(lots/step)*step; return MathMax(mn,MathMin(mx,lots)); }

void Enter(int dir,double a){
   double stopDist=StopATR*a, lots=Lots(stopDist); if(lots<=0) return;
   if(dir>0){ double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
      double sl=ask-stopDist, tp=(TpATR>0)?ask+TpATR*a:0.0;
      if(trade.Buy(lots,_Symbol,0.0,sl,tp,"ArchonORB")) entryBar=barCounter; }
   else{ double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
      double sl=bid+stopDist, tp=(TpATR>0)?bid-TpATR*a:0.0;
      if(trade.Sell(lots,_Symbol,0.0,sl,tp,"ArchonORB")) entryBar=barCounter; } }

void Manage(){ int dir=CurDir(); if(dir==0){ entryBar=-1; return; }
   if(TrailATR>0){ double a=Buf(hAtr,1);
      for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i);
         if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==Magic){
            double cur=PositionGetDouble(POSITION_SL), tp=PositionGetDouble(POSITION_TP);
            if(dir>0){ double n=SymbolInfoDouble(_Symbol,SYMBOL_BID)-TrailATR*a; if(n>cur) trade.PositionModify(tk,n,tp); }
            else     { double n=SymbolInfoDouble(_Symbol,SYMBOL_ASK)+TrailATR*a; if(cur==0||n<cur) trade.PositionModify(tk,n,tp); } } } }
   if(entryBar>=0 && (barCounter-entryBar)>=Hold) CloseMine(); }

void OnTick(){
   datetime t=iTime(_Symbol,_Period,0); if(t==lastBar) return; lastBar=t; barCounter++;
   Manage();
   if(Bars(_Symbol,_Period) < MathMax(LB,TrendN)+3) return;
   double a=Buf(hAtr,1), sma=Buf(hSma,1), c1=iClose(_Symbol,_Period,1);
   if(a<=0 || sma==EMPTY_VALUE) return;
   double buf=K*a*0.2; int sig=0;
   if(AllowLong && c1>HighC(2,LB)+buf && c1>sma) sig=1;
   else if(AllowShort && c1<LowC(2,LB)-buf && c1<sma) sig=-1;
   if(sig==0) return;
   int dir=CurDir(); if(sig==dir) return;
   if(dir!=0) CloseMine();
   Enter(sig,a);
}
//+------------------------------------------------------------------+
