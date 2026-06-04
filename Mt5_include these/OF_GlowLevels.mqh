//+------------------------------------------------------------------+
//| OF_GlowLevels.mqh                                                |
//| VP / S+R level drawing with a soft "glow" effect — multiple      |
//| trend lines at decreasing alpha give the illusion of a halo.     |
//| Uses standard OBJ_TREND objects (no canvas) so it scales with    |
//| zoom and survives chart reload.                                  |
//+------------------------------------------------------------------+
#property strict
#include "OF_ChartTheme.mqh"

class COFGlow
  {
private:
   long              m_chart;

   void              DrawOne(const string name, const datetime t1, const double price,
                             const datetime t2, const color clr, const int width,
                             const ENUM_LINE_STYLE style)
     {
      ObjectDelete(m_chart, name);
      if(!ObjectCreate(m_chart, name, OBJ_TREND, 0, t1, price, t2, price)) return;
      ObjectSetInteger(m_chart, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(m_chart, name, OBJPROP_WIDTH, width);
      ObjectSetInteger(m_chart, name, OBJPROP_STYLE, style);
      ObjectSetInteger(m_chart, name, OBJPROP_RAY_LEFT, false);
      ObjectSetInteger(m_chart, name, OBJPROP_RAY_RIGHT, true);
      ObjectSetInteger(m_chart, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(m_chart, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(m_chart, name, OBJPROP_BACK, true);
     }

   void              Halo(const string baseName, const datetime t1, const double price,
                          const datetime t2, const color core, const int coreWidth,
                          const ENUM_LINE_STYLE coreStyle)
     {
      // 3 stacked lines: faint wide outer, medium mid, sharp inner.
      DrawOne(baseName + "_g3", t1, price, t2, core, coreWidth + 6, STYLE_SOLID);
      DrawOne(baseName + "_g2", t1, price, t2, core, coreWidth + 3, STYLE_SOLID);
      DrawOne(baseName + "_g1", t1, price, t2, core, coreWidth,     coreStyle);
     }

public:
   void              Init(const long chart_id = 0) { m_chart = chart_id; }

   void              POC(const double price)
     { Halo(OF_PREFIX + "POC", 0, price, 0, OF_POC, 2, STYLE_SOLID); Label(OF_PREFIX + "POC_lbl", price, "POC", OF_POC); }
   void              VAH(const double price)
     { Halo(OF_PREFIX + "VAH", 0, price, 0, OF_VAH_VAL, 1, STYLE_DASH); Label(OF_PREFIX + "VAH_lbl", price, "VAH", OF_VAH_VAL); }
   void              VAL(const double price)
     { Halo(OF_PREFIX + "VAL", 0, price, 0, OF_VAH_VAL, 1, STYLE_DASH); Label(OF_PREFIX + "VAL_lbl", price, "VAL", OF_VAH_VAL); }
   void              LVN(const double price, const string tag = "LVN")
     { Halo(OF_PREFIX + tag, 0, price, 0, OF_LVN, 1, STYLE_DOT); }
   void              HVN(const double price, const string tag = "HVN")
     { Halo(OF_PREFIX + tag, 0, price, 0, OF_HVN, 1, STYLE_DOT); }

   void              Label(const string name, const double price, const string text, const color clr)
     {
      ObjectDelete(m_chart, name);
      datetime t = TimeCurrent() + PeriodSeconds(PERIOD_CURRENT) * 5;
      if(!ObjectCreate(m_chart, name, OBJ_TEXT, 0, t, price)) return;
      ObjectSetString (m_chart, name, OBJPROP_TEXT, text);
      ObjectSetString (m_chart, name, OBJPROP_FONT, OF_FONT_BOLD);
      ObjectSetInteger(m_chart, name, OBJPROP_FONTSIZE, OF_FONT_SIZE);
      ObjectSetInteger(m_chart, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(m_chart, name, OBJPROP_ANCHOR, ANCHOR_LEFT);
      ObjectSetInteger(m_chart, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(m_chart, name, OBJPROP_HIDDEN, true);
     }

   void              Clear()
     { ObjectsDeleteAll(m_chart, OF_PREFIX, 0, OBJ_TREND); ObjectsDeleteAll(m_chart, OF_PREFIX, 0, OBJ_TEXT); }
  };
//+------------------------------------------------------------------+
