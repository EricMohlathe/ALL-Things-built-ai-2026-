//! Risk manager — sizing + DD halt + spread guard + consecutive-loss halt
//! + news blackout. Brief §12 rules 1–8.
//!
//! Mirrors `OF_RiskManager.mqh` and `RiskManager.cs`.
//!
//! The 1%/2% hard cap is enforced in `new` — passing `risk_pct > 2.0`
//! silently clamps. This is brief §12 rule 2 and is non-negotiable.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::common::{AccountState, GateResult};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NewsEvent {
    pub start: DateTime<Utc>,
    pub end: DateTime<Utc>,
    pub impact: String,
    pub desc: String,
}

pub struct RiskManager {
    pub risk_pct: f64,
    pub risk_half_pct: f64,
    pub max_dd_pct: f64,
    pub max_consec_losses: i32,
    pub max_spread_mult: f64,

    pub day_start_equity: f64,
    pub day_started_at: DateTime<Utc>,
    pub consec_losses: i32,
    pub day_halted: bool,

    spread_hist: [f64; 100],
    spread_idx: usize,
    spread_filled: bool,
    spread_median: f64,

    pub news: Vec<NewsEvent>,
    pub news_block_high: bool,
    pub news_block_medium: bool,
}

impl RiskManager {
    pub fn new(
        risk_pct: f64,
        risk_half_pct: f64,
        max_dd_pct: f64,
        max_consec_losses: i32,
        max_spread_mult: f64,
        day_start_equity: f64,
        now: DateTime<Utc>,
    ) -> Self {
        Self {
            risk_pct: risk_pct.clamp(0.0, 2.0), // brief §12 rule 2
            risk_half_pct: risk_half_pct.clamp(0.0, 2.0),
            max_dd_pct,
            max_consec_losses,
            max_spread_mult,
            day_start_equity,
            day_started_at: now,
            consec_losses: 0,
            day_halted: false,
            spread_hist: [0.0; 100],
            spread_idx: 0,
            spread_filled: false,
            spread_median: 0.0,
            news: Vec::new(),
            news_block_high: true,
            news_block_medium: false,
        }
    }

    pub fn on_day_rollover(&mut self, equity: f64, now: DateTime<Utc>) {
        self.day_start_equity = equity;
        self.day_started_at = now;
        self.consec_losses = 0;
        self.day_halted = false;
    }

    pub fn sample_spread(&mut self, spread: f64) {
        self.spread_hist[self.spread_idx] = spread;
        self.spread_idx = (self.spread_idx + 1) % 100;
        if self.spread_idx == 0 {
            self.spread_filled = true;
        }
        let n = if self.spread_filled { 100 } else { self.spread_idx.max(1) };
        let mut sorted = self.spread_hist[..n].to_vec();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        self.spread_median = sorted[n / 2];
    }

    pub fn daily_dd_pct(&self, equity: f64) -> f64 {
        if self.day_start_equity <= 0.0 {
            0.0
        } else {
            (equity - self.day_start_equity) / self.day_start_equity * 100.0
        }
    }

    pub fn check_daily_drawdown(&self, equity: f64) -> GateResult {
        let pct = self.daily_dd_pct(equity);
        if pct <= -self.max_dd_pct {
            GateResult::fail_with(format!("Daily DD {pct:.2}%"), pct)
        } else {
            GateResult::pass_with(format!("Daily DD {pct:.2}%"), pct)
        }
    }

    pub fn check_spread(&self, current_spread: f64) -> GateResult {
        if self.spread_median <= 0.0 {
            return GateResult::pass_with("no median yet", current_spread);
        }
        if current_spread > self.spread_median * self.max_spread_mult {
            GateResult::fail_with(format!("Spread blowout {current_spread:.5}"), current_spread)
        } else {
            GateResult::pass_with(format!("Spread ok {current_spread:.5}"), current_spread)
        }
    }

    pub fn check_consec_losses(&self) -> GateResult {
        if self.consec_losses >= self.max_consec_losses {
            GateResult::fail_with(
                format!("Consec losses {}", self.consec_losses),
                self.consec_losses as f64,
            )
        } else {
            GateResult::pass_with(
                format!("Consec losses {}", self.consec_losses),
                self.consec_losses as f64,
            )
        }
    }

    pub fn check_news_blackout(&self, now: DateTime<Utc>) -> GateResult {
        for ev in &self.news {
            let blocks = match ev.impact.to_uppercase().as_str() {
                "HIGH" => self.news_block_high,
                "MEDIUM" => self.news_block_medium,
                _ => false,
            };
            if !blocks {
                continue;
            }
            if now >= ev.start && now <= ev.end {
                return GateResult::fail(format!("News blackout: {}", ev.desc));
            }
        }
        GateResult::pass("no news")
    }

    pub fn notify_trade_closed(&mut self, pnl: f64) {
        if pnl < 0.0 {
            self.consec_losses += 1;
        } else {
            self.consec_losses = 0;
        }
    }

    pub fn halt_day(&mut self) {
        self.day_halted = true;
    }

    /// Brief §11.8 canonical sizing.
    pub fn compute_volume(
        &self,
        acct: &AccountState,
        sl_price_distance: f64,
        half_size: bool,
    ) -> f64 {
        let pct = if half_size { self.risk_half_pct } else { self.risk_pct };
        let risk_amount = acct.equity * pct / 100.0;
        if sl_price_distance <= 0.0 || acct.pip_size <= 0.0 || acct.pip_value <= 0.0 {
            return 0.0;
        }
        let pip_distance = sl_price_distance / acct.pip_size;
        if pip_distance <= 0.0 {
            return 0.0;
        }
        let raw = risk_amount / (pip_distance * acct.pip_value);
        crate::common::normalise_volume(raw, acct.volume_step, acct.volume_min)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::TimeZone;

    fn now() -> DateTime<Utc> {
        Utc.with_ymd_and_hms(2026, 5, 5, 12, 0, 0).unwrap()
    }

    #[test]
    fn risk_pct_hard_clamped() {
        let r = RiskManager::new(5.0, 0.5, 5.0, 3, 2.0, 10_000.0, now());
        assert_eq!(r.risk_pct, 2.0);
    }

    #[test]
    fn dd_halt_fires_at_threshold() {
        let r = RiskManager::new(1.0, 0.5, 5.0, 3, 2.0, 10_000.0, now());
        let g = r.check_daily_drawdown(9_500.0);
        assert!(!g.passed);
    }
}
