//+------------------------------------------------------------------+
//|  GODMODE Session-Range Forge                                     |
//|  Unified engine: 9:30 Opening Range + ICT Asian Range            |
//|  Five selectable entry models, one risk kernel, one journal.     |
//|                                                                  |
//|  Built for FALSIFICATION, not for belief. Every trade is written |
//|  to a CSV with MFE/MAE in R so the accompanying forensics script  |
//|  can run day-clustered inference and cost sweeps on it.          |
//|                                                                  |
//|  Version: 1.00   Platform: MetaTrader 5 (MQL5)                   |
//+------------------------------------------------------------------+
#property copyright "GODMODE Session-Range Forge"
#property link      ""
#property version   "1.00"
#property description "9:30 ORB + ICT Asian Range engine with 5 entry models and a forensic trade journal."

#include <Trade\Trade.mqh>

//====================================================================
//  ENUMS
//====================================================================
enum ENUM_PRESET
  {
   PRESET_NY_ORB_0930,     // NY 9:30 Opening Range (09:30-09:35 NY, trade 09:35-10:30)
   PRESET_ASIAN_ICT,       // ICT Asian Range (19:00-00:00 NY, trade 02:00-11:00)
   PRESET_LONDON_ORB,      // London Opening Range (03:00-03:15 NY, trade 03:15-06:00)
   PRESET_CUSTOM           // Use the raw time inputs below
  };

enum ENUM_MODEL
  {
   MODEL_BREAK_DIRECT,     // 1 Direct break, no retest (Zarattini-consistent)
   MODEL_BREAK_FVG,        // 2 Break + fair value gap in the displacement
   MODEL_TRAP,             // 3 Break out -> close back in -> close back out
   MODEL_RETEST,           // 4 Break -> retest -> rejection close (the taught version)
   MODEL_SWEEP_MSS         // 5 Sweep of range extreme -> market structure shift (ICT)
  };

enum ENUM_BIAS_MODE
  {
   BIAS_OFF,               // No directional filter
   BIAS_HTF_EMA,           // Higher timeframe EMA slope/side
   BIAS_PREV_DAY,          // Position vs previous day's range midpoint
   BIAS_RANGE_CANDLE       // Direction of the range-forming candle (ORB classic)
  };

enum ENUM_EXIT_MODE
  {
   EXIT_FIXED_R,           // Fixed R multiple take profit
   EXIT_TIME_ONLY,         // Hold to the session flat-time, stop only
   EXIT_R_THEN_TIME,       // Fixed R target, else flatten at session end
   EXIT_ATR_TRAIL          // ATR trailing stop, flatten at session end
  };

//====================================================================
//  INPUTS
//====================================================================
input group             "===  1. PRESET & MODEL  ==="
input ENUM_PRESET       InpPreset            = PRESET_NY_ORB_0930;  // Session preset
input ENUM_MODEL        InpModel             = MODEL_BREAK_DIRECT;  // Entry model
input ENUM_TIMEFRAMES   InpRangeTF           = PERIOD_M5;           // Range-building timeframe
input ENUM_TIMEFRAMES   InpEntryTF           = PERIOD_M1;           // Entry/trigger timeframe

input group             "===  2. CLOCK (all times New York local)  ==="
input double            InpBrokerGMTOffset   = 2.0;    // Broker GMT offset in winter (hours)
input bool              InpAutoGMTOffset     = true;   // Try to detect offset at init (live only)
input int               InpRangeStartHH      = 9;      // Range window start hour   (NY)
input int               InpRangeStartMM      = 30;     // Range window start minute (NY)
input int               InpRangeEndHH        = 9;      // Range window end hour     (NY)
input int               InpRangeEndMM        = 35;     // Range window end minute   (NY)
input int               InpTradeStartHH      = 9;      // Entry window start hour   (NY)
input int               InpTradeStartMM      = 35;     // Entry window start minute (NY)
input int               InpTradeEndHH        = 10;     // Entry window end hour     (NY)
input int               InpTradeEndMM        = 30;     // Entry window end minute   (NY)
input int               InpFlatHH            = 15;     // Force-flat hour           (NY)
input int               InpFlatMM            = 55;     // Force-flat minute         (NY)
input bool              InpTradeMonday       = true;   // Monday
input bool              InpTradeTuesday      = true;   // Tuesday
input bool              InpTradeWednesday    = true;   // Wednesday
input bool              InpTradeThursday     = true;   // Thursday
input bool              InpTradeFriday       = true;   // Friday

input group             "===  3. SIGNAL RULES  ==="
input bool              InpRequireBodyClose  = true;   // Break must be a BODY close, not a wick
input double            InpBreakBufferPts    = 0;      // Extra points beyond range to count a break
input int               InpMaxBarsToTrigger  = 60;     // Give up if no trigger within N entry bars
input int               InpFVGLookback       = 3;      // Bars scanned for the displacement FVG
input double            InpMinFVGPts         = 0;      // Minimum FVG height in points (0 = any)
input int               InpRetestMaxBars     = 20;     // Retest must occur within N bars of break
input int               InpMSSFractalRight   = 2;      // Fractal confirmation bars for MSS swing
input int               InpMSSLookback       = 40;     // Bars scanned for the MSS swing level
input int               InpReclaimBars       = 6;      // Sweep must close back inside within N bars
input double            InpMinRangePts       = 0;      // Skip day if range narrower than this
input double            InpMaxRangeATR       = 0;      // Skip day if range > N x ATR (0 = off)

input group             "===  4. DIRECTIONAL BIAS  ==="
input ENUM_BIAS_MODE    InpBiasMode          = BIAS_OFF;        // Bias filter
input ENUM_TIMEFRAMES   InpBiasTF            = PERIOD_H4;       // Bias timeframe
input int               InpBiasEMAPeriod     = 50;              // Bias EMA period
input bool              InpBiasBlocksCounter = true;            // Bias blocks counter-trend entries

input group             "===  5. STOPS & TARGETS  ==="
input ENUM_EXIT_MODE    InpExitMode          = EXIT_FIXED_R;    // Exit management
input double            InpTargetR           = 2.0;             // Take profit in R multiples
input double            InpStopBufferPts     = 0;               // Extra points beyond structural stop
input int               InpATRPeriod         = 14;              // ATR period
input double            InpMinStopATR        = 0.25;            // Stop floor as fraction of ATR
input double            InpMaxStopATR        = 3.0;             // Stop ceiling as multiple of ATR
input double            InpBreakevenAtR      = 0.0;             // Move stop to BE at N R (0 = off)
input double            InpPartialAtR        = 0.0;             // Close part of position at N R (0 = off)
input double            InpPartialPercent    = 50.0;            // Percent closed at partial
input double            InpATRTrailMult      = 1.5;             // ATR multiple for trailing stop

