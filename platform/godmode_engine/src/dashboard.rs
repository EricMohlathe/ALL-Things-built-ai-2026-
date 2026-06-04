//! Dashboard view-model — pure data, no rendering.
//!
//! The application shell (Tauri/Electron + React) consumes a
//! [`DashboardSnapshot`] each bar close and renders the 8-row panel.
//! This module mirrors `OF_Dashboard.mqh` and `Dashboard.cs` but stops
//! short of doing any chart drawing.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::common::{HtfBias, MarketState, Priority, Session, TradeDir, VpLoc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DashboardSnapshot {
    pub symbol: String,
    pub mode: String,
    pub state: MarketState,
    pub session: Session,
    pub bias: HtfBias,
    pub loc: VpLoc,
    pub cvd_dir: TradeDir,
    pub footprint_ready: bool,
    pub sl: f64,
    pub rr: f64,
    pub score: i32,
    pub priority: Priority,
    pub cvd: f64,
    pub bar_delta: f64,
    pub vol_z: f64,
    pub poc: f64,
    pub vah: f64,
    pub val: f64,
    pub daily_dd_pct: f64,
    pub trades_today: i32,
    pub last_refresh: DateTime<Utc>,
}

impl DashboardSnapshot {
    pub fn render_text(&self) -> String {
        format!(
"GODMODE OFEA — {sym} — {mode}
[1] State ........ {state}
[2] KillZone .... {sess}
[3] HTF ......... {bias}
[4] VP Loc ...... {loc}
[5] CVD ......... {cvd_dir}
[6] Footprint ... {fp}
[7] SL .......... {sl:.5}
[8] R:R ......... {rr:.1}
CONF {score}/8 P{prio}
CVD {cvd:.0} Δ {bd:.0} volZ {vz:.2}
POC {poc:.5} VAH {vah:.5} VAL {val:.5}
DD {dd:.2}% Trades {n}",
            sym = self.symbol,
            mode = self.mode,
            state = match self.state {
                MarketState::Balanced => "BAL",
                MarketState::Imbalanced => "IMB",
                MarketState::Unknown => "UNK",
            },
            sess = crate::common::session_to_str(self.session),
            bias = crate::common::bias_to_str(self.bias),
            loc = crate::common::loc_to_str(self.loc),
            cvd_dir = match self.cvd_dir {
                TradeDir::Long => "BULL",
                TradeDir::Short => "BEAR",
                TradeDir::None => "FLAT",
            },
            fp = if self.footprint_ready { "OK" } else { "WAITING" },
            sl = self.sl,
            rr = self.rr,
            score = self.score,
            prio = self.priority as i32,
            cvd = self.cvd,
            bd = self.bar_delta,
            vz = self.vol_z,
            poc = self.poc,
            vah = self.vah,
            val = self.val,
            dd = self.daily_dd_pct,
            n = self.trades_today,
        )
    }
}

/// 250 ms throttle helper. The shell calls this each tick; if it returns
/// `false`, skip the re-render for this tick.
pub fn should_refresh(last: DateTime<Utc>, now: DateTime<Utc>) -> bool {
    (now - last).num_milliseconds() >= 250
}
