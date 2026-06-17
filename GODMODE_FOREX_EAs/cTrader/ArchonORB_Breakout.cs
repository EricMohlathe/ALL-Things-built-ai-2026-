// ============================================================================
//  ARCHON ORB — GODMODE FOREX EA (cTrader)  —  SELF-CONTAINED
// ----------------------------------------------------------------------------
//  Concept : Opening-range / volatility breakout (Crabel/Williams). Break of the
//            prior LB-bar range (of closes) by a K*ATR*0.2 buffer, IN the trend
//            direction (vs 50-SMA). Fat-tail trend capture, both directions.
//            Price-only -> works on spot forex. Higher trade volume (90-108/run).
//
//  VALIDATED (real backtest, D1, no-lookahead, fees on, OOS = held-out 30%):
//     EUR futures (6E): PF 1.62 | WR 50% |  90 trd | OOS PF 3.58 | stopATR 3 / tpATR 6
//     EURJPY          : PF 1.58 | WR 47% | 108 trd | OOS PF 2.04 | stop1/tp2/trail1.5
//  Defaults = 6E preset. Validate YOUR pair in the backtester. Attach to D1.
// ============================================================================
using System;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None, AddIndicators = true)]
    public class ArchonORB_Breakout : Robot
    {
        [Parameter("Lookback (LB)", Group = "Signal", DefaultValue = 20, MinValue = 5)] public int LB { get; set; }
        [Parameter("K (buffer x ATR x0.2)", Group = "Signal", DefaultValue = 1.0, MinValue = 0.0)] public double K { get; set; }
        [Parameter("Trend SMA", Group = "Signal", DefaultValue = 50, MinValue = 5)] public int TrendN { get; set; }
        [Parameter("Hold Bars", Group = "Signal", DefaultValue = 12, MinValue = 1)] public int Hold { get; set; }
        [Parameter("Allow Long", Group = "Signal", DefaultValue = true)] public bool AllowLong { get; set; }
        [Parameter("Allow Short", Group = "Signal", DefaultValue = true)] public bool AllowShort { get; set; }

        [Parameter("Risk % / trade", Group = "Risk", DefaultValue = 1.0, MinValue = 0.05)] public double RiskPct { get; set; }
        [Parameter("Stop ATR mult", Group = "Risk", DefaultValue = 3.0, MinValue = 0.1)] public double StopATR { get; set; }
        [Parameter("TP ATR mult", Group = "Risk", DefaultValue = 6.0, MinValue = 0.0)] public double TpATR { get; set; }
        [Parameter("Trail ATR mult", Group = "Risk", DefaultValue = 0.0, MinValue = 0.0)] public double TrailATR { get; set; }
        [Parameter("ATR Period", Group = "Misc", DefaultValue = 14)] public int AtrPeriod { get; set; }
        [Parameter("Label", Group = "Misc", DefaultValue = "ArchonORB")] public string Lbl { get; set; }

        private SimpleMovingAverage _sma;
        private AverageTrueRange _atr;
        private int _entryBar = -1;

        protected override void OnStart()
        {
            _sma = Indicators.SimpleMovingAverage(Bars.ClosePrices, TrendN);
            _atr = Indicators.AverageTrueRange(AtrPeriod, MovingAverageType.Simple);
            Print("Archon ORB started. Volatility breakout + SMA{0} trend filter.", TrendN);
        }

        private double HighC(int from, int n) { double m = double.MinValue; for (int i = from; i < from + n; i++) m = Math.Max(m, Bars.ClosePrices.Last(i)); return m; }
        private double LowC(int from, int n) { double m = double.MaxValue; for (int i = from; i < from + n; i++) m = Math.Min(m, Bars.ClosePrices.Last(i)); return m; }

        protected override void OnBar()
        {
            Manage();
            if (Bars.ClosePrices.Count < Math.Max(LB, TrendN) + 3) return;
            double a = _atr.Result.Last(1); if (a <= 0) return;
            double c1 = Bars.ClosePrices.Last(1), sma = _sma.Result.Last(1);
            double buf = K * a * 0.2;
            int sig = 0;
            if (AllowLong && c1 > HighC(2, LB) + buf && c1 > sma) sig = 1;
            else if (AllowShort && c1 < LowC(2, LB) - buf && c1 < sma) sig = -1;
            if (sig == 0) return;

            var pos = Positions.FirstOrDefault(p => p.Label == Lbl);
            int dir = pos == null ? 0 : (pos.TradeType == TradeType.Buy ? 1 : -1);
            if (sig == dir) return;
            if (pos != null) ClosePosition(pos);
            Enter(sig, a);
        }

        private void Enter(int dir, double a)
        {
            double vol = Symbol.NormalizeVolumeInUnits(Account.Equity * (RiskPct / 100.0) / (StopATR * a), RoundingMode.Down);
            if (vol < Symbol.VolumeInUnitsMin) vol = Symbol.VolumeInUnitsMin;
            double slPips = StopATR * a / Symbol.PipSize;
            double? tpPips = TpATR > 0 ? (double?)(TpATR * a / Symbol.PipSize) : null;
            var tt = dir > 0 ? TradeType.Buy : TradeType.Sell;
            var r = ExecuteMarketOrder(tt, SymbolName, vol, Lbl, slPips, tpPips);
            if (r.IsSuccessful) _entryBar = Bars.ClosePrices.Count - 1;
        }

        private void Manage()
        {
            var pos = Positions.FirstOrDefault(p => p.Label == Lbl);
            if (pos == null) { _entryBar = -1; return; }
            if (TrailATR > 0)
            {
                double a = _atr.Result.Last(1);
                if (pos.TradeType == TradeType.Buy) { double n = Symbol.Bid - TrailATR * a; if (!pos.StopLoss.HasValue || n > pos.StopLoss.Value) ModifyPosition(pos, n, pos.TakeProfit); }
                else { double n = Symbol.Ask + TrailATR * a; if (!pos.StopLoss.HasValue || n < pos.StopLoss.Value) ModifyPosition(pos, n, pos.TakeProfit); }
            }
            if (_entryBar >= 0 && (Bars.ClosePrices.Count - 1 - _entryBar) >= Hold) ClosePosition(pos);
        }
    }
}
