//+------------------------------------------------------------------+
//|  Isaiah6022_AsianSweep.mq5                                       |
//|                                                                  |
//|  Strategy 02 — The Asian Range Liquidity Sweep.                  |
//|                                                                  |
//|  Mark the 19:00-00:00 NY overnight range. Wait for price to take  |
//|  out one extreme, close back inside, and then shift structure.    |
//|  Trade the reversal. Entries 02:00-11:00 NY.                      |
//|                                                                  |
//|  The sweep predicts VOLATILITY, not direction. Osler's order-book |
//|  work found take-profit orders cluster AT a level (reversal) and  |
//|  stop orders cluster JUST BEYOND it (continuation) — which is why |
//|  the two source families trade this same level in opposite        |
//|  directions and both publish winning screenshots.                 |
//|                                                                  |
//|  Direction therefore has to come from somewhere other than the    |
//|  sweep. That is what the bias filter is for, and it defaults ON.  |
//|  Run it once with InpBiasMode = I22_BIAS_OFF: if the filter does  |
//|  not improve the result, the strategy has no premise left.        |
//|                                                                  |
//|  Install:                                                        |
//|    MQL5/Include/Isaiah6022_Core.mqh                              |
//|    MQL5/Experts/Isaiah6022_AsianSweep.mq5                        |
//+------------------------------------------------------------------+
#property copyright "Isaiah 60:22"
#property version   "1.00"
#property description "ICT Asian-range liquidity sweep with market structure shift confirmation and a forensic journal."

#include <Isaiah6022_Core.mqh>

//====================================================================
//  ENTRY MODELS
//====================================================================
enum ENUM_SWEEP_MODEL
  {
   SWEEP_MSS,          // 1 Sweep -> reclaim -> market structure shift. DEFAULT
   SWEEP_MSS_FVG,      // 2 As above, then wait for the retracement into the displacement FVG
   SWEEP_RECLAIM,      // 3 Sweep -> close back inside. No MSS required (weaker, for comparison)
   SWEEP_RANGE_CROSS   // 4 Sweep one side, then trade the close through the OPPOSITE boundary
  };

//====================================================================
//  INPUTS
//====================================================================
input group             "===  1. MODEL & TIMEFRAMES  ==="
input ENUM_SWEEP_MODEL  InpModel             = SWEEP_MSS;      // Entry model
input ENUM_TIMEFRAMES   InpRangeTF           = PERIOD_M15;     // Range timeframe (overnight range)
input ENUM_TIMEFRAMES   InpEntryTF           = PERIOD_M5;      // Entry / trigger timeframe

input group             "===  2. CLOCK — all times New York local  ==="
input double            InpBrokerGMTOffset   = 2.0;   // Broker GMT offset in WINTER (verify, do not guess)
input bool              InpAutoGMTOffset     = true;  // Try to detect the offset at init (live only)
input int               InpRangeStartHH      = 19;    // Asian range start hour   (NY)
input int               InpRangeStartMM      = 0;     // Asian range start minute (NY)
input int               InpRangeEndHH        = 0;     // Asian range end hour     (NY, wraps midnight)
input int               InpRangeEndMM        = 0;     // Asian range end minute   (NY)
input int               InpTradeStartHH      = 2;     // Entry window start hour   (NY, covers London open)
input int               InpTradeStartMM      = 0;     // Entry window start minute (NY)
input int               InpTradeEndHH        = 11;    // Entry window end hour     (NY, covers NY AM)
input int               InpTradeEndMM        = 0;     // Entry window end minute   (NY)
input int               InpFlatHH            = 12;    // Force-flat hour   (NY)
input int               InpFlatMM            = 0;     // Force-flat minute (NY)
input bool              InpTradeMonday       = true;  // Monday
input bool              InpTradeTuesday      = true;  // Tuesday
input bool              InpTradeWednesday    = true;  // Wednesday
input bool              InpTradeThursday     = true;  // Thursday
input bool              InpTradeFriday       = true;  // Friday

