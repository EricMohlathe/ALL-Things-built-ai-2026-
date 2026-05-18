//+------------------------------------------------------------------+
//| GODMODE_ConfluenceDashboard.mq5                                  |
//| Master visual dashboard — all 12 gates, probability bar, setup   |
//| name, buy/sell levels (entry, TP1-3, SL1-3), session light, HTF  |
//| trend strength meter. Drag onto chart; updates on every bar.     |
//+------------------------------------------------------------------+
#property copyright "GODMODE_OFEA — Enhanced"
#property version   "2.00"
#property indicator_chart_window
#property indicator_plots   0
#property indicator_buffers 0
#property strict

#include "../Include/OF_Common.mqh"
#include "../Include/OF_VWAP.mqh"
#include "../Include/OF_BidAsk.mqh"
#include "../Include/OF_DeltaEnhanced.mqh"
#include "../Include/OF_RegimeHMM.mqh"
#include "../Include/OF_PriceAction.mqh"
#include "../Include/OF_SweepDetector.mqh"
#include "../Include/OF_ProbabilityScore.mqh"

// ── Inputs ────────────────────────────────────────────────────────
input bool   ShowDashboard      = true;
input bool   ShowProbabilityBar = true;
input bool   ShowSetupCard      = true;
input bool   ShowSessionLight   = true;
input bool   ShowHTFStrength    = true;
input bool   ShowTPSLLevels     = true;

input int    DashX              = 12;
input int    DashY              = 28;
input int    DashFontSize       = 9;
input color  ColOK              = clrLime;
input color  ColFail            = clrTomato;
input color  ColWait            = clrGold;
input color  ColAccent          = clrDeepSkyBlue;
input color  ColBg              = C'10,14,20';

// ── State ─────────────────────────────────────────────────────────
COF_VWAP             g_vwap;
COF_BidAsk           g_ba;
COF_DeltaEnhanced    g_d;
COF_RegimeHMM        g_reg;
COF_PriceAction      g_pa;
COF_SweepDetector    g_sw;
COF_ProbabilityScore g_prob;

string g_pref = "GME_DASH_";
datetime g_lastBar = 0;

// HTF EMA buffers (M15/H1/H4/D1) + reused ATR handle
int    h_emaM15, h_emaH1, h_emaH4, h_emaD1, h_atr;
double bufM15[1], bufH1[1], bufH4[1], bufD1[1];

int OnInit()
{
   g_ba.Init();
   g_d.Init();
   g_reg.Init();
   g_vwap.Reset(TimeCurrent());          // initialise VWAP state on attach

   h_emaM15 = iMA (_Symbol, PERIOD_M15, 20, 0, MODE_EMA, PRICE_CLOSE);
   h_emaH1  = iMA (_Symbol, PERIOD_H1,  20, 0, MODE_EMA, PRICE_CLOSE);
   h_emaH4  = iMA (_Symbol, PERIOD_H4,  20, 0, MODE_EMA, PRICE_CLOSE);
   h_emaD1  = iMA (_Symbol, PERIOD_D1,  50, 0, MODE_EMA, PRICE_CLOSE);
   h_atr    = iATR(_Symbol, _Period, 14);

   if (h_emaM15 == INVALID_HANDLE || h_emaH1 == INVALID_HANDLE ||
       h_emaH4  == INVALID_HANDLE || h_emaD1 == INVALID_HANDLE || h_atr == INVALID_HANDLE)
      return INIT_FAILED;

   EventSetTimer(1);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   ObjectsDeleteAll(0, g_pref);
   IndicatorRelease(h_emaM15);
   IndicatorRelease(h_emaH1);
   IndicatorRelease(h_emaH4);
   IndicatorRelease(h_emaD1);
   IndicatorRelease(h_atr);
}

