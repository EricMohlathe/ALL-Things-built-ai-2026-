//+------------------------------------------------------------------+
//| OF_CvdSubwindow.mqh                                              |
//| CVD line + divergence arrows in a dedicated sub-window (panel    |
//| below price). Hooks into existing OF_DeltaEngine series.         |
//| Brief §9.2.                                                      |
//+------------------------------------------------------------------+
#property strict
#include "OF_ChartTheme.mqh"

// Note: this is a *renderer*. The CVD series itself is computed in
// OF_DeltaEngine.mqh — pass the array in.

class COFCvdPanel
  {
private:
   long              m_chart;
   int               m_window;        // chart sub-window index (0 = main)

   void              Polyline(const string nameBase, const datetime &t[], const double &y[],
                              const int count, const color up, const color down)
     {
      for(int i = 1; i < count; i++)
        {
         string n = StringFormat("%sCVD_seg_%d", OF_PREFIX, i);
         ObjectDelete(m_chart, n);
         if(!ObjectCreate(m_chart, n, OBJ_TREND, m_window, t[i - 1], y[i - 1], t[i], y[i])) continue;
         color c = (y[i] >= y[i - 1]) ? up : down;
         ObjectSetInteger(m_chart, n, OBJPROP_COLOR, c);
         ObjectSetInteger(m_chart, n, OBJPROP_WIDTH, 2);
         ObjectSetInteger(m_chart, n, OBJPROP_RAY_RIGHT, false);
         ObjectSetInteger(m_chart, n, OBJPROP_SELECTABLE, false);
         ObjectSetInteger(m_chart, n, OBJPROP_HIDDEN, true);
        }
     }

public:
   void              Init(const long chart_id = 0, const int sub_window = 1)
     { m_chart = chart_id; m_window = sub_window; }

   // Pass parallel newest-first arrays (t[0]=latest bar time, y[0]=latest CVD).
   // count = number of bars to render (e.g. 100).
   void              Render(const datetime &t[], const double &y[], const int count)
     {
      // Reverse to oldest-first for sequential drawing.
      datetime tt[]; double yy[];
      ArrayResize(tt, count); ArrayResize(yy, count);
      for(int i = 0; i < count; i++) { tt[i] = t[count - 1 - i]; yy[i] = y[count - 1 - i]; }
      Polyline(OF_PREFIX + "CVD", tt, yy, count, OF_OK, OF_FAIL);
     }

   void              DivergenceArrow(const datetime t, const double y, const bool bullish)
     {
      string n = StringFormat("%sCVDdiv_%I64d", OF_PREFIX, (long)t);
      ObjectDelete(m_chart, n);
      if(!ObjectCreate(m_chart, n, OBJ_ARROW, m_window, t, y)) return;
      ObjectSetInteger(m_chart, n, OBJPROP_ARROWCODE, bullish ? 233 : 234);
      ObjectSetInteger(m_chart, n, OBJPROP_COLOR, bullish ? OF_OK : OF_FAIL);
      ObjectSetInteger(m_chart, n, OBJPROP_WIDTH, 2);
      ObjectSetInteger(m_chart, n, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(m_chart, n, OBJPROP_HIDDEN, true);
     }

   void              Clear()
     { ObjectsDeleteAll(m_chart, OF_PREFIX + "CVD_seg_", m_window, OBJ_TREND);
       ObjectsDeleteAll(m_chart, OF_PREFIX + "CVDdiv_", m_window, OBJ_ARROW); }
  };
//+------------------------------------------------------------------+
