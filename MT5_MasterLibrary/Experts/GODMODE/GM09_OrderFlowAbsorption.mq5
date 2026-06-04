//+------------------------------------------------------------------+
//|                            GM09_OrderFlowAbsorption.mq5           |
//|                      GODMODE Master EA Library  -  Archetype 09   |
//|                                                                  |
//|  Order-flow absorption + CVD divergence.                          |
//|  Distilled from: GODMODE_OFEA core (DeltaEngine), Carmine order   |
//|  flow, ATAS/Bookmap footprint educators, ChartFanatics OF cohort. |
//|                                                                  |
//|  >>> TICK DATA ONLY. On bar-based backtests the tick stream is    |
//|  synthetic and delta/CVD are meaningless. Use "Every tick based   |
//|  on real ticks" in the Strategy Tester, and live tick feed.       |
//|                                                                  |
//|  Logic: accumulate per-bar delta (buy vol - sell vol) and a       |
//|  cumulative delta (CVD). Trade two signals:                       |
//|   * Absorption: heavy delta against the candle that price holds   |
//|     (delta<0 but close up = buyers absorbing -> long; mirror).    |
//|   * CVD divergence: price new low / CVD higher low -> long.       |
//+------------------------------------------------------------------+
#property copyright "GODMODE Master Library"
#property version   "1.00"
#property strict

#include <GODMODE/GODMODE_Core.mqh>

input group "=== Identity ==="
input long   InpMagic            = 9009;

input group "=== Risk Mode ==="
input GM_RiskMode InpRiskMode    = RISK_CONSERVATIVE;
input double InpRiskConservative = 1.0;
input double InpRiskAggressive   = 3.0;
input double InpRiskFlip         = 8.0;
input double InpMaxLotRiskMult   = 3.0;

input group "=== Session (broker time) ==="
input bool   InpUseSession       = true;
input int    InpTradeStartHour   = 7;
input int    InpTradeEndHour     = 20;
input int    InpForceCloseHour   = 22;

input group "=== Order Flow ==="
input int    InpDeltaLookback    = 20;          // bars for CVD / volume-Z window
input double InpVolZThreshold    = 1.5;         // volume Z for absorption
input bool   InpUseAbsorption    = true;
input bool   InpUseCVDDivergence = true;
input int    InpATRPeriod        = 14;
input double InpSLATRMult        = 1.0;
input double InpRR               = 2.0;
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

// tick accumulation
double    g_buy = 0.0, g_sell = 0.0;
double    g_prevLast = 0.0, g_prevMid = 0.0;
double    g_barDelta[], g_vol[], g_cvd[];
int       g_filled = 0;
int       g_N = 20;

int OnInit()
  {
   g_trade.Init(InpMagic);
   g_guards.Init(InpMagic);
   g_log.Init("GODMODE_GM09_OrderFlow_log.csv");
   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   g_N = MathMax(InpDeltaLookback, 5);
   ArrayResize(g_barDelta, g_N); ArrayInitialize(g_barDelta, 0.0);
   ArrayResize(g_vol,      g_N); ArrayInitialize(g_vol, 0.0);
   ArrayResize(g_cvd,      g_N); ArrayInitialize(g_cvd, 0.0);
   Print("GM09 Order-Flow Absorption initialised. TICK DATA ONLY. RiskMode=", EnumToString(InpRiskMode));
   return INIT_SUCCEEDED;
  }
void OnDeinit(const int reason) { }

double ATRValue() { double b[]; if(g_atrHandle==INVALID_HANDLE||CopyBuffer(g_atrHandle,0,1,1,b)<=0) return 0.0; return b[0]; }
double RiskPct()  { return GM_ResolveRiskPct(InpRiskMode, InpRiskConservative, InpRiskAggressive, InpRiskFlip); }
double MaxLotMult(){ return (InpRiskMode == RISK_FLIP) ? 1000.0 : InpMaxLotRiskMult; }

double VolumeZ()
  {
   int n = g_filled; if(n < 2) return 0.0;
   double mean = 0.0; for(int i = 0; i < n; i++) mean += g_vol[i]; mean /= n;
   double sd = 0.0; for(int i = 0; i < n; i++) sd += (g_vol[i]-mean)*(g_vol[i]-mean);
   sd = MathSqrt(sd / n);
   if(sd < 1e-9) return 0.0;
   return (g_vol[0] - mean) / sd;
  }

