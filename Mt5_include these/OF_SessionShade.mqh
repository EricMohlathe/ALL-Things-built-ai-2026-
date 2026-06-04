//+------------------------------------------------------------------+
//| OF_SessionShade.mqh                                              |
//| Translucent session backgrounds via OBJ_RECTANGLE in background  |
//| mode. Drawn once per new bar in the session window.              |
//+------------------------------------------------------------------+
#property strict
#include "OF_ChartTheme.mqh"

class COFSessionShade
  {
private:
   long              m_chart;
   double            m_top;
   double            m_bot;

   void              Rect(const string name, const datetime t1, const datetime t2, const color clr)
     {
      ObjectDelete(m_chart, name);
      double hi = ChartGetDouble(m_chart, CHART_PRICE_MAX);
      double lo = ChartGetDouble(m_chart, CHART_PRICE_MIN);
      if(!ObjectCreate(m_chart, name, OBJ_RECTANGLE, 0, t1, hi, t2, lo)) return;
      ObjectSetInteger(m_chart, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(m_chart, name, OBJPROP_FILL, true);
      ObjectSetInteger(m_chart, name, OBJPROP_BACK, true);
      ObjectSetInteger(m_chart, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(m_chart, name, OBJPROP_HIDDEN, true);
     }

public:
   void              Init(const long chart_id = 0) { m_chart = chart_id; }

   // Call each new bar; pass the SAST minute of that bar.
   // Brief §11.6 windows: LDN_MAIN 660-930, NY_MAIN 1050-1260.
   void              Update(const datetime bar_time, const int sast_minute)
     {
      datetime bar_end = bar_time + PeriodSeconds(PERIOD_CURRENT);
      string key = "";
      color clr = clrNONE;
      if(sast_minute >= 660 && sast_minute < 930) { key = "LDN"; clr = OF_SESSION_LDN; }
      else if(sast_minute >= 1050 && sast_minute < 1260) { key = "NY"; clr = OF_SESSION_NY; }
      else return;
      // one rectangle per bar — cheap and the chart redraws cleanly.
      string name = StringFormat("%sShade_%s_%I64d", OF_PREFIX, key, (long)bar_time);
      Rect(name, bar_time, bar_end, clr);
     }

   void              Clear()
     { ObjectsDeleteAll(m_chart, OF_PREFIX + "Shade_", 0, OBJ_RECTANGLE); }
  };
//+------------------------------------------------------------------+
