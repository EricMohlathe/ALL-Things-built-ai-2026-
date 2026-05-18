// NotificationCenter.cs
// N-A..N-L cascade dispatcher (brief §4) — mirrors OF_NotificationCenter.mqh

using System;
using System.Collections.Generic;
using cAlgo.API;

namespace GodmodeOfea
{
    public sealed class NotificationCenter
    {
        private readonly Robot _robot;
        private readonly bool _sound, _push, _email, _enable;
        private readonly Dictionary<string, DateTime> _lastBarFired = new();
        private readonly Func<DateTime> _currentBarTime;

        public NotificationCenter(Robot robot, bool enable, bool sound, bool push, bool email,
            Func<DateTime> currentBarTime)
        {
            _robot = robot; _enable = enable; _sound = sound; _push = push; _email = email;
            _currentBarTime = currentBarTime;
        }

        private bool ShouldFire(string tag)
        {
            DateTime cur = _currentBarTime();
            if (_lastBarFired.TryGetValue(tag, out var last) && last == cur) return false;
            _lastBarFired[tag] = cur;
            return true;
        }

        public void Fire(string tag, string msg, SoundType? sound = null, bool sendPush = false)
        {
            if (!_enable) return;
            if (!ShouldFire(tag)) return;
            string text = $"[{_robot.SymbolName}] {tag} — {msg}";
            _robot.Print(text);
            try
            {
                if (_sound && sound.HasValue) _robot.Notifications.PlaySound(sound.Value);
                if (_push && sendPush) _robot.Notifications.SendEmail("godmode@local", "godmode@local", tag, text);
            }
            catch { }
            try { _robot.Chart.DrawStaticText("godmode_toast", text, VerticalAlignment.Bottom, HorizontalAlignment.Left, Color.White); } catch { }
        }

        public void NA_VpLevel(string lvl, double price) =>
            Fire("N-A", $"VP {lvl} touch @ {price:F5}", SoundType.PositiveNotification);
        public void NB_TripleConfluence() =>
            Fire("N-B", "Triple confluence achieved", SoundType.PositiveNotification);
        public void NC_KillZone(Session s) =>
            Fire("N-C", $"Kill zone active: {OFHelpers.SessionToStr(s)}");
        public void ND_HTFAligned(HtfBias b) =>
            Fire("N-D", $"HTF aligned: {OFHelpers.BiasToStr(b)}");
        public void NE_CvdConfirm(TradeDir d, double cvd) =>
            Fire("N-E", $"CVD confirms {OFHelpers.DirToStr(d)} (CVD={cvd:F0})", SoundType.PositiveNotification);
        public void NF_ProfileState(ProfileShape sh, MarketState st) =>
            Fire("N-F", $"Shape {OFHelpers.ShapeToStr(sh)} state {(int)st}");
        public void NG_FootprintSignal(string kind, int stars) =>
            Fire("N-G", $"Footprint {kind} ★{stars}", SoundType.PositiveNotification);
        public void NH_Aggression(double volZ) =>
            Fire("N-H", $"Aggression vol Z={volZ:F2}", SoundType.Announcement, true);
        public void NI_AplusReady(SetupCandidate c, double rr) =>
            Fire("N-I", $"A+ READY {OFHelpers.DirToStr(c.Direction)} setup={(int)c.SetupId} score={c.Score} R:R={rr:F1}",
                 SoundType.Announcement, true);
        public void NJ_TradeFired(SetupCandidate c, double lots, string mode) =>
            Fire("N-J", $"{OFHelpers.DirToStr(c.Direction)} {lots:F2} units @ {c.Entry:F5} SL {c.Sl:F5} TP {c.Tp:F5} [{mode}]",
                 SoundType.PositiveNotification, true);
        public void NK_PositionEvent(string ev) =>
            Fire("N-K_" + ev, $"Position event: {ev}", SoundType.PositiveNotification);
        public void NL_KillSwitch(string reason) =>
            Fire("N-L_" + reason, $"KILL SWITCH: {reason}", SoundType.NegativeNotification, true);

        // N-V: Pace-of-Tape elevated (microstructure aggression confirmation).
        // Brief §22 marginal-gain layer — see docs/external_data_integration.md.
        public void NV_PaceOfTape(double pace) =>
            Fire("N-V", $"Pace-of-Tape elevated pace={pace:F2}", SoundType.PositiveNotification);

        // N-W: Bookmap-confirmed iceberg (true microstructure, not the price-pattern proxy).
        // Fired when the BookmapBridge surfaces an ICEBERG event matching trade direction.
        public void NW_BookmapIceberg(string side, double price, int consec, double vol, double maxDepth) =>
            Fire("N-W", $"Bookmap iceberg {side} @ {price:F5} consec={consec} vol={vol:F0} maxDepth={maxDepth:F0}",
                 SoundType.Announcement, true);

        // N-X: Sierra Chart level proximity — close to a JIGSAW_Export-derived
        // POC/VAH/VAL/dVWAP/std-dev band. Strengthens GATE 3 location when present.
        public void NX_SierraChartLevel(string label, double price) =>
            Fire("N-X", $"Sierra Chart {label} @ {price:F5}", SoundType.PositiveNotification);

        // N-Y: Operator manual level proximity (Google Sheets-imported).
        public void NY_ManualLevel(string note, double price) =>
            Fire("N-Y", $"Manual level '{note}' @ {price:F5}", SoundType.PositiveNotification);
    }
}
