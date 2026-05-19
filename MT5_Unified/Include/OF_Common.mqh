//+------------------------------------------------------------------+
//|                                                    OF_Common.mqh |
//|  GODMODE_OFEA — shared enums, structs, helpers                   |
//|  Source authority: brief §6, §7, §10, §15                        |
//|  Mirrors ctrader/GODMODE_OFEA/Modules/OFCommon.cs                |
//+------------------------------------------------------------------+
#property strict
#ifndef OF_COMMON_MQH
#define OF_COMMON_MQH

//--- Operating mode (brief §0)
enum ENUM_OPMODE { OPMODE_MANUAL = 0, OPMODE_AUTO = 1 };

//--- Session classification (brief §11.6)
enum ENUM_SESSION
  {
   SESSION_NONE     = 0,
   SESSION_ASIAN    = 1,
   SESSION_LDN_OPEN = 2,
   SESSION_LDN_MAIN = 3,
   SESSION_NY_OPEN  = 4,
   SESSION_NY_MAIN  = 5,
   SESSION_AFTER    = 6
  };

//--- Sub-window tier (brief §22.6 — refinement M6)
enum ENUM_SUBTIER { SUBTIER_NONE = 0, SUBTIER_A = 1, SUBTIER_B = 2 };

//--- Profile shape (brief §11.3)
enum ENUM_PROFILE_SHAPE
  {
   SHAPE_UNKNOWN = 0,
   SHAPE_D       = 1,   // balanced
   SHAPE_P       = 2,   // bullish trend
   SHAPE_b       = 3,   // bearish trend
   SHAPE_THIN    = 4    // imbalance pending
  };

//--- Market state (brief §10.2)
enum ENUM_MARKET_STATE { STATE_UNKNOWN = 0, STATE_BALANCED = 1, STATE_IMBALANCED = 2 };

//--- HTF bias (brief §11.7)
enum ENUM_HTF_BIAS { BIAS_NEUTRAL = 0, BIAS_BULL = 1, BIAS_BEAR = 2 };

//--- Active model
enum ENUM_ACTIVE_MODEL { MODEL_NONE = 0, MODEL_M1_TREND = 1, MODEL_M2_MEANREV = 2 };

//--- VP location (brief §3 ④)
enum ENUM_VP_LOC { LOC_NONE = 0, LOC_VAL = 1, LOC_VAH = 2, LOC_POC = 3, LOC_LVN = 4, LOC_HVN = 5 };

//--- Trade direction
enum ENUM_DIR { DIR_NONE = 0, DIR_LONG = 1, DIR_SHORT = -1 };

//--- Setup IDs (brief §6 — 25 setups)
enum ENUM_SETUP_ID
  {
   SETUP_NONE         = 0,
   SETUP_ABSBOT       = 1,
   SETUP_ABSTOP       = 2,
   SETUP_CVDBEAR      = 3,
   SETUP_CVDBULL      = 4,
   SETUP_VALBNC       = 5,
   SETUP_VAHFADE      = 6,
   SETUP_POCRET       = 7,
   SETUP_LVNLONG      = 8,
   SETUP_LVNSHORT     = 9,
   SETUP_HVNREJ       = 10,
   SETUP_STACKBULL    = 11,
   SETUP_STACKBEAR    = 12,
   SETUP_PULLSTACK    = 13,
   SETUP_SPRING       = 14,
   SETUP_UPTHRUST     = 15,
   SETUP_SOS          = 16,
   SETUP_LPSY         = 17,
   SETUP_LIQSWEEP     = 18,
   SETUP_OBRETURN     = 19,
   SETUP_SMTDIV       = 20,
   SETUP_BREAKER      = 21,
   SETUP_AMD          = 22,
   SETUP_UNFAUC       = 23,
   SETUP_POORHL       = 24,
   SETUP_ICEBERG      = 25
  };

//--- Priority tier (brief §5 GATE 8)
enum ENUM_PRIORITY { PRIO_NONE = 0, PRIO_P1 = 1, PRIO_P2 = 2, PRIO_P3 = 3, PRIO_P4 = 4, PRIO_P5 = 5 };

//+------------------------------------------------------------------+
//| GateResult — every gate returns this so dashboard + journal can  |
//| render the WHY of a decision (brief §15 rule 3)                  |
//+------------------------------------------------------------------+
struct GateResult
  {
   bool   passed;
   string reason;
   double value;
  };

GateResult GR(const bool p, const string r, const double v = 0.0)
  {
   GateResult g; g.passed = p; g.reason = r; g.value = v; return g;
  }

