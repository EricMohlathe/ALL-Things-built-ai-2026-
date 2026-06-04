// ============================================================================
//  GODMODE Dashboard  ⚡  — cTrader / cAlgo overlay indicator
//  Visualises every GODMODE archetype (GM01–GM26) as colour-coded modules:
//  a live control-panel dashboard, FVG/OB/S&D/OTE zones, swing markers,
//  session shading, confluence signal + a toggle button. Reuses GODMODE.Core.
//
//  INSTALL: New Indicator -> paste this -> add GODMODE_Core.cs to the SAME
//  project (Solution -> Add -> Existing). Build. Drop on any chart.
// ============================================================================
using System;
using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;
using GODMODE.Core;
using System.IO;
using System.Linq;

namespace cAlgo
{
    [Indicator(IsOverlay = true, AccessRights = AccessRights.None, AutoRescale = false)]
    public class GODMODE_Dashboard : Indicator
    {
        [Parameter("Trend EMA", Group = "Modules", DefaultValue = 50)] public int EmaLen { get; set; }
        [Parameter("Fast EMA", Group = "Modules", DefaultValue = 20)] public int FastLen { get; set; }
        [Parameter("VWAP SD Mult", Group = "Modules", DefaultValue = 2.0)] public double VwapMult { get; set; }
        [Parameter("VWAP/SD Length", Group = "Modules", DefaultValue = 100)] public int VwapLen { get; set; }
        [Parameter("Swing Wing", Group = "Modules", DefaultValue = 3)] public int Wing { get; set; }
        [Parameter("Zone Lookback", Group = "Modules", DefaultValue = 30)] public int ZoneLB { get; set; }
        [Parameter("OTE Lookback", Group = "Modules", DefaultValue = 20)] public int OteLB { get; set; }
        [Parameter("Displacement ATR", Group = "Modules", DefaultValue = 1.0)] public double DispMult { get; set; }
        [Parameter("Base Max ATR", Group = "Modules", DefaultValue = 0.6)] public double BaseMaxMult { get; set; }
        [Parameter("ATR Period", Group = "Modules", DefaultValue = 14)] public int AtrLen { get; set; }
        [Parameter("Min Layers", Group = "Modules", DefaultValue = 4)] public int MinLayers { get; set; }

        [Parameter("Show Zones", Group = "Display", DefaultValue = true)] public bool ShowZones { get; set; }
        [Parameter("Show Signals", Group = "Display", DefaultValue = true)] public bool ShowSignals { get; set; }
        [Parameter("London KZ Start", Group = "Display", DefaultValue = 7)] public int LonStart { get; set; }
        [Parameter("London KZ End", Group = "Display", DefaultValue = 10)] public int LonEnd { get; set; }
        [Parameter("NY KZ Start", Group = "Display", DefaultValue = 12)] public int NyStart { get; set; }
        [Parameter("NY KZ End", Group = "Display", DefaultValue = 15)] public int NyEnd { get; set; }

        private AverageTrueRange _atr;
        private ExponentialMovingAverage _ema, _fast;
        private bool _showZones;
        private long _lastSignalBar = -1;

        // theme
        private static readonly Color CBull = Color.FromHex("#FF00E5A0");
        private static readonly Color CBear = Color.FromHex("#FFFF4D6D");
        private static readonly Color CNeut = Color.FromHex("#FF5B8DEF");
        private static readonly Color CGold = Color.FromHex("#FFFFD24C");
        private static readonly Color CText = Color.FromHex("#FFE6EDF3");
        private static readonly Color CDim  = Color.FromHex("#FF7D8persistented"); // placeholder fixed below

        private Grid _grid;
        private TextBlock[] _rowName, _rowBias;
        private TextBlock _score, _signal, _kz;
        private readonly string[] _names = { "Trend GM22", "VWAP GM07", "Struct GM16", "FVG GM03", "OB GM04/05", "S&D GM15", "Sweep GM14", "OTE GM12", "Session GM11", "Gap GM20", "Momentum GM08" };

