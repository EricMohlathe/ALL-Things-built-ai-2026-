// AutoRiskReward.cs
//
// Automatically draws a Reward/Risk visual annotation on the cTrader chart
// every time the EA opens a position. Adapted from Frozen Tundra auto_risk_
// reward.cpp (Sierra Chart) which auto-creates the canonical "RR Tool"
// rectangle on each new fill.
//
// In cTrader we have no built-in RR tool, but we can compose the same visual
// from primitive Chart drawings: a green TP rectangle above entry, a red SL
// rectangle below entry, a horizontal entry line with size + R:R label, and
// optional partial / BE / trail markers.
//
// Wires into TradeManager: call OnPositionOpened(Position p) when a position
// is opened, OnPositionClosed(Position p) when closed (cleans up the drawing).
// Brief §9.5 "Trade Lines" — this implements that section.

using System;
using cAlgo.API;
using cAlgo.API.Internals;

namespace GodmodeOfea
{
    public sealed class AutoRiskReward
    {
        private readonly Robot _robot;
        private readonly Chart _chart;
        private readonly Symbol _symbol;
        private readonly bool _showCurrencyValue;
        private readonly int _fontSize;
        private readonly int _lineWidth;

        // We track a single annotation per position. Operators of multi-position
        // EAs would extend this to a Dictionary<long, AnnotationGroup> keyed on
        // position.Id; brief §19 rule 9 default is no pyramiding so single is fine.
        private long _trackedPositionId = 0;
        private string _entryLineKey = string.Empty;
        private string _slRectKey = string.Empty;
        private string _tpRectKey = string.Empty;
        private string _labelKey = string.Empty;

        public AutoRiskReward(Robot robot, Chart chart, Symbol symbol,
                              int fontSize = 11, int lineWidth = 1, bool showCurrencyValue = true)
        {
            _robot = robot;
            _chart = chart;
            _symbol = symbol;
            _fontSize = fontSize;
            _lineWidth = lineWidth;
            _showCurrencyValue = showCurrencyValue;
        }

        public void OnPositionOpened(Position p)
        {
            if (p == null) return;
            if (p.SymbolName != _symbol.Name) return;
            // Clean any previous drawings.
            ClearDrawings();
            _trackedPositionId = p.Id;
            _entryLineKey = $"godmode_rr_entry_{p.Id}";
            _slRectKey    = $"godmode_rr_sl_{p.Id}";
            _tpRectKey    = $"godmode_rr_tp_{p.Id}";
            _labelKey     = $"godmode_rr_label_{p.Id}";
            Redraw(p);
        }

        public void OnTick(Position p)
        {
            if (p == null || p.Id != _trackedPositionId) return;
            // Refresh the right edge so the rectangles always extend to the latest bar.
            Redraw(p);
        }

        public void OnPositionClosed(long positionId)
        {
            if (positionId != _trackedPositionId) return;
            ClearDrawings();
            _trackedPositionId = 0;
        }

        private void Redraw(Position p)
        {
            try
            {
                double entry = p.EntryPrice;
                double sl = p.StopLoss ?? entry;
                double tp = p.TakeProfit ?? entry;
                if (sl == 0 || tp == 0) return;

                DateTime tStart = _chart.Bars[Math.Max(0, _chart.Bars.Count - 100)].OpenTime;
                DateTime tEnd   = _chart.Bars[_chart.Bars.Count - 1].OpenTime.AddMinutes(120);

                // SL rectangle (entry → SL, red, semi-transparent).
                var slRect = _chart.DrawRectangle(_slRectKey, tStart, entry, tEnd, sl, Color.FromArgb(60, 220, 60, 60));
                slRect.IsFilled = true;

                // TP rectangle (entry → TP, green, semi-transparent).
                var tpRect = _chart.DrawRectangle(_tpRectKey, tStart, entry, tEnd, tp, Color.FromArgb(60, 60, 220, 60));
                tpRect.IsFilled = true;

                // Entry line.
                var entryLine = _chart.DrawTrendLine(_entryLineKey, tStart, entry, tEnd, entry, Color.White);
                entryLine.LineStyle = LineStyle.Solid;
                entryLine.Thickness = _lineWidth;

                // Label: size + R:R + optional currency.
                double risk = Math.Abs(entry - sl);
                double reward = Math.Abs(tp - entry);
                double rr = risk > 0 ? reward / risk : 0;
                double riskPips = risk / OFHelpers.PipSize(_symbol);
                double rewardPips = reward / OFHelpers.PipSize(_symbol);

                string text = $"{p.TradeType.ToString().ToUpperInvariant()} {p.VolumeInUnits:N0}\n" +
                              $"Risk: {riskPips:F1} pips  Reward: {rewardPips:F1} pips\n" +
                              $"R:R = {rr:F2}";
                if (_showCurrencyValue)
                {
                    double pipValue = _symbol.PipValue;
                    text += $"\n≈ {pipValue * riskPips:N2} risk / {pipValue * rewardPips:N2} reward";
                }
                _chart.DrawStaticText(_labelKey, text, VerticalAlignment.Center, HorizontalAlignment.Right, Color.Yellow);
            }
            catch (Exception e)
            {
                _robot.Print($"AutoRR draw err: {e.Message}");
            }
        }

        private void ClearDrawings()
        {
            try
            {
                if (!string.IsNullOrEmpty(_entryLineKey)) _chart.RemoveObject(_entryLineKey);
                if (!string.IsNullOrEmpty(_slRectKey))    _chart.RemoveObject(_slRectKey);
                if (!string.IsNullOrEmpty(_tpRectKey))    _chart.RemoveObject(_tpRectKey);
                if (!string.IsNullOrEmpty(_labelKey))     _chart.RemoveObject(_labelKey);
            }
            catch { /* drawing may already be gone */ }
        }
    }
}