//+------------------------------------------------------------------+
//| SetupCandidate — produced by detectors, consumed by pipeline     |
//+------------------------------------------------------------------+
struct SetupCandidate
  {
   ENUM_SETUP_ID setupId;
   ENUM_DIR      direction;
   double        entry;
   double        sl;
   double        tp;
   int           score;          // 0..5 from §5 GATE 8
   int           absStars;       // 0..5 from §11.4
   ENUM_VP_LOC   vpLoc;
   ENUM_PRIORITY priority;
   string        reason;
  };

void ResetSetupCandidate(SetupCandidate &c)
  {
   c.setupId = SETUP_NONE; c.direction = DIR_NONE;
   c.entry = 0.0; c.sl = 0.0; c.tp = 0.0;
   c.score = 0; c.absStars = 0;
   c.vpLoc = LOC_NONE; c.priority = PRIO_NONE; c.reason = "";
  }

//+------------------------------------------------------------------+
//| Helpers                                                          |
//+------------------------------------------------------------------+
string SessionToStr(const ENUM_SESSION s)
  {
   switch(s)
     {
      case SESSION_ASIAN:    return "ASIAN";
      case SESSION_LDN_OPEN: return "LDN_OPEN";
      case SESSION_LDN_MAIN: return "LDN_MAIN";
      case SESSION_NY_OPEN:  return "NY_OPEN";
      case SESSION_NY_MAIN:  return "NY_MAIN";
      case SESSION_AFTER:    return "AFTER";
     }
   return "NONE";
  }

string DirToStr(const ENUM_DIR d) { return d == DIR_LONG ? "LONG" : (d == DIR_SHORT ? "SHORT" : "NONE"); }

string LocToStr(const ENUM_VP_LOC l)
  {
   switch(l)
     {
      case LOC_VAL: return "VAL";
      case LOC_VAH: return "VAH";
      case LOC_POC: return "POC";
      case LOC_LVN: return "LVN";
      case LOC_HVN: return "HVN";
     }
   return "OUT";
  }

string ShapeToStr(const ENUM_PROFILE_SHAPE s)
  {
   switch(s)
     {
      case SHAPE_D:    return "D";
      case SHAPE_P:    return "P";
      case SHAPE_b:    return "b";
      case SHAPE_THIN: return "THIN";
     }
   return "UNK";
  }

string BiasToStr(const ENUM_HTF_BIAS b) { return b == BIAS_BULL ? "BULL" : (b == BIAS_BEAR ? "BEAR" : "NEUTRAL"); }

//--- Standard pip size (brief §11.8)
double PipSize(const string sym)
  {
   const int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   const double point = SymbolInfoDouble(sym, SYMBOL_POINT);
   return (digits == 3 || digits == 5) ? 10.0 * point : point;
  }

//--- Round a lot to broker step (brief §11.8)
double NormaliseLots(const string sym, const double raw)
  {
   const double step  = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   const double mn    = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   const double mx    = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   if(step <= 0.0) return raw;
   double lots = MathFloor(raw / step) * step;
   if(lots < mn) lots = mn;
   if(lots > mx) lots = mx;
   return NormalizeDouble(lots, 2);
  }

//--- ATR helper using built-in indicator handle cache.
//    NOTE: prior implementation called iATR() on every invocation without
//    releasing the handle — a hard resource leak that ran the terminal out
//    of indicator slots within hours of live trading. We now cache up to
//    16 (symbol|tf|period) tuples and reuse the handle across calls.
struct OF_AtrCacheEntry { string key; int handle; };
OF_AtrCacheEntry g_of_atr_cache[16];
int              g_of_atr_cache_n = 0;

double ATR(const string sym, const ENUM_TIMEFRAMES tf, const int period)
  {
   const string key = sym + "|" + IntegerToString((int)tf) + "|" + IntegerToString(period);
   int h = INVALID_HANDLE;
   for(int i = 0; i < g_of_atr_cache_n; i++)
      if(g_of_atr_cache[i].key == key) { h = g_of_atr_cache[i].handle; break; }
   if(h == INVALID_HANDLE)
     {
      h = iATR(sym, tf, period);
      if(h == INVALID_HANDLE) return 0.0;
      if(g_of_atr_cache_n < 16)
        {
         g_of_atr_cache[g_of_atr_cache_n].key    = key;
         g_of_atr_cache[g_of_atr_cache_n].handle = h;
         g_of_atr_cache_n++;
        }
      // Newly-created handles need a moment to populate; treat 0-reads as
      // "not ready" rather than zero ATR (would have NaN-divided downstream).
     }
   // BarsCalculated guard: prevents reading a half-initialised buffer that
   // would otherwise return uninitialised memory on first attach.
   if(BarsCalculated(h) <= 0) return 0.0;
   double buf[]; ArraySetAsSeries(buf, true);
   if(CopyBuffer(h, 0, 0, 1, buf) <= 0) return 0.0;
   if(!MathIsValidNumber(buf[0]) || buf[0] < 0) return 0.0;
   return buf[0];
  }

#endif