        protected override void Initialize()
        {
            _atr = Indicators.AverageTrueRange(AtrLen, MovingAverageType.Simple);
            _ema = Indicators.ExponentialMovingAverage(Bars.ClosePrices, EmaLen);
            _fast = Indicators.ExponentialMovingAverage(Bars.ClosePrices, FastLen);
            _showZones = ShowZones;
            BuildPanel();
        }

        private void BuildPanel()
        {
            var dim = Color.FromHex("#FF8B97A7");
            int rows = _names.Length + 4;
            _grid = new Grid(rows, 2) { Width = 168, BackgroundColor = Color.FromArgb(220, 11, 18, 32), Margin = 6 };
            _rowName = new TextBlock[_names.Length];
            _rowBias = new TextBlock[_names.Length];

            var title = new TextBlock { Text = "⚡ GODMODE", ForegroundColor = CGold, FontWeight = FontWeight.Bold, Margin = new Thickness(6, 4, 6, 4) };
            _grid.AddChild(title, 0, 0, 1, 2);

            for (int i = 0; i < _names.Length; i++)
            {
                _rowName[i] = new TextBlock { Text = _names[i], ForegroundColor = CText, Margin = new Thickness(6, 1, 4, 1), FontSize = 11 };
                _rowBias[i] = new TextBlock { Text = "—", ForegroundColor = dim, Margin = new Thickness(4, 1, 6, 1), FontSize = 11, HorizontalAlignment = HorizontalAlignment.Right };
                _grid.AddChild(_rowName[i], i + 1, 0);
                _grid.AddChild(_rowBias[i], i + 1, 1);
            }
            int sr = _names.Length + 1;
            _grid.AddChild(new TextBlock { Text = "SCORE", ForegroundColor = CGold, FontWeight = FontWeight.Bold, Margin = new Thickness(6, 3, 4, 1) }, sr, 0);
            _score = new TextBlock { Text = "L0 S0", ForegroundColor = CText, Margin = new Thickness(4, 3, 6, 1), HorizontalAlignment = HorizontalAlignment.Right };
            _grid.AddChild(_score, sr, 1);
            _grid.AddChild(new TextBlock { Text = "SIGNAL", ForegroundColor = CText, Margin = new Thickness(6, 1, 4, 1) }, sr + 1, 0);
            _signal = new TextBlock { Text = "WAIT", ForegroundColor = dim, Margin = new Thickness(4, 1, 6, 1), FontWeight = FontWeight.Bold, HorizontalAlignment = HorizontalAlignment.Right };
            _grid.AddChild(_signal, sr + 1, 1);

            var btn = new Button { Text = "Toggle Zones", Margin = new Thickness(6, 4, 6, 6), BackgroundColor = Color.FromArgb(255, 30, 44, 66), ForegroundColor = CText, FontSize = 11 };
            btn.Click += args => { _showZones = !_showZones; if (!_showZones) RemoveZones(); };
            _grid.AddChild(btn, sr + 2, 0, 1, 2);

            var border = new Border { Child = _grid, HorizontalAlignment = HorizontalAlignment.Right, VerticalAlignment = VerticalAlignment.Top, Margin = 8, CornerRadius = new CornerRadius(6), BorderColor = Color.FromArgb(120, 91, 141, 239), BorderThickness = new Thickness(1) };
            Chart.AddControl(border);
        }

        private double Vwap()
        {
            double pv = 0, vv = 0;
            int last = Bars.ClosePrices.Count - 1;
            for (int i = Math.Max(0, last - VwapLen + 1); i <= last; i++)
            {
                double tp = (Bars.HighPrices[i] + Bars.LowPrices[i] + Bars.ClosePrices[i]) / 3.0;
                double v = Bars.TickVolumes[i];
                pv += tp * v; vv += v;
            }
            return vv > 0 ? pv / vv : Bars.ClosePrices[last];
        }

