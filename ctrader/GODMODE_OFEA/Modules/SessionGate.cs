// SessionGate.cs
// SAST window detection + kill-zone tagging (brief §11.6, §22.6)
// Mirrors OF_SessionGate.mqh

using System;
using cAlgo.API;

namespace GodmodeOfea
{
    public sealed class SessionGate
    {
        private readonly int _offsetHours;
        private readonly int _nyOpenBlackoutMin;
        private readonly bool _tA, _tLO, _tLM, _tNO, _tNM;
        private Session _lastSession = Session.None;

        public SessionGate(int offset, int nyBlackout,
            bool asian, bool ldnO, bool ldnM, bool nyO, bool nyM)
        {
            _offsetHours = offset; _nyOpenBlackoutMin = nyBlackout;
            _tA = asian; _tLO = ldnO; _tLM = ldnM; _tNO = nyO; _tNM = nyM;
        }

        public int SastMinute(DateTime brokerNowUtc)
        {
            int h = brokerNowUtc.Hour + _offsetHours;
            while (h >= 24) h -= 24;
            while (h < 0)   h += 24;
            return h * 60 + brokerNowUtc.Minute;
        }

        public Session Classify(DateTime brokerNowUtc, out int sastMin)
        {
            int m = SastMinute(brokerNowUtc);
            sastMin = m;
            if (m >= 120  && m < 600)  return Session.Asian;
            if (m >= 600  && m < 660)  return Session.LdnOpen;
            if (m >= 660  && m < 930)  return Session.LdnMain;
            if (m >= 930  && m < 1050) return Session.NyOpen;
            if (m >= 1050 && m < 1260) return Session.NyMain;
            return Session.After;
        }

        public bool IsSessionEnabled(Session s) => s switch
        {
            Session.Asian   => _tA,
            Session.LdnOpen => _tLO,
            Session.LdnMain => _tLM,
            Session.NyOpen  => _tNO,
            Session.NyMain  => _tNM,
            _ => false
        };

        public bool InNyOpenBlackout(DateTime now)
        {
            int m = SastMinute(now);
            return m >= 930 && m < 930 + _nyOpenBlackoutMin;
        }

        public SubTier GetSubTier(DateTime now)
        {
            int m = SastMinute(now);
            if (m >= 660  && m < 810)  return SubTier.A;
            if (m >= 810  && m < 930)  return SubTier.B;
            if (m >= 1050 && m < 1140) return SubTier.A;
            if (m >= 1140 && m < 1260) return SubTier.B;
            return SubTier.None;
        }

        public bool ApproachingNyMainEnd(DateTime now, int minutesBefore)
        {
            int m = SastMinute(now);
            return m >= 1260 - minutesBefore && m < 1260;
        }

        public bool SessionChanged(Session newS)
        {
            bool changed = newS != _lastSession;
            _lastSession = newS;
            return changed;
        }

        public ActiveModel ModelForSession(Session s) => s switch
        {
            Session.LdnMain => ActiveModel.M2MeanRev,
            Session.NyMain  => ActiveModel.M1Trend,
            Session.LdnOpen => ActiveModel.M1Trend,
            _ => ActiveModel.None
        };
    }
}
