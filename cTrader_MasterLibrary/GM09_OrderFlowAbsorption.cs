// GM09 Order-Flow Absorption + CVD divergence — GODMODE Master cBot Library (cTrader)
// GODMODE_OFEA core idea, standalone. Mirror of MT5 GM09.
// >>> TICK DATA ONLY. On m-bar backtests use tick-from-server / real ticks.
using System;
using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;
using GODMODE.Core;
using System.IO;
using System.Linq;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.FullAccess, AddIndicators = true)]
    public class GM09_OrderFlowAbsorption : Robot
    {
        [Parameter("Risk Mode", Group = "Risk", DefaultValue = GMRiskMode.Conservative)] public GMRiskMode RiskModeP { get; set; }
        [Parameter("Risk % Conservative", Group = "Risk", DefaultValue = 1.0)] public double RiskCons { get; set; }
        [Parameter("Risk % Aggressive", Group = "Risk", DefaultValue = 3.0)] public double RiskAggr { get; set; }
        [Parameter("Risk % Flip", Group = "Risk", DefaultValue = 8.0)] public double RiskFlip { get; set; }
        [Parameter("Max MinLot Risk Mult", Group = "Risk", DefaultValue = 3.0)] public double MaxLotMult { get; set; }

        [Parameter("Offset Hours", Group = "Session", DefaultValue = 0)] public int OffsetHours { get; set; }
        [Parameter("Use Session", Group = "Session", DefaultValue = true)] public bool UseSession { get; set; }
        [Parameter("Trade Start Hour", Group = "Session", DefaultValue = 7)] public int TradeStartHour { get; set; }
        [Parameter("Trade End Hour", Group = "Session", DefaultValue = 20)] public int TradeEndHour { get; set; }
        [Parameter("Force Close Hour", Group = "Session", DefaultValue = 22)] public int ForceCloseHour { get; set; }

        [Parameter("Delta Lookback", Group = "Entry", DefaultValue = 20)] public int DeltaLookback { get; set; }
        [Parameter("Vol Z Threshold", Group = "Entry", DefaultValue = 1.5)] public double VolZThr { get; set; }
        [Parameter("Use Absorption", Group = "Entry", DefaultValue = true)] public bool UseAbsorption { get; set; }
        [Parameter("Use CVD Divergence", Group = "Entry", DefaultValue = true)] public bool UseCVDDiv { get; set; }
        [Parameter("ATR Period", Group = "Entry", DefaultValue = 14)] public int ATRPeriod { get; set; }
        [Parameter("SL ATR Mult", Group = "Entry", DefaultValue = 1.0)] public double SLATRMult { get; set; }
        [Parameter("Reward:Risk", Group = "Entry", DefaultValue = 2.0)] public double RR { get; set; }
        [Parameter("Max Trades/Day", Group = "Entry", DefaultValue = 3)] public int MaxTrades { get; set; }

        [Parameter("BE at R", Group = "Manage", DefaultValue = 1.0)] public double BEatR { get; set; }
        [Parameter("Partial at R", Group = "Manage", DefaultValue = 1.0)] public double PartialAtR { get; set; }
        [Parameter("Partial %", Group = "Manage", DefaultValue = 50.0)] public double PartialPct { get; set; }
        [Parameter("Use Trail", Group = "Manage", DefaultValue = false)] public bool UseTrail { get; set; }
        [Parameter("Trail ATR Mult", Group = "Manage", DefaultValue = 1.5)] public double TrailATR { get; set; }

        [Parameter("Max Daily DD %", Group = "Guards", DefaultValue = 6.0)] public double MaxDD { get; set; }
        [Parameter("Max Consec Losses", Group = "Guards", DefaultValue = 3)] public int MaxConsec { get; set; }
        [Parameter("Max Spread Pips", Group = "Guards", DefaultValue = 0.0)] public double MaxSpread { get; set; }

        private GMTrade _trade; private GMGuards _guards; private GMLogger _log; private AverageTrueRange _atr; private int _tradesToday;
        private double _buy, _sell, _prevMid;
        private double[] _barDelta, _vol, _cvd; private int _filled, _N;

        protected override void OnStart()
        {
            _trade = new GMTrade(this, "GM09"); _guards = new GMGuards(this, "GM09");
            _log = new GMLogger("GODMODE_GM09_OrderFlow_log.csv");
            _atr = Indicators.AverageTrueRange(ATRPeriod, MovingAverageType.Simple);
            _N = Math.Max(DeltaLookback, 5);
            _barDelta = new double[_N]; _vol = new double[_N]; _cvd = new double[_N];
            Print("GM09 Order-Flow Absorption started. TICK DATA ONLY. RiskMode=" + RiskModeP);
        }

        private double RiskPct() => GMUtil.ResolveRiskPct(RiskModeP, RiskCons, RiskAggr, RiskFlip);
        private double LotMult() => GMUtil.MaxLotMult(RiskModeP, MaxLotMult);
        private double Atr() => _atr.Result.Last(1);
        private int H(DateTime t) => (t.Hour + OffsetHours) % 24;

        private double VolumeZ()
        {
            int n = _filled; if (n < 2) return 0;
            double mean = 0; for (int i = 0; i < n; i++) mean += _vol[i]; mean /= n;
            double sd = 0; for (int i = 0; i < n; i++) sd += (_vol[i] - mean) * (_vol[i] - mean);
            sd = Math.Sqrt(sd / n);
            return sd < 1e-9 ? 0 : (_vol[0] - mean) / sd;
        }

        protected override void OnTick()
        {
            double mid = (Symbol.Bid + Symbol.Ask) * 0.5;
            if (_prevMid > 0)
            {
                if (mid > _prevMid) _buy += 1.0;
                else if (mid < _prevMid) _sell += 1.0;
            }
            _prevMid = mid;
            _trade.Manage(BEatR, PartialAtR, PartialPct, UseTrail, TrailATR, Atr());
        }

        protected override void OnBar()
        {
            // snapshot just-closed bar's delta into the ring
            double bd = _buy - _sell;
            double tv = _buy + _sell;
            if (tv <= 0) tv = Bars.TickVolumes.Last(1);
            for (int i = _N - 1; i > 0; i--) { _barDelta[i] = _barDelta[i - 1]; _vol[i] = _vol[i - 1]; _cvd[i] = _cvd[i - 1]; }
            _barDelta[0] = bd; _vol[0] = tv; _cvd[0] = _cvd[1] + bd;
            _buy = 0; _sell = 0;
            if (_filled < _N) _filled++;

            var now = Server.Time;
            if (_guards.IsNewDay()) { _guards.OnNewDay(); _tradesToday = 0; }
            if (_guards.IsHalted) return;
            if (_guards.DailyDDBreached(MaxDD)) { _trade.CloseAll(); _guards.Halt(); _log.Log("GM09", "KILL_DD", GMDir.None, 0, 0, 0, 0, 0, 0, "daily DD"); return; }
            if (MaxConsec > 0 && _guards.TrailingLossStreak() >= MaxConsec) { _guards.Halt(); return; }
            if (H(now) >= ForceCloseHour) { _trade.CloseAll(); return; }
            if (UseSession && !GMUtil.InWindow(GMUtil.MinuteOfDay(now, OffsetHours), TradeStartHour * 60, TradeEndHour * 60)) return;
            if (_trade.HasPosition || _tradesToday >= MaxTrades) return;
            if (!_guards.SpreadOK(MaxSpread)) return;
            if (_filled < _N) return;

            double o = Bars.OpenPrices.Last(1), c = Bars.ClosePrices.Last(1);
            double volZ = VolumeZ(); double atr = Atr();
            if (atr <= 0) return;

            GMDir dir = GMDir.None; string note = "";
            if (UseAbsorption && volZ >= VolZThr)
            {
                if (bd < 0 && c >= o) { dir = GMDir.Long; note = "bull absorption"; }
                if (bd > 0 && c <= o) { dir = GMDir.Short; note = "bear absorption"; }
            }
            if (dir == GMDir.None && UseCVDDiv)
            {
                double lowestLow = double.MaxValue, highestHigh = double.MinValue, lowestCVD = double.MaxValue, highestCVD = double.MinValue;
                for (int i = 1; i <= _N; i++)
                {
                    double ll = Bars.LowPrices.Last(i), hh = Bars.HighPrices.Last(i);
                    if (ll < lowestLow) lowestLow = ll;
                    if (hh > highestHigh) highestHigh = hh;
                }
                for (int i = 0; i < _N; i++)
                {
                    if (_cvd[i] < lowestCVD) lowestCVD = _cvd[i];
                    if (_cvd[i] > highestCVD) highestCVD = _cvd[i];
                }
                double pt = Symbol.TickSize;
                bool bullDiv = Bars.LowPrices.Last(1) <= lowestLow + pt && _cvd[0] > lowestCVD + 1e-9;
                bool bearDiv = Bars.HighPrices.Last(1) >= highestHigh - pt && _cvd[0] < highestCVD - 1e-9;
                if (bullDiv) { dir = GMDir.Long; note = "CVD bull div"; }
                else if (bearDiv) { dir = GMDir.Short; note = "CVD bear div"; }
            }
            if (dir == GMDir.None) return;

            double entry = dir == GMDir.Long ? Symbol.Ask : Symbol.Bid;
            double sl = dir == GMDir.Long ? Bars.LowPrices.Last(1) - atr * SLATRMult : Bars.HighPrices.Last(1) + atr * SLATRMult;
            double risk = Math.Abs(entry - sl);
            if (risk <= 0) return;
            double tp = dir == GMDir.Long ? entry + risk * RR : entry - risk * RR;

            double vol = GMUtil.CalcVolume(this, risk, RiskPct(), LotMult());
            if (vol <= 0) { _log.Log("GM09", "SKIP_SIZE", dir, entry, sl, tp, 0, RR, 0, "min lot risk too high"); return; }

            if (_trade.Open(dir, vol, sl, tp, "GM09_OF"))
            { _tradesToday++; _log.Log("GM09", "ENTRY", dir, entry, sl, tp, vol, RR, 1, note); }
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
