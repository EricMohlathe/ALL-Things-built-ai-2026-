//+------------------------------------------------------------------+
//|                                                  GODMODE_OFEA.mq5|
//|                                                                  |
//|  Markets spend 70-80% of their time in balance and 20-30% in     |
//|  imbalance. The edge is not predicting which state is next - it  |
//|  is reacting to state-change signatures left by institutions:    |
//|  absorption, stacked imbalances, CVD divergence, and aggression  |
//|  prints, at high-probability volume-profile locations, during    |
//|  high-probability sessions, with HTF alignment.                  |
//|                                                                  |
//|  Operator priority: capital protection > expectancy > win rate.  |
//|                                                                  |
//|  Source authority: brief §1 thesis, §2 5-gate stack,             |
//|  §3 8-row dashboard, §4 N-A..N-L cascade, §5 bar-close pipeline, |
//|  §6 25-setup catalogue, §7 input schema, §11 algorithms,         |
//|  §12 kill switches, §15 code quality.                            |
//+------------------------------------------------------------------+
#property copyright   "GODMODE_OFEA"
#property version     "1.00"
#property description "Order-flow EA — 5 gates + 25 setups + dashboard + cascade"
#property strict

#include "../../Include/OF_Common.mqh"
#include "../../Include/OF_Logger.mqh"
#include "../../Include/OF_DeltaEngine.mqh"
#include "../../Include/OF_VolumeProfile.mqh"
#include "../../Include/OF_FootprintAnalyzer.mqh"
#include "../../Include/OF_AbsorptionStars.mqh"
#include "../../Include/OF_SessionGate.mqh"
#include "../../Include/OF_HTFAlignment.mqh"
#include "../../Include/OF_RiskManager.mqh"
#include "../../Include/OF_TradeManager.mqh"
#include "../../Include/OF_NotificationCenter.mqh"
#include "../../Include/OF_Dashboard.mqh"
#include "../../Include/OF_ChartViz.mqh"
#include "../../Include/OF_SetupDetectors.mqh"

//=== MODE & PLATFORM ===
input ENUM_OPMODE OperatingMode      = OPMODE_MANUAL;     // brief §0 default
input bool        EnableNotifications = true;
input bool        EnablePushAlerts    = true;
input bool        EnableSoundAlerts   = true;
input bool        EnableEmailAlerts   = false;

//=== STRATEGY MASTER ===
input bool   EnableModel1_Trend       = true;
input bool   EnableModel2_MeanRev     = true;
input bool   HalfSize_OnHTFConflict   = false;

//=== SESSION (SAST UTC+2) ===
input int    SAST_OffsetFromBroker    = 0;     // adjust if broker time != UTC
input bool   TradeAsianSession        = false;
input bool   TradeLondonOpen          = false;
input bool   TradeLondonMain          = true;
input bool   TradeNYOpen              = false;
input bool   TradeNYMain              = true;
input int    NYOpen_Blackout_Mins     = 20;

//=== ORDER FLOW DETECTION ===
input int    DeltaLookback            = 20;
input double VolZThreshold            = 1.5;
input double DeltaZThreshold          = 2.0;
input double AggressionZThreshold     = 2.0;
input int    MinAbsorptionStars       = 3;
input int    MinStackedImbalanceRows  = 3;
input double ImbalanceRatio           = 3.0;

//=== VOLUME PROFILE ===
input int    VPLength                 = 100;
input int    VPBins                   = 50;
input double VAValueAreaPct           = 0.70;
input double LVNRatio                 = 0.20;
input double HVNRatio                 = 0.70;
input double LocTolATR                = 0.5;

//=== RISK MANAGEMENT ===
input double RiskPct                  = 1.0;
input double RiskPct_HalfMode         = 0.5;
input double MaxRR                    = 6.0;
input double MinRR                    = 2.0;
input double MaxDDPct                 = 5.0;
input int    MaxConsecLosses          = 3;
input double MaxSpreadMult            = 2.0;
input long   MagicNumber              = 202604;
input bool   AllowPyramiding          = false;