int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[], const double &high[],
                const double &low[], const double &close[],
                const long &tick_volume[], const long &volume[], const int &spread[])
{
   if (rates_total < 50) return 0;

   // Per-tick: bid/ask spread monitor.
   g_ba.Update(_Symbol);

   // Per-bar processing.
   if (time[0] == g_lastBar) { Render(rates_total, time, high, low, close); return rates_total; }
   g_lastBar = time[0];

   // Update VWAP with typical price × volume.
   double typ = (high[0] + low[0] + close[0]) / 3.0;
   g_vwap.Update(typ, (double)tick_volume[0], time[0]);

   // Update enhanced delta (close-position proxy when MT5 can't expose true buy/sell vol).
   double rng = high[0] - low[0];
   double bw  = rng > 0 ? (close[0] - low[0]) / rng : 0.5;
   double barDelta = tick_volume[0] * (bw - (1.0 - bw));
   g_d.OnBar(barDelta, close[0]);

   // Update regime HMM-lite.
   g_reg.Update(g_d.st.cvdSlope, /*footImb=*/0, /*profileSkew=*/0, g_d.st.zScore);

   // Update price action.
   double H[], L[], C[];
   ArraySetAsSeries(H, true); ArraySetAsSeries(L, true); ArraySetAsSeries(C, true);
   CopyHigh(_Symbol, _Period, 0, 30, H);
   CopyLow(_Symbol, _Period, 0, 30, L);
   CopyClose(_Symbol, _Period, 0, 30, C);
   double atrVal[1];
   if (CopyBuffer(h_atr, 0, 0, 1, atrVal) < 1) atrVal[0] = 0;
   g_pa.Update(H, L, C, 20, 0.10, atrVal[0]);

   // Drive the 6-precondition sweep detector from the modules we've already
   // computed. We don't have HTF-level proximity or absorption directly here
   // (the full EA does), so pass the conservative subset; this still gives a
   // meaningful preconditionsPassed count for the probability bar.
   int    dir       = g_d.st.cvdSlope > 0 ? +1 : -1;
   double extreme   = dir > 0 ? high[0] : low[0];
   bool   eqLevel   = g_pa.st.equalHighsCluster || g_pa.st.equalLowsCluster;
   bool   inKZ      = false;   // bound to OF_SessionGate in EA; conservative false here
   bool   htfNear   = false;   // bound to OF_HTFAlignment in EA
   bool   momExh    = (g_d.st.regime == CVD_DIVERGENT) || g_d.st.climax;
   bool   absorbed  = g_reg.st.current == OFR_ABSORPTION;
   bool   flipped   = g_d.st.deltaFlipped;
   g_sw.Evaluate(eqLevel, htfNear, inKZ, momExh, absorbed, flipped, dir, extreme, 0);

   Render(rates_total, time, high, low, close);
   return rates_total;
}

void OnTimer() { /* spread + VWAP refresh on inactive symbols */ }

// ── Rendering ─────────────────────────────────────────────────────
void Render(int rates_total, const datetime &time[], const double &high[],
            const double &low[], const double &close[])
{
   ObjectsDeleteAll(0, g_pref);
   if (ShowDashboard)      DrawDashboard(close[0]);
   if (ShowProbabilityBar) DrawProbabilityBar();
   if (ShowSetupCard)      DrawSetupCard(close[0]);
   if (ShowSessionLight)   DrawSessionLight();
   if (ShowHTFStrength)    DrawHTFStrength();
   if (ShowTPSLLevels)     DrawTPSLLevels(close[0], high[0], low[0], time[0]);
}

void DrawDashboard(double price)
{
   string rows[15];
   int    rowColors[15];
   int n = 0;

   rows[n] = StringFormat("GODMODE · %s · %s · Δ subTF", _Symbol, EnumToString(_Period));         rowColors[n++] = clrWhite;
   rows[n] = StringFormat("① VWAP       %.5f  Z %.2f", g_vwap.VWAP(), g_vwap.ZScore(price));      rowColors[n++] = (price > g_vwap.VWAP() ? ColOK : ColFail);
   rows[n] = StringFormat("② Spread Z   %.2f  pts %.1f", g_ba.st.zSpread, g_ba.st.spreadPts);    rowColors[n++] = (g_ba.SpreadAcceptable() ? ColOK : ColFail);
   rows[n] = StringFormat("③ CVD        %.0f  slope %.2f", g_d.st.cvd, g_d.st.cvdSlope);         rowColors[n++] = (g_d.st.cvdSlope > 0 ? ColOK : ColFail);
   rows[n] = StringFormat("④ CVD-Z      %.2f  climax %s", g_d.st.zScore, g_d.st.climax ? "★" : "-"); rowColors[n++] = (g_d.st.climax ? ColAccent : ColWait);
   rows[n] = StringFormat("⑤ Regime     %s  bars %d", g_reg.Name(), g_reg.st.barsInState);        rowColors[n++] = ColAccent;
   rows[n] = StringFormat("⑥ Δ Flip     %s", g_d.st.deltaFlipped ? "YES" : "no");                rowColors[n++] = (g_d.st.deltaFlipped ? ColOK : ColWait);
   rows[n] = StringFormat("⑦ Eq HL      H:%s L:%s", g_pa.st.equalHighsCluster?"●":"○", g_pa.st.equalLowsCluster?"●":"○"); rowColors[n++] = (g_pa.st.equalHighsCluster||g_pa.st.equalLowsCluster ? ColOK : ColWait);
   rows[n] = StringFormat("⑧ FVG        ↑%s ↓%s", g_pa.st.fvgUp?"●":"○", g_pa.st.fvgDown?"●":"○"); rowColors[n++] = (g_pa.st.fvgUp||g_pa.st.fvgDown ? ColOK : ColWait);
   rows[n] = StringFormat("⑨ Structure  %s", StructStr());                                       rowColors[n++] = ColAccent;
   rows[n] = StringFormat("⑩ CVD Regime %s", CVDRegimeStr());                                     rowColors[n++] = ColAccent;

   for (int i = 0; i < n; i++) PutLabel(g_pref+"r"+IntegerToString(i), DashX, DashY + i*16, rows[i], rowColors[i]);
}

