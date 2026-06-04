//+------------------------------------------------------------------+
//|                                    GM17_InitialBalance.mq5       |
//|                      GODMODE Master EA Library  -  Archetype 17   |
//|  Initial Balance: range of the first N minutes of the session,    |
//|  then trade the breakout (market-profile IB extension).           |
//+------------------------------------------------------------------+
#property copyright "GODMODE Master Library"
#property version   "1.00"
#property strict

#include <GODMODE/GODMODE_Core.mqh>

input group "=== Identity ==="
input long   InpMagic            = 9017;

input group "=== Risk Mode ==="
input GM_RiskMode InpRiskMode    = RISK_CONSERVATIVE;
input double InpRiskConservative = 1.0;
input double InpRiskAggressive   = 3.0;
input double InpRiskFlip          = 8.0;
input double InpMaxLotRiskMult   = 3.0;

input group "=== Session (broker time) ==="
input int    InpIBStartHour      = 8;
input int    InpIBEndHour        = 9;
input int    InpTradeEndHour     = 16;
input int    InpForceCloseHour   = 22;

input group "=== Signals ==="
input int    InpSLPaddingPoints  = 20;
input bool   InpSLOppositeEdge   = false;      // SL at opposite IB edge instead of bar extreme
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
double    g_ibHi = -DBL_MAX, g_ibLo = DBL_MAX;
bool      g_ibValid = false;

int OnInit()
  {
   g_trade.Init(InpMagic);
   g_guards.Init(InpMagic);
   g_log.Init("GODMODE_GM17_InitialBalance_log.csv");
   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   Print("GM17 Initial Balance initialised. RiskMode=", EnumToString(InpRiskMode));
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
   if(g_guards.IsNewDay()) { g_guards.OnNewDay(); g_tradesToday=0; g_ibHi=-DBL_MAX; g_ibLo=DBL_MAX; g_ibValid=false; }
   if(g_guards.IsHalted()) return;
   if(g_guards.DailyDDBreached(InpMaxDailyDDPct))
     { g_trade.CloseAll(); g_guards.Halt(); g_log.Log("GM17","KILL_DD",GM_NONE,0,0,0,0,0,0,"daily DD"); return; }
   if(InpMaxConsecLosses>0 && g_guards.TrailingLossStreak()>=InpMaxConsecLosses) { g_guards.Halt(); return; }
   if(st.hour >= InpForceCloseHour) { g_trade.CloseAll(); return; }

   int mod=st.hour*60+st.min;
   double hi1=iHigh(_Symbol,PERIOD_CURRENT,1), lo1=iLow(_Symbol,PERIOD_CURRENT,1);

   if(GM_InWindow(mod, InpIBStartHour*60, InpIBEndHour*60))
     { if(hi1>g_ibHi) g_ibHi=hi1; if(lo1<g_ibLo) g_ibLo=lo1; g_ibValid=(g_ibHi>g_ibLo); return; }
   if(!g_ibValid) return;
   if(!GM_InWindow(mod, InpIBEndHour*60, InpTradeEndHour*60)) return;
   if(g_trade.HasPosition() || g_tradesToday>=InpMaxTradesPerDay) return;
   if(!g_guards.SpreadOK(InpMaxSpreadPoints)) return;

   double close=iClose(_Symbol,PERIOD_CURRENT,1);
   double pad=InpSLPaddingPoints*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   GM_Dir dir=GM_NONE; double sl=0.0;
   if(close>g_ibHi) { dir=GM_LONG;  sl=InpSLOppositeEdge ? g_ibLo-pad : lo1-pad; }
   else if(close<g_ibLo) { dir=GM_SHORT; sl=InpSLOppositeEdge ? g_ibHi+pad : hi1+pad; }
   if(dir==GM_NONE) return;

   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK), bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double entry=(dir==GM_LONG)?ask:bid;
   double risk=MathAbs(entry-sl); if(risk<=0) return;
   double tp=(dir==GM_LONG)?entry+risk*InpRR:entry-risk*InpRR;

   double lots=GM_CalcLots(risk, RiskPct(), MaxLotMult());
   if(lots<=0.0) { g_log.Log("GM17","SKIP_SIZE",dir,entry,sl,tp,0,InpRR,0,"min lot risk too high"); return; }

   if(g_trade.Open(dir, lots, sl, tp, "GM17_IB"))
     { g_tradesToday++; g_log.Log("GM17","ENTRY",dir,entry,sl,tp,lots,InpRR,1,"IB breakout"); }
  }
//+------------------------------------------------------------------+
