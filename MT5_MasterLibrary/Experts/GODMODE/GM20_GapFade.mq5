//+------------------------------------------------------------------+
//|                                    GM20_GapFade.mq5             |
//|                      GODMODE Master EA Library  -  Archetype 20   |
//|  Opening-gap vs prior daily close: fade back to the close, or     |
//|  trade the gap-and-go continuation.                               |
//+------------------------------------------------------------------+
#property copyright "GODMODE Master Library"
#property version   "1.00"
#property strict

#include <GODMODE/GODMODE_Core.mqh>

input group "=== Identity ==="
input long   InpMagic            = 9020;

input group "=== Risk Mode ==="
input GM_RiskMode InpRiskMode    = RISK_CONSERVATIVE;
input double InpRiskConservative = 1.0;
input double InpRiskAggressive   = 3.0;
input double InpRiskFlip          = 8.0;
input double InpMaxLotRiskMult   = 3.0;

input group "=== Session (broker time) ==="
input int    InpSessStartHour    = 8;
input int    InpEntryWindowHours = 3;
input int    InpForceCloseHour   = 22;

input group "=== Signals ==="
input int    InpMode             = 0;          // 0=fade to prior close, 1=gap-and-go
input double InpGapAtrMult       = 0.8;
input double InpSLAtrMult        = 1.5;
input double InpRR               = 2.0;         // used in gap-and-go mode
input int    InpATRPeriod        = 14;
input int    InpMaxTradesPerDay  = 1;

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
   g_log.Init("GODMODE_GM20_GapFade_log.csv");
   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   Print("GM20 Gap Fade/Go initialised. RiskMode=", EnumToString(InpRiskMode));
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
     { g_trade.CloseAll(); g_guards.Halt(); g_log.Log("GM20","KILL_DD",GM_NONE,0,0,0,0,0,0,"daily DD"); return; }
   if(InpMaxConsecLosses>0 && g_guards.TrailingLossStreak()>=InpMaxConsecLosses) { g_guards.Halt(); return; }
   if(st.hour >= InpForceCloseHour) { g_trade.CloseAll(); return; }
   int mod=st.hour*60+st.min;
   if(!GM_InWindow(mod, InpSessStartHour*60, (InpSessStartHour+InpEntryWindowHours)*60)) return;
   if(g_trade.HasPosition() || g_tradesToday>=InpMaxTradesPerDay) return;
   if(!g_guards.SpreadOK(InpMaxSpreadPoints)) return;
   if(iBars(_Symbol,PERIOD_D1)<2) return;

   double atr=ATRValue(); if(atr<=0) return;
   double yClose=iClose(_Symbol,PERIOD_D1,1);
   double tOpen =iOpen(_Symbol,PERIOD_D1,0);
   double gap=tOpen-yClose;
   double thr=InpGapAtrMult*atr;
   if(MathAbs(gap)<thr) return;

   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK), bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   GM_Dir dir=GM_NONE; double sl=0.0, tp=0.0, entry=0.0;

   if(InpMode==0)   // fade toward prior close
     {
      if(gap>0) { dir=GM_SHORT; entry=bid; sl=entry+InpSLAtrMult*atr; tp=yClose; }
      else      { dir=GM_LONG;  entry=ask; sl=entry-InpSLAtrMult*atr; tp=yClose; }
     }
   else             // gap-and-go continuation
     {
      if(gap>0) { dir=GM_LONG;  entry=ask; sl=entry-InpSLAtrMult*atr; }
      else      { dir=GM_SHORT; entry=bid; sl=entry+InpSLAtrMult*atr; }
     }
   if(dir==GM_NONE) return;
   double risk=MathAbs(entry-sl); if(risk<=0) return;
   if(InpMode==1) tp=(dir==GM_LONG)?entry+risk*InpRR:entry-risk*InpRR;
   double rr=MathAbs(tp-entry)/risk;
   if(rr<=0) { g_log.Log("GM20","SKIP_RR",dir,entry,sl,tp,0,0,0,"tp wrong side"); return; }

   double lots=GM_CalcLots(risk, RiskPct(), MaxLotMult());
   if(lots<=0.0) { g_log.Log("GM20","SKIP_SIZE",dir,entry,sl,tp,0,rr,0,"min lot risk too high"); return; }

   if(g_trade.Open(dir, lots, sl, tp, InpMode==0?"GM20_Fade":"GM20_GapGo"))
     { g_tradesToday++; g_log.Log("GM20","ENTRY",dir,entry,sl,tp,lots,rr,1, InpMode==0?"gap fade":"gap go"); }
  }
//+------------------------------------------------------------------+
