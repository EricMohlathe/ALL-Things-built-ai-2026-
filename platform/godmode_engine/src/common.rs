//! Shared enums, structs, and helper math.
//!
//! Mirrors `mt5/Include/OF_Common.mqh` and `ctrader/Modules/OFCommon.cs`.
//! Every numeric and enum value here must agree with the other two builds.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OpMode {
    Manual = 0,
    Auto = 1,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Session {
    None = 0,
    Asian = 1,
    LdnOpen = 2,
    LdnMain = 3,
    NyOpen = 4,
    NyMain = 5,
    After = 6,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SubTier {
    None = 0,
    A = 1,
    B = 2,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ProfileShape {
    Unknown = 0,
    /// Balanced bell — Model 2 mean-reversion preferred.
    D = 1,
    /// Top-heavy P-shape — buy imbalance.
    P = 2,
    /// Bottom-heavy b-shape — sell imbalance.
    B = 3,
    /// Thin distribution — low-participation auction.
    Thin = 4,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MarketState {
    Unknown = 0,
    Balanced = 1,
    Imbalanced = 2,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum HtfBias {
    Neutral = 0,
    Bull = 1,
    Bear = 2,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ActiveModel {
    None = 0,
    M1Trend = 1,
    M2MeanRev = 2,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum VpLoc {
    None = 0,
    Val = 1,
    Vah = 2,
    Poc = 3,
    Lvn = 4,
    Hvn = 5,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TradeDir {
    None = 0,
    Long = 1,
    Short = -1,
}

/// Brief §6 — the 25 setup IDs. Must match MT5 `ENUM_SETUP_ID` and
/// cTrader `SetupId` value-for-value.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SetupId {
    None = 0,
    AbsBot = 1,
    AbsTop = 2,
    CvdBear = 3,
    CvdBull = 4,
    ValBnc = 5,
    VahFade = 6,
    PocRet = 7,
    LvnLong = 8,
    LvnShort = 9,
    HvnRej = 10,
    StackBull = 11,
    StackBear = 12,
    PullStack = 13,
    Spring = 14,
    Upthrust = 15,
    Sos = 16,
    Lpsy = 17,
    LiqSweep = 18,
    ObReturn = 19,
    SmtDiv = 20,
    Breaker = 21,
    Amd = 22,
    UnfAuc = 23,
    PoorHL = 24,
    Iceberg = 25,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Priority {
    None = 0,
    P1 = 1,
    P2 = 2,
    P3 = 3,
    P4 = 4,
    P5 = 5,
}

/// Every gate function returns one of these. Brief §15 rule 3: the gate's
/// reason and value are journaled and rendered to the operator dashboard so
/// the *why* of every decision is auditable.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GateResult {
    pub passed: bool,
    pub reason: String,
    pub value: f64,
}

impl GateResult {
    pub fn pass(reason: impl Into<String>) -> Self {
        Self { passed: true, reason: reason.into(), value: 0.0 }
    }

    pub fn pass_with(reason: impl Into<String>, value: f64) -> Self {
        Self { passed: true, reason: reason.into(), value }
    }

    pub fn fail(reason: impl Into<String>) -> Self {
        Self { passed: false, reason: reason.into(), value: 0.0 }
    }

    pub fn fail_with(reason: impl Into<String>, value: f64) -> Self {
        Self { passed: false, reason: reason.into(), value }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SetupCandidate {
    pub setup_id: SetupId,
    pub direction: TradeDir,
    pub entry: f64,
    pub sl: f64,
    pub tp: f64,
    pub score: i32,
    pub abs_stars: i32,
    pub loc: VpLoc,
    pub priority: Priority,
    pub reason: String,
}

impl SetupCandidate {
    pub fn empty() -> Self {
        Self {
            setup_id: SetupId::None,
            direction: TradeDir::None,
            entry: 0.0,
            sl: 0.0,
            tp: 0.0,
            score: 0,
            abs_stars: 0,
            loc: VpLoc::None,
            priority: Priority::None,
            reason: String::new(),
        }
    }
}

/// One tick from any broker feed. `is_buy_aggressor` is the canonical
/// classification — if the broker provides it directly use that; otherwise
/// derive from uptick/downtick of mid against the previous tick.
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct Tick {
    pub ts: DateTime<Utc>,
    pub bid: f64,
    pub ask: f64,
    pub last: f64,
    pub volume: f64,
    pub is_buy_aggressor: Option<bool>,
}

impl Tick {
    pub fn mid(&self) -> f64 {
        0.5 * (self.bid + self.ask)
    }

    pub fn spread(&self) -> f64 {
        (self.ask - self.bid).max(0.0)
    }
}

/// One closed bar. Engine consumes a stream of these via `on_bar_close`.
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct Bar {
    pub ts_open: DateTime<Utc>,
    pub ts_close: DateTime<Utc>,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    /// Total tick volume (broker tick count or actual size, depending on feed).
    pub volume: f64,
    /// Buy-aggressor volume minus sell-aggressor volume, computed by the
    /// `delta::DeltaEngine` between bar opens. Engine fills this in if the
    /// caller leaves it `None`.
    pub bar_delta: Option<f64>,
}

/// Snapshot of the broker account that the engine reads on every bar close.
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct AccountState {
    pub equity: f64,
    pub balance: f64,
    pub spread: f64,
    pub pip_size: f64,
    pub tick_size: f64,
    pub pip_value: f64,
    pub volume_step: f64,
    pub volume_min: f64,
}

/// Output of the engine when GATE 8 fires in MODE_AUTO. The application
/// shell turns this into a broker order via the connectivity layer.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderIntent {
    pub direction: TradeDir,
    pub entry: f64,
    pub sl: f64,
    pub tp: f64,
    pub volume: f64,
    pub label: String,
    pub comment: String,
}

// ---------- helpers ----------

pub fn session_to_str(s: Session) -> &'static str {
    match s {
        Session::Asian => "ASIAN",
        Session::LdnOpen => "LDN_OPEN",
        Session::LdnMain => "LDN_MAIN",
        Session::NyOpen => "NY_OPEN",
        Session::NyMain => "NY_MAIN",
        Session::After => "AFTER",
        Session::None => "NONE",
    }
}

pub fn dir_to_str(d: TradeDir) -> &'static str {
    match d {
        TradeDir::Long => "LONG",
        TradeDir::Short => "SHORT",
        TradeDir::None => "NONE",
    }
}

pub fn loc_to_str(l: VpLoc) -> &'static str {
    match l {
        VpLoc::Val => "VAL",
        VpLoc::Vah => "VAH",
        VpLoc::Poc => "POC",
        VpLoc::Lvn => "LVN",
        VpLoc::Hvn => "HVN",
        VpLoc::None => "OUT",
    }
}

pub fn shape_to_str(s: ProfileShape) -> &'static str {
    match s {
        ProfileShape::D => "D",
        ProfileShape::P => "P",
        ProfileShape::B => "b",
        ProfileShape::Thin => "THIN",
        ProfileShape::Unknown => "UNK",
    }
}

pub fn bias_to_str(b: HtfBias) -> &'static str {
    match b {
        HtfBias::Bull => "BULL",
        HtfBias::Bear => "BEAR",
        HtfBias::Neutral => "NEUTRAL",
    }
}

/// Round volume *down* to the broker's volume step. Matches
/// `Symbol.NormalizeVolumeInUnits(raw, RoundingMode.Down)` in cTrader and
/// `OFHelpers.NormaliseLots` in MT5.
pub fn normalise_volume(raw: f64, step: f64, min: f64) -> f64 {
    if step <= 0.0 || raw <= 0.0 {
        return 0.0;
    }
    let steps = (raw / step).floor();
    let v = steps * step;
    if v < min {
        0.0
    } else {
        v
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalise_volume_rounds_down() {
        assert_eq!(normalise_volume(8.34, 0.01, 0.01), 8.34);
        assert_eq!(normalise_volume(8.349, 0.01, 0.01), 8.34);
        assert_eq!(normalise_volume(0.005, 0.01, 0.01), 0.0);
    }

    #[test]
    fn gate_result_factories() {
        let p = GateResult::pass("ok");
        assert!(p.passed);
        let f = GateResult::fail_with("bad", -2.5);
        assert!(!f.passed);
        assert_eq!(f.value, -2.5);
    }
}