input group             "===  6. RISK KERNEL (hard limits)  ==="
input double            InpRiskPercent       = 0.5;             // Risk per trade, percent of equity
input double            InpMaxDailyLossPct   = 2.0;             // Halt for the day at this loss
input double            InpMaxTotalDDPct     = 10.0;            // Halt permanently at this drawdown
input int               InpMaxTradesPerDay   = 2;               // Max entries per NY day
input int               InpMaxConsecLosses   = 4;               // Halt for the day after N losses
input double            InpMaxSpreadPts      = 30;              // Reject entry above this spread
input double            InpMaxSpreadVsStop   = 10.0;            // Reject if spread > N% of stop
input int               InpSlippagePts       = 20;              // Max deviation on market orders
input long              InpMagic             = 930193;          // Magic number

input group             "===  7. FORENSIC JOURNAL  ==="
input bool              InpWriteJournal      = true;            // Write per-trade CSV
input string            InpJournalFile       = "SRF_journal.csv";// File in MQL5/Files
input string            InpRunTag            = "run01";         // Tag written to every row
input bool              InpShowDashboard     = true;            // On-chart dashboard
input bool              InpDrawObjects       = true;            // Draw range lines

//====================================================================
//  GLOBAL STATE
//====================================================================
CTrade   trade;

int      g_atrHandle      = INVALID_HANDLE;
int      g_biasHandle     = INVALID_HANDLE;
double   g_gmtOffset      = 0.0;

// Resolved session times (minutes from NY midnight)
int      g_rangeStartMin  = 0;
int      g_rangeEndMin    = 0;
int      g_tradeStartMin  = 0;
int      g_tradeEndMin    = 0;
int      g_flatMin        = 0;
bool     g_rangeWraps     = false;   // range window crosses midnight

// Per-day state
string   g_dayKey         = "";
bool     g_rangeReady     = false;
double   g_rangeHigh      = 0.0;
double   g_rangeLow       = 0.0;
double   g_rangeOpen      = 0.0;
double   g_rangeClose     = 0.0;
double   g_rangeATR       = 0.0;
int      g_tradesToday    = 0;
int      g_consecLosses   = 0;
double   g_dayStartEquity = 0.0;
bool     g_dayHalted      = false;
bool     g_globalHalted   = false;
double   g_peakEquity     = 0.0;
int      g_barsSinceRange = 0;

// Signal machine
int      g_breakDir       = 0;       // 0 none, +1 up, -1 down
datetime g_breakTime      = 0;
double   g_breakLevel     = 0.0;
int      g_barsSinceBreak = 0;
bool     g_backInside     = false;   // for TRAP
bool     g_retestSeen     = false;   // for RETEST
int      g_sweepDir       = 0;       // for SWEEP_MSS: +1 = swept low (long bias)
double   g_sweepExtreme   = 0.0;
int      g_barsSinceSweep = 0;
double   g_mssLevel       = 0.0;

// Open trade tracking (for MFE/MAE)
ulong    g_ticket         = 0;
ulong    g_posID           = 0;
double   g_entryPrice     = 0.0;
double   g_riskPoints     = 0.0;
double   g_initialSL      = 0.0;
double   g_initialTP      = 0.0;
int      g_posDir         = 0;
datetime g_entryTime      = 0;
double   g_mfePts         = 0.0;
double   g_maePts         = 0.0;
double   g_entrySpread    = 0.0;
double   g_entryLots      = 0.0;
bool     g_bePlaced       = false;
bool     g_partialDone    = false;
string   g_entryDayKey    = "";
string   g_biasAtEntry    = "";
int      g_entryBarCount  = 0;

datetime g_lastEntryBar   = 0;
datetime g_lastRangeBar   = 0;

//====================================================================
//  FORWARD DECLARATIONS
//====================================================================
void   ResetDay(const string newKey);
void   ResetSignal();
void   BuildRange();
void   DrawRange();
void   ApplyPreset();
int    EvaluateSignal(double &stopRef);
void   OpenTrade(const int dir, const double stopRef);
void   ManageOpenPosition();
void   CheckClosedPosition();
void   WriteJournalRow(const double exitPrice, const datetime exitTime,
                       const double profit, const string reason);
void   EnsureJournalHeader();
void   Dashboard();
bool   IsUSDST(const datetime gmt);
double Pt();

//====================================================================
//  TIME HELPERS
//====================================================================

//--- Is the given GMT time inside US daylight saving?
//    DST: 2nd Sunday of March 07:00 GMT  ->  1st Sunday of November 06:00 GMT
bool IsUSDST(const datetime gmt)
  {
   MqlDateTime t;
   TimeToStruct(gmt, t);
   int year = t.year;

// second Sunday of March
   datetime marchStart = StringToTime(StringFormat("%04d.03.01 00:00", year));
   MqlDateTime m;
   TimeToStruct(marchStart, m);
   int firstSunOffset = (7 - m.day_of_week) % 7;          // days until first Sunday
   long     dstStart  = (long)marchStart + (long)(firstSunOffset + 7) * 86400 + 7 * 3600;

// first Sunday of November
   datetime novStart = StringToTime(StringFormat("%04d.11.01 00:00", year));
   MqlDateTime n;
   TimeToStruct(novStart, n);
   int firstSunNov = (7 - n.day_of_week) % 7;
   long     dstEnd = (long)novStart + (long)firstSunNov * 86400 + 6 * 3600;

   return ((long)gmt >= dstStart && (long)gmt < dstEnd);
  }

//--- Convert broker/server time to New York local time
datetime SrvToNY(const datetime srv)
  {
   long gmt = (long)srv - (long)MathRound(g_gmtOffset * 3600.0);
   int  off = IsUSDST((datetime)gmt) ? -4 : -5;
   return (datetime)(gmt + (long)off * 3600);
  }

int NYMinuteOfDay(const datetime srv)
  {
   MqlDateTime t;
   TimeToStruct(SrvToNY(srv), t);
   return t.hour * 60 + t.min;
  }

string NYDayKey(const datetime srv)
  {
   MqlDateTime t;
   TimeToStruct(SrvToNY(srv), t);
   return StringFormat("%04d-%02d-%02d", t.year, t.mon, t.day);
  }