input group             "===  3. SWEEP & STRUCTURE RULES  ==="
input double            InpSweepBufferPts    = 0;     // Points beyond the extreme to count as a sweep
input int               InpReclaimBars       = 6;     // Sweep must close back inside within N bars
input int               InpMSSFractalRight   = 2;     // Fractal confirmation bars for the MSS swing
input int               InpMSSLookback       = 40;    // Bars scanned for the MSS swing level
input int               InpMaxBarsToTrigger  = 60;    // Give up if no trigger within N entry bars
input int               InpFVGLookback       = 3;     // Bars scanned for the displacement FVG
input double            InpMinFVGPts         = 0;     // Minimum FVG height in points (0 = any)
input bool              InpRequireBodyClose  = true;  // Structure breaks must be BODY closes
input double            InpMinRangePts       = 0;     // Skip the day if the range is narrower than this
input double            InpMaxRangeATR       = 2.5;   // Skip the day if range > N x ATR — a wide
                                                      // overnight range is not a consolidation
input bool              InpUseMidnightOpen   = true;  // Require entry on the correct side of the NY midnight open

input group             "===  4. DIRECTIONAL BIAS — NOT optional here  ==="
input ENUM_I22_BIAS     InpBiasMode          = I22_BIAS_HTF_EMA;  // Bias filter
input ENUM_TIMEFRAMES   InpBiasTF            = PERIOD_H4;         // Bias timeframe
input int               InpBiasEMAPeriod     = 50;                // Bias EMA period
input bool              InpBiasBlocksCounter = true;              // Bias blocks counter-trend entries
input bool              InpRequireBias       = true;              // No bias, no trade

input group             "===  5. STOPS & TARGETS  ==="
input ENUM_I22_EXIT     InpExitMode          = I22_EXIT_FIXED_R;  // Exit management
input double            InpTargetR           = 2.0;   // Take profit in R multiples
input double            InpStopBufferPts     = 150;   // Points beyond the MSS swing (the 10-20 pip buffer)
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
input int               InpMaxTradesPerDay   = 1;     // One sweep per session; the second is revenge
input int               InpMaxConsecLosses   = 4;     // Halt for the session after N losses
input double            InpMaxSpreadPts      = 30;    // Reject an entry above this spread
input double            InpMaxSpreadVsStop   = 10.0;  // Reject if spread exceeds N% of the stop
input int               InpSlippagePts       = 20;    // Max deviation on market orders
input long              InpMagic             = 60222; // Magic number

input group             "===  7. FORENSIC JOURNAL  ==="
input bool              InpWriteJournal      = true;                  // Write the per-trade CSV
input string            InpJournalFile       = "I22_Sweep_journal.csv"; // File in MQL5/Files
input string            InpRunTag            = "asian_sweep_v1";      // CHANGE THIS EVERY RUN
input bool              InpShowDashboard     = true;                  // On-chart dashboard
input bool              InpDrawObjects       = true;                  // Draw the range lines

//====================================================================
//  STRATEGY STATE
//====================================================================
int      s_sweepSide      = 0;     // +1 swept the HIGH (look for shorts), -1 swept the LOW (look for longs)
double   s_sweepExtreme   = 0.0;   // the furthest price reached during the sweep
datetime s_sweepBarTime   = 0;
int      s_barsSinceSweep = 0;
bool     s_reclaimed      = false; // closed back inside the range after the sweep
int      s_barsSinceReclaim = 0;
bool     s_mssConfirmed   = false;
double   s_mssSwing       = 0.0;   // the swing the MSS broke — the structural stop reference
double   s_mssProtected   = 0.0;   // the extreme to stop behind
double   s_midnightOpen   = 0.0;
datetime s_lastEntryBar   = 0;

//+------------------------------------------------------------------+
void ResetSignalState()
  {
   s_sweepSide        = 0;
   s_sweepExtreme     = 0.0;
   s_sweepBarTime     = 0;
   s_barsSinceSweep   = 0;
   s_reclaimed        = false;
   s_barsSinceReclaim = 0;
   s_mssConfirmed     = false;
   s_mssSwing         = 0.0;
   s_mssProtected     = 0.0;
   s_midnightOpen     = 0.0;
  }

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

   g_cfg.tradeDay[0] = false;
   g_cfg.tradeDay[1] = InpTradeMonday;
   g_cfg.tradeDay[2] = InpTradeTuesday;
   g_cfg.tradeDay[3] = InpTradeWednesday;
   g_cfg.tradeDay[4] = InpTradeThursday;
   g_cfg.tradeDay[5] = InpTradeFriday;
   g_cfg.tradeDay[6] = false;

   g_cfg.rangeTF          = InpRangeTF;
   g_cfg.entryTF          = InpEntryTF;

   g_cfg.requireBodyClose = InpRequireBodyClose;
   g_cfg.breakBufferPts   = InpSweepBufferPts;
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
   g_cfg.strategyTag      = "ASIAN_SWEEP";
   g_cfg.modelTag         = EnumToString(InpModel);
   g_cfg.drawObjects      = InpDrawObjects;
   g_cfg.showDashboard    = InpShowDashboard;

   if(InpRiskPercent <= 0.0 || InpRiskPercent > 5.0)
     {
      Print("Isaiah 60:22 | risk percent must be between 0 and 5. Refusing to start.");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(InpRequireBias && InpBiasMode == I22_BIAS_OFF)
      Print("Isaiah 60:22 | WARNING: InpRequireBias is on but the bias filter is OFF. "
            "Every sweep will be tradeable in both directions, which is the premise this "
            "strategy does not have. Set a bias mode, or turn InpRequireBias off knowingly.");

   if(!I22_Init()) return INIT_FAILED;

   ResetSignalState();
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason) { I22_Deinit(); }

