// HTFAlignment.cs
// H4 EMA(20) + D1 EMA(50) bias (brief §11.7)
// Mirrors OF_HTFAlignment.mqh

using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace GodmodeOfea
{
    public sealed class HtfAlignment
    {
        private readonly Bars _h4;
        private readonly Bars _d1;
        private readonly ExponentialMovingAverage _emaH4;
        private readonly ExponentialMovingAverage _emaD1;

        public HtfAlignment(Robot robot, Symbol s)
        {
            _h4 = robot.MarketData.GetBars(TimeFrame.Hour4, s.Name);
            _d1 = robot.MarketData.GetBars(TimeFrame.Daily, s.Name);
            _emaH4 = robot.Indicators.ExponentialMovingAverage(_h4.ClosePrices, 20);
            _emaD1 = robot.Indicators.ExponentialMovingAverage(_d1.ClosePrices, 50);
        }

        public HtfBias H4Bias()
        {
            double ema = _emaH4.Result.Last(0);
            double cls = _h4.ClosePrices.Last(0);
            if (cls > ema * 1.0001) return HtfBias.Bull;
            if (cls < ema * 0.9999) return HtfBias.Bear;
            return HtfBias.Neutral;
        }

        public HtfBias D1Bias()
        {
            double ema = _emaD1.Result.Last(0);
            double cls = _d1.ClosePrices.Last(0);
            if (cls > ema * 1.0001) return HtfBias.Bull;
            if (cls < ema * 0.9999) return HtfBias.Bear;
            return HtfBias.Neutral;
        }

        public bool IsAligned(TradeDir dir)
        {
            var h4 = H4Bias();
            var d1 = D1Bias();
            if (h4 != d1) return false;
            if (dir == TradeDir.Long)  return h4 == HtfBias.Bull;
            if (dir == TradeDir.Short) return h4 == HtfBias.Bear;
            return false;
        }

        public HtfBias Combined()
        {
            var h4 = H4Bias();
            var d1 = D1Bias();
            return h4 == d1 ? h4 : HtfBias.Neutral;
        }
    }
}
