//! # godmode_engine
//!
//! Platform-agnostic core for the GODMODE_OFEA order-flow trading system.
//!
//! This crate is the third 1:1 mirror of the trading logic that lives in:
//!   - `mt5/GODMODE_OFEA/Include/*.mqh` (MQL5 build)
//!   - `ctrader/GODMODE_OFEA/Modules/*.cs` (cTrader/cAlgo build)
//!
//! Acceptance test (TESTING.md Phase 6 generalised): replay an identical tick
//! file through all three engines and assert ≥95% signal agreement.
//!
//! ## Layering
//!
//! No I/O, no networking, no UI. The engine consumes:
//!   - `Tick` events  → [`engine::Engine::on_tick`]
//!   - bar-close events → [`engine::Engine::on_bar_close`]
//!
//! …and emits:
//!   - `GateOutcome` per gate (0..=8)
//!   - `Notification` events (N-A..N-L)
//!   - `OrderIntent` (in MODE_AUTO) or chart-only intents (MODE_MANUAL)
//!
//! Persistence, broker connectivity, and visualisation are concerns of the
//! application shell that wraps this crate (Tauri/Electron + WebGL).
//!
//! ## Hard constraints
//!
//! Inherited verbatim from brief §19. These cannot be relaxed by configuration:
//!   - Gate ordering F2→F5→loc→F3→F4→footprint→trigger→score
//!   - 1% per-trade risk cap, hard-clamped to 2% even if input is higher
//!   - 5% daily DD halt
//!   - 3-consecutive-loss day halt
//!   - 70% POC exit for Model 2
//!   - NY-Open 20-minute blackout
//!   - Session close at 21:00 SAST

pub mod common;
pub mod delta;
pub mod profile;
pub mod footprint;
pub mod stars;
pub mod session;
pub mod htf;
pub mod risk;
pub mod trade;
pub mod notify;
pub mod dashboard;
pub mod logger;
pub mod setups;
pub mod engine;
pub mod replay;

#[cfg(feature = "ffi")]
pub mod ffi;

pub use common::{
    GateResult, SetupCandidate, Tick, Bar, AccountState, OrderIntent,
    OpMode, Session, SubTier, ProfileShape, MarketState, HtfBias,
    ActiveModel, VpLoc, TradeDir, SetupId, Priority,
};
pub use engine::{Engine, EngineConfig, EngineEvent};
