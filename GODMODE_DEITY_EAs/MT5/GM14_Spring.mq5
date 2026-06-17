//+------------------------------------------------------------------+
//|  GM14 SPRING — GODMODE DEITY EA (MetaTrader 5) — SELF-CONTAINED   |
//|------------------------------------------------------------------|
//|  Concept: Wyckoff spring / liquidity-sweep reclaim. Low wicks     |
//|  BELOW the prior swing-low of closes (lookback LB), close back     |
//|  ABOVE it = stop-run reversal long. Long-only (long side validated)|
//|                                                                   |
//|  VALIDATED (real backtest, OpenAlice stdlib engine, ~1000 daily   |
//|  bars, no-lookahead, fill next open, fees on; OOS = held-out 30%): |
//|    SILVER 1D: PF 5.74 WR 71.7% 53trd +323.5% OOS 8.96  exits NONE  |
//|    YM     1D: PF 2.48 WR 81.0% 58trd +59.8%  OOS 2.01  stop4/tp1.5 |
//|    GOLD   1D: PF 2.29 WR 75.5% 49trd +27.6%  OOS 2.78  stop3/tp1   |
//|    ES     1D: PF 1.72 WR 78.0% 50trd +24.4%  OOS 1.26  stop4/tp1.5 |
//|  Defaults = GOLD preset (has a stop). SILVER max-PF = stop0/tp0.   |
//|  Edge is TREND-ALIGNED. Truth = MT5 Strategy Tester.              |
//+------------------------------------------------------------------+
#property copyright "GODMODE OS"
#property version   "1.00"
#property strict
#include <Trade/Trade.mqh>

input int    LB        = 20;     // Lookback (swing window, closes)
input int    Hold      = 10;     // Hold bars (time exit)
input double RiskPct   = 1.0;    // Risk % of equity per trade
input double StopATR   = 3.0;    // Stop = StopATR x ATR (0 = no hard stop)
input double TpATR     = 1.0;    // TP   = TpATR  x ATR (0 = none)
input double TrailATR  = 0.0;    // Trailing stop ATR mult (0 = off)
input double SizingATR = 3.0;    // ATR mult used for sizing when StopATR=0
input int    AtrPeriod = 14;
input long   Magic     = 814014; // GM14

CTrade   trade;
int      atrHandle;
datetime lastBar = 0;
int      entryBarIndex = -1;
int      barCounter = 0;

int OnInit()
{
   atrHandle = iATR(_Symbol, _Period, AtrPeriod);
   if(atrHandle == INVALID_HANDLE) return(INIT_FAILED);
   trade.SetExpertMagicNumber(Magic);
   PrintFormat("GM14 Spring init. LB=%d Hold=%d Stop=%.1f TP=%.1f", LB, Hold, StopATR, TpATR);
   return(INIT_SUCCEEDED);
}
void OnDeinit(const int r){ IndicatorRelease(atrHandle); }

double Atr()
{ double b[]; if(CopyBuffer(atrHandle,0,1,1,b)==1) return b[0]; return 0; }

long TickVol(int shift)
{ long v[]; if(CopyTickVolume(_Symbol,_Period,shift,1,v)==1) return v[0]; return 0; }

double Delta(int shift)
{ double sign = (iClose(_Symbol,_Period,shift) >= iOpen(_Symbol,_Period,shift)) ? 1.0 : -1.0;
  return sign * (double)TickVol(shift); }

double LowestClose(int from,int n)
{ double m = DBL_MAX; for(int s=from; s<from+n; s++){ double c=iClose(_Symbol,_Period,s); if(c<m) m=c; } return m; }

bool HasPosition()
{
   for(int i=PositionsTotal()-1;i>=0;i--){
      ulong tk=PositionGetTicket(i);
      if(PositionSelectByTicket(tk) && PositionGetString(POSITION_SYMBOL)==_Symbol
         && PositionGetInteger(POSITION_MAGIC)==Magic) return true;
   }
   return false;
}

double LotsForRisk(double atr)
{
   double riskRef = (StopATR>0 ? StopATR : SizingATR) * atr;        // price distance
   if(riskRef<=0) return 0;
   double tickSize = SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   double tickVal  = SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
   if(tickSize<=0 || tickVal<=0) return SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double lossPerLot = (riskRef/tickSize)*tickVal;
   double riskCash = AccountInfoDouble(ACCOUNT_EQUITY)*(RiskPct/100.0);
   double lots = (lossPerLot>0) ? riskCash/lossPerLot : 0;
   double step = SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   double mn   = SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double mx   = SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   if(step>0) lots = MathFloor(lots/step)*step;
   lots = MathMax(mn, MathMin(mx, lots));
   return lots;
}

void OpenLong(double atr)
{
   double lots = LotsForRisk(atr);
   if(lots<=0) return;
   double ask = SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double sl  = (StopATR>0) ? ask - StopATR*atr : 0.0;
   double tp  = (TpATR>0)   ? ask + TpATR*atr   : 0.0;
   if(trade.Buy(lots,_Symbol,0.0,sl,tp,"GM14_Spring"))
   { entryBarIndex = barCounter; }
}

void ManageOpen()
{
   if(!HasPosition()){ entryBarIndex = -1; return; }
   // trailing stop (ratchet up)
   if(TrailATR>0){
      double atr=Atr(); double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
      double newSl=bid-TrailATR*atr;
      for(int i=PositionsTotal()-1;i>=0;i--){
         ulong tk=PositionGetTicket(i);
         if(PositionSelectByTicket(tk) && PositionGetString(POSITION_SYMBOL)==_Symbol
            && PositionGetInteger(POSITION_MAGIC)==Magic){
            double curSl=PositionGetDouble(POSITION_SL);
            if(newSl>curSl) trade.PositionModify(tk,newSl,PositionGetDouble(POSITION_TP));
         }
      }
   }
   // time exit
   if(entryBarIndex>=0 && (barCounter-entryBarIndex)>=Hold){
      for(int i=PositionsTotal()-1;i>=0;i--){
         ulong tk=PositionGetTicket(i);
         if(PositionSelectByTicket(tk) && PositionGetString(POSITION_SYMBOL)==_Symbol
            && PositionGetInteger(POSITION_MAGIC)==Magic) trade.PositionClose(tk);
      }
   }
}

void OnTick()
{
   datetime t = iTime(_Symbol,_Period,0);
   if(t==lastBar) return;        // act once per new bar
   lastBar = t; barCounter++;

   ManageOpen();
   if(HasPosition()) return;
   if(Bars(_Symbol,_Period) < LB+5) return;

   double sigLow   = iLow(_Symbol,_Period,1);
   double sigClose = iClose(_Symbol,_Period,1);
   double llPrev   = LowestClose(2, LB);
   double atr      = Atr();
   if(atr<=0) return;

   if(sigLow < llPrev && sigClose > llPrev)   // GM14 spring (long)
      OpenLong(atr);
}
//+------------------------------------------------------------------+
