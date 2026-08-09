//+------------------------------------------------------------------+
//|  Isaiah6022_Core.mqh                                             |
//|  Shared engine for the Isaiah 60:22 session-range EAs.           |
//|                                                                  |
//|  Contains: New York clock with the real US DST rule, range       |
//|  builder, risk kernel, position manager, and a forensic journal  |
//|  whose CSV schema is byte-compatible with srf_forensics.py.      |
//|                                                                  |
//|  Install: MQL5/Include/Isaiah6022_Core.mqh                       |
//+------------------------------------------------------------------+
#property copyright "Isaiah 60:22"
#property version   "1.00"

#include <Trade\Trade.mqh>

//====================================================================
//  ENUMS
//====================================================================
enum ENUM_I22_BIAS
  {
   I22_BIAS_OFF,            // No directional filter
   I22_BIAS_HTF_EMA,        // Higher timeframe EMA side + slope
   I22_BIAS_PREV_DAY,       // Position vs previous day's range midpoint
   I22_BIAS_RANGE_CANDLE    // Direction of the range-forming candle
  };

enum ENUM_I22_EXIT
  {
   I22_EXIT_FIXED_R,        // Fixed R multiple take profit
   I22_EXIT_TIME_ONLY,      // Stop only, hold to the force-flat time
   I22_EXIT_R_THEN_TIME,    // Fixed R target, else flatten at session end
   I22_EXIT_ATR_TRAIL       // ATR trailing stop, flatten at session end
  };

//====================================================================
//  CONFIG — filled by the EA in OnInit
//====================================================================
struct I22Config
  {
   // clock (all New York local)
   double            brokerGMTOffset;   // broker's WINTER offset from GMT
   bool              autoGMTOffset;
   int               rangeStartMin;     // minutes from NY midnight
   int               rangeEndMin;
   int               tradeStartMin;
   int               tradeEndMin;
   int               flatMin;
   bool              rangeWraps;        // range window crosses midnight
   bool              tradeDay[7];       // index by DayOfWeek, 0 = Sunday

   // timeframes
   ENUM_TIMEFRAMES   rangeTF;
   ENUM_TIMEFRAMES   entryTF;

   // signal
   bool              requireBodyClose;
   double            breakBufferPts;
   int               maxBarsToTrigger;
   double            minRangePts;
   double            maxRangeATR;

   // bias
   ENUM_I22_BIAS     biasMode;
   ENUM_TIMEFRAMES   biasTF;
   int               biasEMAPeriod;
   bool              biasBlocksCounter;

   // stops and targets
   ENUM_I22_EXIT     exitMode;
   double            targetR;
   double            stopBufferPts;
   int               atrPeriod;
   double            minStopATR;
   double            maxStopATR;
   double            breakevenAtR;
   double            partialAtR;
   double            partialPercent;
   double            atrTrailMult;

   // risk kernel
   double            riskPercent;
   double            maxDailyLossPct;
   double            maxTotalDDPct;
   int               maxTradesPerDay;
   int               maxConsecLosses;
   double            maxSpreadPts;
   double            maxSpreadVsStop;
   int               slippagePts;
   long              magic;

   // journal
   bool              writeJournal;
   string            journalFile;
   string            runTag;
   string            strategyTag;
   string            modelTag;
   bool              drawObjects;
   bool              showDashboard;
  };

//====================================================================
//  STATE
//====================================================================
CTrade   g_trade;

I22Config g_cfg;

int      g_atrHandle    = INVALID_HANDLE;
int      g_biasHandle   = INVALID_HANDLE;
double   g_gmtOffset    = 0.0;

// session
string   g_dayKey       = "";
double   g_rangeHigh    = 0.0;
double   g_rangeLow     = 0.0;
bool     g_rangeReady   = false;
double   g_rangeATR     = 0.0;
int      g_rangeDir     = 0;      // direction of the range-forming candle
int      g_tradesToday  = 0;
int      g_consecLosses = 0;
double   g_dayStartEq   = 0.0;
double   g_peakEquity   = 0.0;
bool     g_haltedToday  = false;
bool     g_haltedTotal  = false;
bool     g_daySkipped   = false;
string   g_skipReason   = "";

// live position
ulong    g_ticket       = 0;
int      g_posDir       = 0;
double   g_entryPrice   = 0.0;
double   g_initialSL    = 0.0;
double   g_initialTP    = 0.0;
double   g_riskPoints   = 0.0;
double   g_entrySpread  = 0.0;
double   g_entryLots    = 0.0;
datetime g_entryTime    = 0;
int      g_entryBarCount= 0;
double   g_mfePts       = 0.0;
double   g_maePts       = 0.0;
string   g_biasAtEntry  = "OFF";
string   g_entryDayKey  = "";
bool     g_bePlaced     = false;
bool     g_partialDone  = false;

datetime g_lastEntryBar = 0;

//====================================================================
//  PRIMITIVES
//====================================================================
double Pt()      { return SymbolInfoDouble(_Symbol, SYMBOL_POINT); }
double SpreadPts(){ return (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD); }

