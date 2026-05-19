//+------------------------------------------------------------------+
//| GODMODE_PriceActionLabels.mq5 — BOS/CHoCH/EqH/EqL/FVG markers    |
//+------------------------------------------------------------------+
#property copyright "GODMODE_OFEA — Enhanced"
#property version   "2.00"
#property indicator_chart_window
#property indicator_plots   0
#property strict

#include "../../Include/OF_PriceAction.mqh"

input int     SwingLookback = 20;
input double  TolEqualATR   = 0.10;
input bool    ShowFVG       = true;
input bool    ShowEqual     = true;
input bool    ShowStructure = true;

COF_PriceAction g_pa;
string pref = "GME_PA_";
datetime lastBar = 0;
int      g_hAtr = INVALID_HANDLE;

int OnInit()
{
   g_hAtr = iATR(_Symbol, _Period, 14);
   return g_hAtr == INVALID_HANDLE ? INIT_FAILED : INIT_SUCCEEDED;
}
void OnDeinit(const int reason)
{
   if (g_hAtr != INVALID_HANDLE) IndicatorRelease(g_hAtr);
   ObjectsDeleteAll(0, pref);
}

int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[], const double &high[],
                const double &low[], const double &close[],
                const long &tick_volume[], const long &volume[], const int &spread[])
{
   if (rates_total < 30) return rates_total;
   // Track the most recent CLOSED bar so structure labels don't flicker
   // on intra-bar ticks and don't lock in based on partial-bar wicks.
   const int iLast = rates_total - 2;
   if (iLast < 1) return rates_total;
   if (time[iLast] == lastBar) return rates_total;
   lastBar = time[iLast];

   double H[], L[], C[];
   ArraySetAsSeries(H, true); ArraySetAsSeries(L, true); ArraySetAsSeries(C, true);
   // Check CopyHigh/Low/Close return values — at session boundaries these
   // can briefly fail; skip the update rather than feed undersized arrays
   // into Update() (which would index past the end inside the swing scan).
   if (CopyHigh (_Symbol, _Period, 0, 50, H) < 50) return rates_total;
   if (CopyLow  (_Symbol, _Period, 0, 50, L) < 50) return rates_total;
   if (CopyClose(_Symbol, _Period, 0, 50, C) < 50) return rates_total;
   double atrV[1];
   if (CopyBuffer(g_hAtr, 0, 0, 1, atrV) < 1) atrV[0] = 0;
   g_pa.Update(H, L, C, SwingLookback, TolEqualATR, atrV[0]);

   ObjectsDeleteAll(0, pref);
   if (ShowStructure && g_pa.st.structure != PA_NONE) DrawStruct(time[rates_total-1], close[rates_total-1]);
   if (ShowEqual)     DrawEqual(time[rates_total-1]);
   if (ShowFVG)       DrawFVG(time[rates_total-1]);
   return rates_total;
}
void DrawStruct(datetime t, double price)
{
   string txt; color c;
   switch (g_pa.st.structure)
   {
      case PA_BOS_UP:    txt="BOS↑";    c=clrLime;   break;
      case PA_BOS_DOWN:  txt="BOS↓";    c=clrTomato; break;
      case PA_CHOCH_UP:  txt="CHoCH↑";  c=clrLime;   break;
      case PA_CHOCH_DOWN:txt="CHoCH↓";  c=clrTomato; break;
      default: return;
   }
   string name = pref+"struct";
   if (ObjectFind(0, name) < 0) ObjectCreate(0, name, OBJ_TEXT, 0, t, price);
   ObjectSetInteger(0, name, OBJPROP_TIME, t);
   ObjectSetDouble (0, name, OBJPROP_PRICE, price);
   ObjectSetString (0, name, OBJPROP_TEXT, txt);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 11);
}
void DrawEqual(datetime t)
{
   if (g_pa.st.equalHighsCluster)
   {
      string n = pref+"eqH";
      if (ObjectFind(0, n) < 0) ObjectCreate(0, n, OBJ_HLINE, 0, 0, g_pa.st.lastSwingHigh);
      ObjectSetDouble (0, n, OBJPROP_PRICE, g_pa.st.lastSwingHigh);
      ObjectSetInteger(0, n, OBJPROP_COLOR, clrOrange);
      ObjectSetInteger(0, n, OBJPROP_STYLE, STYLE_DASH);
      ObjectSetString (0, n, OBJPROP_TEXT, "Equal Highs (liquidity)");
   }
   if (g_pa.st.equalLowsCluster)
   {
      string n = pref+"eqL";
      if (ObjectFind(0, n) < 0) ObjectCreate(0, n, OBJ_HLINE, 0, 0, g_pa.st.lastSwingLow);
      ObjectSetDouble (0, n, OBJPROP_PRICE, g_pa.st.lastSwingLow);
      ObjectSetInteger(0, n, OBJPROP_COLOR, clrOrange);
      ObjectSetInteger(0, n, OBJPROP_STYLE, STYLE_DASH);
      ObjectSetString (0, n, OBJPROP_TEXT, "Equal Lows (liquidity)");
   }
}
void DrawFVG(datetime t)
{
   if (g_pa.st.fvgUp)
   { Rect(pref+"fvgUp",   t, g_pa.st.fvgUpBot,   t+3600*8, g_pa.st.fvgUpTop,   C'40,90,40'); }
   if (g_pa.st.fvgDown)
   { Rect(pref+"fvgDown", t, g_pa.st.fvgDownBot, t+3600*8, g_pa.st.fvgDownTop, C'120,40,40'); }
}
void Rect(string name, datetime t1, double p1, datetime t2, double p2, color c)
{
   if (ObjectFind(0, name) < 0) ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, p1, t2, p2);
   ObjectSetInteger(0, name, OBJPROP_TIME, 0, t1);
   ObjectSetDouble (0, name, OBJPROP_PRICE, 0, p1);
   ObjectSetInteger(0, name, OBJPROP_TIME, 1, t2);
   ObjectSetDouble (0, name, OBJPROP_PRICE, 1, p2);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_BACK, true);
   ObjectSetInteger(0, name, OBJPROP_FILL, true);
}