//=== TRADE MANAGEMENT ===
input bool   UsePartialClose          = true;
input double PartialClosePct          = 50.0;
input double PartialCloseAtR          = 1.0;
input double MoveSLToBE_AtR           = 1.0;
input bool   UseTrailingStop          = true;
input double TrailATRMult             = 1.0;
input bool   ExitAtPOC                = true;

//=== VISUALISATION ===
input bool   ShowDashboard            = true;
input bool   ShowVPLevels             = true;
input bool   ShowCVDLine              = true;
input bool   ShowFootprintMarkers     = true;
input bool   ShowSessionShading       = true;
input bool   ShowTradeArrows          = true;
input color  DashboardColor_OK        = clrLime;
input color  DashboardColor_FAIL      = clrRed;
input color  DashboardColor_WAIT      = clrGoldenrod;

//=== SETUP TOGGLES (1–25) ===
input bool EnableSetup_01_AbsBot   = true;
input bool EnableSetup_02_AbsTop   = true;
input bool EnableSetup_03_CVDBear  = true;
input bool EnableSetup_04_CVDBull  = true;
input bool EnableSetup_05_VALBnc   = true;
input bool EnableSetup_06_VAHFade  = true;
input bool EnableSetup_07_POCRet   = true;
input bool EnableSetup_08_LVNLong  = true;
input bool EnableSetup_09_LVNShort = true;
input bool EnableSetup_10_HVNRej   = false;     // B-grade, default OFF (brief §6)
input bool EnableSetup_11_StackBull= true;
input bool EnableSetup_12_StackBear= true;
input bool EnableSetup_13_PullStack= true;
input bool EnableSetup_14_Spring   = true;
input bool EnableSetup_15_Upthrust = true;
input bool EnableSetup_16_SOS      = true;
input bool EnableSetup_17_LPSY     = true;
input bool EnableSetup_18_LiqSweep = true;
input bool EnableSetup_19_OBReturn = true;
input bool EnableSetup_20_SMTDiv   = true;
input bool EnableSetup_21_Breaker  = true;
input bool EnableSetup_22_AMD      = true;
input bool EnableSetup_23_UnfAuc   = true;
input bool EnableSetup_24_PoorHL   = true;
input bool EnableSetup_25_Iceberg  = true;

//=== §22 marginal-gain stack (default OFF — earn via logged data) ===
input bool   M1_RequireLiquiditySweep = false;
input int    M1_SweepLookbackBars     = 10;
input bool   M2_RequireSecondTouch    = false;
input int    M2_TouchLookbackBars     = 30;
input double M2_TouchTolPips          = 3.0;
input bool   M3_UseATRRegimeFilter    = false;
input double M3_MinATRRatio           = 0.70;
input double M3_MaxATRRatio           = 1.50;
input bool   M5_UseCorrelatedCVD      = false;
input string M5_CorrelatedSymbol      = "EURGBP";
input bool   M5_HalfSizeOnNeutral     = true;
input bool   M6_UseSubWindowTiering   = false;
input int    M6_TierBMinScore         = 5;

//+------------------------------------------------------------------+
//| Globals                                                          |
//+------------------------------------------------------------------+
CDeltaEngine          g_de;
CVolumeProfile        g_vp;
CFootprintAnalyzer    g_fp;
CSessionGate          g_sess;
CHtfAlignment         g_htf;
CRiskManager          g_risk;
CTradeManager         g_trade;
CNotificationCenter   g_notif;
CDashboard            g_dash;
CChartViz             g_viz;

datetime              g_lastBarTime  = 0;
int                   g_tradesToday  = 0;
datetime              g_lastDay      = 0;