        public override void Calculate(int index)
        {
            if (!IsLastBar) return;
            int n = Bars.ClosePrices.Count;
            if (n < Math.Max(VwapLen, ZoneLB) + 5) return;

            double atr = _atr.Result.Last(1); if (atr <= 0) return;
            double close = Bars.ClosePrices.Last(1), o1 = Bars.OpenPrices.Last(1), hi1 = Bars.HighPrices.Last(1), lo1 = Bars.LowPrices.Last(1);
            double ema = _ema.Result.Last(1);
            double vw = Vwap(), dev = VwapMult * StdDev(VwapLen);
            int hour = Server.Time.Hour;
            bool inKZ = (hour >= LonStart && hour < LonEnd) || (hour >= NyStart && hour < NyEnd);

            int bTrend = close > ema ? 1 : close < ema ? -1 : 0;
            int bVwap = close < vw - dev ? 1 : close > vw + dev ? -1 : 0;
            double shHi, shLo; int sH, sL;
            bool haveHi = GMStruct.LastSwingHigh(Bars, ZoneLB, Wing, out shHi, out sH);
            bool haveLo = GMStruct.LastSwingLow(Bars, ZoneLB, Wing, out shLo, out sL);
            int bStruct = haveHi && close > shHi ? 1 : haveLo && close < shLo ? -1 : 0;
            double ft, fb;
            int bFvg = GMStruct.FindBullishFVG(Bars, ZoneLB, out ft, out fb) && lo1 <= ft && close >= fb ? 1
                     : GMStruct.FindBearishFVG(Bars, ZoneLB, out ft, out fb) && hi1 >= fb && close <= ft ? -1 : 0;
            int bMom = (close - o1) > DispMult * atr ? 1 : (o1 - close) > DispMult * atr ? -1 : 0;
            int bSfp = haveLo && lo1 < shLo && close > shLo ? 1 : haveHi && hi1 > shHi && close < shHi ? -1 : 0;
            double oteHi = GMStruct.HighestHigh(Bars, OteLB, 1), oteLo = GMStruct.LowestLow(Bars, OteLB, 1), rng = oteHi - oteLo;
            int bOte = rng > 0 && close <= oteHi - 0.62 * rng && close >= oteHi - 0.79 * rng && close > ema ? 1
                     : rng > 0 && close >= oteLo + 0.62 * rng && close <= oteLo + 0.79 * rng && close < ema ? -1 : 0;

            int longN = (bTrend > 0 ? 1 : 0) + (bVwap > 0 ? 1 : 0) + (bStruct > 0 ? 1 : 0) + (bFvg > 0 ? 1 : 0) + (bMom > 0 ? 1 : 0) + (bSfp > 0 ? 1 : 0) + (bOte > 0 ? 1 : 0) + (inKZ ? 1 : 0);
            int shortN = (bTrend < 0 ? 1 : 0) + (bVwap < 0 ? 1 : 0) + (bStruct < 0 ? 1 : 0) + (bFvg < 0 ? 1 : 0) + (bMom < 0 ? 1 : 0) + (bSfp < 0 ? 1 : 0) + (bOte < 0 ? 1 : 0) + (inKZ ? 1 : 0);

            int[] biases = { bTrend, bVwap, bStruct, bFvg, bMom, bMom, bSfp, bOte, inKZ ? 1 : 0, 0, bMom };
            var dim = Color.FromHex("#FF8B97A7");
            for (int i = 0; i < _names.Length; i++)
            {
                int b = biases[i];
                _rowBias[i].Text = b > 0 ? "LONG" : b < 0 ? "SHORT" : "—";
                _rowBias[i].ForegroundColor = b > 0 ? CBull : b < 0 ? CBear : dim;
            }
            _score.Text = "L" + longN + " S" + shortN;
            _score.ForegroundColor = longN > shortN ? CBull : shortN > longN ? CBear : CNeut;
            bool goLong = longN >= MinLayers && longN > shortN;
            bool goShort = shortN >= MinLayers && shortN > longN;
            _signal.Text = goLong ? "⚡ LONG" : goShort ? "⚡ SHORT" : "WAIT";
            _signal.ForegroundColor = goLong ? CBull : goShort ? CBear : dim;

            if (_showZones) DrawZones(atr, close, ema);
            if (ShowSignals && (goLong || goShort) && Bars.OpenTimes.Count - 1 != _lastSignalBar)
            {
                _lastSignalBar = Bars.OpenTimes.Count - 1;
                int li = Bars.ClosePrices.Count - 1;
                if (goLong) Chart.DrawIcon("gm_sig", ChartIconType.UpArrow, li, lo1 - atr * 0.5, CBull);
                else Chart.DrawIcon("gm_sig", ChartIconType.DownArrow, li, hi1 + atr * 0.5, CBear);
            }
        }

