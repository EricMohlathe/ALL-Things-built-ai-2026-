//+------------------------------------------------------------------+
//|                                              OF_ChartViz.mqh     |
//|  POC/VAH/VAL/LVN/HVN lines, footprint markers, session shading,  |
//|  trade lines, divergence arrows (brief §9)                       |
//+------------------------------------------------------------------+
#property strict
#ifndef OF_CHART_VIZ_MQH
#define OF_CHART_VIZ_MQH

#include "OF_Common.mqh"

class CChartViz
  {
private:
   string m_prefix;
   bool   m_showVP, m_showFp, m_showSession, m_showTrade;

   void EnsureLine(const string name, const double price, const color clr,
                   const ENUM_LINE_STYLE style, const int width, const string lbl)
     {
      const string n = m_prefix + name;
      if(ObjectFind(0, n) < 0)
        {
         ObjectCreate(0, n, OBJ_HLINE, 0, 0, price);
         ObjectSetInteger(0, n, OBJPROP_BACK, true);
        }
      ObjectSetDouble (0, n, OBJPROP_PRICE, price);
      ObjectSetInteger(0, n, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, n, OBJPROP_STYLE, style);
      ObjectSetInteger(0, n, OBJPROP_WIDTH, width);
      ObjectSetString (0, n, OBJPROP_TEXT, lbl);
     }

public:
   void Init(const string prefix, const bool vp, const bool fp,
             const bool sess, const bool trade)
     { m_prefix = prefix; m_showVP = vp; m_showFp = fp; m_showSession = sess; m_showTrade = trade; }

   void Deinit() { ObjectsDeleteAll(0, m_prefix); }

   //--- VP lines (brief §9.1)
   void DrawVPLevels(const double poc, const double vah, const double val)
     {
      if(!m_showVP) return;
      EnsureLine("poc", poc, clrMagenta, STYLE_SOLID, 2, "POC");
      EnsureLine("vah", vah, clrDodgerBlue, STYLE_DASH, 1, "VAH");
      EnsureLine("val", val, clrDodgerBlue, STYLE_DASH, 1, "VAL");
     }

   //--- Footprint marker — single coloured arrow with star-count text
   void DrawAbsorption(const string id, const double price, const datetime t,
                       const ENUM_DIR dir, const int stars)
     {
      if(!m_showFp) return;
      const string n = m_prefix + "abs_" + id;
      if(ObjectFind(0, n) < 0)
        {
         ObjectCreate(0, n, OBJ_ARROW, 0, t, price);
         ObjectSetInteger(0, n, OBJPROP_ARROWCODE, 159);     // bullet
         ObjectSetInteger(0, n, OBJPROP_WIDTH, 3);
        }
      ObjectSetInteger(0, n, OBJPROP_COLOR, dir == DIR_LONG ? clrLime : clrRed);
      ObjectSetInteger(0, n, OBJPROP_TIME, t);
      ObjectSetDouble (0, n, OBJPROP_PRICE, price);
      // star-count tag
      const string s = m_prefix + "abs_t_" + id;
      if(ObjectFind(0, s) < 0) { ObjectCreate(0, s, OBJ_TEXT, 0, t, price); }
      ObjectSetInteger(0, s, OBJPROP_TIME, t);
      ObjectSetDouble (0, s, OBJPROP_PRICE, price);
      ObjectSetString (0, s, OBJPROP_TEXT, StringFormat("★%d", stars));
      ObjectSetInteger(0, s, OBJPROP_COLOR, dir == DIR_LONG ? clrLime : clrRed);
     }

   //--- Trade lines (brief §9.5)
   void DrawTradeLines(const double entry, const double sl, const double tp,
                       const datetime t, const ENUM_DIR dir)
     {
      if(!m_showTrade) return;
      EnsureLine("trade_entry", entry, dir == DIR_LONG ? clrLime : clrOrangeRed, STYLE_SOLID, 2, "ENTRY");
      EnsureLine("trade_sl",    sl,    clrRed,                                  STYLE_DASH,  1, "SL");
      EnsureLine("trade_tp",    tp,    clrLimeGreen,                            STYLE_DASH,  1, "TP");
     }

   //--- Session shading via OBJ_RECTANGLE_LABEL
   void DrawSessionRect(const datetime tStart, const datetime tEnd, const color clr, const string id)
     {
      if(!m_showSession) return;
      const string n = m_prefix + "sess_" + id;
      if(ObjectFind(0, n) < 0)
        {
         ObjectCreate(0, n, OBJ_RECTANGLE, 0, tStart, 0, tEnd, 0);
         ObjectSetInteger(0, n, OBJPROP_BACK, true);
         ObjectSetInteger(0, n, OBJPROP_COLOR, clr);
         ObjectSetInteger(0, n, OBJPROP_FILL, true);
         ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
        }
      // top/bottom set to chart price range — best-effort
      const double hi = ChartGetDouble(0, CHART_PRICE_MAX);
      const double lo = ChartGetDouble(0, CHART_PRICE_MIN);
      ObjectSetInteger(0, n, OBJPROP_TIME,  0, tStart);
      ObjectSetDouble (0, n, OBJPROP_PRICE, 0, hi);
      ObjectSetInteger(0, n, OBJPROP_TIME,  1, tEnd);
      ObjectSetDouble (0, n, OBJPROP_PRICE, 1, lo);
     }
  };

#endif
