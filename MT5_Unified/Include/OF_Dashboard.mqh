//+------------------------------------------------------------------+
//|                                              OF_Dashboard.mqh    |
//|  8-row checklist + metrics panel (brief §3, §9.6)                |
//|  Renders top-right via OBJ_LABEL + CORNER_RIGHT_UPPER            |
//+------------------------------------------------------------------+
#property strict
#ifndef OF_DASHBOARD_MQH
#define OF_DASHBOARD_MQH

#include "OF_Common.mqh"

class CDashboard
  {
private:
   string m_prefix;
   color  m_okColor, m_failColor, m_waitColor;
   uint     m_lastRefresh;   // GetTickCount() millisecond timestamp

   void DrawLabel(const string name, const string text, const int row, const color clr)
     {
      const string objName = m_prefix + name;
      if(ObjectFind(0, objName) < 0)
        {
         ObjectCreate(0, objName, OBJ_LABEL, 0, 0, 0);
         ObjectSetInteger(0, objName, OBJPROP_CORNER, CORNER_RIGHT_UPPER);
         ObjectSetInteger(0, objName, OBJPROP_XDISTANCE, 12);
         ObjectSetInteger(0, objName, OBJPROP_FONTSIZE, 9);
         ObjectSetString (0, objName, OBJPROP_FONT, "Consolas");
         ObjectSetInteger(0, objName, OBJPROP_BACK, false);
         ObjectSetInteger(0, objName, OBJPROP_HIDDEN, true);
        }
      ObjectSetInteger(0, objName, OBJPROP_YDISTANCE, 14 + row * 16);
      ObjectSetString (0, objName, OBJPROP_TEXT, text);
      ObjectSetInteger(0, objName, OBJPROP_COLOR, clr);
     }

public:
   void Init(const string prefix, const color ok, const color fail, const color wait)
     { m_prefix = prefix; m_okColor = ok; m_failColor = fail; m_waitColor = wait; m_lastRefresh = 0; }

   void Deinit() { ObjectsDeleteAll(0, m_prefix); }

   //--- Throttled to 250ms (brief §23.6). TimeCurrent() is second-granular,
   //    so we use GetTickCount() for true sub-second throttling.
   bool ShouldRefresh()
     {
      const uint now = GetTickCount();
      if(now - m_lastRefresh < 250) return false;
      m_lastRefresh = now;
      return true;
     }

   //--- Render the 8-row + metrics panel (brief §3)
   void Render(const string sym, const string mode,
               const ENUM_MARKET_STATE state, const ENUM_SESSION sess,
               const ENUM_HTF_BIAS bias, const ENUM_VP_LOC loc,
               const ENUM_DIR cvdDir, const bool fpReady,
               const double sl, const double rr,
               const int score, const ENUM_PRIORITY prio,
               const double cvd, const double bd, const double volZ,
               const double poc, const double vah, const double val,
               const double dailyDD, const int trades)
     {
      DrawLabel("hdr", StringFormat("GODMODE OFEA — %s — %s", sym, mode), 0, clrWhite);

      DrawLabel("r1", StringFormat("[1] State ............ %s",
         (state == STATE_BALANCED ? "BALANCED" : state == STATE_IMBALANCED ? "IMBAL" : "UNK")),
         1, state == STATE_UNKNOWN ? m_waitColor : m_okColor);

      DrawLabel("r2", StringFormat("[2] KillZone ........ %s", SessionToStr(sess)),
         2, (sess == SESSION_LDN_MAIN || sess == SESSION_NY_MAIN) ? m_okColor : m_waitColor);

      DrawLabel("r3", StringFormat("[3] HTF ............. %s", BiasToStr(bias)),
         3, bias == BIAS_NEUTRAL ? m_waitColor : m_okColor);

      DrawLabel("r4", StringFormat("[4] VP Loc .......... %s", LocToStr(loc)),
         4, loc == LOC_NONE ? m_waitColor : m_okColor);

      DrawLabel("r5", StringFormat("[5] CVD ............. %s",
         (cvdDir == DIR_LONG ? "BULL" : cvdDir == DIR_SHORT ? "BEAR" : "FLAT")),
         5, cvdDir == DIR_NONE ? m_waitColor : m_okColor);

      DrawLabel("r6", StringFormat("[6] Footprint ....... %s", fpReady ? "OK" : "WAITING"),
         6, fpReady ? m_okColor : m_waitColor);

      DrawLabel("r7", StringFormat("[7] SL .............. %.5f", sl),
         7, sl > 0 ? m_okColor : m_waitColor);

      DrawLabel("r8", StringFormat("[8] R:R ............. %.1f", rr),
         8, rr >= 2.0 ? m_okColor : m_waitColor);

      DrawLabel("sum", StringFormat("CONF %d/8 P%d", score, (int)prio),
         9, score >= 6 ? m_okColor : m_waitColor);
      DrawLabel("met1", StringFormat("CVD %.0f Δ %.0f volZ %.2f", cvd, bd, volZ),
         10, clrLightGray);
      DrawLabel("met2", StringFormat("POC %.5f VAH %.5f VAL %.5f", poc, vah, val),
         11, clrLightGray);
      DrawLabel("met3", StringFormat("DD %.2f%% Trades %d", dailyDD, trades),
         12, dailyDD < -1.0 ? m_failColor : clrLightGray);
     }
  };

#endif