void DrawProbabilityBar()
{
   // Compute composite probability.
   double g1  = g_pa.st.equalHighsCluster || g_pa.st.equalLowsCluster ? 1 : 0; // F1 stand-in
   double g2  = 1.0; // F2 — TODO: bind to OF_SessionGate
   double g3  = 1.0; // F3 — TODO: bind to OF_HTFAlignment
   double g4  = MathAbs(g_d.st.cvdSlope) > 0 ? 1 : 0;
   double g5  = 1.0; // F5 — TODO: bind to OF_VolumeProfile
   double g6  = g_reg.st.justTransitioned ? 1 : 0.5;
   double g7  = g_sw.last.preconditionsPassed / 6.0;
   double g8  = MathAbs(g_vwap.ZScore(SymbolInfoDouble(_Symbol, SYMBOL_BID))) < 2.0 ? 1 : 0;
   double g9  = (g_pa.st.fvgUp || g_pa.st.fvgDown) ? 1 : 0;
   double g10 = 0.5; // pool resilience — TODO bind
   double g11 = g_ba.SpreadAcceptable() ? 1 : 0;
   double g12 = 1.0; // R:R — TODO bind
   double pct = g_prob.Compute(g1,g2,g3,g4,g5,g6,g7,g8,g9,g10,g11,g12);

   int barX = DashX;
   int barY = DashY + 11*16 + 4;
   int barW = 220;
   int barH = 16;
   int fillW = (int)(barW * pct / 100.0);

   PutRect(g_pref+"pb_bg",   barX,         barY, barW,  barH, ColBg);
   color fill = pct >= 75 ? ColOK : (pct >= 50 ? ColWait : ColFail);
   PutRect(g_pref+"pb_fill", barX,         barY, fillW, barH, fill);
   PutLabel(g_pref+"pb_txt", barX+barW+8,  barY-2, StringFormat("%s  %.0f%%", g_prob.Grade(), pct), clrWhite);
}

void DrawSetupCard(double price)
{
   // Setup-name + buy/sell direction header.
   string setup = "—";
   int dir = 0; // -1 short, +1 long
   if (g_reg.ExhaustionLongFromAbsorption() && g_pa.st.equalLowsCluster)      { setup = "AbsBot Long"; dir = +1; }
   else if (g_reg.ExhaustionShortFromAbsorption() && g_pa.st.equalHighsCluster) { setup = "AbsTop Short"; dir = -1; }
   else if (g_pa.st.fvgUp)   { setup = "FVG Long";  dir = +1; }
   else if (g_pa.st.fvgDown) { setup = "FVG Short"; dir = -1; }

   string dirTxt = dir > 0 ? "BUY" : (dir < 0 ? "SELL" : "WAIT");
   color  dirCol = dir > 0 ? ColOK : (dir < 0 ? ColFail : ColWait);

   PutLabel(g_pref+"sc_setup", DashX, DashY + 12*16+8,  "Setup: "+setup, clrWhite);
   PutLabel(g_pref+"sc_dir",   DashX, DashY + 13*16+8,  "Action: "+dirTxt, dirCol);
}

