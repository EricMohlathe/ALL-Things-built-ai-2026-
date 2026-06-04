//+------------------------------------------------------------------+
//|                                               GODMODE_Core.mqh    |
//|        Shared engine for the GODMODE Master EA Library (MT5)      |
//|                                                                  |
//|  Every archetype EA in this library #includes this file and      |
//|  reuses: risk-based sizing (tuned for $10-$100 accounts),        |
//|  session clock, daily kill-switches, trade management, and a     |
//|  CSV journal that logs ENTRIES *and* SKIPS (so per-setup win     |
//|  rate has a denominator). See README.md.                         |
//+------------------------------------------------------------------+
#ifndef GODMODE_CORE_MQH
#define GODMODE_CORE_MQH

#include <Trade/Trade.mqh>

//==================================================================
//  ENUMS
//==================================================================
enum GM_RiskMode
  {
   RISK_CONSERVATIVE = 0,  // 1-2% risk, capital protection first
   RISK_AGGRESSIVE   = 1,  // higher risk %, faster compounding
   RISK_FLIP         = 2   // max risk for $10->big attempts (HIGH blow-up odds)
  };

enum GM_Dir { GM_NONE = 0, GM_LONG = 1, GM_SHORT = -1 };

//==================================================================
//  BASIC HELPERS
//==================================================================
double GM_PipSize()
  {
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(digits == 3 || digits == 5)
      return point * 10.0;
   return point;
  }

// New-bar detection on a given timeframe. Caller owns the lastBarTime store.
bool GM_IsNewBar(const ENUM_TIMEFRAMES tf, datetime &lastBarTime)
  {
   datetime t = iTime(_Symbol, tf, 0);
   if(t != lastBarTime)
     {
      lastBarTime = t;
      return true;
     }
   return false;
  }

// Resolve the active risk % from the chosen mode.
double GM_ResolveRiskPct(const GM_RiskMode mode, const double conservativePct,
                         const double aggressivePct, const double flipPct)
  {
   switch(mode)
     {
      case RISK_CONSERVATIVE: return conservativePct;
      case RISK_AGGRESSIVE:   return aggressivePct;
      case RISK_FLIP:         return flipPct;
     }
   return conservativePct;
  }

//==================================================================
//  POSITION SIZING  (the part that actually matters for $10 accounts)
//==================================================================
// Converts a risk % + stop distance into a broker-legal lot size.
// maxRiskMultiple: if the broker minimum lot would risk more than
// this multiple of the target risk, the trade is REJECTED (returns 0)
// in Conservative/Aggressive mode. In Flip mode the guard is relaxed.
double GM_CalcLots(const double slDistancePrice, const double riskPct,
                   const double maxRiskMultiple)
  {
   if(slDistancePrice <= 0.0 || riskPct <= 0.0)
      return 0.0;

   double equity     = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskMoney  = equity * riskPct / 100.0;
   double tickValue  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue <= 0.0 || tickSize <= 0.0)
      return 0.0;

   double valuePerPrice = tickValue / tickSize;          // money per 1.0 price / 1 lot
   double rawLots       = riskMoney / (slDistancePrice * valuePerPrice);

   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(step <= 0.0) step = 0.01;

   double lots = MathFloor(rawLots / step) * step;

   if(lots < vmin)
     {
      // Tiny-account reality: the minimum lot may risk far more than target.
      double effRisk = vmin * slDistancePrice * valuePerPrice;
      if(effRisk > riskMoney * maxRiskMultiple)
         return 0.0;          // would exceed the risk budget -> skip
      lots = vmin;
     }
   if(lots > vmax) lots = vmax;
   return lots;
  }

double GM_NormalizeVolume(const double v)
  {
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   if(step <= 0.0) step = 0.01;
   double n = MathFloor(v / step) * step;
   if(n < vmin) n = 0.0;
   return n;
  }

