// Dashboard.cs
// 8-row checklist + metrics panel (brief §3, §9.6) — mirrors OF_Dashboard.mqh.

using System;
using cAlgo.API;

namespace GodmodeOfea
{
    public sealed class Dashboard
    {
        private readonly Chart _chart;
        private readonly Color _ok, _fail, _wait;
        private DateTime _lastRefresh;

        public Dashboard(Chart chart, Color ok, Color fail, Color wait)
        {
            _chart = chart; _ok = ok; _fail = fail; _wait = wait;
        }

        public bool ShouldRefresh()
        {
            // throttle to ~250 ms (brief §23.6)
            var now = DateTime.UtcNow;
            if ((now - _lastRefresh).TotalMilliseconds < 250) return false;
            _lastRefresh = now;
            return true;
        }

        private void Row(string id, string text, Color c)
        {
            _chart.DrawStaticText("godmode_" + id, text, VerticalAlignment.Top, HorizontalAlignment.Right, c);
        }

        public void Render(string sym, string mode,
                           MarketState state, Session sess, HtfBias bias, VpLoc loc,
                           TradeDir cvdDir, bool fpReady,
                           double sl, double rr, int score, Priority prio,
                           double cvd, double bd, double volZ,
                           double poc, double vah, double val,
                           double dailyDD, int trades)
        {
            // Compose the 8-row panel as a single multi-line string per cAlgo idiom.
            string panel =
                $"GODMODE OFEA — {sym} — {mode}\n" +
                $"[1] State ........ {(state == MarketState.Balanced ? "BAL" : state == MarketState.Imbalanced ? "IMB" : "UNK")}\n" +
                $"[2] KillZone .... {OFHelpers.SessionToStr(sess)}\n" +
                $"[3] HTF ......... {OFHelpers.BiasToStr(bias)}\n" +
                $"[4] VP Loc ...... {OFHelpers.LocToStr(loc)}\n" +
                $"[5] CVD ......... {(cvdDir == TradeDir.Long ? "BULL" : cvdDir == TradeDir.Short ? "BEAR" : "FLAT")}\n" +
                $"[6] Footprint ... {(fpReady ? "OK" : "WAITING")}\n" +
                $"[7] SL .......... {sl:F5}\n" +
                $"[8] R:R ......... {rr:F1}\n" +
                $"CONF {score}/8 P{(int)prio}\n" +
                $"CVD {cvd:F0} Δ {bd:F0} volZ {volZ:F2}\n" +
                $"POC {poc:F5} VAH {vah:F5} VAL {val:F5}\n" +
                $"DD {dailyDD:F2}% Trades {trades}";
            Color overall = score >= 6 ? _ok : _wait;
            _chart.DrawStaticText("godmode_panel", panel, VerticalAlignment.Top, HorizontalAlignment.Right, overall);
        }

        public void Clear() => _chart.RemoveObject("godmode_panel");
    }
}
