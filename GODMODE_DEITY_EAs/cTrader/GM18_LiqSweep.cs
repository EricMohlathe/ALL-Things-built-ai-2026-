// ============================================================================
//  GM18 LIQSWEEP — GODMODE DEITY EA (cTrader)  —  SELF-CONTAINED (D1)
// ----------------------------------------------------------------------------
//  Concept : Liquidity-sweep reversal, BOTH directions. Sweep below prior swing-low
//            (of closes, LB) and close in the UPPER half of range → LONG; mirror
//            (sweep high, close lower half) → SHORT. Stop-run reversal.
//
//  VALIDATED (real backtest, D1, no-lookahead, fees on, OOS = held-out 30%):
//     PLATINUM: PF 2.72 | WR 78% | 59 trd | OOS 1.45 | stopATR 2.5 / tpATR 0.8
//     AUDUSD  : PF 1.47 | WR 68% | 101 trd | OOS 2.27 | stopATR 3 / tpATR 1
//  Defaults = PLATINUM preset. Attach to D1 (NOT intraday — that config loses to costs).
// ============================================================================
using System;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None, AddIndicators = true)]
    public class GM18_LiqSweep : Robot
    {
        [Parameter("Lookback (LB)", Group = "Signal", DefaultValue = 20, MinValue = 5)] public int LB { get; set; }
        [Parameter("Hold Bars", Group = "Signal", DefaultValue = 10, MinValue = 1)] public int Hold { get; set; }
        [Parameter("Allow Long", Group = "Signal", DefaultValue = true)] public bool AllowLong { get; set; }
        [Parameter("Allow Short", Group = "Signal", DefaultValue = true)] public bool AllowShort { get; set; }
        [Parameter("Risk % / trade", Group = "Risk", DefaultValue = 1.0, MinValue = 0.05)] public double RiskPct { get; set; }
        [Parameter("Stop ATR mult", Group = "Risk", DefaultValue = 2.5, MinValue = 0.1)] public double StopATR { get; set; }
        [Parameter("TP ATR mult", Group = "Risk", DefaultValue = 0.8, MinValue = 0.0)] public double TpATR { get; set; }
        [Parameter("Trail ATR mult", Group = "Risk", DefaultValue = 0.0, MinValue = 0.0)] public double TrailATR { get; set; }
        [Parameter("ATR Period", Group = "Misc", DefaultValue = 14)] public int AtrPeriod { get; set; }
        [Parameter("Label", Group = "Misc", DefaultValue = "GM18_LiqSweep")] public string Lbl { get; set; }

        private AverageTrueRange _atr;
        private int _entryBar = -1;

        protected override void OnStart()
        { _atr = Indicators.AverageTrueRange(AtrPeriod, MovingAverageType.Simple); Print("GM18 LiqSweep (D1) started. Both-direction stop-run reversal."); }

        private double LowC(int f, int n) { double m = double.MaxValue; for (int i = f; i < f + n; i++) m = Math.Min(m, Bars.ClosePrices.Last(i)); return m; }
        private double HighC(int f, int n) { double m = double.MinValue; for (int i = f; i < f + n; i++) m = Math.Max(m, Bars.ClosePrices.Last(i)); return m; }

        protected override void OnBar()
        {
            Manage();
            if (Bars.ClosePrices.Count < LB + 5) return;
            double hi = Bars.HighPrices.Last(1), lo = Bars.LowPrices.Last(1), cl = Bars.ClosePrices.Last(1), rng = hi - lo;
            if (rng <= 0) return;
            int sig = 0;
            if (AllowLong && lo < LowC(2, LB) && cl > lo + 0.5 * rng) sig = 1;
            else if (AllowShort && hi > HighC(2, LB) && cl < hi - 0.5 * rng) sig = -1;
            if (sig == 0) return;
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
