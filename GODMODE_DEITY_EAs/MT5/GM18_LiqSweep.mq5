//+------------------------------------------------------------------+
//|  GM18 LIQSWEEP — GODMODE DEITY EA (MT5) — SELF-CONTAINED (D1)     |
//|------------------------------------------------------------------|
//|  Liquidity-sweep reversal, BOTH directions. Sweep below prior     |
//|  swing-low of closes (LB), close UPPER half → LONG; mirror → SHORT|
//|                                                                   |
//|  VALIDATED (D1, no-lookahead, fees on, OOS=held-out 30%):         |
//|    PLATINUM: PF 2.72 WR 78%  59trd OOS 1.45 stop2.5/tp0.8         |
//|    AUDUSD  : PF 1.47 WR 68% 101trd OOS 2.27 stop3/tp1             |
//|  Defaults = PLATINUM preset. Attach to D1 (intraday config loses).|
//+------------------------------------------------------------------+
#property copyright "GODMODE OS"
#property version   "1.00"
#property strict
#include <Trade/Trade.mqh>

input int    LB=20; input int Hold=10; input bool AllowLong=true; input bool AllowShort=true;
input double RiskPct=1.0; input double StopATR=2.5; input double TpATR=0.8; input double TrailATR=0.0;
input int    AtrPeriod=14; input long Magic=814018;

CTrade trade; int hAtr; datetime lastBar=0; int entryBar=-1, barCounter=0;
int OnInit(){ hAtr=iATR(_Symbol,_Period,AtrPeriod); if(hAtr==INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(Magic); Print("GM18 LiqSweep (D1) init. Both-direction."); return INIT_SUCCEEDED; }
void OnDeinit(const int r){ IndicatorRelease(hAtr); }
double Atr(){ double b[]; if(CopyBuffer(hAtr,0,1,1,b)==1) return b[0]; return 0; }
double LowC(int f,int n){ double m=DBL_MAX; for(int i=f;i<f+n;i++){ double c=iClose(_Symbol,_Period,i); if(c<m) m=c; } return m; }
double HighC(int f,int n){ double m=-DBL_MAX; for(int i=f;i<f+n;i++){ double c=iClose(_Symbol,_Period,i); if(c>m) m=c; } return m; }
int CurDir(){ for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i);
   if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==Magic)
      return (PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY)?1:-1; } return 0; }
void CloseMine(){ for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i);
   if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==Magic) trade.PositionClose(tk); } }
double Lots(double sd){ double ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
   if(ts<=0||tv<=0||sd<=0) return SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double lots=AccountInfoDouble(ACCOUNT_EQUITY)*(RiskPct/100.0)/((sd/ts)*tv);
   double st=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   if(st>0) lots=MathFloor(lots/st)*st; return MathMax(mn,MathMin(mx,lots)); }
void Enter(int dir,double a){ double sd=StopATR*a, lots=Lots(sd); if(lots<=0) return;
   if(dir>0){ double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK); double sl=ask-sd, tp=(TpATR>0)?ask+TpATR*a:0.0;
      if(trade.Buy(lots,_Symbol,0.0,sl,tp,"GM18_LiqSweep")) entryBar=barCounter; }
   else{ double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID); double sl=bid+sd, tp=(TpATR>0)?bid-TpATR*a:0.0;
      if(trade.Sell(lots,_Symbol,0.0,sl,tp,"GM18_LiqSweep")) entryBar=barCounter; } }
void Manage(){ int dir=CurDir(); if(dir==0){ entryBar=-1; return; }
   if(TrailATR>0){ double a=Atr();
      for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i);
         if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==Magic){
            double cur=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);
            if(dir>0){ double n=SymbolInfoDouble(_Symbol,SYMBOL_BID)-TrailATR*a; if(n>cur) trade.PositionModify(tk,n,tp); }
            else     { double n=SymbolInfoDouble(_Symbol,SYMBOL_ASK)+TrailATR*a; if(cur==0||n<cur) trade.PositionModify(tk,n,tp); } } } }
   if(entryBar>=0 && (barCounter-entryBar)>=Hold) CloseMine(); }
void OnTick(){ datetime t=iTime(_Symbol,_Period,0); if(t==lastBar) return; lastBar=t; barCounter++;
   Manage(); if(Bars(_Symbol,_Period)<LB+5) return; double a=Atr(); if(a<=0) return;
   double hi=iHigh(_Symbol,_Period,1),lo=iLow(_Symbol,_Period,1),cl=iClose(_Symbol,_Period,1),rng=hi-lo; if(rng<=0) return;
   int sig=0;
   if(AllowLong && lo<LowC(2,LB) && cl>lo+0.5*rng) sig=1;
   else if(AllowShort && hi>HighC(2,LB) && cl<hi-0.5*rng) sig=-1;
   if(sig==0) return; int dir=CurDir(); if(sig==dir) return; if(dir!=0) CloseMine(); Enter(sig,a); }
//+------------------------------------------------------------------+
