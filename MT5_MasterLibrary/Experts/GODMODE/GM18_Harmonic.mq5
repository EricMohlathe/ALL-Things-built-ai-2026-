//+------------------------------------------------------------------+
//|                                    GM18_Harmonic.mq5             |
//|                      GODMODE Master EA Library  -  Archetype 18   |
//|  Harmonic patterns (XABCD): Gartley / Bat / Butterfly / Crab via  |
//|  Fibonacci leg ratios on alternating fractal swings.              |
//+------------------------------------------------------------------+
#property copyright "GODMODE Master Library"
#property version   "1.00"
#property strict

#include <GODMODE/GODMODE_Core.mqh>

input group "=== Identity ==="
input long   InpMagic            = 9018;

input group "=== Risk Mode ==="
input GM_RiskMode InpRiskMode    = RISK_CONSERVATIVE;
input double InpRiskConservative = 1.0;
input double InpRiskAggressive   = 3.0;
input double InpRiskFlip          = 8.0;
input double InpMaxLotRiskMult   = 3.0;

input group "=== Session (broker time) ==="
input bool   InpUseSession       = true;
input int    InpTradeStartHour   = 6;
input int    InpTradeEndHour     = 20;
input int    InpForceCloseHour   = 22;

input group "=== Signals ==="
input int    InpSwingLookback    = 120;
input int    InpSwingWing        = 3;
input double InpTol              = 0.09;
input int    InpMaxDBars         = 5;
input double InpPRZMult          = 1.0;
input int    InpSLPaddingPoints  = 20;
input double InpRR               = 2.0;
input int    InpATRPeriod        = 14;
input int    InpMaxTradesPerDay  = 2;

input group "=== Trade Management ==="
input double InpBEatR            = 1.0;
input double InpPartialAtR       = 1.0;
input double InpPartialPct       = 50.0;
input bool   InpUseTrail         = false;
input double InpTrailATRMult     = 1.5;

input group "=== Guards ==="
input double InpMaxDailyDDPct    = 6.0;
input int    InpMaxConsecLosses  = 3;
input double InpMaxSpreadPoints  = 0;

CGMTrade  g_trade;
CGMGuards g_guards;
CGMLogger g_log;
int       g_atrHandle = INVALID_HANDLE;
datetime  g_lastBar   = 0;
int       g_tradesToday = 0;

int OnInit()
  {
   g_trade.Init(InpMagic);
   g_guards.Init(InpMagic);
   g_log.Init("GODMODE_GM18_Harmonic_log.csv");
   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   Print("GM18 Harmonic initialised. RiskMode=", EnumToString(InpRiskMode));
   return INIT_SUCCEEDED;
  }
void OnDeinit(const int reason) { }

double ATRValue() { double b[]; if(g_atrHandle==INVALID_HANDLE||CopyBuffer(g_atrHandle,0,1,1,b)<=0) return 0.0; return b[0]; }
double RiskPct()  { return GM_ResolveRiskPct(InpRiskMode, InpRiskConservative, InpRiskAggressive, InpRiskFlip); }
double MaxLotMult(){ return (InpRiskMode == RISK_FLIP) ? 1000.0 : InpMaxLotRiskMult; }
bool   NearR(const double x, const double t, const double tol) { return MathAbs(x-t)<=tol; }

