using System;
using cAlgo.API;

namespace GodmodeOfea.Enhanced
{
    public class BidAskMonitor
    {
        private readonly double[] _buf;
        private ulong _idx;            // ulong wraps cleanly; year-scale safe
        public double Bid, Ask, Spread, SpreadPts;
        public double MeanSpreadPts, SdSpreadPts, ZSpread;

        public BidAskMonitor(int window = 120) { _buf = new double[window]; }

        public void Update(Symbol symbol)
        {
            // Snapshot bid/ask once — cAlgo updates are volatile across the method.
            var bid = symbol.Bid;
            var ask = symbol.Ask;
            Bid = bid;
            Ask = ask;
            Spread = ask - bid;
            SpreadPts = Spread / symbol.TickSize;
            ulong L = (ulong)_buf.Length;
            _buf[(int)(_idx % L)] = SpreadPts;
            _idx++;
            int n = (int)Math.Min(_idx, L);
            double sum = 0, sum2 = 0;
            for (int i = 0; i < n; i++) { sum += _buf[i]; sum2 += _buf[i] * _buf[i]; }
            MeanSpreadPts = n > 0 ? sum / n : 0;
            var v = n > 0 ? (sum2 / n) - (MeanSpreadPts * MeanSpreadPts) : 0;
            if (v < 0 || double.IsNaN(v) || double.IsInfinity(v)) v = 0;
            SdSpreadPts = v > 0 ? Math.Sqrt(v) : 0;
            ZSpread = SdSpreadPts > 0 ? (SpreadPts - MeanSpreadPts) / SdSpreadPts : 0;
        }
        public bool SpreadAcceptable(double maxZ = 2.0) => ZSpread <= maxZ;
        public bool CostAcceptable(double atr, double maxFrac = 0.20) =>
            atr > 0 ? (Spread / atr) < maxFrac : true;
    }
}
