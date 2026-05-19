//+------------------------------------------------------------------+
//| OF_TradeLines.mqh                                                |
//| Entry / SL / TP / partial / BE / trail / POC-exit lines + badges.|
//| Brief §9.5 trade-line spec.                                      |
//+------------------------------------------------------------------+
#property strict
#include "OF_ChartTheme.mqh"

class COFTradeLines
  {
private:
   long              m_chart;
   ulong             m_ticket;

   string            N(const string suffix) { return StringFormat("%sTL_%I64u_%s", OF_PREFIX, m_ticket, suffix); }

   void              HLine(const string name, const double price, const color clr,
                           const ENUM_LINE_STYLE style, const int width, const string text)
     {
      ObjectDelete(m_chart, name);
      if(!ObjectCreate(m_chart, name, OBJ_HLINE, 0, 0, price)) return;
      ObjectSetInteger(m_chart, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(m_chart, name, OBJPROP_STYLE, style);
      ObjectSetInteger(m_chart, name, OBJPROP_WIDTH, width);
      ObjectSetString (m_chart, name, OBJPROP_TEXT, text);
      ObjectSetInteger(m_chart, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(m_chart, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(m_chart, name, OBJPROP_BACK, true);
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
   void              Init(const long chart_id, const ulong ticket)
     { m_chart = chart_id; m_ticket = ticket; }

   void              DrawEntry(const double price, const string sizeLabel)
     { HLine(N("entry"), price, OF_TEXT, STYLE_SOLID, 2, "Entry " + sizeLabel); }

   void              DrawSL(const double price, const double pips)
     { HLine(N("sl"), price, OF_FAIL, STYLE_DASH, 1, StringFormat("SL (-%.1fp)", pips)); }

   void              DrawTP(const double price, const double pips, const double rr)
     { HLine(N("tp"), price, OF_OK, STYLE_DASH, 1, StringFormat("TP (+%.1fp / %.2fR)", pips, rr)); }

   void              MarkPartial(const datetime t, const double price)
     { Badge(N(StringFormat("partial_%I64d", (long)t)), t, price, "½", OF_WAIT); }

   void              MarkBE(const datetime t, const double price)
     { Badge(N(StringFormat("be_%I64d", (long)t)), t, price, "BE", OF_ACCENT); }

   void              UpdateTrail(const double price)
     { HLine(N("trail"), price, OF_DIM, STYLE_DOT, 1, "Trail"); }

   void              ClearAll()
     {
      string prefix = StringFormat("%sTL_%I64u_", OF_PREFIX, m_ticket);
      ObjectsDeleteAll(m_chart, prefix, 0, -1);
     }
  };
//+------------------------------------------------------------------+