//==================================================================
//  SESSION CLOCK  (offset-from-server, e.g. SAST = UTC+2)
//==================================================================
int GM_MinuteOfDay(const int offsetHours)
  {
   MqlDateTime st;
   TimeToStruct(TimeCurrent(), st);
   int h = st.hour + offsetHours;
   while(h >= 24) h -= 24;
   while(h <  0)  h += 24;
   return h * 60 + st.min;
  }

// startMin/endMin are minutes-from-midnight in the offset timezone.
// Handles windows that wrap past midnight.
bool GM_InWindow(const int minuteOfDay, const int startMin, const int endMin)
  {
   if(startMin <= endMin)
      return (minuteOfDay >= startMin && minuteOfDay < endMin);
   return (minuteOfDay >= startMin || minuteOfDay < endMin);
  }

//==================================================================
//  DAILY GUARDS  (kill switches)
//==================================================================
class CGMGuards
  {
private:
   double   m_dayStartEquity;
   bool     m_halted;
   datetime m_lastDay;
   long     m_magic;
public:
   void Init(const long magic)
     {
      m_magic          = magic;
      m_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
      m_halted         = false;
      m_lastDay        = 0;
     }

   // Returns true on the first call of a new calendar day.
   bool IsNewDay()
     {
      MqlDateTime s;
      TimeToStruct(TimeCurrent(), s);
      datetime d = StringToTime(StringFormat("%04d.%02d.%02d", s.year, s.mon, s.day));
      if(d != m_lastDay)
        {
         m_lastDay = d;
         return true;
        }
      return false;
     }

   void OnNewDay()
     {
      m_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
      m_halted         = false;
     }

   double DailyDDPct()
     {
      if(m_dayStartEquity <= 0.0) return 0.0;
      return (AccountInfoDouble(ACCOUNT_EQUITY) - m_dayStartEquity) / m_dayStartEquity * 100.0;
     }

   bool DailyDDBreached(const double maxDDpct) { return DailyDDPct() <= -maxDDpct; }
   void Halt()       { m_halted = true; }
   bool IsHalted()   { return m_halted; }

   // Spread guard: current spread (points) vs a multiple of the typical spread.
   bool SpreadOK(const double maxSpreadPoints)
     {
      if(maxSpreadPoints <= 0.0) return true;
      double spread = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
      return spread <= maxSpreadPoints;
     }

   // Count of consecutive losing CLOSED trades for this magic, today.
   int TrailingLossStreak()
     {
      MqlDateTime s;
      TimeToStruct(TimeCurrent(), s);
      datetime from = StringToTime(StringFormat("%04d.%02d.%02d", s.year, s.mon, s.day));
      if(!HistorySelect(from, TimeCurrent()))
         return 0;
      int total  = HistoryDealsTotal();
      int streak = 0;
      for(int i = total - 1; i >= 0; i--)
        {
         ulong ticket = HistoryDealGetTicket(i);
         if(ticket == 0) continue;
         if(HistoryDealGetInteger(ticket, DEAL_MAGIC) != m_magic) continue;
         if(HistoryDealGetInteger(ticket, DEAL_ENTRY) != DEAL_ENTRY_OUT) continue;
         double profit = HistoryDealGetDouble(ticket, DEAL_PROFIT)
                       + HistoryDealGetDouble(ticket, DEAL_SWAP)
                       + HistoryDealGetDouble(ticket, DEAL_COMMISSION);
         if(profit < 0.0) streak++;
         else             break;
        }
      return streak;
     }
  };

