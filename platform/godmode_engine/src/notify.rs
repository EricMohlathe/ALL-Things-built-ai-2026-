//! Notification cascade — N-A through N-L.
//!
//! Mirrors `OF_NotificationCenter.mqh` and `NotificationCenter.cs`. Brief §4.
//! Edge-detected (FALSE→TRUE per bar) and rate-limited via a tag → bar-time
//! map. The application shell turns `Notification` events into chart toasts,
//! sounds, push notifications, etc.

use std::collections::HashMap;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::common::{HtfBias, MarketState, ProfileShape, Session, SetupCandidate, TradeDir};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum NotifKind {
    /// N-A — VP level touch.
    VpLevel,
    /// N-B — triple confluence achieved.
    TripleConfluence,
    /// N-C — kill-zone (session) entry.
    KillZone,
    /// N-D — HTF aligned.
    HtfAligned,
    /// N-E — CVD confirmation.
    CvdConfirm,
    /// N-F — profile state classified.
    ProfileState,
    /// N-G — footprint signal.
    FootprintSignal,
    /// N-H — aggression spike.
    Aggression,
    /// N-I — A+ entry ready.
    AplusReady,
    /// N-J — order placed (AUTO mode).
    TradeFired,
    /// N-K — position event (partial / BE / trail / POC exit).
    PositionEvent,
    /// N-L — kill switch.
    KillSwitch,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Notification {
    pub kind: NotifKind,
    pub tag: String,
    pub msg: String,
    pub ts: DateTime<Utc>,
}

pub struct NotificationCenter {
    enabled: bool,
    pub sound: bool,
    pub push: bool,
    pub email: bool,
    last_fired: HashMap<String, DateTime<Utc>>,
}

impl NotificationCenter {
    pub fn new(enabled: bool, sound: bool, push: bool, email: bool) -> Self {
        Self {
            enabled,
            sound,
            push,
            email,
            last_fired: HashMap::new(),
        }
    }

    fn should_fire(&mut self, tag: &str, current_bar: DateTime<Utc>) -> bool {
        if !self.enabled {
            return false;
        }
        if let Some(prev) = self.last_fired.get(tag) {
            if *prev == current_bar {
                return false;
            }
        }
        self.last_fired.insert(tag.to_owned(), current_bar);
        true
    }

    fn emit(
        &mut self,
        kind: NotifKind,
        tag: impl Into<String>,
        msg: impl Into<String>,
        bar: DateTime<Utc>,
    ) -> Option<Notification> {
        let tag = tag.into();
        if !self.should_fire(&tag, bar) {
            return None;
        }
        Some(Notification {
            kind,
            tag,
            msg: msg.into(),
            ts: bar,
        })
    }

    pub fn na_vp_level(&mut self, lvl: &str, price: f64, bar: DateTime<Utc>) -> Option<Notification> {
        self.emit(
            NotifKind::VpLevel,
            "N-A",
            format!("VP {lvl} touch @ {price:.5}"),
            bar,
        )
    }

    pub fn nb_triple_confluence(&mut self, bar: DateTime<Utc>) -> Option<Notification> {
        self.emit(NotifKind::TripleConfluence, "N-B", "Triple confluence achieved", bar)
    }

    pub fn nc_kill_zone(&mut self, s: Session, bar: DateTime<Utc>) -> Option<Notification> {
        self.emit(
            NotifKind::KillZone,
            "N-C",
            format!("Kill zone active: {}", crate::common::session_to_str(s)),
            bar,
        )
    }

    pub fn nd_htf_aligned(&mut self, b: HtfBias, bar: DateTime<Utc>) -> Option<Notification> {
        self.emit(
            NotifKind::HtfAligned,
            "N-D",
            format!("HTF aligned: {}", crate::common::bias_to_str(b)),
            bar,
        )
    }

    pub fn ne_cvd_confirm(&mut self, d: TradeDir, cvd: f64, bar: DateTime<Utc>) -> Option<Notification> {
        self.emit(
            NotifKind::CvdConfirm,
            "N-E",
            format!(
                "CVD confirms {} (CVD={cvd:.0})",
                crate::common::dir_to_str(d)
            ),
            bar,
        )
    }

    pub fn nf_profile_state(
        &mut self,
        sh: ProfileShape,
        st: MarketState,
        bar: DateTime<Utc>,
    ) -> Option<Notification> {
        self.emit(
            NotifKind::ProfileState,
            "N-F",
            format!(
                "Shape {} state {}",
                crate::common::shape_to_str(sh),
                st as i32
            ),
            bar,
        )
    }

    pub fn ng_footprint_signal(&mut self, kind: &str, stars: i32, bar: DateTime<Utc>) -> Option<Notification> {
        self.emit(
            NotifKind::FootprintSignal,
            "N-G",
            format!("Footprint {kind} ★{stars}"),
            bar,
        )
    }

    pub fn nh_aggression(&mut self, vol_z: f64, bar: DateTime<Utc>) -> Option<Notification> {
        self.emit(
            NotifKind::Aggression,
            "N-H",
            format!("Aggression vol Z={vol_z:.2}"),
            bar,
        )
    }

    pub fn ni_aplus_ready(&mut self, c: &SetupCandidate, rr: f64, bar: DateTime<Utc>) -> Option<Notification> {
        self.emit(
            NotifKind::AplusReady,
            "N-I",
            format!(
                "A+ READY {} setup={} score={} R:R={rr:.1}",
                crate::common::dir_to_str(c.direction),
                c.setup_id as i32,
                c.score
            ),
            bar,
        )
    }

    pub fn nj_trade_fired(
        &mut self,
        c: &SetupCandidate,
        lots: f64,
        mode: &str,
        bar: DateTime<Utc>,
    ) -> Option<Notification> {
        self.emit(
            NotifKind::TradeFired,
            "N-J",
            format!(
                "{} {lots:.2} units @ {:.5} SL {:.5} TP {:.5} [{mode}]",
                crate::common::dir_to_str(c.direction),
                c.entry,
                c.sl,
                c.tp
            ),
            bar,
        )
    }

    pub fn nk_position_event(&mut self, ev: &str, bar: DateTime<Utc>) -> Option<Notification> {
        self.emit(
            NotifKind::PositionEvent,
            format!("N-K_{ev}"),
            format!("Position event: {ev}"),
            bar,
        )
    }

    pub fn nl_kill_switch(&mut self, reason: &str, bar: DateTime<Utc>) -> Option<Notification> {
        self.emit(
            NotifKind::KillSwitch,
            format!("N-L_{reason}"),
            format!("KILL SWITCH: {reason}"),
            bar,
        )
    }
}
