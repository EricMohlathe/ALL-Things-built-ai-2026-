//+------------------------------------------------------------------+
//|  Isaiah6022_NY0930_ORB.mq5                                       |
//|                                                                  |
//|  Strategy 01 — The 9:30 New York Opening Range.                  |
//|                                                                  |
//|  Mark the 09:30-09:35 NY five-minute candle. Trade the body       |
//|  close beyond it. Stop at the opposite boundary. Entries close    |
//|  at 10:30 NY.                                                     |
//|                                                                  |
//|  The default entry model is the DIRECT break, not the retest.     |
//|  The retest is provided so you can measure it for yourself:       |
//|  across 165,336 tested trades it LOWERED the win rate             |
//|  (33.0% -> 31.9% on holdout, p < 0.001). Run both, on your        |
//|  instrument, at your costs, and believe your own journal.         |
//|                                                                  |
//|  Install:                                                        |
//|    MQL5/Include/Isaiah6022_Core.mqh                              |
//|    MQL5/Experts/Isaiah6022_NY0930_ORB.mq5                        |
//|  Compile with F7, attach to any chart of the traded symbol.       |
//+------------------------------------------------------------------+
#property copyright "Isaiah 60:22"
#property version   "1.00"
#property description "9:30 NY opening-range breakout with a forensic journal. Direct break by default; retest available for falsification."

#include <Isaiah6022_Core.mqh>

//====================================================================
//  ENTRY MODELS
//====================================================================
enum ENUM_ORB_MODEL
  {
   ORB_BREAK_DIRECT,   // 1 Body close beyond the range. Enter at that close. DEFAULT
   ORB_BREAK_FVG,      // 2 Break, then enter on a fair value gap in the displacement
   ORB_RETEST,         // 3 Break -> pullback to the boundary -> rejection close
   ORB_TRAP            // 4 Break out -> close back inside -> close back out
  };

//====================================================================
//  INPUTS
//====================================================================
input group             "===  1. MODEL & TIMEFRAMES  ==="
input ENUM_ORB_MODEL    InpModel             = ORB_BREAK_DIRECT;   // Entry model
input ENUM_TIMEFRAMES   InpRangeTF           = PERIOD_M5;          // Range timeframe (the 9:30 candle)
input ENUM_TIMEFRAMES   InpEntryTF           = PERIOD_M1;          // Entry / trigger timeframe

input group             "===  2. CLOCK — all times New York local  ==="
input double            InpBrokerGMTOffset   = 2.0;   // Broker GMT offset in WINTER (verify, do not guess)
input bool              InpAutoGMTOffset     = true;  // Try to detect the offset at init (live only)
input int               InpRangeStartHH      = 9;     // Range start hour   (NY)
input int               InpRangeStartMM      = 30;    // Range start minute (NY)
input int               InpRangeEndHH        = 9;     // Range end hour     (NY)
input int               InpRangeEndMM        = 35;    // Range end minute   (NY)
input int               InpTradeStartHH      = 9;     // Entry window start hour   (NY)
input int               InpTradeStartMM      = 35;    // Entry window start minute (NY)
input int               InpTradeEndHH        = 10;    // Entry window end hour     (NY)
input int               InpTradeEndMM        = 30;    // Entry window end minute   (NY)
input int               InpFlatHH            = 15;    // Force-flat hour   (NY)
input int               InpFlatMM            = 55;    // Force-flat minute (NY)
input bool              InpTradeMonday       = true;  // Monday
input bool              InpTradeTuesday      = true;  // Tuesday
input bool              InpTradeWednesday    = true;  // Wednesday
input bool              InpTradeThursday     = true;  // Thursday
input bool              InpTradeFriday       = true;  // Friday

input group             "===  3. SIGNAL RULES  ==="
input bool              InpRequireBodyClose  = true;  // Break must be a BODY close, not a wick
input double            InpBreakBufferPts    = 0;     // Extra points beyond the range to count a break
input int               InpMaxBarsToTrigger  = 60;    // Give up if no trigger within N entry bars
input int               InpFVGLookback       = 3;     // Bars scanned for the displacement FVG
input double            InpMinFVGPts         = 0;     // Minimum FVG height in points (0 = any)
input int               InpRetestMaxBars     = 20;    // Retest must occur within N bars of the break
input double            InpMinRangePts       = 0;     // Skip the day if the range is narrower than this
input double            InpMaxRangeATR       = 3.0;   // Skip the day if range > N x ATR (0 = off)

