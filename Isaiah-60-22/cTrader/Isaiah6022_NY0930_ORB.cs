// ---------------------------------------------------------------------------
//  Isaiah6022_NY0930_ORB.cs
//
//  Strategy 01 — The 9:30 New York Opening Range.  cTrader / cAlgo cBot.
//
//  Mark the 09:30-09:35 NY five-minute candle. Trade the body close beyond it.
//  Stop at the opposite boundary. Entries close at 10:30 NY.
//
//  The default entry model is the DIRECT break, not the retest. The retest is
//  provided so you can measure it yourself: across 165,336 tested trades it
//  LOWERED the win rate (33.0% -> 31.9% on holdout, p < 0.001).
//
//  CLOCK. The robot declares TimeZone = UTC, so Server.Time is UTC and the
//  conversion to New York uses the real US daylight-saving rule. Unlike the
//  MT5 build there is no broker-offset input to get wrong. This is the one
//  place where cTrader is simply better for session strategies.
//
//  JOURNAL. Writes a CSV with the same schema as the MT5 build, so the same
//  srf_forensics.py grades output from either platform — and so you can
//  diff the two to find execution differences rather than argue about them.
//  Requires AccessRights.FullAccess for file output.
//
//  Install: cTrader -> Automate -> New cBot -> paste -> Build (F6).
// ---------------------------------------------------------------------------

