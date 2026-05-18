using System;
using cAlgo.API;

namespace GodmodeOfea.Enhanced
{
    public class BidAskMonitor
    {
        private readonly double[] _buf;
        private int _idx;
        public double Bid, Ask, Spread, SpreadPts;
        public double MeanSpreadPts, SdSpreadPts, ZSpread;

        public BidAskMonitor(int window = 120) { _buf = new double[window]; }

        public void Update(Symbol symbol)
        {
            Bid = symbol.Bid;
            Ask = symbol.Ask;
            Spread = Ask - Bid;
            SpreadPts = Spread / symbol.TickSize;
            _buf[_idx % _buf.Length] = SpreadPts;
            _idx++;
            int n = Math.Min(_idx, _buf.Length);
            double sum = 0, sum2 = 0;
            for (int i = 0; i < n; i++) { sum += _buf[i]; sum2 += _buf[i] * _buf[i]; }
            MeanSpreadPts = n > 0 ? sum / n : 0;
            var v = n > 0 ? (sum2 / n) - (MeanSpreadPts * MeanSpreadPts) : 0;
            SdSpreadPts = v > 0 ? Math.Sqrt(v) : 0;
            ZSpread = SdSpreadPts > 0 ? (SpreadPts - MeanSpreadPts) / SdSpreadPts : 0;
        }
        public bool SpreadAcceptable(double maxZ = 2.0) => ZSpread <= maxZ;
        public bool CostAcceptable(double atr, double maxFrac = 0.20) =>
            atr > 0 ? (Spread / atr) < maxFrac : true;
    }
}
