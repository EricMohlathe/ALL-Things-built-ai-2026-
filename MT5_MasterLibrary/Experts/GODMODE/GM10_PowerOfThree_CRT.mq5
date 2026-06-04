//+------------------------------------------------------------------+
//|                              GM10_PowerOfThree_CRT.mq5            |
//|                      GODMODE Master EA Library  -  Archetype 10   |
//|                                                                  |
//|  Power of Three (Accumulation - Manipulation - Distribution) /    |
//|  Candle Range Theory, with CISD (Change in State of Delivery)     |
//|  confirmation. Distilled from: Trade With PAT PO3, Roboquant CRT, |
//|  KISS (CISD), 9am CR model, ICT PO3 guide.                        |
//|                                                                  |
//|  Logic:                                                           |
//|   * ACCUMULATION: build a reference range over a pre-session.     |
//|   * MANIPULATION: price sweeps one edge of the range (stop hunt). |
//|   * CISD: mark the last counter-candle of the manip leg; wait for |
//|     a close back THROUGH it (state change).                       |
//|   * DISTRIBUTION: enter the reversal toward the opposite edge;    |
//|     optional standard-deviation (measured-move) extension target. |
//+------------------------------------------------------------------+
#property copyright "GODMODE Master Library"
#property version   "1.00"
#property strict

#include <GODMODE/GODMODE_Core.mqh>

input group "=== Identity ==="
input long   InpMagic            = 9010;

input group "=== Risk Mode ==="
input GM_RiskMode InpRiskMode    = RISK_CONSERVATIVE;
input double InpRiskConservative = 1.0;
input double InpRiskAggressive   = 3.0;
input double InpRiskFlip         = 8.0;
input double InpMaxLotRiskMult   = 3.0;

input group "=== Sessions (broker server time) ==="
input int    InpRangeStartHour   = 0;           // Accumulation range start
input int    InpRangeEndHour     = 6;           // Accumulation range end
input int    InpTradeStartHour   = 6;           // Manipulation/distribution window start
input int    InpTradeEndHour     = 12;          // Stop new trades after
input int    InpForceCloseHour   = 13;          // Force close all after

input group "=== Entry / Exit ==="
input bool   InpRequireCISD      = true;        // require close through CISD level
input int    InpSLPaddingPoints  = 10;
input int    InpTPType           = 0;           // 0=Opposite edge, 1=SD extension, 2=Fixed RR
input double InpSDMult           = 1.0;         // SD/measured-move multiple (TPType=1)
input double InpRR               = 2.5;         // (TPType=2)
input double InpMinRR            = 1.5;
input int    InpATRPeriod        = 14;

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

double    g_rHigh = 0.0, g_rLow = 0.0;
bool      g_rangeReady = false, g_tradedToday = false;
int       g_phase = 0;          // 0 none, 1 swept-high (short setup), -1 swept-low (long setup)
double    g_cisd = 0.0, g_manipExtreme = 0.0;

int OnInit()
  {
   g_trade.Init(InpMagic);
   g_guards.Init(InpMagic);
   g_log.Init("GODMODE_GM10_PO3_CRT_log.csv");
   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   Print("GM10 Power-of-3 / CRT initialised. RiskMode=", EnumToString(InpRiskMode));
   return INIT_SUCCEEDED;
  }
void OnDeinit(const int reason) { }

double ATRValue() { double b[]; if(g_atrHandle==INVALID_HANDLE||CopyBuffer(g_atrHandle,0,1,1,b)<=0) return 0.0; return b[0]; }
double RiskPct()  { return GM_ResolveRiskPct(InpRiskMode, InpRiskConservative, InpRiskAggressive, InpRiskFlip); }
double MaxLotMult(){ return (InpRiskMode == RISK_FLIP) ? 1000.0 : InpMaxLotRiskMult; }

void ResetDay()
  {
   g_rHigh=0; g_rLow=0; g_rangeReady=false; g_tradedToday=false;
   g_phase=0; g_cisd=0; g_manipExtreme=0;
  }