string NYStamp(const datetime srv)
  {
   MqlDateTime t;
   TimeToStruct(SrvToNY(srv), t);
   return StringFormat("%04d-%02d-%02d %02d:%02d:%02d",
                       t.year, t.mon, t.day, t.hour, t.min, t.sec);
  }

int NYDayOfWeek(const datetime srv)
  {
   MqlDateTime t;
   TimeToStruct(SrvToNY(srv), t);
   return t.day_of_week;   // 0 = Sunday
  }

bool DayEnabled(const datetime srv)
  {
   int d = NYDayOfWeek(srv);
   if(d == 1) return InpTradeMonday;
   if(d == 2) return InpTradeTuesday;
   if(d == 3) return InpTradeWednesday;
   if(d == 4) return InpTradeThursday;
   if(d == 5) return InpTradeFriday;
   return false;
  }

//--- The "trade day" a bar belongs to. For a range that wraps midnight
//    (e.g. ICT Asian 19:00 -> 00:00), evening bars belong to the NEXT day.
string TradeDayKey(const datetime srv)
  {
   if(!g_rangeWraps)
      return NYDayKey(srv);

   int mod = NYMinuteOfDay(srv);
   if(mod >= g_rangeStartMin)                 // evening portion -> next calendar day
      return NYDayKey(srv + 86400);
   return NYDayKey(srv);
  }

//--- Is this bar inside the range-building window?
bool InRangeWindow(const datetime srv)
  {
   int m = NYMinuteOfDay(srv);
   if(g_rangeWraps)
      return (m >= g_rangeStartMin || m < g_rangeEndMin);
   return (m >= g_rangeStartMin && m < g_rangeEndMin);
  }

bool InTradeWindow(const datetime srv)
  {
   int m = NYMinuteOfDay(srv);
   if(g_tradeStartMin <= g_tradeEndMin)
      return (m >= g_tradeStartMin && m < g_tradeEndMin);
   return (m >= g_tradeStartMin || m < g_tradeEndMin);
  }

bool PastFlatTime(const datetime srv)
  {
   int m = NYMinuteOfDay(srv);
   if(g_flatMin >= g_tradeStartMin)
      return (m >= g_flatMin);
   return (m >= g_flatMin && m < g_tradeStartMin);
  }

//====================================================================
//  MARKET HELPERS
//====================================================================
double Pt()          { return SymbolInfoDouble(_Symbol, SYMBOL_POINT); }
double SpreadPts()   { return (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD); }

double ATRValue(const int shift = 1)
  {
   if(g_atrHandle == INVALID_HANDLE) return 0.0;
   double buf[];
   ArraySetAsSeries(buf, true);
   if(CopyBuffer(g_atrHandle, 0, shift, 1, buf) < 1) return 0.0;
   return buf[0];
  }

double BiasEMA(const int shift = 1)
  {
   if(g_biasHandle == INVALID_HANDLE) return 0.0;
   double buf[];
   ArraySetAsSeries(buf, true);
   if(CopyBuffer(g_biasHandle, 0, shift, 1, buf) < 1) return 0.0;
   return buf[0];
  }

//--- +1 bullish, -1 bearish, 0 neutral / filter off
int DirectionalBias()
  {
   switch(InpBiasMode)
     {
      case BIAS_OFF:
         return 0;

      case BIAS_HTF_EMA:
        {
         double ema = BiasEMA(1);
         double c   = iClose(_Symbol, InpBiasTF, 1);
         if(ema <= 0.0 || c <= 0.0) return 0;
         return (c > ema) ? 1 : -1;
        }

      case BIAS_PREV_DAY:
        {
         double h = iHigh(_Symbol, PERIOD_D1, 1);
         double l = iLow(_Symbol, PERIOD_D1, 1);
         double c = iClose(_Symbol, PERIOD_D1, 1);
         if(h <= l) return 0;
         return (c > (h + l) / 2.0) ? 1 : -1;
        }

      case BIAS_RANGE_CANDLE:
        {
         if(!g_rangeReady) return 0;
         if(g_rangeClose > g_rangeOpen) return 1;
         if(g_rangeClose < g_rangeOpen) return -1;
         return 0;
        }
     }
   return 0;
  }

string BiasLabel(const int b)
  {
   if(b > 0) return "BULL";
   if(b < 0) return "BEAR";
   return "FLAT";
  }

//====================================================================
//  PATTERN PRIMITIVES  (all on closed bars only - no repainting)
//====================================================================

//--- Bullish FVG in the last InpFVGLookback bars of the entry TF.
//    3-candle gap: low[i] > high[i+2]
bool HasBullishFVG(double &gapLow, double &gapHigh)
  {
   for(int i = 1; i <= InpFVGLookback; i++)
     {
      double l1 = iLow(_Symbol, InpEntryTF, i);
      double h3 = iHigh(_Symbol, InpEntryTF, i + 2);
      if(l1 > h3)
        {
         double h = (l1 - h3) / Pt();
         if(h >= InpMinFVGPts)
           {
            gapLow  = h3;
            gapHigh = l1;
            return true;
           }
        }
     }
   return false;
  }

bool HasBearishFVG(double &gapLow, double &gapHigh)
  {
   for(int i = 1; i <= InpFVGLookback; i++)
     {
      double h1 = iHigh(_Symbol, InpEntryTF, i);
      double l3 = iLow(_Symbol, InpEntryTF, i + 2);
      if(h1 < l3)
        {
         double h = (l3 - h1) / Pt();
         if(h >= InpMinFVGPts)
           {
            gapLow  = h1;
            gapHigh = l3;
            return true;
           }
        }
     }
   return false;
  }

//--- Last confirmed fractal swing high/low on the entry timeframe.
double LastFractalHigh()
  {
   int r = MathMax(1, InpMSSFractalRight);
   for(int i = r + 1; i <= InpMSSLookback; i++)
     {
      double h = iHigh(_Symbol, InpEntryTF, i);
      bool ok = true;
      for(int k = 1; k <= r && ok; k++)
        {
         if(iHigh(_Symbol, InpEntryTF, i - k) >= h) ok = false;
         if(iHigh(_Symbol, InpEntryTF, i + k) >= h) ok = false;
        }
      if(ok) return h;
     }
   return 0.0;
  }