//+------------------------------------------------------------------+
//| OnInit                                                           |
//+------------------------------------------------------------------+
int OnInit()
  {
   g_de.Init(_Symbol, DeltaLookback);
   g_vp.Init(_Symbol, VPBins, VPLength, VAValueAreaPct, LVNRatio, HVNRatio);
   g_fp.Init(_Symbol, VolZThreshold, DeltaZThreshold, MinStackedImbalanceRows, ImbalanceRatio);
   g_sess.Init(SAST_OffsetFromBroker, NYOpen_Blackout_Mins,
               TradeAsianSession, TradeLondonOpen, TradeLondonMain, TradeNYOpen, TradeNYMain);
   if(!g_htf.Init(_Symbol)) { Print("HTF init failed"); return INIT_FAILED; }
   g_risk.Init(_Symbol, MagicNumber, RiskPct, RiskPct_HalfMode,
               MaxDDPct, MaxConsecLosses, MaxSpreadMult);
   g_trade.Init(_Symbol, MagicNumber, "GODMODE",
                UsePartialClose, PartialClosePct, PartialCloseAtR, MoveSLToBE_AtR,
                UseTrailingStop, TrailATRMult, ExitAtPOC);
   g_notif.Init(EnableNotifications, EnableSoundAlerts, EnablePushAlerts, EnableEmailAlerts);
   g_dash.Init("godmode_", DashboardColor_OK, DashboardColor_FAIL, DashboardColor_WAIT);
   g_viz.Init("godmode_", ShowVPLevels, ShowFootprintMarkers, ShowSessionShading, ShowTradeArrows);
   g_lastBarTime = 0; g_tradesToday = 0; g_lastDay = 0;
   Print("GODMODE_OFEA initialized — mode=", (OperatingMode == OPMODE_MANUAL ? "MANUAL" : "AUTO"));
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| OnDeinit                                                         |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   g_dash.Deinit();
   g_viz.Deinit();
   g_htf.Deinit();
   // Release every iATR handle the shared ATR() helper opened during the
   // run — otherwise each optimization pass leaks one handle per (sym,tf)
   // tuple and the terminal eventually rejects new iATR() calls.
   OF_AtrCacheRelease();
  }

//+------------------------------------------------------------------+
//| OnTick — accumulate per-tick deltas, refresh dashboard           |
//+------------------------------------------------------------------+
void OnTick()
  {
   g_de.OnTickAccumulate();
   if(g_de.DetectNewBar()) RunBarClose();
   if(ShowDashboard && g_dash.ShouldRefresh()) RefreshDashboard();
   ManageOpenPosition();
  }

//+------------------------------------------------------------------+
//| Day rollover guard                                               |
//+------------------------------------------------------------------+
void HandleDayRollover()
  {
   MqlDateTime t; TimeToStruct(TimeCurrent(), t);
   const datetime today = StringToTime(StringFormat("%04d.%02d.%02d", t.year, t.mon, t.day));
   if(today != g_lastDay)
     {
      g_lastDay = today;
      g_tradesToday = 0;
      g_risk.OnDayRollover();
     }
  }

//+------------------------------------------------------------------+
//| Manage existing position every tick                              |
//+------------------------------------------------------------------+
void ManageOpenPosition()
  {
   if(!g_trade.HasOpenPosition()) return;
   const double poc = g_vp.POC();
   g_trade.ManagePosition(poc);
   if(g_sess.ApproachingNyMainEnd(5))
     { g_trade.CloseAll(); g_notif.NL_KillSwitch("NY_MAIN_END"); }
  }

