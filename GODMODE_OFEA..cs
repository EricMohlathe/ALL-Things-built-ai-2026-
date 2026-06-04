// GODMODE_OFEA — Single-file merged build for cTrader
// All modules inlined: GodmodeOfea + GodmodeOfea.Enhanced + GodmodeOfeaFinal

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

// ============================================================
//  ENHANCED NAMESPACE
// ============================================================
namespace GodmodeOfea.Enhanced
{
    public enum CvdRegime { TrendConfirming, Divergent, InverseDivergent, Neutral }

    public class DeltaEnhanced
    {
        private readonly double[] _d, _p, _c;
        private ulong _idx;
        public double Cvd, CvdSlope, ZScore;
        public bool Climax, DeltaFlipped;
        public CvdRegime Regime;

        public DeltaEnhanced(int lookback = 20) { _d = new double[lookback]; _p = new double[lookback]; _c = new double[lookback]; }

        public void OnBar(double barDelta, double closePrice, double climaxThr = 2.0, int flipBars = 3)
        {
            Cvd += barDelta;
            ulong L = (ulong)_d.Length;
            _d[(int)(_idx % L)] = barDelta;
            _p[(int)(_idx % L)] = closePrice;
            _c[(int)(_idx % L)] = Cvd;
            _idx++;
            int n = (int)Math.Min(_idx, L);
            double sum = 0, sum2 = 0;
            for (int i = 0; i < n; i++) { sum += _d[i]; sum2 += _d[i] * _d[i]; }
            var mu = n > 0 ? sum / n : 0;
            var v  = n > 0 ? (sum2 / n) - (mu * mu) : 0;
            if (v < 0 || double.IsNaN(v) || double.IsInfinity(v)) v = 0;
            var sd = v > 0 ? Math.Sqrt(v) : 0;
            ZScore = sd > 0 ? (barDelta - mu) / sd : 0;
            Climax = Math.Abs(ZScore) >= climaxThr;
            if (n >= 2)
            {
                int iNow  = (int)((_idx - 1)        % L);
                int iPast = (int)((_idx - (ulong)n) % L);
                double rawSlope = (_c[iNow] - _c[iPast]) / (double)n;
                double sumAbs = 0;
                for (int j = 0; j < n; j++) sumAbs += Math.Abs(_d[j]);
                double meanAbsBd = n > 0 ? sumAbs / n : 0;
                CvdSlope = meanAbsBd > 0 ? rawSlope / meanAbsBd : 0;
            }
            DeltaFlipped = false;
            if (n > flipBars)
            {
                int signNow = barDelta > 0 ? 1 : (barDelta < 0 ? -1 : 0);
                for (int k = 1; k <= flipBars && k < n; k++)
                {
                    double d = _d[(int)((_idx - 1 - (ulong)k) % L)];
                    int s = d > 0 ? 1 : (d < 0 ? -1 : 0);
                    if (s != 0 && signNow != 0 && s == -signNow) { DeltaFlipped = true; break; }
                }
            }
            ClassifyRegime(n);
        }

        private void ClassifyRegime(int n)
        {
            ulong L = (ulong)_d.Length;
            if ((ulong)n < L) { Regime = CvdRegime.Neutral; return; }
            int iNow  = (int)((_idx - 1)        % L);
            int iPast = (int)((_idx - (ulong)n) % L);
            double dPrice = _p[iNow] - _p[iPast];
            double dCVD   = _c[iNow] - _c[iPast];
            bool same = (dPrice > 0 && dCVD > 0) || (dPrice < 0 && dCVD < 0);
            bool opp  = (dPrice > 0 && dCVD < 0) || (dPrice < 0 && dCVD > 0);
            bool flat = Math.Abs(dPrice) < 0.0001 * Math.Abs(_p[iPast]);
            bool strong = Math.Abs(dCVD) > Math.Abs(Cvd) * 0.1;
            if (same) Regime = CvdRegime.TrendConfirming;
            else if (opp) Regime = CvdRegime.Divergent;
            else if (flat && strong) Regime = CvdRegime.InverseDivergent;
            else Regime = CvdRegime.Neutral;
        }
    }

    public class VWAP
    {
        public DateTime Anchor;
        public double CumPV, CumV, CumPV2, Value, Sd;
        public void Reset(DateTime t) { Anchor = t; CumPV = 0; CumV = 0; CumPV2 = 0; Value = 0; Sd = 0; }
        public bool IsNewSession(DateTime t) => t.Date != Anchor.Date;
        public void Update(double typPrice, double vol, DateTime t)
        {
            if (Anchor == default || IsNewSession(t)) Reset(t);
            if (vol <= 0) return;
            CumPV += typPrice * vol; CumPV2 += typPrice * typPrice * vol; CumV += vol;
            if (CumV > 0)
            {
                Value = CumPV / CumV;
                var v = (CumPV2 / CumV) - (Value * Value);
                if (v < 0 || double.IsNaN(v) || double.IsInfinity(v)) v = 0;
                Sd = v > 0 ? Math.Sqrt(v) : 0;
            }
        }
        public double Upper(double k = 1.0) => Value + k * Sd;
        public double Lower(double k = 1.0) => Value - k * Sd;
        public double ZScore(double price) => (price > 0 && Sd > 0) ? (price - Value) / Sd : 0;
    }

    public enum OfRegime { InitBuy, InitSell, Absorption, Rotation }

    public class RegimeHMM
    {
        public OfRegime Current = OfRegime.Rotation;
        public OfRegime Prior   = OfRegime.Rotation;
        public int BarsInState;
        public bool JustTransitioned;
        public void Update(double cvdSlope, int footImb, double profileSkew, double volZ,
                           double cvdSlopeThr = 0.5, int footImbThr = 3, double volZThr = 1.5)
        {
            var next = Current;
            bool aggressiveBuy  = cvdSlope >  cvdSlopeThr && footImb >= footImbThr;
            bool aggressiveSell = cvdSlope < -cvdSlopeThr && footImb >= footImbThr;
            bool absorbing      = Math.Abs(cvdSlope) > cvdSlopeThr && volZ > volZThr && Math.Abs(profileSkew) < 0.3;
            bool balanced       = Math.Abs(cvdSlope) < cvdSlopeThr * 0.5;
            if (absorbing) next = OfRegime.Absorption;
            else if (aggressiveBuy) next = OfRegime.InitBuy;
            else if (aggressiveSell) next = OfRegime.InitSell;
            else if (balanced) next = OfRegime.Rotation;
            JustTransitioned = next != Current;
            if (JustTransitioned) { Prior = Current; Current = next; BarsInState = 0; }
            else BarsInState++;
        }
        public bool ExhaustionLongFromAbsorption  => Current == OfRegime.Absorption && Prior == OfRegime.InitSell && JustTransitioned;
        public bool ExhaustionShortFromAbsorption => Current == OfRegime.Absorption && Prior == OfRegime.InitBuy  && JustTransitioned;
    }

    public static class KellySizer
    {
        public static double FullKelly(double p, double b)
        {
            if (b <= 0 || p < 0 || p > 1.0) return 0;
            return (p * (b + 1.0) - 1.0) / b;
        }
        public static double FractionalKelly(double p, double b, double kappa = 0.25)
        {
            if (kappa <= 0) return 0;
            return Math.Max(0, FullKelly(p, b)) * Math.Max(0, Math.Min(kappa, 1.0));
        }
        public static double RiskPctFromKelly(double p, double b, double kappa = 0.25)
            => Math.Min(2.0, FractionalKelly(p, b, kappa) * 100.0);
    }

    public class BidAskMonitor
    {
        private readonly double[] _buf;
        private ulong _idx;
        public double Bid, Ask, Spread, SpreadPts, MeanSpreadPts, SdSpreadPts, ZSpread;
        public BidAskMonitor(int window = 120) { _buf = new double[window]; }
        public void Update(Symbol symbol)
        {
            var bid = symbol.Bid; var ask = symbol.Ask;
            Bid = bid; Ask = ask; Spread = ask - bid; SpreadPts = Spread / symbol.TickSize;
            ulong L = (ulong)_buf.Length;
            _buf[(int)(_idx % L)] = SpreadPts; _idx++;
            int n = (int)Math.Min(_idx, L);
            double sum = 0, sum2 = 0;
            for (int i = 0; i < n; i++) { sum += _buf[i]; sum2 += _buf[i] * _buf[i]; }
            MeanSpreadPts = n > 0 ? sum / n : 0;
            var v = n > 0 ? (sum2 / n) - (MeanSpreadPts * MeanSpreadPts) : 0;
            if (v < 0 || double.IsNaN(v) || double.IsInfinity(v)) v = 0;
            SdSpreadPts = v > 0 ? Math.Sqrt(v) : 0;
            ZSpread = SdSpreadPts > 0 ? (SpreadPts - MeanSpreadPts) / SdSpreadPts : 0;
        }
        public bool SpreadAcceptable(double maxZ = 2.0) => ZSpread <= maxZ;
    }

    public enum PaStructure { None, BosUp, BosDown, ChochUp, ChochDown }

    public class PriceAction
    {
        public double LastSwingHigh, LastSwingLow;
        public PaStructure Structure;
        public bool EqualHighsCluster, EqualLowsCluster;
        public bool FvgUp, FvgDown;
        public double FvgUpTop, FvgUpBot, FvgDownTop, FvgDownBot;
        public void Update(double[] highs, double[] lows, double[] closes,
                           int lookbackSwing = 20, double tolEqualAtr = 0.10, double atr = 0)
        {
            if (highs.Length < lookbackSwing + 3) return;
            double curH = -1, curL = 1e18; int iH = -1, iL = -1;
            for (int i = 1; i < lookbackSwing - 1; i++)
            {
                if (highs[i] > highs[i - 1] && highs[i] > highs[i + 1] && highs[i] > curH) { curH = highs[i]; iH = i; }
                if (lows[i]  < lows[i - 1]  && lows[i]  < lows[i + 1]  && lows[i]  < curL) { curL = lows[i];  iL = i; }
            }
            if (iH >= 0) LastSwingHigh = curH;
            if (iL >= 0) LastSwingLow  = curL;
            Structure = PaStructure.None;
            double c = closes[0];
            if (iH >= 0 && c > LastSwingHigh) Structure = PaStructure.BosUp;
            else if (iL >= 0 && c < LastSwingLow) Structure = PaStructure.BosDown;
            double tol = tolEqualAtr * (atr > 0 ? atr : 0.0001 * c);
            int eqH = 0, eqL = 0;
            for (int i = 1; i < lookbackSwing && i < highs.Length; i++)
            {
                if (iH >= 0 && Math.Abs(highs[i] - LastSwingHigh) <= tol) eqH++;
                if (iL >= 0 && Math.Abs(lows[i]  - LastSwingLow)  <= tol) eqL++;
            }
            EqualHighsCluster = eqH >= 2; EqualLowsCluster = eqL >= 2;
            FvgUp = false; FvgDown = false;
            if (highs.Length >= 3)
            {
                if (lows[0]  > highs[2]) { FvgUp   = true; FvgUpBot   = highs[2]; FvgUpTop   = lows[0]; }
                if (highs[0] < lows[2])  { FvgDown  = true; FvgDownBot = highs[0]; FvgDownTop = lows[2]; }
            }
        }
    }

    public class ProbabilityWeights
    {
        public double F1 = 12, F2 = 8, F3 = 12, F4 = 10, F5 = 8;
        public double F6 = 8, F7 = 12, F8 = 6, F9 = 8, F10 = 6, F11 = 4, F12 = 6;
    }

    public class ProbabilityScore
    {
        public ProbabilityWeights W = new ProbabilityWeights();
        public double Total;
        private static double C(double x) => x < 0 ? 0 : (x > 1 ? 1 : x);
        public double Compute(double g1, double g2, double g3, double g4, double g5,
                              double g6, double g7, double g8, double g9, double g10, double g11, double g12)
        {
            Total = W.F1*C(g1)+W.F2*C(g2)+W.F3*C(g3)+W.F4*C(g4)+W.F5*C(g5)
                  + W.F6*C(g6)+W.F7*C(g7)+W.F8*C(g8)+W.F9*C(g9)+W.F10*C(g10)+W.F11*C(g11)+W.F12*C(g12);
            return Total;
        }
        public string Grade()
        {
            if (Total >= 85) return "A+"; if (Total >= 75) return "A";
            if (Total >= 65) return "B";  if (Total >= 50) return "C";
            if (Total >= 35) return "D";  return "F";
        }
    }

    public class SweepResult
    {
        public bool Fired; public int Direction, PreconditionsPassed;
        public double SweepExtreme, AbsorptionScore;
    }

    public class SweepDetector
    {
        public SweepResult Last = new SweepResult();
        public void Evaluate(bool eq, bool htf, bool kz, bool mom, bool abs_, bool flip,
                             int dir, double extreme, double absScore = 0)
        {
            int n = 0;
            if (eq) n++; if (htf) n++; if (kz) n++; if (mom) n++; if (abs_) n++; if (flip) n++;
            Last = new SweepResult { PreconditionsPassed = n, Fired = n == 6, Direction = dir, SweepExtreme = extreme, AbsorptionScore = absScore };
        }
        public double ExpectedR() { switch (Last.PreconditionsPassed) { case 6: return 1.18; case 5: return 0.94; case 4: return 0.55; case 3: return 0.31; default: return 0.08; } }
        public double EmpiricalWinRate() { switch (Last.PreconditionsPassed) { case 6: return 0.67; case 5: return 0.63; case 4: return 0.58; case 3: return 0.54; default: return 0.49; } }
    }

    public class PoolResilience
    {
        public double Density, Depth, Resilience; public bool Exploitable;
        public void Compute(double consumed, double refilled, double levelSize, int orderCount, int tickRange)
        {
            Depth = levelSize; Density = tickRange > 0 ? (double)orderCount / tickRange : 0;
            Resilience = consumed > 0 ? refilled / consumed : 0;
            Exploitable = Density > 0.5 && Depth > 0 && Resilience < 0.30;
        }
    }
}

