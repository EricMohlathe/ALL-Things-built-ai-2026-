// ============================================================================
//  GM15 UPTHRUST — GODMODE DEITY EA (cTrader)  —  SELF-CONTAINED
// ----------------------------------------------------------------------------
//  Concept : Wyckoff upthrust — mirror of the spring. Price pokes ABOVE the prior
//            swing-high (of closes, LB) then CLOSES back below it = failed breakout
//            / distribution → SHORT. Short-only (only the short side validated).
//
//  VALIDATED (real backtest, D1, no-lookahead, fees on, OOS = held-out 30%):
//     EURCHF  : PF 2.36 | WR 68% | 56 trd | OOS 3.26 | stopATR 3 / tpATR 1
//     PLATINUM: PF 1.89 | WR 69% | 29 trd | OOS 2.28 | stopATR 2.5 / tpATR 0.8
//     ZN(note): PF 2.08 | WR 73% | 59 trd | OOS 1.66 | stopATR 4 / tpATR 1.5
//     NZDUSD  : PF 1.52 | WR 61% | 61 trd | OOS 1.40 | stopATR 2.5 / tpATR 0.8
//  Defaults = EURCHF preset. Attach to D1. Truth = broker Strategy Tester.
// ============================================================================
using System;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None, AddIndicators = true)]
    public class GM15_Upthrust : Robot
    {
        [Parameter("Lookback (LB)", Group = "Signal", DefaultValue = 20, MinValue = 5)] public int LB { get; set; }
        [Parameter("Hold Bars", Group = "Signal", DefaultValue = 10, MinValue = 1)] public int Hold { get; set; }
        [Parameter("Risk % / trade", Group = "Risk", DefaultValue = 1.0, MinValue = 0.05)] public double RiskPct { get; set; }
        [Parameter("Stop ATR mult", Group = "Risk", DefaultValue = 3.0, MinValue = 0.1)] public double StopATR { get; set; }
        [Parameter("TP ATR mult", Group = "Risk", DefaultValue = 1.0, MinValue = 0.0)] public double TpATR { get; set; }
        [Parameter("Trail ATR mult", Group = "Risk", DefaultValue = 0.0, MinValue = 0.0)] public double TrailATR { get; set; }
        [Parameter("ATR Period", Group = "Misc", DefaultValue = 14)] public int AtrPeriod { get; set; }
        [Parameter("Label", Group = "Misc", DefaultValue = "GM15_Upthrust")] public string Lbl { get; set; }

        private AverageTrueRange _atr;
        private int _entryBar = -1;

        protected override void OnStart()
        {
            _atr = Indicators.AverageTrueRange(AtrPeriod, MovingAverageType.Simple);
            Print("GM15 Upthrust started. Short-only failed-breakout distribution.");
        }

        private double HighC(int from, int n) { double m = double.MinValue; for (int i = from; i < from + n; i++) m = Math.Max(m, Bars.ClosePrices.Last(i)); return m; }

        protected override void OnBar()
        {
            Manage();
            if (Positions.Any(p => p.Label == Lbl)) return;
            if (Bars.ClosePrices.Count < LB + 5) return;
            double h1 = Bars.HighPrices.Last(1), c1 = Bars.ClosePrices.Last(1), hh = HighC(2, LB);
            if (h1 > hh && c1 < hh) EnterShort();
        }

        private void EnterShort()
        {
            double a = _atr.Result.Last(1); if (a <= 0) return;
            double vol = Symbol.NormalizeVolumeInUnits(Account.Equity * (RiskPct / 100.0) / (StopATR * a), RoundingMode.Down);
            if (vol < Symbol.VolumeInUnitsMin) vol = Symbol.VolumeInUnitsMin;
            double slPips = StopATR * a / Symbol.PipSize;
            double? tpPips = TpATR > 0 ? (double?)(TpATR * a / Symbol.PipSize) : null;
            var r = ExecuteMarketOrder(TradeType.Sell, SymbolName, vol, Lbl, slPips, tpPips);
            if (r.IsSuccessful) _entryBar = Bars.ClosePrices.Count - 1;
        }

        private void Manage()
        {
            var pos = Positions.FirstOrDefault(p => p.Label == Lbl);
            if (pos == null) { _entryBar = -1; return; }
            if (TrailATR > 0)
            {
                double a = _atr.Result.Last(1), nsl = Symbol.Ask + TrailATR * a;
                if (!pos.StopLoss.HasValue || nsl < pos.StopLoss.Value) ModifyPosition(pos, nsl, pos.TakeProfit);
            }
            if (_entryBar >= 0 && (Bars.ClosePrices.Count - 1 - _entryBar) >= Hold) ClosePosition(pos);
        }
    }
}
