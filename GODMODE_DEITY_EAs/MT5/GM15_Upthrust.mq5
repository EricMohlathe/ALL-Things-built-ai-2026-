//+------------------------------------------------------------------+
//|  GM15 UPTHRUST — GODMODE DEITY EA (MT5) — SELF-CONTAINED          |
//|------------------------------------------------------------------|
//|  Wyckoff upthrust (mirror of spring). High pokes ABOVE prior      |
//|  swing-high of closes (LB), closes back BELOW = failed breakout   |
//|  → SHORT. Short-only (only short side validated).                 |
//|                                                                   |
//|  VALIDATED (D1, no-lookahead, fees on, OOS=held-out 30%):         |
//|    EURCHF  : PF 2.36 WR 68% 56trd OOS 3.26 stop3/tp1              |
//|    PLATINUM: PF 1.89 WR 69% 29trd OOS 2.28 stop2.5/tp0.8          |
//|    NZDUSD  : PF 1.52 WR 61% 61trd OOS 1.40 stop2.5/tp0.8          |
//|  Defaults = EURCHF preset. Attach to D1.                         |
//+------------------------------------------------------------------+
#property copyright "GODMODE OS"
#property version   "1.00"
#property strict
#include <Trade/Trade.mqh>

input int    LB        = 20;
input int    Hold      = 10;
input double RiskPct   = 1.0;
input double StopATR   = 3.0;
input double TpATR     = 1.0;
input double TrailATR  = 0.0;
input int    AtrPeriod = 14;
input long   Magic     = 814015;

CTrade trade; int hAtr; datetime lastBar=0; int entryBar=-1, barCounter=0;

int OnInit(){ hAtr=iATR(_Symbol,_Period,AtrPeriod); if(hAtr==INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(Magic); Print("GM15 Upthrust init. Short-only."); return INIT_SUCCEEDED; }
void OnDeinit(const int r){ IndicatorRelease(hAtr); }
double Atr(){ double b[]; if(CopyBuffer(hAtr,0,1,1,b)==1) return b[0]; return 0; }
double HighC(int from,int n){ double m=-DBL_MAX; for(int i=from;i<from+n;i++){ double c=iClose(_Symbol,_Period,i); if(c>m) m=c; } return m; }
bool HasPos(){ for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i);
   if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==Magic) return true; } return false; }
double Lots(double stopDist){ double ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
   if(ts<=0||tv<=0||stopDist<=0) return SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double lots=AccountInfoDouble(ACCOUNT_EQUITY)*(RiskPct/100.0)/((stopDist/ts)*tv);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   if(step>0) lots=MathFloor(lots/step)*step; return MathMax(mn,MathMin(mx,lots)); }
void Manage(){ if(!HasPos()){ entryBar=-1; return; }
   if(TrailATR>0){ double a=Atr();
      for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i);
         if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==Magic){
            double cur=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP),n=SymbolInfoDouble(_Symbol,SYMBOL_ASK)+TrailATR*a;
            if(cur==0||n<cur) trade.PositionModify(tk,n,tp); } } }
   if(entryBar>=0 && (barCounter-entryBar)>=Hold){ for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i);
      if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==Magic) trade.PositionClose(tk); } } }
void OnTick(){ datetime t=iTime(_Symbol,_Period,0); if(t==lastBar) return; lastBar=t; barCounter++;
   Manage(); if(HasPos()) return; if(Bars(_Symbol,_Period)<LB+5) return;
   double a=Atr(); if(a<=0) return;
   double h1=iHigh(_Symbol,_Period,1), c1=iClose(_Symbol,_Period,1), hh=HighC(2,LB);
   if(h1>hh && c1<hh){ double sd=StopATR*a, lots=Lots(sd); if(lots<=0) return;
      double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
      double sl=bid+sd, tp=(TpATR>0)?bid-TpATR*a:0.0;
      if(trade.Sell(lots,_Symbol,0.0,sl,tp,"GM15_Upthrust")) entryBar=barCounter; } }
//+------------------------------------------------------------------+