double LastFractalLow()
  {
   int r = MathMax(1, InpMSSFractalRight);
   for(int i = r + 1; i <= InpMSSLookback; i++)
     {
      double l = iLow(_Symbol, InpEntryTF, i);
      bool ok = true;
      for(int k = 1; k <= r && ok; k++)
        {
         if(iLow(_Symbol, InpEntryTF, i - k) <= l) ok = false;
         if(iLow(_Symbol, InpEntryTF, i + k) <= l) ok = false;
        }
      if(ok) return l;
     }
   return 0.0;
  }

//====================================================================
//  RANGE ENGINE
//====================================================================
void ResetDay(const string newKey)
  {
   g_dayKey          = newKey;
   g_rangeReady      = false;
   g_rangeHigh       = 0.0;
   g_rangeLow        = 0.0;
   g_rangeOpen       = 0.0;
   g_rangeClose      = 0.0;
   g_rangeATR        = 0.0;
   g_tradesToday     = 0;
   g_consecLosses    = 0;
   g_dayHalted       = false;
   g_dayStartEquity  = AccountInfoDouble(ACCOUNT_EQUITY);
   g_barsSinceRange  = 0;
   ResetSignal();
  }

void ResetSignal()
  {
   g_breakDir        = 0;
   g_breakTime       = 0;
   g_breakLevel      = 0.0;
   g_barsSinceBreak  = 0;
   g_backInside      = false;
   g_retestSeen      = false;
   g_sweepDir        = 0;
   g_sweepExtreme    = 0.0;
   g_barsSinceSweep  = 0;
   g_mssLevel        = 0.0;
  }

//--- Build the range from closed bars of the range timeframe.
void BuildRange()
  {
   double hi = -DBL_MAX, lo = DBL_MAX, op = 0.0, cl = 0.0;
   bool found = false;
   int last = -1;

// Walk back over enough bars to cover any session length.
   int maxBars = (int)MathMin(2000, Bars(_Symbol, InpRangeTF) - 2);
   for(int i = 1; i <= maxBars; i++)
     {
      datetime bt = iTime(_Symbol, InpRangeTF, i);
      if(bt == 0) break;
      if(TradeDayKey(bt) != g_dayKey) 
        {
         if(found) break;      // walked past the target day
         continue;
        }
      if(!InRangeWindow(bt)) continue;

      hi = MathMax(hi, iHigh(_Symbol, InpRangeTF, i));
      lo = MathMin(lo, iLow(_Symbol, InpRangeTF, i));
      if(last < 0) { last = i; cl = iClose(_Symbol, InpRangeTF, i); }
      op    = iOpen(_Symbol, InpRangeTF, i);
      found = true;
     }

   if(!found || hi <= lo) return;

   g_rangeHigh  = hi;
   g_rangeLow   = lo;
   g_rangeOpen  = op;
   g_rangeClose = cl;
   g_rangeATR   = ATRValue(1);
   g_rangeReady = true;

   if(InpDrawObjects) DrawRange();
  }

void DrawRange()
  {
   string hn = "SRF_H_" + g_dayKey;
   string ln = "SRF_L_" + g_dayKey;
   if(ObjectFind(0, hn) < 0) ObjectCreate(0, hn, OBJ_HLINE, 0, 0, g_rangeHigh);
   if(ObjectFind(0, ln) < 0) ObjectCreate(0, ln, OBJ_HLINE, 0, 0, g_rangeLow);
   ObjectSetDouble(0, hn, OBJPROP_PRICE, g_rangeHigh);
   ObjectSetDouble(0, ln, OBJPROP_PRICE, g_rangeLow);
   ObjectSetInteger(0, hn, OBJPROP_COLOR, clrDodgerBlue);
   ObjectSetInteger(0, ln, OBJPROP_COLOR, clrTomato);
   ObjectSetInteger(0, hn, OBJPROP_STYLE, STYLE_DOT);
   ObjectSetInteger(0, ln, OBJPROP_STYLE, STYLE_DOT);
  }

//--- Structural filters on the range itself
bool RangeAcceptable()
  {
   if(!g_rangeReady) return false;
   double widthPts = (g_rangeHigh - g_rangeLow) / Pt();
   if(InpMinRangePts > 0 && widthPts < InpMinRangePts) return false;
   if(InpMaxRangeATR > 0 && g_rangeATR > 0)
     {
      double atrPts = g_rangeATR / Pt();
      if(atrPts > 0 && widthPts > InpMaxRangeATR * atrPts) return false;
     }
   return true;
  }

//====================================================================
//  SIGNAL MACHINE  - evaluated once per closed entry-TF bar
//====================================================================

//--- Did the last closed bar break the range? Returns +1/-1/0.
int DetectBreak()
  {
   double c = iClose(_Symbol, InpEntryTF, 1);
   double h = iHigh(_Symbol, InpEntryTF, 1);
   double l = iLow(_Symbol, InpEntryTF, 1);
   double buf = InpBreakBufferPts * Pt();

   if(InpRequireBodyClose)
     {
      if(c > g_rangeHigh + buf) return  1;
      if(c < g_rangeLow  - buf) return -1;
     }
   else
     {
      if(h > g_rangeHigh + buf) return  1;
      if(l < g_rangeLow  - buf) return -1;
     }
   return 0;
  }

//--- Sweep of a range extreme with a close back inside (ICT).
//    Returns +1 if the LOW was swept (bullish setup), -1 if the HIGH was.
int DetectSweep()
  {
   double c   = iClose(_Symbol, InpEntryTF, 1);
   double h   = iHigh(_Symbol, InpEntryTF, 1);
   double l   = iLow(_Symbol, InpEntryTF, 1);
   double buf = InpBreakBufferPts * Pt();

   if(l < g_rangeLow - buf && c >= g_rangeLow) return  1;
   if(h > g_rangeHigh + buf && c <= g_rangeHigh) return -1;
   return 0;
  }

