// OFCommon.cs
// GODMODE_OFEA — shared enums, records, helpers (cAlgo)
// Source authority: brief §6, §7, §10, §15
// Mirrors mt5/GODMODE_OFEA/Include/OF_Common.mqh

using System;
using cAlgo.API;
using cAlgo.API.Internals;

namespace GodmodeOfea
{
    public enum OpMode { Manual = 0, Auto = 1 }

    public enum Session
    {
        None = 0, Asian = 1, LdnOpen = 2, LdnMain = 3, NyOpen = 4, NyMain = 5, After = 6
    }

    public enum SubTier { None = 0, A = 1, B = 2 }

    public enum ProfileShape { Unknown = 0, D = 1, P = 2, b = 3, Thin = 4 }

    public enum MarketState { Unknown = 0, Balanced = 1, Imbalanced = 2 }

    public enum HtfBias { Neutral = 0, Bull = 1, Bear = 2 }

    public enum ActiveModel { None = 0, M1Trend = 1, M2MeanRev = 2 }

    public enum VpLoc { None = 0, Val = 1, Vah = 2, Poc = 3, Lvn = 4, Hvn = 5 }

    public enum TradeDir { None = 0, Long = 1, Short = -1 }

    // Setup IDs — must match mt5 ENUM_SETUP_ID one-to-one (brief §6)
    public enum SetupId
    {
        None = 0,
        AbsBot = 1, AbsTop = 2, CvdBear = 3, CvdBull = 4,
        ValBnc = 5, VahFade = 6, PocRet = 7, LvnLong = 8, LvnShort = 9, HvnRej = 10,
        StackBull = 11, StackBear = 12, PullStack = 13,
        Spring = 14, Upthrust = 15, Sos = 16, Lpsy = 17,
        LiqSweep = 18, ObReturn = 19, SmtDiv = 20, Breaker = 21, Amd = 22,
        UnfAuc = 23, PoorHL = 24, Iceberg = 25
    }

    public enum Priority { None = 0, P1 = 1, P2 = 2, P3 = 3, P4 = 4, P5 = 5 }

    // Every gate returns this — brief §15 rule 3
    public readonly struct GateResult
    {
        public bool   Passed { get; }
        public string Reason { get; }
        public double Value  { get; }
        public GateResult(bool passed, string reason, double value = 0.0)
        {
            Passed = passed; Reason = reason; Value = value;
        }
        public static GateResult Pass(string r, double v = 0.0) => new GateResult(true, r, v);
        public static GateResult Fail(string r, double v = 0.0) => new GateResult(false, r, v);
    }

    public sealed class SetupCandidate
    {
        public SetupId   SetupId   { get; set; } = SetupId.None;
        public TradeDir  Direction { get; set; } = TradeDir.None;
        public double    Entry     { get; set; }
        public double    Sl        { get; set; }
        public double    Tp        { get; set; }
        public int       Score     { get; set; }      // 0..5  brief §5 GATE 8
        public int       AbsStars  { get; set; }      // 0..5  brief §11.4
        public VpLoc     Loc       { get; set; } = VpLoc.None;
        public Priority  Priority  { get; set; } = Priority.None;
        public string    Reason    { get; set; } = string.Empty;
    }

    public static class OFHelpers
    {
        public static string SessionToStr(Session s) => s switch
        {
            Session.Asian => "ASIAN", Session.LdnOpen => "LDN_OPEN", Session.LdnMain => "LDN_MAIN",
            Session.NyOpen => "NY_OPEN", Session.NyMain => "NY_MAIN", Session.After => "AFTER", _ => "NONE"
        };

        public static string DirToStr(TradeDir d) => d == TradeDir.Long ? "LONG" : (d == TradeDir.Short ? "SHORT" : "NONE");

        public static string LocToStr(VpLoc l) => l switch
        {
            VpLoc.Val => "VAL", VpLoc.Vah => "VAH", VpLoc.Poc => "POC",
            VpLoc.Lvn => "LVN", VpLoc.Hvn => "HVN", _ => "OUT"
        };

        public static string ShapeToStr(ProfileShape s) => s switch
        {
            ProfileShape.D => "D", ProfileShape.P => "P", ProfileShape.b => "b",
            ProfileShape.Thin => "THIN", _ => "UNK"
        };

        public static string BiasToStr(HtfBias b) => b == HtfBias.Bull ? "BULL" : (b == HtfBias.Bear ? "BEAR" : "NEUTRAL");

        public static double PipSize(Symbol s)
        {
            // 3- or 5-digit FX brokers use point*10 as pip
            return (s.Digits == 3 || s.Digits == 5) ? s.PipSize : s.TickSize;
        }

        public static double NormaliseVolume(Symbol s, double raw)
        {
            return s.NormalizeVolumeInUnits(raw, RoundingMode.Down);
        }
    }
}
