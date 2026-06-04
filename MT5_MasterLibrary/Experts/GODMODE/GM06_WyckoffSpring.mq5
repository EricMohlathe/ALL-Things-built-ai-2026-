//+------------------------------------------------------------------+
//|                                    GM06_WyckoffSpring.mq5         |
//|                      GODMODE Master EA Library  -  Archetype 06   |
//|                                                                  |
//|  Wyckoff Spring / Upthrust at a trading-range boundary.           |
//|  Distilled from: Wyckoff 2.0 (Villahermosa), GODMODE setups       |
//|  14 (Spring) / 15 (Upthrust), reversal-at-range educators.        |
//|                                                                  |
//|  Logic: define a consolidation range over a lookback (excluding   |
//|  the live bars). A SPRING = price dips below range low then       |
//|  closes back inside -> long. An UPTHRUST = price pokes above      |
//|  range high then closes back inside -> short. SL beyond the       |
//|  spring/upthrust extreme; TP = opposite range edge or R multiple. |
//+------------------------------------------------------------------+
#property copyright "GODMODE Master Library"
#property version   "1.00"
#property strict

#include <GODMODE/GODMODE_Core.mqh>

input group "=== Identity ==="
input long   InpMagic            = 9006;

input group "=== Risk Mode ==="
input GM_RiskMode InpRiskMode    = RISK_CONSERVATIVE;
input double InpRiskConservative = 1.0;
input double InpRiskAggressive   = 3.0;
input double InpRiskFlip         = 8.0;
input double InpMaxLotRiskMult   = 3.0;

input group "=== Session (broker time) ==="
input bool   InpUseSession       = true;
input int    InpTradeStartHour   = 6;
input int    InpTradeEndHour     = 20;
input int    InpForceCloseHour   = 22;

input group "=== Range / Spring ==="
input int    InpRangeLen         = 20;          // bars defining the trading range
input int    InpRangeStartShift  = 2;           // skip the most recent bars (the spring lives here)
input double InpMaxRangeATR      = 4.0;         // reject if range wider than this x ATR (must be a range, not a trend)
input int    InpATRPeriod        = 14;
input int    InpSLPaddingPoints  = 10;
input int    InpTPType           = 0;           // 0=Opposite range edge, 1=Fixed RR
input double InpRR               = 2.5;
input double InpMinRR            = 1.5;
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
   g_log.Init("GODMODE_GM06_Wyckoff_log.csv");
   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   Print("GM06 Wyckoff Spring/Upthrust initialised. RiskMode=", EnumToString(InpRiskMode));
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
   if(g_guards.IsNewDay()) { g_guards.OnNewDay(); g_tradesToday = 0; }
   if(g_guards.IsHalted()) return;
   if(g_guards.DailyDDBreached(InpMaxDailyDDPct))
     { g_trade.CloseAll(); g_guards.Halt(); g_log.Log("GM06","KILL_DD",GM_NONE,0,0,0,0,0,0,"daily DD"); return; }
   if(InpMaxConsecLosses > 0 && g_guards.TrailingLossStreak() >= InpMaxConsecLosses) { g_guards.Halt(); return; }
   if(st.hour >= InpForceCloseHour) { g_trade.CloseAll(); return; }
   if(InpUseSession && !GM_InWindow(st.hour*60+st.min, InpTradeStartHour*60, InpTradeEndHour*60)) return;
   if(g_trade.HasPosition() || g_tradesToday >= InpMaxTradesPerDay) return;
   if(!g_guards.SpreadOK(InpMaxSpreadPoints)) return;

   double atr = ATRValue();
   if(atr <= 0.0) return;

   // Range defined by older bars (exclude the most recent InpRangeStartShift bars).
   double rangeHigh = GM_HighestHigh(InpRangeLen, InpRangeStartShift);
   double rangeLow  = GM_LowestLow (InpRangeLen, InpRangeStartShift);
   double rangeWidth = rangeHigh - rangeLow;
   if(rangeWidth <= 0.0) return;
   if(rangeWidth > InpMaxRangeATR * atr)        // not a consolidation -> skip
     { return; }

   double pad   = InpSLPaddingPoints * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double low1  = iLow  (_Symbol, PERIOD_CURRENT, 1);
   double high1 = iHigh (_Symbol, PERIOD_CURRENT, 1);
   double close1= iClose(_Symbol, PERIOD_CURRENT, 1);

   GM_Dir dir = GM_NONE;
   double sl = 0.0;

   bool spring   = (low1  < rangeLow)  && (close1 > rangeLow);   // dip below, close back in
   bool upthrust = (high1 > rangeHigh) && (close1 < rangeHigh);  // poke above, close back in

   if(spring)        { dir = GM_LONG;  sl = low1  - pad; }
   else if(upthrust) { dir = GM_SHORT; sl = high1 + pad; }
   if(dir == GM_NONE) return;

   double entry = (dir == GM_LONG) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double risk = MathAbs(entry - sl);
   if(risk <= 0.0) return;

   double tp;
   if(InpTPType == 1) tp = (dir == GM_LONG) ? entry + risk * InpRR : entry - risk * InpRR;
   else               tp = (dir == GM_LONG) ? rangeHigh : rangeLow;

   double rr = MathAbs(tp - entry) / risk;
   if(rr < InpMinRR) { g_log.Log("GM06","SKIP_RR",dir,entry,sl,tp,0,rr,0,"below MinRR"); return; }

   double lots = GM_CalcLots(risk, RiskPct(), MaxLotMult());
   if(lots <= 0.0) { g_log.Log("GM06","SKIP_SIZE",dir,entry,sl,tp,0,rr,0,"min lot risk too high"); return; }

   if(g_trade.Open(dir, lots, sl, tp, "GM06_Wyckoff"))
     { g_tradesToday++; g_log.Log("GM06","ENTRY",dir,entry,sl,tp,lots,rr,1, spring ? "spring" : "upthrust"); }
  }
//+------------------------------------------------------------------+
