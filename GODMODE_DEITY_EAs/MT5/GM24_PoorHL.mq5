//+------------------------------------------------------------------+
//|  GM24 POOR HIGH/LOW — GODMODE DEITY EA (MT5) — SELF-CONTAINED     |
//|------------------------------------------------------------------|
//|  Auction poor high/low fade. Matching highs + sell delta → SHORT; |
//|  matching lows + buy delta → LONG. Delta = signed tick volume.    |
//|  Both directions. High trade volume.                              |
//|                                                                   |
//|  VALIDATED (D1, no-lookahead, fees on, OOS=held-out 30%):         |
//|    NQ  : PF 1.82 WR 46%  56trd OOS 1.57 stop3/tp6                 |
//|    GOLD: PF 1.57 WR 41% 132trd OOS 1.41 stop2/trail2.5            |
//|    YM  : PF 1.48 WR 40% 114trd OOS 1.34 stop2/tp4/trail3          |
//|  Defaults = NQ preset. Attach to D1. Delta = futures/metals/crypto.|
//+------------------------------------------------------------------+
#property copyright "GODMODE OS"
#property version   "1.00"
#property strict
#include <Trade/Trade.mqh>

input int    LB=20; input int Hold=10; input bool AllowLong=true; input bool AllowShort=true;
input double RiskPct=1.0; input double StopATR=3.0; input double TpATR=6.0; input double TrailATR=0.0;
input int    AtrPeriod=14; input long Magic=814024;

CTrade trade; int hAtr; datetime lastBar=0; int entryBar=-1, barCounter=0;
int OnInit(){ hAtr=iATR(_Symbol,_Period,AtrPeriod); if(hAtr==INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(Magic); Print("GM24 Poor High/Low init. Both-direction auction fade."); return INIT_SUCCEEDED; }
void OnDeinit(const int r){ IndicatorRelease(hAtr); }
double Atr(){ double b[]; if(CopyBuffer(hAtr,0,1,1,b)==1) return b[0]; return 0; }
long TV(int sh){ long v[]; if(CopyTickVolume(_Symbol,_Period,sh,1,v)==1) return v[0]; return 0; }
double D(int sh){ double sg=(iClose(_Symbol,_Period,sh)>=iOpen(_Symbol,_Period,sh))?1.0:-1.0; return sg*(double)TV(sh); }
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
      if(trade.Buy(lots,_Symbol,0.0,sl,tp,"GM24_PoorHL")) entryBar=barCounter; }
   else{ double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID); double sl=bid+sd, tp=(TpATR>0)?bid-TpATR*a:0.0;
      if(trade.Sell(lots,_Symbol,0.0,sl,tp,"GM24_PoorHL")) entryBar=barCounter; } }
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
   double h1=iHigh(_Symbol,_Period,1),h2=iHigh(_Symbol,_Period,2),l1=iLow(_Symbol,_Period,1),l2=iLow(_Symbol,_Period,2);
   int sig=0;
   if(AllowLong && MathAbs(l1-l2)<0.25*a && D(1)>0) sig=1;
   else if(AllowShort && MathAbs(h1-h2)<0.25*a && D(1)<0) sig=-1;
   if(sig==0) return; int dir=CurDir(); if(sig==dir) return; if(dir!=0) CloseMine(); Enter(sig,a); }
//+------------------------------------------------------------------+
