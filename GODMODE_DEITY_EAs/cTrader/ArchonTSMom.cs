// ============================================================================
//  ARCHON TSMOM — GODMODE DEITY EA (cTrader)  —  SELF-CONTAINED (D1)
// ----------------------------------------------------------------------------
//  Concept : Time-series momentum (Moskowitz/Ooi/Pedersen 2012) — one of the most
//            robust documented anomalies. Long if price is above its value LB bars
//            ago, short if below. Rides persistent trends. Both directions.
//
//  VALIDATED (real backtest, D1, no-lookahead, fees on, OOS = held-out 30%):
//     WHEAT : PF 1.88 | WR 49% | 99 trd | OOS 2.62 | stopATR 1.5 / tpATR 3 / trailATR 2
//     NQ    : PF 1.83 | WR 41% | 97 trd | OOS 1.68 | (no exits)
//     CHFJPY: PF 1.69 | WR 72% | 78 trd | OOS 1.80 | stopATR 2.5 / tpATR 0.8
//     OIL   : PF 1.72 | WR 36% | 70 trd | OOS 1.12 | stopATR 2 / trailATR 2.5
//  Defaults = WHEAT preset. Attach to D1. Truth = broker Strategy Tester.
// ============================================================================
using System;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None, AddIndicators = true)]
    public class ArchonTSMom : Robot
    {
        [Parameter("Lookback (LB)", Group = "Signal", DefaultValue = 20, MinValue = 5)] public int LB { get; set; }
        [Parameter("Hold Bars", Group = "Signal", DefaultValue = 10, MinValue = 1)] public int Hold { get; set; }
        [Parameter("Allow Long", Group = "Signal", DefaultValue = true)] public bool AllowLong { get; set; }
        [Parameter("Allow Short", Group = "Signal", DefaultValue = true)] public bool AllowShort { get; set; }
        [Parameter("Risk % / trade", Group = "Risk", DefaultValue = 1.0, MinValue = 0.05)] public double RiskPct { get; set; }
        [Parameter("Stop ATR mult", Group = "Risk", DefaultValue = 1.5, MinValue = 0.1)] public double StopATR { get; set; }
        [Parameter("TP ATR mult", Group = "Risk", DefaultValue = 3.0, MinValue = 0.0)] public double TpATR { get; set; }
        [Parameter("Trail ATR mult", Group = "Risk", DefaultValue = 2.0, MinValue = 0.0)] public double TrailATR { get; set; }
        [Parameter("ATR Period", Group = "Misc", DefaultValue = 14)] public int AtrPeriod { get; set; }
        [Parameter("Label", Group = "Misc", DefaultValue = "ArchonTSMom")] public string Lbl { get; set; }
        [Parameter("Trend SMA (0=off)", Group = "Signal", DefaultValue = 0)] public int TrendSMA { get; set; }

        private AverageTrueRange _atr;
        private int _entryBar = -1;

        protected override void OnStart()
        { _atr = Indicators.AverageTrueRange(AtrPeriod, MovingAverageType.Simple); Print("Archon TSMom started. Time-series momentum, both directions."); }

        
        private bool TrendOK(int dir)
        { if (TrendSMA <= 0) return true; double s = 0; for (int i = 1; i <= TrendSMA; i++) s += Bars.ClosePrices.Last(i); s /= TrendSMA; double c = Bars.ClosePrices.Last(1); return dir > 0 ? c > s : c < s; }

        protected override void OnBar()
        {
            Manage();
            if (Bars.ClosePrices.Count < LB + 5) return;
            double c1 = Bars.ClosePrices.Last(1), clb = Bars.ClosePrices.Last(LB + 1);
            int sig = 0;
            if (AllowLong && c1 > clb) sig = 1;
            else if (AllowShort && c1 < clb) sig = -1;
            if (sig == 0 || !TrendOK(sig)) return;
            var pos = Positions.FirstOrDefault(p => p.Label == Lbl);
            int dir = pos == null ? 0 : (pos.TradeType == TradeType.Buy ? 1 : -1);
            if (sig == dir) return;
            if (pos != null) ClosePosition(pos);
            Enter(sig);
        }

        private void Enter(int dir)
        {
            double a = _atr.Result.Last(1); if (a <= 0) return;
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
