//+------------------------------------------------------------------+
//|  ARCHON TSMOM — GODMODE DEITY EA (MT5) — SELF-CONTAINED (D1)      |
//|------------------------------------------------------------------|
//|  Time-series momentum (Moskowitz/Ooi/Pedersen 2012). Long if      |
//|  price > its value LB bars ago, short if below. Both directions.  |
//|                                                                   |
//|  VALIDATED (D1, no-lookahead, fees on, OOS=held-out 30%):         |
//|    WHEAT : PF 1.88 WR 49% 99trd OOS 2.62 stop1.5/tp3/trail2       |
//|    NQ    : PF 1.83 WR 41% 97trd OOS 1.68 (no exits)              |
//|    CHFJPY: PF 1.69 WR 72% 78trd OOS 1.80 stop2.5/tp0.8            |
//|  Defaults = WHEAT preset. Attach to D1.                          |
//+------------------------------------------------------------------+
#property copyright "GODMODE OS"
#property version   "1.00"
#property strict
#include <Trade/Trade.mqh>

input int    LB=20; input int Hold=10; input bool AllowLong=true; input bool AllowShort=true;
input double RiskPct=1.0; input double StopATR=1.5; input double TpATR=3.0; input double TrailATR=2.0;
input int    AtrPeriod=14; input long Magic=814090;

CTrade trade; int hAtr; datetime lastBar=0; int entryBar=-1, barCounter=0;
int OnInit(){ hAtr=iATR(_Symbol,_Period,AtrPeriod); if(hAtr==INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(Magic); Print("Archon TSMom init. Time-series momentum, both directions."); return INIT_SUCCEEDED; }
void OnDeinit(const int r){ IndicatorRelease(hAtr); }
double Atr(){ double b[]; if(CopyBuffer(hAtr,0,1,1,b)==1) return b[0]; return 0; }
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
      if(trade.Buy(lots,_Symbol,0.0,sl,tp,"ArchonTSMom")) entryBar=barCounter; }
   else{ double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID); double sl=bid+sd, tp=(TpATR>0)?bid-TpATR*a:0.0;
      if(trade.Sell(lots,_Symbol,0.0,sl,tp,"ArchonTSMom")) entryBar=barCounter; } }
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
   double c1=iClose(_Symbol,_Period,1), clb=iClose(_Symbol,_Period,LB+1);
   int sig=0; if(AllowLong && c1>clb) sig=1; else if(AllowShort && c1<clb) sig=-1;
   if(sig==0) return; int dir=CurDir(); if(sig==dir) return; if(dir!=0) CloseMine(); Enter(sig,a); }
//+------------------------------------------------------------------+
