// FootprintAnalyzer.cs
// Absorption / Stacked imbalance / Unfinished auction (brief §5 GATE 6)
// Mirrors OF_FootprintAnalyzer.mqh

using System;
using cAlgo.API;

namespace GodmodeOfea
{
    public sealed class FootprintAnalyzer
    {
        private readonly Bars _bars;
        private readonly double _volZThr;
        private readonly int _minStackedRows;

        public FootprintAnalyzer(Bars bars, double volZ, double deltaZ, int stackedRows, double imbalanceRatio)
        {
            _bars = bars;
            _volZThr = volZ;
            _minStackedRows = stackedRows;
        }

        public bool BullishAbsorption(DeltaEngine de)
        {
            double volZ = de.VolumeZ();
            double bd   = de.BarDelta;
            double o = _bars.OpenPrices.Last(1);
            double c = _bars.ClosePrices.Last(1);
            return bd < 0 && volZ >= _volZThr && c >= o;
        }

        public bool BearishAbsorption(DeltaEngine de)
        {
            double volZ = de.VolumeZ();
            double bd   = de.BarDelta;
            double o = _bars.OpenPrices.Last(1);
            double c = _bars.ClosePrices.Last(1);
            return bd > 0 && volZ >= _volZThr && c <= o;
        }

        public bool StackedBullImbalance(DeltaEngine de)
        {
            for (int i = 0; i < _minStackedRows; i++) if (de.Delta(i) <= 0) return false;
            return true;
        }

        public bool StackedBearImbalance(DeltaEngine de)
        {
            for (int i = 0; i < _minStackedRows; i++) if (de.Delta(i) >= 0) return false;
            return true;
        }

        public bool UnfinishedAuction(IndicatorDataSeries atr14)
        {
            double prevH = _bars.HighPrices.Last(2);
            double prevL = _bars.LowPrices.Last(2);
            double curH  = _bars.HighPrices.Last(1);
            double curL  = _bars.LowPrices.Last(1);
            double curC  = _bars.ClosePrices.Last(1);
            double prevC = _bars.ClosePrices.Last(2);
            double atr   = atr14.Last(1);
            if (atr <= 0) return false;
            bool poorHigh = curH > prevH && (curC - prevC) < 0.25 * atr;
            bool poorLow  = curL < prevL && (prevC - curC) < 0.25 * atr;
            return poorHigh || poorLow;
        }
    }

    public static class AbsorptionStars
    {
        public static int Compute(Bars bars, DeltaEngine de, TradeDir dir)
        {
            double volZ = de.VolumeZ();
            double dz   = de.DeltaZ();
            if (volZ < 1.0) return 0;
            int stars = 1;
            if (volZ >= 2.0) stars++;
            if (volZ >= 3.0) stars++;
            if (Math.Abs(dz) >= 2.0) stars++;

            double o = bars.OpenPrices.Last(1);
            double c = bars.ClosePrices.Last(1);
            double h = bars.HighPrices.Last(1);
            double l = bars.LowPrices.Last(1);
            double range = Math.Max(h - l, 1e-9);
            double wickPct = 0;
            if (dir == TradeDir.Long)  wickPct = (Math.Min(o, c) - l) / range;
            if (dir == TradeDir.Short) wickPct = (h - Math.Max(o, c)) / range;
            if (wickPct >= 0.4) stars++;
            return Math.Min(stars, 5);
        }
    }
}