//--- Returns +1 long, -1 short, 0 no trade. Fills stop reference price.
int EvaluateSignal(double &stopRef)
  {
   stopRef = 0.0;
   int dir  = 0;
   double gl = 0.0, gh = 0.0;

   switch(InpModel)
     {
      //---------------------------------------------------------------
      case MODEL_BREAK_DIRECT:
        {
         int b = DetectBreak();
         if(b == 0) return 0;
         stopRef = (b > 0) ? g_rangeLow : g_rangeHigh;
         dir = b;
         break;
        }

      //---------------------------------------------------------------
      case MODEL_BREAK_FVG:
        {
         int b = DetectBreak();
         if(b == 0) return 0;
         if(b > 0 && !HasBullishFVG(gl, gh)) return 0;
         if(b < 0 && !HasBearishFVG(gl, gh)) return 0;
         stopRef = (b > 0) ? MathMin(gl, g_rangeLow) : MathMax(gh, g_rangeHigh);
         dir = b;
         break;
        }

      //---------------------------------------------------------------
      case MODEL_TRAP:
        {
         // Stage 1: first break
         if(g_breakDir == 0)
           {
            int b = DetectBreak();
            if(b != 0)
              {
               g_breakDir       = b;
               g_breakLevel     = (b > 0) ? g_rangeHigh : g_rangeLow;
               g_breakTime      = iTime(_Symbol, InpEntryTF, 1);
               g_barsSinceBreak = 0;
               g_backInside     = false;
              }
            return 0;
           }

         double c = iClose(_Symbol, InpEntryTF, 1);

         // Stage 2: close back inside the range
         if(!g_backInside)
           {
            bool inside = (c <= g_rangeHigh && c >= g_rangeLow);
            if(inside) g_backInside = true;
            return 0;
           }

         // Stage 3: close back outside in the ORIGINAL break direction
         if(g_breakDir > 0 && c > g_rangeHigh)
           {
            stopRef = iLow(_Symbol, InpEntryTF, 1);
            dir = 1;
            break;
           }
         if(g_breakDir < 0 && c < g_rangeLow)
           {
            stopRef = iHigh(_Symbol, InpEntryTF, 1);
            dir = -1;
            break;
           }
         return 0;
        }

      //---------------------------------------------------------------
      case MODEL_RETEST:
        {
         // Stage 1: break
         if(g_breakDir == 0)
           {
            int b = DetectBreak();
            if(b != 0)
              {
               g_breakDir       = b;
               g_breakLevel     = (b > 0) ? g_rangeHigh : g_rangeLow;
               g_breakTime      = iTime(_Symbol, InpEntryTF, 1);
               g_barsSinceBreak = 0;
               g_retestSeen     = false;
              }
            return 0;
           }

         if(g_barsSinceBreak > InpRetestMaxBars) { ResetSignal(); return 0; }

         double h = iHigh(_Symbol, InpEntryTF, 1);
         double l = iLow(_Symbol, InpEntryTF, 1);
         double c = iClose(_Symbol, InpEntryTF, 1);
         double o = iOpen(_Symbol, InpEntryTF, 1);

         // Stage 2: price returns to the broken level
         if(!g_retestSeen)
           {
            if(g_breakDir > 0 && l <= g_breakLevel) g_retestSeen = true;
            if(g_breakDir < 0 && h >= g_breakLevel) g_retestSeen = true;
            if(!g_retestSeen) return 0;
           }

         // Stage 3: rejection close in the break direction
         if(g_breakDir > 0 && c > o && c > g_breakLevel)
           {
            stopRef = l;
            dir = 1;
            break;
           }
         if(g_breakDir < 0 && c < o && c < g_breakLevel)
           {
            stopRef = h;
            dir = -1;
            break;
           }
         return 0;
        }

      //---------------------------------------------------------------
      case MODEL_SWEEP_MSS:
        {
         // Stage 1: sweep
         if(g_sweepDir == 0)
           {
            int s = DetectSweep();
            if(s != 0)
              {
               g_sweepDir       = s;
               g_sweepExtreme   = (s > 0) ? iLow(_Symbol, InpEntryTF, 1)
                                          : iHigh(_Symbol, InpEntryTF, 1);
               g_barsSinceSweep = 0;
               g_mssLevel       = (s > 0) ? LastFractalHigh() : LastFractalLow();
              }
            return 0;
           }

         if(g_barsSinceSweep > InpMaxBarsToTrigger) { ResetSignal(); return 0; }

         // Refresh the structural level while we wait
         if(g_mssLevel <= 0.0)
            g_mssLevel = (g_sweepDir > 0) ? LastFractalHigh() : LastFractalLow();
         if(g_mssLevel <= 0.0) return 0;

         double c = iClose(_Symbol, InpEntryTF, 1);

         // Track the extreme in case price keeps running
         if(g_sweepDir > 0) g_sweepExtreme = MathMin(g_sweepExtreme, iLow(_Symbol, InpEntryTF, 1));
         else               g_sweepExtreme = MathMax(g_sweepExtreme, iHigh(_Symbol, InpEntryTF, 1));

         // Stage 2: market structure shift = body close through the swing
         if(g_sweepDir > 0 && c > g_mssLevel)
           {
            stopRef = g_sweepExtreme;
            dir = 1;
            break;
           }
         if(g_sweepDir < 0 && c < g_mssLevel)
           {
            stopRef = g_sweepExtreme;
            dir = -1;
            break;
           }
         return 0;
        }
     }

   if(dir == 0) return 0;

//--- Bias gate
   int bias = DirectionalBias();
   if(InpBiasBlocksCounter && bias != 0 && bias != dir) return 0;

   return dir;
  }

//====================================================================
//  RISK KERNEL
//====================================================================
double PointValuePerLot()
  {
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickSize <= 0.0) return 0.0;
   return tickValue * (Pt() / tickSize);
  }

double CalcLots(const double stopPoints)
  {
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk   = equity * InpRiskPercent / 100.0;
   double pv     = PointValuePerLot();
   if(stopPoints <= 0.0 || pv <= 0.0) return 0.0;

   double lots = risk / (stopPoints * pv);

   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double stepLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(stepLot <= 0.0) stepLot = 0.01;

   lots = MathFloor(lots / stepLot) * stepLot;
   if(lots < minLot) return 0.0;          // refuse to over-risk by rounding up
   return MathMin(lots, maxLot);
  }

bool RiskGatesPass(const double stopPoints)
  {
   if(g_globalHalted || g_dayHalted) return false;
   if(g_tradesToday >= InpMaxTradesPerDay) return false;
   if(g_consecLosses >= InpMaxConsecLosses) { g_dayHalted = true; return false; }
   if(PositionsTotal() > 0 && g_ticket != 0) return false;

   double sp = SpreadPts();
   if(InpMaxSpreadPts > 0 && sp > InpMaxSpreadPts) return false;
   if(InpMaxSpreadVsStop > 0 && stopPoints > 0)
      if((sp / stopPoints) * 100.0 > InpMaxSpreadVsStop) return false;

   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_dayStartEquity > 0)
     {
      double dayLoss = (g_dayStartEquity - eq) / g_dayStartEquity * 100.0;
      if(dayLoss >= InpMaxDailyLossPct) { g_dayHalted = true; return false; }
     }
   if(g_peakEquity > 0)
     {
      double dd = (g_peakEquity - eq) / g_peakEquity * 100.0;
      if(dd >= InpMaxTotalDDPct) { g_globalHalted = true; return false; }
     }
   return true;
  }