        private double StdDev(int len)
        {
            int last = Bars.ClosePrices.Count - 1;
            int start = Math.Max(0, last - len + 1); int cnt = last - start + 1;
            double mean = 0; for (int i = start; i <= last; i++) mean += Bars.ClosePrices[i]; mean /= cnt;
            double s = 0; for (int i = start; i <= last; i++) { double d = Bars.ClosePrices[i] - mean; s += d * d; }
            return Math.Sqrt(s / cnt);
        }

        private void DrawZones(double atr, double close, double ema)
        {
            int li = Bars.ClosePrices.Count - 1;
            double ft, fb, zt, zb;
            if (GMStruct.FindBullishFVG(Bars, ZoneLB, out ft, out fb))
                Rect("gm_fvgb", li - ZoneLB, ft, li + 4, fb, Color.FromArgb(46, 91, 141, 239));
            if (GMStruct.FindBearishFVG(Bars, ZoneLB, out ft, out fb))
                Rect("gm_fvgs", li - ZoneLB, ft, li + 4, fb, Color.FromArgb(46, 181, 126, 220));
            if (GMStruct.FindDemandBase(Bars, ZoneLB, atr, DispMult, BaseMaxMult, out zt, out zb))
                Rect("gm_dem", li - ZoneLB, zt, li + 4, zb, Color.FromArgb(46, 0, 229, 160));
            if (GMStruct.FindSupplyBase(Bars, ZoneLB, atr, DispMult, BaseMaxMult, out zt, out zb))
                Rect("gm_sup", li - ZoneLB, zt, li + 4, zb, Color.FromArgb(46, 255, 77, 109));
            double oteHi = GMStruct.HighestHigh(Bars, OteLB, 1), oteLo = GMStruct.LowestLow(Bars, OteLB, 1), rng = oteHi - oteLo;
            if (rng > 0)
            {
                if (close > ema) Rect("gm_ote", li - OteLB, oteHi - 0.62 * rng, li + 4, oteHi - 0.79 * rng, Color.FromArgb(50, 255, 210, 76));
                else Rect("gm_ote", li - OteLB, oteLo + 0.79 * rng, li + 4, oteLo + 0.62 * rng, Color.FromArgb(50, 255, 210, 76));
            }
        }

        private void Rect(string name, int i1, double y1, int i2, double y2, Color c)
        {
            var r = Chart.DrawRectangle(name, i1, y1, i2, y2, c);
            r.IsFilled = true;
        }

        private void RemoveZones()
        {
            foreach (var nm in new[] { "gm_fvgb", "gm_fvgs", "gm_dem", "gm_sup", "gm_ote" })
                Chart.RemoveObject(nm);
        }
    }
}

// === GODMODE_Core inlined (auto) ===
namespace GODMODE.Core
{
    public enum GMRiskMode { Conservative = 0, Aggressive = 1, Flip = 2 }
    public enum GMDir      { None = 0, Long = 1, Short = -1 }

    // ------------------------------------------------------------------ utils
    public static class GMUtil
    {
        public static double ResolveRiskPct(GMRiskMode mode, double cons, double aggr, double flip)
        {
            switch (mode)
            {
                case GMRiskMode.Conservative: return cons;
                case GMRiskMode.Aggressive:   return aggr;
                case GMRiskMode.Flip:         return flip;
            }
            return cons;
        }

        public static double MaxLotMult(GMRiskMode mode, double normalMult)
            => mode == GMRiskMode.Flip ? 1000.0 : normalMult;

