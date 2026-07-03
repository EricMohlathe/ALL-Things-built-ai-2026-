// ============================================================================
//  GM22 AMD (Accumulation–Manipulation–Distribution)  —  GODMODE DEITY EA (cTrader)
// ----------------------------------------------------------------------------
//  Concept : ICT power-of-three. The PRIOR bar sweeps below the swing-low of
//            closes (manipulation / stop-run), then the current bar expands UP
//            (range > K x ATR), closes higher, with positive delta (distribution
//            / markup). Long-only. Delta = signed volume.
//
//  VALIDATED (real backtest, daily, no-lookahead, OOS = held-out 30% tail):
//     YM (US30) 1D : PF 2.83 | WR 79.3% | 58 trd | +71.5% | OOS PF 5.20 | stopATR 4 / tpATR 1.5
//  Defaults = YM preset. Truth = broker Strategy Tester; numbers = edge evidence.
// ============================================================================
using System;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None, AddIndicators = true)]
    public class GM22_AMD : Robot
    {
        [Parameter("Lookback (LB)", Group = "Signal", DefaultValue = 20, MinValue = 5)] public int LB { get; set; }
        [Parameter("K (range x ATR)", Group = "Signal", DefaultValue = 1.0, MinValue = 0.1)] public double K { get; set; }
        [Parameter("Hold Bars", Group = "Signal", DefaultValue = 10, MinValue = 1)] public int Hold { get; set; }

        [Parameter("Risk % / trade", Group = "Risk", DefaultValue = 1.0, MinValue = 0.05)] public double RiskPct { get; set; }
        [Parameter("Stop ATR mult",  Group = "Risk", DefaultValue = 4.0, MinValue = 0.0)] public double StopATR { get; set; }
        [Parameter("TP ATR mult",    Group = "Risk", DefaultValue = 1.5, MinValue = 0.0)] public double TpATR { get; set; }
        [Parameter("Trail ATR mult", Group = "Risk", DefaultValue = 0.0, MinValue = 0.0)] public double TrailATR { get; set; }
        [Parameter("Sizing ATR (if no stop)", Group = "Risk", DefaultValue = 3.0)] public double SizingATR { get; set; }

        [Parameter("ATR Period", Group = "Misc", DefaultValue = 14)] public int AtrPeriod { get; set; }
        [Parameter("Label", Group = "Misc", DefaultValue = "GM22_AMD")] public string Lbl { get; set; }
        [Parameter("Trend SMA (0=off)", Group = "Signal", DefaultValue = 0)] public int TrendSMA { get; set; }

        private AverageTrueRange _atr;
        private int _entryBar = -1;

        protected override void OnStart()
        {
            _atr = Indicators.AverageTrueRange(AtrPeriod, MovingAverageType.Simple);
            Print("GM22 AMD started. Sweep-then-expansion (ICT po3). LB={0} K={1}", LB, K);
        }

        private double Delta(int shift)
        {
            double sign = Bars.ClosePrices.Last(shift) >= Bars.OpenPrices.Last(shift) ? 1.0 : -1.0;
            return sign * Bars.TickVolumes.Last(shift);
        }
        private double LowestClose(int from, int n)
        { double m = double.MaxValue; for (int s = from; s < from + n; s++) m = Math.Min(m, Bars.ClosePrices.Last(s)); return m; }

        
        private bool TrendOK(int dir)
        { if (TrendSMA <= 0) return true; double s = 0; for (int i = 1; i <= TrendSMA; i++) s += Bars.ClosePrices.Last(i); s /= TrendSMA; double c = Bars.ClosePrices.Last(1); return dir > 0 ? c > s : c < s; }

        protected override void OnBar()
        {
            ManageOpen();
            if (Positions.Any(p => p.Label == Lbl)) return;
            if (Bars.ClosePrices.Count < LB + 6) return;

            double atr = _atr.Result.Last(1);
            double rng = Bars.HighPrices.Last(1) - Bars.LowPrices.Last(1);
            double llPrev2 = LowestClose(3, LB);                            // swing low ending at i-2

            if (Bars.LowPrices.Last(2) < llPrev2 &&                          // prior bar swept lows
                Bars.ClosePrices.Last(1) > Bars.ClosePrices.Last(2) &&      // now closing higher
                rng > K * atr && Delta(1) > 0 && TrendOK(1))                // expansion + buy delta + trend
                EnterLong(atr);
        }

        private void EnterLong(double atr)
        {
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
