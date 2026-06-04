//+------------------------------------------------------------------+
//|                              GM01_OpeningRangeBreakout.mq5        |
//|                      GODMODE Master EA Library  -  Archetype 01   |
//|                                                                  |
//|  Opening Range Breakout (ORB).                                    |
//|  Distilled from: Casper SMC ORB, Ginger ORB, JDUB ORB, Multi-ORB, |
//|  30/15 ORB, RP Profits NY-Open Break & Retest, and the many       |
//|  "NY 09:30 breakout" educators (Trade With PAT, TomTrades, etc).  |
//|                                                                  |
//|  Logic: build a range over the first N minutes of a chosen        |
//|  session; trade the first confirmed breakout; SL = opposite       |
//|  range edge (or breakout candle); TP = fixed R multiple. Optional |
//|  retracement-limit entry and one-trade-per-day discipline.        |
//+------------------------------------------------------------------+
#property copyright "GODMODE Master Library"
#property version   "1.00"
#property strict

#include <GODMODE/GODMODE_Core.mqh>

//------------------------------------------------------------------ inputs
input group "=== Identity ==="
input long   InpMagic            = 9001;        // Magic number (unique per EA)

input group "=== Risk Mode ==="
input GM_RiskMode InpRiskMode    = RISK_CONSERVATIVE; // Conservative / Aggressive / Flip
input double InpRiskConservative = 1.0;         // Risk % (Conservative)
input double InpRiskAggressive   = 3.0;         // Risk % (Aggressive)
input double InpRiskFlip         = 8.0;         // Risk % (Flip - HIGH blow-up odds)
input double InpMaxLotRiskMult   = 3.0;         // Reject if min-lot risk > this x target

input group "=== Opening Range (broker server time) ==="
input int    InpORStartHour      = 15;          // OR start hour (broker time)
input int    InpORStartMinute    = 30;          // OR start minute
input int    InpORDurationMin    = 15;          // OR length (minutes)
input int    InpTradeEndHour     = 21;          // Stop new trades after this hour
input int    InpForceCloseHour   = 22;          // Force-close all after this hour

input group "=== Entry / Exit ==="
input bool   InpReverse          = false;       // Reverse (fade the breakout)
input bool   InpUseRetracement   = false;       // Limit entry on retrace into range
input double InpRetracePct       = 50.0;        // Retrace % of breakout candle
input int    InpSLType           = 0;           // 0=Opposite range,1=Breakout candle,2=ATR
input double InpATRMultSL         = 2.0;        // ATR mult (if SLType=ATR)
input int    InpATRPeriod        = 14;          // ATR period
input double InpRR               = 2.0;         // Reward:Risk for TP
input int    InpSLPaddingPoints  = 5;           // Padding (points) on the stop

input group "=== Trade Management ==="
input double InpBEatR            = 1.0;         // Move to break-even at R (0=off)
input double InpPartialAtR       = 1.0;         // Partial close at R (0=off)
input double InpPartialPct       = 50.0;        // Partial close %
input bool   InpUseTrail         = false;       // ATR trailing stop
input double InpTrailATRMult     = 1.5;         // Trail ATR multiple

input group "=== Guards ==="
input double InpMaxDailyDDPct    = 6.0;         // Halt for the day at this daily DD %
input int    InpMaxConsecLosses  = 3;           // Halt for the day after N losses
input double InpMaxSpreadPoints  = 0;           // Max spread (points, 0=off)

//------------------------------------------------------------------ globals
CGMTrade   g_trade;
CGMGuards  g_guards;
CGMLogger  g_log;
int        g_atrHandle = INVALID_HANDLE;
datetime   g_lastBar   = 0;

double     g_orHigh = 0.0, g_orLow = 0.0;
bool       g_orReady = false;
bool       g_tradedToday = false;
int        g_orDay = -1;

//+------------------------------------------------------------------+
int OnInit()
  {
   g_trade.Init(InpMagic);
   g_guards.Init(InpMagic);
   g_log.Init("GODMODE_GM01_ORB_log.csv");
   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   if(g_atrHandle == INVALID_HANDLE)
      Print("GM01: ATR handle failed");
   Print("GM01 Opening Range Breakout initialised. RiskMode=", EnumToString(InpRiskMode));
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason) { }

//+------------------------------------------------------------------+
double ATRValue()
  {
   if(g_atrHandle == INVALID_HANDLE) return 0.0;
   double b[];
   if(CopyBuffer(g_atrHandle, 0, 1, 1, b) <= 0) return 0.0;
   return b[0];
  }

double RiskPct() { return GM_ResolveRiskPct(InpRiskMode, InpRiskConservative, InpRiskAggressive, InpRiskFlip); }
double MaxLotMult() { return (InpRiskMode == RISK_FLIP) ? 1000.0 : InpMaxLotRiskMult; }

