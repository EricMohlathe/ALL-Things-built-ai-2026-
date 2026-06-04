//! Footprint analyzer — absorption, stacked imbalances, unfinished auctions.
//!
//! Mirrors `OF_FootprintAnalyzer.mqh` and `FootprintAnalyzer.cs`. Brief §5 GATE 6.

use crate::common::Bar;
use crate::delta::DeltaEngine;

pub struct FootprintAnalyzer {
    pub vol_z_thr: f64,
    pub min_stacked_rows: usize,
}

impl FootprintAnalyzer {
    pub fn new(vol_z_thr: f64, min_stacked_rows: usize) -> Self {
        Self {
            vol_z_thr,
            min_stacked_rows: min_stacked_rows.max(2),
        }
    }

    /// Bullish absorption: down-delta + high vol-Z + close ≥ open.
    pub fn bullish_absorption(&self, de: &DeltaEngine, last_bar: &Bar) -> bool {
        let vol_z = de.volume_z();
        let bd = de.bar_delta();
        bd < 0.0 && vol_z >= self.vol_z_thr && last_bar.close >= last_bar.open
    }

    pub fn bearish_absorption(&self, de: &DeltaEngine, last_bar: &Bar) -> bool {
        let vol_z = de.volume_z();
        let bd = de.bar_delta();
        bd > 0.0 && vol_z >= self.vol_z_thr && last_bar.close <= last_bar.open
    }

    pub fn stacked_bull_imbalance(&self, de: &DeltaEngine) -> bool {
        for i in 0..self.min_stacked_rows {
            if de.delta(i) <= 0.0 {
                return false;
            }
        }
        true
    }

    pub fn stacked_bear_imbalance(&self, de: &DeltaEngine) -> bool {
        for i in 0..self.min_stacked_rows {
            if de.delta(i) >= 0.0 {
                return false;
            }
        }
        true
    }

    /// Unfinished auction — poor high or poor low relative to ATR(14).
    pub fn unfinished_auction(&self, bars: &[Bar], atr: f64) -> bool {
        if bars.len() < 2 || atr <= 0.0 {
            return false;
        }
        let cur = &bars[0];
        let prev = &bars[1];
        let poor_high = cur.high > prev.high && (cur.close - prev.close) < 0.25 * atr;
        let poor_low = cur.low < prev.low && (prev.close - cur.close) < 0.25 * atr;
        poor_high || poor_low
    }
}
