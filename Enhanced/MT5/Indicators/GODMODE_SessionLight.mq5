//+------------------------------------------------------------------+
//| GODMODE_SessionLight.mq5 — current session light + chart shading |
//+------------------------------------------------------------------+
#property copyright "GODMODE_OFEA — Enhanced"
#property version   "2.00"
#property indicator_chart_window
#property indicator_plots 0
#property strict

input int X = 12;
input int Y = 460;
input bool ShadeBackground = true;

string pref = "GME_SES_";

int OnInit() { EventSetTimer(2); return INIT_SUCCEEDED; }
void OnDeinit(const int reason) { EventKillTimer(); ObjectsDeleteAll(0, pref); }
int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[], const double &high[],
                const double &low[], const double &close[],
                const long &tick_volume[], const long &volume[], const int &spread[])
{
   Paint(time, rates_total, low, high);
   return rates_total;
}
void OnTimer() { Paint(NULL, 0, NULL, NULL); }

struct Sess { int hStart, mStart, hEnd, mEnd; string name; color col; };

void Paint(const datetime &time[], int rt, const double &low[], const double &high[])
{
   ObjectsDeleteAll(0, pref);
   datetime now = TimeCurrent();
   MqlDateTime dt; TimeToStruct(now, dt);
   int sm = dt.hour * 60 + dt.min;

   string sess; color c;
   if      (sm >= 11*60      && sm <= 15*60+30) { sess = "LDN_MAIN";    c = clrMediumSeaGreen; }
   else if (sm >= 17*60+30   && sm <  17*60+50) { sess = "NY_BLACKOUT"; c = clrCrimson; }
   else if (sm >= 17*60+50   && sm <= 21*60)    { sess = "NY_MAIN";     c = clrDodgerBlue; }
   else if (sm >= 2*60       && sm <  9*60)     { sess = "ASIAN";       c = clrDarkOrange; }
   else                                         { sess = "AFTER/CLOSED";c = clrDimGray; }

   PutRect(pref+"dot",   X, Y, 16, 16, c);
   PutText(pref+"name",  X+24, Y-2, sess, clrWhite, 11);
   PutText(pref+"hint",  X,    Y+22, "Trade only LDN_MAIN / NY_MAIN", clrLightGray, 8);
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