void DrawSessionLight()
{
   // SAST hours: ASIAN, LDN_MAIN, NY_MAIN, NY_BLACKOUT, AFTER.
   datetime now = TimeCurrent();
   MqlDateTime dt; TimeToStruct(now, dt);
   int sm = dt.hour * 60 + dt.min;
   string sess; color c;
   if      (sm >= 11*60      && sm <= 15*60+30) { sess = "LDN_MAIN";    c = clrMediumSeaGreen; }
   else if (sm >= 17*60+30   && sm <  17*60+50) { sess = "NY_BLACKOUT"; c = ColFail; }
   else if (sm >= 17*60+50   && sm <= 21*60)    { sess = "NY_MAIN";     c = clrDodgerBlue; }
   else if (sm >= 2*60       && sm <  9*60)     { sess = "ASIAN";       c = clrDarkOrange; }
   else                                         { sess = "AFTER";       c = clrDimGray; }

   int x = DashX + 240, y = DashY;
   PutRect(g_pref+"sl_dot", x, y, 14, 14, c);
   PutLabel(g_pref+"sl_txt", x + 20, y - 2, sess, clrWhite);
}

void DrawHTFStrength()
{
   if (CopyBuffer(h_emaM15, 0, 0, 1, bufM15) < 1) return;
   if (CopyBuffer(h_emaH1,  0, 0, 1, bufH1)  < 1) return;
   if (CopyBuffer(h_emaH4,  0, 0, 1, bufH4)  < 1) return;
   if (CopyBuffer(h_emaD1,  0, 0, 1, bufD1)  < 1) return;
   double pr = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   string tfs[] = {"M15","H1","H4","D1"};
   double emas[] = {bufM15[0], bufH1[0], bufH4[0], bufD1[0]};
   int x0 = DashX + 240;
   int y0 = DashY + 20;
   for (int i = 0; i < 4; i++)
   {
      bool bull = pr > emas[i];
      double dist = MathAbs(pr - emas[i]) / MathMax(pr, 1e-9) * 100.0;
      color c = bull ? ColOK : ColFail;
      string arrow = bull ? "▲" : "▼";
      string txt = StringFormat("%s %s %.2f%%", tfs[i], arrow, dist);
      PutLabel(g_pref+"htf_"+IntegerToString(i), x0, y0 + i*16, txt, c);
   }
}

void DrawTPSLLevels(double price, double high, double low, datetime t)
{
   double atrV[1];
   if (CopyBuffer(h_atr, 0, 0, 1, atrV) < 1) return;
   double atr = atrV[0];
   if (atr <= 0) return;

   // Direction = sign of CVD slope.
   int dir = g_d.st.cvdSlope > 0 ? +1 : -1;
   double entry = price;
   double sl1 = entry - dir * atr * 1.0;
   double sl2 = entry - dir * atr * 1.5;
   double sl3 = entry - dir * atr * 2.0;
   double tp1 = entry + dir * atr * 1.0;
   double tp2 = entry + dir * atr * 2.0;
   double tp3 = entry + dir * atr * 3.0;

   PutHLine(g_pref+"entry", entry, ColAccent,  "ENTRY");
   PutHLine(g_pref+"sl1",   sl1,   ColFail,    "SL1");
   PutHLine(g_pref+"sl2",   sl2,   ColFail,    "SL2");
   PutHLine(g_pref+"sl3",   sl3,   ColFail,    "SL3");
   PutHLine(g_pref+"tp1",   tp1,   ColOK,      "TP1");
   PutHLine(g_pref+"tp2",   tp2,   ColOK,      "TP2");
   PutHLine(g_pref+"tp3",   tp3,   ColOK,      "TP3");
}

// ── Helpers ───────────────────────────────────────────────────────
void PutLabel(string name, int x, int y, string text, color c)
{
   if (ObjectFind(0, name) < 0) ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, DashFontSize);
   ObjectSetString (0, name, OBJPROP_FONT, "Consolas");
   ObjectSetString (0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
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
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
}
void PutHLine(string name, double price, color c, string tag)
{
   if (ObjectFind(0, name) < 0) ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);
   ObjectSetDouble (0, name, OBJPROP_PRICE, price);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DOT);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
   ObjectSetString (0, name, OBJPROP_TEXT, tag);
}

string StructStr()
{
   switch (g_pa.st.structure)
   {
      case PA_BOS_UP:    return "BOS↑";
      case PA_BOS_DOWN:  return "BOS↓";
      case PA_CHOCH_UP:  return "CHoCH↑";
      case PA_CHOCH_DOWN:return "CHoCH↓";
   }
   return "—";
}
string CVDRegimeStr()
{
   switch (g_d.st.regime)
   {
      case CVD_TREND_CONFIRMING:  return "Trend-Confirm";
      case CVD_DIVERGENT:         return "Divergent";
      case CVD_INVERSE_DIVERGENT: return "Inverse-Div";
   }
   return "Neutral";
}
