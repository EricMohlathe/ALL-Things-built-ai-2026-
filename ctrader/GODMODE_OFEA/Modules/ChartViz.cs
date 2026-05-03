// ChartViz.cs
// VP lines / footprint markers / trade lines / session shading (brief §9)
// Mirrors mt5/Include/OF_ChartViz.mqh

using System;
using cAlgo.API;

namespace GodmodeOfea
{
    public sealed class ChartViz
    {
        private readonly Chart _chart;
        private readonly bool _showVP, _showFp, _showSess, _showTrade;

        public ChartViz(Chart chart, bool vp, bool fp, bool sess, bool trade)
        {
            _chart = chart; _showVP = vp; _showFp = fp; _showSess = sess; _showTrade = trade;
        }

        public void DrawVPLevels(double poc, double vah, double val)
        {
            if (!_showVP) return;
            _chart.DrawHorizontalLine("godmode_poc", poc, Color.Magenta, 2, LineStyle.Solid);
            _chart.DrawHorizontalLine("godmode_vah", vah, Color.DodgerBlue, 1, LineStyle.Dots);
            _chart.DrawHorizontalLine("godmode_val", val, Color.DodgerBlue, 1, LineStyle.Dots);
        }

        public void DrawAbsorption(string id, double price, DateTime t, TradeDir dir, int stars)
        {
            if (!_showFp) return;
            var c = dir == TradeDir.Long ? Color.Lime : Color.Red;
            _chart.DrawIcon("godmode_abs_" + id, ChartIconType.Star, t, price, c);
            _chart.DrawText("godmode_abs_t_" + id, $"★{stars}", t, price, c);
        }

        public void DrawTradeLines(double entry, double sl, double tp, TradeDir dir)
        {
            if (!_showTrade) return;
            var c = dir == TradeDir.Long ? Color.Lime : Color.OrangeRed;
            _chart.DrawHorizontalLine("godmode_te", entry, c, 2, LineStyle.Solid);
            _chart.DrawHorizontalLine("godmode_tsl", sl, Color.Red, 1, LineStyle.Dots);
            _chart.DrawHorizontalLine("godmode_ttp", tp, Color.LimeGreen, 1, LineStyle.Dots);
        }

        public void DrawSessionRect(DateTime t1, DateTime t2, Color clr, string id)
        {
            if (!_showSess) return;
            double hi = _chart.TopY, lo = _chart.BottomY;
            _chart.DrawRectangle("godmode_sess_" + id, t1, hi, t2, lo, clr).IsFilled = true;
        }
    }
}
