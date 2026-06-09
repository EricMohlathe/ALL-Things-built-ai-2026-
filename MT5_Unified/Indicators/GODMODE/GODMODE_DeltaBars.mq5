//+------------------------------------------------------------------+
//| GODMODE_DeltaBars.mq5 — bar-delta histogram + climax markers     |
//+------------------------------------------------------------------+
#property copyright "GODMODE_OFEA — Enhanced"
#property version   "2.00"
#property indicator_separate_window
#property indicator_buffers 4
#property indicator_plots   4
#property indicator_label1  "Delta+"
#property indicator_label2  "Delta-"
#property indicator_label3  "CVD"
#property indicator_label4  "Climax"
#property indicator_color1  clrLime
#property indicator_color2  clrTomato
#property indicator_color3  clrGold
#property indicator_color4  clrMagenta
#property indicator_type1   DRAW_HISTOGRAM
#property indicator_type2   DRAW_HISTOGRAM
#property indicator_type3   DRAW_LINE
#property indicator_type4   DRAW_ARROW
#property indicator_width1  3
#property indicator_width2  3
#property indicator_width3  2

#include "../../Include/OF_DeltaEnhanced.mqh"

input double ClimaxZ = 2.0;
input int    Lookback = 20;

double bP[], bN[], bC[], bX[];
COF_DeltaEnhanced g_d;

int OnInit()
{
   SetIndexBuffer(0, bP); SetIndexBuffer(1, bN); SetIndexBuffer(2, bC); SetIndexBuffer(3, bX);
   PlotIndexSetInteger(3, PLOT_ARROW, 159);
   g_d.Init(Lookback);
   IndicatorSetString(INDICATOR_SHORTNAME, "GODMODE Delta");
   return INIT_SUCCEEDED;
}
int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[], const double &high[],
                const double &low[], const double &close[],
                const long &tick_volume[], const long &volume[], const int &spread[])
{
   // Prior version used `start = prev_calculated - 1` and re-called
   // g_d.OnBar() on the same bar for every tick — running cumulative CVD
   // would double-count tens of thousands of times per session. We only
   // step the model forward on confirmed bars (≤ rates_total-2) and paint
   // the forming bar (rates_total-1) without advancing the accumulator.
   int start = prev_calculated > 0 ? prev_calculated - 1 : 0;
   for (int i = start; i < rates_total - 1; i++)
   {
      double rng = high[i] - low[i];
      double bw  = rng > 0 ? (close[i] - low[i]) / rng : 0.5;
      double bd  = tick_volume[i] * (bw - (1.0 - bw));
      g_d.OnBar(bd, close[i], ClimaxZ);
      bP[i] = bd > 0 ? bd : 0;
      bN[i] = bd < 0 ? bd : 0;
      bC[i] = g_d.st.cvd;
      bX[i] = g_d.st.climax ? bd : EMPTY_VALUE;
   }
   if (rates_total > 0)
   {
      const int iF = rates_total - 1;
      double rng = high[iF] - low[iF];
      double bw  = rng > 0 ? (close[iF] - low[iF]) / rng : 0.5;
      double bd  = tick_volume[iF] * (bw - (1.0 - bw));
      bP[iF] = bd > 0 ? bd : 0;
      bN[iF] = bd < 0 ? bd : 0;
      bC[iF] = g_d.st.cvd;       // last-committed CVD; advances at bar close
      bX[iF] = EMPTY_VALUE;
   }
   return rates_total;
}