double NormPrice(const double p)
  {
   return NormalizeDouble(p, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
  }

//+------------------------------------------------------------------+
//| Value of one point of price movement, for one lot, in account ccy |
//+------------------------------------------------------------------+
double PointValuePerLot()
  {
   double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickSize <= 0.0) return 0.0;
   return tickVal * (Pt() / tickSize);
  }

//====================================================================
//  NEW YORK CLOCK
//  Every window in this workspace is New York local. That is NOT a
//  fixed GMT offset: EDT runs from the 2nd Sunday in March to the
//  1st Sunday in November. A fixed-offset conversion trades the wrong
//  window for roughly eight months of every year.
//====================================================================

//--- nth given weekday of a month, as a date at 00:00 UTC
datetime NthWeekdayOfMonth(const int year, const int month, const int weekday, const int nth)
  {
   MqlDateTime t;
   t.year = year; t.mon = month; t.day = 1;
   t.hour = 0;    t.min = 0;     t.sec = 0;
   datetime first = StructToTime(t);

   MqlDateTime f;
   TimeToStruct(first, f);
   int delta = (weekday - f.day_of_week + 7) % 7;
   return first + (datetime)((delta + (nth - 1) * 7) * 86400);
  }

//--- true when the given UTC instant falls inside US Eastern Daylight Time
bool IsUSDaylightTime(const datetime utc)
  {
   MqlDateTime t;
   TimeToStruct(utc, t);

   // DST begins 2nd Sunday March at 02:00 local standard (07:00 UTC)
   datetime dstStart = NthWeekdayOfMonth(t.year, 3, 0, 2) + 7 * 3600;
   // DST ends 1st Sunday November at 02:00 local daylight (06:00 UTC)
   datetime dstEnd   = NthWeekdayOfMonth(t.year, 11, 0, 1) + 6 * 3600;

   return (utc >= dstStart && utc < dstEnd);
  }

//--- convert broker server time to New York local time
datetime BrokerToNY(const datetime brokerTime)
  {
   datetime utc = brokerTime - (datetime)(int)(g_gmtOffset * 3600.0);
   int nyOffset = IsUSDaylightTime(utc) ? -4 : -5;
   return utc + (datetime)(nyOffset * 3600);
  }

datetime NowNY() { return BrokerToNY(TimeCurrent()); }

int MinuteOfDayNY(const datetime brokerTime)
  {
   MqlDateTime t;
   TimeToStruct(BrokerToNY(brokerTime), t);
   return t.hour * 60 + t.min;
  }

string NYDayKey(const datetime brokerTime)
  {
   MqlDateTime t;
   TimeToStruct(BrokerToNY(brokerTime), t);
   return StringFormat("%04d-%02d-%02d", t.year, t.mon, t.day);
  }

string NYStamp(const datetime brokerTime)
  {
   MqlDateTime t;
   TimeToStruct(BrokerToNY(brokerTime), t);
   return StringFormat("%04d-%02d-%02d %02d:%02d:%02d",
                       t.year, t.mon, t.day, t.hour, t.min, t.sec);
  }

int NYDayOfWeek(const datetime brokerTime)
  {
   MqlDateTime t;
   TimeToStruct(BrokerToNY(brokerTime), t);
   return t.day_of_week;
  }

//--- inclusive-start, exclusive-end window test that tolerates midnight wrap
bool InWindow(const int nowMin, const int startMin, const int endMin)
  {
   if(startMin == endMin) return false;
   if(startMin < endMin)  return (nowMin >= startMin && nowMin < endMin);
   return (nowMin >= startMin || nowMin < endMin);   // wraps midnight
  }

//--- the NY day a wrapping range belongs to: 19:00-00:00 forms the range
//--- for the session that follows it, so pre-midnight bars key to tomorrow
string RangeDayKey(const datetime brokerTime)
  {
   if(!g_cfg.rangeWraps) return NYDayKey(brokerTime);
   int m = MinuteOfDayNY(brokerTime);
   if(m >= g_cfg.rangeStartMin) return NYDayKey(brokerTime + 86400);
   return NYDayKey(brokerTime);
  }

//+------------------------------------------------------------------+
//| Best-effort broker GMT offset detection. Live only — in the       |
//| Strategy Tester this returns the configured value untouched.      |
//+------------------------------------------------------------------+
void ResolveGMTOffset()
  {
   g_gmtOffset = g_cfg.brokerGMTOffset;

   if(!g_cfg.autoGMTOffset)          return;
   if(MQLInfoInteger(MQL_TESTER))    return;

   datetime srv = TimeCurrent();
   datetime gmt = TimeGMT();
   if(srv <= 0 || gmt <= 0) return;

   double detected = (double)(srv - gmt) / 3600.0;
   detected = MathRound(detected * 2.0) / 2.0;      // nearest half hour

   // strip the broker's own summer time so the stored value is the winter one
   if(IsUSDaylightTime(gmt)) detected -= 1.0;

   if(MathAbs(detected) <= 14.0)
     {
      if(MathAbs(detected - g_cfg.brokerGMTOffset) > 0.25)
         PrintFormat("Isaiah 60:22 | broker GMT offset detected as %.1f, input said %.1f. Using detected.",
                     detected, g_cfg.brokerGMTOffset);
      g_gmtOffset = detected;
     }
  }