//+------------------------------------------------------------------+
//| Bar-close pipeline — gates 0..8 in canonical order (brief §5)    |
//+------------------------------------------------------------------+
void RunBarClose()
  {
   HandleDayRollover();
   g_de.OnBarClose();
   g_risk.SampleSpread();
   g_vp.Recompute();

   //=== GATE 0 — KILL SWITCHES ===
   if(g_risk.IsDayHalted()) { return; }
   const GateResult gDD = g_risk.CheckDailyDrawdown();
   if(!gDD.passed)
     {
      g_notif.NL_KillSwitch(StringFormat("DD %.2f%%", gDD.value));
      g_trade.CloseAll(); g_risk.HaltDay(); return;
     }
   const GateResult gSp = g_risk.CheckSpread();
   if(!gSp.passed) { g_notif.NL_KillSwitch("SPREAD_BLOWOUT"); return; }
   const GateResult gCL = g_risk.CheckConsecLosses();
   if(!gCL.passed) { g_notif.NL_KillSwitch("CONSEC_LOSSES"); g_risk.HaltDay(); return; }

   //=== GATE 1 — F2 SESSION ===
   int sastMin = 0;
   const ENUM_SESSION sess = g_sess.Classify(sastMin);
   if(g_sess.SessionChanged(sess) &&
      (sess == SESSION_LDN_MAIN || sess == SESSION_NY_MAIN))
      g_notif.NC_KillZone(sess);
   if(!g_sess.IsSessionEnabled(sess) || g_sess.InNyOpenBlackout())
      return;
   const ENUM_ACTIVE_MODEL model = g_sess.ModelForSession(sess);
   if(model == MODEL_M1_TREND  && !EnableModel1_Trend)   return;
   if(model == MODEL_M2_MEANREV && !EnableModel2_MeanRev) return;

   //=== GATE 2 — F5 STATE ===
   const ENUM_PROFILE_SHAPE shape = g_vp.Shape();
   const ENUM_MARKET_STATE  state = g_vp.State();
   g_notif.NF_ProfileState(shape, state);
   const bool stateOK =
      (model == MODEL_M2_MEANREV && state == STATE_BALANCED) ||
      (model == MODEL_M1_TREND   && state == STATE_IMBALANCED);
   if(!stateOK) return;

   //=== GATE 3 — F1.A LOCATION ===
   const double lastClose = iClose(_Symbol, _Period, 1);
   const ENUM_VP_LOC loc = g_vp.LocationAt(lastClose, LocTolATR * 10.0);
   if(loc == LOC_NONE) return;
   g_notif.NA_VpLevel(LocToStr(loc), lastClose);

   //=== GATE 4 — F3 HTF ALIGNMENT (deferred — direction set by detectors) ===
   const ENUM_HTF_BIAS htf = g_htf.Combined();
   if(htf != BIAS_NEUTRAL) g_notif.ND_HTFAligned(htf);

   //=== GATE 5 — F4 CVD CONFIRMATION (direction-aware further down) ===
   const double cvd = g_de.Cvd();
   const double slope = g_de.CvdSlope5();
   const ENUM_DIR cvdDir = (slope > 0) ? DIR_LONG : (slope < 0 ? DIR_SHORT : DIR_NONE);
   if(cvdDir != DIR_NONE) g_notif.NE_CvdConfirm(cvdDir, cvd);

   //=== GATE 6 — F1.B FOOTPRINT SIGNAL ===
   //=== Routed via the 25 setup detectors below ===
   SetupCandidate best; ResetSetupCandidate(best);
   int bestScore = 0;
   ScoreAllSetups(model, htf, cvdDir, loc, best, bestScore);
   if(best.setupId == SETUP_NONE) return;

   g_notif.NG_FootprintSignal("setup", best.absStars);
   if(g_de.VolumeZ() >= AggressionZThreshold) g_notif.NH_AggressionTrigger(g_de.VolumeZ());

   //=== GATE 7 — TRIGGER + GATE 8 — SCORE & SIZE ===
   const double risk = MathAbs(best.entry - best.sl);
   const double rr   = (risk > 0) ? MathAbs(best.tp - best.entry) / risk : 0.0;
   if(rr < MinRR) return;
   best.score    = bestScore;
   best.priority = (bestScore >= 5) ? PRIO_P1 : (bestScore >= 4 ? PRIO_P2 : PRIO_P3);
   const bool halfSize = HalfSize_OnHTFConflict && !g_htf.IsAligned(best.direction);
   const double lots = g_risk.ComputeLots(risk, halfSize);
   if(lots <= 0) return;

   g_notif.NI_AplusReady(best, rr);

   //=== EXECUTE (AUTO only) ===
   if(OperatingMode == OPMODE_AUTO)
     {
      if(!AllowPyramiding && g_trade.HasOpenPosition()) return;
      if(g_trade.OpenPosition(best.direction, lots, best.sl, best.tp, "GODMODE"))
        {
         g_tradesToday++;
         g_notif.NJ_TradeFired(best, lots, "AUTO");
         OFLog_AppendCsv(OFLog_FmtRow("ENTRY", best, _Symbol, sess, state, htf, shape,
                                      g_vp.POC(), g_vp.VAH(), g_vp.VAL(),
                                      cvd, g_de.BarDelta(), g_de.VolumeZ(), g_de.DeltaZ(),
                                      "AUTO", RiskPct, lots));
        }
     }
   else
     {
      g_viz.DrawTradeLines(best.entry, best.sl, best.tp, iTime(_Symbol, _Period, 1), best.direction);
      OFLog_AppendCsv(OFLog_FmtRow("SKIP_F1", best, _Symbol, sess, state, htf, shape,
                                   g_vp.POC(), g_vp.VAH(), g_vp.VAL(),
                                   cvd, g_de.BarDelta(), g_de.VolumeZ(), g_de.DeltaZ(),
                                   "MANUAL", RiskPct, 0.0));
     }
  }

