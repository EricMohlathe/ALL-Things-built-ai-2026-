//! Tick-delta accumulator + CVD series + divergence detection.
//!
//! Mirrors `OF_DeltaEngine.mqh` and `DeltaEngine.cs`.
//!
//! Brief §11.1 — partition each tick by aggressor side.
//! Brief §11.5 — divergence = price extreme + CVD reversion.

use crate::common::{Bar, Tick, TradeDir};

pub struct DeltaEngine {
    lookback: usize,
    tick_buy: f64,
    tick_sell: f64,
    bar_delta: Vec<f64>,
    volume: Vec<f64>,
    cvd: Vec<f64>,
    high: Vec<f64>,
    low: Vec<f64>,
    last_mid: Option<f64>,
    tick_size: f64,
}

impl DeltaEngine {
    pub fn new(lookback: usize, tick_size: f64) -> Self {
        let lb = lookback.max(30);
        Self {
            lookback: lb,
            tick_buy: 0.0,
            tick_sell: 0.0,
            bar_delta: vec![0.0; lb],
            volume: vec![0.0; lb],
            cvd: vec![0.0; lb],
            high: vec![0.0; lb],
            low: vec![0.0; lb],
            last_mid: None,
            tick_size,
        }
    }

    /// Brief §11.1 — partition by aggressor side. If the broker has stamped
    /// `is_buy_aggressor`, use that. Otherwise fall back to uptick rule:
    /// mid moved up => buy aggressor; mid moved down => sell aggressor.
    pub fn on_tick(&mut self, t: &Tick) {
        let v = if t.volume > 0.0 { t.volume } else { 1.0 };
        let buy = match t.is_buy_aggressor {
            Some(b) => b,
            None => {
                let mid = t.mid();
                let last = self.last_mid.unwrap_or(mid);
                self.last_mid = Some(mid);
                if mid > last {
                    true
                } else if mid < last {
                    false
                } else {
                    return;
                }
            }
        };
        if buy {
            self.tick_buy += v;
        } else {
            self.tick_sell += v;
        }
    }

    /// Snapshot delta into the series, shift, reset accumulators.
    /// Caller passes the just-closed bar so we can persist H/L for divergence.
    pub fn on_bar_close(&mut self, b: &Bar) {
        let bd = self.tick_buy - self.tick_sell;
        let mut tv = self.tick_buy + self.tick_sell;
        if tv <= 0.0 {
            tv = b.volume;
        }
        for i in (1..self.lookback).rev() {
            self.bar_delta[i] = self.bar_delta[i - 1];
            self.volume[i] = self.volume[i - 1];
            self.cvd[i] = self.cvd[i - 1];
            self.high[i] = self.high[i - 1];
            self.low[i] = self.low[i - 1];
        }
        self.bar_delta[0] = bd;
        self.volume[0] = tv;
        self.cvd[0] = self.cvd.get(1).copied().unwrap_or(0.0) + bd;
        self.high[0] = b.high;
        self.low[0] = b.low;
        self.tick_buy = 0.0;
        self.tick_sell = 0.0;
    }

    pub fn cvd(&self) -> f64 {
        self.cvd[0]
    }

    pub fn bar_delta(&self) -> f64 {
        self.bar_delta[0]
    }

    pub fn delta(&self, i: usize) -> f64 {
        if i < self.lookback {
            self.bar_delta[i]
        } else {
            0.0
        }
    }

    pub fn volume_at(&self, i: usize) -> f64 {
        if i < self.lookback {
            self.volume[i]
        } else {
            0.0
        }
    }

    pub fn cvd_at(&self, i: usize) -> f64 {
        if i < self.lookback {
            self.cvd[i]
        } else {
            0.0
        }
    }

    pub fn volume_z(&self) -> f64 {
        z_score(&self.volume)
    }

    pub fn delta_z(&self) -> f64 {
        z_score(&self.bar_delta)
    }