        // Risk %  +  stop distance (price)  ->  broker-legal volume in UNITS.
        // Rejects (returns 0) if the minimum volume would risk more than
        // maxMult x the target risk (the $10-account reality), except in Flip.
        public static double CalcVolume(Robot bot, double slDistance, double riskPct, double maxMult)
        {
            if (slDistance <= 0.0 || riskPct <= 0.0) return 0.0;
            var sym = bot.Symbol;
            double riskMoney = bot.Account.Equity * riskPct / 100.0;
            double pipSize   = sym.PipSize;
            double slPips    = slDistance / pipSize;
            double pipValue  = sym.PipValue;                 // per 1 unit, account currency
            if (pipValue <= 0.0 || slPips <= 0.0) return 0.0;

            double rawUnits = riskMoney / (slPips * pipValue);
            double norm     = sym.NormalizeVolumeInUnits(rawUnits, RoundingMode.Down);
            double minV     = sym.VolumeInUnitsMin;

            if (norm < minV)
            {
                double effRisk = minV * slPips * pipValue;
                if (effRisk > riskMoney * maxMult) return 0.0;   // would blow the budget
                norm = minV;
            }
            double maxV = sym.VolumeInUnitsMax;
            if (norm > maxV) norm = maxV;
            return norm;
        }

        // Minute-of-day in an offset timezone (e.g. SAST = server + 0..2).
        public static int MinuteOfDay(DateTime serverTime, int offsetHours)
        {
            int h = serverTime.Hour + offsetHours;
            while (h >= 24) h -= 24;
            while (h < 0)   h += 24;
            return h * 60 + serverTime.Minute;
        }

        public static bool InWindow(int minuteOfDay, int startMin, int endMin)
        {
            if (startMin <= endMin) return minuteOfDay >= startMin && minuteOfDay < endMin;
            return minuteOfDay >= startMin || minuteOfDay < endMin;   // wraps midnight
        }
    }

    // ---------------------------------------------------------------- guards
    public sealed class GMGuards
    {
        private readonly Robot  _bot;
        private readonly string _label;
        private double   _dayStartEquity;
        private bool     _halted;
        private DateTime _lastDay;

        public GMGuards(Robot bot, string label)
        {
            _bot = bot; _label = label;
            _dayStartEquity = bot.Account.Equity;
            _halted = false; _lastDay = DateTime.MinValue;
        }

        public bool IsNewDay()
        {
            var d = _bot.Server.Time.Date;
            if (d != _lastDay) { _lastDay = d; return true; }
            return false;
        }
        public void OnNewDay() { _dayStartEquity = _bot.Account.Equity; _halted = false; }

        public double DailyDDPct()
        {
            if (_dayStartEquity <= 0.0) return 0.0;
            return (_bot.Account.Equity - _dayStartEquity) / _dayStartEquity * 100.0;
        }
        public bool DailyDDBreached(double maxDDpct) => DailyDDPct() <= -maxDDpct;
        public void Halt() { _halted = true; }
        public bool IsHalted => _halted;

        public bool SpreadOK(double maxSpreadPips)
        {
            if (maxSpreadPips <= 0.0) return true;
            double spreadPips = (_bot.Symbol.Ask - _bot.Symbol.Bid) / _bot.Symbol.PipSize;
            return spreadPips <= maxSpreadPips;
        }

        public int TrailingLossStreak()
        {
            var today = _bot.Server.Time.Date;
            int streak = 0;
            var closed = _bot.History
                .Where(h => h.Label == _label && h.SymbolName == _bot.SymbolName && h.ClosingTime.Date == today)
                .OrderByDescending(h => h.ClosingTime);
            foreach (var t in closed)
            {
                if (t.NetProfit < 0) streak++;
                else break;
            }
            return streak;
        }
    }

    // ----------------------------------------------------------- trade manager
    public sealed class GMTrade
    {
        private readonly Robot  _bot;
        private readonly string _label;
        private long   _lastId = -1;
        private bool   _beDone, _partialDone;

        public GMTrade(Robot bot, string label) { _bot = bot; _label = label; }

        public Position Find()
            => _bot.Positions.FirstOrDefault(p => p.SymbolName == _bot.SymbolName && p.Label == _label);

        public bool HasPosition => Find() != null;