//+------------------------------------------------------------------+
//| Iterate the 25 detectors, pick highest-priority candidate        |
//+------------------------------------------------------------------+
void ScoreAllSetups(const ENUM_ACTIVE_MODEL model, const ENUM_HTF_BIAS htf,
                    const ENUM_DIR cvdDir, const ENUM_VP_LOC loc,
                    SetupCandidate &best, int &bestScore)
  {
   const double tol = LocTolATR * 10.0;
   SetupCandidate c;

   #define TRY(name, cond, fn) \
     if(cond) { ResetSetupCandidate(c); if(fn) ConsiderCandidate(c, model, htf, cvdDir, loc, best, bestScore); }

   TRY("01", EnableSetup_01_AbsBot,    Detect_Setup01_AbsBot   (_Symbol, g_de, g_vp, g_fp, tol, MinAbsorptionStars, c));
   TRY("02", EnableSetup_02_AbsTop,    Detect_Setup02_AbsTop   (_Symbol, g_de, g_vp, g_fp, tol, MinAbsorptionStars, c));
   TRY("03", EnableSetup_03_CVDBear,   Detect_Setup03_CvdBear  (_Symbol, g_de, g_vp, tol, c));
   TRY("04", EnableSetup_04_CVDBull,   Detect_Setup04_CvdBull  (_Symbol, g_de, g_vp, tol, c));
   TRY("05", EnableSetup_05_VALBnc,    Detect_Setup05_ValBounce(_Symbol, g_de, g_vp, tol, c));
   TRY("06", EnableSetup_06_VAHFade,   Detect_Setup06_VahFade  (_Symbol, g_de, g_vp, tol, c));
   TRY("07", EnableSetup_07_POCRet,    Detect_Setup07_PocReturn(_Symbol, g_de, g_vp, tol, c));
   TRY("08", EnableSetup_08_LVNLong,   Detect_Setup08_LvnLong  (_Symbol, g_de, g_vp, tol, c));
   TRY("09", EnableSetup_09_LVNShort,  Detect_Setup09_LvnShort (_Symbol, g_de, g_vp, tol, c));
   TRY("10", EnableSetup_10_HVNRej,    Detect_Setup10_HvnRej   (_Symbol, g_de, g_vp, tol, c));
   TRY("11", EnableSetup_11_StackBull, Detect_Setup11_StackBull(_Symbol, g_de, g_vp, g_fp, tol, c));
   TRY("12", EnableSetup_12_StackBear, Detect_Setup12_StackBear(_Symbol, g_de, g_vp, g_fp, tol, c));
   TRY("13", EnableSetup_13_PullStack, Detect_Setup13_PullStack(_Symbol, g_de, g_vp, tol, c));
   TRY("14", EnableSetup_14_Spring,    Detect_Setup14_Spring   (_Symbol, g_de, g_vp, tol, c));
   TRY("15", EnableSetup_15_Upthrust,  Detect_Setup15_Upthrust (_Symbol, g_de, g_vp, tol, c));
   TRY("16", EnableSetup_16_SOS,       Detect_Setup16_Sos      (_Symbol, g_de, g_vp, tol, c));
   TRY("17", EnableSetup_17_LPSY,      Detect_Setup17_Lpsy     (_Symbol, g_de, g_vp, tol, c));
   TRY("18", EnableSetup_18_LiqSweep,  Detect_Setup18_LiqSweep (_Symbol, g_de, g_vp, tol, c));
   TRY("19", EnableSetup_19_OBReturn,  Detect_Setup19_ObReturn (_Symbol, g_de, g_vp, tol, c));
   TRY("20", EnableSetup_20_SMTDiv,    Detect_Setup20_SmtDiv   (_Symbol, g_de, g_vp, 0.0, tol, c));
   TRY("21", EnableSetup_21_Breaker,   Detect_Setup21_Breaker  (_Symbol, g_de, g_vp, tol, c));
   TRY("22", EnableSetup_22_AMD,       Detect_Setup22_Amd      (_Symbol, g_de, g_vp, tol, c));
   TRY("23", EnableSetup_23_UnfAuc,    Detect_Setup23_UnfAuc   (_Symbol, g_de, g_vp, g_fp, tol, c));
   TRY("24", EnableSetup_24_PoorHL,    Detect_Setup24_PoorHL   (_Symbol, g_de, g_vp, tol, c));
   TRY("25", EnableSetup_25_Iceberg,   Detect_Setup25_Iceberg  (_Symbol, g_de, g_vp, tol, c));

   #undef TRY
  }

