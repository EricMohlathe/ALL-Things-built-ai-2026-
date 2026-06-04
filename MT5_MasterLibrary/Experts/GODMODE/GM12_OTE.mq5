//+------------------------------------------------------------------+
//|                                            GM12_OTE.mq5           |
//|                      GODMODE Master EA Library  -  Archetype 12   |
//|                                                                  |
//|  ICT Optimal Trade Entry: enter trend pullbacks in the 0.62-0.79 |
//|  Fibonacci retracement zone (OTE = 0.705). Distilled from:        |
//|  HowToTrade OTE guide, ICT OTE model.                            |
//|                                                                  |
//|  Logic: confirm trend with an EMA; when price retraces into the   |
//|  OTE zone of the last swing (optionally also inside an FVG), enter |
//|  with-trend. SL beyond the swing extreme; TP = swing origin (1.0) |
//|  or fixed R / SD extension.                                       |
//+------------------------------------------------------------------+
#property copyright "GODMODE Master Library"
#property version   "1.00"
#property strict

#include <GODMODE/GODMODE_Core.mqh>

input group "=== Identity ==="
input long   InpMagic            = 9012;

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

input group "=== OTE ==="
input int    InpSwingLookback    = 20;          // swing window for the Fib
input bool   InpUseEMABias       = true;
input int    InpEMAPeriod        = 50;
input bool   InpRequireFVG       = false;       // also require price inside an FVG
input int    InpFVGLookback      = 15;
input int    InpSLPaddingPoints  = 10;
input int    InpTPType           = 0;           // 0=swing origin(1.0), 1=Fixed RR
input double InpRR               = 2.0;
input double InpMinRR            = 1.5;
input int    InpATRPeriod        = 14;
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
   g_log.Init("GODMODE_GM12_OTE_log.csv");
   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   g_emaHandle = iMA(_Symbol, PERIOD_CURRENT, InpEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   Print("GM12 OTE initialised. RiskMode=", EnumToString(InpRiskMode));
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
     { g_trade.CloseAll(); g_guards.Halt(); g_log.Log("GM12","KILL_DD",GM_NONE,0,0,0,0,0,0,"daily DD"); return; }
   if(InpMaxConsecLosses>0 && g_guards.TrailingLossStreak()>=InpMaxConsecLosses) { g_guards.Halt(); return; }
   if(st.hour >= InpForceCloseHour) { g_trade.CloseAll(); return; }
   if(InpUseSession && !GM_InWindow(st.hour*60+st.min, InpTradeStartHour*60, InpTradeEndHour*60)) return;
   if(g_trade.HasPosition() || g_tradesToday>=InpMaxTradesPerDay) return;
   if(!g_guards.SpreadOK(InpMaxSpreadPoints)) return;

   double price=iClose(_Symbol,PERIOD_CURRENT,1);
   double ema=EMAValue();
   double pad=InpSLPaddingPoints*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double swingHi=GM_HighestHigh(InpSwingLookback,1), swingLo=GM_LowestLow(InpSwingLookback,1);

   GM_Dir dir=GM_NONE; double zTop,zBot; double sl=0.0, tp=0.0;
   double fTop,fBot;

   // Long OTE in uptrend
   if((!InpUseEMABias || price>ema) && GM_OTELong(InpSwingLookback, zTop, zBot))
     {
      bool inZone = price<=zTop && price>=zBot;
      bool fvgOK  = !InpRequireFVG || (GM_FindBullishFVG(InpFVGLookback,fTop,fBot) && price<=fTop && price>=fBot);
      if(inZone && fvgOK)
        { dir=GM_LONG; sl=swingLo-pad; tp=(InpTPType==1)?0:swingHi; }
     }
   // Short OTE in downtrend
   if(dir==GM_NONE && (!InpUseEMABias || price<ema) && GM_OTEShort(InpSwingLookback, zTop, zBot))
     {
      bool inZone = price<=zTop && price>=zBot;
      bool fvgOK  = !InpRequireFVG || (GM_FindBearishFVG(InpFVGLookback,fTop,fBot) && price<=fTop && price>=fBot);
      if(inZone && fvgOK)
        { dir=GM_SHORT; sl=swingHi+pad; tp=(InpTPType==1)?0:swingLo; }
     }
   if(dir==GM_NONE) return;

   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK), bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double entry=(dir==GM_LONG)?ask:bid;
   double risk=MathAbs(entry-sl); if(risk<=0) return;
   if(InpTPType==1) tp=(dir==GM_LONG)?entry+risk*InpRR:entry-risk*InpRR;

   double rr=MathAbs(tp-entry)/risk;
   if(rr<InpMinRR) { g_log.Log("GM12","SKIP_RR",dir,entry,sl,tp,0,rr,0,"below MinRR"); return; }

   double lots=GM_CalcLots(risk, RiskPct(), MaxLotMult());
   if(lots<=0.0) { g_log.Log("GM12","SKIP_SIZE",dir,entry,sl,tp,0,rr,0,"min lot risk too high"); return; }

   if(g_trade.Open(dir, lots, sl, tp, "GM12_OTE"))
     { g_tradesToday++; g_log.Log("GM12","ENTRY",dir,entry,sl,tp,lots,rr,1,"OTE 0.62-0.79"); }
  }
//+------------------------------------------------------------------+