void OnTick()
  {
   // --- accumulate order flow on every tick ---
   MqlTick t;
   if(SymbolInfoTick(_Symbol, t))
     {
      if(t.last > 0.0 && t.volume > 0)
        {
         if(t.last > g_prevLast)      g_buy  += (double)t.volume;
         else if(t.last < g_prevLast) g_sell += (double)t.volume;
         g_prevLast = t.last;
        }
      else
        {
         double mid = (t.bid + t.ask) * 0.5;
         if(g_prevMid > 0.0)
           {
            if(mid > g_prevMid)      g_buy  += 1.0;
            else if(mid < g_prevMid) g_sell += 1.0;
           }
         g_prevMid = mid;
        }
     }

   g_trade.Manage(InpBEatR, InpPartialAtR, InpPartialPct, InpUseTrail, InpTrailATRMult, ATRValue());

   if(!GM_IsNewBar(PERIOD_CURRENT, g_lastBar)) return;

   // --- snapshot the just-closed bar's delta into the ring ---
   double bd = g_buy - g_sell;
   double tv = g_buy + g_sell;
   if(tv <= 0.0) tv = (double)iTickVolume(_Symbol, PERIOD_CURRENT, 1);
   for(int i = g_N - 1; i > 0; i--)
     { g_barDelta[i] = g_barDelta[i-1]; g_vol[i] = g_vol[i-1]; g_cvd[i] = g_cvd[i-1]; }
   g_barDelta[0] = bd; g_vol[0] = tv; g_cvd[0] = g_cvd[1] + bd;
   g_buy = 0.0; g_sell = 0.0;
   if(g_filled < g_N) g_filled++;

   MqlDateTime st; TimeToStruct(TimeCurrent(), st);
   if(g_guards.IsNewDay()) { g_guards.OnNewDay(); g_tradesToday = 0; }
   if(g_guards.IsHalted()) return;
   if(g_guards.DailyDDBreached(InpMaxDailyDDPct))
     { g_trade.CloseAll(); g_guards.Halt(); g_log.Log("GM09","KILL_DD",GM_NONE,0,0,0,0,0,0,"daily DD"); return; }
   if(InpMaxConsecLosses > 0 && g_guards.TrailingLossStreak() >= InpMaxConsecLosses) { g_guards.Halt(); return; }
   if(st.hour >= InpForceCloseHour) { g_trade.CloseAll(); return; }
   if(InpUseSession && !GM_InWindow(st.hour*60+st.min, InpTradeStartHour*60, InpTradeEndHour*60)) return;
   if(g_trade.HasPosition() || g_tradesToday >= InpMaxTradesPerDay) return;
   if(!g_guards.SpreadOK(InpMaxSpreadPoints)) return;
   if(g_filled < g_N) return;                  // wait for a full window

   double o = iOpen (_Symbol, PERIOD_CURRENT, 1);
   double c = iClose(_Symbol, PERIOD_CURRENT, 1);
   double volZ = VolumeZ();
   double atr  = ATRValue();
   if(atr <= 0.0) return;

   GM_Dir dir = GM_NONE;
   string note = "";

   // --- absorption ---
   if(InpUseAbsorption && volZ >= InpVolZThreshold)
     {
      if(bd < 0.0 && c >= o) { dir = GM_LONG;  note = "bull absorption"; }
      if(bd > 0.0 && c <= o) { dir = GM_SHORT; note = "bear absorption"; }
     }

   // --- CVD divergence ---
   if(dir == GM_NONE && InpUseCVDDivergence)
     {
      double lowestLow  =  DBL_MAX, highestHigh = -DBL_MAX;
      double lowestCVD  =  DBL_MAX, highestCVD  = -DBL_MAX;
      for(int i = 1; i <= g_N; i++)
        {
         double ll = iLow (_Symbol, PERIOD_CURRENT, i);
         double hh = iHigh(_Symbol, PERIOD_CURRENT, i);
         if(ll < lowestLow)  lowestLow  = ll;
         if(hh > highestHigh) highestHigh = hh;
        }
      for(int i = 0; i < g_N; i++)
        {
         if(g_cvd[i] < lowestCVD)  lowestCVD  = g_cvd[i];
         if(g_cvd[i] > highestCVD) highestCVD = g_cvd[i];
        }
      double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
      bool bullDiv = (iLow (_Symbol, PERIOD_CURRENT, 1) <= lowestLow + pt)  && (g_cvd[0] > lowestCVD + 1e-9);
      bool bearDiv = (iHigh(_Symbol, PERIOD_CURRENT, 1) >= highestHigh - pt) && (g_cvd[0] < highestCVD - 1e-9);
      if(bullDiv) { dir = GM_LONG;  note = "CVD bull div"; }
      else if(bearDiv) { dir = GM_SHORT; note = "CVD bear div"; }
     }

   if(dir == GM_NONE) return;

   double entry = (dir == GM_LONG) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl = (dir == GM_LONG) ? iLow(_Symbol, PERIOD_CURRENT, 1) - atr * InpSLATRMult
                                : iHigh(_Symbol, PERIOD_CURRENT, 1) + atr * InpSLATRMult;
   double risk = MathAbs(entry - sl);
   if(risk <= 0.0) return;
   double tp = (dir == GM_LONG) ? entry + risk * InpRR : entry - risk * InpRR;

   double lots = GM_CalcLots(risk, RiskPct(), MaxLotMult());
   if(lots <= 0.0) { g_log.Log("GM09","SKIP_SIZE",dir,entry,sl,tp,0,InpRR,0,"min lot risk too high"); return; }

   if(g_trade.Open(dir, lots, sl, tp, "GM09_OF"))
     { g_tradesToday++; g_log.Log("GM09","ENTRY",dir,entry,sl,tp,lots,InpRR,1,note); }
  }
//+------------------------------------------------------------------+
