using System;
using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;
using GodmodeOfea.Enhanced;

namespace cAlgo.Robots
{
    [Robot(AccessRights = AccessRights.None, AddIndicators = true)]
    public class GODMODE_OFEA_Enhanced : Robot
    {
        [Parameter("Operating Mode", DefaultValue = "MANUAL")]
        public string OpMode { get; set; }

        [Parameter("Risk % per trade (cap 2.0)", DefaultValue = 0.5, MinValue = 0.0, MaxValue = 2.0, Step = 0.1)]
        public double RiskPctMax { get; set; }

        [Parameter("Kelly fraction κ", DefaultValue = 0.25, MinValue = 0.1, MaxValue = 1.0)]
        public double KellyKappa { get; set; }

        [Parameter("Spread max Z", DefaultValue = 2.0)]
        public double SpreadMaxZ { get; set; }

        [Parameter("Bar-delta lookback", DefaultValue = 20)]
        public int BarDeltaLookback { get; set; }

        private VWAP            _vwap;
        private BidAskMonitor   _ba;
        private DeltaEnhanced   _dE;
        private RegimeHMM       _reg;
        private PriceAction     _pa;
        private SweepDetector   _sw;
        private PoolResilience  _pool;
        private ProbabilityScore _prob;
        private DateTime _lastBar;

        protected override void OnStart()
        {
            _vwap = new VWAP();
            _ba   = new BidAskMonitor();
            _dE   = new DeltaEnhanced(BarDeltaLookback);
            _reg  = new RegimeHMM();
            _pa   = new PriceAction();
            _sw   = new SweepDetector();
            _pool = new PoolResilience();
            _prob = new ProbabilityScore();
            Print($"GODMODE_OFEA Enhanced initialised — mode={OpMode} κ={KellyKappa:F2}");
        }

        protected override void OnTick()
        {
            _ba.Update(Symbol);
            if (Bars.OpenTimes.LastValue == _lastBar) return;
            _lastBar = Bars.OpenTimes.LastValue;
            OnBarClose();
        }

        private void OnBarClose()
        {
            int last = Bars.ClosePrices.Count - 2;       // last closed bar
            if (last < 30) return;

            double high  = Bars.HighPrices[last];
            double low   = Bars.LowPrices[last];
            double close = Bars.ClosePrices[last];
            double tv    = Bars.TickVolumes[last];

            double rng = high - low;
            double bw  = rng > 0 ? (close - low) / rng : 0.5;
            double bd  = tv * (bw - (1.0 - bw));
            _dE.OnBar(bd, close);

            double typ = (high + low + close) / 3.0;
            _vwap.Update(typ, tv, Bars.OpenTimes[last]);

            _reg.Update(_dE.CvdSlope, 0, 0, _dE.ZScore);

            int N = 50;
            var H = new double[N]; var L = new double[N]; var C = new double[N];
            for (int i = 0; i < N; i++)
            {
                int idx = last - i;
                if (idx < 0) break;
                H[i] = Bars.HighPrices[idx];
                L[i] = Bars.LowPrices[idx];
                C[i] = Bars.ClosePrices[idx];
            }
            double atr = Indicators.AverageTrueRange(14, MovingAverageType.Simple).Result.LastValue;
            _pa.Update(H, L, C, 20, 0.10, atr);

            double pct = ComputeCompositeProbability();
            Print($"[ENHANCED] regime={_reg.Current} prob={pct:F0}% grade={_prob.Grade()}");

            if (OpMode == "AUTO" && pct >= 85.0) FireTradeIfReady();
        }

        private double ComputeCompositeProbability()
        {
            double g1 = (_pa.EqualHighsCluster || _pa.EqualLowsCluster) ? 1 : 0;
            double g2 = 1.0;
            double g3 = 1.0;
            double g4 = Math.Abs(_dE.CvdSlope) > 0 ? 1 : 0;
            double g5 = 1.0;
            double g6 = _reg.JustTransitioned ? 1 : 0.5;
            double g7 = _sw.Last.PreconditionsPassed / 6.0;
            double g8 = Math.Abs(_vwap.ZScore(Symbol.Bid)) < 2.0 ? 1 : 0;
            double g9 = (_pa.FvgUp || _pa.FvgDown) ? 1 : 0;
            double g10 = 0.5;
            double g11 = _ba.SpreadAcceptable(SpreadMaxZ) ? 1 : 0;
            double g12 = 1.0;
            return _prob.Compute(g1, g2, g3, g4, g5, g6, g7, g8, g9, g10, g11, g12);
        }

        private void FireTradeIfReady()
        {
            double p = _sw.EmpiricalWinRate();
            double b = _sw.ExpectedR() > 0 ? _sw.ExpectedR() + 1.0 : 2.0;
            double riskPct = Math.Min(RiskPctMax, KellySizer.RiskPctFromKelly(p, b, KellyKappa));
            Print($"[ENHANCED] would-fire: kellyRiskPct={riskPct:F3}");
        }
    }
}