//+------------------------------------------------------------------+
//| Score a candidate (brief §5 GATE 8)                              |
//+------------------------------------------------------------------+
void ConsiderCandidate(const SetupCandidate &c, const ENUM_ACTIVE_MODEL model,
                       const ENUM_HTF_BIAS htf, const ENUM_DIR cvdDir,
                       const ENUM_VP_LOC loc, SetupCandidate &best, int &bestScore)
  {
   int score = 0;
   if(loc != LOC_NONE) score++;                    // VP level
   if(g_de.VolumeZ() >= VolZThreshold) score++;     // delta confirms via vol-z
   if(g_de.BullishDivergence() || g_de.BearishDivergence()) score++; // divergence
   if(c.absStars >= MinAbsorptionStars) score++;    // absorption
   int dummyMin = 0;
   const ENUM_SESSION s = g_sess.Classify(dummyMin);
   if(s == SESSION_LDN_MAIN || s == SESSION_NY_MAIN) score++;
   // HTF gate (brief F3) — block if conflict and half-size disabled
   if(htf != BIAS_NEUTRAL)
     {
      const bool aligned = (c.direction == DIR_LONG && htf == BIAS_BULL) ||
                           (c.direction == DIR_SHORT && htf == BIAS_BEAR);
      if(!aligned && !HalfSize_OnHTFConflict) return;
     }
   // CVD direction — must agree
   if(cvdDir != DIR_NONE && cvdDir != c.direction) return;

   if(score > bestScore) { bestScore = score; best = c; }
  }

//+------------------------------------------------------------------+
//| Refresh dashboard                                                |
//+------------------------------------------------------------------+
void RefreshDashboard()
  {
   int sastMin = 0;
   const ENUM_SESSION s = g_sess.Classify(sastMin);
   const ENUM_HTF_BIAS htf = g_htf.Combined();
   const double cvd = g_de.Cvd();
   const double slope = g_de.CvdSlope5();
   const ENUM_DIR cvdDir = (slope > 0) ? DIR_LONG : (slope < 0 ? DIR_SHORT : DIR_NONE);
   const double cls = iClose(_Symbol, _Period, 1);
   const ENUM_VP_LOC loc = g_vp.LocationAt(cls, LocTolATR * 10.0);
   const string mode = OperatingMode == OPMODE_MANUAL ? "MANUAL" : "AUTO";
   g_dash.Render(_Symbol, mode, g_vp.State(), s, htf, loc,
                 cvdDir, false, 0.0, 0.0, 0, PRIO_NONE,
                 cvd, g_de.BarDelta(), g_de.VolumeZ(),
                 g_vp.POC(), g_vp.VAH(), g_vp.VAL(),
                 g_risk.DailyDDPct(), g_tradesToday);
   if(ShowVPLevels) g_viz.DrawVPLevels(g_vp.POC(), g_vp.VAH(), g_vp.VAL());
  }
//+------------------------------------------------------------------+