// ============================================================
//  BASE NAMESPACE
// ============================================================
namespace GodmodeOfea
{
    public enum OpMode { Manual = 0, Auto = 1 }
    public enum Session { None = 0, Asian = 1, LdnOpen = 2, LdnMain = 3, NyOpen = 4, NyMain = 5, After = 6 }
    public enum SubTier { None = 0, A = 1, B = 2 }
    public enum ProfileShape { Unknown = 0, D = 1, P = 2, b = 3, Thin = 4 }
    public enum MarketState { Unknown = 0, Balanced = 1, Imbalanced = 2 }
    public enum HtfBias { Neutral = 0, Bull = 1, Bear = 2 }
    public enum ActiveModel { None = 0, M1Trend = 1, M2MeanRev = 2 }
    public enum VpLoc { None = 0, Val = 1, Vah = 2, Poc = 3, Lvn = 4, Hvn = 5 }
    public enum TradeDir { None = 0, Long = 1, Short = -1 }
    public enum SetupId
    {
        None = 0, AbsBot = 1, AbsTop = 2, CvdBear = 3, CvdBull = 4,
        ValBnc = 5, VahFade = 6, PocRet = 7, LvnLong = 8, LvnShort = 9, HvnRej = 10,
        StackBull = 11, StackBear = 12, PullStack = 13, Spring = 14, Upthrust = 15,
        Sos = 16, Lpsy = 17, LiqSweep = 18, ObReturn = 19, SmtDiv = 20,
        Breaker = 21, Amd = 22, UnfAuc = 23, PoorHL = 24, Iceberg = 25
    }
    public enum Priority { None = 0, P1 = 1, P2 = 2, P3 = 3, P4 = 4, P5 = 5 }

    public readonly struct GateResult
    {
        public bool   Passed { get; }
        public string Reason { get; }
        public double Value  { get; }
        public GateResult(bool passed, string reason, double value = 0.0) { Passed = passed; Reason = reason; Value = value; }
        public static GateResult Pass(string r, double v = 0.0) => new GateResult(true, r, v);
        public static GateResult Fail(string r, double v = 0.0) => new GateResult(false, r, v);
    }