//==================================================================
//  TRADE MANAGER  (open + BE + partial + ATR trail)
//==================================================================
class CGMTrade
  {
private:
   CTrade m_trade;
   long   m_magic;
   string m_sym;
   ulong  m_lastTicket;
   bool   m_beDone;
   bool   m_partialDone;
   ulong  m_sel;
public:
   void Init(const long magic)
     {
      m_magic       = magic;
      m_sym         = _Symbol;
      m_lastTicket  = 0;
      m_beDone      = false;
      m_partialDone = false;
      m_trade.SetExpertMagicNumber(magic);
      m_trade.SetTypeFillingBySymbol(_Symbol);
     }

   bool SelectMine()
     {
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong t = PositionGetTicket(i);
         if(t == 0) continue;
         if(PositionGetInteger(POSITION_MAGIC)  == m_magic &&
            PositionGetString(POSITION_SYMBOL)  == m_sym)
           { m_sel = t; return true; }
        }
      return false;
     }

   bool HasPosition() { return SelectMine(); }

   bool Open(const GM_Dir dir, const double lots, const double sl,
             const double tp, const string comment)
     {
      if(lots <= 0.0 || dir == GM_NONE) return false;
      m_beDone = false; m_partialDone = false;
      bool ok = false;
      if(dir == GM_LONG)  ok = m_trade.Buy (lots, m_sym, 0.0, sl, tp, comment);
      if(dir == GM_SHORT) ok = m_trade.Sell(lots, m_sym, 0.0, sl, tp, comment);
      return ok;
     }

   void CloseAll()
     {
      if(SelectMine())
         m_trade.PositionClose(m_sym);
     }

   void Manage(const double beAtR, const double partialAtR, const double partialPct,
               const bool useTrail, const double trailAtrMult, const double atrValue)
     {
      if(!SelectMine()) { m_lastTicket = 0; return; }
      if(m_sel != m_lastTicket) { m_lastTicket = m_sel; m_beDone = false; m_partialDone = false; }

      long   type  = PositionGetInteger(POSITION_TYPE);
      double entry = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl    = PositionGetDouble(POSITION_SL);
      double tp    = PositionGetDouble(POSITION_TP);
      double vol   = PositionGetDouble(POSITION_VOLUME);
      double cur   = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(m_sym, SYMBOL_BID)
                                                 : SymbolInfoDouble(m_sym, SYMBOL_ASK);
      double risk  = MathAbs(entry - sl);
      if(risk <= 0.0) return;
      double rMult = (type == POSITION_TYPE_BUY) ? (cur - entry) / risk : (entry - cur) / risk;

      // Partial close at R
      if(partialAtR > 0.0 && partialPct > 0.0 && !m_partialDone && rMult >= partialAtR)
        {
         double closeVol = GM_NormalizeVolume(vol * partialPct / 100.0);
         if(closeVol > 0.0 && closeVol < vol)
           { if(m_trade.PositionClosePartial(m_sym, closeVol)) m_partialDone = true; }
        }

      // Break-even
      if(beAtR > 0.0 && !m_beDone && rMult >= beAtR)
        {
         double be = (type == POSITION_TYPE_BUY) ? entry + GM_PipSize() : entry - GM_PipSize();
         if(m_trade.PositionModify(m_sym, be, tp)) m_beDone = true;
        }

      // ATR trailing stop
      if(useTrail && atrValue > 0.0 && rMult >= beAtR)
        {
         double newSl = (type == POSITION_TYPE_BUY) ? cur - atrValue * trailAtrMult
                                                    : cur + atrValue * trailAtrMult;
         double curSl = PositionGetDouble(POSITION_SL);
         bool tighter = (type == POSITION_TYPE_BUY) ? (newSl > curSl)
                                                    : (newSl < curSl || curSl == 0.0);
         if(tighter) m_trade.PositionModify(m_sym, newSl, tp);
        }
     }
  };

