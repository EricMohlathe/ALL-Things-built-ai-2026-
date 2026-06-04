//+------------------------------------------------------------------+
//|                            GM02_SessionSweepReversal.mq5          |
//|                      GODMODE Master EA Library  -  Archetype 02   |
//|                                                                  |
//|  Session Liquidity Sweep -> Reclaim reversal                      |
//|  (ICT "Judas swing" / Power-of-3 / AMD, CRT Candle Range Theory,  |
//|   TJR Asia Sweep). Distilled from your attached scripts:          |
//|   TJR Asia Sweep, Roboquant CRT, 9am CR Model, Asia Sweep iFVG,   |
//|   5min Asia Gold.                                                 |
//|                                                                  |
//|  Logic: build a reference range over a "manipulation" session     |
//|  (e.g. Asian). In the trade session, wait for price to SWEEP one  |
//|  edge of that range (take liquidity) then CLOSE BACK INSIDE        |
//|  (reclaim). Enter the reversal toward the opposite edge.          |
//|  SL beyond the swept extreme; TP = opposite range edge or R mult. |
//+------------------------------------------------------------------+
#property copyright "GODMODE Master Library"
#property version   "1.00"
#property strict

#include <GODMODE/GODMODE_Core.mqh>

//------------------------------------------------------------------ inputs
input group "=== Identity ==="
input long   InpMagic            = 9002;

input group "=== Risk Mode ==="
input GM_RiskMode InpRiskMode    = RISK_CONSERVATIVE;
input double InpRiskConservative = 1.0;
input double InpRiskAggressive   = 3.0;
input double InpRiskFlip         = 8.0;
input double InpMaxLotRiskMult   = 3.0;

input group "=== Sessions (broker server time, minutes handled internally) ==="
input int    InpRangeStartHour   = 0;           // Manipulation range start hour
input int    InpRangeEndHour     = 6;           // Manipulation range end hour
input int    InpTradeStartHour   = 6;           // Trade (sweep-hunting) session start
input int    InpTradeEndHour     = 11;          // Stop new trades after this hour
input int    InpForceCloseHour   = 12;          // Force close all after this hour

input group "=== Entry / Exit ==="
input bool   InpRequireReclaim   = true;        // Require close back inside range (deviation)
input int    InpSLType           = 0;           // 0=Swept extreme,1=ATR
input double InpATRMultSL         = 1.5;        // ATR mult (if SLType=ATR)
input int    InpATRPeriod        = 14;
input int    InpSLPaddingPoints  = 10;          // Padding beyond the swept extreme
input int    InpTPType           = 0;           // 0=Opposite range edge,1=Fixed RR
input double InpRR               = 2.5;         // R:R (if TPType=Fixed RR)
input double InpMinRR            = 1.5;          // Reject setups below this R:R

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

//------------------------------------------------------------------ globals
CGMTrade  g_trade;
CGMGuards g_guards;
CGMLogger g_log;
int       g_atrHandle = INVALID_HANDLE;
datetime  g_lastBar   = 0;

double    g_rHigh = 0.0, g_rLow = 0.0;
bool      g_rangeReady = false;
bool      g_sweptHigh = false, g_sweptLow = false;
double    g_sweepExtreme = 0.0;
bool      g_tradedToday = false;

//+------------------------------------------------------------------+
int OnInit()
  {
   g_trade.Init(InpMagic);
   g_guards.Init(InpMagic);
   g_log.Init("GODMODE_GM02_SweepReversal_log.csv");
   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   Print("GM02 Session Sweep Reversal initialised. RiskMode=", EnumToString(InpRiskMode));
   return INIT_SUCCEEDED;
  }
void OnDeinit(const int reason) { }

double ATRValue()
  {
   if(g_atrHandle == INVALID_HANDLE) return 0.0;
   double b[];
   if(CopyBuffer(g_atrHandle, 0, 1, 1, b) <= 0) return 0.0;
   return b[0];
  }
double RiskPct()  { return GM_ResolveRiskPct(InpRiskMode, InpRiskConservative, InpRiskAggressive, InpRiskFlip); }
double MaxLotMult(){ return (InpRiskMode == RISK_FLIP) ? 1000.0 : InpMaxLotRiskMult; }

