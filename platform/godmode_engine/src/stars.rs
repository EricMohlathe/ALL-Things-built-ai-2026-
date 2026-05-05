//! Absorption-star confidence score (brief §11.4).
//!
//! 5-component formula:
//!   - +1 if vol Z ≥ 1.0
//!   - +1 if vol Z ≥ 2.0
//!   - +1 if vol Z ≥ 3.0
//!   - +1 if |delta Z| ≥ 2.0
//!   - +1 if directional wick fraction ≥ 0.40
//!
//! Mirrors `OF_AbsorptionStars.mqh` and `AbsorptionStars` static class in
//! cTrader's `FootprintAnalyzer.cs`. Numbers must agree exactly.

use crate::common::{Bar, TradeDir};
use crate::delta::DeltaEngine;

pub fn compute(bar: &Bar, de: &DeltaEngine, dir: TradeDir) -> i32 {
    let vol_z = de.volume_z();
    if vol_z < 1.0 {
        return 0;
    }
    let dz = de.delta_z();
    let mut stars = 1i32;
    if vol_z >= 2.0 {
        stars += 1;
    }
    if vol_z >= 3.0 {
        stars += 1;
    }
    if dz.abs() >= 2.0 {
        stars += 1;
    }
    let range = (bar.high - bar.low).max(1e-9);
    let wick_pct = match dir {
        TradeDir::Long => (bar.open.min(bar.close) - bar.low) / range,
        TradeDir::Short => (bar.high - bar.open.max(bar.close)) / range,
        TradeDir::None => 0.0,
    };
    if wick_pct >= 0.40 {
        stars += 1;
    }
    stars.min(5)
}