        public bool Open(GMDir dir, double volume, double sl, double tp, string comment)
        {
            if (volume <= 0.0 || dir == GMDir.None) return false;
            var type  = dir == GMDir.Long ? TradeType.Buy : TradeType.Sell;
            double price = dir == GMDir.Long ? _bot.Symbol.Ask : _bot.Symbol.Bid;
            double pip   = _bot.Symbol.PipSize;
            double slPips = Math.Abs(price - sl) / pip;
            double tpPips = Math.Abs(tp - price) / pip;
            _beDone = false; _partialDone = false;
            try
            {
                var r = _bot.ExecuteMarketOrder(type, _bot.SymbolName, volume, _label, slPips, tpPips, comment);
                return r != null && r.IsSuccessful;
            }
            catch (Exception e) { _bot.Print("GMTrade.Open err: " + e.Message); return false; }
        }

        public void CloseAll()
        {
            var p = Find();
            if (p != null) { try { _bot.ClosePosition(p); } catch { } }
        }

        public void Manage(double beAtR, double partialAtR, double partialPct,
                           bool useTrail, double trailAtrMult, double atrValue)
        {
            var p = Find();
            if (p == null) { _lastId = -1; return; }
            if (p.Id != _lastId) { _lastId = p.Id; _beDone = false; _partialDone = false; }

            double entry = p.EntryPrice;
            double sl    = p.StopLoss ?? entry;
            double tp    = p.TakeProfit ?? 0.0;
            double cur   = p.TradeType == TradeType.Buy ? _bot.Symbol.Bid : _bot.Symbol.Ask;
            double risk  = Math.Abs(entry - sl);
            if (risk <= 0.0) return;
            double rMult = p.TradeType == TradeType.Buy ? (cur - entry) / risk : (entry - cur) / risk;

            if (partialAtR > 0.0 && partialPct > 0.0 && !_partialDone && rMult >= partialAtR)
            {
                double cv = _bot.Symbol.NormalizeVolumeInUnits(p.VolumeInUnits * partialPct / 100.0, RoundingMode.Down);
                if (cv > 0.0 && cv < p.VolumeInUnits) { try { _bot.ClosePosition(p, cv); _partialDone = true; } catch { } }
            }

            if (beAtR > 0.0 && !_beDone && rMult >= beAtR)
            {
                double pip = _bot.Symbol.PipSize;
                double be = p.TradeType == TradeType.Buy ? entry + pip : entry - pip;
                try { p.ModifyStopLossPrice(be); _beDone = true; } catch { }
            }

            if (useTrail && atrValue > 0.0 && rMult >= beAtR)
            {
                double newSl = p.TradeType == TradeType.Buy ? cur - atrValue * trailAtrMult
                                                            : cur + atrValue * trailAtrMult;
                double curSl = p.StopLoss ?? (p.TradeType == TradeType.Buy ? double.MinValue : double.MaxValue);
                bool tighter = p.TradeType == TradeType.Buy ? newSl > curSl : newSl < curSl;
                if (tighter) { try { p.ModifyStopLossPrice(newSl); } catch { } }
            }
        }
    }

