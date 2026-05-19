//! Engine orchestrator — runs the canonical bar-close gate pipeline 0..=8.
//!
//! Brief §5 + §19 rule 6. Gate ordering is non-negotiable:
//!     GATE 0  Kill switches (DD, spread, consec, news)
//!     GATE 1  F2 Session
//!     GATE 2  F5 State (model ↔ shape)
//!     GATE 3  F1.A Location (POC/VAH/VAL/LVN/HVN)
//!     GATE 4  F3 HTF alignment
//!     GATE 5  F4 CVD confirmation
//!     GATE 6  F1.B Footprint signal (25 detectors → best)
//!     GATE 7  Trigger confirmation (per-detector)
//!     GATE 8  Score & size (RR + sizing)
//!
//! Mirrors the `RunBarClose` method in `GODMODE_OFEA.mq5` and `OnBar` in
//! `GODMODE_OFEA.cs`. Output: `EngineEvent` stream that the application
//! shell turns into UI updates and broker calls.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::common::{
    AccountState, ActiveModel, GateResult, MarketState, OpMode, OrderIntent, Priority,
    Session, SetupCandidate, SetupId, Tick, TradeDir, VpLoc,
};
use crate::dashboard::DashboardSnapshot;
use crate::delta::DeltaEngine;
use crate::footprint::FootprintAnalyzer;
use crate::htf::HtfSnapshot;
use crate::notify::{NotificationCenter, Notification};
use crate::profile::VolumeProfile;
use crate::risk::RiskManager;
use crate::session::SessionGate;
use crate::setups::{run_all, DetectorContext};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EngineConfig {
    pub symbol: String,
    pub mode: OpMode,
    pub lookback: usize,
    pub vp_bins: usize,
    pub vp_length: usize,
    pub vp_va: f64,
    pub vp_lvn_ratio: f64,
    pub vp_hvn_ratio: f64,
    pub vol_z_threshold: f64,
    pub min_stacked_rows: usize,
    pub min_abs_stars: i32,
    pub loc_tol_atr: f64,
    pub min_rr: f64,
    pub aggression_z_threshold: f64,
    pub half_size_on_htf_conflict: bool,
    pub session_offset_hours: i32,
    pub ny_open_blackout_min: i32,
    pub allow_asian: bool,
    pub allow_ldn_open: bool,
    pub allow_ldn_main: bool,
    pub allow_ny_open: bool,
    pub allow_ny_main: bool,
    pub risk_pct: f64,
    pub risk_half_pct: f64,
    pub max_dd_pct: f64,
    pub max_consec_losses: i32,
    pub max_spread_mult: f64,
}

