//+------------------------------------------------------------------+
//| GODMODE_BidAskSpread.mq5 — live spread monitor with z-score      |
//+------------------------------------------------------------------+
#property copyright "GODMODE_OFEA — Enhanced"
#property version   "2.00"
#property indicator_chart_window
#property indicator_plots   0
#property strict

#include "../../Include/OF_BidAsk.mqh"

input int  Window         = 120;
input int  X              = 12;
input int  Y              = 260;
input int  FontSize       = 10;
input bool ShowGate       = true;
input double MaxZ         = 2.0;

COF_BidAsk g_ba;
string pref = "GME_BA_";

int OnInit() { g_ba.Init(Window); EventSetTimer(1); return INIT_SUCCEEDED; }
void OnDeinit(const int reason) { EventKillTimer(); ObjectsDeleteAll(0, pref); }

int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[], const double &high[],
                const double &low[], const double &close[],
                const long &tick_volume[], const long &volume[], const int &spread[])
{
   g_ba.Update(_Symbol);
   Render();
   return rates_total;
}
void OnTimer() { g_ba.Update(_Symbol); Render(); }

void Render()
{
   ObjectsDeleteAll(0, pref);
   string lines[6];
   color  cols[6];
   int n = 0;
   lines[n] = StringFormat("BID/ASK MONITOR");                                cols[n++] = clrWhite;
   lines[n] = StringFormat("Bid     %.5f", g_ba.st.bid);                       cols[n++] = clrLightGray;
   lines[n] = StringFormat("Ask     %.5f", g_ba.st.ask);                       cols[n++] = clrLightGray;
   lines[n] = StringFormat("Spread  %.1f pts", g_ba.st.spreadPts);              cols[n++] = clrLightGray;
   lines[n] = StringFormat("Z-score %.2f",   g_ba.st.zSpread);                  cols[n++] = (g_ba.st.zSpread > MaxZ ? clrTomato : clrLime);
   if (ShowGate)
   { lines[n] = StringFormat("Gate    %s", g_ba.SpreadAcceptable(MaxZ)?"PASS":"FAIL"); cols[n++] = (g_ba.SpreadAcceptable(MaxZ)?clrLime:clrTomato); }
   for (int i = 0; i < n; i++) Label(pref+IntegerToString(i), X, Y+i*16, lines[i], cols[i]);
}
void Label(string name, int x, int y, string text, color c)
{
   if (ObjectFind(0, name) < 0) ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, FontSize);
   ObjectSetString (0, name, OBJPROP_FONT, "Consolas");
   ObjectSetString (0, name, OBJPROP_TEXT, text);
}