void OnTick()
  {
   g_trade.Manage(InpBEatR, InpPartialAtR, InpPartialPct, InpUseTrail, InpTrailATRMult, ATRValue());
   if(!GM_IsNewBar(PERIOD_CURRENT, g_lastBar)) return;

   MqlDateTime st; TimeToStruct(TimeCurrent(), st);
   if(g_guards.IsNewDay()) { g_guards.OnNewDay(); g_tradesToday=0; }
   if(g_guards.IsHalted()) return;
   if(g_guards.DailyDDBreached(InpMaxDailyDDPct))
     { g_trade.CloseAll(); g_guards.Halt(); g_log.Log("GM18","KILL_DD",GM_NONE,0,0,0,0,0,0,"daily DD"); return; }
   if(InpMaxConsecLosses>0 && g_guards.TrailingLossStreak()>=InpMaxConsecLosses) { g_guards.Halt(); return; }
   if(st.hour >= InpForceCloseHour) { g_trade.CloseAll(); return; }
   if(InpUseSession && !GM_InWindow(st.hour*60+st.min, InpTradeStartHour*60, InpTradeEndHour*60)) return;
   if(g_trade.HasPosition() || g_tradesToday>=InpMaxTradesPerDay) return;
   if(!g_guards.SpreadOK(InpMaxSpreadPoints)) return;

   double pp[5]; int psh[5]; bool phi[5]; int n=0, lastType=0;
   for(int s=InpSwingWing+1; s<=InpSwingLookback && n<5; s++)
     {
      if(GM_IsSwingHigh(s,InpSwingWing) && lastType!=1)
        { pp[n]=iHigh(_Symbol,PERIOD_CURRENT,s); psh[n]=s; phi[n]=true;  lastType=1;  n++; }
      else if(GM_IsSwingLow(s,InpSwingWing) && lastType!=-1)
        { pp[n]=iLow(_Symbol,PERIOD_CURRENT,s);  psh[n]=s; phi[n]=false; lastType=-1; n++; }
     }
   if(n<5) return;
   if(psh[0] > InpSwingWing+InpMaxDBars) return;

   double atr=ATRValue(); if(atr<=0) return;
   double D=pp[0], C=pp[1], B=pp[2], A=pp[3], X=pp[4];
   double XA=MathAbs(A-X), AB=MathAbs(B-A), BC=MathAbs(C-B), CD=MathAbs(D-C), AD=MathAbs(D-A);
   if(XA<=0||AB<=0||BC<=0||CD<=0) return;
   double retAB=AB/XA, retBC=BC/AB, retAD=AD/XA;
   bool bcOK   = retBC>=0.382-InpTol && retBC<=0.886+InpTol;
   bool gartley= NearR(retAB,0.618,InpTol) && NearR(retAD,0.786,InpTol);
   bool bat    = retAB>=0.382-InpTol && retAB<=0.5+InpTol && NearR(retAD,0.886,InpTol);
   bool bfly   = NearR(retAB,0.786,InpTol) && retAD>=1.272-InpTol && retAD<=1.618+InpTol;
   bool crab   = retAB>=0.382-InpTol && retAB<=0.618+InpTol && NearR(retAD,1.618,InpTol);
   if(!(bcOK && (gartley||bat||bfly||crab))) return;

   double close=iClose(_Symbol,PERIOD_CURRENT,1);
   if(MathAbs(close-D) > InpPRZMult*atr) return;

   double pad=InpSLPaddingPoints*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   GM_Dir dir = phi[0] ? GM_SHORT : GM_LONG;
   double sl = (dir==GM_LONG) ? iLow(_Symbol,PERIOD_CURRENT,psh[0])-pad : iHigh(_Symbol,PERIOD_CURRENT,psh[0])+pad;

   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK), bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double entry=(dir==GM_LONG)?ask:bid;
   double risk=MathAbs(entry-sl); if(risk<=0) return;
   double tp=(dir==GM_LONG)?entry+risk*InpRR:entry-risk*InpRR;

   double lots=GM_CalcLots(risk, RiskPct(), MaxLotMult());
   string pat = gartley?"Gartley":(bat?"Bat":(bfly?"Butterfly":"Crab"));
   if(lots<=0.0) { g_log.Log("GM18","SKIP_SIZE",dir,entry,sl,tp,0,InpRR,0,"min lot risk too high"); return; }

   if(g_trade.Open(dir, lots, sl, tp, "GM18_"+pat))
     { g_tradesToday++; g_log.Log("GM18","ENTRY",dir,entry,sl,tp,lots,InpRR,1, pat+" PRZ"); }
  }
//+------------------------------------------------------------------+