using System;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace cAlgo.Robots
{
    public enum OrbModel
    {
        BreakDirect,    // Body close beyond the range. Enter at that close. DEFAULT
        BreakFvg,       // Break, then enter on a fair value gap in the displacement
        Retest,         // Break -> pullback to the boundary -> rejection close
        Trap            // Break out -> close back inside -> close back out
    }

    public enum BiasMode
    {
        Off,
        HtfEma,
        PrevDay,
        RangeCandle
    }

    public enum ExitMode
    {
        FixedR,
        TimeOnly,
        RThenTime,
        AtrTrail
    }

    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.FullAccess, AddIndicators = true)]
    public class Isaiah6022_NY0930_ORB : Robot
    {
        // ── 1. Model and timeframes ────────────────────────────────────────
        [Parameter("Entry model", Group = "1. Model", DefaultValue = OrbModel.BreakDirect)]
        public OrbModel Model { get; set; }

        [Parameter("Range timeframe", Group = "1. Model", DefaultValue = "Minute5")]
        public TimeFrame RangeTf { get; set; }

        [Parameter("Entry timeframe", Group = "1. Model", DefaultValue = "Minute1")]
        public TimeFrame EntryTf { get; set; }

        // ── 2. Clock, all times New York local ─────────────────────────────
        [Parameter("Range start hour (NY)", Group = "2. Clock", DefaultValue = 9, MinValue = 0, MaxValue = 23)]
        public int RangeStartHH { get; set; }

        [Parameter("Range start minute (NY)", Group = "2. Clock", DefaultValue = 30, MinValue = 0, MaxValue = 59)]
        public int RangeStartMM { get; set; }

        [Parameter("Range end hour (NY)", Group = "2. Clock", DefaultValue = 9, MinValue = 0, MaxValue = 23)]
        public int RangeEndHH { get; set; }

        [Parameter("Range end minute (NY)", Group = "2. Clock", DefaultValue = 35, MinValue = 0, MaxValue = 59)]
        public int RangeEndMM { get; set; }

        [Parameter("Entry window start hour (NY)", Group = "2. Clock", DefaultValue = 9)]
        public int TradeStartHH { get; set; }

        [Parameter("Entry window start minute (NY)", Group = "2. Clock", DefaultValue = 35)]
        public int TradeStartMM { get; set; }

        [Parameter("Entry window end hour (NY)", Group = "2. Clock", DefaultValue = 10)]
        public int TradeEndHH { get; set; }

        [Parameter("Entry window end minute (NY)", Group = "2. Clock", DefaultValue = 30)]
        public int TradeEndMM { get; set; }

        [Parameter("Force-flat hour (NY)", Group = "2. Clock", DefaultValue = 15)]
        public int FlatHH { get; set; }

        [Parameter("Force-flat minute (NY)", Group = "2. Clock", DefaultValue = 55)]
        public int FlatMM { get; set; }

        [Parameter("Trade Monday", Group = "2. Clock", DefaultValue = true)]    public bool TradeMon { get; set; }
        [Parameter("Trade Tuesday", Group = "2. Clock", DefaultValue = true)]   public bool TradeTue { get; set; }
        [Parameter("Trade Wednesday", Group = "2. Clock", DefaultValue = true)] public bool TradeWed { get; set; }
        [Parameter("Trade Thursday", Group = "2. Clock", DefaultValue = true)]  public bool TradeThu { get; set; }
        [Parameter("Trade Friday", Group = "2. Clock", DefaultValue = true)]    public bool TradeFri { get; set; }

        // ── 3. Signal rules ────────────────────────────────────────────────
        [Parameter("Break must be a body close", Group = "3. Signal", DefaultValue = true)]
        public bool RequireBodyClose { get; set; }

        [Parameter("Break buffer (pips)", Group = "3. Signal", DefaultValue = 0.0)]
        public double BreakBufferPips { get; set; }

        [Parameter("Max bars to trigger", Group = "3. Signal", DefaultValue = 60)]
        public int MaxBarsToTrigger { get; set; }

        [Parameter("FVG lookback bars", Group = "3. Signal", DefaultValue = 3)]
        public int FvgLookback { get; set; }

        [Parameter("Min FVG height (pips)", Group = "3. Signal", DefaultValue = 0.0)]
        public double MinFvgPips { get; set; }

        [Parameter("Retest max bars after break", Group = "3. Signal", DefaultValue = 20)]
        public int RetestMaxBars { get; set; }

        [Parameter("Min range (pips), 0 = off", Group = "3. Signal", DefaultValue = 0.0)]
        public double MinRangePips { get; set; }

        [Parameter("Max range as x ATR, 0 = off", Group = "3. Signal", DefaultValue = 3.0)]
        public double MaxRangeAtr { get; set; }

        // ── 4. Bias ────────────────────────────────────────────────────────
        [Parameter("Bias filter", Group = "4. Bias", DefaultValue = BiasMode.Off)]
        public BiasMode Bias { get; set; }

        [Parameter("Bias timeframe", Group = "4. Bias", DefaultValue = "Hour4")]
        public TimeFrame BiasTf { get; set; }

        [Parameter("Bias EMA period", Group = "4. Bias", DefaultValue = 50)]
        public int BiasEmaPeriod { get; set; }

        [Parameter("Bias blocks counter-trend", Group = "4. Bias", DefaultValue = true)]
        public bool BiasBlocksCounter { get; set; }

        // ── 5. Stops and targets ───────────────────────────────────────────
        [Parameter("Exit mode", Group = "5. Exits", DefaultValue = ExitMode.FixedR)]
        public ExitMode Exit { get; set; }

        [Parameter("Target in R", Group = "5. Exits", DefaultValue = 2.0, MinValue = 0.1)]
        public double TargetR { get; set; }

        [Parameter("Stop buffer (pips)", Group = "5. Exits", DefaultValue = 0.0)]
        public double StopBufferPips { get; set; }

        [Parameter("ATR period", Group = "5. Exits", DefaultValue = 14)]
        public int AtrPeriod { get; set; }

        [Parameter("Min stop as x ATR", Group = "5. Exits", DefaultValue = 0.25)]
        public double MinStopAtr { get; set; }

        [Parameter("Max stop as x ATR", Group = "5. Exits", DefaultValue = 3.0)]
        public double MaxStopAtr { get; set; }

        [Parameter("Break-even at R, 0 = off", Group = "5. Exits", DefaultValue = 0.0)]
        public double BreakevenAtR { get; set; }

        [Parameter("Partial at R, 0 = off", Group = "5. Exits", DefaultValue = 0.0)]
        public double PartialAtR { get; set; }

        [Parameter("Partial percent", Group = "5. Exits", DefaultValue = 50.0)]
        public double PartialPercent { get; set; }

        [Parameter("ATR trail multiple", Group = "5. Exits", DefaultValue = 1.5)]
        public double AtrTrailMult { get; set; }

        // ── 6. Risk kernel ─────────────────────────────────────────────────
        [Parameter("Risk % of equity", Group = "6. Risk", DefaultValue = 0.5, MinValue = 0.01, MaxValue = 5.0)]
        public double RiskPercent { get; set; }

        [Parameter("Max daily loss %", Group = "6. Risk", DefaultValue = 2.0)]
        public double MaxDailyLossPct { get; set; }

        [Parameter("Max total drawdown %", Group = "6. Risk", DefaultValue = 10.0)]
        public double MaxTotalDdPct { get; set; }

        [Parameter("Max trades per session", Group = "6. Risk", DefaultValue = 2)]
        public int MaxTradesPerDay { get; set; }

        [Parameter("Max consecutive losses", Group = "6. Risk", DefaultValue = 4)]
        public int MaxConsecLosses { get; set; }

        [Parameter("Max spread (pips), 0 = off", Group = "6. Risk", DefaultValue = 3.0)]
        public double MaxSpreadPips { get; set; }

        [Parameter("Max spread as % of stop", Group = "6. Risk", DefaultValue = 10.0)]
        public double MaxSpreadVsStop { get; set; }

        // ── 7. Journal ─────────────────────────────────────────────────────
        [Parameter("Write journal CSV", Group = "7. Journal", DefaultValue = true)]
        public bool WriteJournal { get; set; }

        [Parameter("Journal file name", Group = "7. Journal", DefaultValue = "I22_ORB_journal.csv")]
        public string JournalFile { get; set; }

        [Parameter("Run tag — CHANGE EVERY RUN", Group = "7. Journal", DefaultValue = "orb_direct_ct_v1")]
        public string RunTag { get; set; }

        [Parameter("Show dashboard", Group = "7. Journal", DefaultValue = true)]
        public bool ShowDashboard { get; set; }

        [Parameter("Draw range lines", Group = "7. Journal", DefaultValue = true)]
        public bool DrawObjects { get; set; }

        // ── State ──────────────────────────────────────────────────────────
        private const string Label = "I22_ORB";

        private Bars _rangeBars, _entryBars, _biasBars;
        private AverageTrueRange _atr;
        private ExponentialMovingAverage _biasEma;

        private string _dayKey = "";
        private double _rangeHigh, _rangeLow;
        private bool _rangeReady, _daySkipped;
        private string _skipReason = "";
        private double _rangeAtr;
        private int _rangeDir;
        private int _tradesToday, _consecLosses;
        private double _dayStartEquity, _peakEquity;
        private bool _haltedToday, _haltedTotal;

        private int _breakDir;
        private double _breakLevel;
        private int _barsSinceBreak;
        private bool _trapArmed;
        private int _trapDir;

        private DateTime _lastEntryBarTime = DateTime.MinValue;
        private DateTime _lastRangeBarTime = DateTime.MinValue;

        // live position bookkeeping
        private Position _pos;
        private double _entryPrice, _initialSl, _initialTp, _riskPips, _entrySpreadPips, _entryVolume;
        private DateTime _entryTimeNy;
        private string _entryDayKey = "";
        private double _mfePips, _maePips;
        private string _biasAtEntry = "OFF";
        private bool _bePlaced, _partialDone;
        private int _entryBarIndex;

        private string _journalPath;

        // ══════════════════════════════════════════════════════════════════
        //  NEW YORK CLOCK
        //  Server.Time is UTC because the Robot attribute says so. EDT runs
        //  from the 2nd Sunday in March to the 1st Sunday in November.
        // ══════════════════════════════════════════════════════════════════
        private static DateTime NthWeekdayOfMonth(int year, int month, DayOfWeek weekday, int nth)
        {
            var first = new DateTime(year, month, 1, 0, 0, 0, DateTimeKind.Utc);
            int delta = ((int)weekday - (int)first.DayOfWeek + 7) % 7;
            return first.AddDays(delta + (nth - 1) * 7);
        }

        private static bool IsUsDaylightTime(DateTime utc)
        {
            // 02:00 local standard = 07:00 UTC on the second Sunday in March
            var dstStart = NthWeekdayOfMonth(utc.Year, 3, DayOfWeek.Sunday, 2).AddHours(7);
            // 02:00 local daylight = 06:00 UTC on the first Sunday in November
            var dstEnd = NthWeekdayOfMonth(utc.Year, 11, DayOfWeek.Sunday, 1).AddHours(6);
            return utc >= dstStart && utc < dstEnd;
        }

        private static DateTime ToNy(DateTime utc)
        {
            return utc.AddHours(IsUsDaylightTime(utc) ? -4 : -5);
        }

        private DateTime NowNy => ToNy(Server.Time);

        private static int MinuteOfDay(DateTime ny) => ny.Hour * 60 + ny.Minute;

        private static string DayKeyOf(DateTime ny) => ny.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);

        private static string StampOf(DateTime ny) => ny.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture);

        private int RangeStartMin => RangeStartHH * 60 + RangeStartMM;
        private int RangeEndMin => RangeEndHH * 60 + RangeEndMM;
        private int TradeStartMin => TradeStartHH * 60 + TradeStartMM;
        private int TradeEndMin => TradeEndHH * 60 + TradeEndMM;
        private int FlatMin => FlatHH * 60 + FlatMM;
        private bool RangeWraps => RangeEndMin <= RangeStartMin;

        private static bool InWindow(int nowMin, int startMin, int endMin)
        {
            if (startMin == endMin) return false;
            if (startMin < endMin) return nowMin >= startMin && nowMin < endMin;
            return nowMin >= startMin || nowMin < endMin;   // wraps midnight
        }

        // A range that wraps midnight belongs to the session that FOLLOWS it.
        private string RangeDayKey(DateTime ny)
        {
            if (!RangeWraps) return DayKeyOf(ny);
            return MinuteOfDay(ny) >= RangeStartMin ? DayKeyOf(ny.AddDays(1)) : DayKeyOf(ny);
        }

        private bool IsTradeDay(DayOfWeek d)
        {
            switch (d)
            {
                case DayOfWeek.Monday: return TradeMon;
                case DayOfWeek.Tuesday: return TradeTue;
                case DayOfWeek.Wednesday: return TradeWed;
                case DayOfWeek.Thursday: return TradeThu;
                case DayOfWeek.Friday: return TradeFri;
                default: return false;
            }
        }

        // ══════════════════════════════════════════════════════════════════
        //  LIFECYCLE
        // ══════════════════════════════════════════════════════════════════
        protected override void OnStart()
        {
            _rangeBars = MarketData.GetBars(RangeTf);
            _entryBars = MarketData.GetBars(EntryTf);
            _biasBars = MarketData.GetBars(BiasTf);

            _atr = Indicators.AverageTrueRange(_rangeBars, AtrPeriod, MovingAverageType.Simple);
            if (Bias == BiasMode.HtfEma)
                _biasEma = Indicators.ExponentialMovingAverage(_biasBars.ClosePrices, BiasEmaPeriod);

            _peakEquity = Account.Equity;
            _dayStartEquity = Account.Equity;

            _journalPath = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), JournalFile);
            EnsureJournalHeader();

            Positions.Closed += OnPositionClosed;

            Print("Isaiah 60:22 | NY_ORB_0930 / {0} started. NY time now {1}. Journal: {2}",
                  Model, StampOf(NowNy), WriteJournal ? _journalPath : "(off)");
            Print("Isaiah 60:22 | range {0:00}:{1:00}-{2:00}:{3:00} NY, entries {4:00}:{5:00}-{6:00}:{7:00} NY, flat {8:00}:{9:00} NY",
                  RangeStartHH, RangeStartMM, RangeEndHH, RangeEndMM,
                  TradeStartHH, TradeStartMM, TradeEndHH, TradeEndMM, FlatHH, FlatMM);
        }

        protected override void OnStop()
        {
            Positions.Closed -= OnPositionClosed;
        }

        // ══════════════════════════════════════════════════════════════════
        //  MAIN LOOP
        // ══════════════════════════════════════════════════════════════════
        protected override void OnTick()
        {
            var ny = NowNy;
            int nowMin = MinuteOfDay(ny);

            // roll the session
            string key = RangeDayKey(ny);
            if (key != _dayKey) ResetSession(key);

            _pos = Positions.Find(Label, SymbolName);

            // force flat outside the holding window
            if (_pos != null && !InWindow(nowMin, TradeStartMin, FlatMin))
            {
                ClosePosition(_pos);
                Print("Isaiah 60:22 | flattened: force-flat time reached");
                DrawDashboard();
                return;
            }

            if (_pos != null)
            {
                TrackExcursion();
                ManagePosition();
                DrawDashboard();
                return;
            }

            if (RiskKernelBlocks()) { DrawDashboard(); return; }
            if (!IsTradeDay(ny.DayOfWeek)) { DrawDashboard(); return; }

            // build / close the range on closed range-TF bars
            if (InWindow(nowMin, RangeStartMin, RangeEndMin)) { UpdateRange(); DrawDashboard(); return; }
            FinaliseRange();

            if (!_rangeReady || _daySkipped) { DrawDashboard(); return; }
            if (!InWindow(nowMin, TradeStartMin, TradeEndMin)) { DrawDashboard(); return; }

            // one decision per closed entry bar
            var lastEntryOpen = _entryBars.OpenTimes.Last(1);
            if (lastEntryOpen == _lastEntryBarTime) { DrawDashboard(); return; }
            _lastEntryBarTime = lastEntryOpen;

            EvaluateSignal();
            DrawDashboard();
        }

        // ══════════════════════════════════════════════════════════════════
        //  SESSION AND RANGE
        // ══════════════════════════════════════════════════════════════════
        private void ResetSession(string newKey)
        {
            _dayKey = newKey;
            _rangeHigh = 0; _rangeLow = 0;
            _rangeReady = false; _daySkipped = false; _skipReason = "";
            _rangeAtr = 0; _rangeDir = 0;
            _tradesToday = 0;
            _haltedToday = false;
            _dayStartEquity = Account.Equity;
            _lastRangeBarTime = DateTime.MinValue;
            ResetSignalState();

            if (DrawObjects)
            {
                Chart.RemoveObject("I22_RangeHigh");
                Chart.RemoveObject("I22_RangeLow");
            }
        }

        private void ResetSignalState()
        {
            _breakDir = 0;
            _breakLevel = 0;
            _barsSinceBreak = 0;
            _trapArmed = false;
            _trapDir = 0;
        }

        private void UpdateRange()
        {
            var barTime = _rangeBars.OpenTimes.Last(1);
            if (barTime == _lastRangeBarTime) return;      // one pass per closed bar
            _lastRangeBarTime = barTime;

            var barNy = ToNy(barTime);
            if (!InWindow(MinuteOfDay(barNy), RangeStartMin, RangeEndMin)) return;
            if (RangeDayKey(barNy) != _dayKey) return;

            double h = _rangeBars.HighPrices.Last(1);
            double l = _rangeBars.LowPrices.Last(1);
            double o = _rangeBars.OpenPrices.Last(1);
            double c = _rangeBars.ClosePrices.Last(1);

            if (_rangeHigh == 0 || h > _rangeHigh) _rangeHigh = h;
            if (_rangeLow == 0 || l < _rangeLow) _rangeLow = l;

            if (c > o) _rangeDir = 1;
            else if (c < o) _rangeDir = -1;
        }

        private void FinaliseRange()
        {
            if (_rangeReady || _rangeHigh <= 0 || _rangeLow <= 0) return;

            _rangeReady = true;
            _rangeAtr = _atr.Result.Last(1);

            double rangePips = (_rangeHigh - _rangeLow) / Symbol.PipSize;
            double atrPips = _rangeAtr > 0 ? _rangeAtr / Symbol.PipSize : 0;

            if (MinRangePips > 0 && rangePips < MinRangePips)
            {
                _daySkipped = true;
                _skipReason = string.Format("range {0:F1} pips < min {1:F1}", rangePips, MinRangePips);
            }
            else if (MaxRangeAtr > 0 && atrPips > 0 && rangePips > MaxRangeAtr * atrPips)
            {
                _daySkipped = true;
                _skipReason = string.Format("range {0:F2} x ATR > max {1:F2}", rangePips / atrPips, MaxRangeAtr);
            }

            if (DrawObjects)
            {
                Chart.DrawHorizontalLine("I22_RangeHigh", _rangeHigh, Color.DodgerBlue, 1, LineStyle.Dots);
                Chart.DrawHorizontalLine("I22_RangeLow", _rangeLow, Color.OrangeRed, 1, LineStyle.Dots);
            }

            Print("Isaiah 60:22 | {0} range set  H={1}  L={2}  ({3:F1} pips, {4:F2} x ATR){5}",
                  _dayKey, Math.Round(_rangeHigh, Symbol.Digits), Math.Round(_rangeLow, Symbol.Digits),
                  rangePips, atrPips > 0 ? rangePips / atrPips : 0,
                  _daySkipped ? "  SKIPPED: " + _skipReason : "");
        }

        // ══════════════════════════════════════════════════════════════════
        //  BIAS
        // ══════════════════════════════════════════════════════════════════
        private int CurrentBias(out string label)
        {
            label = "OFF";
            switch (Bias)
            {
                case BiasMode.Off:
                    return 0;

                case BiasMode.HtfEma:
                {
                    if (_biasEma == null) { label = "NA"; return 0; }
                    double e1 = _biasEma.Result.Last(1);
                    double e2 = _biasEma.Result.Last(2);
                    double c1 = _biasBars.ClosePrices.Last(1);
                    if (double.IsNaN(e1) || double.IsNaN(e2)) { label = "NA"; return 0; }

                    if (c1 > e1 && e1 >= e2) { label = "BULL"; return 1; }
                    if (c1 < e1 && e1 <= e2) { label = "BEAR"; return -1; }
                    label = "FLAT";
                    return 0;
                }

                case BiasMode.PrevDay:
                {
                    var daily = MarketData.GetBars(TimeFrame.Daily);
                    double ph = daily.HighPrices.Last(1);
                    double pl = daily.LowPrices.Last(1);
                    if (ph <= pl) { label = "NA"; return 0; }
                    double mid = (ph + pl) / 2.0;
                    if (Symbol.Bid > mid) { label = "BULL"; return 1; }
                    if (Symbol.Bid < mid) { label = "BEAR"; return -1; }
                    label = "FLAT";
                    return 0;
                }

                case BiasMode.RangeCandle:
                    if (_rangeDir > 0) { label = "BULL"; return 1; }
                    if (_rangeDir < 0) { label = "BEAR"; return -1; }
                    label = "FLAT";
                    return 0;
            }
            return 0;
        }

        // ══════════════════════════════════════════════════════════════════
        //  SIGNAL
        // ══════════════════════════════════════════════════════════════════
        private int DetectBreak(out double level)
        {
            level = 0;
            double c = _entryBars.ClosePrices.Last(1);
            double h = _entryBars.HighPrices.Last(1);
            double l = _entryBars.LowPrices.Last(1);
            double buf = BreakBufferPips * Symbol.PipSize;

            double upTest = RequireBodyClose ? c : h;
            double dnTest = RequireBodyClose ? c : l;

            if (upTest > _rangeHigh + buf) { level = _rangeHigh; return 1; }
            if (dnTest < _rangeLow - buf) { level = _rangeLow; return -1; }
            return 0;
        }

        // Bullish FVG: low[i] > high[i+2]. Bearish: high[i] < low[i+2].
        // Returns the near edge of the gap — the level price must trade back to.
        private double FindFvg(int dir)
        {
            double minH = MinFvgPips * Symbol.PipSize;

            for (int i = 1; i <= FvgLookback; i++)
            {
                double l0 = _entryBars.LowPrices.Last(i);
                double h0 = _entryBars.HighPrices.Last(i);
                double l2 = _entryBars.LowPrices.Last(i + 2);
                double h2 = _entryBars.HighPrices.Last(i + 2);

                if (dir > 0 && l0 > h2 && (l0 - h2) >= minH) return l0;
                if (dir < 0 && h0 < l2 && (l2 - h0) >= minH) return h0;
            }
            return 0;
        }

        private bool RetestRejection(int dir, double level)
        {
            double o = _entryBars.OpenPrices.Last(1);
            double c = _entryBars.ClosePrices.Last(1);
            double h = _entryBars.HighPrices.Last(1);
            double l = _entryBars.LowPrices.Last(1);

            if (dir > 0) return l <= level && c > level && c > o;
            return h >= level && c < level && c < o;
        }

        private void EvaluateSignal()
        {
            if (_breakDir != 0) _barsSinceBreak++;

            string biasLbl;
            int bias = CurrentBias(out biasLbl);

            // 1. the break that arms the setup
            if (_breakDir == 0)
            {
                double level;
                int dir = DetectBreak(out level);
                if (dir != 0)
                {
                    _breakDir = dir;
                    _breakLevel = level;
                    _barsSinceBreak = 0;
                    Print("Isaiah 60:22 | {0} break of {1}",
                          dir > 0 ? "upside" : "downside", Math.Round(level, Symbol.Digits));
                }
            }

            if (_breakDir == 0) return;

            if (MaxBarsToTrigger > 0 && _barsSinceBreak > MaxBarsToTrigger)
            {
                Print("Isaiah 60:22 | setup expired without a trigger");
                ResetSignalState();
                return;
            }

            // 2. bias veto
            if (BiasBlocksCounter && bias != 0 && bias != _breakDir)
            {
                Print("Isaiah 60:22 | entry vetoed by bias ({0} vs {1} break)",
                      biasLbl, _breakDir > 0 ? "upside" : "downside");
                ResetSignalState();
                return;
            }

            // 3. model trigger
            int tradeDir = _breakDir;
            double stopPrice = tradeDir > 0 ? _rangeLow : _rangeHigh;
            bool fire = false;
            string trigger = "";

            switch (Model)
            {
                case OrbModel.BreakDirect:
                    fire = _barsSinceBreak == 0;      // the break bar IS the trigger
                    trigger = "direct_break";
                    break;

                case OrbModel.BreakFvg:
                {
                    double fvg = FindFvg(tradeDir);
                    if (fvg > 0)
                    {
                        double px = tradeDir > 0 ? Symbol.Ask : Symbol.Bid;
                        if ((tradeDir > 0 && px <= fvg) || (tradeDir < 0 && px >= fvg))
                        {
                            fire = true;
                            trigger = "break_fvg";
                        }
                    }
                    break;
                }

                case OrbModel.Retest:
                    if (_barsSinceBreak >= 1 && _barsSinceBreak <= RetestMaxBars &&
                        RetestRejection(tradeDir, _breakLevel))
                    {
                        fire = true;
                        trigger = "retest_rejection";
                        stopPrice = tradeDir > 0
                            ? _entryBars.LowPrices.Last(1)
                            : _entryBars.HighPrices.Last(1);
                    }
                    break;

                case OrbModel.Trap:
                {
                    double c = _entryBars.ClosePrices.Last(1);
                    if (!_trapArmed)
                    {
                        if (_barsSinceBreak >= 1 && c < _rangeHigh && c > _rangeLow)
                        {
                            _trapArmed = true;
                            _trapDir = -_breakDir;
                            Print("Isaiah 60:22 | trap armed: break failed back inside the range");
                        }
                    }
                    else
                    {
                        if (_trapDir > 0 && c > _rangeHigh) { fire = true; tradeDir = 1; }
                        if (_trapDir < 0 && c < _rangeLow) { fire = true; tradeDir = -1; }
                        if (fire)
                        {
                            trigger = "trap_reversal";
                            stopPrice = tradeDir > 0 ? _rangeLow : _rangeHigh;
                        }
                    }
                    break;
                }
            }

            if (fire && OpenPosition(tradeDir, stopPrice, trigger, biasLbl))
                ResetSignalState();
        }

        // ══════════════════════════════════════════════════════════════════
        //  RISK KERNEL
        // ══════════════════════════════════════════════════════════════════
        private bool RiskKernelBlocks()
        {
            if (_haltedTotal) return true;

            if (Account.Equity > _peakEquity) _peakEquity = Account.Equity;

            if (MaxTotalDdPct > 0 && _peakEquity > 0)
            {
                double dd = (_peakEquity - Account.Equity) / _peakEquity * 100.0;
                if (dd >= MaxTotalDdPct)
                {
                    _haltedTotal = true;
                    Print("Isaiah 60:22 | HALT (permanent): drawdown {0:F2}% >= {1:F2}%", dd, MaxTotalDdPct);
                    return true;
                }
            }

            if (_haltedToday) return true;

            if (MaxDailyLossPct > 0 && _dayStartEquity > 0)
            {
                double loss = (_dayStartEquity - Account.Equity) / _dayStartEquity * 100.0;
                if (loss >= MaxDailyLossPct)
                {
                    _haltedToday = true;
                    Print("Isaiah 60:22 | HALT (session): loss {0:F2}% >= {1:F2}%", loss, MaxDailyLossPct);
                    return true;
                }
            }

            if (MaxConsecLosses > 0 && _consecLosses >= MaxConsecLosses)
            {
                _haltedToday = true;
                Print("Isaiah 60:22 | HALT (session): {0} consecutive losses", _consecLosses);
                return true;
            }

            return MaxTradesPerDay > 0 && _tradesToday >= MaxTradesPerDay;
        }

        private double ClampStopPips(double stopPips)
        {
            double atrPips = _rangeAtr > 0 ? _rangeAtr / Symbol.PipSize : 0;
            if (atrPips <= 0) return stopPips;

            if (MinStopAtr > 0) stopPips = Math.Max(stopPips, MinStopAtr * atrPips);
            if (MaxStopAtr > 0 && stopPips > MaxStopAtr * atrPips) return -1;   // reject
            return stopPips;
        }

        // Refuses to round UP to the broker minimum: if one minimum unit risks
        // more than the configured percent, the correct action is no trade.
        private double VolumeForRisk(double stopPips)
        {
            if (stopPips <= 0) return 0;

            double riskMoney = Account.Equity * RiskPercent / 100.0;
            double pipValuePerUnit = Symbol.PipValue;
            if (pipValuePerUnit <= 0) return 0;

            double units = riskMoney / (stopPips * pipValuePerUnit);
            units = Symbol.NormalizeVolumeInUnits(units, RoundingMode.Down);

            if (units < Symbol.VolumeInUnitsMin) return 0;
            return Math.Min(units, Symbol.VolumeInUnitsMax);
        }

        private bool SpreadBlocks(double stopPips, out string why)
        {
            why = "";
            double spreadPips = Symbol.Spread / Symbol.PipSize;

            if (MaxSpreadPips > 0 && spreadPips > MaxSpreadPips)
            {
                why = string.Format("spread {0:F1} > max {1:F1} pips", spreadPips, MaxSpreadPips);
                return true;
            }
            if (MaxSpreadVsStop > 0 && stopPips > 0)
            {
                double pct = spreadPips / stopPips * 100.0;
                if (pct > MaxSpreadVsStop)
                {
                    why = string.Format("spread is {0:F1}% of the stop, max {1:F1}%", pct, MaxSpreadVsStop);
                    return true;
                }
            }
            return false;
        }

        // ══════════════════════════════════════════════════════════════════
        //  EXECUTION
        // ══════════════════════════════════════════════════════════════════
        private bool OpenPosition(int dir, double stopPrice, string trigger, string biasLbl)
        {
            double entry = dir > 0 ? Symbol.Ask : Symbol.Bid;

            double buffer = StopBufferPips * Symbol.PipSize;
            stopPrice = dir > 0 ? stopPrice - buffer : stopPrice + buffer;

            double stopPips = Math.Abs(entry - stopPrice) / Symbol.PipSize;
            stopPips = ClampStopPips(stopPips);
            if (stopPips <= 0)
            {
                Print("Isaiah 60:22 | entry rejected: stop outside the ATR band");
                return false;
            }

            string why;
            if (SpreadBlocks(stopPips, out why))
            {
                Print("Isaiah 60:22 | entry rejected: {0}", why);
                return false;
            }

            double volume = VolumeForRisk(stopPips);
            if (volume <= 0)
            {
                Print("Isaiah 60:22 | entry rejected: one minimum lot exceeds the configured risk");
                return false;
            }

            double? tpPips = null;
            if (Exit == ExitMode.FixedR || Exit == ExitMode.RThenTime)
                tpPips = Math.Round(stopPips * TargetR, 1);

            var result = ExecuteMarketOrder(
                dir > 0 ? TradeType.Buy : TradeType.Sell,
                SymbolName, volume, Label, Math.Round(stopPips, 1), tpPips, trigger);

            if (!result.IsSuccessful)
            {
                Print("Isaiah 60:22 | order failed: {0}", result.Error);
                return false;
            }

            _pos = result.Position;
            _entryPrice = _pos.EntryPrice;
            _initialSl = _pos.StopLoss ?? 0;
            _initialTp = _pos.TakeProfit ?? 0;
            _riskPips = stopPips;
            _entrySpreadPips = Symbol.Spread / Symbol.PipSize;
            _entryVolume = volume;
            _entryTimeNy = NowNy;
            _entryDayKey = _dayKey;
            _entryBarIndex = _entryBars.Count;
            _mfePips = 0; _maePips = 0;
            _bePlaced = false; _partialDone = false;
            _biasAtEntry = biasLbl;
            _tradesToday++;

            Print("Isaiah 60:22 | {0} {1} units @ {2}  SL {3}  TP {4}  risk {5:F1} pips  [{6}]",
                  dir > 0 ? "LONG" : "SHORT", volume, Math.Round(_entryPrice, Symbol.Digits),
                  Math.Round(_initialSl, Symbol.Digits),
                  _initialTp > 0 ? Math.Round(_initialTp, Symbol.Digits).ToString() : "none",
                  stopPips, trigger);
            return true;
        }

        private void TrackExcursion()
        {
            if (_pos == null) return;

            double px = _pos.TradeType == TradeType.Buy ? Symbol.Bid : Symbol.Ask;
            double movePips = (_pos.TradeType == TradeType.Buy
                ? px - _pos.EntryPrice
                : _pos.EntryPrice - px) / Symbol.PipSize;

            if (movePips > _mfePips) _mfePips = movePips;
            if (-movePips > _maePips) _maePips = -movePips;
        }

        private void ManagePosition()
        {
            if (_pos == null || _riskPips <= 0) return;

            double px = _pos.TradeType == TradeType.Buy ? Symbol.Bid : Symbol.Ask;
            double rNow = (_pos.TradeType == TradeType.Buy
                ? px - _pos.EntryPrice
                : _pos.EntryPrice - px) / Symbol.PipSize / _riskPips;

            // partial
            if (!_partialDone && PartialAtR > 0 && rNow >= PartialAtR)
            {
                double part = Symbol.NormalizeVolumeInUnits(
                    _pos.VolumeInUnits * PartialPercent / 100.0, RoundingMode.Down);
                if (part >= Symbol.VolumeInUnitsMin &&
                    (_pos.VolumeInUnits - part) >= Symbol.VolumeInUnitsMin)
                {
                    var r = ClosePosition(_pos, part);
                    if (r.IsSuccessful) Print("Isaiah 60:22 | partial {0} units closed at {1:F2}R", part, rNow);
                }
                _partialDone = true;
            }

            // break-even
            if (!_bePlaced && BreakevenAtR > 0 && rNow >= BreakevenAtR)
            {
                ModifyPosition(_pos, _pos.EntryPrice, _pos.TakeProfit);
                _bePlaced = true;
                Print("Isaiah 60:22 | stop moved to break-even at {0:F2}R", rNow);
            }

            // ATR trail
            if (Exit == ExitMode.AtrTrail)
            {
                double atr = _atr.Result.Last(1);
                if (atr > 0)
                {
                    double trail = _pos.TradeType == TradeType.Buy
                        ? px - AtrTrailMult * atr
                        : px + AtrTrailMult * atr;

                    bool improves = _pos.StopLoss == null ||
                        (_pos.TradeType == TradeType.Buy ? trail > _pos.StopLoss : trail < _pos.StopLoss);
                    if (improves) ModifyPosition(_pos, trail, _pos.TakeProfit);
                }
            }
        }

        // ══════════════════════════════════════════════════════════════════
        //  JOURNAL
        // ══════════════════════════════════════════════════════════════════
        private void EnsureJournalHeader()
        {
            if (!WriteJournal) return;
            try
            {
                if (File.Exists(_journalPath)) return;
                File.WriteAllText(_journalPath, string.Join(",",
                    "run_tag", "symbol", "preset", "model", "ticket", "direction",
                    "ny_day", "entry_time_ny", "exit_time_ny",
                    "entry_price", "exit_price", "sl_price", "tp_price",
                    "risk_points", "r_realized", "mfe_r", "mae_r",
                    "spread_pts_entry", "range_high", "range_low", "range_pts",
                    "atr_pts", "range_atr_ratio", "bias", "lots",
                    "profit_ccy", "balance_after", "bars_held", "exit_reason") + Environment.NewLine);
            }
            catch (Exception ex)
            {
                Print("Isaiah 60:22 | cannot create journal: {0}", ex.Message);
            }
        }

        private void OnPositionClosed(PositionClosedEventArgs args)
        {
            var p = args.Position;
            if (p.Label != Label || p.SymbolName != SymbolName) return;

            if (p.NetProfit < 0) _consecLosses++;
            else _consecLosses = 0;

            string reason;
            switch (args.Reason)
            {
                case PositionCloseReason.StopLoss: reason = "stop_loss"; break;
                case PositionCloseReason.TakeProfit: reason = "take_profit"; break;
                default: reason = "manual_or_time"; break;
            }

            double exitPrice = p.TradeType == TradeType.Buy ? Symbol.Bid : Symbol.Ask;
            double movePips = (p.TradeType == TradeType.Buy
                ? exitPrice - p.EntryPrice
                : p.EntryPrice - exitPrice) / Symbol.PipSize;

            double rReal = _riskPips > 0 ? movePips / _riskPips : 0;
            double mfeR = _riskPips > 0 ? _mfePips / _riskPips : 0;
            double maeR = _riskPips > 0 ? _maePips / _riskPips : 0;
            double rangePips = _rangeHigh > _rangeLow ? (_rangeHigh - _rangeLow) / Symbol.PipSize : 0;
            double atrPips = _rangeAtr > 0 ? _rangeAtr / Symbol.PipSize : 0;

            Print("Isaiah 60:22 | closed {0}  {1:F2}  ({2})  MFE {3:F2}R  MAE {4:F2}R",
                  p.TradeType, p.NetProfit, reason, mfeR, maeR);

            if (!WriteJournal) return;

            try
            {
                var inv = CultureInfo.InvariantCulture;
                var sb = new StringBuilder();
                sb.Append(string.Join(",",
                    RunTag,
                    SymbolName,
                    "NY_ORB_0930",
                    Model.ToString(),
                    p.Id.ToString(inv),
                    p.TradeType == TradeType.Buy ? "LONG" : "SHORT",
                    _entryDayKey,
                    StampOf(_entryTimeNy),
                    StampOf(NowNy),
                    p.EntryPrice.ToString("F5", inv),
                    exitPrice.ToString("F5", inv),
                    _initialSl.ToString("F5", inv),
                    _initialTp.ToString("F5", inv),
                    _riskPips.ToString("F1", inv),
                    rReal.ToString("F4", inv),
                    mfeR.ToString("F4", inv),
                    maeR.ToString("F4", inv),
                    _entrySpreadPips.ToString("F1", inv),
                    _rangeHigh.ToString("F5", inv),
                    _rangeLow.ToString("F5", inv),
                    rangePips.ToString("F1", inv),
                    atrPips.ToString("F1", inv),
                    (atrPips > 0 ? rangePips / atrPips : 0).ToString("F3", inv),
                    _biasAtEntry,
                    _entryVolume.ToString("F2", inv),
                    p.NetProfit.ToString("F2", inv),
                    Account.Balance.ToString("F2", inv),
                    (_entryBars.Count - _entryBarIndex).ToString(inv),
                    reason));
                sb.Append(Environment.NewLine);
                File.AppendAllText(_journalPath, sb.ToString());
            }
            catch (Exception ex)
            {
                Print("Isaiah 60:22 | journal write failed: {0}", ex.Message);
            }
        }

        // ══════════════════════════════════════════════════════════════════
        //  DASHBOARD
        // ══════════════════════════════════════════════════════════════════
        private void DrawDashboard()
        {
            if (!ShowDashboard) return;

            var ny = NowNy;
            string state = "waiting for range";
            if (_haltedTotal) state = "HALTED (drawdown)";
            else if (_haltedToday) state = "halted for the session";
            else if (_daySkipped) state = "day skipped: " + _skipReason;
            else if (_pos != null) state = _pos.TradeType == TradeType.Buy ? "LONG open" : "SHORT open";
            else if (_rangeReady) state = "range set, hunting";

            string signal = _breakDir == 0
                ? "no break yet"
                : string.Format("{0} break of {1}, {2} bars ago",
                    _breakDir > 0 ? "upside" : "downside",
                    Math.Round(_breakLevel, Symbol.Digits), _barsSinceBreak);
            if (_trapArmed) signal += "  [trap armed]";

            var text = string.Format(
                "Isaiah 60:22  |  NY_ORB_0930 / {0}\n" +
                "NY time    {1}\n" +
                "session    {2}\n" +
                "range      {3}  /  {4}\n" +
                "state      {5}\n" +
                "signal     {6}\n" +
                "trades     {7} of {8} today   consec losses {9}",
                Model,
                ny.ToString("HH:mm:ss", CultureInfo.InvariantCulture),
                _dayKey,
                _rangeHigh > 0 ? Math.Round(_rangeHigh, Symbol.Digits).ToString() : "-",
                _rangeLow > 0 ? Math.Round(_rangeLow, Symbol.Digits).ToString() : "-",
                state, signal, _tradesToday, MaxTradesPerDay, _consecLosses);

            Chart.DrawStaticText("I22_Dash", text, VerticalAlignment.Top, HorizontalAlignment.Left, Color.Gainsboro);
        }
    }
}