//==================================================================
//  CSV JOURNAL  (logs ENTRIES and SKIPS - the denominator matters)
//==================================================================
class CGMLogger
  {
private:
   string m_file;
public:
   void Init(const string fileName)
     {
      m_file = fileName;
      if(!FileIsExist(m_file, FILE_COMMON))
        {
         int h = FileOpen(m_file, FILE_WRITE | FILE_CSV | FILE_COMMON | FILE_ANSI, ',');
         if(h != INVALID_HANDLE)
           {
            FileWrite(h, "time_utc", "ea", "symbol", "event", "dir",
                      "entry", "sl", "tp", "lots", "rr", "score", "note");
            FileClose(h);
           }
        }
     }

   void Log(const string ea, const string evt, const GM_Dir dir, const double entry,
            const double sl, const double tp, const double lots, const double rr,
            const int score, const string note)
     {
      int h = FileOpen(m_file, FILE_READ | FILE_WRITE | FILE_CSV | FILE_COMMON | FILE_ANSI, ',');
      if(h == INVALID_HANDLE) return;
      FileSeek(h, 0, SEEK_END);
      string ds = (dir == GM_LONG) ? "LONG" : (dir == GM_SHORT ? "SHORT" : "NONE");
      FileWrite(h, TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS), ea, _Symbol,
                evt, ds, DoubleToString(entry, _Digits), DoubleToString(sl, _Digits),
                DoubleToString(tp, _Digits), DoubleToString(lots, 2),
                DoubleToString(rr, 2), IntegerToString(score), note);
      FileClose(h);
     }
  };

//==================================================================
//  SWING / STRUCTURE HELPERS  (shared by SMC/ICT archetypes)
//==================================================================
// Highest high / lowest low over a lookback (excludes the live bar 0).
double GM_HighestHigh(const int lookback, const int startShift = 1)
  {
   double hi = -DBL_MAX;
   for(int i = startShift; i < startShift + lookback; i++)
     {
      double h = iHigh(_Symbol, PERIOD_CURRENT, i);
      if(h > hi) hi = h;
     }
   return hi;
  }

double GM_LowestLow(const int lookback, const int startShift = 1)
  {
   double lo = DBL_MAX;
   for(int i = startShift; i < startShift + lookback; i++)
     {
      double l = iLow(_Symbol, PERIOD_CURRENT, i);
      if(l < lo) lo = l;
     }
   return lo;
  }

// Bullish FVG between bar i (low) and bar i+2 (high): returns true and fills
// top/bottom of the most recent unfilled gap inside lookback.
bool GM_FindBullishFVG(const int lookback, double &top, double &bottom)
  {
   for(int i = 1; i < lookback; i++)
     {
      double lo  = iLow (_Symbol, PERIOD_CURRENT, i);
      double hi2 = iHigh(_Symbol, PERIOD_CURRENT, i + 2);
      if(lo > hi2)               // gap exists
        { top = lo; bottom = hi2; return true; }
     }
   return false;
  }

bool GM_FindBearishFVG(const int lookback, double &top, double &bottom)
  {
   for(int i = 1; i < lookback; i++)
     {
      double hi  = iHigh(_Symbol, PERIOD_CURRENT, i);
      double lo2 = iLow (_Symbol, PERIOD_CURRENT, i + 2);
      if(hi < lo2)
        { top = lo2; bottom = hi; return true; }
     }
   return false;
  }

// Bullish order block: the last DOWN candle immediately before a strong
// bullish displacement candle. Returns its high/low as the OB zone.
bool GM_FindBullishOB(const int lookback, const double atrVal, const double dispMult,
                      double &obTop, double &obBot)
  {
   if(atrVal <= 0.0) return false;
   for(int d = 1; d < lookback; d++)
     {
      double o = iOpen (_Symbol, PERIOD_CURRENT, d);
      double c = iClose(_Symbol, PERIOD_CURRENT, d);
      bool bullDisp = (c > o) && ((c - o) > dispMult * atrVal);
      if(!bullDisp) continue;
      for(int j = d + 1; j <= d + 5 && j < lookback; j++)
        {
         double oj = iOpen (_Symbol, PERIOD_CURRENT, j);
         double cj = iClose(_Symbol, PERIOD_CURRENT, j);
         if(cj < oj)                           // last bearish candle before the push
           { obTop = iHigh(_Symbol, PERIOD_CURRENT, j); obBot = iLow(_Symbol, PERIOD_CURRENT, j); return true; }
        }
     }
   return false;
  }

