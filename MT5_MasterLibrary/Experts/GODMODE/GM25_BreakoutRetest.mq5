//+------------------------------------------------------------------+
//|                                    GM25_BreakoutRetest.mq5       |
//|                      GODMODE Master EA Library  -  Archetype 25   |
//|  Range break, then enter on the retest that holds the broken      |
//|  level (break-and-retest / VWAP-reclaim-retest family).           |
//+------------------------------------------------------------------+
#property copyright "GODMODE Master Library"
#property version   "1.00"
#property strict

#include <GODMODE/GODMODE_Core.mqh>

input group "=== Identity ==="
input long   InpMagic            = 9025;

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
input int    InpRangeLookback    = 20;
input int    InpRetestTolPoints  = 20;
input int    InpMaxWaitBars      = 8;
input int    InpSLPaddingPoints  = 10;
input double InpRR               = 2.0;
input int    InpATRPeriod        = 14;
input int    InpMaxTradesPerDay  = 3;

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
bool      g_brkUp = false, g_brkDn = false;
double    g_lvlUp = 0, g_lvlDn = 0;
int       g_ageUp = 0, g_ageDn = 0;

int OnInit()
  {
   g_trade.Init(InpMagic);
   g_guards.Init(InpMagic);
   g_log.Init("GODMODE_GM25_BreakoutRetest_log.csv");
   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   Print("GM25 Breakout-Retest initialised. RiskMode=", EnumToString(InpRiskMode));
   return INIT_SUCCEEDED;
  }
void OnDeinit(const int reason) { }

double ATRValue() { double b[]; if(g_atrHandle==INVALID_HANDLE||CopyBuffer(g_atrHandle,0,1,1,b)<=0) return 0.0; return b[0]; }
double RiskPct()  { return GM_ResolveRiskPct(InpRiskMode, InpRiskConservative, InpRiskAggressive, InpRiskFlip); }
double MaxLotMult(){ return (InpRiskMode == RISK_FLIP) ? 1000.0 : InpMaxLotRiskMult; }

void OnTick()
  {
   g_trade.Manage(InpBEatR, InpPartialAtR, InpPartialPct, InpUseTrail, InpTrailATRMult, ATRValue());
   if(!GM_IsNewBar(PERIOD_CURRENT, g_lastBar)) return;

   MqlDateTime st; TimeToStruct(TimeCurrent(), st);
   if(g_guards.IsNewDay()) { g_guards.OnNewDay(); g_tradesToday=0; }
   if(g_guards.IsHalted()) return;
   if(g_guards.DailyDDBreached(InpMaxDailyDDPct))
     { g_trade.CloseAll(); g_guards.Halt(); g_log.Log("GM25","KILL_DD",GM_NONE,0,0,0,0,0,0,"daily DD"); return; }
   if(InpMaxConsecLosses>0 && g_guards.TrailingLossStreak()>=InpMaxConsecLosses) { g_guards.Halt(); return; }
   if(st.hour >= InpForceCloseHour) { g_trade.CloseAll(); return; }

   double rh=GM_HighestHigh(InpRangeLookback,2), rl=GM_LowestLow(InpRangeLookback,2);
   double c1=iClose(_Symbol,PERIOD_CURRENT,1), hi1=iHigh(_Symbol,PERIOD_CURRENT,1), lo1=iLow(_Symbol,PERIOD_CURRENT,1);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double tol=InpRetestTolPoints*point, pad=InpSLPaddingPoints*point;

   if(!g_brkUp && c1>rh)      { g_brkUp=true; g_lvlUp=rh; g_ageUp=0; }
   else if(g_brkUp)           { g_ageUp++; if(g_ageUp>InpMaxWaitBars || c1<g_lvlUp-tol) g_brkUp=false; }
   if(!g_brkDn && c1<rl)      { g_brkDn=true; g_lvlDn=rl; g_ageDn=0; }
   else if(g_brkDn)           { g_ageDn++; if(g_ageDn>InpMaxWaitBars || c1>g_lvlDn+tol) g_brkDn=false; }

   if(InpUseSession && !GM_InWindow(st.hour*60+st.min, InpTradeStartHour*60, InpTradeEndHour*60)) return;
   if(g_trade.HasPosition() || g_tradesToday>=InpMaxTradesPerDay) return;
   if(!g_guards.SpreadOK(InpMaxSpreadPoints)) return;

   GM_Dir dir=GM_NONE; double sl=0.0;
   if(g_brkUp && lo1<=g_lvlUp+tol && c1>g_lvlUp)      { dir=GM_LONG;  sl=g_lvlUp-pad; g_brkUp=false; }
   else if(g_brkDn && hi1>=g_lvlDn-tol && c1<g_lvlDn) { dir=GM_SHORT; sl=g_lvlDn+pad; g_brkDn=false; }
   if(dir==GM_NONE) return;

   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK), bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double entry=(dir==GM_LONG)?ask:bid;
   double risk=MathAbs(entry-sl); if(risk<=0) return;
   double tp=(dir==GM_LONG)?entry+risk*InpRR:entry-risk*InpRR;

   double lots=GM_CalcLots(risk, RiskPct(), MaxLotMult());
   if(lots<=0.0) { g_log.Log("GM25","SKIP_SIZE",dir,entry,sl,tp,0,InpRR,0,"min lot risk too high"); return; }

   if(g_trade.Open(dir, lots, sl, tp, "GM25_BR"))
     { g_tradesToday++; g_log.Log("GM25","ENTRY",dir,entry,sl,tp,lots,InpRR,1,"breakout-retest hold"); }
  }
//+------------------------------------------------------------------+
