//+------------------------------------------------------------------+
//|        OrderFlow_Footprint_Indicator.mq5  (template)             |
//+------------------------------------------------------------------+
#property copyright "OrderFlow Mastery Skill"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 2
#property indicator_plots   2
#property indicator_type1   DRAW_LINE
#property indicator_label1  "POC"
#property indicator_type2   DRAW_LINE
#property indicator_label2  "POI"

double PocBuf[];
double PoiBuf[];

input int    InpLookbackTicks = 1000;
input double InpImbalanceRatio= 3.0;

int OnInit()
{
   SetIndexBuffer(0, PocBuf, INDICATOR_DATA);
   SetIndexBuffer(1, PoiBuf, INDICATOR_DATA);
   ArraySetAsSeries(PocBuf, true);
   ArraySetAsSeries(PoiBuf, true);
   IndicatorSetString(INDICATOR_SHORTNAME, "OF Footprint");
   return INIT_SUCCEEDED;
}

int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[],
                const double &high[],   const double &low[],
                const double &close[],  const long &tick_volume[],
                const long &volume[],   const int &spread[])
{
   // Per-bar POC = price level with max tick volume contribution
   // Approximation when no DOM: POC ≈ (open+close)/2 weighted by volume
   for(int i = MathMax(prev_calculated-1, 0); i < rates_total; i++)
   {
      PocBuf[i] = (high[i] + low[i] + close[i]) / 3.0;
      PoiBuf[i] = (high[i] + low[i]) / 2.0;
   }
   return rates_total;
}
