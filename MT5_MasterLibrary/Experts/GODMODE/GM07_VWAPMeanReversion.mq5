//+------------------------------------------------------------------+
//|                                 GM07_VWAPMeanReversion.mq5        |
//|                      GODMODE Master EA Library  -  Archetype 07   |
//|                                                                  |
//|  Session-anchored VWAP mean reversion (fade the extremes).        |
//|  Distilled from: Auction Market Theory (Fabio Valentini),         |
//|  SMB Capital VWAP reclaim, GODMODE setups 5/6/7 (VAL/VAH/POC).     |
//|                                                                  |
//|  Logic: build a daily-anchored VWAP with std-dev bands. When      |
//|  price closes BEYOND a band and the bar rejects (closes back      |
//|  toward VWAP), fade it back to VWAP. SL beyond the extreme;        |
//|  TP = VWAP (default) or fixed R multiple.                          |
//+------------------------------------------------------------------+
#property copyright "GODMODE Master Library"
#property version   "1.00"
#property strict

#include <GODMODE/GODMODE_Core.mqh>

input group "=== Identity ==="
input long   InpMagic            = 9007;

input group "=== Risk Mode ==="
input GM_RiskMode InpRiskMode    = RISK_CONSERVATIVE;
input double InpRiskConservative = 1.0;
input double InpRiskAggressive   = 3.0;
input double InpRiskFlip         = 8.0;
input double InpMaxLotRiskMult   = 3.0;

input group "=== Session (broker time) ==="
input bool   InpUseSession       = true;
input int    InpTradeStartHour   = 8;
input int    InpTradeEndHour     = 20;
input int    InpForceCloseHour   = 22;

input group "=== VWAP bands ==="
input double InpBandSD           = 2.0;         // bands at this many std-devs
input bool   InpRequireRejection = true;        // require a rejection close
input int    InpATRPeriod        = 14;
input double InpSLATRMult        = 1.0;         // extra ATR padding on the stop
input int    InpTPType           = 0;           // 0=VWAP, 1=Fixed RR
input double InpRR               = 1.5;
input double InpMinRR            = 1.0;
input int    InpMaxTradesPerDay  = 3;

input group "=== Trade Management ==="
input double InpBEatR            = 1.0;
input double InpPartialAtR       = 0.0;         // off by default (mean-rev = quick)
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

// VWAP accumulators (reset each day)
double    g_cumPV = 0.0, g_cumV = 0.0, g_cumPV2 = 0.0;
double    g_vwap = 0.0, g_sd = 0.0;

int OnInit()
  {
   g_trade.Init(InpMagic);
   g_guards.Init(InpMagic);
   g_log.Init("GODMODE_GM07_VWAP_log.csv");
   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   Print("GM07 VWAP Mean Reversion initialised. RiskMode=", EnumToString(InpRiskMode));
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
   if(g_guards.IsNewDay())
     {
      g_guards.OnNewDay(); g_tradesToday = 0;
      g_cumPV = 0.0; g_cumV = 0.0; g_cumPV2 = 0.0; g_vwap = 0.0; g_sd = 0.0;
     }

   // --- update VWAP with the just-closed bar ---
   double h = iHigh (_Symbol, PERIOD_CURRENT, 1);
   double l = iLow  (_Symbol, PERIOD_CURRENT, 1);
   double c = iClose(_Symbol, PERIOD_CURRENT, 1);
   double o = iOpen (_Symbol, PERIOD_CURRENT, 1);
   double typ = (h + l + c) / 3.0;
   double vol = (double)iTickVolume(_Symbol, PERIOD_CURRENT, 1);
   if(vol > 0.0)
     {
      g_cumPV  += typ * vol;
      g_cumV   += vol;
      g_cumPV2 += typ * typ * vol;
      if(g_cumV > 0.0)
        {
         g_vwap = g_cumPV / g_cumV;
         double var = (g_cumPV2 / g_cumV) - (g_vwap * g_vwap);
         if(var < 0.0) var = 0.0;
         g_sd = MathSqrt(var);
        }
     }

   if(g_guards.IsHalted()) return;
   if(g_guards.DailyDDBreached(InpMaxDailyDDPct))
     { g_trade.CloseAll(); g_guards.Halt(); g_log.Log("GM07","KILL_DD",GM_NONE,0,0,0,0,0,0,"daily DD"); return; }
   if(InpMaxConsecLosses > 0 && g_guards.TrailingLossStreak() >= InpMaxConsecLosses) { g_guards.Halt(); return; }
   if(st.hour >= InpForceCloseHour) { g_trade.CloseAll(); return; }
   if(InpUseSession && !GM_InWindow(st.hour*60+st.min, InpTradeStartHour*60, InpTradeEndHour*60)) return;
   if(g_trade.HasPosition() || g_tradesToday >= InpMaxTradesPerDay) return;
   if(!g_guards.SpreadOK(InpMaxSpreadPoints)) return;
   if(g_vwap <= 0.0 || g_sd <= 0.0) return;          // not enough data yet

   double atr   = ATRValue();
   double upper = g_vwap + InpBandSD * g_sd;
   double lower = g_vwap - InpBandSD * g_sd;

   GM_Dir dir = GM_NONE;
   double sl = 0.0;

   // Above upper band + bearish rejection -> fade short
   if(c >= upper)
     {
      bool reject = !InpRequireRejection || (c < o);
      if(reject) { dir = GM_SHORT; sl = h + atr * InpSLATRMult; }
     }
   // Below lower band + bullish rejection -> fade long
   if(dir == GM_NONE && c <= lower)
     {
      bool reject = !InpRequireRejection || (c > o);
      if(reject) { dir = GM_LONG; sl = l - atr * InpSLATRMult; }
     }
   if(dir == GM_NONE) return;

   double entry = (dir == GM_LONG) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double risk = MathAbs(entry - sl);
   if(risk <= 0.0) return;

   double tp;
   if(InpTPType == 1) tp = (dir == GM_LONG) ? entry + risk * InpRR : entry - risk * InpRR;
   else               tp = g_vwap;

   double rr = MathAbs(tp - entry) / risk;
   if(rr < InpMinRR) { g_log.Log("GM07","SKIP_RR",dir,entry,sl,tp,0,rr,0,"below MinRR"); return; }

   double lots = GM_CalcLots(risk, RiskPct(), MaxLotMult());
   if(lots <= 0.0) { g_log.Log("GM07","SKIP_SIZE",dir,entry,sl,tp,0,rr,0,"min lot risk too high"); return; }

   if(g_trade.Open(dir, lots, sl, tp, "GM07_VWAP"))
     { g_tradesToday++; g_log.Log("GM07","ENTRY",dir,entry,sl,tp,lots,rr,1,"VWAP band fade"); }
  }
//+------------------------------------------------------------------+