// Bearish order block: last UP candle before a strong bearish displacement.
bool GM_FindBearishOB(const int lookback, const double atrVal, const double dispMult,
                      double &obTop, double &obBot)
  {
   if(atrVal <= 0.0) return false;
   for(int d = 1; d < lookback; d++)
     {
      double o = iOpen (_Symbol, PERIOD_CURRENT, d);
      double c = iClose(_Symbol, PERIOD_CURRENT, d);
      bool bearDisp = (c < o) && ((o - c) > dispMult * atrVal);
      if(!bearDisp) continue;
      for(int j = d + 1; j <= d + 5 && j < lookback; j++)
        {
         double oj = iOpen (_Symbol, PERIOD_CURRENT, j);
         double cj = iClose(_Symbol, PERIOD_CURRENT, j);
         if(cj > oj)
           { obTop = iHigh(_Symbol, PERIOD_CURRENT, j); obBot = iLow(_Symbol, PERIOD_CURRENT, j); return true; }
        }
     }
   return false;
  }

// ---- Standard-deviation / measured-move projection ----------------
// Project a multiple of a reference range from a level, in dir (+1 up,-1 down).
// Used for "SD" targets a la Quarterly Theory / Lumi (a measured move, not a
// statistical sigma). GM07 separately uses true statistical VWAP std-dev bands.
double GM_SDExtension(const double fromLevel, const double rangeSize,
                      const int dir, const double mult)
  { return fromLevel + (double)dir * mult * rangeSize; }

// ---- Price-action trigger candles (Nial Fuller set) ---------------
bool GM_IsBullPin(const int ago)
  {
   double h=iHigh(_Symbol,PERIOD_CURRENT,ago), l=iLow(_Symbol,PERIOD_CURRENT,ago);
   double o=iOpen(_Symbol,PERIOD_CURRENT,ago), c=iClose(_Symbol,PERIOD_CURRENT,ago);
   double rng=h-l; if(rng<=0) return false;
   return (MathMin(o,c)-l)/rng >= 0.6;            // long lower tail
  }
bool GM_IsBearPin(const int ago)
  {
   double h=iHigh(_Symbol,PERIOD_CURRENT,ago), l=iLow(_Symbol,PERIOD_CURRENT,ago);
   double o=iOpen(_Symbol,PERIOD_CURRENT,ago), c=iClose(_Symbol,PERIOD_CURRENT,ago);
   double rng=h-l; if(rng<=0) return false;
   return (h-MathMax(o,c))/rng >= 0.6;            // long upper tail
  }
bool GM_IsBullEngulf()
  {
   double o1=iOpen(_Symbol,PERIOD_CURRENT,1), c1=iClose(_Symbol,PERIOD_CURRENT,1);
   double o2=iOpen(_Symbol,PERIOD_CURRENT,2), c2=iClose(_Symbol,PERIOD_CURRENT,2);
   return c2<o2 && c1>o1 && o1<=c2 && c1>=o2;
  }
bool GM_IsBearEngulf()
  {
   double o1=iOpen(_Symbol,PERIOD_CURRENT,1), c1=iClose(_Symbol,PERIOD_CURRENT,1);
   double o2=iOpen(_Symbol,PERIOD_CURRENT,2), c2=iClose(_Symbol,PERIOD_CURRENT,2);
   return c2>o2 && c1<o1 && o1>=c2 && c1<=o2;
  }
bool GM_IsInsideBar()
  {
   return iHigh(_Symbol,PERIOD_CURRENT,1) < iHigh(_Symbol,PERIOD_CURRENT,2) &&
          iLow (_Symbol,PERIOD_CURRENT,1) > iLow (_Symbol,PERIOD_CURRENT,2);
  }