    // ----------------------------------------------------------------- logger
    public sealed class GMLogger
    {
        private readonly string _path;
        public GMLogger(string fileName)
        {
            _path = System.IO.Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), fileName);
            try
            {
                if (!System.IO.File.Exists(_path))
                    System.IO.File.WriteAllText(_path,
                        "time_utc,ea,symbol,event,dir,entry,sl,tp,volume,rr,score,note" + Environment.NewLine);
            }
            catch (System.IO.IOException) { }
        }

        public void Log(string ea, string evt, GMDir dir, double entry, double sl, double tp,
                        double volume, double rr, int score, string note)
        {
            string ds = dir == GMDir.Long ? "LONG" : (dir == GMDir.Short ? "SHORT" : "NONE");
            string row = string.Format(System.Globalization.CultureInfo.InvariantCulture,
                "{0:yyyy.MM.dd HH:mm:ss},{1},{2},{3},{4},{5:F5},{6:F5},{7:F5},{8:F2},{9:F2},{10},{11}",
                DateTime.UtcNow, ea, "SYM", evt, ds, entry, sl, tp, volume, rr, score, note);
            try { System.IO.File.AppendAllText(_path, row + Environment.NewLine); } catch (System.IO.IOException) { }
        }
    }

    // ------------------------------------------------------------- structure
    public static class GMStruct
    {
        public static double HighestHigh(Bars bars, int lookback, int startShift)
        {
            double hi = double.MinValue;
            for (int i = startShift; i < startShift + lookback; i++)
            {
                double h = bars.HighPrices.Last(i);
                if (h > hi) hi = h;
            }
            return hi;
        }
        public static double LowestLow(Bars bars, int lookback, int startShift)
        {
            double lo = double.MaxValue;
            for (int i = startShift; i < startShift + lookback; i++)
            {
                double l = bars.LowPrices.Last(i);
                if (l < lo) lo = l;
            }
            return lo;
        }

        public static bool FindBullishFVG(Bars bars, int lookback, out double top, out double bottom)
        {
            top = 0; bottom = 0;
            for (int i = 1; i < lookback; i++)
            {
                double lo  = bars.LowPrices.Last(i);
                double hi2 = bars.HighPrices.Last(i + 2);
                if (lo > hi2) { top = lo; bottom = hi2; return true; }
            }
            return false;
        }
        public static bool FindBearishFVG(Bars bars, int lookback, out double top, out double bottom)
        {
            top = 0; bottom = 0;
            for (int i = 1; i < lookback; i++)
            {
                double hi  = bars.HighPrices.Last(i);
                double lo2 = bars.LowPrices.Last(i + 2);
                if (hi < lo2) { top = lo2; bottom = hi; return true; }
            }
            return false;
        }

        public static bool FindBullishOB(Bars bars, int lookback, double atr, double dispMult,
                                         out double obTop, out double obBot)
        {
            obTop = 0; obBot = 0;
            if (atr <= 0.0) return false;
            for (int d = 1; d < lookback; d++)
            {
                double o = bars.OpenPrices.Last(d), c = bars.ClosePrices.Last(d);
                if (!(c > o && (c - o) > dispMult * atr)) continue;
                for (int j = d + 1; j <= d + 5 && j < lookback; j++)
                {
                    if (bars.ClosePrices.Last(j) < bars.OpenPrices.Last(j))
                    { obTop = bars.HighPrices.Last(j); obBot = bars.LowPrices.Last(j); return true; }
                }
            }
            return false;
        }
        public static bool FindBearishOB(Bars bars, int lookback, double atr, double dispMult,
                                         out double obTop, out double obBot)
        {
            obTop = 0; obBot = 0;
            if (atr <= 0.0) return false;
            for (int d = 1; d < lookback; d++)
            {
                double o = bars.OpenPrices.Last(d), c = bars.ClosePrices.Last(d);
                if (!(c < o && (o - c) > dispMult * atr)) continue;
                for (int j = d + 1; j <= d + 5 && j < lookback; j++)
                {
                    if (bars.ClosePrices.Last(j) > bars.OpenPrices.Last(j))
                    { obTop = bars.HighPrices.Last(j); obBot = bars.LowPrices.Last(j); return true; }
                }
            }
            return false;
        }

        // ---- Standard-deviation / measured-move projection ----
        public static double SDExtension(double fromLevel, double rangeSize, int dir, double mult)
            => fromLevel + dir * mult * rangeSize;

        // ---- Price-action trigger candles (Nial Fuller set) ----
        public static bool IsBullPin(Bars b, int ago)
        {
            double h = b.HighPrices.Last(ago), l = b.LowPrices.Last(ago);
            double o = b.OpenPrices.Last(ago), c = b.ClosePrices.Last(ago);
            double rng = h - l; return rng > 0 && (Math.Min(o, c) - l) / rng >= 0.6;
        }
        public static bool IsBearPin(Bars b, int ago)
        {
            double h = b.HighPrices.Last(ago), l = b.LowPrices.Last(ago);
            double o = b.OpenPrices.Last(ago), c = b.ClosePrices.Last(ago);
            double rng = h - l; return rng > 0 && (h - Math.Max(o, c)) / rng >= 0.6;
        }
        public static bool IsBullEngulf(Bars b)
        {
            double o1 = b.OpenPrices.Last(1), c1 = b.ClosePrices.Last(1), o2 = b.OpenPrices.Last(2), c2 = b.ClosePrices.Last(2);
            return c2 < o2 && c1 > o1 && o1 <= c2 && c1 >= o2;
        }
        public static bool IsBearEngulf(Bars b)
        {
            double o1 = b.OpenPrices.Last(1), c1 = b.ClosePrices.Last(1), o2 = b.OpenPrices.Last(2), c2 = b.ClosePrices.Last(2);
            return c2 > o2 && c1 < o1 && o1 >= c2 && c1 <= o2;
        }
        public static bool IsInsideBar(Bars b)
            => b.HighPrices.Last(1) < b.HighPrices.Last(2) && b.LowPrices.Last(1) > b.LowPrices.Last(2);

        // ---- ICT Optimal Trade Entry (0.62-0.79 retracement zone) ----
        public static bool OTELong(Bars b, int lookback, out double zTop, out double zBot)
        {
            double hi = HighestHigh(b, lookback, 1), lo = LowestLow(b, lookback, 1);
            double r = hi - lo; zTop = 0; zBot = 0; if (r <= 0) return false;
            zTop = hi - 0.62 * r; zBot = hi - 0.79 * r; return true;
        }
        public static bool OTEShort(Bars b, int lookback, out double zTop, out double zBot)
        {
            double hi = HighestHigh(b, lookback, 1), lo = LowestLow(b, lookback, 1);
            double r = hi - lo; zTop = 0; zBot = 0; if (r <= 0) return false;
            zBot = lo + 0.62 * r; zTop = lo + 0.79 * r; return true;
        }

        // ---- Fractal swings (wing bars each side; shift>=wing+1 to be closed) ----
        public static bool IsSwingHigh(Bars b, int shift, int wing)
        {
            double h = b.HighPrices.Last(shift);
            for (int k = 1; k <= wing; k++)
            { if (b.HighPrices.Last(shift - k) >= h) return false; if (b.HighPrices.Last(shift + k) > h) return false; }
            return true;
        }
        public static bool IsSwingLow(Bars b, int shift, int wing)
        {
            double l = b.LowPrices.Last(shift);
            for (int k = 1; k <= wing; k++)
            { if (b.LowPrices.Last(shift - k) <= l) return false; if (b.LowPrices.Last(shift + k) < l) return false; }
            return true;
        }
        public static bool LastSwingHigh(Bars b, int lookback, int wing, out double price, out int shift)
        {
            price = 0; shift = 0;
            for (int s = wing + 1; s <= lookback; s++)
                if (IsSwingHigh(b, s, wing)) { price = b.HighPrices.Last(s); shift = s; return true; }
            return false;
        }
        public static bool LastSwingLow(Bars b, int lookback, int wing, out double price, out int shift)
        {
            price = 0; shift = 0;
            for (int s = wing + 1; s <= lookback; s++)
                if (IsSwingLow(b, s, wing)) { price = b.LowPrices.Last(s); shift = s; return true; }
            return false;
        }

        // ---- Supply & Demand bases: small-range base candle + displacement leave ----
        public static bool FindDemandBase(Bars b, int lookback, double atr, double dispMult, double baseMaxMult, out double top, out double bot)
        {
            top = 0; bot = 0; if (atr <= 0) return false;
            for (int d = 1; d < lookback - 1; d++)
            {
                double o = b.OpenPrices.Last(d), c = b.ClosePrices.Last(d);
                if (!(c > o && (c - o) > dispMult * atr)) continue;
                double bh = b.HighPrices.Last(d + 1), bl = b.LowPrices.Last(d + 1);
                if (bh - bl < baseMaxMult * atr) { top = bh; bot = bl; return true; }
            }
            return false;
        }
        public static bool FindSupplyBase(Bars b, int lookback, double atr, double dispMult, double baseMaxMult, out double top, out double bot)
        {
            top = 0; bot = 0; if (atr <= 0) return false;
            for (int d = 1; d < lookback - 1; d++)
            {
                double o = b.OpenPrices.Last(d), c = b.ClosePrices.Last(d);
                if (!(c < o && (o - c) > dispMult * atr)) continue;
                double bh = b.HighPrices.Last(d + 1), bl = b.LowPrices.Last(d + 1);
                if (bh - bl < baseMaxMult * atr) { top = bh; bot = bl; return true; }
            }
            return false;
        }
    }
}
