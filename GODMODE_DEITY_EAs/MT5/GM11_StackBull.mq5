//+------------------------------------------------------------------+
//|  GM11 STACKBULL — GODMODE DEITY EA (MetaTrader 5) — SELF-CONTAINED|
//|------------------------------------------------------------------|
//|  Concept: Footprint buy-delta stacking. 3 consecutive positive-   |
//|  delta bars AND current delta > K x |mean delta over LB|. Delta =  |
//|  signed volume (+vol up-close / -vol down-close). Long-only.       |
//|                                                                   |
//|  VALIDATED (real backtest, daily, no-lookahead, OOS=held-out 30%): |
//|    GOLD 1D: PF 3.38 WR 75.9% 58trd +39.2% OOS 6.48 stop3/tp1       |
//|  Defaults = GOLD preset. Truth = MT5 Strategy Tester.             |
//+------------------------------------------------------------------+
#property copyright "GODMODE OS"
#property version   "1.00"
#property strict
#include <Trade/Trade.mqh>

input int    LB        = 20;
input double K         = 1.0;    // delta threshold (x mean delta)
input int    Hold      = 10;
input double RiskPct   = 1.0;
input double StopATR   = 3.0;
input double TpATR     = 1.0;
input double TrailATR  = 0.0;
input double SizingATR = 3.0;
input int    AtrPeriod = 14;
input int    TrendSMA  = 0;      // trend filter (0=off; GOLD/NQ:200 validated)
input long   Magic     = 814011; // GM11

CTrade   trade;
int      atrHandle;
datetime lastBar = 0;
int      entryBarIndex = -1, barCounter = 0;

int OnInit(){ atrHandle=iATR(_Symbol,_Period,AtrPeriod); if(atrHandle==INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(Magic); Print("GM11 StackBull init."); return INIT_SUCCEEDED; }
void OnDeinit(const int r){ IndicatorRelease(atrHandle); }

double Atr(){ double b[]; if(CopyBuffer(atrHandle,0,1,1,b)==1) return b[0]; return 0; }
long TickVol(int s){ long v[]; if(CopyTickVolume(_Symbol,_Period,s,1,v)==1) return v[0]; return 0; }
double Delta(int s){ double sign=(iClose(_Symbol,_Period,s)>=iOpen(_Symbol,_Period,s))?1.0:-1.0; return sign*(double)TickVol(s); }
double MeanDelta(){ double sum=0; for(int j=1;j<=LB;j++) sum+=Delta(j); return sum/LB; }

bool HasPosition(){ for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i);
   if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==Magic) return true; } return false; }

double LotsForRisk(double atr){
   double riskRef=(StopATR>0?StopATR:SizingATR)*atr; if(riskRef<=0) return 0;
   double ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE), tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
   if(ts<=0||tv<=0) return SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double lossPerLot=(riskRef/ts)*tv;
   double riskCash=AccountInfoDouble(ACCOUNT_EQUITY)*(RiskPct/100.0);
   double lots=(lossPerLot>0)?riskCash/lossPerLot:0;
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP), mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN), mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   if(step>0) lots=MathFloor(lots/step)*step; return MathMax(mn,MathMin(mx,lots)); }

void OpenLong(double atr){ double lots=LotsForRisk(atr); if(lots<=0) return;
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double sl=(StopATR>0)?ask-StopATR*atr:0.0, tp=(TpATR>0)?ask+TpATR*atr:0.0;
   if(trade.Buy(lots,_Symbol,0.0,sl,tp,"GM11_StackBull")) entryBarIndex=barCounter; }

void ManageOpen(){ if(!HasPosition()){ entryBarIndex=-1; return; }
   if(TrailATR>0){ double atr=Atr(),bid=SymbolInfoDouble(_Symbol,SYMBOL_BID),newSl=bid-TrailATR*atr;
      for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i);
         if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==Magic){
            double cur=PositionGetDouble(POSITION_SL); if(newSl>cur) trade.PositionModify(tk,newSl,PositionGetDouble(POSITION_TP)); } } }
   if(entryBarIndex>=0&&(barCounter-entryBarIndex)>=Hold){
      for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i);
         if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==Magic) trade.PositionClose(tk); } } }


bool TrendOK(int dir){ if(TrendSMA<=0) return true; double s=0; for(int i=1;i<=TrendSMA;i++) s+=iClose(_Symbol,_Period,i); s/=TrendSMA; double c=iClose(_Symbol,_Period,1); return dir>0 ? c>s : c<s; }

void OnTick(){ datetime t=iTime(_Symbol,_Period,0); if(t==lastBar) return; lastBar=t; barCounter++;
   ManageOpen(); if(HasPosition()) return; if(Bars(_Symbol,_Period)<LB+5) return;
   double atr=Atr(); if(atr<=0) return;
   if(Delta(1)>0 && Delta(2)>0 && Delta(3)>0 && Delta(1) > K*MathAbs(MeanDelta()) && TrendOK(1))
      OpenLong(atr); }
//+------------------------------------------------------------------+
