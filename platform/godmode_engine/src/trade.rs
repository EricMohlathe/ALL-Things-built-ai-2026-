//! Trade manager — emits `PositionAction` events that the application shell
//! turns into broker calls. Brief §5 + §16.
//!
//! Mirrors `OF_TradeManager.mqh` and `TradeManager.cs` but is *intent-only*:
//! the engine never talks to a broker directly. The shell observes the
//! emitted action stream and reflects them as orders / modifications /
//! closes on whichever broker is connected for that symbol.

use crate::common::{OrderIntent, TradeDir};

#[derive(Debug, Clone)]
pub enum PositionAction {
    Open(OrderIntent),
    PartialClose { fraction: f64, reason: String },
    MoveStopToBreakEven { offset_pips: f64, reason: String },
    TrailStop { new_sl: f64, reason: String },
    CloseAll { reason: String },
}

#[derive(Debug, Clone, Copy)]
pub struct OpenPositionView {
    pub direction: TradeDir,
    pub entry: f64,
    pub stop_loss: f64,
    pub take_profit: f64,
    pub volume: f64,
    pub partial_taken: bool,
    pub be_moved: bool,
}

pub struct TradeManager {
    pub label: String,
    pub partial_close: bool,
    pub partial_pct: f64,
    pub partial_at_r: f64,
    pub be_at_r: f64,
    pub use_trail: bool,
    pub trail_atr_mult: f64,
    pub exit_at_poc: bool,
}

impl TradeManager {
    pub fn new(
        label: impl Into<String>,
        partial_close: bool,
        partial_pct: f64,
        partial_at_r: f64,
        be_at_r: f64,
        use_trail: bool,
        trail_atr_mult: f64,
        exit_at_poc: bool,
    ) -> Self {
        Self {
            label: label.into(),
            partial_close,
            partial_pct,
            partial_at_r,
            be_at_r,
            use_trail,
            trail_atr_mult,
            exit_at_poc,
        }
    }

    /// Produce the action list for a single bar-close given current
    /// position view, current price, ATR, and POC. Mirrors the order of
    /// checks in `TradeManager.ManagePosition` (cTrader).
    pub fn manage(
        &self,
        pos: &OpenPositionView,
        current_price: f64,
        atr: f64,
        poc: f64,
        pip_size: f64,
    ) -> Vec<PositionAction> {
        let mut out = Vec::new();
        let risk = (pos.entry - pos.stop_loss).abs();
        if risk <= 0.0 {
            return out;
        }
        let r_mult = match pos.direction {
            TradeDir::Long => (current_price - pos.entry) / risk,
            TradeDir::Short => (pos.entry - current_price) / risk,
            TradeDir::None => 0.0,
        };
        if self.partial_close && r_mult >= self.partial_at_r && !pos.partial_taken {
            out.push(PositionAction::PartialClose {
                fraction: (self.partial_pct / 100.0).clamp(0.0, 0.95),
                reason: format!("partial @ {:.2}R", r_mult),
            });
        }
        if r_mult >= self.be_at_r && !pos.be_moved {
            out.push(PositionAction::MoveStopToBreakEven {
                offset_pips: 1.0,
                reason: format!("BE @ {:.2}R", r_mult),
            });
        }
        if self.use_trail && r_mult >= self.be_at_r && atr > 0.0 {
            let new_sl = match pos.direction {
                TradeDir::Long => current_price - atr * self.trail_atr_mult,
                TradeDir::Short => current_price + atr * self.trail_atr_mult,
                TradeDir::None => 0.0,
            };
            let tighter = match pos.direction {
                TradeDir::Long => new_sl > pos.stop_loss,
                TradeDir::Short => new_sl < pos.stop_loss,
                TradeDir::None => false,
            };
            if tighter {
                out.push(PositionAction::TrailStop {
                    new_sl,
                    reason: format!("trail {}xATR", self.trail_atr_mult),
                });
            }
        }
        // POC exit (Model 2 70% rule — brief §16).
        if self.exit_at_poc && poc > 0.0 {
            let reached = match pos.direction {
                TradeDir::Long => current_price >= poc,
                TradeDir::Short => current_price <= poc,
                TradeDir::None => false,
            };
            if reached {
                out.push(PositionAction::CloseAll {
                    reason: "POC exit (M2)".into(),
                });
            }
        }
        // Avoid unused warning while keeping the param in the signature so
        // the shell can pass through pip_size for symbol-aware logging.
        let _ = pip_size;
        out
    }
}