//====================================================================
//  INDICATORS
//====================================================================
bool InitIndicators()
  {
   g_atrHandle = iATR(_Symbol, g_cfg.rangeTF, g_cfg.atrPeriod);
   if(g_atrHandle == INVALID_HANDLE)
     {
      Print("Isaiah 60:22 | failed to create ATR handle");
      return false;
     }

   if(g_cfg.biasMode == I22_BIAS_HTF_EMA)
     {
      g_biasHandle = iMA(_Symbol, g_cfg.biasTF, g_cfg.biasEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
      if(g_biasHandle == INVALID_HANDLE)
        {
         Print("Isaiah 60:22 | failed to create bias EMA handle");
         return false;
        }
     }
   return true;
  }

void ReleaseIndicators()
  {
   if(g_atrHandle  != INVALID_HANDLE) IndicatorRelease(g_atrHandle);
   if(g_biasHandle != INVALID_HANDLE) IndicatorRelease(g_biasHandle);
  }

double ATRValue()
  {
   double buf[];
   if(CopyBuffer(g_atrHandle, 0, 1, 1, buf) != 1) return 0.0;
   return buf[0];
  }

//====================================================================
//  DIRECTIONAL BIAS
//  Returns +1 long-only, -1 short-only, 0 no opinion.
//====================================================================
int CurrentBias(string &label)
  {
   label = "OFF";

   switch(g_cfg.biasMode)
     {
      case I22_BIAS_OFF:
         return 0;

      case I22_BIAS_HTF_EMA:
        {
         double ema[];
         if(CopyBuffer(g_biasHandle, 0, 1, 2, ema) != 2) { label = "NA"; return 0; }
         double close1 = iClose(_Symbol, g_cfg.biasTF, 1);
         if(close1 <= 0.0) { label = "NA"; return 0; }

         bool up   = (close1 > ema[1] && ema[1] >= ema[0]);
         bool down = (close1 < ema[1] && ema[1] <= ema[0]);
         if(up)   { label = "BULL"; return  1; }
         if(down) { label = "BEAR"; return -1; }
         label = "FLAT";
         return 0;
        }

      case I22_BIAS_PREV_DAY:
        {
         double ph = iHigh(_Symbol, PERIOD_D1, 1);
         double pl = iLow (_Symbol, PERIOD_D1, 1);
         if(ph <= 0.0 || pl <= 0.0 || ph <= pl) { label = "NA"; return 0; }
         double mid = (ph + pl) / 2.0;
         double px  = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         if(px > mid) { label = "BULL"; return  1; }
         if(px < mid) { label = "BEAR"; return -1; }
         label = "FLAT";
         return 0;
        }

      case I22_BIAS_RANGE_CANDLE:
        {
         if(g_rangeDir > 0) { label = "BULL"; return  1; }
         if(g_rangeDir < 0) { label = "BEAR"; return -1; }
         label = "FLAT";
         return 0;
        }
     }
   return 0;
  }

//====================================================================
//  SESSION / RANGE
//====================================================================
void ResetSession(const string newKey)
  {
   g_dayKey      = newKey;
   g_rangeHigh   = 0.0;
   g_rangeLow    = 0.0;
   g_rangeReady  = false;
   g_rangeATR    = 0.0;
   g_rangeDir    = 0;
   g_tradesToday = 0;
   g_haltedToday = false;
   g_daySkipped  = false;
   g_skipReason  = "";
   g_dayStartEq  = AccountInfoDouble(ACCOUNT_EQUITY);
   g_lastEntryBar= 0;

   if(g_cfg.drawObjects)
     {
      ObjectDelete(0, "I22_RangeHigh");
      ObjectDelete(0, "I22_RangeLow");
     }
  }

//+------------------------------------------------------------------+
//| Build the reference range from closed bars inside the window.     |
//| Called on every new range-timeframe bar.                          |
//+------------------------------------------------------------------+
void UpdateRange()
  {
   static datetime lastCounted = 0;

   datetime barTime = iTime(_Symbol, g_cfg.rangeTF, 1);
   if(barTime <= 0 || barTime == lastCounted) return;   // one pass per closed bar
   lastCounted = barTime;

   int m = MinuteOfDayNY(barTime);
   if(!InWindow(m, g_cfg.rangeStartMin, g_cfg.rangeEndMin)) return;

   string key = RangeDayKey(barTime);
   if(key != g_dayKey) return;          // belongs to a different session

   double h = iHigh (_Symbol, g_cfg.rangeTF, 1);
   double l = iLow  (_Symbol, g_cfg.rangeTF, 1);
   double o = iOpen (_Symbol, g_cfg.rangeTF, 1);
   double c = iClose(_Symbol, g_cfg.rangeTF, 1);
   if(h <= 0.0 || l <= 0.0) return;

   if(g_rangeHigh == 0.0 || h > g_rangeHigh) g_rangeHigh = h;
   if(g_rangeLow  == 0.0 || l < g_rangeLow ) g_rangeLow  = l;

   if(c > o)      g_rangeDir =  1;
   else if(c < o) g_rangeDir = -1;
  }

//+------------------------------------------------------------------+
//| Close the range once the formation window has passed, and decide  |
//| whether the session is tradeable at all.                          |
//+------------------------------------------------------------------+
void FinaliseRange()
  {
   if(g_rangeReady || g_rangeHigh <= 0.0 || g_rangeLow <= 0.0) return;

   g_rangeReady = true;
   g_rangeATR   = ATRValue();

   double rangePts = (g_rangeHigh - g_rangeLow) / Pt();
   double atrPts   = (g_rangeATR > 0.0) ? g_rangeATR / Pt() : 0.0;

   if(g_cfg.minRangePts > 0.0 && rangePts < g_cfg.minRangePts)
     {
      g_daySkipped = true;
      g_skipReason = StringFormat("range %.0f pts < min %.0f", rangePts, g_cfg.minRangePts);
     }
   else if(g_cfg.maxRangeATR > 0.0 && atrPts > 0.0 && rangePts > g_cfg.maxRangeATR * atrPts)
     {
      g_daySkipped = true;
      g_skipReason = StringFormat("range %.1f x ATR > max %.1f", rangePts / atrPts, g_cfg.maxRangeATR);
     }

   if(g_cfg.drawObjects)
     {
      ObjectCreate(0, "I22_RangeHigh", OBJ_HLINE, 0, 0, g_rangeHigh);
      ObjectSetInteger(0, "I22_RangeHigh", OBJPROP_COLOR, clrDodgerBlue);
      ObjectSetInteger(0, "I22_RangeHigh", OBJPROP_STYLE, STYLE_DOT);
      ObjectCreate(0, "I22_RangeLow", OBJ_HLINE, 0, 0, g_rangeLow);
      ObjectSetInteger(0, "I22_RangeLow", OBJPROP_COLOR, clrOrangeRed);
      ObjectSetInteger(0, "I22_RangeLow", OBJPROP_STYLE, STYLE_DOT);
     }

   PrintFormat("Isaiah 60:22 | %s range set  H=%s L=%s  (%.0f pts, %.2f x ATR)%s",
               g_dayKey, DoubleToString(g_rangeHigh, _Digits), DoubleToString(g_rangeLow, _Digits),
               rangePts, (atrPts > 0.0 ? rangePts / atrPts : 0.0),
               (g_daySkipped ? "  SKIPPED: " + g_skipReason : ""));
  }

//====================================================================
//  RISK KERNEL
//====================================================================

//--- hard stops that end the day, or the account
bool RiskKernelBlocks()
  {
   if(g_haltedTotal) return true;

   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq > g_peakEquity) g_peakEquity = eq;

   if(g_cfg.maxTotalDDPct > 0.0 && g_peakEquity > 0.0)
     {
      double dd = (g_peakEquity - eq) / g_peakEquity * 100.0;
      if(dd >= g_cfg.maxTotalDDPct)
        {
         g_haltedTotal = true;
         PrintFormat("Isaiah 60:22 | HALT (permanent): drawdown %.2f%% >= %.2f%%", dd, g_cfg.maxTotalDDPct);
         return true;
        }
     }

   if(g_haltedToday) return true;

   if(g_cfg.maxDailyLossPct > 0.0 && g_dayStartEq > 0.0)
     {
      double dayLoss = (g_dayStartEq - eq) / g_dayStartEq * 100.0;
      if(dayLoss >= g_cfg.maxDailyLossPct)
        {
         g_haltedToday = true;
         PrintFormat("Isaiah 60:22 | HALT (today): session loss %.2f%% >= %.2f%%", dayLoss, g_cfg.maxDailyLossPct);
         return true;
        }
     }

   if(g_cfg.maxConsecLosses > 0 && g_consecLosses >= g_cfg.maxConsecLosses)
     {
      g_haltedToday = true;
      PrintFormat("Isaiah 60:22 | HALT (today): %d consecutive losses", g_consecLosses);
      return true;
     }

   if(g_cfg.maxTradesPerDay > 0 && g_tradesToday >= g_cfg.maxTradesPerDay)
      return true;

   return false;
  }

