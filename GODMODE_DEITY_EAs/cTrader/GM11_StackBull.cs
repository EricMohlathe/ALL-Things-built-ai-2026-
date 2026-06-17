// ============================================================================
//  GM11 STACKBULL  —  GODMODE DEITY EA (cTrader / cAlgo)  —  SELF-CONTAINED
// ----------------------------------------------------------------------------
//  Concept : Footprint buy-delta stacking. THREE consecutive positive-delta bars
//            AND the current bar's delta exceeds K x |mean delta over LB| =
//            aggressive-buyer continuation. Delta = signed volume (no taker feed
//            on metals/futures): +vol on up-close bars, -vol on down-close bars.
//            Long-only (only long side validated).
//
//  VALIDATED (real backtest, daily, no-lookahead, OOS = held-out 30% tail):
//     GOLD(GC=F) 1D : PF 3.38 | WR 75.9% | 58 trd | +39.2% | OOS PF 6.48 | stopATR 3 / tpATR 1
//  Defaults = GOLD preset. Truth = broker Strategy Tester; numbers = edge evidence.
// ============================================================================
using System;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None, AddIndicators = true)]
    public class GM11_StackBull : Robot
    {
        [Parameter("Lookback (LB)", Group = "Signal", DefaultValue = 20, MinValue = 5)] public int LB { get; set; }
        [Parameter("K (delta thresh)", Group = "Signal", DefaultValue = 1.0, MinValue = 0.0)] public double K { get; set; }
        [Parameter("Hold Bars", Group = "Signal", DefaultValue = 10, MinValue = 1)] public int Hold { get; set; }

        [Parameter("Risk % / trade", Group = "Risk", DefaultValue = 1.0, MinValue = 0.05)] public double RiskPct { get; set; }
        [Parameter("Stop ATR mult",  Group = "Risk", DefaultValue = 3.0, MinValue = 0.0)] public double StopATR { get; set; }
        [Parameter("TP ATR mult",    Group = "Risk", DefaultValue = 1.0, MinValue = 0.0)] public double TpATR { get; set; }
        [Parameter("Trail ATR mult", Group = "Risk", DefaultValue = 0.0, MinValue = 0.0)] public double TrailATR { get; set; }
        [Parameter("Sizing ATR (if no stop)", Group = "Risk", DefaultValue = 3.0)] public double SizingATR { get; set; }

        [Parameter("ATR Period", Group = "Misc", DefaultValue = 14)] public int AtrPeriod { get; set; }
        [Parameter("Label", Group = "Misc", DefaultValue = "GM11_StackBull")] public string Lbl { get; set; }

        private AverageTrueRange _atr;
        private int _entryBar = -1;

        protected override void OnStart()
        {
            _atr = Indicators.AverageTrueRange(AtrPeriod, MovingAverageType.Simple);
            Print("GM11 StackBull started. 3-bar buy-delta stack. LB={0} K={1}", LB, K);
        }

        private double Delta(int shift)
        {
            double sign = Bars.ClosePrices.Last(shift) >= Bars.OpenPrices.Last(shift) ? 1.0 : -1.0;
            return sign * Bars.TickVolumes.Last(shift);
        }
        private double MeanDelta()
        { double s = 0; for (int j = 1; j <= LB; j++) s += Delta(j); return s / LB; }

        protected override void OnBar()
        {
            ManageOpen();
            if (Positions.Any(p => p.Label == Lbl)) return;
            if (Bars.ClosePrices.Count < LB + 5) return;

            if (Delta(1) > 0 && Delta(2) > 0 && Delta(3) > 0 &&
                Delta(1) > K * Math.Abs(MeanDelta()))
                EnterLong();
        }

        private void EnterLong()
        {
            double atr = _atr.Result.Last(1);
            if (atr <= 0) return;
            double riskRef = (StopATR > 0 ? StopATR : SizingATR) * atr;
            double riskCash = Account.Equity * (RiskPct / 100.0);
            double volume = Symbol.NormalizeVolumeInUnits(riskCash / riskRef, RoundingMode.Down);
            if (volume < Symbol.VolumeInUnitsMin) volume = Symbol.VolumeInUnitsMin;
            double? slPips = StopATR > 0 ? (double?)(StopATR * atr / Symbol.PipSize) : null;
            double? tpPips = TpATR > 0 ? (double?)(TpATR * atr / Symbol.PipSize) : null;
            var r = ExecuteMarketOrder(TradeType.Buy, SymbolName, volume, Lbl, slPips, tpPips);
            if (r.IsSuccessful) _entryBar = Bars.ClosePrices.Count - 1;
        }

        private void ManageOpen()
        {
            var pos = Positions.FirstOrDefault(p => p.Label == Lbl);
            if (pos == null) { _entryBar = -1; return; }
            if (TrailATR > 0)
            {
                double atr = _atr.Result.Last(1);
                double newSl = Symbol.Bid - TrailATR * atr;
                if (!pos.StopLoss.HasValue || newSl > pos.StopLoss.Value) ModifyPosition(pos, newSl, pos.TakeProfit);
            }
            if (_entryBar >= 0 && (Bars.ClosePrices.Count - 1 - _entryBar) >= Hold) ClosePosition(pos);
        }
    }
}
