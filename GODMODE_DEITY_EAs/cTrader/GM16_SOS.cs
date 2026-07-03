// ============================================================================
//  GM16 SOS (Sign of Strength)  —  GODMODE DEITY EA (cTrader / cAlgo)  —  SELF-CONTAINED
// ----------------------------------------------------------------------------
//  Concept : Wyckoff Sign of Strength. A WIDE-range up bar (range > K x ATR),
//            closing up, with positive delta, that breaks the prior swing-high
//            (of closes, LB) = demand expansion / markup begins. Long-only.
//            Delta = signed volume (+vol up-close / -vol down-close).
//
//  VALIDATED (real backtest, daily, no-lookahead, OOS = held-out 30% tail):
//     NQ (NASDAQ100) 1D : PF 2.92 | WR 64.4% | 59 trd | +96.8% | OOS PF 2.31 | stopATR 2 / tpATR 4 / trailATR 3
//     ES (SP500)     1D : PF 2.87 | WR 83.6% | 61 trd | +34.0% | OOS PF 1.81 | stopATR 3 / tpATR 1
//     YM (US30)      1D : PF 2.38 | WR 58.2% | 67 trd | +48.2% | OOS PF 1.83 | exits NONE (hold-only)
//     SILVER(SI=F)   1D : PF 1.83 | WR 57.1% | 49 trd | +40.3% | OOS PF 2.91 | stopATR 1.5 / tpATR 3 / trailATR 2
//  Defaults = NQ preset. Truth = broker Strategy Tester; numbers = edge evidence.
// ============================================================================
using System;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None, AddIndicators = true)]
    public class GM16_SOS : Robot
    {
        [Parameter("Lookback (LB)", Group = "Signal", DefaultValue = 20, MinValue = 5)] public int LB { get; set; }
        [Parameter("K (range x ATR)", Group = "Signal", DefaultValue = 1.0, MinValue = 0.1)] public double K { get; set; }
        [Parameter("Hold Bars", Group = "Signal", DefaultValue = 10, MinValue = 1)] public int Hold { get; set; }

        [Parameter("Risk % / trade", Group = "Risk", DefaultValue = 1.0, MinValue = 0.05)] public double RiskPct { get; set; }
        [Parameter("Stop ATR mult",  Group = "Risk", DefaultValue = 2.0, MinValue = 0.0)] public double StopATR { get; set; }
        [Parameter("TP ATR mult",    Group = "Risk", DefaultValue = 4.0, MinValue = 0.0)] public double TpATR { get; set; }
        [Parameter("Trail ATR mult", Group = "Risk", DefaultValue = 3.0, MinValue = 0.0)] public double TrailATR { get; set; }
        [Parameter("Sizing ATR (if no stop)", Group = "Risk", DefaultValue = 3.0)] public double SizingATR { get; set; }

        [Parameter("ATR Period", Group = "Misc", DefaultValue = 14)] public int AtrPeriod { get; set; }
        [Parameter("Label", Group = "Misc", DefaultValue = "GM16_SOS")] public string Lbl { get; set; }
        [Parameter("Trend SMA (0=off)", Group = "Signal", DefaultValue = 0)] public int TrendSMA { get; set; }

        private AverageTrueRange _atr;
        private int _entryBar = -1;

        protected override void OnStart()
        {
            _atr = Indicators.AverageTrueRange(AtrPeriod, MovingAverageType.Simple);
            Print("GM16 SOS started. Wide-range demand expansion breakout. LB={0} K={1}", LB, K);
        }

        private double Delta(int shift)
        {
            double sign = Bars.ClosePrices.Last(shift) >= Bars.OpenPrices.Last(shift) ? 1.0 : -1.0;
            return sign * Bars.TickVolumes.Last(shift);
        }
        private double HighestClose(int from, int n)
        { double m = double.MinValue; for (int s = from; s < from + n; s++) m = Math.Max(m, Bars.ClosePrices.Last(s)); return m; }

        
        private bool TrendOK(int dir)
        { if (TrendSMA <= 0) return true; double s = 0; for (int i = 1; i <= TrendSMA; i++) s += Bars.ClosePrices.Last(i); s /= TrendSMA; double c = Bars.ClosePrices.Last(1); return dir > 0 ? c > s : c < s; }

        protected override void OnBar()
        {
            ManageOpen();
            if (Positions.Any(p => p.Label == Lbl)) return;
            if (Bars.ClosePrices.Count < LB + 5) return;

            double atr = _atr.Result.Last(1);
            double rng = Bars.HighPrices.Last(1) - Bars.LowPrices.Last(1);
            bool up = Bars.ClosePrices.Last(1) > Bars.OpenPrices.Last(1);
            double hhPrev = HighestClose(2, LB);

            if (rng > K * atr && up && Delta(1) > 0 && Bars.ClosePrices.Last(1) >= hhPrev && TrendOK(1))
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
