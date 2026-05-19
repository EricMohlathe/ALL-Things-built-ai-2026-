// GODMODE_OFEA.cs
//
// Markets spend 70-80% of their time in balance and 20-30% in
// imbalance. The edge is not predicting which state is next - it
// is reacting to state-change signatures left by institutions:
// absorption, stacked imbalances, CVD divergence, and aggression
// prints, at high-probability volume-profile locations, during
// high-probability sessions, with HTF alignment.
//
// Operator priority: capital protection > expectancy > win rate.
//
// Source authority: brief §1 thesis, §2 5-gate stack,
// §3 8-row dashboard, §4 N-A..N-L cascade, §5 bar-close pipeline,
// §6 25-setup catalogue, §7 input schema, §11 algorithms,
// §12 kill switches, §15 code quality.
//
// Mirrors mt5/Experts/GODMODE_OFEA/GODMODE_OFEA.mq5 byte-for-byte
// in numerics and parameter names. Different syntax, identical behaviour.

using System;
using System.IO;
using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace GodmodeOfea
{
    // FullAccess required for HttpClient (GoogleSheetsLevels), file I/O
    // (Sierra/Bookmap bridges + TradeLogger), and Notifications.SendEmail.
    // Trader is prompted once on first install to grant the elevated rights.
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.FullAccess)]
    public class GODMODE_OFEA : Robot
    {
        //=== MODE & PLATFORM ===
        [Parameter("Operating Mode", Group = "Mode", DefaultValue = OpMode.Manual)]
        public OpMode OperatingMode { get; set; }
        [Parameter("Enable Notifications", Group = "Mode", DefaultValue = true)]
        public bool EnableNotifications { get; set; }
        [Parameter("Enable Push Alerts", Group = "Mode", DefaultValue = true)]
        public bool EnablePushAlerts { get; set; }
        [Parameter("Enable Sound Alerts", Group = "Mode", DefaultValue = true)]
        public bool EnableSoundAlerts { get; set; }
        [Parameter("Enable Email Alerts", Group = "Mode", DefaultValue = false)]
        public bool EnableEmailAlerts { get; set; }

        //=== STRATEGY MASTER ===
        [Parameter("Enable Model1 Trend", Group = "Strategy", DefaultValue = true)]
        public bool EnableModel1_Trend { get; set; }
        [Parameter("Enable Model2 MeanRev", Group = "Strategy", DefaultValue = true)]
        public bool EnableModel2_MeanRev { get; set; }
        [Parameter("Half Size On HTF Conflict", Group = "Strategy", DefaultValue = false)]
        public bool HalfSize_OnHTFConflict { get; set; }

        //=== SESSION (SAST UTC+2) ===
        [Parameter("SAST OffsetFromBroker (hours)", Group = "Session", DefaultValue = 0)]
        public int SAST_OffsetFromBroker { get; set; }
        [Parameter("Trade Asian Session", Group = "Session", DefaultValue = false)]
        public bool TradeAsianSession { get; set; }
        [Parameter("Trade London Open", Group = "Session", DefaultValue = false)]
        public bool TradeLondonOpen { get; set; }
        [Parameter("Trade London Main", Group = "Session", DefaultValue = true)]
        public bool TradeLondonMain { get; set; }
        [Parameter("Trade NY Open", Group = "Session", DefaultValue = false)]
        public bool TradeNYOpen { get; set; }
        [Parameter("Trade NY Main", Group = "Session", DefaultValue = true)]
        public bool TradeNYMain { get; set; }
        [Parameter("NY Open Blackout Mins", Group = "Session", DefaultValue = 20)]
        public int NYOpen_Blackout_Mins { get; set; }

        //=== ORDER FLOW DETECTION ===
        [Parameter("Delta Lookback", Group = "OrderFlow", DefaultValue = 20)]
        public int DeltaLookback { get; set; }
        [Parameter("Vol Z Threshold", Group = "OrderFlow", DefaultValue = 1.5)]
        public double VolZThreshold { get; set; }
        [Parameter("Delta Z Threshold", Group = "OrderFlow", DefaultValue = 2.0)]
        public double DeltaZThreshold { get; set; }
        [Parameter("Aggression Z Threshold", Group = "OrderFlow", DefaultValue = 2.0)]
        public double AggressionZThreshold { get; set; }
        [Parameter("Min Absorption Stars", Group = "OrderFlow", DefaultValue = 3)]
        public int MinAbsorptionStars { get; set; }
        [Parameter("Min Stacked Imbalance Rows", Group = "OrderFlow", DefaultValue = 3)]
        public int MinStackedImbalanceRows { get; set; }
        [Parameter("Imbalance Ratio", Group = "OrderFlow", DefaultValue = 3.0)]
        public double ImbalanceRatio { get; set; }

        //=== VOLUME PROFILE ===
        [Parameter("VP Length", Group = "VP", DefaultValue = 100)]
        public int VPLength { get; set; }
        [Parameter("VP Bins", Group = "VP", DefaultValue = 50)]
        public int VPBins { get; set; }
        [Parameter("VA Value Area Pct", Group = "VP", DefaultValue = 0.70)]
        public double VAValueAreaPct { get; set; }
        [Parameter("LVN Ratio", Group = "VP", DefaultValue = 0.20)]
        public double LVNRatio { get; set; }
        [Parameter("HVN Ratio", Group = "VP", DefaultValue = 0.70)]
        public double HVNRatio { get; set; }
        [Parameter("Loc Tol ATR", Group = "VP", DefaultValue = 0.5)]
        public double LocTolATR { get; set; }

        //=== RISK MANAGEMENT ===
        [Parameter("Risk Pct", Group = "Risk", DefaultValue = 1.0)]
        public double RiskPct { get; set; }
        [Parameter("Risk Pct Half Mode", Group = "Risk", DefaultValue = 0.5)]
        public double RiskPct_HalfMode { get; set; }
        [Parameter("Max R:R", Group = "Risk", DefaultValue = 6.0)]
        public double MaxRR { get; set; }
        [Parameter("Min R:R", Group = "Risk", DefaultValue = 2.0)]
        public double MinRR { get; set; }
        [Parameter("Max DD Pct", Group = "Risk", DefaultValue = 5.0)]
        public double MaxDDPct { get; set; }
        [Parameter("Max Consec Losses", Group = "Risk", DefaultValue = 3)]
        public int MaxConsecLosses { get; set; }
        [Parameter("Max Spread Mult", Group = "Risk", DefaultValue = 2.0)]
        public double MaxSpreadMult { get; set; }
        [Parameter("Magic Number", Group = "Risk", DefaultValue = 202604)]
        public int MagicNumber { get; set; }
        [Parameter("Allow Pyramiding", Group = "Risk", DefaultValue = false)]
        public bool AllowPyramiding { get; set; }

        //=== TRADE MANAGEMENT ===
        [Parameter("Use Partial Close", Group = "TradeMgmt", DefaultValue = true)]
        public bool UsePartialClose { get; set; }
        [Parameter("Partial Close Pct", Group = "TradeMgmt", DefaultValue = 50.0)]
        public double PartialClosePct { get; set; }
        [Parameter("Partial Close At R", Group = "TradeMgmt", DefaultValue = 1.0)]
        public double PartialCloseAtR { get; set; }
        [Parameter("Move SL To BE At R", Group = "TradeMgmt", DefaultValue = 1.0)]
        public double MoveSLToBE_AtR { get; set; }
        [Parameter("Use Trailing Stop", Group = "TradeMgmt", DefaultValue = true)]
        public bool UseTrailingStop { get; set; }
        [Parameter("Trail ATR Mult", Group = "TradeMgmt", DefaultValue = 1.0)]
        public double TrailATRMult { get; set; }
        [Parameter("Exit At POC", Group = "TradeMgmt", DefaultValue = true)]
        public bool ExitAtPOC { get; set; }

        //=== VISUALISATION ===
        [Parameter("Show Dashboard", Group = "Viz", DefaultValue = true)]
        public bool ShowDashboard { get; set; }
        [Parameter("Show VP Levels", Group = "Viz", DefaultValue = true)]
        public bool ShowVPLevels { get; set; }
        [Parameter("Show CVD Line", Group = "Viz", DefaultValue = true)]
        public bool ShowCVDLine { get; set; }
        [Parameter("Show Footprint Markers", Group = "Viz", DefaultValue = true)]
        public bool ShowFootprintMarkers { get; set; }
        [Parameter("Show Session Shading", Group = "Viz", DefaultValue = true)]
        public bool ShowSessionShading { get; set; }
        [Parameter("Show Trade Arrows", Group = "Viz", DefaultValue = true)]
        public bool ShowTradeArrows { get; set; }

        //=== SETUP TOGGLES (1-25) ===
        [Parameter("01 AbsBot",   Group = "Setups", DefaultValue = true)]  public bool EnableSetup_01_AbsBot   { get; set; }
        [Parameter("02 AbsTop",   Group = "Setups", DefaultValue = true)]  public bool EnableSetup_02_AbsTop   { get; set; }
        [Parameter("03 CVDBear",  Group = "Setups", DefaultValue = true)]  public bool EnableSetup_03_CVDBear  { get; set; }
        [Parameter("04 CVDBull",  Group = "Setups", DefaultValue = true)]  public bool EnableSetup_04_CVDBull  { get; set; }
        [Parameter("05 VALBnc",   Group = "Setups", DefaultValue = true)]  public bool EnableSetup_05_VALBnc   { get; set; }
        [Parameter("06 VAHFade",  Group = "Setups", DefaultValue = true)]  public bool EnableSetup_06_VAHFade  { get; set; }
        [Parameter("07 POCRet",   Group = "Setups", DefaultValue = true)]  public bool EnableSetup_07_POCRet   { get; set; }
        [Parameter("08 LVNLong",  Group = "Setups", DefaultValue = true)]  public bool EnableSetup_08_LVNLong  { get; set; }
        [Parameter("09 LVNShort", Group = "Setups", DefaultValue = true)]  public bool EnableSetup_09_LVNShort { get; set; }
        [Parameter("10 HVNRej",   Group = "Setups", DefaultValue = false)] public bool EnableSetup_10_HVNRej   { get; set; }
        [Parameter("11 StackBull",Group = "Setups", DefaultValue = true)]  public bool EnableSetup_11_StackBull{ get; set; }
        [Parameter("12 StackBear",Group = "Setups", DefaultValue = true)]  public bool EnableSetup_12_StackBear{ get; set; }
        [Parameter("13 PullStack",Group = "Setups", DefaultValue = true)]  public bool EnableSetup_13_PullStack{ get; set; }
        [Parameter("14 Spring",   Group = "Setups", DefaultValue = true)]  public bool EnableSetup_14_Spring   { get; set; }
        [Parameter("15 Upthrust", Group = "Setups", DefaultValue = true)]  public bool EnableSetup_15_Upthrust { get; set; }
        [Parameter("16 SOS",      Group = "Setups", DefaultValue = true)]  public bool EnableSetup_16_SOS      { get; set; }
        [Parameter("17 LPSY",     Group = "Setups", DefaultValue = true)]  public bool EnableSetup_17_LPSY     { get; set; }
        [Parameter("18 LiqSweep", Group = "Setups", DefaultValue = true)]  public bool EnableSetup_18_LiqSweep { get; set; }
        [Parameter("19 OBReturn", Group = "Setups", DefaultValue = true)]  public bool EnableSetup_19_OBReturn { get; set; }
        [Parameter("20 SMTDiv",   Group = "Setups", DefaultValue = true)]  public bool EnableSetup_20_SMTDiv   { get; set; }
        [Parameter("21 Breaker",  Group = "Setups", DefaultValue = true)]  public bool EnableSetup_21_Breaker  { get; set; }
        [Parameter("22 AMD",      Group = "Setups", DefaultValue = true)]  public bool EnableSetup_22_AMD      { get; set; }
        [Parameter("23 UnfAuc",   Group = "Setups", DefaultValue = true)]  public bool EnableSetup_23_UnfAuc   { get; set; }
        [Parameter("24 PoorHL",   Group = "Setups", DefaultValue = true)]  public bool EnableSetup_24_PoorHL   { get; set; }
        [Parameter("25 Iceberg",  Group = "Setups", DefaultValue = true)]  public bool EnableSetup_25_Iceberg  { get; set; }

        // §22 marginal-gain stack (default off - earn via logged data)
        [Parameter("M1 Require Liquidity Sweep", Group = "M-Refinements", DefaultValue = false)]
        public bool M1_RequireLiquiditySweep { get; set; }
        [Parameter("M2 Require Second Touch", Group = "M-Refinements", DefaultValue = false)]
        public bool M2_RequireSecondTouch { get; set; }
        [Parameter("M3 Use ATR Regime Filter", Group = "M-Refinements", DefaultValue = false)]
        public bool M3_UseATRRegimeFilter { get; set; }
        [Parameter("M5 Use Correlated CVD", Group = "M-Refinements", DefaultValue = false)]
        public bool M5_UseCorrelatedCVD { get; set; }
        [Parameter("M5 Correlated Symbol", Group = "M-Refinements", DefaultValue = "EURGBP")]
        public string M5_CorrelatedSymbol { get; set; }
        [Parameter("M6 Use Sub-Window Tiering", Group = "M-Refinements", DefaultValue = false)]
        public bool M6_UseSubWindowTiering { get; set; }
        [Parameter("M6 Tier B Min Score", Group = "M-Refinements", DefaultValue = 5)]
        public int M6_TierBMinScore { get; set; }

        // Globals
        private DeltaEngine _delta;
        private VolumeProfile _vp;
        private FootprintAnalyzer _fp;
        private SessionGate _sess;
        private HtfAlignment _htf;
        private RiskManager _risk;
        private TradeManager _trade;
        private NotificationCenter _notif;
        private Dashboard _dash;
        private ChartViz _viz;
        private TradeLogger _logger;
        private AverageTrueRange _atr;
        private DateTime _lastDay;
        private int _tradesToday;

        protected override void OnStart()
        {
            _delta  = new DeltaEngine(Symbol, Bars, DeltaLookback);
            _vp     = new VolumeProfile(Symbol, Bars, VPBins, VPLength, VAValueAreaPct, LVNRatio, HVNRatio);
            _fp     = new FootprintAnalyzer(Bars, VolZThreshold, DeltaZThreshold, MinStackedImbalanceRows, ImbalanceRatio);
            _sess   = new SessionGate(SAST_OffsetFromBroker, NYOpen_Blackout_Mins,
                        TradeAsianSession, TradeLondonOpen, TradeLondonMain, TradeNYOpen, TradeNYMain);
            _htf    = new HtfAlignment(this, Symbol);
            _risk   = new RiskManager(this, Symbol, RiskPct, RiskPct_HalfMode,
                        MaxDDPct, MaxConsecLosses, MaxSpreadMult);
            _atr    = Indicators.AverageTrueRange(14, MovingAverageType.Simple);
            _trade  = new TradeManager(this, Symbol, "GODMODE",
                        UsePartialClose, PartialClosePct, PartialCloseAtR, MoveSLToBE_AtR,
                        UseTrailingStop, TrailATRMult, ExitAtPOC, _atr);
            _notif  = new NotificationCenter(this, EnableNotifications, EnableSoundAlerts,
                        EnablePushAlerts, EnableEmailAlerts, () => Bars.OpenTimes.LastValue);
            _dash   = new Dashboard(Chart, Color.Lime, Color.Red, Color.Goldenrod);
            _viz    = new ChartViz(Chart, ShowVPLevels, ShowFootprintMarkers, ShowSessionShading, ShowTradeArrows);
            _logger = new TradeLogger(Path.Combine(Environment.GetFolderPath(
                        Environment.SpecialFolder.MyDocuments), "GODMODE_OFEA_log.csv"));
            // Wire consecutive-loss tracking. Without this hook the kill switch
            // CheckConsecLosses never trips because _consecLosses stays at zero.
            Positions.Closed += OnPositionClosedHook;
            Print("GODMODE_OFEA initialized — mode={0}", OperatingMode);
        }

        private void OnPositionClosedHook(PositionClosedEventArgs args)
        {
            if (args?.Position == null) return;
            if (args.Position.Label != "GODMODE") return;
            try { _risk?.NotifyTradeClosed(args.Position.NetProfit); }
            catch (Exception e) { Print($"OnPositionClosed err: {e.Message}"); }
        }

        protected override void OnTick()
        {
            if (ShowDashboard && _dash.ShouldRefresh()) RefreshDashboard();
            ManageOpenPosition();
        }

        protected override void OnBar()
        {
            HandleDayRollover();
            _delta.OnBarClose();
            _risk.SampleSpread();
            _vp.Recompute();
            RunBarClose();
        }

        protected override void OnStop()
        {
            Positions.Closed -= OnPositionClosedHook;
            _delta?.Detach();
            _dash?.Clear();
        }

        private void HandleDayRollover()
        {
            var today = Server.Time.Date;
            if (today != _lastDay) { _lastDay = today; _tradesToday = 0; _risk.OnDayRollover(); }
        }

        private void ManageOpenPosition()
        {
            if (_trade.FindOpenPosition() == null) return;
            _trade.ManagePosition(_vp.Poc);
            if (_sess.ApproachingNyMainEnd(Server.Time, 5))
            {
                _trade.CloseAll();
                _notif.NL_KillSwitch("NY_MAIN_END");
            }
        }

        // Brief §5 — gates 0..8 in canonical order
        private void RunBarClose()
        {
            // GATE 0
            if (_risk.IsDayHalted) return;
            var gDD = _risk.CheckDailyDrawdown();
            if (!gDD.Passed)
            {
                _notif.NL_KillSwitch($"DD {gDD.Value:F2}%");
                _trade.CloseAll(); _risk.HaltDay(); return;
            }
            var gSp = _risk.CheckSpread();
            if (!gSp.Passed) { _notif.NL_KillSwitch("SPREAD_BLOWOUT"); return; }
            var gCL = _risk.CheckConsecLosses();
            if (!gCL.Passed) { _notif.NL_KillSwitch("CONSEC_LOSSES"); _risk.HaltDay(); return; }

            // GATE 1
            int sastMin;
            var session = _sess.Classify(Server.Time, out sastMin);
            if (_sess.SessionChanged(session) && (session == Session.LdnMain || session == Session.NyMain))
                _notif.NC_KillZone(session);
            if (!_sess.IsSessionEnabled(session) || _sess.InNyOpenBlackout(Server.Time)) return;
            var model = _sess.ModelForSession(session);
            if (model == ActiveModel.M1Trend && !EnableModel1_Trend) return;
            if (model == ActiveModel.M2MeanRev && !EnableModel2_MeanRev) return;

            // GATE 2
            var shape = _vp.Shape;
            var state = _vp.State;
            _notif.NF_ProfileState(shape, state);
            bool stateOK = (model == ActiveModel.M2MeanRev && state == MarketState.Balanced)
                        || (model == ActiveModel.M1Trend   && state == MarketState.Imbalanced);
            if (!stateOK) return;

            // GATE 3
            double lastClose = Bars.ClosePrices.Last(1);
            var loc = _vp.LocationAt(lastClose, LocTolATR * 10.0);
            if (loc == VpLoc.None) return;
            _notif.NA_VpLevel(OFHelpers.LocToStr(loc), lastClose);

            // GATE 4
            var htf = _htf.Combined();
            if (htf != HtfBias.Neutral) _notif.ND_HTFAligned(htf);

            // GATE 5
            double slope = _delta.CvdSlope5();
            var cvdDir = slope > 0 ? TradeDir.Long : (slope < 0 ? TradeDir.Short : TradeDir.None);
            if (cvdDir != TradeDir.None) _notif.NE_CvdConfirm(cvdDir, _delta.Cvd);

            // GATE 6 + routing through 25 detectors
            SetupCandidate best = null; int bestScore = 0;
            ScoreAllSetups(model, htf, cvdDir, loc, ref best, ref bestScore);
            if (best == null) return;

            _notif.NG_FootprintSignal("setup", best.AbsStars);
            if (_delta.VolumeZ() >= AggressionZThreshold) _notif.NH_Aggression(_delta.VolumeZ());

            // GATE 7 + 8
            double risk = Math.Abs(best.Entry - best.Sl);
            double rr = risk > 0 ? Math.Abs(best.Tp - best.Entry) / risk : 0;
            if (rr < MinRR) return;
            // Cap absurd R:R (parameter was previously declared but unused).
            // MT5 build clamps the same way — keep parameter-mirrored behaviour.
            if (MaxRR > 0 && rr > MaxRR)
            {
                double cappedDist = risk * MaxRR;
                best.Tp = best.Direction == TradeDir.Long ? best.Entry + cappedDist : best.Entry - cappedDist;
                rr = MaxRR;
            }
            best.Score = bestScore;
            best.Priority = bestScore >= 5 ? Priority.P1 : (bestScore >= 4 ? Priority.P2 : Priority.P3);
            bool halfSize = HalfSize_OnHTFConflict && !_htf.IsAligned(best.Direction);
            double volume = _risk.ComputeVolume(risk, halfSize);
            if (volume <= 0) return;

            _notif.NI_AplusReady(best, rr);

            // EXECUTE
            if (OperatingMode == OpMode.Auto)
            {
                if (!AllowPyramiding && _trade.FindOpenPosition() != null) return;
                if (_trade.OpenPosition(best.Direction, volume, best.Sl, best.Tp, "GODMODE"))
                {
                    _tradesToday++;
                    _notif.NJ_TradeFired(best, volume, "AUTO");
                    _logger.Append("ENTRY", best, Symbol.Name, session, state, htf, shape,
                        _vp.Poc, _vp.Vah, _vp.Val, _delta.Cvd, _delta.BarDelta,
                        _delta.VolumeZ(), _delta.DeltaZ(), "AUTO", RiskPct, volume);
                }
            }
            else
            {
                _viz.DrawTradeLines(best.Entry, best.Sl, best.Tp, best.Direction);
                _logger.Append("SKIP_F1", best, Symbol.Name, session, state, htf, shape,
                    _vp.Poc, _vp.Vah, _vp.Val, _delta.Cvd, _delta.BarDelta,
                    _delta.VolumeZ(), _delta.DeltaZ(), "MANUAL", RiskPct, 0);
            }
        }

        private void ScoreAllSetups(ActiveModel model, HtfBias htf, TradeDir cvdDir, VpLoc loc,
                                    ref SetupCandidate best, ref int bestScore)
        {
            double tol = LocTolATR * 10.0;
            void Try(SetupCandidate c) { if (c != null) Consider(c, htf, cvdDir, loc, ref best, ref bestScore); }

            if (EnableSetup_01_AbsBot)    Try(SetupDetectors.AbsBot   (Symbol, Bars, _delta, _vp, _fp, tol, MinAbsorptionStars));
            if (EnableSetup_02_AbsTop)    Try(SetupDetectors.AbsTop   (Symbol, Bars, _delta, _vp, _fp, tol, MinAbsorptionStars));
            if (EnableSetup_03_CVDBear)   Try(SetupDetectors.CvdBear  (Symbol, Bars, _delta, _vp, tol));
            if (EnableSetup_04_CVDBull)   Try(SetupDetectors.CvdBull  (Symbol, Bars, _delta, _vp, tol));
            if (EnableSetup_05_VALBnc)    Try(SetupDetectors.ValBounce(Symbol, Bars, _delta, _vp, tol));
            if (EnableSetup_06_VAHFade)   Try(SetupDetectors.VahFade  (Symbol, Bars, _delta, _vp, tol));
            if (EnableSetup_07_POCRet)    Try(SetupDetectors.PocReturn(Symbol, Bars, _delta, _vp, tol));
            if (EnableSetup_08_LVNLong)   Try(SetupDetectors.LvnLong  (Symbol, Bars, _delta, _vp, tol));
            if (EnableSetup_09_LVNShort)  Try(SetupDetectors.LvnShort (Symbol, Bars, _delta, _vp, tol));
            if (EnableSetup_10_HVNRej)    Try(SetupDetectors.HvnRej   (Symbol, Bars, _delta, _vp, tol));
            if (EnableSetup_11_StackBull) Try(SetupDetectors.StackBull(Symbol, Bars, _delta, _vp, _fp, tol));
            if (EnableSetup_12_StackBear) Try(SetupDetectors.StackBear(Symbol, Bars, _delta, _vp, _fp, tol));
            if (EnableSetup_13_PullStack) Try(SetupDetectors.PullStack(Symbol, Bars, _delta, _vp, tol));
            if (EnableSetup_14_Spring)    Try(SetupDetectors.Spring   (Symbol, Bars, _delta, _vp, tol));
            if (EnableSetup_15_Upthrust)  Try(SetupDetectors.Upthrust (Symbol, Bars, _delta, _vp, tol));
            if (EnableSetup_16_SOS)       Try(SetupDetectors.Sos      (Symbol, Bars, _delta, _vp, tol));
            if (EnableSetup_17_LPSY)      Try(SetupDetectors.Lpsy     (Symbol, Bars, _delta, _vp, tol));
            if (EnableSetup_18_LiqSweep)  Try(SetupDetectors.LiqSweep (Symbol, Bars, _delta, _vp, tol));
            if (EnableSetup_19_OBReturn)  Try(SetupDetectors.ObReturn (Symbol, Bars, _delta, _vp, tol));
            if (EnableSetup_20_SMTDiv)    Try(SetupDetectors.SmtDiv   (Symbol, Bars, _delta, _vp, 0.0, tol));
            if (EnableSetup_21_Breaker)   Try(SetupDetectors.Breaker  (Symbol, Bars, _delta, _vp, tol));
            if (EnableSetup_22_AMD)       Try(SetupDetectors.Amd      (Symbol, Bars, _delta, _vp, tol));
            if (EnableSetup_23_UnfAuc)    Try(SetupDetectors.UnfAuc   (Symbol, Bars, _delta, _vp, _fp, _atr, tol));
            if (EnableSetup_24_PoorHL)    Try(SetupDetectors.PoorHL   (Symbol, Bars, _delta, _vp, tol));
            if (EnableSetup_25_Iceberg)   Try(SetupDetectors.Iceberg  (Symbol, Bars, _delta, _vp, _atr, tol));
        }

        private void Consider(SetupCandidate c, HtfBias htf, TradeDir cvdDir, VpLoc loc,
                              ref SetupCandidate best, ref int bestScore)
        {
            int score = 0;
            if (loc != VpLoc.None) score++;
            if (_delta.VolumeZ() >= VolZThreshold) score++;
            if (_delta.BullishDivergence() || _delta.BearishDivergence()) score++;
            if (c.AbsStars >= MinAbsorptionStars) score++;
            int dummy;
            var s = _sess.Classify(Server.Time, out dummy);
            if (s == Session.LdnMain || s == Session.NyMain) score++;

            if (htf != HtfBias.Neutral)
            {
                bool aligned = (c.Direction == TradeDir.Long && htf == HtfBias.Bull)
                            || (c.Direction == TradeDir.Short && htf == HtfBias.Bear);
                if (!aligned && !HalfSize_OnHTFConflict) return;
            }
            if (cvdDir != TradeDir.None && cvdDir != c.Direction) return;
            if (score > bestScore) { bestScore = score; best = c; }
        }

        private void RefreshDashboard()
        {
            int sastMin;
            var s = _sess.Classify(Server.Time, out sastMin);
            var htf = _htf.Combined();
            double slope = _delta.CvdSlope5();
            var cvdDir = slope > 0 ? TradeDir.Long : (slope < 0 ? TradeDir.Short : TradeDir.None);
            double cls = Bars.ClosePrices.Last(1);
            var loc = _vp.LocationAt(cls, LocTolATR * 10.0);
            string mode = OperatingMode == OpMode.Manual ? "MANUAL" : "AUTO";
            _dash.Render(Symbol.Name, mode, _vp.State, s, htf, loc, cvdDir, false,
                0, 0, 0, Priority.None,
                _delta.Cvd, _delta.BarDelta, _delta.VolumeZ(),
                _vp.Poc, _vp.Vah, _vp.Val,
                _risk.DailyDDPct, _tradesToday);
            if (ShowVPLevels) _viz.DrawVPLevels(_vp.Poc, _vp.Vah, _vp.Val);
        }
    }
}
