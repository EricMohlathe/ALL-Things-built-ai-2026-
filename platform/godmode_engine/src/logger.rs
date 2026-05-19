//! CSV journal writer — schema per brief §13.
//!
//! Mirrors `OF_Logger.mqh` and `TradeLogger.cs`. The schema is byte-identical
//! across all three builds so any one journal can be analysed by the same
//! ML pipeline.

// The `Default` impls below are kept as explicit `impl Default` blocks rather
// than `#[derive(Default)]` on the enums in `common.rs`, because those enums
// are the public conformance surface mirrored across the MT5 / cTrader builds —
// we don't want a `#[default]` attribute encoded into their derived metadata.
// Suppress clippy's derivable_impls lint locally.
#![allow(clippy::derivable_impls)]

use std::fs::{File, OpenOptions};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};

use chrono::{DateTime, Utc};

use crate::common::{
    bias_to_str, dir_to_str, session_to_str, shape_to_str, HtfBias, MarketState, ProfileShape,
    Session, SetupCandidate,
};

pub const HEADER: &str = "timestamp_utc,symbol,event_type,setup_id,score,priority,\
direction,entry_price,sl,tp,lots,risk_pct,\
session,market_state,htf_bias,profile_shape,\
poc,vah,val,\
cvd_at_entry,bar_delta,vol_z,delta_z,abs_stars,\
notif_cascade_completed,mode,\
result_pnl_pips,result_pnl_pct,result_R,hold_minutes";

pub struct TradeLogger {
    path: PathBuf,
}

#[derive(Debug, Clone, Default)]
pub struct LogRow<'a> {
    pub event_type: &'a str,
    pub symbol: &'a str,
    pub now: DateTime<Utc>,
    pub session: Session,
    pub state: MarketState,
    pub bias: HtfBias,
    pub shape: ProfileShape,
    pub poc: f64,
    pub vah: f64,
    pub val: f64,
    pub cvd: f64,
    pub bar_delta: f64,
    pub vol_z: f64,
    pub delta_z: f64,
    pub mode: &'a str,
    pub risk_pct: f64,
    pub lots: f64,
    pub result_pips: f64,
    pub result_pct: f64,
    pub result_r: f64,
    pub hold_min: f64,
}

impl Default for Session {
    fn default() -> Self {
        Self::None
    }
}
impl Default for MarketState {
    fn default() -> Self {
        Self::Unknown
    }
}
impl Default for HtfBias {
    fn default() -> Self {
        Self::Neutral
    }
}
impl Default for ProfileShape {
    fn default() -> Self {
        Self::Unknown
    }
}

impl TradeLogger {
    pub fn new(path: impl AsRef<Path>) -> std::io::Result<Self> {
        let path = path.as_ref().to_owned();
        if let Some(dir) = path.parent() {
            std::fs::create_dir_all(dir)?;
        }
        let needs_header = !path.exists();
        if needs_header {
            let mut f = File::create(&path)?;
            writeln!(f, "{HEADER}")?;
        }
        Ok(Self { path })
    }

    pub fn append(&self, c: &SetupCandidate, row: &LogRow<'_>) -> std::io::Result<()> {
        let mut f = BufWriter::new(
            OpenOptions::new()
                .append(true)
                .create(true)
                .open(&self.path)?,
        );
        writeln!(
            f,
            "{ts},{sym},{ev},{sid},{score},{prio},{dir},{ep:.5},{sl:.5},{tp:.5},{lots:.2},{rpct:.2},\
             {sess},{state},{bias},{shape},{poc:.5},{vah:.5},{val:.5},\
             {cvd:.0},{bd:.0},{vz:.2},{dz:.2},{stars},1,{mode},\
             {rp:.2},{rpc:.4},{rr:.2},{hm:.1}",
            ts = row.now.format("%Y.%m.%d %H:%M:%S"),
            sym = row.symbol,
            ev = row.event_type,
            sid = c.setup_id as i32,
            score = c.score,
            prio = c.priority as i32,
            dir = dir_to_str(c.direction),
            ep = c.entry,
            sl = c.sl,
            tp = c.tp,
            lots = row.lots,
            rpct = row.risk_pct,
            sess = session_to_str(row.session),
            state = row.state as i32,
            bias = bias_to_str(row.bias),
            shape = shape_to_str(row.shape),
            poc = row.poc,
            vah = row.vah,
            val = row.val,
            cvd = row.cvd,
            bd = row.bar_delta,
            vz = row.vol_z,
            dz = row.delta_z,
            stars = c.abs_stars,
            mode = row.mode,
            rp = row.result_pips,
            rpc = row.result_pct,
            rr = row.result_r,
            hm = row.hold_min,
        )?;
        Ok(())
    }
}
