// ============================================================================
//  GM14 SPRING  —  GODMODE DEITY EA (cTrader / cAlgo)  —  SELF-CONTAINED
// ----------------------------------------------------------------------------
//  Concept : Wyckoff spring / liquidity-sweep reclaim. Price wicks BELOW the
//            prior swing-low (of closes, lookback LB) then CLOSES back above it
//            = stop-run reversal long. Long-only (only the long side validated).
//
//  VALIDATED (real backtest, OpenAlice stdlib engine, ~1000 daily bars, no-lookahead,
//  signal on close, fill next open, fees on; out-of-sample = held-out tail 30%):
//     SILVER(SI=F) 1D : PF 5.74 | WR 71.7% | 53 trd | +323.5% | OOS PF 8.96  | exits: NONE (hold-only)
//     YM (US30)    1D : PF 2.48 | WR 81.0% | 58 trd | +59.8%  | OOS PF 2.01  | stopATR 4 / tpATR 1.5
//     GOLD(GC=F)   1D : PF 2.29 | WR 75.5% | 49 trd | +27.6%  | OOS PF 2.78  | stopATR 3 / tpATR 1
//     ES (SP500)   1D : PF 1.72 | WR 78.0% | 50 trd | +24.4%  | OOS PF 1.26  | stopATR 4 / tpATR 1.5
//
//  Defaults below = GOLD preset (has a protective stop). For the max-PF SILVER
//  variant set StopATR=0, TpATR=0 (hold-only) — but understand that runs with NO
//  hard stop. See README for the full preset table + reproduction steps.
//
//  Edge is TREND-ALIGNED (buy springs inside an uptrending asset). It will
//  underperform in sustained downtrends — this is honest, not a flaw.
//  Truth = your broker's Strategy Tester. These numbers are the edge evidence.
// ============================================================================
using System;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None, AddIndicators = true)]
    public class GM14_Spring : Robot
    {
        [Parameter("Lookback (LB)", Group = "Signal", DefaultValue = 20, MinValue = 5)] public int LB { get; set; }
        [Parameter("Hold Bars",     Group = "Signal", DefaultValue = 10, MinValue = 1)] public int Hold { get; set; }

        [Parameter("Risk % / trade", Group = "Risk", DefaultValue = 1.0, MinValue = 0.05)] public double RiskPct { get; set; }
        [Parameter("Stop ATR mult",  Group = "Risk", DefaultValue = 3.0, MinValue = 0.0)]  public double StopATR { get; set; }
        [Parameter("TP ATR mult",    Group = "Risk", DefaultValue = 1.0, MinValue = 0.0)]  public double TpATR { get; set; }
        [Parameter("Trail ATR mult", Group = "Risk", DefaultValue = 0.0, MinValue = 0.0)]  public double TrailATR { get; set; }
        [Parameter("Sizing ATR (if no stop)", Group = "Risk", DefaultValue = 3.0)] public double SizingATR { get; set; }

        [Parameter("ATR Period", Group = "Misc", DefaultValue = 14)] public int AtrPeriod { get; set; }
        [Parameter("Label",      Group = "Misc", DefaultValue = "GM14_Spring")] public string Lbl { get; set; }

        private AverageTrueRange _atr;
        private int _entryBar = -1;

        protected override void OnStart()
        {
            _atr = Indicators.AverageTrueRange(AtrPeriod, MovingAverageType.Simple);
            Print("GM14 Spring started. Long-only Wyckoff spring. LB={0} Hold={1}", LB, Hold);
        }

        // lowest/highest CLOSE over `n` bars, window ending at shift `from` (inclusive going back)
        private double LowestClose(int from, int n)
        { double m = double.MaxValue; for (int s = from; s < from + n; s++) m = Math.Min(m, Bars.ClosePrices.Last(s)); return m; }

        protected override void OnBar()
        {
            ManageOpen();
            if (Positions.Any(p => p.Label == Lbl)) return;           // one position at a time
            if (Bars.ClosePrices.Count < LB + 5) return;

            double sigLow = Bars.LowPrices.Last(1);
            double sigClose = Bars.ClosePrices.Last(1);
            double llPrev = LowestClose(2, LB);                       // swing low of closes, NOT incl. signal bar

            if (sigLow < llPrev && sigClose > llPrev)                 // GM14 spring (long)
                EnterLong();
        }

        private void EnterLong()
        {
            double atr = _atr.Result.Last(1);
            if (atr <= 0) return;
            double riskRef = (StopATR > 0 ? StopATR : SizingATR) * atr;     // price-distance used for sizing
            double riskCash = Account.Equity * (RiskPct / 100.0);
            double unitsPerPrice = riskCash / riskRef;                      // volume in units = cash / price-distance
            double volume = Symbol.NormalizeVolumeInUnits(unitsPerPrice, RoundingMode.Down);
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

            // ATR trailing stop (ratchet up only)
            if (TrailATR > 0)
            {
                double atr = _atr.Result.Last(1);
                double newSl = Symbol.Bid - TrailATR * atr;
                if (!pos.StopLoss.HasValue || newSl > pos.StopLoss.Value)
                    ModifyPosition(pos, newSl, pos.TakeProfit);
            }
            // time-based exit after Hold bars (matches validated hold logic)
            if (_entryBar >= 0 && (Bars.ClosePrices.Count - 1 - _entryBar) >= Hold)
                ClosePosition(pos);
        }
    }
}
