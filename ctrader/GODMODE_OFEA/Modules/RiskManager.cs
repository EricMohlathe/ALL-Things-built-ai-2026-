// RiskManager.cs
// Sizing + DD halt + spread guard + consec losses (brief §12)
// Mirrors OF_RiskManager.mqh

using System;
using cAlgo.API;
using cAlgo.API.Internals;

namespace GodmodeOfea
{
    public sealed class RiskManager
    {
        private readonly Robot _robot;
        private readonly Symbol _symbol;
        private readonly double _riskPct;
        private readonly double _riskHalfPct;
        private readonly double _maxDDPct;
        private readonly int _maxConsecLosses;
        private readonly double _maxSpreadMult;

        private int _consecLosses;
        private double _dayStartEquity;
        private DateTime _dayStartUtc;
        private bool _dayHalted;

        private readonly double[] _spreadHist = new double[100];
        private int _spreadIdx;
        private bool _spreadFilled;
        private double _spreadMedian;

        public RiskManager(Robot robot, Symbol symbol, double riskPct, double riskHalf,
                           double maxDD, int maxConsec, double spreadMult)
        {
            _robot = robot; _symbol = symbol;
            _riskPct = Math.Min(riskPct, 2.0);   // brief §12 rule 2 hard cap
            _riskHalfPct = Math.Min(riskHalf, 2.0);  // §12 rule 2: also cap half-mode
            _maxDDPct = maxDD;
            _maxConsecLosses = maxConsec;
            _maxSpreadMult = spreadMult;
            _dayStartEquity = robot.Account.Equity;
            _dayStartUtc = DateTime.UtcNow;
        }

        public void OnDayRollover()
        {
            _dayStartEquity = _robot.Account.Equity;
            _consecLosses = 0;
            _dayHalted = false;
        }

        public void SampleSpread()
        {
            double s = _symbol.Spread;
            if (s <= 0 || double.IsNaN(s) || double.IsInfinity(s)) return;
            _spreadHist[_spreadIdx] = s;
            _spreadIdx = (_spreadIdx + 1) % 100;
            if (_spreadIdx == 0) _spreadFilled = true;
            int n = _spreadFilled ? 100 : Math.Max(_spreadIdx, 1);
            var sorted = new double[n];
            Array.Copy(_spreadHist, sorted, n);
            Array.Sort(sorted);
            // Proper median for even-n: average of the two middle samples.
            _spreadMedian = (n % 2 == 1)
                ? sorted[n / 2]
                : 0.5 * (sorted[n / 2 - 1] + sorted[n / 2]);
        }

        public GateResult CheckDailyDrawdown()
        {
            if (_dayStartEquity <= 0) return GateResult.Pass("DD ok");
            double pct = (_robot.Account.Equity - _dayStartEquity) / _dayStartEquity * 100.0;
            return pct <= -_maxDDPct
                ? GateResult.Fail($"Daily DD {pct:F2}%", pct)
                : GateResult.Pass($"Daily DD {pct:F2}%", pct);
        }

        public GateResult CheckSpread()
        {
            double cur = _symbol.Spread;
            if (_spreadMedian <= 0) return GateResult.Pass("no median yet", cur);
            return cur > _spreadMedian * _maxSpreadMult
                ? GateResult.Fail($"Spread blowout {cur:F5}", cur)
                : GateResult.Pass($"Spread ok {cur:F5}", cur);
        }

        public GateResult CheckConsecLosses() =>
            _consecLosses >= _maxConsecLosses
                ? GateResult.Fail($"Consec losses {_consecLosses}", _consecLosses)
                : GateResult.Pass($"Consec losses {_consecLosses}", _consecLosses);

        public void NotifyTradeClosed(double pnl)
        {
            if (pnl < 0) _consecLosses++; else _consecLosses = 0;
        }

        public void HaltDay() { _dayHalted = true; }
        public bool IsDayHalted => _dayHalted;
        public double DailyDDPct => _dayStartEquity <= 0 ? 0 :
            (_robot.Account.Equity - _dayStartEquity) / _dayStartEquity * 100.0;

        public double ComputeVolume(double slPriceDistance, bool halfSize)
        {
            double pct = halfSize ? _riskHalfPct : _riskPct;
            double riskAmount = _robot.Account.Equity * pct / 100.0;
            if (slPriceDistance <= 0) return 0;
            double pipDistance = slPriceDistance / OFHelpers.PipSize(_symbol);
            double pipValue = _symbol.PipValue;
            if (pipValue <= 0 || pipDistance <= 0) return 0;
            double volume = riskAmount / (pipDistance * pipValue);
            return OFHelpers.NormaliseVolume(_symbol, volume);
        }

        public GateResult CheckNewsBlackout(DateTime now, DateTime preStart, DateTime postEnd, string desc)
        {
            return now >= preStart && now <= postEnd
                ? GateResult.Fail($"News blackout: {desc}")
                : GateResult.Pass("no news");
        }
    }
}
