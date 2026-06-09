//+------------------------------------------------------------------+
//| GODMODE_HTFStrength.mq5 — trend strength meter per timeframe     |
//| For each of M15/H1/H4/D1: direction (▲▼), %-distance from EMA,   |
//| and ADX-style strength bar.                                      |
//+------------------------------------------------------------------+
#property copyright "GODMODE_OFEA — Enhanced"
#property version   "2.00"
#property indicator_chart_window
#property indicator_plots 0
#property strict

input int X = 12;
input int Y = 540;

string pref = "GME_HTF_";
int h_m15, h_h1, h_h4, h_d1;
int a_m15, a_h1, a_h4, a_d1;

int OnInit()
{
   h_m15 = iMA (_Symbol, PERIOD_M15, 20, 0, MODE_EMA, PRICE_CLOSE);
   h_h1  = iMA (_Symbol, PERIOD_H1,  20, 0, MODE_EMA, PRICE_CLOSE);
   h_h4  = iMA (_Symbol, PERIOD_H4,  20, 0, MODE_EMA, PRICE_CLOSE);
   h_d1  = iMA (_Symbol, PERIOD_D1,  50, 0, MODE_EMA, PRICE_CLOSE);
   a_m15 = iADX(_Symbol, PERIOD_M15, 14);
   a_h1  = iADX(_Symbol, PERIOD_H1,  14);
   a_h4  = iADX(_Symbol, PERIOD_H4,  14);
   a_d1  = iADX(_Symbol, PERIOD_D1,  14);
   // Fail-fast if any handle is invalid — otherwise CopyBuffer will silently
   // return uninitialised memory and the strength meter will paint garbage.
   if(h_m15 == INVALID_HANDLE || h_h1 == INVALID_HANDLE ||
      h_h4  == INVALID_HANDLE || h_d1 == INVALID_HANDLE ||
      a_m15 == INVALID_HANDLE || a_h1 == INVALID_HANDLE ||
      a_h4  == INVALID_HANDLE || a_d1 == INVALID_HANDLE)
      return INIT_FAILED;
   EventSetTimer(5);
   return INIT_SUCCEEDED;
}
void OnDeinit(const int r) { EventKillTimer(); ObjectsDeleteAll(0, pref);
   IndicatorRelease(h_m15); IndicatorRelease(h_h1); IndicatorRelease(h_h4); IndicatorRelease(h_d1);
   IndicatorRelease(a_m15); IndicatorRelease(a_h1); IndicatorRelease(a_h4); IndicatorRelease(a_d1); }
int OnCalculate(const int rt, const int pc, const datetime &t[], const double &o[],
                const double &h[], const double &l[], const double &c[],
                const long &tv[], const long &v[], const int &s[]) { Render(); return rt; }
void OnTimer() { Render(); }

void Render()
{
   ObjectsDeleteAll(0, pref);
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   ENUM_TIMEFRAMES tfs[] = {PERIOD_M15, PERIOD_H1, PERIOD_H4, PERIOD_D1};
   string tfn[] = {"M15", "H1", "H4", "D1"};
   int    emH[] = {h_m15, h_h1, h_h4, h_d1};
   int    adH[] = {a_m15, a_h1, a_h4, a_d1};

   PutText(pref+"hdr", X, Y, "HTF STRENGTH", clrWhite, 10);
   for (int i = 0; i < 4; i++)
   {
      double emaB[1], adxB[1];
      // BarsCalculated guard — newly-created HTF handles need a few seconds
      // before CopyBuffer can return valid data. Skip the row rather than
      // paint NaN/0 distance percentages.
      if(BarsCalculated(emH[i]) <= 0 || BarsCalculated(adH[i]) <= 0) continue;
      if(CopyBuffer(emH[i], 0, 0, 1, emaB) < 1) continue;
      if(CopyBuffer(adH[i], 0, 0, 1, adxB) < 1) continue;
      if(!MathIsValidNumber(emaB[0]) || emaB[0] <= 0) continue;
      bool bull = price > emaB[0];
      string arr = bull ? "▲" : "▼";
      double dist = MathAbs(price - emaB[0]) / MathMax(price, 1e-9) * 100.0;
      double adx  = adxB[0];
      string txt = StringFormat("%-4s %s %.2f%%  ADX %.0f", tfn[i], arr, dist, adx);
      color  c   = bull ? clrLime : clrTomato;
      PutText(pref+"row"+IntegerToString(i), X, Y + 20 + i*16, txt, c, 9);

      // ADX strength bar
      int barW = (int)MathMin(adx * 2, 100);
      PutRect(pref+"bar"+IntegerToString(i), X+200, Y + 22 + i*16, barW, 8,
              adx >= 25 ? clrGold : C'80,80,80');
   }
}
void PutText(string name, int x, int y, string t, color c, int fs)
{
   if (ObjectFind(0, name) < 0) ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, fs);
   ObjectSetString (0, name, OBJPROP_FONT, "Consolas");
   ObjectSetString (0, name, OBJPROP_TEXT, t);
}
void PutRect(string name, int x, int y, int w, int h, color c)
{
   if (ObjectFind(0, name) < 0) ObjectCreate(0, name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, c);
   ObjectSetInteger(0, name, OBJPROP_BORDER_TYPE, BORDER_FLAT);
}