input group             "===  4. DIRECTIONAL BIAS  ==="
input ENUM_I22_BIAS     InpBiasMode          = I22_BIAS_OFF;   // Bias filter (get a baseline before adding one)
input ENUM_TIMEFRAMES   InpBiasTF            = PERIOD_H4;      // Bias timeframe
input int               InpBiasEMAPeriod     = 50;             // Bias EMA period
input bool              InpBiasBlocksCounter = true;           // Bias blocks counter-trend entries

input group             "===  5. STOPS & TARGETS  ==="
input ENUM_I22_EXIT     InpExitMode          = I22_EXIT_FIXED_R;  // Exit management
input double            InpTargetR           = 2.0;   // Take profit in R multiples
input double            InpStopBufferPts     = 0;     // Extra points beyond the structural stop
input int               InpATRPeriod         = 14;    // ATR period
input double            InpMinStopATR        = 0.25;  // Stop floor as a fraction of ATR
input double            InpMaxStopATR        = 3.0;   // Stop ceiling as a multiple of ATR
input double            InpBreakevenAtR      = 0.0;   // Move the stop to BE at N R (0 = off)
input double            InpPartialAtR        = 0.0;   // Close part of the position at N R (0 = off)
input double            InpPartialPercent    = 50.0;  // Percent closed at the partial
input double            InpATRTrailMult      = 1.5;   // ATR multiple for the trailing stop

input group             "===  6. RISK KERNEL (hard limits)  ==="
input double            InpRiskPercent       = 0.5;   // Risk per trade, percent of equity
input double            InpMaxDailyLossPct   = 2.0;   // Halt for the session at this loss
input double            InpMaxTotalDDPct     = 10.0;  // Halt permanently at this drawdown
input int               InpMaxTradesPerDay   = 2;     // Max entries per NY session
input int               InpMaxConsecLosses   = 4;     // Halt for the session after N losses
input double            InpMaxSpreadPts      = 30;    // Reject an entry above this spread
input double            InpMaxSpreadVsStop   = 10.0;  // Reject if spread exceeds N% of the stop
input int               InpSlippagePts       = 20;    // Max deviation on market orders
input long              InpMagic             = 60221; // Magic number

input group             "===  7. FORENSIC JOURNAL  ==="
input bool              InpWriteJournal      = true;                // Write the per-trade CSV
input string            InpJournalFile       = "I22_ORB_journal.csv"; // File in MQL5/Files
input string            InpRunTag            = "orb_direct_v1";     // CHANGE THIS EVERY RUN
input bool              InpShowDashboard     = true;                // On-chart dashboard
input bool              InpDrawObjects       = true;                // Draw the range lines

//====================================================================
//  STRATEGY STATE
//====================================================================
int      s_breakDir      = 0;     // direction of the confirmed break, 0 = none yet
double   s_breakLevel    = 0.0;   // the boundary that was broken
double   s_breakClose    = 0.0;   // close of the breaking bar
datetime s_breakBarTime  = 0;
int      s_barsSinceBreak= 0;
bool     s_trapArmed     = false; // broke out and closed back inside
int      s_trapDir       = 0;
datetime s_lastEntryBar  = 0;

//+------------------------------------------------------------------+
//| Reset the per-session signal state                                |
//+------------------------------------------------------------------+
void ResetSignalState()
  {
   s_breakDir       = 0;
   s_breakLevel     = 0.0;
   s_breakClose     = 0.0;
   s_breakBarTime   = 0;
   s_barsSinceBreak = 0;
   s_trapArmed      = false;
   s_trapDir        = 0;
  }

