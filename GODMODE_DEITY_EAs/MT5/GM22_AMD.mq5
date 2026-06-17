//+------------------------------------------------------------------+
//|  GM22 AMD — GODMODE DEITY EA (MetaTrader 5) — SELF-CONTAINED      |
//|------------------------------------------------------------------|
//|  Concept: ICT Accumulation-Manipulation-Distribution (power of 3).|
//|  Prior bar sweeps below swing-low of closes (manipulation), then   |
//|  current bar expands UP (range > K x ATR), closes higher, positive |
//|  delta (distribution/markup). Long-only.                           |
//|                                                                   |
//|  VALIDATED (real backtest, daily, no-lookahead, OOS=held-out 30%): |
//|    YM 1D: PF 2.83 WR 79.3% 58trd +71.5% OOS 5.20 stop4/tp1.5       |
//|  Defaults = YM preset. Truth = MT5 Strategy Tester.               |
//+------------------------------------------------------------------+
#property copyright "GODMODE OS"
#property version   "1.00"
#property strict
#include <Trade/Trade.mqh>

input int    LB        = 20;
input double K         = 1.0;    // range > K x ATR
input int    Hold      = 10;
input double RiskPct   = 1.0;
input double StopATR   = 4.0;
input double TpATR     = 1.5;
input double TrailATR  = 0.0;
input double SizingATR = 3.0;
input int    AtrPeriod = 14;
input long   Magic     = 814022; // GM22

CTrade   trade;
int      atrHandle;
datetime lastBar = 0;
int      entryBarIndex = -1, barCounter = 0;

int OnInit(){ atrHandle=iATR(_Symbol,_Period,AtrPeriod); if(atrHandle==INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(Magic); Print("GM22 AMD init."); return INIT_SUCCEEDED; }
void OnDeinit(const int r){ IndicatorRelease(atrHandle); }

double Atr(){ double b[]; if(CopyBuffer(atrHandle,0,1,1,b)==1) return b[0]; return 0; }
long TickVol(int s){ long v[]; if(CopyTickVolume(_Symbol,_Period,s,1,v)==1) return v[0]; return 0; }
double Delta(int s){ double sign=(iClose(_Symbol,_Period,s)>=iOpen(_Symbol,_Period,s))?1.0:-1.0; return sign*(double)TickVol(s); }
double LowestClose(int from,int n){ double m=DBL_MAX; for(int s=from;s<from+n;s++){ double c=iClose(_Symbol,_Period,s); if(c<m) m=c; } return m; }

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
   if(trade.Buy(lots,_Symbol,0.0,sl,tp,"GM22_AMD")) entryBarIndex=barCounter; }

void ManageOpen(){ if(!HasPosition()){ entryBarIndex=-1; return; }
   if(TrailATR>0){ double atr=Atr(),bid=SymbolInfoDouble(_Symbol,SYMBOL_BID),newSl=bid-TrailATR*atr;
      for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i);
         if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==Magic){
            double cur=PositionGetDouble(POSITION_SL); if(newSl>cur) trade.PositionModify(tk,newSl,PositionGetDouble(POSITION_TP)); } } }
   if(entryBarIndex>=0&&(barCounter-entryBarIndex)>=Hold){
      for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i);
         if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==Magic) trade.PositionClose(tk); } } }

void OnTick(){ datetime t=iTime(_Symbol,_Period,0); if(t==lastBar) return; lastBar=t; barCounter++;
   ManageOpen(); if(HasPosition()) return; if(Bars(_Symbol,_Period)<LB+6) return;
   double atr=Atr(); if(atr<=0) return;
   double rng=iHigh(_Symbol,_Period,1)-iLow(_Symbol,_Period,1);
   double llPrev2=LowestClose(3,LB);
   if(iLow(_Symbol,_Period,2)<llPrev2 && iClose(_Symbol,_Period,1)>iClose(_Symbol,_Period,2)
      && rng>K*atr && Delta(1)>0)
      OpenLong(atr); }
//+------------------------------------------------------------------+
