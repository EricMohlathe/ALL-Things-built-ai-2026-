//+------------------------------------------------------------------+
//|                                    GM26_ConfluenceStack.mq5      |
//|                      GODMODE Master EA Library  -  Archetype 26   |
//|  THE META-EDGE: fire only when N independent layers agree         |
//|  (trend + FVG + zone + swing sweep + session + momentum).         |
//|  A hard floor of 4-5 layers is where the legitimately higher      |
//|  win-rate band lives - single setups do not get you there.        |
//+------------------------------------------------------------------+
#property copyright "GODMODE Master Library"
#property version   "1.00"
#property strict

#include <GODMODE/GODMODE_Core.mqh>

input group "=== Identity ==="
input long   InpMagic            = 9026;

input group "=== Risk Mode ==="
input GM_RiskMode InpRiskMode    = RISK_CONSERVATIVE;
input double InpRiskConservative = 1.0;
input double InpRiskAggressive   = 3.0;
input double InpRiskFlip          = 8.0;
input double InpMaxLotRiskMult   = 3.0;

input group "=== Session (broker time) ==="
input int    InpTradeStartHour   = 7;
input int    InpTradeEndHour     = 16;
input int    InpForceCloseHour   = 22;

input group "=== Confluence ==="
input int    InpMinLayers        = 4;
input bool   InpUseTrend         = true;
input bool   InpUseFVG           = true;
input bool   InpUseZone          = true;
input bool   InpUseSweep         = true;
input bool   InpUseSessionLayer  = true;
input bool   InpUseMomentum      = true;

input group "=== Params ==="
input int    InpEMAPeriod        = 50;
input int    InpFVGLookback      = 15;
input int    InpZoneLookback     = 30;
input int    InpSwingLookback    = 30;
input int    InpSwingWing        = 2;
input double InpDispMult         = 1.0;
input double InpBaseMaxMult      = 0.6;
input double InpSLAtrMult        = 1.5;
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
int       g_emaHandle = INVALID_HANDLE;
datetime  g_lastBar   = 0;
int       g_tradesToday = 0;

int OnInit()
  {
   g_trade.Init(InpMagic);
   g_guards.Init(InpMagic);
   g_log.Init("GODMODE_GM26_ConfluenceStack_log.csv");
   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   g_emaHandle = iMA(_Symbol, PERIOD_CURRENT, InpEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   Print("GM26 Confluence Stack initialised. MinLayers=", InpMinLayers, " RiskMode=", EnumToString(InpRiskMode));
   return INIT_SUCCEEDED;
  }
void OnDeinit(const int reason) { }

double ATRValue() { double b[]; if(g_atrHandle==INVALID_HANDLE||CopyBuffer(g_atrHandle,0,1,1,b)<=0) return 0.0; return b[0]; }
double EMAValue() { double b[]; if(g_emaHandle==INVALID_HANDLE||CopyBuffer(g_emaHandle,0,1,1,b)<=0) return 0.0; return b[0]; }
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
     { g_trade.CloseAll(); g_guards.Halt(); g_log.Log("GM26","KILL_DD",GM_NONE,0,0,0,0,0,0,"daily DD"); return; }
   if(InpMaxConsecLosses>0 && g_guards.TrailingLossStreak()>=InpMaxConsecLosses) { g_guards.Halt(); return; }
   if(st.hour >= InpForceCloseHour) { g_trade.CloseAll(); return; }
   if(g_trade.HasPosition() || g_tradesToday>=InpMaxTradesPerDay) return;
   if(!g_guards.SpreadOK(InpMaxSpreadPoints)) return;

   double atr=ATRValue(); if(atr<=0) return;
   double o1=iOpen(_Symbol,PERIOD_CURRENT,1), c1=iClose(_Symbol,PERIOD_CURRENT,1);
   double hi1=iHigh(_Symbol,PERIOD_CURRENT,1), lo1=iLow(_Symbol,PERIOD_CURRENT,1);
   double ema=EMAValue();
   bool inSess = GM_InWindow(st.hour*60+st.min, InpTradeStartHour*60, InpTradeEndHour*60);

   double ft=0, fb=0, zt=0, zb=0, swLo=0, swHi=0; int sLs=0, sHs=0;
   bool bullFvg = GM_FindBullishFVG(InpFVGLookback, ft, fb) && lo1<=ft && c1>=fb;
   bool bearFvg = GM_FindBearishFVG(InpFVGLookback, ft, fb) && hi1>=fb && c1<=ft;
   bool bullZone = (GM_FindDemandBase(InpZoneLookback,atr,InpDispMult,InpBaseMaxMult,zt,zb) && lo1<=zt && c1>=zb)
                || (GM_FindBullishOB(InpZoneLookback,atr,InpDispMult,zt,zb) && lo1<=zt && c1>=zb);
   bool bearZone = (GM_FindSupplyBase(InpZoneLookback,atr,InpDispMult,InpBaseMaxMult,zt,zb) && hi1>=zb && c1<=zt)
                || (GM_FindBearishOB(InpZoneLookback,atr,InpDispMult,zt,zb) && hi1>=zb && c1<=zt);
   bool haveLo = GM_LastSwingLow(InpSwingLookback, InpSwingWing, swLo, sLs);
   bool haveHi = GM_LastSwingHigh(InpSwingLookback, InpSwingWing, swHi, sHs);
   bool bullSweep = haveLo && lo1<swLo && c1>swLo;
   bool bearSweep = haveHi && hi1>swHi && c1<swHi;
   bool bullMom = (c1-o1) > InpDispMult*atr || GM_IsBullEngulf();
   bool bearMom = (o1-c1) > InpDispMult*atr || GM_IsBearEngulf();

   int longN=0, shortN=0;
   if(InpUseTrend)    { if(c1>ema) longN++; if(c1<ema) shortN++; }
   if(InpUseFVG)      { if(bullFvg) longN++; if(bearFvg) shortN++; }
   if(InpUseZone)     { if(bullZone) longN++; if(bearZone) shortN++; }
   if(InpUseSweep)    { if(bullSweep) longN++; if(bearSweep) shortN++; }
   if(InpUseSessionLayer && inSess) { longN++; shortN++; }
   if(InpUseMomentum) { if(bullMom) longN++; if(bearMom) shortN++; }

   GM_Dir dir=GM_NONE;
   if(longN>=InpMinLayers && longN>shortN)      dir=GM_LONG;
   else if(shortN>=InpMinLayers && shortN>longN) dir=GM_SHORT;
   if(dir==GM_NONE) return;

   double pad=InpSLPaddingPoints*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double sl = (dir==GM_LONG) ? (haveLo ? swLo-pad : c1-InpSLAtrMult*atr)
                              : (haveHi ? swHi+pad : c1+InpSLAtrMult*atr);

   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK), bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double entry=(dir==GM_LONG)?ask:bid;
   double risk=MathAbs(entry-sl); if(risk<=0) return;
   double tp=(dir==GM_LONG)?entry+risk*InpRR:entry-risk*InpRR;
   int score=(dir==GM_LONG)?longN:shortN;

   double lots=GM_CalcLots(risk, RiskPct(), MaxLotMult());
   if(lots<=0.0) { g_log.Log("GM26","SKIP_SIZE",dir,entry,sl,tp,0,InpRR,score,"min lot risk too high"); return; }

   if(g_trade.Open(dir, lots, sl, tp, "GM26_Stack"))
     { g_tradesToday++; g_log.Log("GM26","ENTRY",dir,entry,sl,tp,lots,InpRR,score,"confluence layers"); }
  }
//+------------------------------------------------------------------+
