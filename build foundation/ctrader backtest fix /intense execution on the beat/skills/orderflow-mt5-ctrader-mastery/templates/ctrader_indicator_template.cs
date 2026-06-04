using System;
using cAlgo.API;
using cAlgo.API.Internals;

namespace cAlgo.Indicators
{
    [Indicator(IsOverlay = true, AccessRights = AccessRights.None)]
    public class OrderFlowFootprint : Indicator
    {
        [Parameter("Lookback Ticks", DefaultValue = 1000)] public int    InpLookbackTicks { get; set; }
        [Parameter("Imbalance Ratio", DefaultValue = 3.0)] public double InpImbalanceRatio { get; set; }

        [Output("POC", LineColor = "Yellow", Thickness = 2)] public IndicatorDataSeries Poc { get; set; }
        [Output("POI", LineColor = "Magenta", Thickness = 1)] public IndicatorDataSeries Poi { get; set; }

        protected override void Initialize() { }

        public override void Calculate(int index)
        {
            // Approximation when no DOM available
            Poc[index] = (Bars.HighPrices[index] + Bars.LowPrices[index] + Bars.ClosePrices[index]) / 3.0;
            Poi[index] = (Bars.HighPrices[index] + Bars.LowPrices[index]) / 2.0;
        }
    }
}