void OnTick()
  {
   g_trade.Manage(InpBEatR, InpPartialAtR, InpPartialPct, InpUseTrail, InpTrailATRMult, ATRValue());
   if(!GM_IsNewBar(PERIOD_CURRENT, g_lastBar)) return;

   MqlDateTime st; TimeToStruct(TimeCurrent(), st);
   int mod = st.hour*60 + st.min;

   if(g_guards.IsNewDay()) { g_guards.OnNewDay(); ResetDay(); }
   if(g_guards.IsHalted()) return;
   if(g_guards.DailyDDBreached(InpMaxDailyDDPct))
     { g_trade.CloseAll(); g_guards.Halt(); g_log.Log("GM10","KILL_DD",GM_NONE,0,0,0,0,0,0,"daily DD"); return; }
   if(InpMaxConsecLosses>0 && g_guards.TrailingLossStreak()>=InpMaxConsecLosses) { g_guards.Halt(); return; }
   if(st.hour >= InpForceCloseHour) { g_trade.CloseAll(); return; }

   // --- accumulation: build range ---
   double prevHigh = iHigh(_Symbol,PERIOD_CURRENT,1), prevLow = iLow(_Symbol,PERIOD_CURRENT,1);
   bool inRange = GM_InWindow(mod, InpRangeStartHour*60, InpRangeEndHour*60);
   if(inRange)
     {
      if(g_rHigh==0.0 || prevHigh>g_rHigh) g_rHigh=prevHigh;
      if(g_rLow ==0.0 || prevLow <g_rLow ) g_rLow =prevLow;
     }
   else if(g_rHigh>0.0 && g_rLow>0.0 && !g_rangeReady && mod>=InpRangeEndHour*60)
     {
      g_rangeReady=true;
      ObjectDelete(0,"GM10_RH"); ObjectDelete(0,"GM10_RL");
      ObjectCreate(0,"GM10_RH",OBJ_HLINE,0,0,g_rHigh); ObjectSetInteger(0,"GM10_RH",OBJPROP_COLOR,clrGold);
      ObjectCreate(0,"GM10_RL",OBJ_HLINE,0,0,g_rLow ); ObjectSetInteger(0,"GM10_RL",OBJPROP_COLOR,clrGold);
     }

   if(!g_rangeReady || g_tradedToday) return;
   if(!GM_InWindow(mod, InpTradeStartHour*60, InpTradeEndHour*60)) return;
   if(g_trade.HasPosition()) return;

   double barHigh=iHigh(_Symbol,PERIOD_CURRENT,1), barLow=iLow(_Symbol,PERIOD_CURRENT,1), close=iClose(_Symbol,PERIOD_CURRENT,1);

   // --- manipulation: first sweep ---
   if(g_phase==0)
     {
      if(barHigh>g_rHigh) { g_phase=1;  g_manipExtreme=barHigh; g_cisd=barLow; }
      else if(barLow<g_rLow) { g_phase=-1; g_manipExtreme=barLow; g_cisd=barHigh; }
      return;
     }
   // track the manip leg + CISD (last counter-candle level)
   if(g_phase==1 && barHigh>g_manipExtreme) { g_manipExtreme=barHigh; g_cisd=barLow; }
   if(g_phase==-1 && barLow<g_manipExtreme) { g_manipExtreme=barLow; g_cisd=barHigh; }

   // --- distribution: CISD close-through ---
   GM_Dir dir=GM_NONE;
   if(g_phase==1)  { bool ok = !InpRequireCISD || close<g_cisd; if(ok) dir=GM_SHORT; }
   if(g_phase==-1) { bool ok = !InpRequireCISD || close>g_cisd; if(ok) dir=GM_LONG; }
   if(dir==GM_NONE) return;
   if(!g_guards.SpreadOK(InpMaxSpreadPoints)) { g_log.Log("GM10","SKIP_SPREAD",dir,0,0,0,0,0,"spread"); return; }

   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK), bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double entry=(dir==GM_LONG)?ask:bid;
   double pad=InpSLPaddingPoints*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double sl=(dir==GM_LONG)?g_manipExtreme-pad:g_manipExtreme+pad;
   double risk=MathAbs(entry-sl); if(risk<=0) return;

   double rangeSize=g_rHigh-g_rLow;
   double tp;
   if(InpTPType==2)      tp=(dir==GM_LONG)?entry+risk*InpRR:entry-risk*InpRR;
   else if(InpTPType==1) tp=(dir==GM_LONG)?GM_SDExtension(g_rHigh,rangeSize,1,InpSDMult)
                                          :GM_SDExtension(g_rLow ,rangeSize,-1,InpSDMult);
   else                  tp=(dir==GM_LONG)?g_rHigh:g_rLow;     // opposite edge

   double rr=MathAbs(tp-entry)/risk;
   if(rr<InpMinRR) { g_log.Log("GM10","SKIP_RR",dir,entry,sl,tp,0,rr,0,"below MinRR"); return; }

   double lots=GM_CalcLots(risk, RiskPct(), MaxLotMult());
   if(lots<=0.0) { g_log.Log("GM10","SKIP_SIZE",dir,entry,sl,tp,0,rr,0,"min lot risk too high"); return; }

   if(g_trade.Open(dir, lots, sl, tp, "GM10_PO3"))
     { g_tradedToday=true; g_log.Log("GM10","ENTRY",dir,entry,sl,tp,lots,rr,2, g_phase==1?"manip high->short(CISD)":"manip low->long(CISD)"); }
  }
//+------------------------------------------------------------------+