//--- Apply ATR floor/ceiling to a structural stop distance
double ClampStopPoints(double stopPoints)
  {
   double atrPts = (g_rangeATR > 0) ? g_rangeATR / Pt() : ATRValue(1) / Pt();
   if(atrPts > 0)
     {
      if(InpMinStopATR > 0) stopPoints = MathMax(stopPoints, InpMinStopATR * atrPts);
      if(InpMaxStopATR > 0) stopPoints = MathMin(stopPoints, InpMaxStopATR * atrPts);
     }
   double minStop = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   return MathMax(stopPoints, minStop + 1.0);
  }

//====================================================================
//  EXECUTION
//====================================================================
void OpenTrade(const int dir, const double stopRef)
  {
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = (dir > 0) ? ask : bid;

   double rawStop = (dir > 0) ? (entry - stopRef) : (stopRef - entry);
   rawStop += InpStopBufferPts * Pt();
   double stopPoints = ClampStopPoints(rawStop / Pt());

   if(!RiskGatesPass(stopPoints)) return;

   double lots = CalcLots(stopPoints);
   if(lots <= 0.0) return;

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double sl, tp = 0.0;

   if(dir > 0)
     {
      sl = NormalizeDouble(entry - stopPoints * Pt(), digits);
      if(InpExitMode == EXIT_FIXED_R || InpExitMode == EXIT_R_THEN_TIME)
         tp = NormalizeDouble(entry + stopPoints * InpTargetR * Pt(), digits);
     }
   else
     {
      sl = NormalizeDouble(entry + stopPoints * Pt(), digits);
      if(InpExitMode == EXIT_FIXED_R || InpExitMode == EXIT_R_THEN_TIME)
         tp = NormalizeDouble(entry - stopPoints * InpTargetR * Pt(), digits);
     }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippagePts);
   trade.SetTypeFillingBySymbol(_Symbol);

   bool ok = (dir > 0)
             ? trade.Buy(lots, _Symbol, 0.0, sl, tp, "SRF|" + EnumToString(InpModel))
             : trade.Sell(lots, _Symbol, 0.0, sl, tp, "SRF|" + EnumToString(InpModel));

   if(!ok)
     {
      PrintFormat("ENTRY REJECTED  ret=%d  %s", trade.ResultRetcode(), trade.ResultComment());
      return;
     }

   g_ticket        = trade.ResultOrder();
   if(g_ticket == 0) g_ticket = trade.ResultDeal();

// Resolve the actual position ticket
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      g_ticket = t;
      break;
     }

   g_posID         = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
   g_entryPrice    = PositionGetDouble(POSITION_PRICE_OPEN);
   if(g_entryPrice <= 0.0) g_entryPrice = entry;
   g_riskPoints    = stopPoints;
   g_initialSL     = sl;
   g_initialTP     = tp;
   g_posDir        = dir;
   g_entryTime     = TimeCurrent();
   g_mfePts        = 0.0;
   g_maePts        = 0.0;
   g_entrySpread   = SpreadPts();
   g_entryLots     = lots;
   g_bePlaced      = false;
   g_partialDone   = false;
   g_entryDayKey   = g_dayKey;
   g_biasAtEntry   = BiasLabel(DirectionalBias());
   g_entryBarCount = Bars(_Symbol, InpEntryTF);
   g_tradesToday++;

   PrintFormat("ENTRY %s  lots=%.2f  entry=%.5f  sl=%.5f  tp=%.5f  riskPts=%.1f  model=%s",
               (dir > 0 ? "BUY" : "SELL"), lots, g_entryPrice, sl, tp, stopPoints,
               EnumToString(InpModel));
  }

//--- Track excursion and run the management rules
void ManageOpenPosition()
  {
   if(g_ticket == 0) return;
   if(!PositionSelectByTicket(g_ticket)) return;

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double px  = (g_posDir > 0) ? bid : ask;

   double movePts = (g_posDir > 0) ? (px - g_entryPrice) / Pt()
                                   : (g_entryPrice - px) / Pt();
   g_mfePts = MathMax(g_mfePts, movePts);
   g_maePts = MathMin(g_maePts, movePts);

   double rNow = (g_riskPoints > 0) ? movePts / g_riskPoints : 0.0;
   int digits  = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

//--- Partial close
   if(!g_partialDone && InpPartialAtR > 0 && rNow >= InpPartialAtR)
     {
      double vol  = PositionGetDouble(POSITION_VOLUME);
      double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
      if(step <= 0) step = 0.01;
      double part = MathFloor((vol * InpPartialPercent / 100.0) / step) * step;
      if(part >= SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN) && part < vol)
        {
         if(trade.PositionClosePartial(g_ticket, part)) g_partialDone = true;
        }
      else
         g_partialDone = true;
     }

//--- Breakeven
   if(!g_bePlaced && InpBreakevenAtR > 0 && rNow >= InpBreakevenAtR)
     {
      double be = NormalizeDouble(g_entryPrice, digits);
      double tp = PositionGetDouble(POSITION_TP);
      if(trade.PositionModify(g_ticket, be, tp)) g_bePlaced = true;
     }

//--- ATR trail
   if(InpExitMode == EXIT_ATR_TRAIL)
     {
      double atr = ATRValue(1);
      if(atr > 0)
        {
         double curSL = PositionGetDouble(POSITION_SL);
         double tp    = PositionGetDouble(POSITION_TP);
         if(g_posDir > 0)
           {
            double want = NormalizeDouble(px - InpATRTrailMult * atr, digits);
            if(want > curSL && want < px) trade.PositionModify(g_ticket, want, tp);
           }
         else
           {
            double want = NormalizeDouble(px + InpATRTrailMult * atr, digits);
            if((curSL == 0 || want < curSL) && want > px) trade.PositionModify(g_ticket, want, tp);
           }
        }
     }

//--- Time exit
   if(PastFlatTime(TimeCurrent()))
     {
      trade.PositionClose(g_ticket, InpSlippagePts);
     }
  }