    public sealed class SetupCandidate
    {
        public SetupId  SetupId   { get; set; } = SetupId.None;
        public TradeDir Direction { get; set; } = TradeDir.None;
        public double   Entry     { get; set; }
        public double   Sl        { get; set; }
        public double   Tp        { get; set; }
        public int      Score     { get; set; }
        public int      AbsStars  { get; set; }
        public VpLoc    Loc       { get; set; } = VpLoc.None;
        public Priority Priority  { get; set; } = Priority.None;
        public string   Reason    { get; set; } = string.Empty;
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
            VpLoc.Val => "VAL", VpLoc.Vah => "VAH", VpLoc.Poc => "POC", VpLoc.Lvn => "LVN", VpLoc.Hvn => "HVN", _ => "OUT"
        };
        public static string ShapeToStr(ProfileShape s) => s switch
        {
            ProfileShape.D => "D", ProfileShape.P => "P", ProfileShape.b => "b", ProfileShape.Thin => "THIN", _ => "UNK"
        };
        public static string BiasToStr(HtfBias b) => b == HtfBias.Bull ? "BULL" : (b == HtfBias.Bear ? "BEAR" : "NEUTRAL");
        public static double PipSize(Symbol s) => (s.Digits == 3 || s.Digits == 5) ? s.PipSize : s.TickSize;
        public static double NormaliseVolume(Symbol s, double raw) => s.NormalizeVolumeInUnits(raw, RoundingMode.Down);
    }

    public sealed class DeltaEngine
    {
        private readonly Symbol _symbol;
        private readonly int _lookback;
        private readonly Bars _bars;
        private double _tickBuy, _tickSell, _prevMid;
        private readonly List<double> _barDelta, _volume, _cvd;

        public DeltaEngine(Symbol symbol, Bars bars, int lookback)
        {
            _symbol = symbol; _bars = bars; _lookback = Math.Max(lookback, 30);
            _barDelta = new List<double>(_lookback); _volume = new List<double>(_lookback); _cvd = new List<double>(_lookback);
            for (int i = 0; i < _lookback; i++) { _barDelta.Add(0); _volume.Add(0); _cvd.Add(0); }
            _symbol.Tick += OnTick;
        }
        public void Detach() { _symbol.Tick -= OnTick; }
        private void OnTick(SymbolTickEventArgs args)
        {
            // Use mid-price direction: Ask>Bid is always true (spread), so compare to previous mid
            double mid = (args.Ask + args.Bid) * 0.5;
            if (_prevMid > 0)
            {
                if (mid > _prevMid) _tickBuy += 1.0;
                else if (mid < _prevMid) _tickSell += 1.0;
            }
            _prevMid = mid;
        }
        public void OnBarClose()
        {
            double bd = _tickBuy - _tickSell;
            double tv = _tickBuy + _tickSell;
            if (tv <= 0) tv = _bars.TickVolumes.Last(1);
            for (int i = _lookback - 1; i > 0; --i) { _barDelta[i] = _barDelta[i-1]; _volume[i] = _volume[i-1]; _cvd[i] = _cvd[i-1]; }
            _barDelta[0] = bd; _volume[0] = tv; _cvd[0] = _cvd[1] + bd;
            _tickBuy = 0; _tickSell = 0;
        }
        public double Cvd      => _cvd[0];
        public double BarDelta => _barDelta[0];
        public double Volume(int i) => (i >= 0 && i < _lookback) ? _volume[i] : 0;
        public double Delta(int i)  => (i >= 0 && i < _lookback) ? _barDelta[i] : 0;
        public double VolumeZ()
        {
            double mean = 0; for (int i = 0; i < _lookback; i++) mean += _volume[i]; mean /= _lookback;
            double sd = 0; for (int i = 0; i < _lookback; i++) sd += (_volume[i]-mean)*(_volume[i]-mean);
            sd = Math.Sqrt(sd / _lookback); return sd < 1e-9 ? 0 : (_volume[0] - mean) / sd;
        }
        public double DeltaZ()
        {
            double mean = 0; for (int i = 0; i < _lookback; i++) mean += _barDelta[i]; mean /= _lookback;
            double sd = 0; for (int i = 0; i < _lookback; i++) sd += (_barDelta[i]-mean)*(_barDelta[i]-mean);
            sd = Math.Sqrt(sd / _lookback); return sd < 1e-9 ? 0 : (_barDelta[0] - mean) / sd;
        }
        public double CvdSlope5() { int n = Math.Min(5, _lookback - 1); return _cvd[0] - _cvd[n]; }
        public bool BullishDivergence()
        {
            int n = Math.Min(20, _lookback - 1);
            double pLow = _bars.LowPrices.Last(1); for (int i = 2; i <= n; i++) pLow = Math.Min(pLow, _bars.LowPrices.Last(i));
            double cvdMin = _cvd[1]; for (int i = 2; i <= n; i++) if (_cvd[i] < cvdMin) cvdMin = _cvd[i];
            return _bars.LowPrices.Last(1) <= pLow + _symbol.TickSize && _cvd[1] > cvdMin + 1e-9;
        }
        public bool BearishDivergence()
        {
            int n = Math.Min(20, _lookback - 1);
            double pHigh = _bars.HighPrices.Last(1); for (int i = 2; i <= n; i++) pHigh = Math.Max(pHigh, _bars.HighPrices.Last(i));
            double cvdMax = _cvd[1]; for (int i = 2; i <= n; i++) if (_cvd[i] > cvdMax) cvdMax = _cvd[i];
            return _bars.HighPrices.Last(1) >= pHigh - _symbol.TickSize && _cvd[1] < cvdMax - 1e-9;
        }
    }

    public sealed class VolumeProfile
    {
        private readonly Symbol _symbol; private readonly Bars _bars;
        private readonly int _bins, _length; private readonly double _va, _lvnRatio, _hvnRatio;
        private double[] _binVol; private bool[] _lvnFlag, _hvnFlag;
        private double _lo, _hi, _binSize;
        public double Poc { get; private set; } public double Vah { get; private set; } public double Val { get; private set; }
        public ProfileShape Shape { get; private set; } = ProfileShape.Unknown;
        public MarketState State => Shape == ProfileShape.D ? MarketState.Balanced : (Shape == ProfileShape.Unknown ? MarketState.Unknown : MarketState.Imbalanced);
        public VolumeProfile(Symbol s, Bars bars, int bins, int length, double va, double lvnR, double hvnR)
        {
            _symbol = s; _bars = bars; _bins = bins; _length = length; _va = va; _lvnRatio = lvnR; _hvnRatio = hvnR;
            _binVol = new double[bins]; _lvnFlag = new bool[bins]; _hvnFlag = new bool[bins];
        }
        public bool Recompute()
        {
            Array.Clear(_binVol, 0, _bins); Array.Clear(_lvnFlag, 0, _bins); Array.Clear(_hvnFlag, 0, _bins);
            if (_bars.Count < _length + 2) return false;
            double hi = _bars.HighPrices.Last(1), lo = _bars.LowPrices.Last(1);
            for (int i = 1; i <= _length; i++) { hi = Math.Max(hi, _bars.HighPrices.Last(i)); lo = Math.Min(lo, _bars.LowPrices.Last(i)); }
            _lo = lo; _hi = hi; _binSize = (hi - lo) / _bins;
            if (_binSize <= 0) return false;
            for (int i = 1; i <= _length; i++)
            {
                double c = _bars.ClosePrices.Last(i);
                int b = (int)Math.Floor((c - lo) / _binSize);
                if (b < 0) b = 0; if (b >= _bins) b = _bins - 1;
                _binVol[b] += _bars.TickVolumes.Last(i);
            }
            int pocBin = 0; for (int i = 1; i < _bins; i++) if (_binVol[i] > _binVol[pocBin]) pocBin = i;
            Poc = lo + (pocBin + 0.5) * _binSize;
            double total = 0; for (int i = 0; i < _bins; i++) total += _binVol[i];
            double target = total * _va, acc = _binVol[pocBin]; int hiBin = pocBin, loBin = pocBin;
            while (acc < target && (hiBin < _bins - 1 || loBin > 0))
            {
                double up = hiBin + 1 < _bins ? _binVol[hiBin + 1] : -1;
                double dn = loBin - 1 >= 0   ? _binVol[loBin - 1] : -1;
                if (up >= dn && up >= 0) { hiBin++; acc += up; } else if (dn >= 0) { loBin--; acc += dn; } else break;
            }
            Vah = lo + (hiBin + 1) * _binSize; Val = lo + loBin * _binSize;
            double pocVol = _binVol[pocBin];
            for (int i = 0; i < _bins; i++) { _lvnFlag[i] = _binVol[i] < pocVol * _lvnRatio; _hvnFlag[i] = _binVol[i] > pocVol * _hvnRatio; }
            ClassifyShape(pocBin, pocVol); return true;
        }
        private void ClassifyShape(int pocBin, double pocVol)
        {
            int lowBin = -1, highBin = -1;
            for (int i = 0; i < _bins; i++) if (_binVol[i] > 0) { if (lowBin < 0) lowBin = i; highBin = i; }
            if (lowBin < 0) { Shape = ProfileShape.Unknown; return; }
            int midBin = (lowBin + highBin) / 2;
            double upper = 0, lower = 0;
            for (int i = midBin; i <= highBin; i++) upper += _binVol[i];
            for (int i = lowBin;  i <  midBin;  i++) lower += _binVol[i];
            double tot = upper + lower, skew = tot > 0 ? (upper - lower) / tot : 0;
            double sum = 0; int nz = 0;
            for (int i = 0; i < _bins; i++) if (_binVol[i] > 0) { sum += _binVol[i]; nz++; }
            double peak = (nz > 0 && sum > 0) ? pocVol / (sum / nz) : 1.0;
            if (Math.Abs(skew) < 0.10 && peak > 2.0) Shape = ProfileShape.D;
            else if (skew > 0.20)  Shape = ProfileShape.P;
            else if (skew < -0.20) Shape = ProfileShape.b;
            else if (peak < 1.3)   Shape = ProfileShape.Thin;
            else                   Shape = ProfileShape.D;
        }
        public VpLoc LocationAt(double price, double tolPips)
        {
            double tol = tolPips * OFHelpers.PipSize(_symbol);
            if (Math.Abs(price - Poc) < tol) return VpLoc.Poc;
            if (Math.Abs(price - Vah) < tol) return VpLoc.Vah;
            if (Math.Abs(price - Val) < tol) return VpLoc.Val;
            int bin = (int)Math.Floor((price - _lo) / _binSize);
            if (bin >= 0 && bin < _bins) { if (_lvnFlag[bin]) return VpLoc.Lvn; if (_hvnFlag[bin]) return VpLoc.Hvn; }
            return VpLoc.None;
        }
    }

    public sealed class FootprintAnalyzer
    {
        private readonly Bars _bars; private readonly double _volZThr; private readonly int _minStackedRows;
        public FootprintAnalyzer(Bars bars, double volZ, double deltaZ, int stackedRows, double imbalanceRatio)
        { _bars = bars; _volZThr = volZ; _minStackedRows = stackedRows; }
        public bool BullishAbsorption(DeltaEngine de) { return de.BarDelta < 0 && de.VolumeZ() >= _volZThr && _bars.ClosePrices.Last(1) >= _bars.OpenPrices.Last(1); }
        public bool BearishAbsorption(DeltaEngine de) { return de.BarDelta > 0 && de.VolumeZ() >= _volZThr && _bars.ClosePrices.Last(1) <= _bars.OpenPrices.Last(1); }
        public bool StackedBullImbalance(DeltaEngine de) { for (int i = 0; i < _minStackedRows; i++) if (de.Delta(i) <= 0) return false; return true; }
        public bool StackedBearImbalance(DeltaEngine de) { for (int i = 0; i < _minStackedRows; i++) if (de.Delta(i) >= 0) return false; return true; }
        public bool UnfinishedAuction(IndicatorDataSeries atr14)
        {
            double atr = atr14.Last(1); if (atr <= 0) return false;
            bool poorHigh = _bars.HighPrices.Last(1) > _bars.HighPrices.Last(2) && (_bars.ClosePrices.Last(1) - _bars.ClosePrices.Last(2)) < 0.25 * atr;
            bool poorLow  = _bars.LowPrices.Last(1)  < _bars.LowPrices.Last(2)  && (_bars.ClosePrices.Last(2) - _bars.ClosePrices.Last(1)) < 0.25 * atr;
            return poorHigh || poorLow;
        }
    }

    public static class AbsorptionStars
    {
        public static int Compute(Bars bars, DeltaEngine de, TradeDir dir)
        {
            double volZ = de.VolumeZ(), dz = de.DeltaZ();
            if (volZ < 1.0) return 0;
            int stars = 1; if (volZ >= 2.0) stars++; if (volZ >= 3.0) stars++; if (Math.Abs(dz) >= 2.0) stars++;
            double o = bars.OpenPrices.Last(1), c = bars.ClosePrices.Last(1), h = bars.HighPrices.Last(1), l = bars.LowPrices.Last(1);
            double range = Math.Max(h - l, 1e-9), wickPct = 0;
            if (dir == TradeDir.Long)  wickPct = (Math.Min(o, c) - l) / range;
            if (dir == TradeDir.Short) wickPct = (h - Math.Max(o, c)) / range;
            if (wickPct >= 0.4) stars++;
            return Math.Min(stars, 5);
        }
    }

    public sealed class SessionGate
    {
        private readonly int _offsetHours, _nyOpenBlackoutMin;
        private readonly bool _tA, _tLO, _tLM, _tNO, _tNM;
        private Session _lastSession = Session.None;
        public SessionGate(int offset, int nyBlackout, bool asian, bool ldnO, bool ldnM, bool nyO, bool nyM)
        { _offsetHours = offset; _nyOpenBlackoutMin = nyBlackout; _tA = asian; _tLO = ldnO; _tLM = ldnM; _tNO = nyO; _tNM = nyM; }
        public int SastMinute(DateTime t) { int h = t.Hour + _offsetHours; while (h >= 24) h -= 24; while (h < 0) h += 24; return h * 60 + t.Minute; }
        public Session Classify(DateTime t, out int sastMin)
        {
            int m = SastMinute(t); sastMin = m;
            if (m >= 120  && m < 600)  return Session.Asian;
            if (m >= 600  && m < 660)  return Session.LdnOpen;
            if (m >= 660  && m < 930)  return Session.LdnMain;
            if (m >= 930  && m < 1050) return Session.NyOpen;
            if (m >= 1050 && m < 1260) return Session.NyMain;
            return Session.After;
        }
        public bool IsSessionEnabled(Session s) => s switch { Session.Asian => _tA, Session.LdnOpen => _tLO, Session.LdnMain => _tLM, Session.NyOpen => _tNO, Session.NyMain => _tNM, _ => false };
        public bool InNyOpenBlackout(DateTime now) { int m = SastMinute(now); return m >= 930 && m < 930 + _nyOpenBlackoutMin; }
        public bool ApproachingNyMainEnd(DateTime now, int minBefore) { int m = SastMinute(now); return m >= 1260 - minBefore && m < 1260; }
        public bool SessionChanged(Session newS) { bool changed = newS != _lastSession; _lastSession = newS; return changed; }
        public ActiveModel ModelForSession(Session s) => s switch { Session.LdnMain => ActiveModel.M2MeanRev, Session.NyMain => ActiveModel.M1Trend, Session.LdnOpen => ActiveModel.M1Trend, _ => ActiveModel.None };
    }

    public sealed class HtfAlignment
    {
        private readonly Bars _h4, _d1;
        private readonly ExponentialMovingAverage _emaH4, _emaD1;
        public HtfAlignment(Robot robot, Symbol s)
        {
            _h4 = robot.MarketData.GetBars(TimeFrame.Hour4, s.Name);
            _d1 = robot.MarketData.GetBars(TimeFrame.Daily, s.Name);
            _emaH4 = robot.Indicators.ExponentialMovingAverage(_h4.ClosePrices, 20);
            _emaD1 = robot.Indicators.ExponentialMovingAverage(_d1.ClosePrices, 50);
        }
        public HtfBias H4Bias() { double e = _emaH4.Result.Last(0), c = _h4.ClosePrices.Last(0); return c > e*1.0001 ? HtfBias.Bull : c < e*0.9999 ? HtfBias.Bear : HtfBias.Neutral; }
        public HtfBias D1Bias() { double e = _emaD1.Result.Last(0), c = _d1.ClosePrices.Last(0); return c > e*1.0001 ? HtfBias.Bull : c < e*0.9999 ? HtfBias.Bear : HtfBias.Neutral; }
        public bool IsAligned(TradeDir dir) { var h4 = H4Bias(); var d1 = D1Bias(); if (h4 != d1) return false; return dir == TradeDir.Long ? h4 == HtfBias.Bull : dir == TradeDir.Short && h4 == HtfBias.Bear; }
        public HtfBias Combined() { var h4 = H4Bias(); var d1 = D1Bias(); return h4 == d1 ? h4 : HtfBias.Neutral; }
    }

    public sealed class RiskManager
    {
        private readonly Robot _robot; private readonly Symbol _symbol;
        private readonly double _riskPct, _riskHalfPct, _maxDDPct, _maxSpreadMult;
        private readonly int _maxConsecLosses;
        private int _consecLosses; private double _dayStartEquity; private bool _dayHalted;
        private readonly double[] _spreadHist = new double[100]; private int _spreadIdx; private bool _spreadFilled; private double _spreadMedian;
        public RiskManager(Robot robot, Symbol symbol, double riskPct, double riskHalf, double maxDD, int maxConsec, double spreadMult)
        {
            _robot = robot; _symbol = symbol;
            _riskPct = Math.Min(riskPct, 2.0); _riskHalfPct = Math.Min(riskHalf, 2.0);
            _maxDDPct = maxDD; _maxConsecLosses = maxConsec; _maxSpreadMult = spreadMult;
            _dayStartEquity = robot.Account.Equity;
        }
        public void OnDayRollover() { _dayStartEquity = _robot.Account.Equity; _consecLosses = 0; _dayHalted = false; }
        public void SampleSpread()
        {
            _spreadHist[_spreadIdx] = _symbol.Spread; _spreadIdx = (_spreadIdx + 1) % 100;
            if (_spreadIdx == 0) _spreadFilled = true;
            int n = _spreadFilled ? 100 : Math.Max(_spreadIdx, 1);
            var sorted = new double[n]; Array.Copy(_spreadHist, sorted, n); Array.Sort(sorted);
            _spreadMedian = sorted[n / 2];
        }
        public GateResult CheckDailyDrawdown()
        {
            if (_dayStartEquity <= 0) return GateResult.Pass("DD ok");
            double pct = (_robot.Account.Equity - _dayStartEquity) / _dayStartEquity * 100.0;
            return pct <= -_maxDDPct ? GateResult.Fail($"Daily DD {pct:F2}%", pct) : GateResult.Pass($"Daily DD {pct:F2}%", pct);
        }
        public GateResult CheckSpread()
        {
            double cur = _symbol.Spread;
            if (_spreadMedian <= 0) return GateResult.Pass("no median yet", cur);
            return cur > _spreadMedian * _maxSpreadMult ? GateResult.Fail($"Spread blowout {cur:F5}", cur) : GateResult.Pass($"Spread ok {cur:F5}", cur);
        }
        public GateResult CheckConsecLosses() => _consecLosses >= _maxConsecLosses
            ? GateResult.Fail($"Consec losses {_consecLosses}", _consecLosses)
            : GateResult.Pass($"Consec losses {_consecLosses}", _consecLosses);
        public void NotifyTradeClosed(double pnl) { if (pnl < 0) _consecLosses++; else _consecLosses = 0; }
        public void HaltDay() { _dayHalted = true; }
        public bool IsDayHalted => _dayHalted;
        public double DailyDDPct => _dayStartEquity <= 0 ? 0 : (_robot.Account.Equity - _dayStartEquity) / _dayStartEquity * 100.0;
        public double ComputeVolume(double slPriceDistance, bool halfSize)
        {
            double pct = halfSize ? _riskHalfPct : _riskPct;
            double riskAmount = _robot.Account.Equity * pct / 100.0;
            if (slPriceDistance <= 0) return 0;
            double pipDistance = slPriceDistance / OFHelpers.PipSize(_symbol);
            double pipValue = _symbol.PipValue;
            if (pipValue <= 0 || pipDistance <= 0) return 0;
            double rawVolume = riskAmount / (pipDistance * pipValue);
            double normalised = OFHelpers.NormaliseVolume(_symbol, rawVolume);
            // Reject if minimum lot size inflates effective risk above 3× target (blown account protection)
            double effectiveRisk = normalised * pipDistance * pipValue;
            if (normalised > 0 && effectiveRisk > riskAmount * 3.0) return 0;
            return normalised;
        }
    }

    public sealed class TradeManager
    {
        private readonly Robot _robot; private readonly Symbol _symbol; private readonly string _label;
        private readonly bool _partialClose, _useTrail, _exitAtPoc;
        private readonly double _partialPct, _partialAtR, _beAtR, _trailAtrMult;
        private readonly AverageTrueRange _atr;
        public TradeManager(Robot robot, Symbol symbol, string label, bool partial, double partialPct, double partialAtR, double beAtR, bool useTrail, double trailAtr, bool exitPoc, AverageTrueRange atr)
        { _robot = robot; _symbol = symbol; _label = label; _partialClose = partial; _partialPct = partialPct; _partialAtR = partialAtR; _beAtR = beAtR; _useTrail = useTrail; _trailAtrMult = trailAtr; _exitAtPoc = exitPoc; _atr = atr; }
        public Position FindOpenPosition() => _robot.Positions.FirstOrDefault(p => p.SymbolName == _symbol.Name && p.Label == _label);
        public bool OpenPosition(TradeDir dir, double volume, double sl, double tp, string comment)
        {
            if (volume <= 0) return false;
            var type = dir == TradeDir.Long ? TradeType.Buy : TradeType.Sell;
            double slPips = Math.Abs((dir == TradeDir.Long ? _symbol.Ask - sl : sl - _symbol.Bid)) / OFHelpers.PipSize(_symbol);
            double tpPips = Math.Abs((dir == TradeDir.Long ? tp - _symbol.Ask : _symbol.Bid - tp)) / OFHelpers.PipSize(_symbol);
            try { var r = _robot.ExecuteMarketOrder(type, _symbol.Name, volume, _label, slPips, tpPips, comment); return r.IsSuccessful; }
            catch (Exception e) { _robot.Print($"OpenPosition err: {e.Message}"); return false; }
        }
        public void ManagePosition(double poc)
        {
            var p = FindOpenPosition(); if (p == null) return;
            double cur = p.TradeType == TradeType.Buy ? _symbol.Bid : _symbol.Ask;
            double risk = Math.Abs(p.EntryPrice - (p.StopLoss ?? p.EntryPrice)); if (risk <= 0) return;
            double rMult = p.TradeType == TradeType.Buy ? (cur - p.EntryPrice) / risk : (p.EntryPrice - cur) / risk;
            if (_partialClose && rMult >= _partialAtR && !(p.Comment ?? "").Contains("[P]"))
            { double cv = _symbol.NormalizeVolumeInUnits(p.VolumeInUnits * (_partialPct / 100.0), RoundingMode.Down); if (cv > 0) try { _robot.ClosePosition(p, cv); } catch { } }
            if (rMult >= _beAtR)
            { double pip = OFHelpers.PipSize(_symbol); double beSl = p.EntryPrice + (p.TradeType == TradeType.Buy ? pip : -pip); try { _robot.ModifyPosition(p, beSl, p.TakeProfit, ProtectionType.Absolute); } catch { } }
            if (_useTrail && rMult >= _beAtR)
            {
                double atr = _atr.Result.Last(0);
                if (atr > 0)
                {
                    double newSl = p.TradeType == TradeType.Buy ? cur - atr * _trailAtrMult : cur + atr * _trailAtrMult;
                    bool tighter = p.TradeType == TradeType.Buy ? newSl > (p.StopLoss ?? double.NegativeInfinity) : newSl < (p.StopLoss ?? double.PositiveInfinity);
                    if (tighter) try { _robot.ModifyPosition(p, newSl, p.TakeProfit, ProtectionType.Absolute); } catch { }
                }
            }
            if (_exitAtPoc && poc > 0) { bool reached = p.TradeType == TradeType.Buy ? cur >= poc : cur <= poc; if (reached) try { _robot.ClosePosition(p); } catch { } }
        }
        public void CloseAll() { var p = FindOpenPosition(); if (p != null) try { _robot.ClosePosition(p); } catch { } }
    }

    public sealed class NotificationCenter
    {
        private readonly Robot _robot; private readonly bool _sound, _push, _enable;
        private readonly Dictionary<string, DateTime> _lastBarFired = new Dictionary<string, DateTime>();
        private readonly Func<DateTime> _currentBarTime;
        public NotificationCenter(Robot robot, bool enable, bool sound, bool push, bool email, Func<DateTime> currentBarTime)
        { _robot = robot; _enable = enable; _sound = sound; _push = push; _currentBarTime = currentBarTime; }
        private bool ShouldFire(string tag) { DateTime cur = _currentBarTime(); if (_lastBarFired.TryGetValue(tag, out var last) && last == cur) return false; _lastBarFired[tag] = cur; return true; }
        public void Fire(string tag, string msg, SoundType? sound = null, bool sendPush = false)
        {
            if (!_enable || !ShouldFire(tag)) return;
            string text = $"[{_robot.SymbolName}] {tag} — {msg}"; _robot.Print(text);
            try { if (_sound && sound.HasValue) _robot.Notifications.PlaySound(sound.Value); } catch { }
            try { _robot.Chart.DrawStaticText("godmode_toast", text, VerticalAlignment.Bottom, HorizontalAlignment.Left, Color.White); } catch { }
        }
        public void NA_VpLevel(string lvl, double price)       => Fire("N-A", $"VP {lvl} touch @ {price:F5}", SoundType.PositiveNotification);
        public void NC_KillZone(Session s)                     => Fire("N-C", $"Kill zone active: {OFHelpers.SessionToStr(s)}");
        public void ND_HTFAligned(HtfBias b)                   => Fire("N-D", $"HTF aligned: {OFHelpers.BiasToStr(b)}");
        public void NE_CvdConfirm(TradeDir d, double cvd)      => Fire("N-E", $"CVD confirms {OFHelpers.DirToStr(d)} (CVD={cvd:F0})", SoundType.PositiveNotification);
        public void NF_ProfileState(ProfileShape sh, MarketState st) => Fire("N-F", $"Shape {OFHelpers.ShapeToStr(sh)} state {(int)st}");
        public void NG_FootprintSignal(string kind, int stars) => Fire("N-G", $"Footprint {kind} ★{stars}", SoundType.PositiveNotification);
        public void NH_Aggression(double volZ)                 => Fire("N-H", $"Aggression vol Z={volZ:F2}", SoundType.Announcement, true);
        public void NI_AplusReady(SetupCandidate c, double rr) => Fire("N-I", $"A+ READY {OFHelpers.DirToStr(c.Direction)} setup={(int)c.SetupId} score={c.Score} R:R={rr:F1}", SoundType.Announcement, true);
        public void NJ_TradeFired(SetupCandidate c, double lots, string mode) => Fire("N-J", $"{OFHelpers.DirToStr(c.Direction)} {lots:F2} units @ {c.Entry:F5} SL {c.Sl:F5} TP {c.Tp:F5} [{mode}]", SoundType.PositiveNotification, true);
        public void NL_KillSwitch(string reason)               => Fire("N-L_"+reason, $"KILL SWITCH: {reason}", SoundType.NegativeNotification, true);
    }

    public sealed class Dashboard
    {
        private readonly Chart _chart; private readonly Color _ok, _fail, _wait; private DateTime _lastRefresh;
        public Dashboard(Chart chart, Color ok, Color fail, Color wait) { _chart = chart; _ok = ok; _fail = fail; _wait = wait; }
        public bool ShouldRefresh() { var now = DateTime.UtcNow; if ((now - _lastRefresh).TotalMilliseconds < 250) return false; _lastRefresh = now; return true; }
        public void Render(string sym, string mode, MarketState state, Session sess, HtfBias bias, VpLoc loc, TradeDir cvdDir, bool fpReady, double sl, double rr, int score, Priority prio, double cvd, double bd, double volZ, double poc, double vah, double val, double dailyDD, int trades)
        {
            string panel = $"GODMODE OFEA FINAL — {sym} — {mode}\n[1] State ...... {(state==MarketState.Balanced?"BAL":state==MarketState.Imbalanced?"IMB":"UNK")}\n[2] KillZone .. {OFHelpers.SessionToStr(sess)}\n[3] HTF ........ {OFHelpers.BiasToStr(bias)}\n[4] VP Loc ..... {OFHelpers.LocToStr(loc)}\n[5] CVD ........ {(cvdDir==TradeDir.Long?"BULL":cvdDir==TradeDir.Short?"BEAR":"FLAT")}\n[6] Footprint .. {(fpReady?"OK":"WAITING")}\n[7] SL ......... {sl:F5}\n[8] R:R ........ {rr:F1}\nCONF {score}/8 P{(int)prio}\nCVD {cvd:F0} Δ {bd:F0} volZ {volZ:F2}\nPOC {poc:F5} VAH {vah:F5} VAL {val:F5}\nDD {dailyDD:F2}% Trades {trades}";
            _chart.DrawStaticText("godmode_panel", panel, VerticalAlignment.Top, HorizontalAlignment.Right, score >= 6 ? _ok : _wait);
        }
        public void Clear() => _chart.RemoveObject("godmode_panel");
    }

    public sealed class ChartViz
    {
        private readonly Chart _chart; private readonly bool _showVP, _showFp, _showSess, _showTrade;
        public ChartViz(Chart chart, bool vp, bool fp, bool sess, bool trade) { _chart = chart; _showVP = vp; _showFp = fp; _showSess = sess; _showTrade = trade; }
        public void DrawVPLevels(double poc, double vah, double val)
        { if (!_showVP) return; _chart.DrawHorizontalLine("godmode_poc", poc, Color.Magenta, 2, LineStyle.Solid); _chart.DrawHorizontalLine("godmode_vah", vah, Color.DodgerBlue, 1, LineStyle.Dots); _chart.DrawHorizontalLine("godmode_val", val, Color.DodgerBlue, 1, LineStyle.Dots); }
        public void DrawTradeLines(double entry, double sl, double tp, TradeDir dir)
        { if (!_showTrade) return; var c = dir == TradeDir.Long ? Color.Lime : Color.OrangeRed; _chart.DrawHorizontalLine("godmode_te", entry, c, 2, LineStyle.Solid); _chart.DrawHorizontalLine("godmode_tsl", sl, Color.Red, 1, LineStyle.Dots); _chart.DrawHorizontalLine("godmode_ttp", tp, Color.LimeGreen, 1, LineStyle.Dots); }
    }

    public sealed class TradeLogger
    {
        private readonly string _path;
        private const string Header = "timestamp_utc,symbol,event_type,setup_id,score,priority,direction,entry_price,sl,tp,lots,risk_pct,session,market_state,htf_bias,profile_shape,poc,vah,val,cvd_at_entry,bar_delta,vol_z,delta_z,abs_stars,mode";
        public TradeLogger(string path)
        {
            _path = path;
            try { Directory.CreateDirectory(Path.GetDirectoryName(_path) ?? "."); if (!System.IO.File.Exists(_path)) System.IO.File.WriteAllText(_path, Header + Environment.NewLine); }
            catch (IOException) { }
        }
        public void Append(string eventType, SetupCandidate c, string symbol, Session session, MarketState state, HtfBias bias, ProfileShape shape, double poc, double vah, double val, double cvd, double barDelta, double volZ, double deltaZ, string mode, double riskPct, double lots)
        {
            var inv = CultureInfo.InvariantCulture;
            string row = string.Format(inv, "{0:yyyy.MM.dd HH:mm:ss},{1},{2},{3},{4},{5},{6},{7:F5},{8:F5},{9:F5},{10:F2},{11:F2},{12},{13},{14},{15},{16:F5},{17:F5},{18:F5},{19:F0},{20:F0},{21:F2},{22:F2},{23},{24}",
                DateTime.UtcNow, symbol, eventType, (int)c.SetupId, c.Score, (int)c.Priority, OFHelpers.DirToStr(c.Direction), c.Entry, c.Sl, c.Tp, lots, riskPct,
                OFHelpers.SessionToStr(session), (int)state, OFHelpers.BiasToStr(bias), OFHelpers.ShapeToStr(shape), poc, vah, val, cvd, barDelta, volZ, deltaZ, c.AbsStars, mode);
            try { System.IO.File.AppendAllText(_path, row + Environment.NewLine); } catch (IOException) { }
        }
    }

    public sealed class AutoRiskReward
    {
        private readonly Robot _robot; private readonly Chart _chart; private readonly Symbol _symbol;
        private long _trackedPositionId; private string _entryLineKey="", _slRectKey="", _tpRectKey="", _labelKey="";
        public AutoRiskReward(Robot robot, Chart chart, Symbol symbol) { _robot = robot; _chart = chart; _symbol = symbol; }
        public void OnPositionOpened(Position p)
        {
            if (p == null || p.SymbolName != _symbol.Name) return;
            ClearDrawings(); _trackedPositionId = p.Id;
            _entryLineKey = $"godmode_rr_entry_{p.Id}"; _slRectKey = $"godmode_rr_sl_{p.Id}";
            _tpRectKey = $"godmode_rr_tp_{p.Id}"; _labelKey = $"godmode_rr_label_{p.Id}";
            Redraw(p);
        }
        public void OnTick(Position p) { if (p != null && p.Id == _trackedPositionId) Redraw(p); }
        private void Redraw(Position p)
        {
            try
            {
                double entry = p.EntryPrice, sl = p.StopLoss ?? entry, tp = p.TakeProfit ?? entry;
                if (sl == 0 || tp == 0) return;
                DateTime tStart = _chart.Bars[Math.Max(0, _chart.Bars.Count-100)].OpenTime;
                DateTime tEnd   = _chart.Bars[_chart.Bars.Count-1].OpenTime.AddMinutes(120);
                var slRect = _chart.DrawRectangle(_slRectKey, tStart, entry, tEnd, sl, Color.FromArgb(60,220,60,60)); slRect.IsFilled = true;
                var tpRect = _chart.DrawRectangle(_tpRectKey, tStart, entry, tEnd, tp, Color.FromArgb(60,60,220,60)); tpRect.IsFilled = true;
                _chart.DrawTrendLine(_entryLineKey, tStart, entry, tEnd, entry, Color.White);
                double risk=Math.Abs(entry-sl), reward=Math.Abs(tp-entry), rr=risk>0?reward/risk:0;
                double riskPips=risk/OFHelpers.PipSize(_symbol), rewardPips=reward/OFHelpers.PipSize(_symbol);
                _chart.DrawStaticText(_labelKey, $"{p.TradeType.ToString().ToUpperInvariant()} {p.VolumeInUnits:N0}\nRisk:{riskPips:F1}p Reward:{rewardPips:F1}p R:R={rr:F2}", VerticalAlignment.Center, HorizontalAlignment.Right, Color.Yellow);
            }
            catch (Exception e) { _robot.Print($"AutoRR err:{e.Message}"); }
        }
        private void ClearDrawings()
        {
            try { if (!string.IsNullOrEmpty(_entryLineKey)) _chart.RemoveObject(_entryLineKey); if (!string.IsNullOrEmpty(_slRectKey)) _chart.RemoveObject(_slRectKey); if (!string.IsNullOrEmpty(_tpRectKey)) _chart.RemoveObject(_tpRectKey); if (!string.IsNullOrEmpty(_labelKey)) _chart.RemoveObject(_labelKey); } catch { }
        }
    }

    public static class SetupDetectors
    {
        public static SetupCandidate Build(Symbol sym, Bars bars, SetupId id, TradeDir dir, double poc, double targetLevel, VpLoc loc, int absStars, string reason)
        {
            double bid=sym.Bid, ask=sym.Ask, pt=sym.TickSize, aggH=bars.HighPrices.Last(1), aggL=bars.LowPrices.Last(1);
            var c = new SetupCandidate { SetupId=id, Direction=dir, AbsStars=absStars, Loc=loc, Reason=reason };
            if (dir==TradeDir.Long)  { c.Entry=ask; c.Sl=aggL-2*pt; c.Tp=targetLevel>0?targetLevel:poc; }
            else                      { c.Entry=bid; c.Sl=aggH+2*pt; c.Tp=targetLevel>0?targetLevel:poc; }
            return c;
        }
        public static SetupCandidate AbsBot(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, FootprintAnalyzer fp, double locTolPips, int minStars)
        { double c=b.ClosePrices.Last(1); var loc=vp.LocationAt(c,locTolPips); if(loc!=VpLoc.Val&&loc!=VpLoc.Lvn) return null; if(!fp.BullishAbsorption(de)) return null; int st=AbsorptionStars.Compute(b,de,TradeDir.Long); if(st<minStars) return null; return Build(s,b,SetupId.AbsBot,TradeDir.Long,vp.Poc,vp.Poc,loc,st,"AbsBot@VAL/LVN"); }
        public static SetupCandidate AbsTop(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, FootprintAnalyzer fp, double locTolPips, int minStars)
        { double c=b.ClosePrices.Last(1); var loc=vp.LocationAt(c,locTolPips); if(loc!=VpLoc.Vah&&loc!=VpLoc.Hvn) return null; if(!fp.BearishAbsorption(de)) return null; int st=AbsorptionStars.Compute(b,de,TradeDir.Short); if(st<minStars) return null; return Build(s,b,SetupId.AbsTop,TradeDir.Short,vp.Poc,vp.Poc,loc,st,"AbsTop@VAH/HVN"); }
        public static SetupCandidate CvdBear(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double t)
        { if(!de.BearishDivergence()) return null; double c=b.ClosePrices.Last(1); return Build(s,b,SetupId.CvdBear,TradeDir.Short,vp.Poc,vp.Poc,vp.LocationAt(c,t),0,"CVD bear div"); }
        public static SetupCandidate CvdBull(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double t)
        { if(!de.BullishDivergence()) return null; double c=b.ClosePrices.Last(1); return Build(s,b,SetupId.CvdBull,TradeDir.Long,vp.Poc,vp.Poc,vp.LocationAt(c,t),0,"CVD bull div"); }
        public static SetupCandidate ValBounce(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double t)
        { double c=b.ClosePrices.Last(1),o=b.OpenPrices.Last(1); if(vp.LocationAt(c,t)!=VpLoc.Val||c<=o||de.BarDelta<0) return null; return Build(s,b,SetupId.ValBnc,TradeDir.Long,vp.Poc,vp.Poc,VpLoc.Val,0,"VAL bounce"); }
        public static SetupCandidate VahFade(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double t)
        { double c=b.ClosePrices.Last(1),o=b.OpenPrices.Last(1); if(vp.LocationAt(c,t)!=VpLoc.Vah||c>=o||de.BarDelta>0) return null; return Build(s,b,SetupId.VahFade,TradeDir.Short,vp.Poc,vp.Poc,VpLoc.Vah,0,"VAH fade"); }
        public static SetupCandidate PocReturn(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double t)
        { double c=b.ClosePrices.Last(1); if(vp.LocationAt(c,t)!=VpLoc.Poc) return null; var dir=de.BarDelta>=0?TradeDir.Long:TradeDir.Short; return Build(s,b,SetupId.PocRet,dir,vp.Poc,dir==TradeDir.Long?vp.Vah:vp.Val,VpLoc.Poc,0,"POC return"); }
        public static SetupCandidate LvnLong(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double t)
        { double c=b.ClosePrices.Last(1); if(vp.LocationAt(c,t)!=VpLoc.Lvn||de.BarDelta<=0||de.VolumeZ()<1.0) return null; return Build(s,b,SetupId.LvnLong,TradeDir.Long,vp.Poc,vp.Vah,VpLoc.Lvn,0,"LVN accel L"); }
        public static SetupCandidate LvnShort(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double t)
        { double c=b.ClosePrices.Last(1); if(vp.LocationAt(c,t)!=VpLoc.Lvn||de.BarDelta>=0||de.VolumeZ()<1.0) return null; return Build(s,b,SetupId.LvnShort,TradeDir.Short,vp.Poc,vp.Val,VpLoc.Lvn,0,"LVN accel S"); }
        public static SetupCandidate HvnRej(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double t)
        { double c=b.ClosePrices.Last(1); if(vp.LocationAt(c,t)!=VpLoc.Hvn) return null; var dir=de.BarDelta<0?TradeDir.Short:TradeDir.Long; return Build(s,b,SetupId.HvnRej,dir,vp.Poc,vp.Poc,VpLoc.Hvn,0,"HVN rej"); }
        public static SetupCandidate StackBull(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, FootprintAnalyzer fp, double t)
        { if(!fp.StackedBullImbalance(de)||de.CvdSlope5()<=0) return null; double c=b.ClosePrices.Last(1); return Build(s,b,SetupId.StackBull,TradeDir.Long,vp.Poc,vp.Vah,vp.LocationAt(c,t),0,"Stack bull+CVD"); }
        public static SetupCandidate StackBear(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, FootprintAnalyzer fp, double t)
        { if(!fp.StackedBearImbalance(de)||de.CvdSlope5()>=0) return null; double c=b.ClosePrices.Last(1); return Build(s,b,SetupId.StackBear,TradeDir.Short,vp.Poc,vp.Val,vp.LocationAt(c,t),0,"Stack bear+CVD"); }
        public static SetupCandidate PullStack(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double t)
        {
            double zone=0; var dir=TradeDir.None;
            for(int i=1;i<10;i++) { bool bull=de.Delta(i)>0&&de.Delta(i+1)>0&&de.Delta(i+2)>0; bool bear=de.Delta(i)<0&&de.Delta(i+1)<0&&de.Delta(i+2)<0; if(bull){zone=b.LowPrices.Last(i);dir=TradeDir.Long;break;} if(bear){zone=b.HighPrices.Last(i);dir=TradeDir.Short;break;} }
            if(dir==TradeDir.None) return null;
            double c=b.ClosePrices.Last(1),pip=OFHelpers.PipSize(s);
            if(Math.Abs(c-zone)>5*pip) return null;
            return Build(s,b,SetupId.PullStack,dir,vp.Poc,vp.Poc,vp.LocationAt(c,t),0,"Pull stack");
        }
        public static SetupCandidate Spring(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double t)
        { double sL=b.LowPrices.Last(5); for(int i=6;i<30;i++) sL=Math.Min(sL,b.LowPrices.Last(i)); double cL=b.LowPrices.Last(1),cC=b.ClosePrices.Last(1); if(cL>sL||cC<=sL||!de.BullishDivergence()) return null; return Build(s,b,SetupId.Spring,TradeDir.Long,vp.Poc,vp.Poc,vp.LocationAt(cC,t),0,"Spring"); }
        public static SetupCandidate Upthrust(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double t)
        { double sH=b.HighPrices.Last(5); for(int i=6;i<30;i++) sH=Math.Max(sH,b.HighPrices.Last(i)); double cH=b.HighPrices.Last(1),cC=b.ClosePrices.Last(1); if(cH<sH||cC>=sH||!de.BearishDivergence()) return null; return Build(s,b,SetupId.Upthrust,TradeDir.Short,vp.Poc,vp.Poc,vp.LocationAt(cC,t),0,"Upthrust"); }
        public static SetupCandidate Sos(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double t)
        { if(de.CvdSlope5()<=0||de.VolumeZ()<1.0) return null; double c=b.ClosePrices.Last(1); return Build(s,b,SetupId.Sos,TradeDir.Long,vp.Poc,vp.Vah,vp.LocationAt(c,t),0,"SOS"); }
        public static SetupCandidate Lpsy(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double t)
        { if(de.CvdSlope5()>=0||de.VolumeZ()<1.0) return null; double c=b.ClosePrices.Last(1); return Build(s,b,SetupId.Lpsy,TradeDir.Short,vp.Poc,vp.Val,vp.LocationAt(c,t),0,"LPSY"); }
        public static SetupCandidate LiqSweep(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double t)
        { double sH=b.HighPrices.Last(3),sL=b.LowPrices.Last(3); for(int i=4;i<50;i++){sH=Math.Max(sH,b.HighPrices.Last(i));sL=Math.Min(sL,b.LowPrices.Last(i));} double cH=b.HighPrices.Last(1),cL=b.LowPrices.Last(1),cC=b.ClosePrices.Last(1); TradeDir dir=TradeDir.None; if(cH>sH&&cC<sH) dir=TradeDir.Short; if(cL<sL&&cC>sL) dir=TradeDir.Long; if(dir==TradeDir.None) return null; return Build(s,b,SetupId.LiqSweep,dir,vp.Poc,vp.Poc,vp.LocationAt(cC,t),0,"Liq sweep"); }
        public static SetupCandidate ObReturn(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double t)
        { for(int i=5;i<30;i++){double oo=b.OpenPrices.Last(i),oc=b.ClosePrices.Last(i),cur=b.ClosePrices.Last(1),pip=OFHelpers.PipSize(s); if(oc<oo&&Math.Abs(cur-b.HighPrices.Last(i))<5*pip&&de.CvdSlope5()<0) return Build(s,b,SetupId.ObReturn,TradeDir.Short,vp.Poc,vp.Val,vp.LocationAt(cur,t),0,"OB return short"); if(oc>oo&&Math.Abs(cur-b.LowPrices.Last(i))<5*pip&&de.CvdSlope5()>0) return Build(s,b,SetupId.ObReturn,TradeDir.Long,vp.Poc,vp.Vah,vp.LocationAt(cur,t),0,"OB return long");} return null; }
        public static SetupCandidate SmtDiv(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double corrCvdSlope, double t)
        { double mySlope=de.CvdSlope5(); if(mySlope*corrCvdSlope>=0) return null; double c=b.ClosePrices.Last(1); var dir=mySlope>0?TradeDir.Long:TradeDir.Short; return Build(s,b,SetupId.SmtDiv,dir,vp.Poc,vp.Poc,vp.LocationAt(c,t),0,"SMT div"); }
        public static SetupCandidate Breaker(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double t)
        { double sH=b.HighPrices.Last(5),sL=b.LowPrices.Last(5); for(int i=6;i<40;i++){sH=Math.Max(sH,b.HighPrices.Last(i));sL=Math.Min(sL,b.LowPrices.Last(i));} double cC=b.ClosePrices.Last(1),pip=OFHelpers.PipSize(s); if(cC>sH&&Math.Abs(cC-sH)<5*pip&&de.CvdSlope5()>0) return Build(s,b,SetupId.Breaker,TradeDir.Long,vp.Poc,vp.Vah,vp.LocationAt(cC,t),0,"Breaker L"); if(cC<sL&&Math.Abs(cC-sL)<5*pip&&de.CvdSlope5()<0) return Build(s,b,SetupId.Breaker,TradeDir.Short,vp.Poc,vp.Val,vp.LocationAt(cC,t),0,"Breaker S"); return null; }
        public static SetupCandidate Amd(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double t)
        { double rh=b.HighPrices.Last(5),rl=b.LowPrices.Last(5); for(int i=6;i<24;i++){rh=Math.Max(rh,b.HighPrices.Last(i));rl=Math.Min(rl,b.LowPrices.Last(i));} double cC=b.ClosePrices.Last(1); if(cC>rh&&de.DeltaZ()>1.5) return Build(s,b,SetupId.Amd,TradeDir.Long,vp.Poc,vp.Vah,vp.LocationAt(cC,t),0,"AMD long"); if(cC<rl&&de.DeltaZ()<-1.5) return Build(s,b,SetupId.Amd,TradeDir.Short,vp.Poc,vp.Val,vp.LocationAt(cC,t),0,"AMD short"); return null; }
        public static SetupCandidate UnfAuc(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, FootprintAnalyzer fp, AverageTrueRange atrInd, double t)
        { if(!fp.UnfinishedAuction(atrInd.Result)) return null; double cH=b.HighPrices.Last(1),pH=b.HighPrices.Last(2),cC=b.ClosePrices.Last(1); var dir=cH>pH?TradeDir.Short:TradeDir.Long; return Build(s,b,SetupId.UnfAuc,dir,vp.Poc,vp.Poc,vp.LocationAt(cC,t),0,"Unfinished auc"); }
        public static SetupCandidate PoorHL(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double t)
        { double pH=b.HighPrices.Last(2),pL=b.LowPrices.Last(2),cH=b.HighPrices.Last(1),cL=b.LowPrices.Last(1),cC=b.ClosePrices.Last(1),pip=OFHelpers.PipSize(s); if(Math.Abs(cH-pH)<pip&&de.BarDelta<0) return Build(s,b,SetupId.PoorHL,TradeDir.Short,vp.Poc,vp.Poc,vp.LocationAt(cC,t),0,"Poor high"); if(Math.Abs(cL-pL)<pip&&de.BarDelta>0) return Build(s,b,SetupId.PoorHL,TradeDir.Long,vp.Poc,vp.Poc,vp.LocationAt(cC,t),0,"Poor low"); return null; }
        public static SetupCandidate Iceberg(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, AverageTrueRange atrInd, double t)
        { double volZ=de.VolumeZ(),dz=de.DeltaZ(),atr=atrInd.Result.Last(0),range=b.HighPrices.Last(1)-b.LowPrices.Last(1); if(volZ<2.0||Math.Abs(dz)>0.5||atr<=0||range>0.6*atr) return null; double cC=b.ClosePrices.Last(1); var loc=vp.LocationAt(cC,t); if(loc==VpLoc.None) return null; var dir=(loc==VpLoc.Val||loc==VpLoc.Lvn)?TradeDir.Long:TradeDir.Short; return Build(s,b,SetupId.Iceberg,dir,vp.Poc,vp.Poc,loc,0,"Iceberg"); }
    }

    // ============================================================
    //  GOD-LEVEL ENHANCEMENT MODULES
    // ============================================================

    // ICT: Premium/Discount zone classifier
    public static class PremiumDiscountZone
    {
        public enum Zone { Discount, AtEquilibrium, Premium }
        public static Zone Classify(Bars bars, int lookback = 50)
        {
            if (bars.Count < lookback + 2) return Zone.AtEquilibrium;
            double hi = bars.HighPrices.Maximum(lookback);
            double lo = bars.LowPrices.Minimum(lookback);
            double range = hi - lo;
            if (range <= 0) return Zone.AtEquilibrium;
            double eq = lo + range * 0.5;
            double price = bars.ClosePrices.Last(1);
            if (price < eq - range * 0.05) return Zone.Discount;
            if (price > eq + range * 0.05) return Zone.Premium;
            return Zone.AtEquilibrium;
        }
        // True if setup direction aligns with zone (longs from discount, shorts from premium)
        public static bool Aligned(Zone z, TradeDir dir)
            => (dir == TradeDir.Long && z == Zone.Discount) || (dir == TradeDir.Short && z == Zone.Premium);
    }

    // ICT: Optimal Trade Entry — 61.8–79% Fibonacci retracement zone
    public sealed class OTECalculator
    {
        public bool InOTELong(Bars bars, int lookback = 20)
        {
            if (bars.Count < lookback + 2) return false;
            double swingLow = bars.LowPrices.Minimum(lookback);
            double swingHigh = bars.HighPrices.Maximum(lookback);
            double range = swingHigh - swingLow;
            if (range <= 0) return false;
            double price = bars.ClosePrices.Last(1);
            double ote61 = swingHigh - range * 0.618;
            double ote79 = swingHigh - range * 0.79;
            return price >= ote79 && price <= ote61;
        }
        public bool InOTEShort(Bars bars, int lookback = 20)
        {
            if (bars.Count < lookback + 2) return false;
            double swingLow = bars.LowPrices.Minimum(lookback);
            double swingHigh = bars.HighPrices.Maximum(lookback);
            double range = swingHigh - swingLow;
            if (range <= 0) return false;
            double price = bars.ClosePrices.Last(1);
            double ote61 = swingLow + range * 0.618;
            double ote79 = swingLow + range * 0.79;
            return price >= ote61 && price <= ote79;
        }
        public bool InOTE(Bars bars, TradeDir dir, int lookback = 20)
            => dir == TradeDir.Long ? InOTELong(bars, lookback) : InOTEShort(bars, lookback);
    }

    // ICT/SMC: Displacement candle + FVG entry zone detector
    public sealed class DisplacementDetector
    {
        public bool IsBullishDisplacement(Bars bars, IndicatorDataSeries atr, double mult = 2.0)
        {
            if (bars.Count < 4) return false;
            double range = bars.HighPrices.Last(1) - bars.LowPrices.Last(1);
            double atrVal = atr.Last(1);
            if (atrVal <= 0 || range < mult * atrVal) return false;
            double bodyPct = (bars.ClosePrices.Last(1) - bars.OpenPrices.Last(1)) / range;
            return bodyPct > 0.5;
        }
        public bool IsBearishDisplacement(Bars bars, IndicatorDataSeries atr, double mult = 2.0)
        {
            if (bars.Count < 4) return false;
            double range = bars.HighPrices.Last(1) - bars.LowPrices.Last(1);
            double atrVal = atr.Last(1);
            if (atrVal <= 0 || range < mult * atrVal) return false;
            double bodyPct = (bars.OpenPrices.Last(1) - bars.ClosePrices.Last(1)) / range;
            return bodyPct > 0.5;
        }
        // Price is inside a bullish FVG (gap between bar[i] low and bar[i+2] high)
        public bool PriceInBullishFVG(Bars bars, int lookback = 15)
        {
            double price = bars.ClosePrices.Last(1);
            for (int i = 2; i < Math.Min(lookback, bars.Count - 3); i++)
            {
                double lo = bars.LowPrices.Last(i);
                double hi2 = bars.HighPrices.Last(i + 2);
                if (lo > hi2 && price >= hi2 && price <= lo) return true;
            }
            return false;
        }
        public bool PriceInBearishFVG(Bars bars, int lookback = 15)
        {
            double price = bars.ClosePrices.Last(1);
            for (int i = 2; i < Math.Min(lookback, bars.Count - 3); i++)
            {
                double hi = bars.HighPrices.Last(i);
                double lo2 = bars.LowPrices.Last(i + 2);
                if (hi < lo2 && price >= hi && price <= lo2) return true;
            }
            return false;
        }
        public bool PriceInFVG(Bars bars, TradeDir dir, int lookback = 15)
            => dir == TradeDir.Long ? PriceInBullishFVG(bars, lookback) : PriceInBearishFVG(bars, lookback);
    }

    // SMC: Inducement detector — equal H/L swept then reversed
    public sealed class InducementDetector
    {
        public bool BullishInducement(Bars bars, Symbol symbol, int lookback = 15)
        {
            if (bars.Count < lookback + 3) return false;
            double tol = symbol.PipSize * 3;
            for (int i = 4; i < lookback; i++)
            {
                bool equalLows = Math.Abs(bars.LowPrices.Last(i) - bars.LowPrices.Last(i + 1)) < tol;
                if (!equalLows) continue;
                double swept = Math.Min(bars.LowPrices.Last(1), bars.LowPrices.Last(2));
                bool wasSwept = swept < bars.LowPrices.Last(i) - tol;
                bool reversed = bars.ClosePrices.Last(1) > bars.LowPrices.Last(i);
                if (wasSwept && reversed) return true;
            }
            return false;
        }
        public bool BearishInducement(Bars bars, Symbol symbol, int lookback = 15)
        {
            if (bars.Count < lookback + 3) return false;
            double tol = symbol.PipSize * 3;
            for (int i = 4; i < lookback; i++)
            {
                bool equalHighs = Math.Abs(bars.HighPrices.Last(i) - bars.HighPrices.Last(i + 1)) < tol;
                if (!equalHighs) continue;
                double swept = Math.Max(bars.HighPrices.Last(1), bars.HighPrices.Last(2));
                bool wasSwept = swept > bars.HighPrices.Last(i) + tol;
                bool reversed = bars.ClosePrices.Last(1) < bars.HighPrices.Last(i);
                if (wasSwept && reversed) return true;
            }
            return false;
        }
        public bool Detected(Bars bars, Symbol symbol, TradeDir dir, int lookback = 15)
            => dir == TradeDir.Long ? BullishInducement(bars, symbol, lookback) : BearishInducement(bars, symbol, lookback);
    }

    // SMC: Strong vs Weak structure quality scorer
    public sealed class StructureQuality
    {
        public bool IsStrongHigh(Bars bars, int barsAgo)
        {
            if (barsAgo >= bars.Count - 1) return false;
            double h = bars.HighPrices.Last(barsAgo), o = bars.OpenPrices.Last(barsAgo), c = bars.ClosePrices.Last(barsAgo);
            double range = h - bars.LowPrices.Last(barsAgo);
            return range > 0 && (h - Math.Max(o, c)) / range < 0.4;
        }
        public bool IsStrongLow(Bars bars, int barsAgo)
        {
            if (barsAgo >= bars.Count - 1) return false;
            double l = bars.LowPrices.Last(barsAgo), o = bars.OpenPrices.Last(barsAgo), c = bars.ClosePrices.Last(barsAgo);
            double range = bars.HighPrices.Last(barsAgo) - l;
            return range > 0 && (Math.Min(o, c) - l) / range < 0.4;
        }
        public double Score(Bars bars, TradeDir dir, int lookback = 10)
        {
            int strong = 0, total = 0;
            for (int i = 1; i < Math.Min(lookback, bars.Count - 1); i++)
            {
                total++;
                if (dir == TradeDir.Long && IsStrongLow(bars, i)) strong++;
                if (dir == TradeDir.Short && IsStrongHigh(bars, i)) strong++;
            }
            return total > 0 ? (double)strong / total : 0.5;
        }
    }

    // Price Action: trigger candle confirmation
    public sealed class TriggerCandleDetector
    {
        public bool IsBullishPinBar(Bars bars, int ago = 1)
        {
            double h = bars.HighPrices.Last(ago), l = bars.LowPrices.Last(ago);
            double o = bars.OpenPrices.Last(ago), c = bars.ClosePrices.Last(ago);
            double range = h - l;
            return range > 0 && (Math.Min(o, c) - l) / range >= 0.60;
        }
        public bool IsBearishPinBar(Bars bars, int ago = 1)
        {
            double h = bars.HighPrices.Last(ago), l = bars.LowPrices.Last(ago);
            double o = bars.OpenPrices.Last(ago), c = bars.ClosePrices.Last(ago);
            double range = h - l;
            return range > 0 && (h - Math.Max(o, c)) / range >= 0.60;
        }
        public bool IsBullishEngulfing(Bars bars)
        {
            double o1=bars.OpenPrices.Last(1),c1=bars.ClosePrices.Last(1),o2=bars.OpenPrices.Last(2),c2=bars.ClosePrices.Last(2);
            return c2<o2 && c1>o1 && o1<=c2 && c1>=o2;
        }
        public bool IsBearishEngulfing(Bars bars)
        {
            double o1=bars.OpenPrices.Last(1),c1=bars.ClosePrices.Last(1),o2=bars.OpenPrices.Last(2),c2=bars.ClosePrices.Last(2);
            return c2>o2 && c1<o1 && o1>=c2 && c1<=o2;
        }
        public bool IsDoji(Bars bars, int ago = 1)
        {
            double range = bars.HighPrices.Last(ago) - bars.LowPrices.Last(ago);
            return range > 0 && Math.Abs(bars.ClosePrices.Last(ago) - bars.OpenPrices.Last(ago)) / range < 0.10;
        }
        public bool IsInsideBar(Bars bars)
            => bars.HighPrices.Last(1) < bars.HighPrices.Last(2) && bars.LowPrices.Last(1) > bars.LowPrices.Last(2);
        public bool Confirms(Bars bars, TradeDir dir)
        {
            if (dir == TradeDir.Long)  return IsBullishPinBar(bars) || IsBullishEngulfing(bars);
            if (dir == TradeDir.Short) return IsBearishPinBar(bars) || IsBearishEngulfing(bars);
            return false;
        }
    }

    // Institutional levels: PDH/PDL/PDC, Weekly Open, London Open Range, Round Numbers
    public sealed class InstitutionalLevels
    {
        private double _pdh, _pdl, _pdc, _weeklyOpen, _lorHigh = double.MinValue, _lorLow = double.MaxValue;
        private DateTime _lastDay, _lastWeek;
        private bool _lorDone;
        public double PDH => _pdh; public double PDL => _pdl; public double PDC => _pdc;
        public double WeeklyOpen => _weeklyOpen;
        public double LORHigh => _lorDone ? _lorHigh : 0;
        public double LORLow  => _lorDone ? _lorLow  : 0;
        public void Update(Bars bars, DateTime t, SessionGate sess)
        {
            if (t.Date != _lastDay && bars.Count > 2)
            {
                _pdh = bars.HighPrices.Last(1); _pdl = bars.LowPrices.Last(1); _pdc = bars.ClosePrices.Last(1);
                _lastDay = t.Date; _lorHigh = double.MinValue; _lorLow = double.MaxValue; _lorDone = false;
            }
            if (t.DayOfWeek == DayOfWeek.Monday && t.Date != _lastWeek && bars.Count > 1)
            { _weeklyOpen = bars.OpenPrices.Last(1); _lastWeek = t.Date; }
            int sm; var s = sess.Classify(t, out sm);
            if (s == Session.LdnOpen && !_lorDone)
            {
                if (bars.HighPrices.Last(1) > _lorHigh) _lorHigh = bars.HighPrices.Last(1);
                if (bars.LowPrices.Last(1)  < _lorLow)  _lorLow  = bars.LowPrices.Last(1);
            }
            if (s == Session.LdnMain && !_lorDone && _lorHigh > double.MinValue) _lorDone = true;
        }
        public bool IsNear(double price, double tol)
        {
            if (_pdh > 0 && Math.Abs(price - _pdh) < tol) return true;
            if (_pdl > 0 && Math.Abs(price - _pdl) < tol) return true;
            if (_pdc > 0 && Math.Abs(price - _pdc) < tol) return true;
            if (_weeklyOpen > 0 && Math.Abs(price - _weeklyOpen) < tol) return true;
            if (_lorDone && (Math.Abs(price - _lorHigh) < tol || Math.Abs(price - _lorLow) < tol)) return true;
            return false;
        }
        public bool IsNearRoundNumber(double price, Symbol symbol)
        {
            double pips = price / symbol.PipSize;
            double mod100 = pips % 100, mod50 = pips % 50;
            return mod100 < 3 || mod100 > 97 || mod50 < 3 || mod50 > 47;
        }
    }

    // Filter: ADX trend strength
    public sealed class ADXFilter
    {
        private readonly DirectionalMovementSystem _adx;
        public ADXFilter(Robot robot, Bars bars) { _adx = robot.Indicators.DirectionalMovementSystem(bars, 14); }
        public bool TrendStrong()  => _adx.ADX.Last(0) > 20;
        public bool MarketRanging()=> _adx.ADX.Last(0) < 30;
        public double Value        => _adx.ADX.Last(0);
    }

    // Filter: Volume clock — relative volume for this hour
    public sealed class VolumeClockFilter
    {
        private readonly Dictionary<int, List<double>> _byHour = new Dictionary<int, List<double>>();
        public void Record(double vol, DateTime t)
        {
            int h = t.Hour;
            if (!_byHour.ContainsKey(h)) _byHour[h] = new List<double>();
            if (_byHour[h].Count > 20) _byHour[h].RemoveAt(0);
            _byHour[h].Add(vol);
        }
        public double RelVol(double vol, DateTime t)
        {
            int h = t.Hour;
            if (!_byHour.ContainsKey(h) || _byHour[h].Count < 5) return 1.0;
            double avg = _byHour[h].Average();
            return avg > 0 ? vol / avg : 1.0;
        }
        public bool IsActive(double vol, DateTime t) => RelVol(vol, t) >= 0.80;
    }

    // CVD improvement: M1 sub-bar delta aggregation for M15 accuracy
    public sealed class M1DeltaAggregator
    {
        private readonly Bars _m1;
        public M1DeltaAggregator(Robot robot, Symbol symbol)
        { _m1 = robot.MarketData.GetBars(TimeFrame.Minute, symbol.Name); }
        private static double BarProxy(double h, double l, double c, double v)
        { double rng = h - l; double bw = rng > 0 ? (c - l) / rng : 0.5; return v * (bw - (1.0 - bw)); }
        public double M15Delta(int m15BarsAgo = 1)
        {
            double tot = 0; int base_ = m15BarsAgo * 15;
            for (int i = base_; i < base_ + 15 && i < _m1.Count - 1; i++)
                tot += BarProxy(_m1.HighPrices.Last(i), _m1.LowPrices.Last(i), _m1.ClosePrices.Last(i), _m1.TickVolumes.Last(i));
            return tot;
        }
        public double M1CVD(int m1Bars = 75)
        {
            double cvd = 0;
            for (int i = 1; i <= Math.Min(m1Bars, _m1.Count - 2); i++)
                cvd += BarProxy(_m1.HighPrices.Last(i), _m1.LowPrices.Last(i), _m1.ClosePrices.Last(i), _m1.TickVolumes.Last(i));
            return cvd;
        }
    }

    // Structure: M15 + H1 multi-timeframe alignment (extends existing H4+D1)
    public sealed class MultiTimeframeStructure
    {
        private readonly ExponentialMovingAverage _emaM15, _emaH1;
        private readonly Bars _m15, _h1;
        public MultiTimeframeStructure(Robot robot, Symbol symbol)
        {
            _m15 = robot.MarketData.GetBars(TimeFrame.Minute15, symbol.Name);
            _h1  = robot.MarketData.GetBars(TimeFrame.Hour, symbol.Name);
            _emaM15 = robot.Indicators.ExponentialMovingAverage(_m15.ClosePrices, 20);
            _emaH1  = robot.Indicators.ExponentialMovingAverage(_h1.ClosePrices, 20);
        }
        public HtfBias M15Bias() { double e=_emaM15.Result.Last(0),c=_m15.ClosePrices.Last(0); return c>e*1.0001?HtfBias.Bull:c<e*0.9999?HtfBias.Bear:HtfBias.Neutral; }
        public HtfBias H1Bias()  { double e=_emaH1.Result.Last(0), c=_h1.ClosePrices.Last(0);  return c>e*1.0001?HtfBias.Bull:c<e*0.9999?HtfBias.Bear:HtfBias.Neutral; }
        public int AlignmentScore(TradeDir dir, HtfBias h4d1)
        {
            int s = 0;
            var m15 = M15Bias(); var h1 = H1Bias();
            if (dir==TradeDir.Long)  { if(m15==HtfBias.Bull)s++; if(h1==HtfBias.Bull)s++; if(h4d1==HtfBias.Bull)s+=2; }
            if (dir==TradeDir.Short) { if(m15==HtfBias.Bear)s++; if(h1==HtfBias.Bear)s++; if(h4d1==HtfBias.Bear)s+=2; }
            return s; // 0–4
        }
    }
}

