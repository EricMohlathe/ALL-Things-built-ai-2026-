//+------------------------------------------------------------------+
//| OF_FootprintMarkers.mqh                                          |
//| Star / triangle / diamond markers for footprint signals.         |
//| Uses OBJ_ARROW with Wingdings codes for crispness at all zooms.  |
//| Brief §9.3.                                                      |
//+------------------------------------------------------------------+
#property strict
#include "OF_ChartTheme.mqh"

class COFFootprint
  {
private:
   long              m_chart;

   void              Arrow(const string name, const datetime t, const double price,
                           const ushort code, const color clr, const int size = 3,
                           const ENUM_ARROW_ANCHOR anchor = ANCHOR_TOP)
     {
      ObjectDelete(m_chart, name);
      if(!ObjectCreate(m_chart, name, OBJ_ARROW, 0, t, price)) return;
      ObjectSetInteger(m_chart, name, OBJPROP_ARROWCODE, code);
      ObjectSetInteger(m_chart, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(m_chart, name, OBJPROP_WIDTH, size);
      ObjectSetInteger(m_chart, name, OBJPROP_ANCHOR, anchor);
      ObjectSetInteger(m_chart, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(m_chart, name, OBJPROP_HIDDEN, true);
     }

   void              Badge(const string name, const datetime t, const double price,
                           const string text, const color clr)
     {
      ObjectDelete(m_chart, name);
      if(!ObjectCreate(m_chart, name, OBJ_TEXT, 0, t, price)) return;
      ObjectSetString (m_chart, name, OBJPROP_TEXT, text);
      ObjectSetString (m_chart, name, OBJPROP_FONT, OF_FONT_BOLD);
      ObjectSetInteger(m_chart, name, OBJPROP_FONTSIZE, OF_FONT_SIZE_SM);
      ObjectSetInteger(m_chart, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(m_chart, name, OBJPROP_ANCHOR, ANCHOR_LEFT);
      ObjectSetInteger(m_chart, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(m_chart, name, OBJPROP_HIDDEN, true);
     }

public:
   void              Init(const long chart_id = 0) { m_chart = chart_id; }

   // 1..5-star absorption. Star char + star count badge.
   void              Absorption(const datetime t, const double price, const bool bullish,
                                const int stars)
     {
      color clr = bullish ? OF_OK : OF_FAIL;
      string n = StringFormat("%sAbs_%I64d", OF_PREFIX, (long)t);
      Arrow(n, t, price, 171, clr, 2, bullish ? ANCHOR_TOP : ANCHOR_BOTTOM);   // ★ Wingdings 171
      Badge(n + "_b", t, price, IntegerToString(stars), OF_STAR);
     }

   void              StackedImbalance(const datetime t, const double price, const bool bullish)
     {
      color clr = bullish ? OF_ACCENT : OF_WAIT;
      string n = StringFormat("%sStk_%I64d", OF_PREFIX, (long)t);
      Arrow(n, t, price, bullish ? 233 : 234, clr, 2);   // ▲ / ▼
     }

   void              UnfinishedAuction(const datetime t, const double price)
     {
      string n = StringFormat("%sUnf_%I64d", OF_PREFIX, (long)t);
      Arrow(n, t, price, 159, OF_WAIT, 3);   // ○
     }

   void              Iceberg(const datetime t, const double price)
     {
      string n = StringFormat("%sIce_%I64d", OF_PREFIX, (long)t);
      Arrow(n, t, price, 116, OF_ICEBERG, 3);   // ◆
     }

   void              Clear()
     { ObjectsDeleteAll(m_chart, OF_PREFIX + "Abs_", 0, -1);
       ObjectsDeleteAll(m_chart, OF_PREFIX + "Stk_", 0, -1);
       ObjectsDeleteAll(m_chart, OF_PREFIX + "Unf_", 0, -1);
       ObjectsDeleteAll(m_chart, OF_PREFIX + "Ice_", 0, -1); }
  };
//+------------------------------------------------------------------+