//+------------------------------------------------------------------+
void OnTick()
  {
   // Manage open position every tick (trailing reacts intrabar)
   g_trade.Manage(InpBEatR, InpPartialAtR, InpPartialPct, InpUseTrail, InpTrailATRMult, ATRValue());

   if(!GM_IsNewBar(PERIOD_CURRENT, g_lastBar))
      return;

   datetime now = TimeCurrent();
   MqlDateTime st; TimeToStruct(now, st);
   int mod = st.hour * 60 + st.min;                 // minute of day, broker time
   int orStart = InpORStartHour * 60 + InpORStartMinute;
   int orEnd   = orStart + InpORDurationMin;

   // --- daily rollover ---
   if(g_guards.IsNewDay())
     {
      g_guards.OnNewDay();
      g_orHigh = 0.0; g_orLow = 0.0; g_orReady = false; g_tradedToday = false;
     }

   // --- daily guards ---
   if(g_guards.IsHalted()) return;
   if(g_guards.DailyDDBreached(InpMaxDailyDDPct))
     { g_trade.CloseAll(); g_guards.Halt(); g_log.Log("GM01","KILL_DD",GM_NONE,0,0,0,0,0,0,"daily DD"); return; }
   if(InpMaxConsecLosses > 0 && g_guards.TrailingLossStreak() >= InpMaxConsecLosses)
     { g_guards.Halt(); g_log.Log("GM01","KILL_CONSEC",GM_NONE,0,0,0,0,0,"consec losses"); return; }

   // --- force close at end of session ---
   if(st.hour >= InpForceCloseHour)
     { g_trade.CloseAll(); return; }

   // --- build the opening range (use the just-closed bar = shift 1) ---
   double prevHigh = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double prevLow  = iLow (_Symbol, PERIOD_CURRENT, 1);
   bool inFormation = GM_InWindow(mod, orStart, orEnd);
   if(inFormation)
     {
      if(g_orHigh == 0.0 || prevHigh > g_orHigh) g_orHigh = prevHigh;
      if(g_orLow  == 0.0 || prevLow  < g_orLow ) g_orLow  = prevLow;
     }
   else if(g_orHigh > 0.0 && g_orLow > 0.0 && !g_orReady && mod >= orEnd)
     {
      g_orReady = true;
      DrawRangeLines();
     }

   if(!g_orReady || g_tradedToday) return;
   if(g_trade.HasPosition()) return;
   if(st.hour >= InpTradeEndHour) return;
   if(!g_guards.SpreadOK(InpMaxSpreadPoints))
     { g_log.Log("GM01","SKIP_SPREAD",GM_NONE,0,0,0,0,0,"spread"); return; }

   double close = iClose(_Symbol, PERIOD_CURRENT, 1);
   double pad   = InpSLPaddingPoints * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   GM_Dir dir   = GM_NONE;

   bool brokeUp   = close > g_orHigh;
   bool brokeDown = close < g_orLow;

   if(brokeUp)   dir = InpReverse ? GM_SHORT : GM_LONG;
   if(brokeDown) dir = InpReverse ? GM_LONG  : GM_SHORT;
   if(dir == GM_NONE) return;

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = (dir == GM_LONG) ? ask : bid;
   double sl = 0.0;

   double atr = ATRValue();
   if(InpSLType == 2 && atr > 0.0)
      sl = (dir == GM_LONG) ? entry - atr * InpATRMultSL : entry + atr * InpATRMultSL;
   else if(InpSLType == 1)
      sl = (dir == GM_LONG) ? iLow(_Symbol, PERIOD_CURRENT, 1) - pad
                            : iHigh(_Symbol, PERIOD_CURRENT, 1) + pad;
   else // opposite range
      sl = (dir == GM_LONG) ? g_orLow - pad : g_orHigh + pad;

   double risk = MathAbs(entry - sl);
   if(risk <= 0.0) return;
   double tp = (dir == GM_LONG) ? entry + risk * InpRR : entry - risk * InpRR;

   double lots = GM_CalcLots(risk, RiskPct(), MaxLotMult());
   if(lots <= 0.0)
     { g_log.Log("GM01","SKIP_SIZE",dir,entry,sl,tp,0,InpRR,0,"min lot risk too high"); return; }

   if(g_trade.Open(dir, lots, sl, tp, "GM01_ORB"))
     {
      g_tradedToday = true;
      g_log.Log("GM01","ENTRY",dir,entry,sl,tp,lots,InpRR,1,"ORB breakout");
     }
  }

//+------------------------------------------------------------------+
void DrawRangeLines()
  {
   string a = "GM01_ORH", b = "GM01_ORL";
   ObjectDelete(0, a); ObjectDelete(0, b);
   ObjectCreate(0, a, OBJ_HLINE, 0, 0, g_orHigh);
   ObjectSetInteger(0, a, OBJPROP_COLOR, clrLime);
   ObjectCreate(0, b, OBJ_HLINE, 0, 0, g_orLow);
   ObjectSetInteger(0, b, OBJPROP_COLOR, clrRed);
  }
//+------------------------------------------------------------------+
