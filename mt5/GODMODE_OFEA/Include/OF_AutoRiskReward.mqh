//+------------------------------------------------------------------+
//| OF_AutoRiskReward.mqh                                            |
//| Auto-draws an entry/SL/TP visual annotation on every fill.       |
//| Mirrors ctrader/Modules/AutoRiskReward.cs.                       |
//|                                                                  |
//| Adapted from Frozen Tundra auto_risk_reward.cpp.                 |
//| Implements brief §9.5 "Trade Lines".                             |
//+------------------------------------------------------------------+
#property strict

#include <Trade\PositionInfo.mqh>

class CAutoRiskReward
  {
private:
   string            m_symbol;
   long              m_chart_id;
   long              m_tracked_ticket;
   string            m_entry_line, m_sl_rect, m_tp_rect, m_label;
   bool              m_show_currency;

   void              ClearDrawings()
     {
      if(StringLen(m_entry_line) > 0) ObjectDelete(m_chart_id, m_entry_line);
      if(StringLen(m_sl_rect)    > 0) ObjectDelete(m_chart_id, m_sl_rect);
      if(StringLen(m_tp_rect)    > 0) ObjectDelete(m_chart_id, m_tp_rect);
      if(StringLen(m_label)      > 0) ObjectDelete(m_chart_id, m_label);
      m_entry_line = m_sl_rect = m_tp_rect = m_label = "";
     }

   void              DrawRect(const string name, const datetime t1, const double p1,
                              const datetime t2, const double p2, const color clr)
     {
      ObjectDelete(m_chart_id, name);
      if(!ObjectCreate(m_chart_id, name, OBJ_RECTANGLE, 0, t1, p1, t2, p2)) return;
      ObjectSetInteger(m_chart_id, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(m_chart_id, name, OBJPROP_FILL, true);
      ObjectSetInteger(m_chart_id, name, OBJPROP_BACK, true);
      ObjectSetInteger(m_chart_id, name, OBJPROP_SELECTABLE, false);
     }

   void              DrawLine(const string name, const datetime t1, const double p1,
                              const datetime t2, const double p2, const color clr, const int width)
     {
      ObjectDelete(m_chart_id, name);
      if(!ObjectCreate(m_chart_id, name, OBJ_TREND, 0, t1, p1, t2, p2)) return;
      ObjectSetInteger(m_chart_id, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(m_chart_id, name, OBJPROP_WIDTH, width);
      ObjectSetInteger(m_chart_id, name, OBJPROP_RAY_RIGHT, false);
      ObjectSetInteger(m_chart_id, name, OBJPROP_SELECTABLE, false);
     }

public:
   void              Init(const string symbol, const long chart_id = 0,
                          const bool show_currency = true)
     {
      m_symbol = symbol;
      m_chart_id = chart_id;
      m_tracked_ticket = 0;
      m_show_currency = show_currency;
      m_entry_line = m_sl_rect = m_tp_rect = m_label = "";
     }

   void              OnPositionOpened(const ulong ticket)
     {
      CPositionInfo pi;
      if(!pi.SelectByTicket(ticket)) return;
      if(pi.Symbol() != m_symbol) return;
      ClearDrawings();
      m_tracked_ticket = (long)ticket;
      m_entry_line = StringFormat("godmode_rr_entry_%I64u", ticket);
      m_sl_rect    = StringFormat("godmode_rr_sl_%I64u", ticket);
      m_tp_rect    = StringFormat("godmode_rr_tp_%I64u", ticket);
      m_label      = StringFormat("godmode_rr_label_%I64u", ticket);
      Redraw(ticket);
     }

   void              OnTick(const ulong ticket)
     {
      if((long)ticket != m_tracked_ticket) return;
      Redraw(ticket);
     }

   void              OnPositionClosed(const ulong ticket)
     {
      if((long)ticket != m_tracked_ticket) return;
      ClearDrawings();
      m_tracked_ticket = 0;
     }

private:
   void              Redraw(const ulong ticket)
     {
      CPositionInfo pi;
      if(!pi.SelectByTicket(ticket)) return;
      double entry = pi.PriceOpen();
      double sl = pi.StopLoss();
      double tp = pi.TakeProfit();
      if(sl == 0 || tp == 0) return;

      datetime t_start = (datetime)SeriesInfoInteger(m_symbol, PERIOD_CURRENT, SERIES_FIRSTDATE);
      // Project the right edge ~2h ahead so the rectangles look like they extend.
      datetime t_now = TimeCurrent();
      datetime t_end = t_now + 7200;

      DrawRect(m_sl_rect, t_start, entry, t_end, sl, clrRed);
      DrawRect(m_tp_rect, t_start, entry, t_end, tp, clrGreen);
      DrawLine(m_entry_line, t_start, entry, t_end, entry, clrWhite, 1);

      double risk = MathAbs(entry - sl);
      double reward = MathAbs(tp - entry);
      double rr = risk > 0 ? reward / risk : 0;
      double pip_size = SymbolInfoDouble(m_symbol, SYMBOL_POINT) *
                        ((SymbolInfoInteger(m_symbol, SYMBOL_DIGITS) == 3 ||
                          SymbolInfoInteger(m_symbol, SYMBOL_DIGITS) == 5) ? 10 : 1);
      double risk_pips = risk / pip_size;
      double reward_pips = reward / pip_size;

      string text = StringFormat("%s %.2f\nRisk: %.1f pips  Reward: %.1f pips\nR:R = %.2f",
                                 pi.PositionType() == POSITION_TYPE_BUY ? "LONG" : "SHORT",
                                 pi.Volume(), risk_pips, reward_pips, rr);
      ObjectDelete(m_chart_id, m_label);
      ObjectCreate(m_chart_id, m_label, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(m_chart_id, m_label, OBJPROP_CORNER, CORNER_RIGHT_UPPER);
      ObjectSetInteger(m_chart_id, m_label, OBJPROP_XDISTANCE, 12);
      ObjectSetInteger(m_chart_id, m_label, OBJPROP_YDISTANCE, 240);
      ObjectSetInteger(m_chart_id, m_label, OBJPROP_COLOR, clrYellow);
      ObjectSetInteger(m_chart_id, m_label, OBJPROP_FONTSIZE, 10);
      ObjectSetString (m_chart_id, m_label, OBJPROP_TEXT, text);
      ObjectSetInteger(m_chart_id, m_label, OBJPROP_SELECTABLE, false);
     }
  };
//+------------------------------------------------------------------+