// ============================================================
//  MAIN ROBOT
// ============================================================
namespace GodmodeOfeaFinal
{
    using GodmodeOfea;
    using GodmodeOfea.Enhanced;

    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.FullAccess, AddIndicators = true)]
    public class GODMODE_OFEA_FINAL : Robot
    {
        [Parameter("Operating Mode",          Group="Mode",    DefaultValue=OpMode.Manual)] public OpMode OperatingMode  { get; set; }
        [Parameter("Enable Notifications",    Group="Mode",    DefaultValue=true)]  public bool EnableNotifications { get; set; }
        [Parameter("Enable Push Alerts",      Group="Mode",    DefaultValue=true)]  public bool EnablePushAlerts    { get; set; }
        [Parameter("Enable Sound Alerts",     Group="Mode",    DefaultValue=true)]  public bool EnableSoundAlerts   { get; set; }
        [Parameter("Enable Email Alerts",     Group="Mode",    DefaultValue=false)] public bool EnableEmailAlerts   { get; set; }
        [Parameter("Enable Model1 Trend",     Group="Strategy",DefaultValue=true)]  public bool EnableModel1_Trend  { get; set; }
        [Parameter("Enable Model2 MeanRev",   Group="Strategy",DefaultValue=true)]  public bool EnableModel2_MeanRev{ get; set; }
        [Parameter("Half Size On HTF Conflict",Group="Strategy",DefaultValue=false)] public bool HalfSize_OnHTFConflict { get; set; }
        [Parameter("SAST OffsetFromBroker (hours)",Group="Session",DefaultValue=0)] public int SAST_OffsetFromBroker { get; set; }
        [Parameter("Trade Asian Session",     Group="Session", DefaultValue=false)] public bool TradeAsianSession  { get; set; }
        [Parameter("Trade London Open",       Group="Session", DefaultValue=false)] public bool TradeLondonOpen    { get; set; }
        [Parameter("Trade London Main",       Group="Session", DefaultValue=true)]  public bool TradeLondonMain    { get; set; }
        [Parameter("Trade NY Open",           Group="Session", DefaultValue=false)] public bool TradeNYOpen        { get; set; }
        [Parameter("Trade NY Main",           Group="Session", DefaultValue=true)]  public bool TradeNYMain        { get; set; }
        [Parameter("NY Open Blackout Mins",   Group="Session", DefaultValue=20)]    public int  NYOpen_Blackout_Mins{ get; set; }
        [Parameter("Delta Lookback",          Group="OrderFlow",DefaultValue=20)]   public int    DeltaLookback      { get; set; }
        [Parameter("Vol Z Threshold",         Group="OrderFlow",DefaultValue=1.5)]  public double VolZThreshold      { get; set; }
        [Parameter("Delta Z Threshold",       Group="OrderFlow",DefaultValue=2.0)]  public double DeltaZThreshold    { get; set; }
        [Parameter("Aggression Z Threshold",  Group="OrderFlow",DefaultValue=2.0)]  public double AggressionZThreshold{ get; set; }
        [Parameter("Min Absorption Stars",    Group="OrderFlow",DefaultValue=3)]    public int    MinAbsorptionStars  { get; set; }
        [Parameter("Min Stacked Imbalance Rows",Group="OrderFlow",DefaultValue=3)]  public int    MinStackedImbalanceRows{ get; set; }
        [Parameter("Imbalance Ratio",         Group="OrderFlow",DefaultValue=3.0)]  public double ImbalanceRatio      { get; set; }
        [Parameter("VP Length",               Group="VP",      DefaultValue=100)]   public int    VPLength  { get; set; }
        [Parameter("VP Bins",                 Group="VP",      DefaultValue=50)]    public int    VPBins    { get; set; }
        [Parameter("VA Value Area Pct",       Group="VP",      DefaultValue=0.70)]  public double VAValueAreaPct{ get; set; }
        [Parameter("LVN Ratio",               Group="VP",      DefaultValue=0.20)]  public double LVNRatio  { get; set; }
        [Parameter("HVN Ratio",               Group="VP",      DefaultValue=0.70)]  public double HVNRatio  { get; set; }
        [Parameter("Loc Tol ATR",             Group="VP",      DefaultValue=0.5)]   public double LocTolATR { get; set; }
        [Parameter("Risk Pct",                Group="Risk",    DefaultValue=1.0)]   public double RiskPct         { get; set; }
        [Parameter("Risk Pct Half Mode",      Group="Risk",    DefaultValue=0.5)]   public double RiskPct_HalfMode{ get; set; }
        [Parameter("Risk Pct Max",            Group="Risk",    DefaultValue=0.5, MinValue=0.0, MaxValue=2.0, Step=0.1)] public double RiskPctMax { get; set; }
        [Parameter("Kelly fraction k",        Group="Risk",    DefaultValue=0.25, MinValue=0.1, MaxValue=1.0)] public double KellyKappa { get; set; }
        [Parameter("Max R:R",                 Group="Risk",    DefaultValue=6.0)]   public double MaxRR           { get; set; }
        [Parameter("Min R:R",                 Group="Risk",    DefaultValue=2.0)]   public double MinRR           { get; set; }
        [Parameter("Max DD Pct",              Group="Risk",    DefaultValue=5.0)]   public double MaxDDPct        { get; set; }
        [Parameter("Max Consec Losses",       Group="Risk",    DefaultValue=3)]     public int    MaxConsecLosses  { get; set; }
        [Parameter("Max Spread Mult",         Group="Risk",    DefaultValue=2.0)]   public double MaxSpreadMult   { get; set; }
        [Parameter("Spread Max Z",            Group="Risk",    DefaultValue=2.0)]   public double SpreadMaxZ      { get; set; }
        [Parameter("Allow Pyramiding",        Group="Risk",    DefaultValue=false)] public bool   AllowPyramiding { get; set; }
        [Parameter("Use Partial Close",       Group="TradeMgmt",DefaultValue=true)] public bool   UsePartialClose { get; set; }
        [Parameter("Partial Close Pct",       Group="TradeMgmt",DefaultValue=50.0)] public double PartialClosePct { get; set; }
        [Parameter("Partial Close At R",      Group="TradeMgmt",DefaultValue=1.0)]  public double PartialCloseAtR { get; set; }
        [Parameter("Move SL To BE At R",      Group="TradeMgmt",DefaultValue=1.0)]  public double MoveSLToBE_AtR  { get; set; }
        [Parameter("Use Trailing Stop",       Group="TradeMgmt",DefaultValue=true)] public bool   UseTrailingStop { get; set; }
        [Parameter("Trail ATR Mult",          Group="TradeMgmt",DefaultValue=1.0)]  public double TrailATRMult    { get; set; }
        [Parameter("Exit At POC",             Group="TradeMgmt",DefaultValue=true)] public bool   ExitAtPOC       { get; set; }
        [Parameter("Bar-delta lookback",      Group="Enhanced",DefaultValue=20)]    public int    BarDeltaLookback     { get; set; }
        [Parameter("Enhanced Prob Threshold", Group="Enhanced",DefaultValue=85.0)]  public double EnhancedProbThreshold{ get; set; }
        [Parameter("Show Dashboard",          Group="Viz",     DefaultValue=true)]  public bool ShowDashboard       { get; set; }
        [Parameter("Show VP Levels",          Group="Viz",     DefaultValue=true)]  public bool ShowVPLevels        { get; set; }
        [Parameter("Show CVD Line",           Group="Viz",     DefaultValue=true)]  public bool ShowCVDLine         { get; set; }
        [Parameter("Show Footprint Markers",  Group="Viz",     DefaultValue=true)]  public bool ShowFootprintMarkers{ get; set; }
        [Parameter("Show Session Shading",    Group="Viz",     DefaultValue=true)]  public bool ShowSessionShading  { get; set; }
        [Parameter("Show Trade Arrows",       Group="Viz",     DefaultValue=true)]  public bool ShowTradeArrows     { get; set; }
        [Parameter("01 AbsBot",    Group="Setups",DefaultValue=true)]  public bool EnableSetup_01_AbsBot    { get; set; }
        [Parameter("02 AbsTop",    Group="Setups",DefaultValue=true)]  public bool EnableSetup_02_AbsTop    { get; set; }
        [Parameter("03 CVDBear",   Group="Setups",DefaultValue=true)]  public bool EnableSetup_03_CVDBear   { get; set; }
        [Parameter("04 CVDBull",   Group="Setups",DefaultValue=true)]  public bool EnableSetup_04_CVDBull   { get; set; }
        [Parameter("05 VALBnc",    Group="Setups",DefaultValue=true)]  public bool EnableSetup_05_VALBnc    { get; set; }
        [Parameter("06 VAHFade",   Group="Setups",DefaultValue=true)]  public bool EnableSetup_06_VAHFade   { get; set; }
        [Parameter("07 POCRet",    Group="Setups",DefaultValue=true)]  public bool EnableSetup_07_POCRet    { get; set; }
        [Parameter("08 LVNLong",   Group="Setups",DefaultValue=true)]  public bool EnableSetup_08_LVNLong   { get; set; }
        [Parameter("09 LVNShort",  Group="Setups",DefaultValue=true)]  public bool EnableSetup_09_LVNShort  { get; set; }
        [Parameter("10 HVNRej",    Group="Setups",DefaultValue=false)] public bool EnableSetup_10_HVNRej    { get; set; }
        [Parameter("11 StackBull", Group="Setups",DefaultValue=true)]  public bool EnableSetup_11_StackBull { get; set; }
        [Parameter("12 StackBear", Group="Setups",DefaultValue=true)]  public bool EnableSetup_12_StackBear { get; set; }
        [Parameter("13 PullStack", Group="Setups",DefaultValue=true)]  public bool EnableSetup_13_PullStack { get; set; }
        [Parameter("14 Spring",    Group="Setups",DefaultValue=true)]  public bool EnableSetup_14_Spring    { get; set; }
        [Parameter("15 Upthrust",  Group="Setups",DefaultValue=true)]  public bool EnableSetup_15_Upthrust  { get; set; }
        [Parameter("16 SOS",       Group="Setups",DefaultValue=true)]  public bool EnableSetup_16_SOS       { get; set; }
        [Parameter("17 LPSY",      Group="Setups",DefaultValue=true)]  public bool EnableSetup_17_LPSY      { get; set; }
        [Parameter("18 LiqSweep",  Group="Setups",DefaultValue=true)]  public bool EnableSetup_18_LiqSweep  { get; set; }
        [Parameter("19 OBReturn",  Group="Setups",DefaultValue=true)]  public bool EnableSetup_19_OBReturn  { get; set; }
        [Parameter("20 SMTDiv",    Group="Setups",DefaultValue=true)]  public bool EnableSetup_20_SMTDiv    { get; set; }
        [Parameter("21 Breaker",   Group="Setups",DefaultValue=true)]  public bool EnableSetup_21_Breaker   { get; set; }
        [Parameter("22 AMD",       Group="Setups",DefaultValue=true)]  public bool EnableSetup_22_AMD       { get; set; }
        [Parameter("23 UnfAuc",    Group="Setups",DefaultValue=true)]  public bool EnableSetup_23_UnfAuc    { get; set; }
        [Parameter("24 PoorHL",    Group="Setups",DefaultValue=true)]  public bool EnableSetup_24_PoorHL    { get; set; }
        [Parameter("25 Iceberg",   Group="Setups",DefaultValue=true)]  public bool EnableSetup_25_Iceberg   { get; set; }

        private DeltaEngine _delta; private VolumeProfile _vp; private FootprintAnalyzer _fp;
        private SessionGate _sess; private HtfAlignment _htf; private RiskManager _risk;
        private TradeManager _trade; private NotificationCenter _notif; private Dashboard _dash;
        private ChartViz _viz; private TradeLogger _logger; private AverageTrueRange _atr;
        private AutoRiskReward _autoRR; private DateTime _lastDay; private int _tradesToday;
        private VWAP _vwap; private BidAskMonitor _ba; private DeltaEnhanced _dE;
        private RegimeHMM _reg; private PriceAction _pa; private SweepDetector _sw;
        private PoolResilience _pool; private ProbabilityScore _prob; private bool _seeded;
        // God-Level enhancement modules
        private OTECalculator          _ote;
        private DisplacementDetector   _disp;
        private InducementDetector     _ind;
        private StructureQuality       _sq;
        private TriggerCandleDetector  _tc;
        private InstitutionalLevels    _instLvl;
        private ADXFilter              _adxFilt;
        private VolumeClockFilter      _volClock;
        private M1DeltaAggregator      _m1Delta;
        private MultiTimeframeStructure _mtfStr;

        protected override void OnStart()
        {
            _delta  = new DeltaEngine(Symbol, Bars, DeltaLookback);
            _vp     = new VolumeProfile(Symbol, Bars, VPBins, VPLength, VAValueAreaPct, LVNRatio, HVNRatio);
            _fp     = new FootprintAnalyzer(Bars, VolZThreshold, DeltaZThreshold, MinStackedImbalanceRows, ImbalanceRatio);
            _sess   = new SessionGate(SAST_OffsetFromBroker, NYOpen_Blackout_Mins, TradeAsianSession, TradeLondonOpen, TradeLondonMain, TradeNYOpen, TradeNYMain);
            _htf    = new HtfAlignment(this, Symbol);
            _risk   = new RiskManager(this, Symbol, RiskPct, RiskPct_HalfMode, MaxDDPct, MaxConsecLosses, MaxSpreadMult);
            _atr    = Indicators.AverageTrueRange(14, MovingAverageType.Simple);
            _trade  = new TradeManager(this, Symbol, "GODMODE", UsePartialClose, PartialClosePct, PartialCloseAtR, MoveSLToBE_AtR, UseTrailingStop, TrailATRMult, ExitAtPOC, _atr);
            _notif  = new NotificationCenter(this, EnableNotifications, EnableSoundAlerts, EnablePushAlerts, EnableEmailAlerts, () => Bars.OpenTimes.LastValue);
            _dash   = new Dashboard(Chart, Color.Lime, Color.Red, Color.Goldenrod);
            _viz    = new ChartViz(Chart, ShowVPLevels, ShowFootprintMarkers, ShowSessionShading, ShowTradeArrows);
            _logger = new TradeLogger(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "GODMODE_OFEA_FINAL_log.csv"));
            _autoRR = new AutoRiskReward(this, Chart, Symbol);
            _vwap = new VWAP(); _ba = new BidAskMonitor(); _dE = new DeltaEnhanced(BarDeltaLookback);
            _reg = new RegimeHMM(); _pa = new PriceAction(); _sw = new SweepDetector();
            _pool = new PoolResilience(); _prob = new ProbabilityScore();
            // God-Level enhancements
            _ote      = new OTECalculator();
            _disp     = new DisplacementDetector();
            _ind      = new InducementDetector();
            _sq       = new StructureQuality();
            _tc       = new TriggerCandleDetector();
            _instLvl  = new InstitutionalLevels();
            _adxFilt  = new ADXFilter(this, Bars);
            _volClock = new VolumeClockFilter();
            _m1Delta  = new M1DeltaAggregator(this, Symbol);
            _mtfStr   = new MultiTimeframeStructure(this, Symbol);
            Print($"GODMODE_OFEA FINAL initialised — mode={OperatingMode} k={KellyKappa:F2} [GOD-LEVEL ACTIVE]");
        }

        protected override void OnTick()
        {
            _ba.Update(Symbol);
            var openPos = _trade.FindOpenPosition();
            if (openPos != null) _autoRR.OnTick(openPos);
            if (ShowDashboard && _dash.ShouldRefresh()) RefreshDashboard();
            ManageOpenPosition();
            if (!_seeded) { _seeded = true; }
        }

        protected override void OnBar()
        {
            HandleDayRollover();
            _delta.OnBarClose(); _risk.SampleSpread(); _vp.Recompute();
            _instLvl.Update(Bars, Server.Time, _sess);
            _volClock.Record(Bars.TickVolumes.Last(1), Server.Time);
            RunEnhancedBarClose();
            RunBarClose();
        }

        protected override void OnStop() { _delta?.Detach(); _dash?.Clear(); }

        private void RunEnhancedBarClose()
        {
            int last = Bars.ClosePrices.Count - 2; if (last < 30) return;
            double high=Bars.HighPrices[last], low=Bars.LowPrices[last], close=Bars.ClosePrices[last], tv=Bars.TickVolumes[last];
            double rng=high-low, bw=rng>0?(close-low)/rng:0.5, bd=tv*(bw-(1.0-bw));
            _dE.OnBar(bd, close);
            _vwap.Update((high+low+close)/3.0, tv, Bars.OpenTimes[last]);
            _reg.Update(_dE.CvdSlope, 0, 0, _dE.ZScore);
            int N=Math.Min(50,last+1); var H=new double[N]; var L=new double[N]; var C=new double[N];
            for(int i=0;i<N;i++){int idx=last-i; if(idx<0)break; H[i]=Bars.HighPrices[idx]; L[i]=Bars.LowPrices[idx]; C[i]=Bars.ClosePrices[idx];}
            _pa.Update(H, L, C, 20, 0.10, _atr.Result.LastValue);
            double pct = ComputeCompositeProbability();
            Print($"[ENHANCED] regime={_reg.Current} prob={pct:F0}% grade={_prob.Grade()}");
            if (OperatingMode == OpMode.Auto && pct >= EnhancedProbThreshold) EnhancedFireTradeIfReady();
        }

        private double ComputeCompositeProbability()
        {
            double g1=(_pa.EqualHighsCluster||_pa.EqualLowsCluster)?1.0:0.0, g2=1.0, g3=1.0;
            double g4=Math.Abs(_dE.CvdSlope)>0?1.0:0.0, g5=1.0, g6=_reg.JustTransitioned?1.0:0.5;
            double g7=_sw.Last.PreconditionsPassed/6.0, g8=Math.Abs(_vwap.ZScore(Symbol.Bid))<2.0?1.0:0.0;
            double g9=(_pa.FvgUp||_pa.FvgDown)?1.0:0.0, g10=0.5, g11=_ba.SpreadAcceptable(SpreadMaxZ)?1.0:0.0, g12=1.0;
            return _prob.Compute(g1,g2,g3,g4,g5,g6,g7,g8,g9,g10,g11,g12);
        }

        private void EnhancedFireTradeIfReady()
        {
            double p=_sw.EmpiricalWinRate(), b=_sw.ExpectedR()>0?_sw.ExpectedR():2.0;
            double riskPct=Math.Min(RiskPctMax, KellySizer.RiskPctFromKelly(p,b,KellyKappa));
            Print($"[ENHANCED] kelly-fire candidate: riskPct={riskPct:F3}%");
        }

        private void HandleDayRollover() { var today=Server.Time.Date; if(today!=_lastDay){_lastDay=today;_tradesToday=0;_risk.OnDayRollover();} }

        private void ManageOpenPosition()
        {
            if(_trade.FindOpenPosition()==null) return;
            _trade.ManagePosition(_vp.Poc);
            if(_sess.ApproachingNyMainEnd(Server.Time,5)){_trade.CloseAll();_notif.NL_KillSwitch("NY_MAIN_END");}
        }

        private void RunBarClose()
        {
            if(_risk.IsDayHalted) return;
            var gDD=_risk.CheckDailyDrawdown(); if(!gDD.Passed){_notif.NL_KillSwitch($"DD {gDD.Value:F2}%");_trade.CloseAll();_risk.HaltDay();return;}
            var gSp=_risk.CheckSpread(); if(!gSp.Passed){_notif.NL_KillSwitch("SPREAD_BLOWOUT");return;}
            var gCL=_risk.CheckConsecLosses(); if(!gCL.Passed){_notif.NL_KillSwitch("CONSEC_LOSSES");_risk.HaltDay();return;}
            if(!_ba.SpreadAcceptable(SpreadMaxZ)){_notif.NL_KillSwitch("BIDASK_SPREAD_Z");return;}
            int sastMin; var session=_sess.Classify(Server.Time,out sastMin);
            if(_sess.SessionChanged(session)&&(session==Session.LdnMain||session==Session.NyMain)) _notif.NC_KillZone(session);
            if(!_sess.IsSessionEnabled(session)||_sess.InNyOpenBlackout(Server.Time)) return;
            var model=_sess.ModelForSession(session);
            if(model==ActiveModel.M1Trend&&!EnableModel1_Trend) return;
            if(model==ActiveModel.M2MeanRev&&!EnableModel2_MeanRev) return;
            var shape=_vp.Shape; var state=_vp.State; _notif.NF_ProfileState(shape,state);
            // M2 mean-reversion setups (VAL/VAH/absorption) fire in any state — location-based, not trend-based
            // M1 trend setups require confirmed imbalanced state; Unknown state is allowed as fallback
            bool stateOK = state == MarketState.Unknown ||
                           model == ActiveModel.M2MeanRev ||
                           (model == ActiveModel.M1Trend && state == MarketState.Imbalanced);
            if(!stateOK) return;
            double lastClose=Bars.ClosePrices.Last(1); var loc=_vp.LocationAt(lastClose,LocTolATR*10.0);
            if(loc==VpLoc.None) return;
            _notif.NA_VpLevel(OFHelpers.LocToStr(loc),lastClose);
            var htf=_htf.Combined(); if(htf!=HtfBias.Neutral) _notif.ND_HTFAligned(htf);
            double slope=_delta.CvdSlope5(); var cvdDir=slope>0?TradeDir.Long:(slope<0?TradeDir.Short:TradeDir.None);
            if(cvdDir!=TradeDir.None) _notif.NE_CvdConfirm(cvdDir,_delta.Cvd);
            SetupCandidate best=null; int bestScore=0;
            ScoreAllSetups(model,htf,cvdDir,loc,ref best,ref bestScore);
            if(best==null) return;
            _notif.NG_FootprintSignal("setup",best.AbsStars);
            if(_delta.VolumeZ()>=AggressionZThreshold) _notif.NH_Aggression(_delta.VolumeZ());
            // ATR-based SL: enforce minimum 0.5×ATR distance to survive noise
            double minSl = _atr.Result.Last(0) * 0.5;
            if (minSl > 0)
            {
                if (best.Direction == TradeDir.Long  && best.Entry - best.Sl < minSl) best.Sl = best.Entry - minSl;
                if (best.Direction == TradeDir.Short && best.Sl - best.Entry < minSl) best.Sl = best.Entry + minSl;
            }
            double riskDist=Math.Abs(best.Entry-best.Sl), rr=riskDist>0?Math.Abs(best.Tp-best.Entry)/riskDist:0;
            if(rr<MinRR) return;
            best.Score=bestScore; best.Priority=bestScore>=5?Priority.P1:(bestScore>=4?Priority.P2:Priority.P3);
            bool halfSize=HalfSize_OnHTFConflict&&!_htf.IsAligned(best.Direction);
            double baseVolume=_risk.ComputeVolume(riskDist,halfSize); if(baseVolume<=0) return;
            _notif.NI_AplusReady(best,rr);
            if(OperatingMode==OpMode.Auto)
            {
                if(!AllowPyramiding&&_trade.FindOpenPosition()!=null) return;
                if(_trade.OpenPosition(best.Direction,baseVolume,best.Sl,best.Tp,"GODMODE_FINAL"))
                {
                    _tradesToday++; _notif.NJ_TradeFired(best,baseVolume,"AUTO");
                    _autoRR.OnPositionOpened(_trade.FindOpenPosition());
                    _logger.Append("ENTRY",best,Symbol.Name,session,state,htf,shape,_vp.Poc,_vp.Vah,_vp.Val,_delta.Cvd,_delta.BarDelta,_delta.VolumeZ(),_delta.DeltaZ(),"AUTO",RiskPct,baseVolume);
                }
            }
            else
            {
                _viz.DrawTradeLines(best.Entry,best.Sl,best.Tp,best.Direction);
                _logger.Append("SKIP_F1",best,Symbol.Name,session,state,htf,shape,_vp.Poc,_vp.Vah,_vp.Val,_delta.Cvd,_delta.BarDelta,_delta.VolumeZ(),_delta.DeltaZ(),"MANUAL",RiskPct,0);
            }
        }

        private void ScoreAllSetups(ActiveModel model, HtfBias htf, TradeDir cvdDir, VpLoc loc, ref SetupCandidate best, ref int bestScore)
        {
            double tol=LocTolATR*10.0; SetupCandidate _c;
            if(EnableSetup_01_AbsBot)    { _c=SetupDetectors.AbsBot   (Symbol,Bars,_delta,_vp,_fp,tol,MinAbsorptionStars); if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_02_AbsTop)    { _c=SetupDetectors.AbsTop   (Symbol,Bars,_delta,_vp,_fp,tol,MinAbsorptionStars); if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_03_CVDBear)   { _c=SetupDetectors.CvdBear  (Symbol,Bars,_delta,_vp,tol);                        if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_04_CVDBull)   { _c=SetupDetectors.CvdBull  (Symbol,Bars,_delta,_vp,tol);                        if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_05_VALBnc)    { _c=SetupDetectors.ValBounce(Symbol,Bars,_delta,_vp,tol);                        if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_06_VAHFade)   { _c=SetupDetectors.VahFade  (Symbol,Bars,_delta,_vp,tol);                        if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_07_POCRet)    { _c=SetupDetectors.PocReturn(Symbol,Bars,_delta,_vp,tol);                        if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_08_LVNLong)   { _c=SetupDetectors.LvnLong  (Symbol,Bars,_delta,_vp,tol);                        if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_09_LVNShort)  { _c=SetupDetectors.LvnShort (Symbol,Bars,_delta,_vp,tol);                        if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_10_HVNRej)    { _c=SetupDetectors.HvnRej   (Symbol,Bars,_delta,_vp,tol);                        if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_11_StackBull) { _c=SetupDetectors.StackBull(Symbol,Bars,_delta,_vp,_fp,tol);                   if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_12_StackBear) { _c=SetupDetectors.StackBear(Symbol,Bars,_delta,_vp,_fp,tol);                   if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_13_PullStack) { _c=SetupDetectors.PullStack(Symbol,Bars,_delta,_vp,tol);                        if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_14_Spring)    { _c=SetupDetectors.Spring   (Symbol,Bars,_delta,_vp,tol);                        if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_15_Upthrust)  { _c=SetupDetectors.Upthrust (Symbol,Bars,_delta,_vp,tol);                        if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_16_SOS)       { _c=SetupDetectors.Sos      (Symbol,Bars,_delta,_vp,tol);                        if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_17_LPSY)      { _c=SetupDetectors.Lpsy     (Symbol,Bars,_delta,_vp,tol);                        if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_18_LiqSweep)  { _c=SetupDetectors.LiqSweep (Symbol,Bars,_delta,_vp,tol);                        if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_19_OBReturn)  { _c=SetupDetectors.ObReturn (Symbol,Bars,_delta,_vp,tol);                        if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_20_SMTDiv)    { _c=SetupDetectors.SmtDiv   (Symbol,Bars,_delta,_vp,0.0,tol);                   if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_21_Breaker)   { _c=SetupDetectors.Breaker  (Symbol,Bars,_delta,_vp,tol);                        if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_22_AMD)       { _c=SetupDetectors.Amd      (Symbol,Bars,_delta,_vp,tol);                        if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_23_UnfAuc)    { _c=SetupDetectors.UnfAuc   (Symbol,Bars,_delta,_vp,_fp,_atr,tol);              if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_24_PoorHL)    { _c=SetupDetectors.PoorHL   (Symbol,Bars,_delta,_vp,tol);                        if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
            if(EnableSetup_25_Iceberg)   { _c=SetupDetectors.Iceberg  (Symbol,Bars,_delta,_vp,_atr,tol);                  if(_c!=null)Consider(_c,htf,cvdDir,loc,ref best,ref bestScore); }
        }

        private void Consider(SetupCandidate c, HtfBias htf, TradeDir cvdDir, VpLoc loc, ref SetupCandidate best, ref int bestScore)
        {
            int score = 0;
            double price = Bars.ClosePrices.Last(1);
            double atrVal = _atr.Result.Last(0);

            // === ORIGINAL GATES (preserved) ===
            if (loc != VpLoc.None) score++;
            if (_delta.VolumeZ() >= VolZThreshold) score++;
            if (_delta.BullishDivergence() || _delta.BearishDivergence()) score++;
            if (c.AbsStars >= MinAbsorptionStars) score++;
            int dummy; var sess = _sess.Classify(Server.Time, out dummy);
            if (sess == Session.LdnMain || sess == Session.NyMain) score++;
            if ((_dE.Regime == CvdRegime.TrendConfirming && c.Direction == TradeDir.Long) ||
                (_dE.Regime == CvdRegime.Divergent && c.Direction == TradeDir.Short)) score++;

            // HTF gate: counter-trend gets score penalty, not hard block
            if (htf != HtfBias.Neutral)
            {
                bool aligned = (c.Direction == TradeDir.Long && htf == HtfBias.Bull) ||
                               (c.Direction == TradeDir.Short && htf == HtfBias.Bear);
                if (!aligned) score--;
            }
            // CVD gate: divergence is valid confirmation
            bool cvdOk = cvdDir == TradeDir.None || cvdDir == c.Direction ||
                         (c.Direction == TradeDir.Long  && _delta.BullishDivergence()) ||
                         (c.Direction == TradeDir.Short && _delta.BearishDivergence());
            if (!cvdOk) return;

            // === GOD-LEVEL ENHANCEMENT SCORING ===

            // M1 CVD confirmation (more accurate than tick proxy)
            double m1Cvd = _m1Delta.M1CVD(75);
            if ((c.Direction == TradeDir.Long && m1Cvd > 0) || (c.Direction == TradeDir.Short && m1Cvd < 0)) score++;

            // ICT: Premium/Discount alignment
            var pdZone = PremiumDiscountZone.Classify(Bars, 50);
            if (PremiumDiscountZone.Aligned(pdZone, c.Direction)) score++;

            // ICT: OTE Fibonacci zone
            if (_ote.InOTE(Bars, c.Direction, 20)) score++;

            // ICT/SMC: Displacement candle in recent bars
            bool bullDisp = _disp.IsBullishDisplacement(Bars, _atr.Result, 2.0);
            bool bearDisp = _disp.IsBearishDisplacement(Bars, _atr.Result, 2.0);
            if ((c.Direction == TradeDir.Long && bullDisp) || (c.Direction == TradeDir.Short && bearDisp)) score++;

            // SMC: Price inside FVG entry zone
            if (_disp.PriceInFVG(Bars, c.Direction, 15)) score++;

            // SMC: Inducement detected (manipulation phase complete)
            if (_ind.Detected(Bars, Symbol, c.Direction, 15)) score++;

            // SMC: Structure quality — strong highs/lows defending the level
            double sqScore = _sq.Score(Bars, c.Direction, 10);
            if (sqScore >= 0.6) score++;

            // Institutional levels confluence (PDH/PDL/PDC/Weekly/LOR/Round numbers)
            double instTol = atrVal > 0 ? atrVal * 0.5 : Symbol.PipSize * 10;
            if (_instLvl.IsNear(price, instTol)) score++;
            if (_instLvl.IsNearRoundNumber(price, Symbol)) score++;

            // ADX filter: trend strength matches model
            if (sess == Session.NyMain && _adxFilt.TrendStrong())  score++; // M1: ADX confirms trend
            if (sess == Session.LdnMain && _adxFilt.MarketRanging()) score++; // M2: ADX confirms range

            // Volume clock: institutional participation active
            if (_volClock.IsActive(Bars.TickVolumes.Last(1), Server.Time)) score++;

            // Multi-timeframe structure alignment (M15 + H1 added to H4+D1)
            score += _mtfStr.AlignmentScore(c.Direction, htf) / 2; // 0–2 additional points

            // Price action: trigger candle confirms direction
            if (_tc.Confirms(Bars, c.Direction)) score++;

            if (score > bestScore) { bestScore = score; best = c; }
        }

        private void RefreshDashboard()
        {
            int sastMin; var s=_sess.Classify(Server.Time,out sastMin); var htf=_htf.Combined();
            double slope=_delta.CvdSlope5(); var cvdDir=slope>0?TradeDir.Long:(slope<0?TradeDir.Short:TradeDir.None);
            double cls=Bars.ClosePrices.Last(1); var loc=_vp.LocationAt(cls,LocTolATR*10.0);
            _dash.Render(Symbol.Name,OperatingMode==OpMode.Manual?"MANUAL":"AUTO",_vp.State,s,htf,loc,cvdDir,false,0,0,0,Priority.None,_delta.Cvd,_delta.BarDelta,_delta.VolumeZ(),_vp.Poc,_vp.Vah,_vp.Val,_risk.DailyDDPct,_tradesToday);
            if(ShowVPLevels) _viz.DrawVPLevels(_vp.Poc,_vp.Vah,_vp.Val);
        }
    }
}
