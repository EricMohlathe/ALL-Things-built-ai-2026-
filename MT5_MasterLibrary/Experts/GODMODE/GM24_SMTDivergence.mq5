//+------------------------------------------------------------------+
//|                                    GM24_SMTDivergence.mq5        |
//|                      GODMODE Master EA Library  -  Archetype 24   |
//|  ICT Smart-Money Technique: a correlated pair fails to confirm a  |
//|  new high/low made by this symbol -> reversal signal.             |
//+------------------------------------------------------------------+
#property copyright "GODMODE Master Library"
#property version   "1.00"
#property strict

#include <GODMODE/GODMODE_Core.mqh>

input group "=== Identity ==="
input long   InpMagic            = 9024;

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
input string InpOtherSymbol      = "GBPUSD";
input bool   InpPositiveCorr     = true;
input int    InpWindowBars       = 12;
input int    InpSLPaddingPoints  = 10;
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
   g_log.Init("GODMODE_GM24_SMTDivergence_log.csv");
   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   SymbolSelect(InpOtherSymbol, true);
   Print("GM24 SMT Divergence initialised vs ", InpOtherSymbol, ". RiskMode=", EnumToString(InpRiskMode));
   return INIT_SUCCEEDED;
  }
void OnDeinit(const int reason) { }

double ATRValue() { double b[]; if(g_atrHandle==INVALID_HANDLE||CopyBuffer(g_atrHandle,0,1,1,b)<=0) return 0.0; return b[0]; }
double RiskPct()  { return GM_ResolveRiskPct(InpRiskMode, InpRiskConservative, InpRiskAggressive, InpRiskFlip); }
double MaxLotMult(){ return (InpRiskMode == RISK_FLIP) ? 1000.0 : InpMaxLotRiskMult; }
double HHsym(const string sym,const int lb,const int start){ double hi=-DBL_MAX; for(int i=start;i<start+lb;i++){ double h=iHigh(sym,PERIOD_CURRENT,i); if(h>hi) hi=h; } return hi; }
double LLsym(const string sym,const int lb,const int start){ double lo= DBL_MAX; for(int i=start;i<start+lb;i++){ double l=iLow(sym,PERIOD_CURRENT,i);  if(l<lo) lo=l; } return lo; }

void OnTick()
  {
   g_trade.Manage(InpBEatR, InpPartialAtR, InpPartialPct, InpUseTrail, InpTrailATRMult, ATRValue());
   if(!GM_IsNewBar(PERIOD_CURRENT, g_lastBar)) return;

   MqlDateTime st; TimeToStruct(TimeCurrent(), st);
   if(g_guards.IsNewDay()) { g_guards.OnNewDay(); g_tradesToday=0; }
   if(g_guards.IsHalted()) return;
   if(g_guards.DailyDDBreached(InpMaxDailyDDPct))
     { g_trade.CloseAll(); g_guards.Halt(); g_log.Log("GM24","KILL_DD",GM_NONE,0,0,0,0,0,0,"daily DD"); return; }
   if(InpMaxConsecLosses>0 && g_guards.TrailingLossStreak()>=InpMaxConsecLosses) { g_guards.Halt(); return; }
   if(st.hour >= InpForceCloseHour) { g_trade.CloseAll(); return; }
   if(InpUseSession && !GM_InWindow(st.hour*60+st.min, InpTradeStartHour*60, InpTradeEndHour*60)) return;
   if(g_trade.HasPosition() || g_tradesToday>=InpMaxTradesPerDay) return;
   if(!g_guards.SpreadOK(InpMaxSpreadPoints)) return;
   if(iBars(InpOtherSymbol,PERIOD_CURRENT) < 2*InpWindowBars+2) return;

   int W=InpWindowBars;
   double tNearHi=GM_HighestHigh(W,1), tFarHi=GM_HighestHigh(W,W+1);
   double tNearLo=GM_LowestLow(W,1),  tFarLo=GM_LowestLow(W,W+1);
   double oNearHi=HHsym(InpOtherSymbol,W,1), oFarHi=HHsym(InpOtherSymbol,W,W+1);
   double oNearLo=LLsym(InpOtherSymbol,W,1), oFarLo=LLsym(InpOtherSymbol,W,W+1);

   double o1=iOpen(_Symbol,PERIOD_CURRENT,1), c1=iClose(_Symbol,PERIOD_CURRENT,1);
   double pad=InpSLPaddingPoints*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   GM_Dir dir=GM_NONE; double sl=0.0;

   bool otherFailHigh = InpPositiveCorr ? (oNearHi<=oFarHi) : (oNearLo>=oFarLo);
   bool otherFailLow  = InpPositiveCorr ? (oNearLo>=oFarLo) : (oNearHi<=oFarHi);
   if(tNearHi>tFarHi && otherFailHigh && c1<o1)      { dir=GM_SHORT; sl=tNearHi+pad; }
   else if(tNearLo<tFarLo && otherFailLow && c1>o1)  { dir=GM_LONG;  sl=tNearLo-pad; }
   if(dir==GM_NONE) return;

   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK), bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double entry=(dir==GM_LONG)?ask:bid;
   double risk=MathAbs(entry-sl); if(risk<=0) return;
   double tp=(dir==GM_LONG)?entry+risk*InpRR:entry-risk*InpRR;

   double lots=GM_CalcLots(risk, RiskPct(), MaxLotMult());
   if(lots<=0.0) { g_log.Log("GM24","SKIP_SIZE",dir,entry,sl,tp,0,InpRR,0,"min lot risk too high"); return; }

   if(g_trade.Open(dir, lots, sl, tp, "GM24_SMT"))
     { g_tradesToday++; g_log.Log("GM24","ENTRY",dir,entry,sl,tp,lots,InpRR,1,"SMT vs "+InpOtherSymbol); }
  }
//+------------------------------------------------------------------+
