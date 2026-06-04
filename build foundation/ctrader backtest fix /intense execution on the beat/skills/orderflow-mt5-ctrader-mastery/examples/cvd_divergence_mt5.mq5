//+------------------------------------------------------------------+
//|  CVD Divergence EA — bear divergence enters short                |
//+------------------------------------------------------------------+
#property version "1.00"
#property strict
#include <Trade/Trade.mqh>
CTrade trade;

input int    InpMagic       = 20260431;
input double InpRiskPct     = 0.5;
input int    InpLookback    = 20;
input string InpComment     = "CVD_DIV";

double  g_cvd[];
datetime g_lastBar = 0;
double  g_prevAsk=0, g_prevBid=0, g_curDelta=0;

int OnInit(){ trade.SetExpertMagicNumber(InpMagic); return INIT_SUCCEEDED; }

bool IsNewBar(){ datetime t=iTime(_Symbol,_Period,0); if(t==g_lastBar) return false; g_lastBar=t; return true; }

void UpdateCvd()
{
   MqlTick tk; if(!SymbolInfoTick(_Symbol,tk)) return;
   if(g_prevAsk==0){g_prevAsk=tk.ask;g_prevBid=tk.bid;return;}
   double s=0; if(tk.last>=g_prevAsk) s=1; else if(tk.last<=g_prevBid) s=-1;
   double v=(tk.volume>0?(double)tk.volume:1.0);
   g_curDelta += s*v;
   g_prevAsk=tk.ask; g_prevBid=tk.bid;
}

void OnNewBarBookkeeping()
{
   ArrayResize(g_cvd, ArraySize(g_cvd)+1);
   int last=ArraySize(g_cvd)-1;
   g_cvd[last] = (last>0 ? g_cvd[last-1] : 0) + g_curDelta;
   g_curDelta = 0;
}

bool IsBearDivergence()
{
   int n = ArraySize(g_cvd);
   if(n < InpLookback+2) return false;
   double pHigh = iHigh(_Symbol,_Period,1);
   double dHigh = g_cvd[n-2];
   for(int i=2;i<=InpLookback;i++)
   {
      double pi = iHigh(_Symbol,_Period,i);
      double di = g_cvd[n-1-i];
      if(pi > pHigh && di < dHigh) return true;
   }
   return false;
}

double LotByRisk(double slPts)
{
   double bal=AccountInfoDouble(ACCOUNT_BALANCE);
   double tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
   double ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   double pt=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double pv=tv*(pt/ts); if(pv<=0||slPts<=0) return 0;
   double lots = bal*InpRiskPct/100.0/(slPts*pv);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   return MathMax(MathFloor(lots/step)*step, SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN));
}

void OnTick()
{
   UpdateCvd();
   if(!IsNewBar()) return;
   OnNewBarBookkeeping();
   if(PositionsTotal()>0) return;

   if(IsBearDivergence())
   {
      double pt=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
      double slPts = 300;
      double price=SymbolInfoDouble(_Symbol,SYMBOL_BID);
      double sl=price+slPts*pt, tp=price-2*slPts*pt;
      double lots=LotByRisk(slPts);
      if(lots>0) trade.Sell(lots,_Symbol,price,sl,tp,InpComment);
   }
}
