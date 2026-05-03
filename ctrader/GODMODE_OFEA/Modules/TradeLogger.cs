// TradeLogger.cs
// CSV journal writer — schema per brief §13. Mirrors OF_Logger.mqh.

using System;
using System.Globalization;
using System.IO;

namespace GodmodeOfea
{
    public sealed class TradeLogger
    {
        private readonly string _path;
        private const string Header =
            "timestamp_utc,symbol,event_type,setup_id,score,priority," +
            "direction,entry_price,sl,tp,lots,risk_pct," +
            "session,market_state,htf_bias,profile_shape," +
            "poc,vah,val," +
            "cvd_at_entry,bar_delta,vol_z,delta_z,abs_stars," +
            "notif_cascade_completed,mode," +
            "result_pnl_pips,result_pnl_pct,result_R,hold_minutes";

        public TradeLogger(string path)
        {
            _path = path;
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(_path) ?? ".");
                if (!File.Exists(_path))
                    File.WriteAllText(_path, Header + Environment.NewLine);
            }
            catch (IOException) { /* logger never throws into the trade engine */ }
        }

        public void Append(string eventType, SetupCandidate c, string symbol,
                           Session session, MarketState state, HtfBias bias, ProfileShape shape,
                           double poc, double vah, double val,
                           double cvd, double barDelta, double volZ, double deltaZ,
                           string mode, double riskPct, double lots,
                           double resultPips = 0.0, double resultPct = 0.0,
                           double resultR = 0.0, double holdMin = 0.0)
        {
            var inv = CultureInfo.InvariantCulture;
            string row = string.Format(inv,
                "{0:yyyy.MM.dd HH:mm:ss},{1},{2},{3},{4},{5},{6},{7:F5},{8:F5},{9:F5},{10:F2},{11:F2}," +
                "{12},{13},{14},{15},{16:F5},{17:F5},{18:F5},{19:F0},{20:F0},{21:F2},{22:F2},{23},1,{24}," +
                "{25:F2},{26:F4},{27:F2},{28:F1}",
                DateTime.UtcNow, symbol, eventType, (int)c.SetupId, c.Score, (int)c.Priority,
                OFHelpers.DirToStr(c.Direction), c.Entry, c.Sl, c.Tp, lots, riskPct,
                OFHelpers.SessionToStr(session), (int)state, OFHelpers.BiasToStr(bias),
                OFHelpers.ShapeToStr(shape), poc, vah, val, cvd, barDelta, volZ, deltaZ, c.AbsStars,
                mode, resultPips, resultPct, resultR, holdMin);

            try { File.AppendAllText(_path, row + Environment.NewLine); }
            catch (IOException) { /* swallow — logger must not break execution */ }
        }
    }
}