// ---- ICT Optimal Trade Entry (0.62-0.79 retracement zone) ---------
bool GM_OTELong(const int lookback, double &zTop, double &zBot)
  {
   double hi=GM_HighestHigh(lookback,1), lo=GM_LowestLow(lookback,1);
   double r=hi-lo; if(r<=0) return false;
   zTop = hi - 0.62*r;     // shallow edge
   zBot = hi - 0.79*r;     // deep edge
   return true;
  }
bool GM_OTEShort(const int lookback, double &zTop, double &zBot)
  {
   double hi=GM_HighestHigh(lookback,1), lo=GM_LowestLow(lookback,1);
   double r=hi-lo; if(r<=0) return false;
   zBot = lo + 0.62*r;
   zTop = lo + 0.79*r;
   return true;
  }

// ---- Fractal swings (wing bars each side; shift>=wing+1 to be closed) ----
bool GM_IsSwingHigh(const int shift, const int wing)
  {
   double h=iHigh(_Symbol,PERIOD_CURRENT,shift);
   for(int k=1;k<=wing;k++)
     { if(iHigh(_Symbol,PERIOD_CURRENT,shift-k)>=h) return false;
       if(iHigh(_Symbol,PERIOD_CURRENT,shift+k)>h)  return false; }
   return true;
  }
bool GM_IsSwingLow(const int shift, const int wing)
  {
   double l=iLow(_Symbol,PERIOD_CURRENT,shift);
   for(int k=1;k<=wing;k++)
     { if(iLow(_Symbol,PERIOD_CURRENT,shift-k)<=l) return false;
       if(iLow(_Symbol,PERIOD_CURRENT,shift+k)<l)  return false; }
   return true;
  }
bool GM_LastSwingHigh(const int lookback, const int wing, double &price, int &shift)
  {
   for(int s=wing+1;s<=lookback;s++)
      if(GM_IsSwingHigh(s,wing)){price=iHigh(_Symbol,PERIOD_CURRENT,s);shift=s;return true;}
   return false;
  }
bool GM_LastSwingLow(const int lookback, const int wing, double &price, int &shift)
  {
   for(int s=wing+1;s<=lookback;s++)
      if(GM_IsSwingLow(s,wing)){price=iLow(_Symbol,PERIOD_CURRENT,s);shift=s;return true;}
   return false;
  }

// ---- Supply & Demand bases: small-range base candle + displacement leave ----
bool GM_FindDemandBase(const int lookback,const double atr,const double dispMult,const double baseMaxMult,double &top,double &bot)
  {
   if(atr<=0) return false;
   for(int d=1;d<lookback-1;d++)
     {
      double o=iOpen(_Symbol,PERIOD_CURRENT,d),c=iClose(_Symbol,PERIOD_CURRENT,d);
      if(!(c>o && (c-o)>dispMult*atr)) continue;
      double bh=iHigh(_Symbol,PERIOD_CURRENT,d+1),bl=iLow(_Symbol,PERIOD_CURRENT,d+1);
      if(bh-bl<baseMaxMult*atr){top=bh;bot=bl;return true;}
     }
   return false;
  }
bool GM_FindSupplyBase(const int lookback,const double atr,const double dispMult,const double baseMaxMult,double &top,double &bot)
  {
   if(atr<=0) return false;
   for(int d=1;d<lookback-1;d++)
     {
      double o=iOpen(_Symbol,PERIOD_CURRENT,d),c=iClose(_Symbol,PERIOD_CURRENT,d);
      if(!(c<o && (o-c)>dispMult*atr)) continue;
      double bh=iHigh(_Symbol,PERIOD_CURRENT,d+1),bl=iLow(_Symbol,PERIOD_CURRENT,d+1);
      if(bh-bl<baseMaxMult*atr){top=bh;bot=bl;return true;}
     }
   return false;
  }

#endif // GODMODE_CORE_MQH
//+------------------------------------------------------------------+