//+------------------------------------------------------------------+
//| OnInit                                                            |
//+------------------------------------------------------------------+
int OnInit()
  {
   g_cfg.brokerGMTOffset  = InpBrokerGMTOffset;
   g_cfg.autoGMTOffset    = InpAutoGMTOffset;
   g_cfg.rangeStartMin    = InpRangeStartHH * 60 + InpRangeStartMM;
   g_cfg.rangeEndMin      = InpRangeEndHH   * 60 + InpRangeEndMM;
   g_cfg.tradeStartMin    = InpTradeStartHH * 60 + InpTradeStartMM;
   g_cfg.tradeEndMin      = InpTradeEndHH   * 60 + InpTradeEndMM;
   g_cfg.flatMin          = InpFlatHH       * 60 + InpFlatMM;

   g_cfg.tradeDay[0] = false;               // Sunday
   g_cfg.tradeDay[1] = InpTradeMonday;
   g_cfg.tradeDay[2] = InpTradeTuesday;
   g_cfg.tradeDay[3] = InpTradeWednesday;
   g_cfg.tradeDay[4] = InpTradeThursday;
   g_cfg.tradeDay[5] = InpTradeFriday;
   g_cfg.tradeDay[6] = false;               // Saturday

   g_cfg.rangeTF          = InpRangeTF;
   g_cfg.entryTF          = InpEntryTF;

   g_cfg.requireBodyClose = InpRequireBodyClose;
   g_cfg.breakBufferPts   = InpBreakBufferPts;
   g_cfg.maxBarsToTrigger = InpMaxBarsToTrigger;
   g_cfg.minRangePts      = InpMinRangePts;
   g_cfg.maxRangeATR      = InpMaxRangeATR;

   g_cfg.biasMode         = InpBiasMode;
   g_cfg.biasTF           = InpBiasTF;
   g_cfg.biasEMAPeriod    = InpBiasEMAPeriod;
   g_cfg.biasBlocksCounter= InpBiasBlocksCounter;

   g_cfg.exitMode         = InpExitMode;
   g_cfg.targetR          = InpTargetR;
   g_cfg.stopBufferPts    = InpStopBufferPts;
   g_cfg.atrPeriod        = InpATRPeriod;
   g_cfg.minStopATR       = InpMinStopATR;
   g_cfg.maxStopATR       = InpMaxStopATR;
   g_cfg.breakevenAtR     = InpBreakevenAtR;
   g_cfg.partialAtR       = InpPartialAtR;
   g_cfg.partialPercent   = InpPartialPercent;
   g_cfg.atrTrailMult     = InpATRTrailMult;

   g_cfg.riskPercent      = InpRiskPercent;
   g_cfg.maxDailyLossPct  = InpMaxDailyLossPct;
   g_cfg.maxTotalDDPct    = InpMaxTotalDDPct;
   g_cfg.maxTradesPerDay  = InpMaxTradesPerDay;
   g_cfg.maxConsecLosses  = InpMaxConsecLosses;
   g_cfg.maxSpreadPts     = InpMaxSpreadPts;
   g_cfg.maxSpreadVsStop  = InpMaxSpreadVsStop;
   g_cfg.slippagePts      = InpSlippagePts;
   g_cfg.magic            = InpMagic;

   g_cfg.writeJournal     = InpWriteJournal;
   g_cfg.journalFile      = InpJournalFile;
   g_cfg.runTag           = InpRunTag;
   g_cfg.strategyTag      = "NY_ORB_0930";
   g_cfg.modelTag         = EnumToString(InpModel);
   g_cfg.drawObjects      = InpDrawObjects;
   g_cfg.showDashboard    = InpShowDashboard;

   if(InpRiskPercent <= 0.0 || InpRiskPercent > 5.0)
     {
      Print("Isaiah 60:22 | risk percent must be between 0 and 5. Refusing to start.");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(InpTargetR <= 0.0)
     {
      Print("Isaiah 60:22 | target R must be positive. Refusing to start.");
      return INIT_PARAMETERS_INCORRECT;
     }

   if(!I22_Init()) return INIT_FAILED;

   ResetSignalState();
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason) { I22_Deinit(); }

//====================================================================
//  SIGNAL DETECTION
//====================================================================

//+------------------------------------------------------------------+
//| Has the last closed entry-TF bar broken a boundary?               |
//| Returns +1 / -1 / 0. Fills the level that was broken.             |
//+------------------------------------------------------------------+
int DetectBreak(double &level)
  {
   double c = iClose(_Symbol, g_cfg.entryTF, 1);
   double h = iHigh (_Symbol, g_cfg.entryTF, 1);
   double l = iLow  (_Symbol, g_cfg.entryTF, 1);
   if(c <= 0.0) return 0;

   double buf = g_cfg.breakBufferPts * Pt();

   double upTest = g_cfg.requireBodyClose ? c : h;
   double dnTest = g_cfg.requireBodyClose ? c : l;

   if(upTest > g_rangeHigh + buf) { level = g_rangeHigh; return  1; }
   if(dnTest < g_rangeLow  - buf) { level = g_rangeLow;  return -1; }
   return 0;
  }

//+------------------------------------------------------------------+
//| A three-bar fair value gap in the direction of the break, formed  |
//| within the last InpFVGLookback bars.                              |
//| Bullish FVG: low[i] > high[i+2]. Bearish: high[i] < low[i+2].     |
//| Returns the mitigation level (the near edge of the gap), or 0.    |
//+------------------------------------------------------------------+
double FindFVG(const int dir)
  {
   double minH = InpMinFVGPts * Pt();

   for(int i = 1; i <= InpFVGLookback; i++)
     {
      double h0 = iHigh(_Symbol, g_cfg.entryTF, i);
      double l0 = iLow (_Symbol, g_cfg.entryTF, i);
      double h2 = iHigh(_Symbol, g_cfg.entryTF, i + 2);
      double l2 = iLow (_Symbol, g_cfg.entryTF, i + 2);
      if(h0 <= 0.0 || h2 <= 0.0) continue;

      if(dir > 0 && l0 > h2 && (l0 - h2) >= minH) return l0;   // bullish gap: enter on return to its low
      if(dir < 0 && h0 < l2 && (l2 - h0) >= minH) return h0;   // bearish gap: enter on return to its high
     }
   return 0.0;
  }

//+------------------------------------------------------------------+
//| Rejection close at the retested boundary: the bar traded back to  |
//| the level and closed away from it, in the break direction.        |
//+------------------------------------------------------------------+
bool RetestRejection(const int dir, const double level)
  {
   double o = iOpen (_Symbol, g_cfg.entryTF, 1);
   double c = iClose(_Symbol, g_cfg.entryTF, 1);
   double h = iHigh (_Symbol, g_cfg.entryTF, 1);
   double l = iLow  (_Symbol, g_cfg.entryTF, 1);
   if(c <= 0.0) return false;

   if(dir > 0)
      return (l <= level && c > level && c > o);
   return (h >= level && c < level && c < o);
  }

//====================================================================
//  MAIN LOOP
//====================================================================
void OnTick()
  {
   string prevDay = g_dayKey;

   if(!I22_Housekeeping())
     {
      if(g_dayKey != prevDay) ResetSignalState();
      DrawDashboard(SignalStateText());
      return;
     }
   if(g_dayKey != prevDay) ResetSignalState();

   // one decision per closed entry bar
   if(!IsNewBar(g_cfg.entryTF, s_lastEntryBar))
     {
      DrawDashboard(SignalStateText());
      return;
     }

   if(s_breakDir != 0) s_barsSinceBreak++;

   string biasLbl;
   int bias = CurrentBias(biasLbl);

   //--- 1. look for the break that arms the setup
   if(s_breakDir == 0)
     {
      double level = 0.0;
      int dir = DetectBreak(level);
      if(dir != 0)
        {
         s_breakDir       = dir;
         s_breakLevel     = level;
         s_breakClose     = iClose(_Symbol, g_cfg.entryTF, 1);
         s_breakBarTime   = iTime (_Symbol, g_cfg.entryTF, 1);
         s_barsSinceBreak = 0;

         PrintFormat("Isaiah 60:22 | %s break of %s at %s",
                     (dir > 0 ? "upside" : "downside"),
                     DoubleToString(level, _Digits),
                     DoubleToString(s_breakClose, _Digits));
        }
     }

   if(s_breakDir == 0)
     {
      DrawDashboard(SignalStateText());
      return;
     }

   // the setup expires
   if(g_cfg.maxBarsToTrigger > 0 && s_barsSinceBreak > g_cfg.maxBarsToTrigger)
     {
      Print("Isaiah 60:22 | setup expired without a trigger");
      ResetSignalState();
      DrawDashboard(SignalStateText());
      return;
     }

   //--- 2. bias veto
   if(g_cfg.biasBlocksCounter && bias != 0 && bias != s_breakDir)
     {
      PrintFormat("Isaiah 60:22 | entry vetoed by bias (%s vs %s break)",
                  biasLbl, (s_breakDir > 0 ? "upside" : "downside"));
      ResetSignalState();
      DrawDashboard(SignalStateText());
      return;
     }

   //--- 3. model-specific trigger
   int    dir       = s_breakDir;
   double stopPrice = (dir > 0) ? g_rangeLow : g_rangeHigh;   // opposite boundary
   bool   fire      = false;
   string trigger   = "";

   switch(InpModel)
     {
      case ORB_BREAK_DIRECT:
         // The break bar IS the trigger. Nothing further to wait for.
         fire    = (s_barsSinceBreak == 0);
         trigger = "direct_break";
         break;

      case ORB_BREAK_FVG:
        {
         double fvg = FindFVG(dir);
         if(fvg > 0.0)
           {
            double px = (dir > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                                  : SymbolInfoDouble(_Symbol, SYMBOL_BID);
            // enter when price has traded back into the gap
            if((dir > 0 && px <= fvg) || (dir < 0 && px >= fvg))
              {
               fire    = true;
               trigger = "break_fvg";
              }
           }
         break;
        }

      case ORB_RETEST:
         if(s_barsSinceBreak >= 1 && s_barsSinceBreak <= InpRetestMaxBars &&
            RetestRejection(dir, s_breakLevel))
           {
            fire    = true;
            trigger = "retest_rejection";
            // the rejection candle's extreme is the tighter, taught stop
            stopPrice = (dir > 0) ? iLow (_Symbol, g_cfg.entryTF, 1)
                                  : iHigh(_Symbol, g_cfg.entryTF, 1);
           }
         break;

      case ORB_TRAP:
        {
         double c = iClose(_Symbol, g_cfg.entryTF, 1);
         if(!s_trapArmed)
           {
            // price broke out, now closes back INSIDE the range
            bool backInside = (c < g_rangeHigh && c > g_rangeLow);
            if(backInside && s_barsSinceBreak >= 1)
              {
               s_trapArmed = true;
               s_trapDir   = -s_breakDir;    // the trap trades the other way
               Print("Isaiah 60:22 | trap armed: break failed back inside the range");
              }
           }
         else
           {
            // and now closes back out, on the opposite side
            if(s_trapDir > 0 && c > g_rangeHigh) { fire = true; dir =  1; }
            if(s_trapDir < 0 && c < g_rangeLow ) { fire = true; dir = -1; }
            if(fire)
              {
               trigger   = "trap_reversal";
               stopPrice = (dir > 0) ? g_rangeLow : g_rangeHigh;
              }
           }
         break;
        }
     }

   if(fire)
     {
      if(OpenPosition(dir, stopPrice, trigger))
         ResetSignalState();
     }

   DrawDashboard(SignalStateText());
  }

//+------------------------------------------------------------------+
//| Dashboard tail                                                    |
//+------------------------------------------------------------------+
string SignalStateText()
  {
   if(s_breakDir == 0) return "signal     no break yet";

   string s = StringFormat("signal     %s break of %s, %d bars ago",
                           (s_breakDir > 0 ? "upside" : "downside"),
                           DoubleToString(s_breakLevel, _Digits),
                           s_barsSinceBreak);
   if(s_trapArmed) s += "  [trap armed]";
   return s;
  }
//+------------------------------------------------------------------+