//====================================================================
//  STRUCTURE HELPERS
//====================================================================

//+------------------------------------------------------------------+
//| The NY midnight open — the opening price of the bar that starts   |
//| the NY trading day. It is the reference the source material uses  |
//| for entry placement, not merely the end of the Asian range.       |
//+------------------------------------------------------------------+
double MidnightOpen()
  {
   for(int i = 1; i < 600; i++)
     {
      datetime bt = iTime(_Symbol, g_cfg.entryTF, i);
      if(bt <= 0) break;
      if(NYDayKey(bt) != g_dayKey) continue;
      if(MinuteOfDayNY(bt) == 0) return iOpen(_Symbol, g_cfg.entryTF, i);
     }
   return 0.0;
  }

//+------------------------------------------------------------------+
//| Most recent confirmed swing high / low on the entry timeframe.    |
//| A swing needs InpMSSFractalRight bars on each side, so it is only |
//| confirmed that many bars after it printed.                        |
//+------------------------------------------------------------------+
bool FindSwing(const bool wantHigh, double &level, int &barIndex)
  {
   int n = InpMSSFractalRight;

   for(int i = 1 + n; i <= InpMSSLookback; i++)
     {
      double pivot = wantHigh ? iHigh(_Symbol, g_cfg.entryTF, i)
                              : iLow (_Symbol, g_cfg.entryTF, i);
      if(pivot <= 0.0) continue;

      bool ok = true;
      for(int k = 1; k <= n && ok; k++)
        {
         double l = wantHigh ? iHigh(_Symbol, g_cfg.entryTF, i + k)
                             : iLow (_Symbol, g_cfg.entryTF, i + k);
         double r = wantHigh ? iHigh(_Symbol, g_cfg.entryTF, i - k)
                             : iLow (_Symbol, g_cfg.entryTF, i - k);
         if(l <= 0.0 || r <= 0.0) { ok = false; break; }
         if(wantHigh) { if(l >= pivot || r >= pivot) ok = false; }
         else         { if(l <= pivot || r <= pivot) ok = false; }
        }

      if(ok)
        {
         level    = pivot;
         barIndex = i;
         return true;
        }
     }
   return false;
  }

//+------------------------------------------------------------------+
//| Market structure shift: after a sweep of the LOW we need price to |
//| break the most recent swing HIGH (and vice versa). That break is  |
//| the displacement that says the reversal has intent.               |
//+------------------------------------------------------------------+
bool DetectMSS(const int tradeDir, double &swingLevel, double &protectedExtreme)
  {
   double c = iClose(_Symbol, g_cfg.entryTF, 1);
   double h = iHigh (_Symbol, g_cfg.entryTF, 1);
   double l = iLow  (_Symbol, g_cfg.entryTF, 1);
   if(c <= 0.0) return false;

   double swing = 0.0;
   int    idx   = 0;

   if(tradeDir > 0)
     {
      if(!FindSwing(true, swing, idx)) return false;
      double test = g_cfg.requireBodyClose ? c : h;
      if(test <= swing) return false;

      // stop goes behind the low that formed on the way up to that swing
      double lowest = l;
      for(int i = 1; i <= idx; i++)
        {
         double li = iLow(_Symbol, g_cfg.entryTF, i);
         if(li > 0.0 && li < lowest) lowest = li;
        }
      swingLevel       = swing;
      protectedExtreme = lowest;
      return true;
     }

   if(!FindSwing(false, swing, idx)) return false;
   double test = g_cfg.requireBodyClose ? c : l;
   if(test >= swing) return false;

   double highest = h;
   for(int i = 1; i <= idx; i++)
     {
      double hi = iHigh(_Symbol, g_cfg.entryTF, i);
      if(hi > highest) highest = hi;
     }
   swingLevel       = swing;
   protectedExtreme = highest;
   return true;
  }

