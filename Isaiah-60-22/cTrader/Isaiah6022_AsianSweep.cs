// ---------------------------------------------------------------------------
//  Isaiah6022_AsianSweep.cs
//
//  Strategy 02 — The Asian Range Liquidity Sweep.  cTrader / cAlgo cBot.
//
//  Mark the 19:00-00:00 NY overnight range. Wait for price to take out one
//  extreme, close back inside, and then shift structure. Trade the reversal.
//  Entries 02:00-11:00 NY.
//
//  THE PREMISE, STATED HONESTLY. The sweep predicts VOLATILITY, not direction.
//  Osler's order-book research found take-profit orders cluster AT a level
//  (which reverses price) and stop orders cluster JUST BEYOND it (which
//  accelerates price). That is why the two source families point at this same
//  level and trade it in opposite directions, and why both can show winning
//  screenshots. Direction has to come from somewhere other than the sweep —
//  which is what the bias filter is for. It defaults ON.
//
//  Run it once with Bias = Off. If the filter does not improve the result,
//  the strategy has no premise left. That is the most informative backtest
//  in this workspace.
//
//  CLOCK. TimeZone = UTC, so Server.Time is UTC and the New York conversion
//  uses the real US daylight-saving rule. No broker-offset input to get wrong.
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
    public enum SweepModel
    {
        SweepMss,        // Sweep -> reclaim -> market structure shift. DEFAULT
        SweepMssFvg,     // As above, then wait for the retracement into the displacement FVG
        SweepReclaim,    // Sweep -> close back inside. No MSS (weaker, for comparison)
        RangeCross       // Sweep one side, then trade the close through the OPPOSITE boundary
    }

    public enum SweepBiasMode
    {
        Off,
        HtfEma,
        PrevDay
    }

    public enum SweepExitMode
    {
        FixedR,
        TimeOnly,
        RThenTime,
        AtrTrail
    }

    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.FullAccess, AddIndicators = true)]
    public class Isaiah6022_AsianSweep : Robot
    {
        // ── 1. Model and timeframes ────────────────────────────────────────
        [Parameter("Entry model", Group = "1. Model", DefaultValue = SweepModel.SweepMss)]
        public SweepModel Model { get; set; }

        [Parameter("Range timeframe", Group = "1. Model", DefaultValue = "Minute15")]
        public TimeFrame RangeTf { get; set; }

        [Parameter("Entry timeframe", Group = "1. Model", DefaultValue = "Minute5")]
        public TimeFrame EntryTf { get; set; }

        // ── 2. Clock, all times New York local ─────────────────────────────
        [Parameter("Asian range start hour (NY)", Group = "2. Clock", DefaultValue = 19)]
        public int RangeStartHH { get; set; }

        [Parameter("Asian range start minute (NY)", Group = "2. Clock", DefaultValue = 0)]
        public int RangeStartMM { get; set; }

        [Parameter("Asian range end hour (NY)", Group = "2. Clock", DefaultValue = 0)]
        public int RangeEndHH { get; set; }

        [Parameter("Asian range end minute (NY)", Group = "2. Clock", DefaultValue = 0)]
        public int RangeEndMM { get; set; }

        [Parameter("Entry window start hour (NY)", Group = "2. Clock", DefaultValue = 2)]
        public int TradeStartHH { get; set; }

        [Parameter("Entry window start minute (NY)", Group = "2. Clock", DefaultValue = 0)]
        public int TradeStartMM { get; set; }

        [Parameter("Entry window end hour (NY)", Group = "2. Clock", DefaultValue = 11)]
        public int TradeEndHH { get; set; }

        [Parameter("Entry window end minute (NY)", Group = "2. Clock", DefaultValue = 0)]
        public int TradeEndMM { get; set; }

        [Parameter("Force-flat hour (NY)", Group = "2. Clock", DefaultValue = 12)]
        public int FlatHH { get; set; }

        [Parameter("Force-flat minute (NY)", Group = "2. Clock", DefaultValue = 0)]
        public int FlatMM { get; set; }

        [Parameter("Trade Monday", Group = "2. Clock", DefaultValue = true)]    public bool TradeMon { get; set; }
        [Parameter("Trade Tuesday", Group = "2. Clock", DefaultValue = true)]   public bool TradeTue { get; set; }
        [Parameter("Trade Wednesday", Group = "2. Clock", DefaultValue = true)] public bool TradeWed { get; set; }
        [Parameter("Trade Thursday", Group = "2. Clock", DefaultValue = true)]  public bool TradeThu { get; set; }
        [Parameter("Trade Friday", Group = "2. Clock", DefaultValue = true)]    public bool TradeFri { get; set; }

        // ── 3. Sweep and structure ─────────────────────────────────────────
        [Parameter("Sweep buffer (pips)", Group = "3. Structure", DefaultValue = 0.0)]
        public double SweepBufferPips { get; set; }

        [Parameter("Reclaim within N bars", Group = "3. Structure", DefaultValue = 6)]
        public int ReclaimBars { get; set; }

        [Parameter("MSS fractal right bars", Group = "3. Structure", DefaultValue = 2)]
        public int MssFractalRight { get; set; }

        [Parameter("MSS swing lookback bars", Group = "3. Structure", DefaultValue = 40)]
        public int MssLookback { get; set; }

        [Parameter("Max bars to trigger", Group = "3. Structure", DefaultValue = 60)]
        public int MaxBarsToTrigger { get; set; }

        [Parameter("FVG lookback bars", Group = "3. Structure", DefaultValue = 3)]
        public int FvgLookback { get; set; }

        [Parameter("Min FVG height (pips)", Group = "3. Structure", DefaultValue = 0.0)]
        public double MinFvgPips { get; set; }

        [Parameter("Structure breaks are body closes", Group = "3. Structure", DefaultValue = true)]
        public bool RequireBodyClose { get; set; }

        [Parameter("Min range (pips), 0 = off", Group = "3. Structure", DefaultValue = 0.0)]
        public double MinRangePips { get; set; }

        [Parameter("Max range as x ATR, 0 = off", Group = "3. Structure", DefaultValue = 2.5)]
        public double MaxRangeAtr { get; set; }

        // Relative volume. DEFAULT OFF, deliberately.
        // Zarattini, Barbon & Aziz (2024) found the opening-range edge lives
        // in which days you trade — but that was US equities with a different
        // RVOL definition, and it did NOT replicate here. Measured on 125
        // sessions of real tick data, the opening-window RVOL distribution is
        // clustered around 1.0 (gold median 1.00, p95 1.24), so a 1.5 gate
        // rejects every session. Calibrated to 1.05-1.10 it helped gold and
        // hurt Nasdaq and AUDJPY. Measure your own instrument before enabling.
        [Parameter("Min relative volume, 0 = off", Group = "3. Structure", DefaultValue = 0.0)]
        public double MinRvol { get; set; }

        [Parameter("RVOL baseline sessions", Group = "3. Structure", DefaultValue = 20)]
        public int RvolLookbackDays { get; set; }

        [Parameter("Require correct side of midnight open", Group = "3. Structure", DefaultValue = true)]
        public bool UseMidnightOpen { get; set; }

        // ── 4. Bias — not optional here ────────────────────────────────────
        [Parameter("Bias filter", Group = "4. Bias", DefaultValue = SweepBiasMode.HtfEma)]
        public SweepBiasMode Bias { get; set; }

        [Parameter("Bias timeframe", Group = "4. Bias", DefaultValue = "Hour4")]
        public TimeFrame BiasTf { get; set; }

        [Parameter("Bias EMA period", Group = "4. Bias", DefaultValue = 50)]
        public int BiasEmaPeriod { get; set; }

        [Parameter("Bias blocks counter-trend", Group = "4. Bias", DefaultValue = true)]
        public bool BiasBlocksCounter { get; set; }

        [Parameter("No bias, no trade", Group = "4. Bias", DefaultValue = true)]
        public bool RequireBias { get; set; }

        // ── 5. Stops and targets ───────────────────────────────────────────
        [Parameter("Exit mode", Group = "5. Exits", DefaultValue = SweepExitMode.FixedR)]
        public SweepExitMode Exit { get; set; }

        [Parameter("Target in R", Group = "5. Exits", DefaultValue = 2.0, MinValue = 0.1)]
        public double TargetR { get; set; }

        [Parameter("Stop buffer beyond MSS swing (pips)", Group = "5. Exits", DefaultValue = 15.0)]
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

        [Parameter("Max trades per session", Group = "6. Risk", DefaultValue = 1)]
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

        [Parameter("Journal file name", Group = "7. Journal", DefaultValue = "I22_Sweep_journal.csv")]
        public string JournalFile { get; set; }

        [Parameter("Run tag — CHANGE EVERY RUN", Group = "7. Journal", DefaultValue = "asian_sweep_ct_v1")]
        public string RunTag { get; set; }

        [Parameter("Show dashboard", Group = "7. Journal", DefaultValue = true)]
        public bool ShowDashboard { get; set; }

        [Parameter("Draw range lines", Group = "7. Journal", DefaultValue = true)]
        public bool DrawObjects { get; set; }

        // ── State ──────────────────────────────────────────────────────────
        private const string Label = "I22_SWEEP";

        private Bars _rangeBars, _entryBars, _biasBars;
        private AverageTrueRange _atr;
        private ExponentialMovingAverage _biasEma;

        private string _dayKey = "";
        private double _rangeHigh, _rangeLow;
        private bool _rangeReady, _daySkipped;
        private string _skipReason = "";
        private double _rangeAtr;
        private double _rvol;
        private double _rvolAtEntry;
        private int _tradesToday, _consecLosses;
        private double _dayStartEquity, _peakEquity;
        private bool _haltedToday, _haltedTotal;

        private int _sweepSide;              // +1 swept the HIGH (hunt shorts), -1 swept the LOW (hunt longs)
        private double _sweepExtreme;
        private int _barsSinceSweep;
        private bool _reclaimed;
        private bool _mssConfirmed;
        private double _mssProtected;
        private double _midnightOpen;

        private DateTime _lastEntryBarTime = DateTime.MinValue;
        private DateTime _lastRangeBarTime = DateTime.MinValue;

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
        // ══════════════════════════════════════════════════════════════════
        private static DateTime NthWeekdayOfMonth(int year, int month, DayOfWeek weekday, int nth)
        {
            var first = new DateTime(year, month, 1, 0, 0, 0, DateTimeKind.Utc);
            int delta = ((int)weekday - (int)first.DayOfWeek + 7) % 7;
            return first.AddDays(delta + (nth - 1) * 7);
        }

        private static bool IsUsDaylightTime(DateTime utc)
        {
            var dstStart = NthWeekdayOfMonth(utc.Year, 3, DayOfWeek.Sunday, 2).AddHours(7);
            var dstEnd = NthWeekdayOfMonth(utc.Year, 11, DayOfWeek.Sunday, 1).AddHours(6);
            return utc >= dstStart && utc < dstEnd;
        }

        private static DateTime ToNy(DateTime utc) => utc.AddHours(IsUsDaylightTime(utc) ? -4 : -5);

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
            return nowMin >= startMin || nowMin < endMin;
        }

        // The 19:00-00:00 range belongs to the session that FOLLOWS it.
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
            if (Bias == SweepBiasMode.HtfEma)
                _biasEma = Indicators.ExponentialMovingAverage(_biasBars.ClosePrices, BiasEmaPeriod);

            _peakEquity = Account.Equity;
            _dayStartEquity = Account.Equity;

            _journalPath = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), JournalFile);
            EnsureJournalHeader();

            Positions.Closed += OnPositionClosed;

            if (RequireBias && Bias == SweepBiasMode.Off)
                Print("Isaiah 60:22 | WARNING: 'No bias, no trade' is on but the bias filter is Off. " +
                      "Every sweep becomes tradeable in both directions, which is the premise this " +
                      "strategy does not have. Set a bias mode, or turn the requirement off knowingly.");

            Print("Isaiah 60:22 | ASIAN_SWEEP / {0} started. NY time now {1}. Journal: {2}",
                  Model, StampOf(NowNy), WriteJournal ? _journalPath : "(off)");
            Print("Isaiah 60:22 | range {0:00}:{1:00}-{2:00}:{3:00} NY (wraps midnight), entries {4:00}:{5:00}-{6:00}:{7:00} NY, flat {8:00}:{9:00} NY",
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

            string key = RangeDayKey(ny);
            if (key != _dayKey) ResetSession(key);

            _pos = Positions.Find(Label, SymbolName);

            if (_pos != null && !InWindow(nowMin, TradeStartMin, FlatMin))
            {
                ClosePosition(_pos);
                Print("Isaiah 60:22 | flattened: force-flat time reached");
                DrawDashboard("");
                return;
            }

            if (_pos != null)
            {
                TrackExcursion();
                ManagePosition();
                DrawDashboard("");
                return;
            }

            if (RiskKernelBlocks()) { DrawDashboard(""); return; }
            if (!IsTradeDay(ny.DayOfWeek)) { DrawDashboard(""); return; }

            if (InWindow(nowMin, RangeStartMin, RangeEndMin)) { UpdateRange(); DrawDashboard(""); return; }
            FinaliseRange();

            if (!_rangeReady || _daySkipped) { DrawDashboard(""); return; }
            if (!InWindow(nowMin, TradeStartMin, TradeEndMin)) { DrawDashboard(""); return; }

            var lastEntryOpen = _entryBars.OpenTimes.Last(1);
            if (lastEntryOpen == _lastEntryBarTime) { DrawDashboard(""); return; }
            _lastEntryBarTime = lastEntryOpen;

            EvaluateSignal();
        }

        // ══════════════════════════════════════════════════════════════════
        //  SESSION AND RANGE
        // ══════════════════════════════════════════════════════════════════
        private void ResetSession(string newKey)
        {
            _dayKey = newKey;
            _rangeHigh = 0; _rangeLow = 0;
            _rangeReady = false; _daySkipped = false; _skipReason = "";
            _rangeAtr = 0;
            _rvol = 0;
            _tradesToday = 0;
            _haltedToday = false;
            _dayStartEquity = Account.Equity;
            _lastRangeBarTime = DateTime.MinValue;
            ResetSignalState();

            if (DrawObjects)
            {
                Chart.RemoveObject("I22_RangeHigh");
                Chart.RemoveObject("I22_RangeLow");
                Chart.RemoveObject("I22_Midnight");
            }
        }

        private void ResetSignalState()
        {
            _sweepSide = 0;
            _sweepExtreme = 0;
            _barsSinceSweep = 0;
            _reclaimed = false;
            _mssConfirmed = false;
            _mssProtected = 0;
            _midnightOpen = 0;
        }

        private void UpdateRange()
        {
            var barTime = _rangeBars.OpenTimes.Last(1);
            if (barTime == _lastRangeBarTime) return;
            _lastRangeBarTime = barTime;

            var barNy = ToNy(barTime);
            if (!InWindow(MinuteOfDay(barNy), RangeStartMin, RangeEndMin)) return;
            if (RangeDayKey(barNy) != _dayKey) return;

            double h = _rangeBars.HighPrices.Last(1);
            double l = _rangeBars.LowPrices.Last(1);

            if (_rangeHigh == 0 || h > _rangeHigh) _rangeHigh = h;
            if (_rangeLow == 0 || l < _rangeLow) _rangeLow = l;
        }

        private void FinaliseRange()
        {
            if (_rangeReady || _rangeHigh <= 0 || _rangeLow <= 0) return;

            _rangeReady = true;
            _rangeAtr = _atr.Result.Last(1);
            _rvol = ComputeRvol();

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
                _skipReason = string.Format("range {0:F2} x ATR — too wide to be a consolidation", rangePips / atrPips);
            }

            if (!_daySkipped && MinRvol > 0 && _rvol < MinRvol)
            {
                _daySkipped = true;
                _skipReason = string.Format("relative volume {0:F2} < min {1:F2}", _rvol, MinRvol);
            }

            if (DrawObjects)
            {
                Chart.DrawHorizontalLine("I22_RangeHigh", _rangeHigh, Color.DodgerBlue, 1, LineStyle.Dots);
                Chart.DrawHorizontalLine("I22_RangeLow", _rangeLow, Color.OrangeRed, 1, LineStyle.Dots);
            }

            Print("Isaiah 60:22 | {0} Asian range set  H={1}  L={2}  ({3:F1} pips, {4:F2} x ATR){5}",
                  _dayKey, Math.Round(_rangeHigh, Symbol.Digits), Math.Round(_rangeLow, Symbol.Digits),
                  rangePips, atrPips > 0 ? rangePips / atrPips : 0,
                  _daySkipped ? "  SKIPPED: " + _skipReason : "");
        }

        // The NY midnight open — the reference the source material uses for
        // entry placement, not merely the end of the range.
        private double MidnightOpen()
        {
            for (int i = 1; i < 600 && i < _entryBars.Count; i++)
            {
                var bt = ToNy(_entryBars.OpenTimes.Last(i));
                if (DayKeyOf(bt) != _dayKey) continue;
                if (MinuteOfDay(bt) == 0) return _entryBars.OpenPrices.Last(i);
            }
            return 0;
        }


        // Volume traded inside today's range window, over the mean of the same
        // window across the previous N sessions. Returns 1.0 when history is
        // too thin to judge, so a short warm-up never rejects every session.
        private double ComputeRvol()
        {
            if (MinRvol <= 0 || RvolLookbackDays < 1) return 1.0;

            double todayVol = 0;
            var prior = new System.Collections.Generic.Dictionary<string, double>();
            int scanned = Math.Min(_rangeBars.Count - 1, 20000);

            for (int i = 1; i <= scanned; i++)
            {
                var barNy = ToNy(_rangeBars.OpenTimes.Last(i));
                if (!InWindow(MinuteOfDay(barNy), RangeStartMin, RangeEndMin)) continue;

                string key = RangeDayKey(barNy);
                double v = _rangeBars.TickVolumes.Last(i);

                if (key == _dayKey) { todayVol += v; continue; }

                if (!prior.ContainsKey(key))
                {
                    if (prior.Count >= RvolLookbackDays) break;
                    prior[key] = 0;
                }
                prior[key] += v;
            }

            if (prior.Count < 2 || todayVol <= 0) return 1.0;

            double baseline = prior.Values.Average();
            return baseline > 0 ? todayVol / baseline : 1.0;
        }

        // ══════════════════════════════════════════════════════════════════
        //  BIAS
        // ══════════════════════════════════════════════════════════════════
        private int CurrentBias(out string label)
        {
            label = "OFF";
            switch (Bias)
            {
                case SweepBiasMode.Off:
                    return 0;

                case SweepBiasMode.HtfEma:
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

                case SweepBiasMode.PrevDay:
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
            }
            return 0;
        }

        // ══════════════════════════════════════════════════════════════════
        //  STRUCTURE
        // ══════════════════════════════════════════════════════════════════

        // Most recent CONFIRMED swing. A swing needs MssFractalRight bars on
        // each side, so it is only confirmed that many bars after it printed.
        private bool FindSwing(bool wantHigh, out double level, out int barsBack)
        {
            level = 0; barsBack = 0;
            int n = MssFractalRight;

            for (int i = 1 + n; i <= MssLookback && i + n < _entryBars.Count; i++)
            {
                double pivot = wantHigh ? _entryBars.HighPrices.Last(i) : _entryBars.LowPrices.Last(i);
                bool ok = true;

                for (int k = 1; k <= n && ok; k++)
                {
                    double left = wantHigh ? _entryBars.HighPrices.Last(i + k) : _entryBars.LowPrices.Last(i + k);
                    double right = wantHigh ? _entryBars.HighPrices.Last(i - k) : _entryBars.LowPrices.Last(i - k);
                    if (wantHigh) { if (left >= pivot || right >= pivot) ok = false; }
                    else { if (left <= pivot || right <= pivot) ok = false; }
                }

                if (ok) { level = pivot; barsBack = i; return true; }
            }
            return false;
        }

        // After a sweep of the LOW we need price to break the most recent swing
        // HIGH (and vice versa). That break is the displacement that says the
        // reversal has intent. A wick alone is not the trade.
        private bool DetectMss(int tradeDir, out double protectedExtreme)
        {
            protectedExtreme = 0;

            double c = _entryBars.ClosePrices.Last(1);
            double h = _entryBars.HighPrices.Last(1);
            double l = _entryBars.LowPrices.Last(1);

            double swing;
            int idx;

            if (tradeDir > 0)
            {
                if (!FindSwing(true, out swing, out idx)) return false;
                double test = RequireBodyClose ? c : h;
                if (test <= swing) return false;

                double lowest = l;
                for (int i = 1; i <= idx; i++)
                {
                    double li = _entryBars.LowPrices.Last(i);
                    if (li < lowest) lowest = li;
                }
                protectedExtreme = lowest;
                return true;
            }

            if (!FindSwing(false, out swing, out idx)) return false;
            double testDn = RequireBodyClose ? c : l;
            if (testDn >= swing) return false;

            double highest = h;
            for (int i = 1; i <= idx; i++)
            {
                double hi = _entryBars.HighPrices.Last(i);
                if (hi > highest) highest = hi;
            }
            protectedExtreme = highest;
            return true;
        }

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

        // ══════════════════════════════════════════════════════════════════
        //  SIGNAL
        // ══════════════════════════════════════════════════════════════════
        private void EvaluateSignal()
        {
            if (_midnightOpen == 0 && UseMidnightOpen) _midnightOpen = MidnightOpen();
            if (_sweepSide != 0) _barsSinceSweep++;

            string biasLbl;
            int bias = CurrentBias(out biasLbl);

            double h = _entryBars.HighPrices.Last(1);
            double l = _entryBars.LowPrices.Last(1);
            double c = _entryBars.ClosePrices.Last(1);
            double buf = SweepBufferPips * Symbol.PipSize;

            // 1. the sweep
            if (_sweepSide == 0)
            {
                if (h > _rangeHigh + buf)
                {
                    _sweepSide = 1;                  // swept the high -> hunting SHORTS
                    _sweepExtreme = h;
                    _barsSinceSweep = 0;
                    Print("Isaiah 60:22 | swept the Asian HIGH at {0} (range high {1})",
                          Math.Round(h, Symbol.Digits), Math.Round(_rangeHigh, Symbol.Digits));
                }
                else if (l < _rangeLow - buf)
                {
                    _sweepSide = -1;                 // swept the low -> hunting LONGS
                    _sweepExtreme = l;
                    _barsSinceSweep = 0;
                    Print("Isaiah 60:22 | swept the Asian LOW at {0} (range low {1})",
                          Math.Round(l, Symbol.Digits), Math.Round(_rangeLow, Symbol.Digits));
                }
            }
            else
            {
                if (_sweepSide > 0 && h > _sweepExtreme) _sweepExtreme = h;
                if (_sweepSide < 0 && l < _sweepExtreme) _sweepExtreme = l;
            }

            if (_sweepSide == 0) { DrawDashboard(""); return; }

            int tradeDir = -_sweepSide;

            // 2. the reclaim. No reclaim within N bars means this was a
            //    breakout, not a sweep, and we are on the wrong side of it.
            if (!_reclaimed)
            {
                bool backInside = _sweepSide > 0 ? c < _rangeHigh : c > _rangeLow;
                if (backInside)
                {
                    _reclaimed = true;
                    Print("Isaiah 60:22 | reclaimed the range — sweep confirmed");
                }
                else if (_barsSinceSweep > ReclaimBars)
                {
                    Print("Isaiah 60:22 | no reclaim within {0} bars — that was a breakout, not a sweep. Stand down.",
                          ReclaimBars);
                    ResetSignalState();
                    DrawDashboard("");
                    return;
                }
                else { DrawDashboard(""); return; }
            }

            if (MaxBarsToTrigger > 0 && _barsSinceSweep > MaxBarsToTrigger)
            {
                Print("Isaiah 60:22 | setup expired without a trigger");
                ResetSignalState();
                DrawDashboard("");
                return;
            }

            // 3. bias. Direction cannot come from the sweep, so it comes from here.
            if (RequireBias && bias == 0)
            {
                DrawDashboard("waiting: no higher-timeframe bias");
                return;
            }
            if (BiasBlocksCounter && bias != 0 && bias != tradeDir)
            {
                Print("Isaiah 60:22 | sweep of the {0} ignored: bias is {1}, the reversal would be {2}",
                      _sweepSide > 0 ? "high" : "low", biasLbl, tradeDir > 0 ? "long" : "short");
                ResetSignalState();
                DrawDashboard("");
                return;
            }

            // 4. midnight-open side filter
            if (UseMidnightOpen && _midnightOpen > 0 && Model != SweepModel.RangeCross)
            {
                double px = tradeDir > 0 ? Symbol.Ask : Symbol.Bid;
                bool okSide = tradeDir > 0 ? px < _midnightOpen : px > _midnightOpen;
                if (!okSide)
                {
                    DrawDashboard("waiting: wrong side of the midnight open");
                    return;
                }
            }

            // 5. model trigger
            bool fire = false;
            string trigger = "";
            double stopPrice = 0;

            switch (Model)
            {
                case SweepModel.SweepMss:
                {
                    if (!_mssConfirmed)
                    {
                        double prot;
                        if (DetectMss(tradeDir, out prot))
                        {
                            _mssConfirmed = true;
                            _mssProtected = prot;
                            Print("Isaiah 60:22 | market structure shift confirmed");
                        }
                    }
                    if (_mssConfirmed)
                    {
                        fire = true;
                        trigger = "sweep_mss";
                        stopPrice = _mssProtected;
                    }
                    break;
                }

                case SweepModel.SweepMssFvg:
                {
                    if (!_mssConfirmed)
                    {
                        double prot;
                        if (DetectMss(tradeDir, out prot))
                        {
                            _mssConfirmed = true;
                            _mssProtected = prot;
                            Print("Isaiah 60:22 | MSS confirmed, waiting for the retracement into the FVG");
                        }
                    }
                    else
                    {
                        double fvg = FindFvg(tradeDir);
                        if (fvg > 0)
                        {
                            double px = tradeDir > 0 ? Symbol.Ask : Symbol.Bid;
                            if ((tradeDir > 0 && px <= fvg) || (tradeDir < 0 && px >= fvg))
                            {
                                fire = true;
                                trigger = "sweep_mss_fvg";
                                stopPrice = _mssProtected;
                            }
                        }
                    }
                    break;
                }

                case SweepModel.SweepReclaim:
                    // Deliberately weaker: no MSS. Included so you can measure
                    // what the MSS filter is actually worth on your instrument.
                    fire = true;
                    trigger = "sweep_reclaim_only";
                    stopPrice = _sweepExtreme;
                    break;

                case SweepModel.RangeCross:
                {
                    bool crossed = tradeDir > 0 ? c > _rangeHigh : c < _rangeLow;
                    if (crossed)
                    {
                        fire = true;
                        trigger = "range_cross";
                        stopPrice = _sweepExtreme;
                    }
                    break;
                }
            }

            if (fire && OpenPosition(tradeDir, stopPrice, trigger, biasLbl))
                ResetSignalState();

            DrawDashboard("");
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
            if (MaxStopAtr > 0 && stopPips > MaxStopAtr * atrPips) return -1;
            return stopPips;
        }

        private double VolumeForRisk(double stopPips)
        {
            if (stopPips <= 0) return 0;

            double riskMoney = Account.Equity * RiskPercent / 100.0;
            if (Symbol.PipValue <= 0) return 0;

            double units = riskMoney / (stopPips * Symbol.PipValue);
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

            // The 10-20 pip buffer beyond the MSS swing is not negotiable:
            // stops parked exactly at an obvious swing are the liquidity that
            // gets taken on the second test.
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
            if (Exit == SweepExitMode.FixedR || Exit == SweepExitMode.RThenTime)
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
            _rvolAtEntry = _rvol;
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

            if (!_bePlaced && BreakevenAtR > 0 && rNow >= BreakevenAtR)
            {
                ModifyPosition(_pos, _pos.EntryPrice, _pos.TakeProfit);
                _bePlaced = true;
                Print("Isaiah 60:22 | stop moved to break-even at {0:F2}R", rNow);
            }

            if (Exit == SweepExitMode.AtrTrail)
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
                    "atr_pts", "range_atr_ratio", "rvol", "bias", "lots",
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
                    "ASIAN_SWEEP",
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
                    _rvolAtEntry.ToString("F3", inv),
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
        private void DrawDashboard(string extra)
        {
            if (!ShowDashboard) return;

            var ny = NowNy;
            string state = "waiting for range";
            if (_haltedTotal) state = "HALTED (drawdown)";
            else if (_haltedToday) state = "halted for the session";
            else if (_daySkipped) state = "day skipped: " + _skipReason;
            else if (_pos != null) state = _pos.TradeType == TradeType.Buy ? "LONG open" : "SHORT open";
            else if (_rangeReady) state = "range set, waiting for the sweep";

            string signal = _sweepSide == 0
                ? "no sweep yet"
                : string.Format("swept the {0} {1} bars ago{2}{3}",
                    _sweepSide > 0 ? "HIGH" : "LOW", _barsSinceSweep,
                    _reclaimed ? "  [reclaimed]" : "  [waiting for reclaim]",
                    _mssConfirmed ? "  [MSS]" : "");

            var text = string.Format(
                "Isaiah 60:22  |  ASIAN_SWEEP / {0}\n" +
                "NY time    {1}\n" +
                "session    {2}\n" +
                "range      {3}  /  {4}   RVOL " + _rvol.ToString("F2") + "\n" +
                "midnight   {5}\n" +
                "state      {6}\n" +
                "signal     {7}\n" +
                "trades     {8} of {9} today   consec losses {10}\n" +
                "{11}",
                Model,
                ny.ToString("HH:mm:ss", CultureInfo.InvariantCulture),
                _dayKey,
                _rangeHigh > 0 ? Math.Round(_rangeHigh, Symbol.Digits).ToString() : "-",
                _rangeLow > 0 ? Math.Round(_rangeLow, Symbol.Digits).ToString() : "-",
                _midnightOpen > 0 ? Math.Round(_midnightOpen, Symbol.Digits).ToString() : "-",
                state, signal, _tradesToday, MaxTradesPerDay, _consecLosses, extra);

            Chart.DrawStaticText("I22_Dash", text, VerticalAlignment.Top, HorizontalAlignment.Left, Color.Gainsboro);
        }
    }
}