impl Default for EngineConfig {
    fn default() -> Self {
        Self {
            symbol: "EURUSD".into(),
            mode: OpMode::Manual,
            lookback: 100,
            vp_bins: 50,
            vp_length: 96, // ~24h on M15
            vp_va: 0.70,
            vp_lvn_ratio: 0.30,
            vp_hvn_ratio: 0.80,
            vol_z_threshold: 1.5,
            min_stacked_rows: 3,
            min_abs_stars: 3,
            loc_tol_atr: 0.5,
            min_rr: 2.0,
            aggression_z_threshold: 2.0,
            half_size_on_htf_conflict: false,
            session_offset_hours: 2,
            ny_open_blackout_min: 20,
            allow_asian: false,
            allow_ldn_open: true,
            allow_ldn_main: true,
            allow_ny_open: false,
            allow_ny_main: true,
            risk_pct: 1.0,
            risk_half_pct: 0.5,
            max_dd_pct: 5.0,
            max_consec_losses: 3,
            max_spread_mult: 2.0,
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct GateOutcome {
    pub gate: u8,
    pub name: &'static str,
    pub result: GateResult,
}

#[derive(Debug, Clone, Serialize)]
pub enum EngineEvent {
    Gate(GateOutcome),
    Notify(Notification),
    Candidate(SetupCandidate),
    Order(OrderIntent),
    Dashboard(DashboardSnapshot),
}

/// Convenience wrapper bundling a closed bar with optional HTF series and
/// account state. The application shell builds this and hands it to
/// `Engine::on_bar_close`.
#[derive(Debug, Clone)]
pub struct BarCloseInput<'a> {
    pub bars: &'a [crate::common::Bar],
    pub h4_closes: &'a [f64],
    pub d1_closes: &'a [f64],
    pub atr14: f64,
    pub correlated_cvd_slope: f64,
    pub account: AccountState,
}

pub struct Engine {
    pub config: EngineConfig,
    pub delta: DeltaEngine,
    pub profile: VolumeProfile,
    pub footprint: FootprintAnalyzer,
    pub session_gate: SessionGate,
    pub risk: RiskManager,
    pub notif: NotificationCenter,
    pub trades_today: i32,
    pub last_dash_refresh: DateTime<Utc>,
}

impl Engine {
    pub fn new(config: EngineConfig, account: AccountState, now: DateTime<Utc>) -> Self {
        let delta = DeltaEngine::new(config.lookback, account.tick_size);
        let profile = VolumeProfile::new(
            config.vp_bins,
            config.vp_length,
            config.vp_va,
            config.vp_lvn_ratio,
            config.vp_hvn_ratio,
        );
        let footprint = FootprintAnalyzer::new(config.vol_z_threshold, config.min_stacked_rows);
        let session_gate = SessionGate::new(
            config.session_offset_hours,
            config.ny_open_blackout_min,
            config.allow_asian,
            config.allow_ldn_open,
            config.allow_ldn_main,
            config.allow_ny_open,
            config.allow_ny_main,
        );
        let risk = RiskManager::new(
            config.risk_pct,
            config.risk_half_pct,
            config.max_dd_pct,
            config.max_consec_losses,
            config.max_spread_mult,
            account.equity,
            now,
        );
        let notif = NotificationCenter::new(true, true, false, false);
        Self {
            config,
            delta,
            profile,
            footprint,
            session_gate,
            risk,
            notif,
            trades_today: 0,
            last_dash_refresh: now,
        }
    }

    pub fn on_tick(&mut self, t: &Tick) {
        self.delta.on_tick(t);
    }

    /// The full bar-close gate pipeline. Emits an event stream the caller
    /// consumes (UI render, broker order, journal append, etc).
    pub fn on_bar_close(&mut self, input: BarCloseInput<'_>) -> Vec<EngineEvent> {
        let mut events = Vec::with_capacity(16);
        if input.bars.is_empty() {
            return events;
        }
        let last_bar = input.bars[0];
        let now = last_bar.ts_close;

        self.delta.on_bar_close(&last_bar);
        self.risk.sample_spread(input.account.spread);
        self.profile.recompute(input.bars);

        // ---------- GATE 0: kill switches ----------
        if self.risk.day_halted {
            events.push(GateOutcome::fail(0, "Kill", "Day halted").into());
            return events;
        }
        let dd = self.risk.check_daily_drawdown(input.account.equity);
        if !dd.passed {
            self.risk.halt_day();
            if let Some(n) = self.notif.nl_kill_switch("DAILY_DD", now) {
                events.push(EngineEvent::Notify(n));
            }
            events.push(GateOutcome::from(0, "Kill·DD", dd).into());
            return events;
        }
        let sp = self.risk.check_spread(input.account.spread);
        if !sp.passed {
            if let Some(n) = self.notif.nl_kill_switch("SPREAD_BLOWOUT", now) {
                events.push(EngineEvent::Notify(n));
            }
            events.push(GateOutcome::from(0, "Kill·Spread", sp).into());
            return events;
        }
        let cl = self.risk.check_consec_losses();
        if !cl.passed {
            self.risk.halt_day();
            if let Some(n) = self.notif.nl_kill_switch("CONSEC_LOSSES", now) {
                events.push(EngineEvent::Notify(n));
            }
            events.push(GateOutcome::from(0, "Kill·Consec", cl).into());
            return events;
        }
        let nb = self.risk.check_news_blackout(now);
        if !nb.passed {
            if let Some(n) = self.notif.nl_kill_switch("NEWS", now) {
                events.push(EngineEvent::Notify(n));
            }
            events.push(GateOutcome::from(0, "Kill·News", nb).into());
            return events;
        }
        events.push(GateOutcome::pass(0, "Kill").into());

        // ---------- GATE 1: F2 session ----------
        let (session, _sast_min) = self.session_gate.classify(now);
        if self.session_gate.in_ny_open_blackout(now) {
            events.push(
                GateOutcome::fail(1, "F2·Session", "NY-Open blackout").into(),
            );
            return events;
        }
        if !self.session_gate.is_session_enabled(session) {
            events.push(
                GateOutcome::fail(
                    1,
                    "F2·Session",
                    format!("Session {} disabled", crate::common::session_to_str(session)),
                )
                .into(),
            );
            return events;
        }
        if self.session_gate.session_changed(session) {
            if let Some(n) = self.notif.nc_kill_zone(session, now) {
                events.push(EngineEvent::Notify(n));
            }
        }
        let model = self.session_gate.model_for_session(session);
        events.push(GateOutcome::pass(1, "F2·Session").into());

        // ---------- GATE 2: F5 state ----------
        let state = self.profile.state();
        let shape = self.profile.shape;
        if let Some(n) = self.notif.nf_profile_state(shape, state, now) {
            events.push(EngineEvent::Notify(n));
        }
        let model_ok = match model {
            ActiveModel::M2MeanRev => state == MarketState::Balanced,
            ActiveModel::M1Trend => state == MarketState::Imbalanced,
            ActiveModel::None => false,
        };
        if !model_ok {
            events.push(
                GateOutcome::fail(
                    2,
                    "F5·State",
                    format!("Model {:?} mismatched state {:?}", model, state),
                )
                .into(),
            );
            return events;
        }
        events.push(GateOutcome::pass(2, "F5·State").into());

        // ---------- GATE 3: F1.A location ----------
        let loc_tol = (input.atr14 * self.config.loc_tol_atr).max(input.account.tick_size * 5.0);
        let loc = self.profile.location_at(last_bar.close, loc_tol);
        if matches!(loc, VpLoc::None) {
            events.push(
                GateOutcome::fail(3, "F1·Loc", "No VP level near close").into(),
            );
            return events;
        }
        if let Some(n) =
            self.notif
                .na_vp_level(crate::common::loc_to_str(loc), last_bar.close, now)
        {
            events.push(EngineEvent::Notify(n));
        }
        events.push(GateOutcome::pass(3, "F1·Loc").into());

        // ---------- GATE 6 (deferred): footprint scan to find candidates ----------
        // We need a candidate to evaluate F3/F4. Run all detectors first,
        // then filter through GATE 4..GATE 8.
        let ctx = DetectorContext {
            bars: input.bars,
            bid: last_bar.close, // shell can override with live bid/ask
            ask: last_bar.close,
            tick_size: input.account.tick_size,
            pip_size: input.account.pip_size,
            loc_tol,
            min_abs_stars: self.config.min_abs_stars,
            atr14: input.atr14,
            correlated_cvd_slope: input.correlated_cvd_slope,
        };
        let candidates = run_all(ctx, &self.delta, &self.profile, &self.footprint);
        if candidates.is_empty() {
            events.push(GateOutcome::fail(6, "F1.B·Footprint", "No detector fired").into());
            return events;
        }

        // ---------- GATE 4: F3 HTF alignment ----------
        let htf = HtfSnapshot::from_series(input.h4_closes, input.d1_closes);
        let combined_bias = htf.combined();

        // ---------- GATE 5: F4 CVD confirm ----------
        let cvd = self.delta.cvd();

        // ---------- score & filter loop ----------
        let mut best: Option<SetupCandidate> = None;
        let mut best_score: i32 = -1;
        for mut c in candidates {
            // GATE 4
            if !htf.is_aligned(c.direction) && !self.config.half_size_on_htf_conflict {
                continue;
            }
            // GATE 5
            if !self.delta.cvd_agrees(c.direction) {
                continue;
            }
            // GATE 8 part 1 — RR check
            let rr = compute_rr(&c);
            if rr < self.config.min_rr {
                continue;
            }
            // Score (brief §5 GATE 8 — 0..=5)
            let mut score = 0;
            if !matches!(c.loc, VpLoc::None) {
                score += 1;
            }
            if self.delta.volume_z() >= self.config.vol_z_threshold {
                score += 1;
            }
            if (c.direction == TradeDir::Long && self.delta.bullish_divergence())
                || (c.direction == TradeDir::Short && self.delta.bearish_divergence())
            {
                score += 1;
            }
            if c.abs_stars >= self.config.min_abs_stars {
                score += 1;
            }
            if matches!(session, Session::LdnMain | Session::NyMain | Session::LdnOpen) {
                score += 1;
            }
            c.score = score;
            c.priority = if score >= 5 {
                Priority::P1
            } else if score >= 4 {
                Priority::P2
            } else {
                Priority::P3
            };
            if score > best_score {
                best_score = score;
                best = Some(c);
            }
        }
        let Some(best) = best else {
            events.push(GateOutcome::fail(4, "F3/F4/RR", "No candidate survived").into());
            return events;
        };
        if let Some(n) = self.notif.nd_htf_aligned(combined_bias, now) {
            events.push(EngineEvent::Notify(n));
        }
        events.push(GateOutcome::pass(4, "F3·HTF").into());
        if let Some(n) = self.notif.ne_cvd_confirm(best.direction, cvd, now) {
            events.push(EngineEvent::Notify(n));
        }
        events.push(GateOutcome::pass(5, "F4·CVD").into());

        // ---------- GATE 6 fire ----------
        if let Some(n) = self
            .notif
            .ng_footprint_signal(setup_label(best.setup_id), best.abs_stars, now)
        {
            events.push(EngineEvent::Notify(n));
        }
        if self.delta.volume_z() >= self.config.aggression_z_threshold {
            if let Some(n) = self.notif.nh_aggression(self.delta.volume_z(), now) {
                events.push(EngineEvent::Notify(n));
            }
        }
        events.push(GateOutcome::pass(6, "F1.B·Footprint").into());

        // ---------- GATE 7 ----------
        events.push(GateOutcome::pass(7, "Trigger").into());

        // ---------- GATE 8 size ----------
        let sl_distance = (best.entry - best.sl).abs();
        let half = self.config.half_size_on_htf_conflict && !htf.is_aligned(best.direction);
        let volume = self
            .risk
            .compute_volume(&input.account, sl_distance, half);
        if volume <= 0.0 {
            events.push(GateOutcome::fail(8, "Size", "Computed volume = 0").into());
            return events;
        }
        let rr = compute_rr(&best);
        if let Some(n) = self.notif.ni_aplus_ready(&best, rr, now) {
            events.push(EngineEvent::Notify(n));
        }
        events.push(GateOutcome::pass(8, "Score+Size").into());
        events.push(EngineEvent::Candidate(best.clone()));

        // ---------- EXECUTE ----------
        if matches!(self.config.mode, OpMode::Auto) {
            let intent = OrderIntent {
                direction: best.direction,
                entry: best.entry,
                sl: best.sl,
                tp: best.tp,
                volume,
                label: "GODMODE".into(),
                comment: format!(
                    "{}/{}",
                    setup_label(best.setup_id),
                    crate::common::loc_to_str(best.loc)
                ),
            };
            if let Some(n) = self.notif.nj_trade_fired(&best, volume, "AUTO", now) {
                events.push(EngineEvent::Notify(n));
            }
            events.push(EngineEvent::Order(intent));
            self.trades_today += 1;
        } else if let Some(n) = self.notif.nj_trade_fired(&best, volume, "MANUAL", now) {
            events.push(EngineEvent::Notify(n));
        }

        // ---------- dashboard snapshot ----------
        let snap = DashboardSnapshot {
            symbol: self.config.symbol.clone(),
            mode: format!("{:?}", self.config.mode),
            state,
            session,
            bias: combined_bias,
            loc: best.loc,
            cvd_dir: best.direction,
            footprint_ready: true,
            sl: best.sl,
            rr,
            score: best.score,
            priority: best.priority,
            cvd,
            bar_delta: self.delta.bar_delta(),
            vol_z: self.delta.volume_z(),
            poc: self.profile.poc,
            vah: self.profile.vah,
            val: self.profile.val,
            daily_dd_pct: self.risk.daily_dd_pct(input.account.equity),
            trades_today: self.trades_today,
            last_refresh: now,
        };
        events.push(EngineEvent::Dashboard(snap));
        events
    }
}

fn compute_rr(c: &SetupCandidate) -> f64 {
    let risk = (c.entry - c.sl).abs();
    let reward = (c.tp - c.entry).abs();
    if risk <= 0.0 {
        0.0
    } else {
        reward / risk
    }
}

fn setup_label(id: SetupId) -> &'static str {
    match id {
        SetupId::AbsBot => "AbsBot",
        SetupId::AbsTop => "AbsTop",
        SetupId::CvdBear => "CvdBear",
        SetupId::CvdBull => "CvdBull",
        SetupId::ValBnc => "ValBnc",
        SetupId::VahFade => "VahFade",
        SetupId::PocRet => "PocRet",
        SetupId::LvnLong => "LvnLong",
        SetupId::LvnShort => "LvnShort",
        SetupId::HvnRej => "HvnRej",
        SetupId::StackBull => "StackBull",
        SetupId::StackBear => "StackBear",
        SetupId::PullStack => "PullStack",
        SetupId::Spring => "Spring",
        SetupId::Upthrust => "Upthrust",
        SetupId::Sos => "SOS",
        SetupId::Lpsy => "LPSY",
        SetupId::LiqSweep => "LiqSweep",
        SetupId::ObReturn => "ObReturn",
        SetupId::SmtDiv => "SmtDiv",
        SetupId::Breaker => "Breaker",
        SetupId::Amd => "AMD",
        SetupId::UnfAuc => "UnfAuc",
        SetupId::PoorHL => "PoorHL",
        SetupId::Iceberg => "Iceberg",
        SetupId::None => "-",
    }
}

impl GateOutcome {
    fn pass(gate: u8, name: &'static str) -> Self {
        Self {
            gate,
            name,
            result: GateResult::pass("ok"),
        }
    }
    fn fail(gate: u8, name: &'static str, reason: impl Into<String>) -> Self {
        Self {
            gate,
            name,
            result: GateResult::fail(reason),
        }
    }
    fn from(gate: u8, name: &'static str, result: GateResult) -> Self {
        Self { gate, name, result }
    }
}

impl From<GateOutcome> for EngineEvent {
    fn from(g: GateOutcome) -> Self {
        EngineEvent::Gate(g)
    }
}