//+------------------------------------------------------------------+
//| Fair value gap in the displacement leg — the retracement entry.   |
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

      if(dir > 0 && l0 > h2 && (l0 - h2) >= minH) return l0;
      if(dir < 0 && h0 < l2 && (l2 - h0) >= minH) return h0;
     }
   return 0.0;
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

   if(!IsNewBar(g_cfg.entryTF, s_lastEntryBar))
     {
      DrawDashboard(SignalStateText());
      return;
     }

   if(s_midnightOpen == 0.0 && InpUseMidnightOpen) s_midnightOpen = MidnightOpen();

   if(s_sweepSide != 0)  s_barsSinceSweep++;
   if(s_reclaimed)       s_barsSinceReclaim++;

   string biasLbl;
   int bias = CurrentBias(biasLbl);

   double h = iHigh (_Symbol, g_cfg.entryTF, 1);
   double l = iLow  (_Symbol, g_cfg.entryTF, 1);
   double c = iClose(_Symbol, g_cfg.entryTF, 1);
   if(c <= 0.0) { DrawDashboard(SignalStateText()); return; }

   double buf = InpSweepBufferPts * Pt();

   //--- 1. detect the sweep
   if(s_sweepSide == 0)
     {
      if(h > g_rangeHigh + buf)
        {
         s_sweepSide      = 1;             // swept the high -> we are hunting SHORTS
         s_sweepExtreme   = h;
         s_sweepBarTime   = iTime(_Symbol, g_cfg.entryTF, 1);
         s_barsSinceSweep = 0;
         PrintFormat("Isaiah 60:22 | swept the Asian HIGH at %s (range high %s)",
                     DoubleToString(h, _Digits), DoubleToString(g_rangeHigh, _Digits));
        }
      else if(l < g_rangeLow - buf)
        {
         s_sweepSide      = -1;            // swept the low -> we are hunting LONGS
         s_sweepExtreme   = l;
         s_sweepBarTime   = iTime(_Symbol, g_cfg.entryTF, 1);
         s_barsSinceSweep = 0;
         PrintFormat("Isaiah 60:22 | swept the Asian LOW at %s (range low %s)",
                     DoubleToString(l, _Digits), DoubleToString(g_rangeLow, _Digits));
        }
     }
   else
     {
      // track how far the sweep ran while we wait for the reclaim
      if(s_sweepSide > 0 && h > s_sweepExtreme) s_sweepExtreme = h;
      if(s_sweepSide < 0 && l < s_sweepExtreme) s_sweepExtreme = l;
     }

   if(s_sweepSide == 0) { DrawDashboard(SignalStateText()); return; }

   int tradeDir = -s_sweepSide;   // sweep the high, trade short; sweep the low, trade long

   //--- 2. the reclaim. If price does not close back inside within
   //---    InpReclaimBars, this was not a sweep — it was a breakout,
   //---    and we are on the wrong side of it.
   if(!s_reclaimed)
     {
      bool backInside = (s_sweepSide > 0) ? (c < g_rangeHigh) : (c > g_rangeLow);
      if(backInside)
        {
         s_reclaimed        = true;
         s_barsSinceReclaim = 0;
         Print("Isaiah 60:22 | reclaimed the range — sweep confirmed");
        }
      else if(s_barsSinceSweep > InpReclaimBars)
        {
         PrintFormat("Isaiah 60:22 | no reclaim within %d bars — that was a breakout, not a sweep. Stand down.",
                     InpReclaimBars);
         ResetSignalState();
         DrawDashboard(SignalStateText());
         return;
        }
      if(!s_reclaimed) { DrawDashboard(SignalStateText()); return; }
     }

   // expiry
   if(g_cfg.maxBarsToTrigger > 0 && s_barsSinceSweep > g_cfg.maxBarsToTrigger)
     {
      Print("Isaiah 60:22 | setup expired without a trigger");
      ResetSignalState();
      DrawDashboard(SignalStateText());
      return;
     }

   //--- 3. bias. Direction cannot come from the sweep, so it has to come
   //---    from here. No bias, no trade.
   if(InpRequireBias && bias == 0)
     {
      DrawDashboard(SignalStateText() + "\n           waiting: no higher-timeframe bias");
      return;
     }
   if(g_cfg.biasBlocksCounter && bias != 0 && bias != tradeDir)
     {
      PrintFormat("Isaiah 60:22 | sweep of the %s ignored: bias is %s, the reversal would be %s",
                  (s_sweepSide > 0 ? "high" : "low"), biasLbl,
                  (tradeDir > 0 ? "long" : "short"));
      ResetSignalState();
      DrawDashboard(SignalStateText());
      return;
     }

   //--- 4. midnight-open filter. In a bullish setup you buy BELOW the
   //---    midnight open; in a bearish setup you sell ABOVE it.
   if(InpUseMidnightOpen && s_midnightOpen > 0.0)
     {
      double px = (tradeDir > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                                 : SymbolInfoDouble(_Symbol, SYMBOL_BID);
      bool okSide = (tradeDir > 0) ? (px < s_midnightOpen) : (px > s_midnightOpen);
      if(!okSide && InpModel != SWEEP_RANGE_CROSS)
        {
         DrawDashboard(SignalStateText() + "\n           waiting: wrong side of the midnight open");
         return;
        }
     }

   //--- 5. model-specific trigger
   bool   fire      = false;
   string trigger   = "";
   double stopPrice = 0.0;

   switch(InpModel)
     {
      case SWEEP_MSS:
        {
         if(!s_mssConfirmed)
           {
            double sw = 0.0, prot = 0.0;
            if(DetectMSS(tradeDir, sw, prot))
              {
               s_mssConfirmed = true;
               s_mssSwing     = sw;
               s_mssProtected = prot;
               PrintFormat("Isaiah 60:22 | market structure shift confirmed, swing %s",
                           DoubleToString(sw, _Digits));
              }
           }
         if(s_mssConfirmed)
           {
            fire      = true;
            trigger   = "sweep_mss";
            stopPrice = s_mssProtected;
           }
         break;
        }

      case SWEEP_MSS_FVG:
        {
         if(!s_mssConfirmed)
           {
            double sw = 0.0, prot = 0.0;
            if(DetectMSS(tradeDir, sw, prot))
              {
               s_mssConfirmed = true;
               s_mssSwing     = sw;
               s_mssProtected = prot;
               Print("Isaiah 60:22 | MSS confirmed, waiting for the retracement into the FVG");
              }
           }
         else
           {
            double fvg = FindFVG(tradeDir);
            if(fvg > 0.0)
              {
               double px = (tradeDir > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                                          : SymbolInfoDouble(_Symbol, SYMBOL_BID);
               if((tradeDir > 0 && px <= fvg) || (tradeDir < 0 && px >= fvg))
                 {
                  fire      = true;
                  trigger   = "sweep_mss_fvg";
                  stopPrice = s_mssProtected;
                 }
              }
           }
         break;
        }

      case SWEEP_RECLAIM:
         // Deliberately weaker: no MSS. Included so you can measure what the
         // MSS filter is actually worth on your instrument.
         fire      = true;
         trigger   = "sweep_reclaim_only";
         stopPrice = s_sweepExtreme;
         break;

      case SWEEP_RANGE_CROSS:
        {
         // Entry option (II) in the source: after the sweep, trade the close
         // through the OPPOSITE boundary.
         bool crossed = (tradeDir > 0) ? (c > g_rangeHigh) : (c < g_rangeLow);
         if(crossed)
           {
            fire      = true;
            trigger   = "range_cross";
            stopPrice = s_sweepExtreme;
           }
         break;
        }
     }

   if(fire)
     {
      if(OpenPosition(tradeDir, stopPrice, trigger))
         ResetSignalState();
     }

   DrawDashboard(SignalStateText());
  }

//+------------------------------------------------------------------+
string SignalStateText()
  {
   if(s_sweepSide == 0) return "signal     no sweep yet";

   string s = StringFormat("signal     swept the %s %d bars ago",
                           (s_sweepSide > 0 ? "HIGH" : "LOW"), s_barsSinceSweep);
   s += s_reclaimed ? "  [reclaimed]" : "  [waiting for reclaim]";
   if(s_mssConfirmed) s += "  [MSS]";
   if(s_midnightOpen > 0.0)
      s += "\n           midnight open " + DoubleToString(s_midnightOpen, _Digits);
   return s;
  }
//+------------------------------------------------------------------+