    pub fn cvd_slope_5(&self) -> f64 {
        let n = 5.min(self.lookback - 1);
        self.cvd[0] - self.cvd[n]
    }

    /// Bullish divergence: current bar makes a new low (within tick_size) but
    /// CVD is *higher* than the last comparable swing.
    pub fn bullish_divergence(&self) -> bool {
        let n = 20.min(self.lookback - 1);
        if n < 2 {
            return false;
        }
        let mut p_low = self.low[1];
        let mut cvd_min = self.cvd[1];
        for i in 2..=n {
            if self.low[i] < p_low {
                p_low = self.low[i];
            }
            if self.cvd[i] < cvd_min {
                cvd_min = self.cvd[i];
            }
        }
        let cur_low = self.low[1];
        cur_low <= p_low + self.tick_size && self.cvd[1] > cvd_min + 1e-9
    }

    pub fn bearish_divergence(&self) -> bool {
        let n = 20.min(self.lookback - 1);
        if n < 2 {
            return false;
        }
        let mut p_high = self.high[1];
        let mut cvd_max = self.cvd[1];
        for i in 2..=n {
            if self.high[i] > p_high {
                p_high = self.high[i];
            }
            if self.cvd[i] > cvd_max {
                cvd_max = self.cvd[i];
            }
        }
        let cur_high = self.high[1];
        cur_high >= p_high - self.tick_size && self.cvd[1] < cvd_max - 1e-9
    }

    /// Returns `true` if the *last bar's* CVD slope agrees with the candidate
    /// direction. Used by GATE 5.
    pub fn cvd_agrees(&self, dir: TradeDir) -> bool {
        let s = self.cvd_slope_5();
        match dir {
            TradeDir::Long => s > 0.0,
            TradeDir::Short => s < 0.0,
            TradeDir::None => false,
        }
    }
}

fn z_score(series: &[f64]) -> f64 {
    if series.is_empty() {
        return 0.0;
    }
    let n = series.len() as f64;
    let mean = series.iter().sum::<f64>() / n;
    let var = series.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / n;
    let sd = var.sqrt();
    if sd < 1e-9 {
        0.0
    } else {
        (series[0] - mean) / sd
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::{TimeZone, Utc};

    fn t(ts: i64, bid: f64, ask: f64) -> Tick {
        Tick {
            ts: Utc.timestamp_opt(ts, 0).unwrap(),
            bid,
            ask,
            last: 0.5 * (bid + ask),
            volume: 1.0,
            is_buy_aggressor: None,
        }
    }

    fn bar(o: f64, h: f64, l: f64, c: f64, v: f64) -> Bar {
        Bar {
            ts_open: Utc.timestamp_opt(0, 0).unwrap(),
            ts_close: Utc.timestamp_opt(60, 0).unwrap(),
            open: o,
            high: h,
            low: l,
            close: c,
            volume: v,
            bar_delta: None,
        }
    }

    #[test]
    fn delta_aggressor_uptick_classifies_buy() {
        let mut de = DeltaEngine::new(50, 0.00001);
        de.on_tick(&t(1, 1.0, 1.0001));
        // First tick has no prior mid → no classification.
        assert_eq!(de.tick_buy, 0.0);
        de.on_tick(&t(2, 1.00005, 1.00015)); // mid moved up
        assert_eq!(de.tick_buy, 1.0);
        de.on_tick(&t(3, 1.0, 1.00005)); // mid moved down
        assert_eq!(de.tick_sell, 1.0);
    }

    #[test]
    fn cvd_accumulates() {
        let mut de = DeltaEngine::new(50, 0.00001);
        de.on_tick(&t(1, 1.0, 1.0001));
        de.on_tick(&t(2, 1.00005, 1.00015));
        de.on_bar_close(&bar(1.0, 1.001, 0.999, 1.0005, 10.0));
        assert_eq!(de.bar_delta(), 1.0);
        assert_eq!(de.cvd(), 1.0);
    }
}
