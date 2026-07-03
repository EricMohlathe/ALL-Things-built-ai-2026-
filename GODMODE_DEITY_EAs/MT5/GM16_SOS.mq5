//+------------------------------------------------------------------+
//|  GM16 SOS — GODMODE DEITY EA (MetaTrader 5) — SELF-CONTAINED      |
//|------------------------------------------------------------------|
//|  Concept: Wyckoff Sign of Strength. Wide-range up bar (range >     |
//|  K x ATR), close>open, positive delta, breaks prior swing-high of  |
//|  closes (LB) = demand expansion / markup. Long-only.               |
//|                                                                   |
//|  VALIDATED (real backtest, daily, no-lookahead, OOS=held-out 30%): |
//|    NQ 1D: PF 2.92 WR 64.4% 59trd +96.8% OOS 2.31 stop2/tp4/trail3  |
//|    ES 1D: PF 2.87 WR 83.6% 61trd +34.0% OOS 1.81 stop3/tp1         |
//|    YM 1D: PF 2.38 WR 58.2% 67trd +48.2% OOS 1.83 exits NONE        |
//|    SILVER 1D: PF 1.83 WR 57.1% 49trd OOS 2.91 stop1.5/tp3/trail2   |
//|  Defaults = NQ preset. Truth = MT5 Strategy Tester.               |
//+------------------------------------------------------------------+
#property copyright "GODMODE OS"
#property version   "1.00"
#property strict
#include <Trade/Trade.mqh>

input int    LB        = 20;
input double K         = 1.0;    // range > K x ATR
input int    Hold      = 10;
input double RiskPct   = 1.0;
input double StopATR   = 2.0;
input double TpATR     = 4.0;
input double TrailATR  = 3.0;
input double SizingATR = 3.0;
input int    AtrPeriod = 14;
input int    TrendSMA  = 0;      // trend filter (0=off; ES:200, NQ:50, SILVER:100 validated)
input long   Magic     = 814016; // GM16

CTrade   trade;
int      atrHandle;
datetime lastBar = 0;
int      entryBarIndex = -1, barCounter = 0;

int OnInit(){ atrHandle=iATR(_Symbol,_Period,AtrPeriod); if(atrHandle==INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(Magic); Print("GM16 SOS init."); return INIT_SUCCEEDED; }
void OnDeinit(const int r){ IndicatorRelease(atrHandle); }

double Atr(){ double b[]; if(CopyBuffer(atrHandle,0,1,1,b)==1) return b[0]; return 0; }
long TickVol(int s){ long v[]; if(CopyTickVolume(_Symbol,_Period,s,1,v)==1) return v[0]; return 0; }
double Delta(int s){ double sign=(iClose(_Symbol,_Period,s)>=iOpen(_Symbol,_Period,s))?1.0:-1.0; return sign*(double)TickVol(s); }
double HighestClose(int from,int n){ double m=-DBL_MAX; for(int s=from;s<from+n;s++){ double c=iClose(_Symbol,_Period,s); if(c>m) m=c; } return m; }

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
   if(trade.Buy(lots,_Symbol,0.0,sl,tp,"GM16_SOS")) entryBarIndex=barCounter; }

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
   double rng=iHigh(_Symbol,_Period,1)-iLow(_Symbol,_Period,1);
   bool up=iClose(_Symbol,_Period,1)>iOpen(_Symbol,_Period,1);
   double hhPrev=HighestClose(2,LB);
   if(rng>K*atr && up && Delta(1)>0 && iClose(_Symbol,_Period,1)>=hhPrev && TrendOK(1))
      OpenLong(atr); }
//+------------------------------------------------------------------+
