//! CSV-driven replay harness.
//!
//! Reads a tick or bar CSV, advances the engine, and emits the event stream.
//! This is the foundation for the conformance test (TESTING.md Phase 6) —
//! same input file fed to MT5 strategy tester, cTrader cAlgo tester, and
//! this engine, and the gate / candidate streams compared.

use std::path::Path;

use chrono::{DateTime, NaiveDateTime, Utc};
use serde::Deserialize;

use crate::common::{AccountState, Bar, Tick};
use crate::engine::{BarCloseInput, Engine, EngineEvent};

#[derive(Debug, Deserialize)]
pub struct BarCsvRow {
    pub ts: String,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub volume: f64,
}

#[derive(Debug, Deserialize)]
pub struct TickCsvRow {
    pub ts: String,
    pub bid: f64,
    pub ask: f64,
    #[serde(default)]
    pub last: f64,
    #[serde(default)]
    pub volume: f64,
    #[serde(default)]
    pub is_buy_aggressor: Option<bool>,
}

fn parse_ts(s: &str) -> anyhow::Result<DateTime<Utc>> {
    // Accept multiple formats: ISO 8601 first, then MT5-style.
    if let Ok(dt) = DateTime::parse_from_rfc3339(s) {
        return Ok(dt.with_timezone(&Utc));
    }
    for fmt in &["%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M"] {
        if let Ok(naive) = NaiveDateTime::parse_from_str(s, fmt) {
            return Ok(DateTime::<Utc>::from_naive_utc_and_offset(naive, Utc));
        }
    }
    anyhow::bail!("unparseable timestamp: {s}")
}

pub fn read_bars(path: impl AsRef<Path>) -> anyhow::Result<Vec<Bar>> {
    let mut rdr = csv::Reader::from_path(path.as_ref())?;
    let mut out = Vec::new();
    for row in rdr.deserialize() {
        let r: BarCsvRow = row?;
        let ts = parse_ts(&r.ts)?;
        out.push(Bar {
            ts_open: ts,
            ts_close: ts,
            open: r.open,
            high: r.high,
            low: r.low,
            close: r.close,
            volume: r.volume,
            bar_delta: None,
        });
    }
    Ok(out)
}

pub fn read_ticks(path: impl AsRef<Path>) -> anyhow::Result<Vec<Tick>> {
    let mut rdr = csv::Reader::from_path(path.as_ref())?;
    let mut out = Vec::new();
    for row in rdr.deserialize() {
        let r: TickCsvRow = row?;
        let ts = parse_ts(&r.ts)?;
        out.push(Tick {
            ts,
            bid: r.bid,
            ask: r.ask,
            last: if r.last == 0.0 { 0.5 * (r.bid + r.ask) } else { r.last },
            volume: if r.volume == 0.0 { 1.0 } else { r.volume },
            is_buy_aggressor: r.is_buy_aggressor,
        });
    }
    Ok(out)
}

pub struct ReplayConfig {
    pub account: AccountState,
    pub atr14: f64,
    pub correlated_cvd_slope: f64,
}

/// Drive an engine through a sequence of bars. Each entry's `bars` slice is
/// expected to be newest-first (`bars[0]` = the bar just closed). The
/// helper builds those slices for you when given a flat oldest-first input.
///
/// Implementation note: we maintain a single newest-first `view` buffer and
/// push each incoming bar to the *front* (via insertion at index 0). This
/// keeps the engine-facing slice in the correct orientation without
/// rebuilding it on every bar — the previous implementation collected a new
/// reversed `Vec` per bar, costing O(N²).
pub fn replay_bars(
    engine: &mut Engine,
    bars_chronological: &[Bar],
    cfg: ReplayConfig,
) -> Vec<EngineEvent> {
    let mut all_events = Vec::new();
    // Newest-first buffer: `view[0]` is always the bar just closed.
    let mut view: Vec<Bar> = Vec::with_capacity(bars_chronological.len());
    for b in bars_chronological {
        view.insert(0, *b);
        let input = BarCloseInput {
            bars: &view,
            h4_closes: &[],
            d1_closes: &[],
            atr14: cfg.atr14,
            correlated_cvd_slope: cfg.correlated_cvd_slope,
            account: cfg.account,
        };
        let mut events = engine.on_bar_close(input);
        all_events.append(&mut events);
    }
    all_events
}