//--- position size from risk percent and the structural stop distance
double LotsForRisk(const double stopPoints)
  {
   if(stopPoints <= 0.0) return 0.0;

   double pvPerLot = PointValuePerLot();
   if(pvPerLot <= 0.0) return 0.0;

   double riskMoney = AccountInfoDouble(ACCOUNT_EQUITY) * g_cfg.riskPercent / 100.0;
   double lots      = riskMoney / (stopPoints * pvPerLot);

   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double stepLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(stepLot <= 0.0) stepLot = 0.01;

   lots = MathFloor(lots / stepLot) * stepLot;
   lots = MathMax(lots, 0.0);
   lots = MathMin(lots, maxLot);

   // Refuse to round UP to the broker minimum. If one minimum lot risks
   // more than the configured percent, the correct action is no trade.
   if(lots < minLot) return 0.0;

   return NormalizeDouble(lots, 2);
  }

//--- clamp a structural stop into the ATR band, return distance in points
double ClampStopPoints(double stopPoints)
  {
   double atrPts = (g_rangeATR > 0.0) ? g_rangeATR / Pt() : 0.0;
   if(atrPts <= 0.0) return stopPoints;

   if(g_cfg.minStopATR > 0.0) stopPoints = MathMax(stopPoints, g_cfg.minStopATR * atrPts);
   if(g_cfg.maxStopATR > 0.0 && stopPoints > g_cfg.maxStopATR * atrPts) return -1.0;  // reject
   return stopPoints;
  }

