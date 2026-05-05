//! HTF alignment: H4 EMA(20) + D1 EMA(50) dual-bias check.
//!
//! Mirrors `OF_HTFAlignment.mqh` and `HTFAlignment.cs`. Brief §11.7.
//!
//! Unlike MT5 (`iMA` indicator handle) and cTrader (`ExponentialMovingAverage`
//! indicator), this engine has no live broker connection — the application
//! shell is responsible for feeding H4 and D1 close series in. The EMA is
//! computed in-process so the result is deterministic across replays.

use crate::common::{HtfBias, TradeDir};

/// Standard EMA: `ema[i] = alpha * close[i] + (1-alpha) * ema[i-1]`,
/// `alpha = 2/(period+1)`. Returns `0.0` if the input is empty.
pub fn ema(closes: &[f64], period: usize) -> f64 {
    if closes.is_empty() || period == 0 {
        return 0.0;
    }
    let alpha = 2.0 / (period as f64 + 1.0);
    let mut e = closes[0];
    for c in closes.iter().skip(1) {
        e = alpha * c + (1.0 - alpha) * e;
    }
    e
}

pub struct HtfSnapshot {
    pub h4_close: f64,
    pub h4_ema20: f64,
    pub d1_close: f64,
    pub d1_ema50: f64,
}

impl HtfSnapshot {
    pub fn from_series(h4: &[f64], d1: &[f64]) -> Self {
        Self {
            h4_close: h4.last().copied().unwrap_or(0.0),
            h4_ema20: ema(h4, 20),
            d1_close: d1.last().copied().unwrap_or(0.0),
            d1_ema50: ema(d1, 50),
        }
    }

    pub fn h4_bias(&self) -> HtfBias {
        bias(self.h4_close, self.h4_ema20)
    }

    pub fn d1_bias(&self) -> HtfBias {
        bias(self.d1_close, self.d1_ema50)
    }

    pub fn combined(&self) -> HtfBias {
        let a = self.h4_bias();
        let b = self.d1_bias();
        if a == b {
            a
        } else {
            HtfBias::Neutral
        }
    }

    pub fn is_aligned(&self, dir: TradeDir) -> bool {
        let c = self.combined();
        match dir {
            TradeDir::Long => c == HtfBias::Bull,
            TradeDir::Short => c == HtfBias::Bear,
            TradeDir::None => false,
        }
    }
}

fn bias(close: f64, ema: f64) -> HtfBias {
    if close > ema * 1.0001 {
        HtfBias::Bull
    } else if close < ema * 0.9999 {
        HtfBias::Bear
    } else {
        HtfBias::Neutral
    }
}
