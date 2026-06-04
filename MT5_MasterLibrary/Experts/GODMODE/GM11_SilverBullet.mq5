//+------------------------------------------------------------------+
//|                                   GM11_SilverBullet.mq5           |
//|                      GODMODE Master EA Library  -  Archetype 11   |
//|                                                                  |
//|  ICT Silver Bullet: trade ONLY inside specific macro time        |
//|  windows, taking a liquidity sweep + FVG reversal.               |
//|  Distilled from: ICT Silver Bullet guide, Lumi ICT macros,       |
//|  Quarterly Theory 90-min cycle windows.                          |
//|                                                                  |
//|  Logic: inside an enabled window, if recent liquidity was swept   |
//|  (a new extreme vs the prior bars) and a fresh FVG forms in the   |
//|  reversal direction with price mitigating it, enter the reversal. |
//|  SL beyond the swept extreme; TP = R multiple.                    |
//+------------------------------------------------------------------+
#property copyright "GODMODE Master Library"
#property version   "1.00"
#property strict

#include <GODMODE/GODMODE_Core.mqh>

input group "=== Identity ==="
input long   InpMagic            = 9011;

input group "=== Risk Mode ==="
input GM_RiskMode InpRiskMode    = RISK_CONSERVATIVE;
input double InpRiskConservative = 1.0;
input double InpRiskAggressive   = 3.0;
input double InpRiskFlip         = 8.0;
input double InpMaxLotRiskMult   = 3.0;

input group "=== Macro Windows (broker server time, hours) ==="
input bool   InpW1Enable         = true;
input int    InpW1Start          = 10;          // e.g. NY AM macro 10:00-11:00
input int    InpW1End            = 11;
input bool   InpW2Enable         = true;
input int    InpW2Start          = 14;          // NY PM macro 14:00-15:00
input int    InpW2End            = 15;
input bool   InpW3Enable         = false;
input int    InpW3Start          = 3;           // London 03:00-04:00
input int    InpW3End            = 4;
input int    InpForceCloseHour   = 22;

input group "=== Entry / Exit ==="
input int    InpSweepLookback    = 12;          // bars to define the liquidity that gets swept
input int    InpFVGLookback      = 8;           // bars to find a fresh FVG
input double InpMinGapPoints     = 15;
input int    InpSLPaddingPoints  = 10;
input double InpRR               = 2.0;
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
datetime  g_lastBar   = 0;
int       g_tradesToday = 0;

int OnInit()
  {
   g_trade.Init(InpMagic);
   g_guards.Init(InpMagic);
   g_log.Init("GODMODE_GM11_SilverBullet_log.csv");
   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   Print("GM11 Silver Bullet initialised. RiskMode=", EnumToString(InpRiskMode));
   return INIT_SUCCEEDED;
  }
void OnDeinit(const int reason) { }

double ATRValue() { double b[]; if(g_atrHandle==INVALID_HANDLE||CopyBuffer(g_atrHandle,0,1,1,b)<=0) return 0.0; return b[0]; }
double RiskPct()  { return GM_ResolveRiskPct(InpRiskMode, InpRiskConservative, InpRiskAggressive, InpRiskFlip); }
double MaxLotMult(){ return (InpRiskMode == RISK_FLIP) ? 1000.0 : InpMaxLotRiskMult; }

bool InAnyWindow(const int mod)
  {
   if(InpW1Enable && GM_InWindow(mod, InpW1Start*60, InpW1End*60)) return true;
   if(InpW2Enable && GM_InWindow(mod, InpW2Start*60, InpW2End*60)) return true;
   if(InpW3Enable && GM_InWindow(mod, InpW3Start*60, InpW3End*60)) return true;
   return false;
  }

void OnTick()
  {
   g_trade.Manage(InpBEatR, InpPartialAtR, InpPartialPct, InpUseTrail, InpTrailATRMult, ATRValue());
   if(!GM_IsNewBar(PERIOD_CURRENT, g_lastBar)) return;

   MqlDateTime st; TimeToStruct(TimeCurrent(), st);
   int mod = st.hour*60 + st.min;

   if(g_guards.IsNewDay()) { g_guards.OnNewDay(); g_tradesToday=0; }
   if(g_guards.IsHalted()) return;
   if(g_guards.DailyDDBreached(InpMaxDailyDDPct))
     { g_trade.CloseAll(); g_guards.Halt(); g_log.Log("GM11","KILL_DD",GM_NONE,0,0,0,0,0,0,"daily DD"); return; }
   if(InpMaxConsecLosses>0 && g_guards.TrailingLossStreak()>=InpMaxConsecLosses) { g_guards.Halt(); return; }
   if(st.hour >= InpForceCloseHour) { g_trade.CloseAll(); return; }

   if(!InAnyWindow(mod)) return;
   if(g_trade.HasPosition() || g_tradesToday>=InpMaxTradesPerDay) return;
   if(!g_guards.SpreadOK(InpMaxSpreadPoints)) return;

   double minGap=InpMinGapPoints*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double pad=InpSLPaddingPoints*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double price=iClose(_Symbol,PERIOD_CURRENT,1);

   // liquidity references just before the live bar
   double priorLow  = GM_LowestLow(InpSweepLookback, 2);
   double priorHigh = GM_HighestHigh(InpSweepLookback, 2);
   double curLow=iLow(_Symbol,PERIOD_CURRENT,1), curHigh=iHigh(_Symbol,PERIOD_CURRENT,1);

   bool sweptLow  = curLow  < priorLow;   // sell-side liquidity taken -> expect up
   bool sweptHigh = curHigh > priorHigh;  // buy-side liquidity taken  -> expect down

   GM_Dir dir=GM_NONE; double sl=0.0; double top,bot;

   if(sweptLow && GM_FindBullishFVG(InpFVGLookback, top, bot) && (top-bot)>=minGap)
     {
      if(price<=top && price>=bot) { dir=GM_LONG; sl=curLow-pad; }
     }
   if(dir==GM_NONE && sweptHigh && GM_FindBearishFVG(InpFVGLookback, top, bot) && (top-bot)>=minGap)
     {
      if(price<=top && price>=bot) { dir=GM_SHORT; sl=curHigh+pad; }
     }
   if(dir==GM_NONE) return;

   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK), bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double entry=(dir==GM_LONG)?ask:bid;
   double risk=MathAbs(entry-sl); if(risk<=0) return;
   double tp=(dir==GM_LONG)?entry+risk*InpRR:entry-risk*InpRR;

   double lots=GM_CalcLots(risk, RiskPct(), MaxLotMult());
   if(lots<=0.0) { g_log.Log("GM11","SKIP_SIZE",dir,entry,sl,tp,0,InpRR,0,"min lot risk too high"); return; }

   if(g_trade.Open(dir, lots, sl, tp, "GM11_SB"))
     { g_tradesToday++; g_log.Log("GM11","ENTRY",dir,entry,sl,tp,lots,InpRR,2,"silver bullet sweep+FVG"); }
  }
//+------------------------------------------------------------------+
