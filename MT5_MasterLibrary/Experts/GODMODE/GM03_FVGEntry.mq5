//+------------------------------------------------------------------+
//|                                       GM03_FVGEntry.mq5           |
//|                      GODMODE Master EA Library  -  Archetype 03   |
//|                                                                  |
//|  Fair Value Gap (FVG) mitigation entry, trend-aligned.            |
//|  Distilled from: ICT FVG model, Casper SMC FCR-FVG, displacement  |
//|  entries, and the "imbalance fill" educators.                     |
//|                                                                  |
//|  Logic: detect a fresh 3-candle FVG (imbalance). When price        |
//|  retraces back INTO the gap (mitigation) AND trade direction       |
//|  aligns with the EMA-bias filter, enter toward the gap direction.  |
//|  SL beyond the gap; TP = fixed R multiple.                         |
//+------------------------------------------------------------------+
#property copyright "GODMODE Master Library"
#property version   "1.00"
#property strict

#include <GODMODE/GODMODE_Core.mqh>

input group "=== Identity ==="
input long   InpMagic            = 9003;

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

input group "=== FVG / Bias ==="
input int    InpFVGLookback      = 20;          // bars to scan for a fresh FVG
input double InpMinGapPoints     = 20;          // minimum gap size (points)
input bool   InpUseEMABias       = true;        // only trade with EMA trend
input int    InpEMAPeriod        = 50;          // bias EMA
input int    InpSLPaddingPoints  = 10;
input double InpRR               = 2.0;
input int    InpMaxTradesPerDay  = 2;

input group "=== Trade Management ==="
input double InpBEatR            = 1.0;
input double InpPartialAtR       = 1.0;
input double InpPartialPct       = 50.0;
input bool   InpUseTrail         = false;
input double InpTrailATRMult     = 1.5;
input int    InpATRPeriod        = 14;

input group "=== Guards ==="
input double InpMaxDailyDDPct    = 6.0;
input int    InpMaxConsecLosses  = 3;
input double InpMaxSpreadPoints  = 0;

//------------------------------------------------------------------ globals
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
   g_log.Init("GODMODE_GM03_FVG_log.csv");
   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   g_emaHandle = iMA(_Symbol, PERIOD_CURRENT, InpEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   Print("GM03 FVG Entry initialised. RiskMode=", EnumToString(InpRiskMode));
   return INIT_SUCCEEDED;
  }
void OnDeinit(const int reason) { }

double ATRValue()
  {
   if(g_atrHandle == INVALID_HANDLE) return 0.0;
   double b[]; if(CopyBuffer(g_atrHandle, 0, 1, 1, b) <= 0) return 0.0; return b[0];
  }
double EMAValue()
  {
   if(g_emaHandle == INVALID_HANDLE) return 0.0;
   double b[]; if(CopyBuffer(g_emaHandle, 0, 1, 1, b) <= 0) return 0.0; return b[0];
  }
double RiskPct()  { return GM_ResolveRiskPct(InpRiskMode, InpRiskConservative, InpRiskAggressive, InpRiskFlip); }
double MaxLotMult(){ return (InpRiskMode == RISK_FLIP) ? 1000.0 : InpMaxLotRiskMult; }

//+------------------------------------------------------------------+
void OnTick()
  {
   g_trade.Manage(InpBEatR, InpPartialAtR, InpPartialPct, InpUseTrail, InpTrailATRMult, ATRValue());

   if(!GM_IsNewBar(PERIOD_CURRENT, g_lastBar)) return;

   MqlDateTime st; TimeToStruct(TimeCurrent(), st);

   if(g_guards.IsNewDay()) { g_guards.OnNewDay(); g_tradesToday = 0; }
   if(g_guards.IsHalted()) return;
   if(g_guards.DailyDDBreached(InpMaxDailyDDPct))
     { g_trade.CloseAll(); g_guards.Halt(); g_log.Log("GM03","KILL_DD",GM_NONE,0,0,0,0,0,0,"daily DD"); return; }
   if(InpMaxConsecLosses > 0 && g_guards.TrailingLossStreak() >= InpMaxConsecLosses)
     { g_guards.Halt(); return; }

   if(st.hour >= InpForceCloseHour) { g_trade.CloseAll(); return; }
   if(InpUseSession && !GM_InWindow(st.hour * 60 + st.min, InpTradeStartHour * 60, InpTradeEndHour * 60))
      return;
   if(g_trade.HasPosition() || g_tradesToday >= InpMaxTradesPerDay) return;
   if(!g_guards.SpreadOK(InpMaxSpreadPoints)) return;

   double price  = iClose(_Symbol, PERIOD_CURRENT, 1);
   double ema    = EMAValue();
   double minGap = InpMinGapPoints * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double pad    = InpSLPaddingPoints * SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   double top = 0.0, bot = 0.0;
   GM_Dir dir = GM_NONE;
   double sl  = 0.0;

   // Bullish FVG: gap below price, price retraced into it -> long
   if(GM_FindBullishFVG(InpFVGLookback, top, bot) && (top - bot) >= minGap)
     {
      bool inGap   = (price <= top && price >= bot);
      bool biasOK  = !InpUseEMABias || price > ema;
      if(inGap && biasOK) { dir = GM_LONG; sl = bot - pad; }
     }
   // Bearish FVG: gap above price, price retraced into it -> short
   if(dir == GM_NONE && GM_FindBearishFVG(InpFVGLookback, top, bot) && (top - bot) >= minGap)
     {
      bool inGap  = (price <= top && price >= bot);
      bool biasOK = !InpUseEMABias || price < ema;
      if(inGap && biasOK) { dir = GM_SHORT; sl = top + pad; }
     }
   if(dir == GM_NONE) return;

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = (dir == GM_LONG) ? ask : bid;
   double risk = MathAbs(entry - sl);
   if(risk <= 0.0) return;
   double tp = (dir == GM_LONG) ? entry + risk * InpRR : entry - risk * InpRR;

   double lots = GM_CalcLots(risk, RiskPct(), MaxLotMult());
   if(lots <= 0.0)
     { g_log.Log("GM03","SKIP_SIZE",dir,entry,sl,tp,0,InpRR,0,"min lot risk too high"); return; }

   if(g_trade.Open(dir, lots, sl, tp, "GM03_FVG"))
     {
      g_tradesToday++;
      g_log.Log("GM03","ENTRY",dir,entry,sl,tp,lots,InpRR,1,"FVG mitigation");
     }
  }
//+------------------------------------------------------------------+