//--- spread gates, checked at the moment of entry
bool SpreadBlocks(const double stopPoints, string &why)
  {
   double sp = SpreadPts();

   if(g_cfg.maxSpreadPts > 0.0 && sp > g_cfg.maxSpreadPts)
     {
      why = StringFormat("spread %.0f > max %.0f pts", sp, g_cfg.maxSpreadPts);
      return true;
     }
   if(g_cfg.maxSpreadVsStop > 0.0 && stopPoints > 0.0)
     {
      double pct = sp / stopPoints * 100.0;
      if(pct > g_cfg.maxSpreadVsStop)
        {
         why = StringFormat("spread is %.1f%% of the stop, max %.1f%%", pct, g_cfg.maxSpreadVsStop);
         return true;
        }
     }
   return false;
  }

//====================================================================
//  JOURNAL
//  Schema is identical to GODMODE_SessionRange_Forge so the same
//  srf_forensics.py grades output from every EA in this workspace.
//====================================================================
void EnsureJournalHeader()
  {
   if(!g_cfg.writeJournal) return;
   if(FileIsExist(g_cfg.journalFile)) return;

   int h = FileOpen(g_cfg.journalFile, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(h == INVALID_HANDLE)
     {
      PrintFormat("Isaiah 60:22 | cannot open journal %s (error %d)", g_cfg.journalFile, GetLastError());
      return;
     }
   FileWrite(h,
             "run_tag", "symbol", "preset", "model", "ticket", "direction",
             "ny_day", "entry_time_ny", "exit_time_ny",
             "entry_price", "exit_price", "sl_price", "tp_price",
             "risk_points", "r_realized", "mfe_r", "mae_r",
             "spread_pts_entry", "range_high", "range_low", "range_pts",
             "atr_pts", "range_atr_ratio", "bias", "lots",
             "profit_ccy", "balance_after", "bars_held", "exit_reason");
   FileClose(h);
  }

void WriteJournalRow(const double exitPrice, const datetime exitTime,
                     const double profit, const string reason)
  {
   if(!g_cfg.writeJournal) return;

   int h = FileOpen(g_cfg.journalFile, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(h == INVALID_HANDLE) return;
   FileSeek(h, 0, SEEK_END);

   double movePts = (g_posDir > 0) ? (exitPrice - g_entryPrice) / Pt()
                                   : (g_entryPrice - exitPrice) / Pt();
   double rReal    = (g_riskPoints > 0.0) ? movePts / g_riskPoints : 0.0;
   double mfeR     = (g_riskPoints > 0.0) ? g_mfePts / g_riskPoints : 0.0;
   double maeR     = (g_riskPoints > 0.0) ? g_maePts / g_riskPoints : 0.0;
   double rangePts = (g_rangeHigh > g_rangeLow) ? (g_rangeHigh - g_rangeLow) / Pt() : 0.0;
   double atrPts   = (g_rangeATR > 0.0) ? g_rangeATR / Pt() : 0.0;
   double ratio    = (atrPts > 0.0) ? rangePts / atrPts : 0.0;
   int    bars     = Bars(_Symbol, g_cfg.entryTF) - g_entryBarCount;

   FileWrite(h,
             g_cfg.runTag, _Symbol, g_cfg.strategyTag, g_cfg.modelTag,
             IntegerToString((long)g_ticket), (g_posDir > 0 ? "LONG" : "SHORT"),
             g_entryDayKey, NYStamp(g_entryTime), NYStamp(exitTime),
             DoubleToString(g_entryPrice, _Digits), DoubleToString(exitPrice, _Digits),
             DoubleToString(g_initialSL, _Digits), DoubleToString(g_initialTP, _Digits),
             DoubleToString(g_riskPoints, 1), DoubleToString(rReal, 4),
             DoubleToString(mfeR, 4), DoubleToString(maeR, 4),
             DoubleToString(g_entrySpread, 1),
             DoubleToString(g_rangeHigh, _Digits), DoubleToString(g_rangeLow, _Digits),
             DoubleToString(rangePts, 1), DoubleToString(atrPts, 1),
             DoubleToString(ratio, 3), g_biasAtEntry,
             DoubleToString(g_entryLots, 2), DoubleToString(profit, 2),
             DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2),
             IntegerToString(bars), reason);
   FileClose(h);
  }

//====================================================================
//  ORDER PLACEMENT
//====================================================================

//+------------------------------------------------------------------+
//| Open a position. stopPrice is the structural invalidation level;  |
//| the target is derived from it by the configured R multiple.       |
//| Returns true if an order actually went in.                        |
//+------------------------------------------------------------------+
bool OpenPosition(const int dir, double stopPrice, const string trigger)
  {
   if(dir == 0) return false;
   if(PositionSelectByTicket(g_ticket)) return false;    // already in

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = (dir > 0) ? ask : bid;

   // widen the raw structural stop by the configured buffer
   double buffer = g_cfg.stopBufferPts * Pt();
   stopPrice = (dir > 0) ? stopPrice - buffer : stopPrice + buffer;

   double stopPoints = MathAbs(entry - stopPrice) / Pt();
   stopPoints = ClampStopPoints(stopPoints);
   if(stopPoints <= 0.0)
     {
      PrintFormat("Isaiah 60:22 | entry rejected: stop outside the ATR band");
      return false;
     }

   string why = "";
   if(SpreadBlocks(stopPoints, why))
     {
      PrintFormat("Isaiah 60:22 | entry rejected: %s", why);
      return false;
     }

   double lots = LotsForRisk(stopPoints);
   if(lots <= 0.0)
     {
      Print("Isaiah 60:22 | entry rejected: one minimum lot exceeds the configured risk");
      return false;
     }

   // recompute the stop price from the clamped distance so SL and size agree
   double sl = (dir > 0) ? entry - stopPoints * Pt() : entry + stopPoints * Pt();
   double tp = 0.0;
   if(g_cfg.exitMode == I22_EXIT_FIXED_R || g_cfg.exitMode == I22_EXIT_R_THEN_TIME)
      tp = (dir > 0) ? entry + stopPoints * g_cfg.targetR * Pt()
                     : entry - stopPoints * g_cfg.targetR * Pt();

   sl = NormPrice(sl);
   tp = (tp > 0.0) ? NormPrice(tp) : 0.0;

   g_trade.SetExpertMagicNumber(g_cfg.magic);
   g_trade.SetDeviationInPoints(g_cfg.slippagePts);

   bool ok = (dir > 0) ? g_trade.Buy (lots, _Symbol, 0.0, sl, tp, trigger)
                       : g_trade.Sell(lots, _Symbol, 0.0, sl, tp, trigger);
   if(!ok)
     {
      PrintFormat("Isaiah 60:22 | order failed: retcode %d %s",
                  g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
      return false;
     }

   g_ticket        = g_trade.ResultOrder();
   if(g_ticket == 0) g_ticket = g_trade.ResultDeal();

   g_posDir        = dir;
   g_entryPrice    = (g_trade.ResultPrice() > 0.0) ? g_trade.ResultPrice() : entry;
   g_initialSL     = sl;
   g_initialTP     = tp;
   g_riskPoints    = stopPoints;
   g_entrySpread   = SpreadPts();
   g_entryLots     = lots;
   g_entryTime     = TimeCurrent();
   g_entryDayKey   = g_dayKey;
   g_entryBarCount = Bars(_Symbol, g_cfg.entryTF);
   g_mfePts        = 0.0;
   g_maePts        = 0.0;
   g_bePlaced      = false;
   g_partialDone   = false;
   g_tradesToday++;

   string lbl;
   CurrentBias(lbl);
   g_biasAtEntry = lbl;

   PrintFormat("Isaiah 60:22 | %s %s  %.2f lots @ %s  SL %s  TP %s  risk %.0f pts  [%s]",
               g_cfg.strategyTag, (dir > 0 ? "LONG" : "SHORT"), lots,
               DoubleToString(g_entryPrice, _Digits), DoubleToString(sl, _Digits),
               (tp > 0.0 ? DoubleToString(tp, _Digits) : "none"), stopPoints, trigger);
   return true;
  }

//====================================================================
//  POSITION MANAGEMENT
//====================================================================
void TrackExcursion()
  {
   if(!PositionSelectByTicket(g_ticket)) return;

   double px   = (g_posDir > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                                : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double move = (g_posDir > 0) ? (px - g_entryPrice) / Pt()
                                : (g_entryPrice - px) / Pt();

   if(move > g_mfePts)  g_mfePts = move;
   if(-move > g_maePts) g_maePts = -move;
  }

void ManagePosition()
  {
   if(!PositionSelectByTicket(g_ticket)) return;

   double px = (g_posDir > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                              : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double rNow = (g_riskPoints > 0.0)
                 ? ((g_posDir > 0) ? (px - g_entryPrice) : (g_entryPrice - px)) / Pt() / g_riskPoints
                 : 0.0;

   double curSL = PositionGetDouble(POSITION_SL);
   double curTP = PositionGetDouble(POSITION_TP);

   // partial close
   if(!g_partialDone && g_cfg.partialAtR > 0.0 && rNow >= g_cfg.partialAtR)
     {
      double vol   = PositionGetDouble(POSITION_VOLUME);
      double step  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
      double minv  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      if(step <= 0.0) step = 0.01;

      double part = MathFloor((vol * g_cfg.partialPercent / 100.0) / step) * step;
      if(part >= minv && (vol - part) >= minv)
        {
         if(g_trade.PositionClosePartial(g_ticket, NormalizeDouble(part, 2)))
            PrintFormat("Isaiah 60:22 | partial %.2f lots closed at %.2fR", part, rNow);
        }
      g_partialDone = true;   // attempt once, whether or not it was possible
     }

   // break-even
   if(!g_bePlaced && g_cfg.breakevenAtR > 0.0 && rNow >= g_cfg.breakevenAtR)
     {
      double be = NormPrice(g_entryPrice);
      bool improves = (g_posDir > 0) ? (be > curSL) : (be < curSL || curSL == 0.0);
      if(improves && g_trade.PositionModify(g_ticket, be, curTP))
        {
         g_bePlaced = true;
         PrintFormat("Isaiah 60:22 | stop moved to break-even at %.2fR", rNow);
        }
      else g_bePlaced = true;
     }

   // ATR trail
   if(g_cfg.exitMode == I22_EXIT_ATR_TRAIL)
     {
      double atr = ATRValue();
      if(atr > 0.0)
        {
         double trail = (g_posDir > 0) ? px - g_cfg.atrTrailMult * atr
                                       : px + g_cfg.atrTrailMult * atr;
         trail = NormPrice(trail);
         bool improves = (g_posDir > 0) ? (trail > curSL) : (trail < curSL || curSL == 0.0);
         if(improves) g_trade.PositionModify(g_ticket, trail, curTP);
        }
     }
  }

//--- close everything this EA owns
void FlattenAll(const string reason)
  {
   if(PositionSelectByTicket(g_ticket))
     {
      g_trade.SetExpertMagicNumber(g_cfg.magic);
      if(g_trade.PositionClose(g_ticket))
         PrintFormat("Isaiah 60:22 | flattened: %s", reason);
     }
  }

//+------------------------------------------------------------------+
//| Detect that our tracked position has closed, and journal it.      |
//| Called every tick; cheap when there is nothing to do.             |
//+------------------------------------------------------------------+
void ReconcileClosedPosition()
  {
   if(g_ticket == 0) return;
   if(PositionSelectByTicket(g_ticket)) return;    // still open

   if(!HistorySelect(g_entryTime - 60, TimeCurrent() + 60))
     {
      g_ticket = 0;
      return;
     }

   double exitPrice = 0.0, profit = 0.0;
   datetime exitTime = TimeCurrent();
   string   reason   = "closed";
   bool     found    = false;

   int deals = HistoryDealsTotal();
   for(int i = deals - 1; i >= 0; i--)
     {
      ulong dealTicket = HistoryDealGetTicket(i);
      if(dealTicket == 0) continue;
      if(HistoryDealGetInteger(dealTicket, DEAL_MAGIC) != g_cfg.magic) continue;
      if(HistoryDealGetInteger(dealTicket, DEAL_ENTRY) != DEAL_ENTRY_OUT) continue;
      if(HistoryDealGetInteger(dealTicket, DEAL_POSITION_ID) != (long)g_ticket) continue;

      exitPrice = HistoryDealGetDouble(dealTicket, DEAL_PRICE);
      exitTime  = (datetime)HistoryDealGetInteger(dealTicket, DEAL_TIME);
      profit   += HistoryDealGetDouble(dealTicket, DEAL_PROFIT)
                + HistoryDealGetDouble(dealTicket, DEAL_SWAP)
                + HistoryDealGetDouble(dealTicket, DEAL_COMMISSION);

      ENUM_DEAL_REASON dr = (ENUM_DEAL_REASON)HistoryDealGetInteger(dealTicket, DEAL_REASON);
      if(dr == DEAL_REASON_SL)      reason = "stop_loss";
      else if(dr == DEAL_REASON_TP) reason = "take_profit";
      else                          reason = "manual_or_time";
      found = true;
      break;
     }

   if(found)
     {
      WriteJournalRow(exitPrice, exitTime, profit, reason);
      if(profit < 0.0) g_consecLosses++;
      else             g_consecLosses = 0;

      PrintFormat("Isaiah 60:22 | closed %s  %.2f  (%s)  MFE %.2fR  MAE %.2fR",
                  (g_posDir > 0 ? "LONG" : "SHORT"), profit, reason,
                  (g_riskPoints > 0.0 ? g_mfePts / g_riskPoints : 0.0),
                  (g_riskPoints > 0.0 ? g_maePts / g_riskPoints : 0.0));
     }

   g_ticket = 0;
   g_posDir = 0;
  }

//====================================================================
//  DASHBOARD
//====================================================================
void DrawDashboard(const string extra)
  {
   if(!g_cfg.showDashboard) return;

   MqlDateTime t;
   TimeToStruct(NowNY(), t);

   string state = "waiting for range";
   if(g_haltedTotal)      state = "HALTED (drawdown)";
   else if(g_haltedToday) state = "halted for the session";
   else if(g_daySkipped)  state = "day skipped: " + g_skipReason;
   else if(g_ticket != 0) state = (g_posDir > 0 ? "LONG open" : "SHORT open");
   else if(g_rangeReady)  state = "range set, hunting";

   string txt = StringFormat(
      "Isaiah 60:22  |  %s / %s\n"
      "NY time    %02d:%02d:%02d   (broker GMT%+.1f winter)\n"
      "session    %s\n"
      "range      %s  /  %s\n"
      "state      %s\n"
      "trades     %d of %d today   consec losses %d\n"
      "%s",
      g_cfg.strategyTag, g_cfg.modelTag,
      t.hour, t.min, t.sec, g_gmtOffset,
      g_dayKey,
      (g_rangeHigh > 0.0 ? DoubleToString(g_rangeHigh, _Digits) : "-"),
      (g_rangeLow  > 0.0 ? DoubleToString(g_rangeLow,  _Digits) : "-"),
      state,
      g_tradesToday, g_cfg.maxTradesPerDay, g_consecLosses,
      extra);

   // Comment() is used rather than OBJ_LABEL because OBJ_LABEL renders a
   // single line only — the multi-line dashboard would be truncated to
   // its first row.
   Comment(txt);
  }

//====================================================================
//  NEW BAR HELPERS
//====================================================================
bool IsNewBar(const ENUM_TIMEFRAMES tf, datetime &store)
  {
   datetime t = iTime(_Symbol, tf, 0);
   if(t == 0 || t == store) return false;
   store = t;
   return true;
  }

//====================================================================
//  SHARED LIFECYCLE — called by each EA
//====================================================================
bool I22_Init()
  {
   ResolveGMTOffset();
   if(!InitIndicators()) return false;

   g_cfg.rangeWraps = (g_cfg.rangeEndMin <= g_cfg.rangeStartMin);

   g_peakEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_dayStartEq = g_peakEquity;

   EnsureJournalHeader();

   PrintFormat("Isaiah 60:22 | %s / %s started.  broker GMT%+.1f (winter), NY now %s",
               g_cfg.strategyTag, g_cfg.modelTag, g_gmtOffset, NYStamp(TimeCurrent()));
   PrintFormat("Isaiah 60:22 | range %02d:%02d-%02d:%02d NY, entries %02d:%02d-%02d:%02d NY, flat %02d:%02d NY",
               g_cfg.rangeStartMin / 60, g_cfg.rangeStartMin % 60,
               g_cfg.rangeEndMin   / 60, g_cfg.rangeEndMin   % 60,
               g_cfg.tradeStartMin / 60, g_cfg.tradeStartMin % 60,
               g_cfg.tradeEndMin   / 60, g_cfg.tradeEndMin   % 60,
               g_cfg.flatMin / 60, g_cfg.flatMin % 60);
   return true;
  }

void I22_Deinit()
  {
   ReleaseIndicators();
   Comment("");
   ObjectDelete(0, "I22_RangeHigh");
   ObjectDelete(0, "I22_RangeLow");
  }

//+------------------------------------------------------------------+
//| Everything that happens before the strategy-specific signal test. |
//| Returns true when the EA is clear to look for an entry.           |
//+------------------------------------------------------------------+
bool I22_Housekeeping()
  {
   datetime now = TimeCurrent();

   ReconcileClosedPosition();

   // roll the session
   string key = RangeDayKey(now);
   if(key != g_dayKey) ResetSession(key);

   int nowMin = MinuteOfDayNY(now);

   // force flat
   if(g_ticket != 0 && !InWindow(nowMin, g_cfg.tradeStartMin, g_cfg.flatMin))
     {
      FlattenAll("force-flat time reached");
      return false;
     }

   if(g_ticket != 0)
     {
      TrackExcursion();
      ManagePosition();
      return false;
     }

   if(RiskKernelBlocks())         return false;
   if(!g_cfg.tradeDay[NYDayOfWeek(now)]) return false;

   // build / close the range
   if(InWindow(nowMin, g_cfg.rangeStartMin, g_cfg.rangeEndMin))
     {
      UpdateRange();
      return false;
     }
   FinaliseRange();

   if(!g_rangeReady || g_daySkipped) return false;
   if(!InWindow(nowMin, g_cfg.tradeStartMin, g_cfg.tradeEndMin)) return false;

   return true;
  }
//+------------------------------------------------------------------+