//====================================================================
//  JOURNAL
//====================================================================
void EnsureJournalHeader()
  {
   if(!InpWriteJournal) return;
   if(FileIsExist(InpJournalFile)) return;
   int h = FileOpen(InpJournalFile, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(h == INVALID_HANDLE) return;
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
   if(!InpWriteJournal) return;

   int h = FileOpen(InpJournalFile, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(h == INVALID_HANDLE) return;
   FileSeek(h, 0, SEEK_END);

   double movePts = (g_posDir > 0) ? (exitPrice - g_entryPrice) / Pt()
                                   : (g_entryPrice - exitPrice) / Pt();
   double rReal   = (g_riskPoints > 0) ? movePts / g_riskPoints : 0.0;
   double mfeR    = (g_riskPoints > 0) ? g_mfePts / g_riskPoints : 0.0;
   double maeR    = (g_riskPoints > 0) ? g_maePts / g_riskPoints : 0.0;
   double rangePts= (g_rangeHigh > g_rangeLow) ? (g_rangeHigh - g_rangeLow) / Pt() : 0.0;
   double atrPts  = (g_rangeATR > 0) ? g_rangeATR / Pt() : 0.0;
   double ratio   = (atrPts > 0) ? rangePts / atrPts : 0.0;
   int    bars    = Bars(_Symbol, InpEntryTF) - g_entryBarCount;

   FileWrite(h,
             InpRunTag, _Symbol, EnumToString(InpPreset), EnumToString(InpModel),
             (string)g_ticket, (g_posDir > 0 ? "LONG" : "SHORT"),
             g_entryDayKey, NYStamp(g_entryTime), NYStamp(exitTime),
             DoubleToString(g_entryPrice, 5), DoubleToString(exitPrice, 5),
             DoubleToString(g_initialSL, 5), DoubleToString(g_initialTP, 5),
             DoubleToString(g_riskPoints, 1), DoubleToString(rReal, 4),
             DoubleToString(mfeR, 4), DoubleToString(maeR, 4),
             DoubleToString(g_entrySpread, 1),
             DoubleToString(g_rangeHigh, 5), DoubleToString(g_rangeLow, 5),
             DoubleToString(rangePts, 1), DoubleToString(atrPts, 1),
             DoubleToString(ratio, 3), g_biasAtEntry,
             DoubleToString(g_entryLots, 2), DoubleToString(profit, 2),
             DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2),
             (string)bars, reason);
   FileClose(h);
  }

//--- Detect that our tracked position has closed and journal it
void CheckClosedPosition()
  {
   if(g_ticket == 0) return;
   if(PositionSelectByTicket(g_ticket)) return;   // still open

   double exitPrice = 0.0, profit = 0.0;
   datetime exitTime = TimeCurrent();
   string reason = "CLOSED";

   if(HistorySelectByPosition(g_posID != 0 ? g_posID : g_ticket))
     {
      int deals = HistoryDealsTotal();
      for(int i = 0; i < deals; i++)
        {
         ulong d = HistoryDealGetTicket(i);
         if(d == 0) continue;
         if(HistoryDealGetInteger(d, DEAL_ENTRY) != DEAL_ENTRY_OUT) continue;
         exitPrice = HistoryDealGetDouble(d, DEAL_PRICE);
         exitTime  = (datetime)HistoryDealGetInteger(d, DEAL_TIME);
         profit   += HistoryDealGetDouble(d, DEAL_PROFIT)
                   + HistoryDealGetDouble(d, DEAL_SWAP)
                   + HistoryDealGetDouble(d, DEAL_COMMISSION);
         long r = HistoryDealGetInteger(d, DEAL_REASON);
         if(r == DEAL_REASON_SL) reason = "STOP";
         else if(r == DEAL_REASON_TP) reason = "TARGET";
         else reason = "MANAGED";
        }
     }

   if(exitPrice <= 0.0)
      exitPrice = (g_posDir > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                                 : SymbolInfoDouble(_Symbol, SYMBOL_ASK);

   WriteJournalRow(exitPrice, exitTime, profit, reason);

   if(profit < 0) g_consecLosses++;
   else           g_consecLosses = 0;

   g_ticket   = 0;
   g_posID    = 0;
   g_posDir   = 0;
   ResetSignal();
  }

//====================================================================
//  DASHBOARD
//====================================================================
void Dashboard()
  {
   if(!InpShowDashboard) return;

   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   double dayPL = (g_dayStartEquity > 0) ? (eq - g_dayStartEquity) / g_dayStartEquity * 100.0 : 0.0;
   string setup = "waiting";
   if(g_breakDir != 0) setup = StringFormat("break %s%s", (g_breakDir > 0 ? "UP" : "DOWN"),
                                            (g_backInside ? " + back inside" : ""));
   if(g_sweepDir != 0) setup = StringFormat("sweep %s, MSS @ %.5f",
                                            (g_sweepDir > 0 ? "LOW" : "HIGH"), g_mssLevel);

   string s = "\n";
   s += "  SESSION-RANGE FORGE  |  " + _Symbol + "\n";
   s += "  -------------------------------------\n";
   s += "  preset      " + EnumToString(InpPreset) + "\n";
   s += "  model       " + EnumToString(InpModel) + "\n";
   s += "  NY clock    " + NYStamp(TimeCurrent()) + "\n";
   s += "  trade day   " + g_dayKey + "\n";
   s += "  range       " + (g_rangeReady
                            ? StringFormat("%.5f / %.5f  (%.0f pts)", g_rangeHigh, g_rangeLow,
                                           (g_rangeHigh - g_rangeLow) / Pt())
                            : "not built") + "\n";
   s += "  window      " + (InTradeWindow(TimeCurrent()) ? "OPEN" : "closed") + "\n";
   s += "  bias        " + BiasLabel(DirectionalBias()) + "\n";
   s += "  setup       " + setup + "\n";
   s += "  -------------------------------------\n";
   s += StringFormat("  trades      %d / %d\n", g_tradesToday, InpMaxTradesPerDay);
   s += StringFormat("  day P/L     %.2f%%   (halt at -%.2f%%)\n", dayPL, InpMaxDailyLossPct);
   s += StringFormat("  spread      %.0f pts\n", SpreadPts());
   s += "  status      " + (g_globalHalted ? "HALTED (drawdown)"
                            : g_dayHalted ? "halted for the day"
                            : "armed") + "\n";
   if(g_ticket != 0 && g_riskPoints > 0)
      s += StringFormat("  open        %s  MFE %.2fR  MAE %.2fR\n",
                        (g_posDir > 0 ? "LONG" : "SHORT"),
                        g_mfePts / g_riskPoints, g_maePts / g_riskPoints);
   s += "\n";
   Comment(s);
  }

//====================================================================
//  PRESETS
//====================================================================
void ApplyPreset()
  {
   int rsH = InpRangeStartHH, rsM = InpRangeStartMM;
   int reH = InpRangeEndHH,   reM = InpRangeEndMM;
   int tsH = InpTradeStartHH, tsM = InpTradeStartMM;
   int teH = InpTradeEndHH,   teM = InpTradeEndMM;
   int fH  = InpFlatHH,       fM  = InpFlatMM;

   switch(InpPreset)
     {
      case PRESET_NY_ORB_0930:
         rsH =  9; rsM = 30; reH =  9; reM = 35;
         tsH =  9; tsM = 35; teH = 10; teM = 30;
         fH  = 15; fM  = 55;
         break;

      case PRESET_ASIAN_ICT:
         rsH = 19; rsM =  0; reH =  0; reM =  0;   // wraps midnight
         tsH =  2; tsM =  0; teH = 11; teM =  0;
         fH  = 12; fM  =  0;
         break;

      case PRESET_LONDON_ORB:
         rsH =  3; rsM =  0; reH =  3; reM = 15;
         tsH =  3; tsM = 15; teH =  6; teM =  0;
         fH  = 11; fM  =  0;
         break;

      case PRESET_CUSTOM:
      default:
         break;
     }

   g_rangeStartMin = rsH * 60 + rsM;
   g_rangeEndMin   = reH * 60 + reM;
   g_tradeStartMin = tsH * 60 + tsM;
   g_tradeEndMin   = teH * 60 + teM;
   g_flatMin       = fH  * 60 + fM;
   g_rangeWraps    = (g_rangeEndMin <= g_rangeStartMin);
  }

//====================================================================
//  LIFECYCLE
//====================================================================
int OnInit()
  {
   if(InpRiskPercent <= 0.0 || InpRiskPercent > 5.0)
     {
      Print("REJECTED: risk per trade must be between 0 and 5 percent.");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(InpTargetR <= 0.0)
     {
      Print("REJECTED: target R must be positive.");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(Bars(_Symbol, InpEntryTF) < 300)
     {
      Print("REJECTED: not enough history on the entry timeframe.");
      return INIT_FAILED;
     }

   g_gmtOffset = InpBrokerGMTOffset;
   if(InpAutoGMTOffset && !MQLInfoInteger(MQL_TESTER))
     {
      double detected = (double)((long)TimeTradeServer() - (long)TimeGMT()) / 3600.0;
      detected = MathRound(detected * 2.0) / 2.0;
      if(MathAbs(detected) <= 14.0)
        {
         // Strip DST so the stored value is the winter offset
         if(IsUSDST(TimeGMT())) detected -= 1.0;
         g_gmtOffset = detected;
        }
     }

   ApplyPreset();

   g_atrHandle = iATR(_Symbol, InpEntryTF, InpATRPeriod);
   if(g_atrHandle == INVALID_HANDLE) { Print("ATR handle failed."); return INIT_FAILED; }

   if(InpBiasMode == BIAS_HTF_EMA)
     {
      g_biasHandle = iMA(_Symbol, InpBiasTF, InpBiasEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
      if(g_biasHandle == INVALID_HANDLE) { Print("Bias EMA handle failed."); return INIT_FAILED; }
     }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippagePts);
   trade.SetAsyncMode(false);

   g_peakEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   ResetDay(TradeDayKey(TimeCurrent()));
   EnsureJournalHeader();

   PrintFormat("Session-Range Forge ready. preset=%s model=%s gmtOffset=%.1f "
               "range=%02d:%02d-%02d:%02d NY  entry=%02d:%02d-%02d:%02d NY  wraps=%s",
               EnumToString(InpPreset), EnumToString(InpModel), g_gmtOffset,
               g_rangeStartMin / 60, g_rangeStartMin % 60,
               g_rangeEndMin / 60, g_rangeEndMin % 60,
               g_tradeStartMin / 60, g_tradeStartMin % 60,
               g_tradeEndMin / 60, g_tradeEndMin % 60,
               (g_rangeWraps ? "yes" : "no"));
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(g_atrHandle  != INVALID_HANDLE) IndicatorRelease(g_atrHandle);
   if(g_biasHandle != INVALID_HANDLE) IndicatorRelease(g_biasHandle);
   Comment("");
   ObjectsDeleteAll(0, "SRF_");
  }

void OnTick()
  {
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq > g_peakEquity) g_peakEquity = eq;

//--- Always run: excursion tracking, management, close detection
   ManageOpenPosition();
   CheckClosedPosition();

   datetime now = TimeCurrent();

//--- Day rollover
   string key = TradeDayKey(now);
   if(key != g_dayKey) ResetDay(key);

//--- Build the range once per new range-TF bar, while inside/just after the window
   datetime rBar = iTime(_Symbol, InpRangeTF, 0);
   if(rBar != g_lastRangeBar)
     {
      g_lastRangeBar = rBar;
      if(!g_rangeReady) BuildRange();
     }

//--- Signal evaluation once per new entry-TF bar
   datetime eBar = iTime(_Symbol, InpEntryTF, 0);
   if(eBar != g_lastEntryBar)
     {
      g_lastEntryBar = eBar;

      if(g_breakDir != 0) g_barsSinceBreak++;
      if(g_sweepDir != 0) g_barsSinceSweep++;
      if(g_rangeReady)    g_barsSinceRange++;

      bool canTrade = g_rangeReady
                      && RangeAcceptable()
                      && DayEnabled(now)
                      && InTradeWindow(now)
                      && g_ticket == 0
                      && g_barsSinceRange <= InpMaxBarsToTrigger;

      if(canTrade)
        {
         double stopRef = 0.0;
         int dir = EvaluateSignal(stopRef);
         if(dir != 0 && stopRef > 0.0) OpenTrade(dir, stopRef);
        }

      // Outside the window, stand down the state machine
      if(!InTradeWindow(now) && g_ticket == 0) ResetSignal();
     }

   Dashboard();
  }

//--- Custom optimisation metric: penalise low trade counts and
//    day-concentrated results so the optimiser cannot chase noise.
double OnTester()
  {
   double trades = TesterStatistics(STAT_TRADES);
   double profit = TesterStatistics(STAT_PROFIT);
   double dd     = TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   if(trades < 100) return 0.0;                 // refuse to rank tiny samples
   if(dd <= 0.0) dd = 0.01;
   return (profit / dd) * MathSqrt(trades / 100.0);
  }
//+------------------------------------------------------------------+
