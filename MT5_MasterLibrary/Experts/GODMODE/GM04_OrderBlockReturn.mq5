//+------------------------------------------------------------------+
//|                                  GM04_OrderBlockReturn.mq5        |
//|                      GODMODE Master EA Library  -  Archetype 04   |
//|                                                                  |
//|  Order Block return.                                              |
//|  Distilled from: ICT/SMC order-block educators (Astro FX, Akil    |
//|  Stokes, Etienne Crete, generic SMC), GODMODE setup 19 (ObReturn).|
//|                                                                  |
//|  Logic: find the last opposite-colour candle before a strong      |
//|  displacement (the order block). When price RETURNS into that      |
//|  zone and aligns with the EMA bias, enter in the displacement      |
//|  direction. SL beyond the OB; TP = fixed R multiple.               |
//+------------------------------------------------------------------+
#property copyright "GODMODE Master Library"
#property version   "1.00"
#property strict

#include <GODMODE/GODMODE_Core.mqh>

input group "=== Identity ==="
input long   InpMagic            = 9004;

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

input group "=== Order Block / Bias ==="
input int    InpOBLookback       = 30;          // bars to scan for an OB
input double InpDispMult         = 0.8;         // displacement size (x ATR)
input int    InpATRPeriod        = 14;
input bool   InpUseEMABias       = true;
input int    InpEMAPeriod        = 50;
input int    InpSLPaddingPoints  = 10;
input double InpRR               = 2.0;
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
int       g_emaHandle = INVALID_HANDLE;
datetime  g_lastBar   = 0;
int       g_tradesToday = 0;

int OnInit()
  {
   g_trade.Init(InpMagic);
   g_guards.Init(InpMagic);
   g_log.Init("GODMODE_GM04_OB_log.csv");
   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   g_emaHandle = iMA(_Symbol, PERIOD_CURRENT, InpEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   Print("GM04 Order Block Return initialised. RiskMode=", EnumToString(InpRiskMode));
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
   if(g_guards.IsNewDay()) { g_guards.OnNewDay(); g_tradesToday = 0; }
   if(g_guards.IsHalted()) return;
   if(g_guards.DailyDDBreached(InpMaxDailyDDPct))
     { g_trade.CloseAll(); g_guards.Halt(); g_log.Log("GM04","KILL_DD",GM_NONE,0,0,0,0,0,0,"daily DD"); return; }
   if(InpMaxConsecLosses > 0 && g_guards.TrailingLossStreak() >= InpMaxConsecLosses) { g_guards.Halt(); return; }
   if(st.hour >= InpForceCloseHour) { g_trade.CloseAll(); return; }
   if(InpUseSession && !GM_InWindow(st.hour*60+st.min, InpTradeStartHour*60, InpTradeEndHour*60)) return;
   if(g_trade.HasPosition() || g_tradesToday >= InpMaxTradesPerDay) return;
   if(!g_guards.SpreadOK(InpMaxSpreadPoints)) return;

   double atr = ATRValue();
   double ema = EMAValue();
   double price = iClose(_Symbol, PERIOD_CURRENT, 1);
   double pad = InpSLPaddingPoints * SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   double obTop = 0.0, obBot = 0.0;
   GM_Dir dir = GM_NONE;
   double sl = 0.0;

   if(GM_FindBullishOB(InpOBLookback, atr, InpDispMult, obTop, obBot))
     {
      bool inZone = (price <= obTop && price >= obBot);
      bool biasOK = !InpUseEMABias || price > ema;
      if(inZone && biasOK) { dir = GM_LONG; sl = obBot - pad; }
     }
   if(dir == GM_NONE && GM_FindBearishOB(InpOBLookback, atr, InpDispMult, obTop, obBot))
     {
      bool inZone = (price <= obTop && price >= obBot);
      bool biasOK = !InpUseEMABias || price < ema;
      if(inZone && biasOK) { dir = GM_SHORT; sl = obTop + pad; }
     }
   if(dir == GM_NONE) return;

   double entry = (dir == GM_LONG) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double risk = MathAbs(entry - sl);
   if(risk <= 0.0) return;
   double tp = (dir == GM_LONG) ? entry + risk * InpRR : entry - risk * InpRR;

   double lots = GM_CalcLots(risk, RiskPct(), MaxLotMult());
   if(lots <= 0.0) { g_log.Log("GM04","SKIP_SIZE",dir,entry,sl,tp,0,InpRR,0,"min lot risk too high"); return; }

   if(g_trade.Open(dir, lots, sl, tp, "GM04_OB"))
     { g_tradesToday++; g_log.Log("GM04","ENTRY",dir,entry,sl,tp,lots,InpRR,1,"OB return"); }
  }
//+------------------------------------------------------------------+
