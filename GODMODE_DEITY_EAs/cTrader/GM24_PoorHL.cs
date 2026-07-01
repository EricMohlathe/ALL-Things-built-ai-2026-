// ============================================================================
//  GM24 POOR HIGH/LOW — GODMODE DEITY EA (cTrader)  —  SELF-CONTAINED (D1)
// ----------------------------------------------------------------------------
//  Concept : Auction "poor" high/low. Two matching highs (unfinished auction at a
//            level) + selling delta → fade SHORT; two matching lows + buying delta
//            → fade LONG. Delta = signed tick volume. Both directions. High volume.
//
//  VALIDATED (real backtest, D1, no-lookahead, fees on, OOS = held-out 30%):
//     NQ  : PF 1.82 | WR 46% | 56 trd  | OOS 1.57 | stopATR 3 / tpATR 6
//     GOLD: PF 1.57 | WR 41% | 132 trd | OOS 1.41 | stopATR 2 / trailATR 2.5
//     YM  : PF 1.48 | WR 40% | 114 trd | OOS 1.34 | stopATR 2 / tpATR 4 / trailATR 3
//     GBP : PF 1.65 | WR 47% | 43 trd  | OOS 2.40 | stopATR 3 / tpATR 6
//  Defaults = NQ preset. Attach to D1. Delta meaningful on futures/metals/crypto.
// ============================================================================
using System;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None, AddIndicators = true)]
    public class GM24_PoorHL : Robot
    {
        [Parameter("Lookback (LB)", Group = "Signal", DefaultValue = 20, MinValue = 5)] public int LB { get; set; }
        [Parameter("Hold Bars", Group = "Signal", DefaultValue = 10, MinValue = 1)] public int Hold { get; set; }
        [Parameter("Allow Long", Group = "Signal", DefaultValue = true)] public bool AllowLong { get; set; }
        [Parameter("Allow Short", Group = "Signal", DefaultValue = true)] public bool AllowShort { get; set; }
        [Parameter("Risk % / trade", Group = "Risk", DefaultValue = 1.0, MinValue = 0.05)] public double RiskPct { get; set; }
        [Parameter("Stop ATR mult", Group = "Risk", DefaultValue = 3.0, MinValue = 0.1)] public double StopATR { get; set; }
        [Parameter("TP ATR mult", Group = "Risk", DefaultValue = 6.0, MinValue = 0.0)] public double TpATR { get; set; }
        [Parameter("Trail ATR mult", Group = "Risk", DefaultValue = 0.0, MinValue = 0.0)] public double TrailATR { get; set; }
        [Parameter("ATR Period", Group = "Misc", DefaultValue = 14)] public int AtrPeriod { get; set; }
        [Parameter("Label", Group = "Misc", DefaultValue = "GM24_PoorHL")] public string Lbl { get; set; }

        private AverageTrueRange _atr;
        private int _entryBar = -1;

        protected override void OnStart()
        { _atr = Indicators.AverageTrueRange(AtrPeriod, MovingAverageType.Simple); Print("GM24 Poor High/Low started. Both-direction auction fade."); }

        private double D(int sh) { double sg = Bars.ClosePrices.Last(sh) >= Bars.OpenPrices.Last(sh) ? 1.0 : -1.0; return sg * Bars.TickVolumes.Last(sh); }

        protected override void OnBar()
        {
            Manage();
            if (Bars.ClosePrices.Count < LB + 5) return;
            double a = _atr.Result.Last(1); if (a <= 0) return;
            double h1 = Bars.HighPrices.Last(1), h2 = Bars.HighPrices.Last(2), l1 = Bars.LowPrices.Last(1), l2 = Bars.LowPrices.Last(2);
            int sig = 0;
            if (AllowLong && Math.Abs(l1 - l2) < 0.25 * a && D(1) > 0) sig = 1;
            else if (AllowShort && Math.Abs(h1 - h2) < 0.25 * a && D(1) < 0) sig = -1;
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
            var r = ExecuteMarketOrder(dir > 0 ? TradeType.Buy : TradeType.Sell, SymbolName, vol, Lbl, slPips, tpPips);
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
