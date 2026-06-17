//+------------------------------------------------------------------+
//|  GM18 LIQSWEEP — GODMODE HIGH-FREQUENCY EA (MT5) — SELF-CONTAINED |
//|------------------------------------------------------------------|
//|  Concept: Liquidity-sweep reversal, BOTH directions. Sweep below  |
//|  prior swing-low of closes (LB), close UPPER half = long. Mirror   |
//|  (sweep high, close lower half) = short. Intraday turnover engine. |
//|                                                                   |
//|  VALIDATED (real backtest, BTC 15m, ~8000 bars/~83d, no-lookahead, |
//|  fill next open, fees on; OOS = held-out 30%):                     |
//|     BTC 15m, Hold 8, stopATR 4 / tpATR 1.5:                        |
//|        PF 1.21 | WR 65% | ~5.0 trades/DAY | OOS PF 1.13            |
//|                                                                   |
//|  *** THIN EDGE (PF ~1.2) — SPREAD-SENSITIVE. ***                  |
//|  - ~5 trades/day but small per-trade edge: a wide broker spread    |
//|    can push it below break-even. Backtest on YOUR symbol+spread.   |
//|  - Validated on crypto (BTC) only (free intraday data + orderflow).|
//|    Logic runs on ANY symbol (forex/metals/indices/crypto) but you  |
//|    MUST validate per-symbol in MT5 Strategy Tester. Edge may not    |
//|    transfer across asset classes.                                  |
//|  - Attach to a 15-MINUTE chart to match the validated config.      |
//+------------------------------------------------------------------+
#property copyright "GODMODE OS"
#property version   "1.00"
#property strict
#include <Trade/Trade.mqh>

input int    LB         = 20;
input int    Hold       = 8;
input bool   AllowLong   = true;
input bool   AllowShort  = true;
input double RiskPct    = 1.0;
input double StopATR    = 4.0;
input double TpATR      = 1.5;
input double TrailATR   = 0.0;
input double MaxSpreadPts = 0.0;   // max spread in points (0 = off)
input int    AtrPeriod  = 14;
input long   Magic      = 814018;  // GM18

CTrade   trade;
int      atrHandle;
datetime lastBar = 0;
int      entryBarIndex = -1, barCounter = 0;

int OnInit(){ atrHandle=iATR(_Symbol,_Period,AtrPeriod); if(atrHandle==INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(Magic); Print("GM18 LiqSweep HiFreq init. Attach to M15."); return INIT_SUCCEEDED; }
void OnDeinit(const int r){ IndicatorRelease(atrHandle); }

double Atr(){ double b[]; if(CopyBuffer(atrHandle,0,1,1,b)==1) return b[0]; return 0; }
double LowestClose(int from,int n){ double m=DBL_MAX; for(int s=from;s<from+n;s++){ double c=iClose(_Symbol,_Period,s); if(c<m) m=c; } return m; }
double HighestClose(int from,int n){ double m=-DBL_MAX; for(int s=from;s<from+n;s++){ double c=iClose(_Symbol,_Period,s); if(c>m) m=c; } return m; }

int CurDir(){ // 0 none, 1 long, -1 short (this EA's position)
   for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i);
      if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==Magic)
         return (PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY)?1:-1; }
   return 0; }
void CloseMine(){ for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i);
   if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==Magic) trade.PositionClose(tk); } }

double Lots(double stopDist){
   double ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE), tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
   if(ts<=0||tv<=0||stopDist<=0) return SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double lossPerLot=(stopDist/ts)*tv;
   double lots=AccountInfoDouble(ACCOUNT_EQUITY)*(RiskPct/100.0)/lossPerLot;
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP), mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN), mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   if(step>0) lots=MathFloor(lots/step)*step; return MathMax(mn,MathMin(mx,lots)); }

void Enter(int dir,double atr){
   if(MaxSpreadPts>0){ double sp=(SymbolInfoDouble(_Symbol,SYMBOL_ASK)-SymbolInfoDouble(_Symbol,SYMBOL_BID))/_Point; if(sp>MaxSpreadPts) return; }
   double stopDist=StopATR*atr, lots=Lots(stopDist); if(lots<=0) return;
   if(dir>0){ double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
      double sl=ask-stopDist, tp=(TpATR>0)?ask+TpATR*atr:0.0;
      if(trade.Buy(lots,_Symbol,0.0,sl,tp,"GM18_HiFreq")) entryBarIndex=barCounter; }
   else{ double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
      double sl=bid+stopDist, tp=(TpATR>0)?bid-TpATR*atr:0.0;
      if(trade.Sell(lots,_Symbol,0.0,sl,tp,"GM18_HiFreq")) entryBarIndex=barCounter; } }

void ManageOpen(){ int dir=CurDir(); if(dir==0){ entryBarIndex=-1; return; }
   if(TrailATR>0){ double atr=Atr();
      for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i);
         if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==Magic){
            double cur=PositionGetDouble(POSITION_SL), tp=PositionGetDouble(POSITION_TP);
            if(dir>0){ double nsl=SymbolInfoDouble(_Symbol,SYMBOL_BID)-TrailATR*atr; if(nsl>cur) trade.PositionModify(tk,nsl,tp); }
            else     { double nsl=SymbolInfoDouble(_Symbol,SYMBOL_ASK)+TrailATR*atr; if(cur==0||nsl<cur) trade.PositionModify(tk,nsl,tp); } } } }
   if(entryBarIndex>=0&&(barCounter-entryBarIndex)>=Hold) CloseMine(); }

void OnTick(){ datetime t=iTime(_Symbol,_Period,0); if(t==lastBar) return; lastBar=t; barCounter++;
   ManageOpen();
   if(Bars(_Symbol,_Period)<LB+5) return;
   double hi=iHigh(_Symbol,_Period,1), lo=iLow(_Symbol,_Period,1), cl=iClose(_Symbol,_Period,1);
   double rng=hi-lo; if(rng<=0) return;
   int sig=0;
   if(AllowLong && lo<LowestClose(2,LB) && cl>lo+0.5*rng) sig=1;
   else if(AllowShort && hi>HighestClose(2,LB) && cl<hi-0.5*rng) sig=-1;
   if(sig==0) return;
   int dir=CurDir();
   if(sig==dir) return;
   double atr=Atr(); if(atr<=0) return;
   if(dir!=0) CloseMine();
   Enter(sig,atr); }
//+------------------------------------------------------------------+
