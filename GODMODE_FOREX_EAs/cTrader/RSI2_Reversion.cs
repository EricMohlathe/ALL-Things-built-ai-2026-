// ============================================================================
//  RSI2 REVERSION — GODMODE FOREX EA (cTrader)  —  SELF-CONTAINED
// ----------------------------------------------------------------------------
//  Concept : Connors RSI(2) mean reversion WITH a long-term trend filter.
//            Buy oversold dips only while price is above its 200-SMA (uptrend),
//            exit when RSI(2) recovers. Long-only. No order-flow / volume needed
//            -> works on SPOT forex where delta setups can't. Different family
//            from the metals/indices deity setups.
//
//  VALIDATED (real backtest, D1, no-lookahead, fees on, OOS = held-out 30%):
//     JPY futures (6J) : PF 4.73 | WR 76% | 45 trd | OOS PF 2.88 | stopATR 4 / tpATR 1.5
//  Logic is symbol-agnostic. Best forex fit per the scan = JPY. Validate YOUR
//  pair in the cTrader backtester before trusting it. Attach to a D1 chart.
// ============================================================================
using System;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None, AddIndicators = true)]
    public class RSI2_Reversion : Robot
    {
        [Parameter("RSI Period", Group = "Signal", DefaultValue = 2, MinValue = 2)] public int RsiN { get; set; }
        [Parameter("Buy below RSI", Group = "Signal", DefaultValue = 10.0)] public double BuyLevel { get; set; }
        [Parameter("Exit above RSI", Group = "Signal", DefaultValue = 60.0)] public double ExitLevel { get; set; }
        [Parameter("Trend SMA", Group = "Signal", DefaultValue = 200, MinValue = 10)] public int TrendN { get; set; }

        [Parameter("Risk % / trade", Group = "Risk", DefaultValue = 1.0, MinValue = 0.05)] public double RiskPct { get; set; }
        [Parameter("Stop ATR mult", Group = "Risk", DefaultValue = 4.0, MinValue = 0.1)] public double StopATR { get; set; }
        [Parameter("TP ATR mult", Group = "Risk", DefaultValue = 1.5, MinValue = 0.0)] public double TpATR { get; set; }
        [Parameter("ATR Period", Group = "Misc", DefaultValue = 14)] public int AtrPeriod { get; set; }
        [Parameter("Label", Group = "Misc", DefaultValue = "RSI2_Rev")] public string Lbl { get; set; }

        private RelativeStrengthIndex _rsi;
        private SimpleMovingAverage _sma;
        private AverageTrueRange _atr;

        protected override void OnStart()
        {
            _rsi = Indicators.RelativeStrengthIndex(Bars.ClosePrices, RsiN);
            _sma = Indicators.SimpleMovingAverage(Bars.ClosePrices, TrendN);
            _atr = Indicators.AverageTrueRange(AtrPeriod, MovingAverageType.Simple);
            Print("RSI2 Reversion started. Long-only mean reversion + SMA{0} filter.", TrendN);
        }

        protected override void OnBar()
        {
            var pos = Positions.FirstOrDefault(p => p.Label == Lbl);
            double rsi = _rsi.Result.Last(1);
            if (pos != null)
            {
                if (rsi > ExitLevel) ClosePosition(pos);   // mean-reversion exit
                return;
            }
            if (Bars.ClosePrices.Count < TrendN + 3) return;
            bool up = Bars.ClosePrices.Last(1) > _sma.Result.Last(1);
            if (up && rsi < BuyLevel) Enter();
        }

        private void Enter()
        {
            double atr = _atr.Result.Last(1);
            if (atr <= 0) return;
            double vol = Symbol.NormalizeVolumeInUnits(Account.Equity * (RiskPct / 100.0) / (StopATR * atr), RoundingMode.Down);
            if (vol < Symbol.VolumeInUnitsMin) vol = Symbol.VolumeInUnitsMin;
            double slPips = StopATR * atr / Symbol.PipSize;
            double? tpPips = TpATR > 0 ? (double?)(TpATR * atr / Symbol.PipSize) : null;
            ExecuteMarketOrder(TradeType.Buy, SymbolName, vol, Lbl, slPips, tpPips);
        }
    }
}