//+------------------------------------------------------------------+
void OnTick()
  {
   g_trade.Manage(InpBEatR, InpPartialAtR, InpPartialPct, InpUseTrail, InpTrailATRMult, ATRValue());

   if(!GM_IsNewBar(PERIOD_CURRENT, g_lastBar))
      return;

   MqlDateTime st; TimeToStruct(TimeCurrent(), st);
   int mod      = st.hour * 60 + st.min;
   int rStart   = InpRangeStartHour * 60;
   int rEnd     = InpRangeEndHour   * 60;

   if(g_guards.IsNewDay())
     {
      g_guards.OnNewDay();
      g_rHigh = 0.0; g_rLow = 0.0; g_rangeReady = false;
      g_sweptHigh = false; g_sweptLow = false; g_sweepExtreme = 0.0; g_tradedToday = false;
     }

   if(g_guards.IsHalted()) return;
   if(g_guards.DailyDDBreached(InpMaxDailyDDPct))
     { g_trade.CloseAll(); g_guards.Halt(); g_log.Log("GM02","KILL_DD",GM_NONE,0,0,0,0,0,0,"daily DD"); return; }
   if(InpMaxConsecLosses > 0 && g_guards.TrailingLossStreak() >= InpMaxConsecLosses)
     { g_guards.Halt(); g_log.Log("GM02","KILL_CONSEC",GM_NONE,0,0,0,0,0,"consec losses"); return; }

   if(st.hour >= InpForceCloseHour)
     { g_trade.CloseAll(); return; }

   // --- build manipulation range ---
   double prevHigh = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double prevLow  = iLow (_Symbol, PERIOD_CURRENT, 1);
   bool inRange = GM_InWindow(mod, rStart, rEnd);
   if(inRange)
     {
      if(g_rHigh == 0.0 || prevHigh > g_rHigh) g_rHigh = prevHigh;
      if(g_rLow  == 0.0 || prevLow  < g_rLow ) g_rLow  = prevLow;
     }
   else if(g_rHigh > 0.0 && g_rLow > 0.0 && !g_rangeReady && mod >= rEnd)
     {
      g_rangeReady = true;
      DrawRangeLines();
     }

   if(!g_rangeReady || g_tradedToday) return;

   bool inTradeWindow = GM_InWindow(mod, InpTradeStartHour * 60, InpTradeEndHour * 60);
   if(!inTradeWindow) return;
   if(g_trade.HasPosition()) return;

   double barHigh = iHigh (_Symbol, PERIOD_CURRENT, 1);
   double barLow  = iLow  (_Symbol, PERIOD_CURRENT, 1);
   double close   = iClose(_Symbol, PERIOD_CURRENT, 1);

   // --- detect sweep (first sweep of the session wins) ---
   if(!g_sweptHigh && !g_sweptLow)
     {
      if(barHigh > g_rHigh) { g_sweptHigh = true; g_sweepExtreme = barHigh; }
      else if(barLow < g_rLow) { g_sweptLow = true; g_sweepExtreme = barLow; }
      // track deeper sweep extreme until reclaim
     }
   else if(g_sweptHigh && barHigh > g_sweepExtreme) g_sweepExtreme = barHigh;
   else if(g_sweptLow  && barLow  < g_sweepExtreme) g_sweepExtreme = barLow;

   if(!g_sweptHigh && !g_sweptLow) return;

   // --- reclaim / reversal trigger ---
   GM_Dir dir = GM_NONE;
   if(g_sweptHigh)
     {
      bool reclaim = !InpRequireReclaim || close < g_rHigh;   // closed back inside
      if(reclaim) dir = GM_SHORT;
     }
   else if(g_sweptLow)
     {
      bool reclaim = !InpRequireReclaim || close > g_rLow;
      if(reclaim) dir = GM_LONG;
     }
   if(dir == GM_NONE) return;

   if(!g_guards.SpreadOK(InpMaxSpreadPoints))
     { g_log.Log("GM02","SKIP_SPREAD",dir,0,0,0,0,0,"spread"); return; }

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = (dir == GM_LONG) ? ask : bid;
   double pad = InpSLPaddingPoints * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double atr = ATRValue();

   double sl;
   if(InpSLType == 1 && atr > 0.0)
      sl = (dir == GM_LONG) ? entry - atr * InpATRMultSL : entry + atr * InpATRMultSL;
   else
      sl = (dir == GM_LONG) ? g_sweepExtreme - pad : g_sweepExtreme + pad;

   double risk = MathAbs(entry - sl);
   if(risk <= 0.0) return;

   double tp;
   if(InpTPType == 1)
      tp = (dir == GM_LONG) ? entry + risk * InpRR : entry - risk * InpRR;
   else
      tp = (dir == GM_LONG) ? g_rHigh : g_rLow;     // opposite edge of the range

   double rr = MathAbs(tp - entry) / risk;
   if(rr < InpMinRR)
     { g_log.Log("GM02","SKIP_RR",dir,entry,sl,tp,0,rr,0,"below MinRR"); return; }

   double lots = GM_CalcLots(risk, RiskPct(), MaxLotMult());
   if(lots <= 0.0)
     { g_log.Log("GM02","SKIP_SIZE",dir,entry,sl,tp,0,rr,0,"min lot risk too high"); return; }

   if(g_trade.Open(dir, lots, sl, tp, "GM02_SweepRev"))
     {
      g_tradedToday = true;
      g_log.Log("GM02","ENTRY",dir,entry,sl,tp,lots,rr,1,
                g_sweptHigh ? "high swept -> short" : "low swept -> long");
     }
  }

//+------------------------------------------------------------------+
void DrawRangeLines()
  {
   string a = "GM02_RH", b = "GM02_RL";
   ObjectDelete(0, a); ObjectDelete(0, b);
   ObjectCreate(0, a, OBJ_HLINE, 0, 0, g_rHigh);
   ObjectSetInteger(0, a, OBJPROP_COLOR, clrAqua);
   ObjectCreate(0, b, OBJ_HLINE, 0, 0, g_rLow);
   ObjectSetInteger(0, b, OBJPROP_COLOR, clrAqua);
  }
//+------------------------------------------------------------------+
