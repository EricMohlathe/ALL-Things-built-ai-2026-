//+------------------------------------------------------------------+
//| GODMODE_VWAP.mq5 — Session VWAP + 1σ/2σ bands                    |
//+------------------------------------------------------------------+
#property copyright "GODMODE_OFEA — Enhanced"
#property version   "2.00"
#property indicator_chart_window
#property indicator_buffers 5
#property indicator_plots   5
#property indicator_label1  "VWAP"
#property indicator_label2  "+1σ"
#property indicator_label3  "-1σ"
#property indicator_label4  "+2σ"
#property indicator_label5  "-2σ"
#property indicator_color1  clrYellow
#property indicator_color2  clrAqua
#property indicator_color3  clrAqua
#property indicator_color4  clrMediumPurple
#property indicator_color5  clrMediumPurple
#property indicator_width1  2
#property indicator_style2  STYLE_DOT
#property indicator_style3  STYLE_DOT
#property indicator_style4  STYLE_DASHDOT
#property indicator_style5  STYLE_DASHDOT

#include "../Include/OF_VWAP.mqh"

input double K_Inner = 1.0;
input double K_Outer = 2.0;

double bV[], bU1[], bL1[], bU2[], bL2[];
COF_VWAP g_vwap;

int OnInit()
{
   SetIndexBuffer(0, bV);  PlotIndexSetInteger(0, PLOT_DRAW_TYPE, DRAW_LINE);
   SetIndexBuffer(1, bU1); PlotIndexSetInteger(1, PLOT_DRAW_TYPE, DRAW_LINE);
   SetIndexBuffer(2, bL1); PlotIndexSetInteger(2, PLOT_DRAW_TYPE, DRAW_LINE);
   SetIndexBuffer(3, bU2); PlotIndexSetInteger(3, PLOT_DRAW_TYPE, DRAW_LINE);
   SetIndexBuffer(4, bL2); PlotIndexSetInteger(4, PLOT_DRAW_TYPE, DRAW_LINE);
   IndicatorSetString(INDICATOR_SHORTNAME, "GODMODE VWAP");
   return INIT_SUCCEEDED;
}

int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[], const double &high[],
                const double &low[], const double &close[],
                const long &tick_volume[], const long &volume[], const int &spread[])
{
   int start = prev_calculated > 0 ? prev_calculated - 1 : 0;
   if (start == 0) g_vwap.Reset(time[0]);

   for (int i = start; i < rates_total; i++)
   {
      double typ = (high[i] + low[i] + close[i]) / 3.0;
      g_vwap.Update(typ, (double)tick_volume[i], time[i]);
      bV[i]  = g_vwap.VWAP();
      bU1[i] = g_vwap.Upper(K_Inner);
      bL1[i] = g_vwap.Lower(K_Inner);
      bU2[i] = g_vwap.Upper(K_Outer);
      bL2[i] = g_vwap.Lower(K_Outer);
   }
   return rates_total;
}
