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

        // MT5 build types SpreadMaxZ as int; mirroring keeps the optimiser ranges
        // aligned across builds. The check itself only ever compares to ZSpread
        // (double) so the narrower type costs nothing at runtime.
        [Parameter("Use Enhanced Gates", DefaultValue = true)]
        public bool UseEnhancedGates { get; set; }

        [Parameter("Spread max Z", DefaultValue = 2)]
        public int SpreadMaxZ { get; set; }

        [Parameter("Bar-delta lookback", DefaultValue = 20)]
        public int BarDeltaLookback { get; set; }

        [Parameter("VWAP Bands K1", DefaultValue = 1)]
        public int VWAPBands_K1 { get; set; }
        [Parameter("VWAP Bands K2", DefaultValue = 2)]
        public int VWAPBands_K2 { get; set; }

        private VWAP            _vwap;
        private BidAskMonitor   _ba;
        private DeltaEnhanced   _dE;
        private RegimeHMM       _reg;
        private PriceAction     _pa;
        private SweepDetector   _sw;
        private PoolResilience  _pool;
        private ProbabilityScore _prob;
        private DateTime _lastBar;
        private bool _seeded;
        private AverageTrueRange _atr14;

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
            _atr14 = Indicators.AverageTrueRange(14, MovingAverageType.Simple);
            Print($"GODMODE_OFEA Enhanced initialised — mode={OpMode} κ={KellyKappa:F2}");
        }

        protected override void OnTick()
        {
            _ba.Update(Symbol);
            // First-tick seed: skip the first comparison so we don't fire
            // OnBarClose on a half-formed bar before any rollover has happened.
            if (!_seeded) { _lastBar = Bars.OpenTimes.LastValue; _seeded = true; return; }
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
            // Expose the configured band envelopes so downstream consumers
            // (manual operators, chart overlay) see the right K-multiples.
            double bandUpper1 = _vwap.Upper(VWAPBands_K1);
            double bandLower1 = _vwap.Lower(VWAPBands_K1);
            double bandUpper2 = _vwap.Upper(VWAPBands_K2);
            double bandLower2 = _vwap.Lower(VWAPBands_K2);
            // Silence "unused variable" warnings without emitting a log line per
            // bar — the values are intended for the next chart-overlay iteration.
            _ = bandUpper1; _ = bandLower1; _ = bandUpper2; _ = bandLower2;

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
            double atr = _atr14.Result.LastValue;
            _pa.Update(H, L, C, 20, 0.10, atr);

            // UseEnhancedGates lets the operator switch the 12-factor probability
            // bar off without removing the overlay, matching MT5 build behaviour.
            double pct = UseEnhancedGates ? ComputeCompositeProbability() : 0.0;
            Print($"[ENHANCED] regime={_reg.Current} prob={pct:F0}% grade={_prob.Grade()}");

            if (OpMode == "AUTO" && UseEnhancedGates && pct >= 85.0) FireTradeIfReady();
        }

        private double ComputeCompositeProbability()
        {
            // Snapshot the live bid once — cAlgo's Symbol properties are volatile
            // and can change between reads, biasing VWAP z-score evaluation.
            var bidSnap = Symbol.Bid;
            double g1 = (_pa.EqualHighsCluster || _pa.EqualLowsCluster) ? 1 : 0;
            double g2 = 1.0;
            double g3 = 1.0;
            double g4 = Math.Abs(_dE.CvdSlope) > 0 ? 1 : 0;
            double g5 = 1.0;
            double g6 = _reg.JustTransitioned ? 1 : 0.5;
            double g7 = _sw.Last.PreconditionsPassed / 6.0;
            double g8 = Math.Abs(_vwap.ZScore(bidSnap)) < 2.0 ? 1 : 0;
            double g9 = (_pa.FvgUp || _pa.FvgDown) ? 1 : 0;
            double g10 = 0.5;
            double g11 = _ba.SpreadAcceptable(SpreadMaxZ) ? 1 : 0;
            double g12 = 1.0;
            return _prob.Compute(g1, g2, g3, g4, g5, g6, g7, g8, g9, g10, g11, g12);
        }

        private void FireTradeIfReady()
        {
            double p = _sw.EmpiricalWinRate();
            // Kelly's b = AvgWin/AvgLoss = R-multiple of the setup. ExpectedR()
            // returns that directly (1.18 at 6/6 preconditions); do NOT add 1.0
            // — that previously inflated b by ~85% and oversized positions.
            double b = _sw.ExpectedR() > 0 ? _sw.ExpectedR() : 2.0;
            double riskPct = Math.Min(RiskPctMax, KellySizer.RiskPctFromKelly(p, b, KellyKappa));
            Print($"[ENHANCED] would-fire: kellyRiskPct={riskPct:F3}");
        }
    }
}
