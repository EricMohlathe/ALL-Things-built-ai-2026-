//! Volume profile: 50-bin POC/VAH/VAL via expansion-from-POC plus
//! D/P/b/THIN shape classifier via skewness + peakedness.
//!
//! Mirrors `OF_VolumeProfile.mqh` and `VolumeProfile.cs`. Brief §11.2 + §11.3.

use crate::common::{Bar, MarketState, ProfileShape, VpLoc};

pub struct VolumeProfile {
    bins: usize,
    length: usize,
    /// Value-area fraction (default 0.70).
    va: f64,
    /// LVN ratio threshold (default 0.30 of POC bin volume).
    lvn_ratio: f64,
    /// HVN ratio threshold (default 0.80 of POC bin volume).
    hvn_ratio: f64,

    bin_vol: Vec<f64>,
    lvn_flag: Vec<bool>,
    hvn_flag: Vec<bool>,

    lo: f64,
    hi: f64,
    bin_size: f64,

    pub poc: f64,
    pub vah: f64,
    pub val: f64,
    pub shape: ProfileShape,
}

impl VolumeProfile {
    pub fn new(bins: usize, length: usize, va: f64, lvn_ratio: f64, hvn_ratio: f64) -> Self {
        let b = bins.max(10);
        Self {
            bins: b,
            length: length.max(20),
            va,
            lvn_ratio,
            hvn_ratio,
            bin_vol: vec![0.0; b],
            lvn_flag: vec![false; b],
            hvn_flag: vec![false; b],
            lo: 0.0,
            hi: 0.0,
            bin_size: 0.0,
            poc: 0.0,
            vah: 0.0,
            val: 0.0,
            shape: ProfileShape::Unknown,
        }
    }

    pub fn state(&self) -> MarketState {
        match self.shape {
            ProfileShape::D => MarketState::Balanced,
            ProfileShape::Unknown => MarketState::Unknown,
            _ => MarketState::Imbalanced,
        }
    }

    /// `bars[0]` = most-recently-closed bar (newest-first slice).
    pub fn recompute(&mut self, bars: &[Bar]) -> bool {
        for b in self.bin_vol.iter_mut() {
            *b = 0.0;
        }
        for b in self.lvn_flag.iter_mut() {
            *b = false;
        }
        for b in self.hvn_flag.iter_mut() {
            *b = false;
        }
        if bars.len() < self.length {
            return false;
        }
        let span = &bars[..self.length];
        let mut hi = span[0].high;
        let mut lo = span[0].low;
        for b in span.iter() {
            hi = hi.max(b.high);
            lo = lo.min(b.low);
        }
        self.lo = lo;
        self.hi = hi;
        self.bin_size = (hi - lo) / self.bins as f64;
        if self.bin_size <= 0.0 {
            return false;
        }
        for b in span.iter() {
            let mut idx = ((b.close - lo) / self.bin_size).floor() as i64;
            if idx < 0 {
                idx = 0;
            }
            if idx >= self.bins as i64 {
                idx = self.bins as i64 - 1;
            }
            self.bin_vol[idx as usize] += b.volume;
        }

        // POC = bin with max volume.
        let mut poc_bin = 0usize;
        for i in 1..self.bins {
            if self.bin_vol[i] > self.bin_vol[poc_bin] {
                poc_bin = i;
            }
        }
        self.poc = lo + (poc_bin as f64 + 0.5) * self.bin_size;

        // Expansion-from-POC value area.
        let total: f64 = self.bin_vol.iter().sum();
        let target = total * self.va;
        let mut acc = self.bin_vol[poc_bin];
        let mut hi_bin = poc_bin;
        let mut lo_bin = poc_bin;
        while acc < target && (hi_bin + 1 < self.bins || lo_bin > 0) {
            let up = if hi_bin + 1 < self.bins {
                self.bin_vol[hi_bin + 1]
            } else {
                -1.0
            };
            let dn = if lo_bin > 0 {
                self.bin_vol[lo_bin - 1]
            } else {
                -1.0
            };
            if up >= dn && up >= 0.0 {
                hi_bin += 1;
                acc += up;
            } else if dn >= 0.0 {
                lo_bin -= 1;
                acc += dn;
            } else {
                break;
            }
        }
        self.vah = lo + (hi_bin as f64 + 1.0) * self.bin_size;
        self.val = lo + lo_bin as f64 * self.bin_size;

        // LVN/HVN flags based on POC-relative volume.
        let poc_vol = self.bin_vol[poc_bin];
        for i in 0..self.bins {
            self.lvn_flag[i] = self.bin_vol[i] < poc_vol * self.lvn_ratio;
            self.hvn_flag[i] = self.bin_vol[i] > poc_vol * self.hvn_ratio;
        }

        self.classify_shape(poc_bin, poc_vol);
        true
    }

    /// Brief §11.3 — skewness sign + peakedness magnitude.
    fn classify_shape(&mut self, _poc_bin: usize, poc_vol: f64) {
        let mut low_bin = -1i64;
        let mut high_bin = -1i64;
        for (i, v) in self.bin_vol.iter().enumerate() {
            if *v > 0.0 {
                if low_bin < 0 {
                    low_bin = i as i64;
                }
                high_bin = i as i64;
            }
        }
        if low_bin < 0 {
            self.shape = ProfileShape::Unknown;
            return;
        }
        let mid_bin = ((low_bin + high_bin) / 2) as usize;
        let mut upper = 0.0;
        let mut lower = 0.0;
        for i in mid_bin..=(high_bin as usize) {
            upper += self.bin_vol[i];
        }
        for i in (low_bin as usize)..mid_bin {
            lower += self.bin_vol[i];
        }
        let tot = upper + lower;
        let skew = if tot > 0.0 { (upper - lower) / tot } else { 0.0 };

        let mut sum = 0.0;
        let mut nz = 0;
        for v in self.bin_vol.iter() {
            if *v > 0.0 {
                sum += *v;
                nz += 1;
            }
        }
        let peak = if nz > 0 && sum > 0.0 {
            poc_vol / (sum / nz as f64)
        } else {
            1.0
        };

        // Match cTrader/MT5 thresholds verbatim.
        self.shape = if skew.abs() < 0.10 && peak > 2.0 {
            ProfileShape::D
        } else if skew > 0.20 {
            ProfileShape::P
        } else if skew < -0.20 {
            ProfileShape::B
        } else if peak < 1.3 {
            ProfileShape::Thin
        } else {
            ProfileShape::D
        };
    }

    pub fn location_at(&self, price: f64, tol: f64) -> VpLoc {
        if (price - self.poc).abs() < tol {
            return VpLoc::Poc;
        }
        if (price - self.vah).abs() < tol {
            return VpLoc::Vah;
        }
        if (price - self.val).abs() < tol {
            return VpLoc::Val;
        }
        if self.bin_size > 0.0 {
            let idx = ((price - self.lo) / self.bin_size).floor() as i64;
            if idx >= 0 && (idx as usize) < self.bins {
                let i = idx as usize;
                if self.lvn_flag[i] {
                    return VpLoc::Lvn;
                }
                if self.hvn_flag[i] {
                    return VpLoc::Hvn;
                }
            }
        }
        VpLoc::None
    }
}
