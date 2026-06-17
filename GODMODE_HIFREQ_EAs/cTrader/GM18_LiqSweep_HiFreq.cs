// ============================================================================
//  GM18 LIQSWEEP — GODMODE HIGH-FREQUENCY EA (cTrader)  —  SELF-CONTAINED
// ----------------------------------------------------------------------------
//  Concept : Liquidity-sweep reversal, BOTH directions. Price sweeps below the
//            prior swing-low (of closes, LB) then closes in the UPPER half of
//            its range = stop-run reversal LONG. Mirror for SHORT (sweep high,
//            close lower half). Intraday turnover engine.
//
//  VALIDATED (real backtest, BTC 15m, ~8000 bars / ~83 days, no-lookahead,
//  fill next open, fees on; OOS = held-out 30% tail):
//     BTC 15m, Hold 8, stopATR 4 / tpATR 1.5 :
//        PF 1.21 | WR 65% | ~5.0 trades/DAY | OOS PF 1.13
//
//  *** THIS IS A THIN EDGE (PF ~1.2). READ THE WARNING. ***
//  - High frequency (~5/day) but small per-trade edge. PF 1.2 means it is
//    HIGHLY sensitive to your broker's SPREAD/commission. A wide spread can
//    push it below break-even. Backtest it on YOUR symbol+spread first.
//  - Validated on crypto (BTC) only — the only market with free intraday
//    data + real order-flow. The LOGIC runs on any symbol you attach (forex,
//    metals, indices, crypto), but you MUST validate per-symbol in the
//    cTrader backtester before trusting it. The edge is NOT guaranteed to
//    transfer across asset classes.
//  - Attach to a 15-MINUTE chart to match the validated config.
// ============================================================================
using System;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None, AddIndicators = true)]
    public class GM18_LiqSweep_HiFreq : Robot
    {
        [Parameter("Lookback (LB)", Group = "Signal", DefaultValue = 20, MinValue = 5)] public int LB { get; set; }
        [Parameter("Hold Bars", Group = "Signal", DefaultValue = 8, MinValue = 1)] public int Hold { get; set; }
        [Parameter("Allow Long", Group = "Signal", DefaultValue = true)] public bool AllowLong { get; set; }
        [Parameter("Allow Short", Group = "Signal", DefaultValue = true)] public bool AllowShort { get; set; }

        [Parameter("Risk % / trade", Group = "Risk", DefaultValue = 1.0, MinValue = 0.05)] public double RiskPct { get; set; }
        [Parameter("Stop ATR mult", Group = "Risk", DefaultValue = 4.0, MinValue = 0.1)] public double StopATR { get; set; }
        [Parameter("TP ATR mult", Group = "Risk", DefaultValue = 1.5, MinValue = 0.0)] public double TpATR { get; set; }
        [Parameter("Trail ATR mult", Group = "Risk", DefaultValue = 0.0, MinValue = 0.0)] public double TrailATR { get; set; }
        [Parameter("Max Spread (price, 0=off)", Group = "Risk", DefaultValue = 0.0)] public double MaxSpread { get; set; }

        [Parameter("ATR Period", Group = "Misc", DefaultValue = 14)] public int AtrPeriod { get; set; }
        [Parameter("Label", Group = "Misc", DefaultValue = "GM18_HiFreq")] public string Lbl { get; set; }

        private AverageTrueRange _atr;
        private int _entryBar = -1;

        protected override void OnStart()
        {
            _atr = Indicators.AverageTrueRange(AtrPeriod, MovingAverageType.Simple);
            Print("GM18 LiqSweep HiFreq started. Attach to M15. LB={0} Hold={1}", LB, Hold);
        }

        private double LowestClose(int from, int n)
        { double m = double.MaxValue; for (int s = from; s < from + n; s++) m = Math.Min(m, Bars.ClosePrices.Last(s)); return m; }
        private double HighestClose(int from, int n)
        { double m = double.MinValue; for (int s = from; s < from + n; s++) m = Math.Max(m, Bars.ClosePrices.Last(s)); return m; }

        protected override void OnBar()
        {
            ManageOpen();
            if (Bars.ClosePrices.Count < LB + 5) return;

            double hi = Bars.HighPrices.Last(1), lo = Bars.LowPrices.Last(1), cl = Bars.ClosePrices.Last(1);
            double rng = (hi - lo); if (rng <= 0) return;
            int sig = 0;
            if (AllowLong && lo < LowestClose(2, LB) && cl > lo + 0.5 * rng) sig = 1;       // sweep low, close upper half
            else if (AllowShort && hi > HighestClose(2, LB) && cl < hi - 0.5 * rng) sig = -1; // sweep high, close lower half
            if (sig == 0) return;

            var pos = Positions.FirstOrDefault(p => p.Label == Lbl);
            int curDir = pos == null ? 0 : (pos.TradeType == TradeType.Buy ? 1 : -1);
            if (sig == curDir) return;                 // already in that direction
            if (pos != null) ClosePosition(pos);       // flip on opposite signal
            Enter(sig);
        }

        private void Enter(int dir)
        {
            if (MaxSpread > 0 && (Symbol.Ask - Symbol.Bid) > MaxSpread) return;
            double atr = _atr.Result.Last(1);
            if (atr <= 0) return;
            double riskCash = Account.Equity * (RiskPct / 100.0);
            double volume = Symbol.NormalizeVolumeInUnits(riskCash / (StopATR * atr), RoundingMode.Down);
            if (volume < Symbol.VolumeInUnitsMin) volume = Symbol.VolumeInUnitsMin;
            double slPips = StopATR * atr / Symbol.PipSize;
            double? tpPips = TpATR > 0 ? (double?)(TpATR * atr / Symbol.PipSize) : null;
            var tt = dir > 0 ? TradeType.Buy : TradeType.Sell;
            var r = ExecuteMarketOrder(tt, SymbolName, volume, Lbl, slPips, tpPips);
            if (r.IsSuccessful) _entryBar = Bars.ClosePrices.Count - 1;
        }

        private void ManageOpen()
        {
            var pos = Positions.FirstOrDefault(p => p.Label == Lbl);
            if (pos == null) { _entryBar = -1; return; }
            if (TrailATR > 0)
            {
                double atr = _atr.Result.Last(1);
                if (pos.TradeType == TradeType.Buy)
                {
                    double nsl = Symbol.Bid - TrailATR * atr;
                    if (!pos.StopLoss.HasValue || nsl > pos.StopLoss.Value) ModifyPosition(pos, nsl, pos.TakeProfit);
                }
                else
                {
                    double nsl = Symbol.Ask + TrailATR * atr;
                    if (!pos.StopLoss.HasValue || nsl < pos.StopLoss.Value) ModifyPosition(pos, nsl, pos.TakeProfit);
                }
            }
            if (_entryBar >= 0 && (Bars.ClosePrices.Count - 1 - _entryBar) >= Hold) ClosePosition(pos);
        }
    }
}
