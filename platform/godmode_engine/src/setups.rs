//! All 25 setup detectors. Brief §6 — IDs and behaviour mirror
//! `OF_SetupDetectors.mqh` and `SetupDetectors.cs` value-for-value.
//!
//! Each detector returns `Option<SetupCandidate>`. Tag, direction, SL/TP
//! geometry, and stars must agree with the MT5/cTrader implementations.
//! Conformance is verified by `tests/conformance.rs`.

use crate::common::{Bar, SetupCandidate, SetupId, TradeDir, VpLoc};
use crate::delta::DeltaEngine;
use crate::footprint::FootprintAnalyzer;
use crate::profile::VolumeProfile;
use crate::stars;

#[derive(Debug, Clone, Copy)]
pub struct DetectorContext<'a> {
    pub bars: &'a [Bar],
    pub bid: f64,
    pub ask: f64,
    pub tick_size: f64,
    pub pip_size: f64,
    /// Tolerance for VP location classification, in price units.
    pub loc_tol: f64,
    pub min_abs_stars: i32,
    /// ATR(14) on the host timeframe; pass `0.0` if unavailable.
    pub atr14: f64,
    /// Optional correlated-symbol CVD slope for SMT divergence (setup #20).
    /// Pass `0.0` to disable.
    pub correlated_cvd_slope: f64,
}

/// Build a candidate with SL 2 ticks beyond the aggression candle and TP at
/// either an explicit target or the POC. Mirrors `Build()` in cTrader.
fn build(
    sym_bid: f64,
    sym_ask: f64,
    tick: f64,
    bars: &[Bar],
    id: SetupId,
    dir: TradeDir,
    poc: f64,
    target_level: f64,
    loc: VpLoc,
    abs_stars: i32,
    reason: &str,
) -> SetupCandidate {
    let agg_h = bars[0].high;
    let agg_l = bars[0].low;
    let mut c = SetupCandidate::empty();
    c.setup_id = id;
    c.direction = dir;
    c.abs_stars = abs_stars;
    c.loc = loc;
    c.reason = reason.to_owned();
    let tp = if target_level > 0.0 { target_level } else { poc };
    match dir {
        TradeDir::Long => {
            c.entry = sym_ask;
            c.sl = agg_l - 2.0 * tick;
            c.tp = tp;
        }
        TradeDir::Short => {
            c.entry = sym_bid;
            c.sl = agg_h + 2.0 * tick;
            c.tp = tp;
        }
        TradeDir::None => {}
    }
    c
}

// ============================================================================
// 25 detectors. The bars slice is newest-first: bars[0] is the just-closed bar.
// ============================================================================

pub fn abs_bot(
    ctx: DetectorContext,
    de: &DeltaEngine,
    vp: &VolumeProfile,
    fp: &FootprintAnalyzer,
) -> Option<SetupCandidate> {
    let last = ctx.bars[0];
    let loc = vp.location_at(last.close, ctx.loc_tol);
    if loc != VpLoc::Val && loc != VpLoc::Lvn {
        return None;
    }
    if !fp.bullish_absorption(de, &last) {
        return None;
    }
    let stars_n = stars::compute(&last, de, TradeDir::Long);
    if stars_n < ctx.min_abs_stars {
        return None;
    }
    let mut c = build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::AbsBot,
        TradeDir::Long,
        vp.poc,
        vp.poc,
        loc,
        stars_n,
        "AbsBot@VAL/LVN",
    );
    c.abs_stars = stars_n;
    Some(c)
}

pub fn abs_top(
    ctx: DetectorContext,
    de: &DeltaEngine,
    vp: &VolumeProfile,
    fp: &FootprintAnalyzer,
) -> Option<SetupCandidate> {
    let last = ctx.bars[0];
    let loc = vp.location_at(last.close, ctx.loc_tol);
    if loc != VpLoc::Vah && loc != VpLoc::Hvn {
        return None;
    }
    if !fp.bearish_absorption(de, &last) {
        return None;
    }
    let stars_n = stars::compute(&last, de, TradeDir::Short);
    if stars_n < ctx.min_abs_stars {
        return None;
    }
    let mut c = build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::AbsTop,
        TradeDir::Short,
        vp.poc,
        vp.poc,
        loc,
        stars_n,
        "AbsTop@VAH/HVN",
    );
    c.abs_stars = stars_n;
    Some(c)
}

pub fn cvd_bear(ctx: DetectorContext, de: &DeltaEngine, vp: &VolumeProfile) -> Option<SetupCandidate> {
    if !de.bearish_divergence() {
        return None;
    }
    let close = ctx.bars[0].close;
    Some(build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::CvdBear,
        TradeDir::Short,
        vp.poc,
        vp.poc,
        vp.location_at(close, ctx.loc_tol),
        0,
        "CVD bear div",
    ))
}

pub fn cvd_bull(ctx: DetectorContext, de: &DeltaEngine, vp: &VolumeProfile) -> Option<SetupCandidate> {
    if !de.bullish_divergence() {
        return None;
    }
    let close = ctx.bars[0].close;
    Some(build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::CvdBull,
        TradeDir::Long,
        vp.poc,
        vp.poc,
        vp.location_at(close, ctx.loc_tol),
        0,
        "CVD bull div",
    ))
}

pub fn val_bounce(ctx: DetectorContext, de: &DeltaEngine, vp: &VolumeProfile) -> Option<SetupCandidate> {
    let last = ctx.bars[0];
    if vp.location_at(last.close, ctx.loc_tol) != VpLoc::Val {
        return None;
    }
    if last.close <= last.open || de.bar_delta() < 0.0 {
        return None;
    }
    Some(build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::ValBnc,
        TradeDir::Long,
        vp.poc,
        vp.poc,
        VpLoc::Val,
        0,
        "VAL bounce",
    ))
}

pub fn vah_fade(ctx: DetectorContext, de: &DeltaEngine, vp: &VolumeProfile) -> Option<SetupCandidate> {
    let last = ctx.bars[0];
    if vp.location_at(last.close, ctx.loc_tol) != VpLoc::Vah {
        return None;
    }
    if last.close >= last.open || de.bar_delta() > 0.0 {
        return None;
    }
    Some(build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::VahFade,
        TradeDir::Short,
        vp.poc,
        vp.poc,
        VpLoc::Vah,
        0,
        "VAH fade",
    ))
}

pub fn poc_return(ctx: DetectorContext, de: &DeltaEngine, vp: &VolumeProfile) -> Option<SetupCandidate> {
    let last = ctx.bars[0];
    if vp.location_at(last.close, ctx.loc_tol) != VpLoc::Poc {
        return None;
    }
    let dir = if de.bar_delta() >= 0.0 {
        TradeDir::Long
    } else {
        TradeDir::Short
    };
    let tp = if matches!(dir, TradeDir::Long) { vp.vah } else { vp.val };
    Some(build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::PocRet,
        dir,
        vp.poc,
        tp,
        VpLoc::Poc,
        0,
        "POC return",
    ))
}

pub fn lvn_long(ctx: DetectorContext, de: &DeltaEngine, vp: &VolumeProfile) -> Option<SetupCandidate> {
    let last = ctx.bars[0];
    if vp.location_at(last.close, ctx.loc_tol) != VpLoc::Lvn {
        return None;
    }
    if de.bar_delta() <= 0.0 || de.volume_z() < 1.0 {
        return None;
    }
    Some(build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::LvnLong,
        TradeDir::Long,
        vp.poc,
        vp.vah,
        VpLoc::Lvn,
        0,
        "LVN accel L",
    ))
}

pub fn lvn_short(ctx: DetectorContext, de: &DeltaEngine, vp: &VolumeProfile) -> Option<SetupCandidate> {
    let last = ctx.bars[0];
    if vp.location_at(last.close, ctx.loc_tol) != VpLoc::Lvn {
        return None;
    }
    if de.bar_delta() >= 0.0 || de.volume_z() < 1.0 {
        return None;
    }
    Some(build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::LvnShort,
        TradeDir::Short,
        vp.poc,
        vp.val,
        VpLoc::Lvn,
        0,
        "LVN accel S",
    ))
}

pub fn hvn_rej(ctx: DetectorContext, de: &DeltaEngine, vp: &VolumeProfile) -> Option<SetupCandidate> {
    let last = ctx.bars[0];
    if vp.location_at(last.close, ctx.loc_tol) != VpLoc::Hvn {
        return None;
    }
    let dir = if de.bar_delta() < 0.0 {
        TradeDir::Short
    } else {
        TradeDir::Long
    };
    Some(build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::HvnRej,
        dir,
        vp.poc,
        vp.poc,
        VpLoc::Hvn,
        0,
        "HVN rej",
    ))
}

pub fn stack_bull(
    ctx: DetectorContext,
    de: &DeltaEngine,
    vp: &VolumeProfile,
    fp: &FootprintAnalyzer,
) -> Option<SetupCandidate> {
    if !fp.stacked_bull_imbalance(de) || de.cvd_slope_5() <= 0.0 {
        return None;
    }
    let close = ctx.bars[0].close;
    Some(build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::StackBull,
        TradeDir::Long,
        vp.poc,
        vp.vah,
        vp.location_at(close, ctx.loc_tol),
        0,
        "Stack bull+CVD",
    ))
}

pub fn stack_bear(
    ctx: DetectorContext,
    de: &DeltaEngine,
    vp: &VolumeProfile,
    fp: &FootprintAnalyzer,
) -> Option<SetupCandidate> {
    if !fp.stacked_bear_imbalance(de) || de.cvd_slope_5() >= 0.0 {
        return None;
    }
    let close = ctx.bars[0].close;
    Some(build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::StackBear,
        TradeDir::Short,
        vp.poc,
        vp.val,
        vp.location_at(close, ctx.loc_tol),
        0,
        "Stack bear+CVD",
    ))
}

pub fn pull_stack(ctx: DetectorContext, de: &DeltaEngine, vp: &VolumeProfile) -> Option<SetupCandidate> {
    let mut zone = 0.0;
    let mut dir = TradeDir::None;
    for i in 1..10 {
        let bull = de.delta(i) > 0.0 && de.delta(i + 1) > 0.0 && de.delta(i + 2) > 0.0;
        let bear = de.delta(i) < 0.0 && de.delta(i + 1) < 0.0 && de.delta(i + 2) < 0.0;
        if i >= ctx.bars.len() {
            break;
        }
        if bull {
            zone = ctx.bars[i].low;
            dir = TradeDir::Long;
            break;
        }
        if bear {
            zone = ctx.bars[i].high;
            dir = TradeDir::Short;
            break;
        }
    }
    if matches!(dir, TradeDir::None) {
        return None;
    }
    let close = ctx.bars[0].close;
    if (close - zone).abs() > 5.0 * ctx.pip_size {
        return None;
    }
    Some(build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::PullStack,
        dir,
        vp.poc,
        vp.poc,
        vp.location_at(close, ctx.loc_tol),
        0,
        "Pull stack",
    ))
}

pub fn spring(ctx: DetectorContext, de: &DeltaEngine, vp: &VolumeProfile) -> Option<SetupCandidate> {
    if ctx.bars.len() < 30 {
        return None;
    }
    let mut swing_low = ctx.bars[5].low;
    for i in 6..30 {
        swing_low = swing_low.min(ctx.bars[i].low);
    }
    let cur_l = ctx.bars[0].low;
    let cur_c = ctx.bars[0].close;
    if cur_l > swing_low || cur_c <= swing_low || !de.bullish_divergence() {
        return None;
    }
    Some(build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::Spring,
        TradeDir::Long,
        vp.poc,
        vp.poc,
        vp.location_at(cur_c, ctx.loc_tol),
        0,
        "Spring",
    ))
}

pub fn upthrust(ctx: DetectorContext, de: &DeltaEngine, vp: &VolumeProfile) -> Option<SetupCandidate> {
    if ctx.bars.len() < 30 {
        return None;
    }
    let mut swing_high = ctx.bars[5].high;
    for i in 6..30 {
        swing_high = swing_high.max(ctx.bars[i].high);
    }
    let cur_h = ctx.bars[0].high;
    let cur_c = ctx.bars[0].close;
    if cur_h < swing_high || cur_c >= swing_high || !de.bearish_divergence() {
        return None;
    }
    Some(build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::Upthrust,
        TradeDir::Short,
        vp.poc,
        vp.poc,
        vp.location_at(cur_c, ctx.loc_tol),
        0,
        "Upthrust",
    ))
}

pub fn sos(ctx: DetectorContext, de: &DeltaEngine, vp: &VolumeProfile) -> Option<SetupCandidate> {
    if de.cvd_slope_5() <= 0.0 || de.volume_z() < 1.0 {
        return None;
    }
    let close = ctx.bars[0].close;
    Some(build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::Sos,
        TradeDir::Long,
        vp.poc,
        vp.vah,
        vp.location_at(close, ctx.loc_tol),
        0,
        "SOS",
    ))
}

pub fn lpsy(ctx: DetectorContext, de: &DeltaEngine, vp: &VolumeProfile) -> Option<SetupCandidate> {
    if de.cvd_slope_5() >= 0.0 || de.volume_z() < 1.0 {
        return None;
    }
    let close = ctx.bars[0].close;
    Some(build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::Lpsy,
        TradeDir::Short,
        vp.poc,
        vp.val,
        vp.location_at(close, ctx.loc_tol),
        0,
        "LPSY",
    ))
}

pub fn liq_sweep(ctx: DetectorContext, vp: &VolumeProfile) -> Option<SetupCandidate> {
    if ctx.bars.len() < 50 {
        return None;
    }
    let mut s_h = ctx.bars[3].high;
    let mut s_l = ctx.bars[3].low;
    for i in 4..50 {
        s_h = s_h.max(ctx.bars[i].high);
        s_l = s_l.min(ctx.bars[i].low);
    }
    let c_h = ctx.bars[0].high;
    let c_l = ctx.bars[0].low;
    let c_c = ctx.bars[0].close;
    let dir = if c_h > s_h && c_c < s_h {
        TradeDir::Short
    } else if c_l < s_l && c_c > s_l {
        TradeDir::Long
    } else {
        TradeDir::None
    };
    if matches!(dir, TradeDir::None) {
        return None;
    }
    Some(build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::LiqSweep,
        dir,
        vp.poc,
        vp.poc,
        vp.location_at(c_c, ctx.loc_tol),
        0,
        "Liq sweep",
    ))
}

pub fn ob_return(ctx: DetectorContext, de: &DeltaEngine, vp: &VolumeProfile) -> Option<SetupCandidate> {
    let cur = ctx.bars[0].close;
    let pip = ctx.pip_size;
    for i in 5..30 {
        if i >= ctx.bars.len() {
            break;
        }
        let oo = ctx.bars[i].open;
        let oc = ctx.bars[i].close;
        if oc < oo && (cur - ctx.bars[i].high).abs() < 5.0 * pip && de.cvd_slope_5() < 0.0 {
            return Some(build(
                ctx.bid,
                ctx.ask,
                ctx.tick_size,
                ctx.bars,
                SetupId::ObReturn,
                TradeDir::Short,
                vp.poc,
                vp.val,
                vp.location_at(cur, ctx.loc_tol),
                0,
                "OB return short",
            ));
        }
        if oc > oo && (cur - ctx.bars[i].low).abs() < 5.0 * pip && de.cvd_slope_5() > 0.0 {
            return Some(build(
                ctx.bid,
                ctx.ask,
                ctx.tick_size,
                ctx.bars,
                SetupId::ObReturn,
                TradeDir::Long,
                vp.poc,
                vp.vah,
                vp.location_at(cur, ctx.loc_tol),
                0,
                "OB return long",
            ));
        }
    }
    None
}

pub fn smt_div(ctx: DetectorContext, de: &DeltaEngine, vp: &VolumeProfile) -> Option<SetupCandidate> {
    let my = de.cvd_slope_5();
    if my * ctx.correlated_cvd_slope >= 0.0 {
        return None;
    }
    let close = ctx.bars[0].close;
    let dir = if my > 0.0 { TradeDir::Long } else { TradeDir::Short };
    Some(build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::SmtDiv,
        dir,
        vp.poc,
        vp.poc,
        vp.location_at(close, ctx.loc_tol),
        0,
        "SMT div",
    ))
}

pub fn breaker(ctx: DetectorContext, de: &DeltaEngine, vp: &VolumeProfile) -> Option<SetupCandidate> {
    if ctx.bars.len() < 40 {
        return None;
    }
    let mut s_h = ctx.bars[5].high;
    let mut s_l = ctx.bars[5].low;
    for i in 6..40 {
        s_h = s_h.max(ctx.bars[i].high);
        s_l = s_l.min(ctx.bars[i].low);
    }
    let cur = ctx.bars[0].close;
    let pip = ctx.pip_size;
    if cur > s_h && (cur - s_h).abs() < 5.0 * pip && de.cvd_slope_5() > 0.0 {
        return Some(build(
            ctx.bid,
            ctx.ask,
            ctx.tick_size,
            ctx.bars,
            SetupId::Breaker,
            TradeDir::Long,
            vp.poc,
            vp.vah,
            vp.location_at(cur, ctx.loc_tol),
            0,
            "Breaker L",
        ));
    }
    if cur < s_l && (cur - s_l).abs() < 5.0 * pip && de.cvd_slope_5() < 0.0 {
        return Some(build(
            ctx.bid,
            ctx.ask,
            ctx.tick_size,
            ctx.bars,
            SetupId::Breaker,
            TradeDir::Short,
            vp.poc,
            vp.val,
            vp.location_at(cur, ctx.loc_tol),
            0,
            "Breaker S",
        ));
    }
    None
}

pub fn amd(ctx: DetectorContext, de: &DeltaEngine, vp: &VolumeProfile) -> Option<SetupCandidate> {
    if ctx.bars.len() < 24 {
        return None;
    }
    let mut rh = ctx.bars[5].high;
    let mut rl = ctx.bars[5].low;
    for i in 6..24 {
        rh = rh.max(ctx.bars[i].high);
        rl = rl.min(ctx.bars[i].low);
    }
    let cur = ctx.bars[0].close;
    if cur > rh && de.delta_z() > 1.5 {
        return Some(build(
            ctx.bid,
            ctx.ask,
            ctx.tick_size,
            ctx.bars,
            SetupId::Amd,
            TradeDir::Long,
            vp.poc,
            vp.vah,
            vp.location_at(cur, ctx.loc_tol),
            0,
            "AMD long",
        ));
    }
    if cur < rl && de.delta_z() < -1.5 {
        return Some(build(
            ctx.bid,
            ctx.ask,
            ctx.tick_size,
            ctx.bars,
            SetupId::Amd,
            TradeDir::Short,
            vp.poc,
            vp.val,
            vp.location_at(cur, ctx.loc_tol),
            0,
            "AMD short",
        ));
    }
    None
}

pub fn unfinished_auction(
    ctx: DetectorContext,
    fp: &FootprintAnalyzer,
    vp: &VolumeProfile,
) -> Option<SetupCandidate> {
    if !fp.unfinished_auction(ctx.bars, ctx.atr14) {
        return None;
    }
    let cur_h = ctx.bars[0].high;
    let prev_h = ctx.bars.get(1).map(|b| b.high).unwrap_or(cur_h);
    let cur_c = ctx.bars[0].close;
    let dir = if cur_h > prev_h { TradeDir::Short } else { TradeDir::Long };
    Some(build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::UnfAuc,
        dir,
        vp.poc,
        vp.poc,
        vp.location_at(cur_c, ctx.loc_tol),
        0,
        "Unfinished auc",
    ))
}

pub fn poor_hl(ctx: DetectorContext, de: &DeltaEngine, vp: &VolumeProfile) -> Option<SetupCandidate> {
    if ctx.bars.len() < 2 {
        return None;
    }
    let prev_h = ctx.bars[1].high;
    let prev_l = ctx.bars[1].low;
    let cur_h = ctx.bars[0].high;
    let cur_l = ctx.bars[0].low;
    let cur_c = ctx.bars[0].close;
    let pip = ctx.pip_size;
    if (cur_h - prev_h).abs() < pip && de.bar_delta() < 0.0 {
        return Some(build(
            ctx.bid,
            ctx.ask,
            ctx.tick_size,
            ctx.bars,
            SetupId::PoorHL,
            TradeDir::Short,
            vp.poc,
            vp.poc,
            vp.location_at(cur_c, ctx.loc_tol),
            0,
            "Poor high",
        ));
    }
    if (cur_l - prev_l).abs() < pip && de.bar_delta() > 0.0 {
        return Some(build(
            ctx.bid,
            ctx.ask,
            ctx.tick_size,
            ctx.bars,
            SetupId::PoorHL,
            TradeDir::Long,
            vp.poc,
            vp.poc,
            vp.location_at(cur_c, ctx.loc_tol),
            0,
            "Poor low",
        ));
    }
    None
}

pub fn iceberg(ctx: DetectorContext, de: &DeltaEngine, vp: &VolumeProfile) -> Option<SetupCandidate> {
    let vol_z = de.volume_z();
    let dz = de.delta_z();
    let atr = ctx.atr14;
    if atr <= 0.0 {
        return None;
    }
    let range = ctx.bars[0].high - ctx.bars[0].low;
    if vol_z < 2.0 || dz.abs() > 0.5 || range > 0.6 * atr {
        return None;
    }
    let cur_c = ctx.bars[0].close;
    let loc = vp.location_at(cur_c, ctx.loc_tol);
    if matches!(loc, VpLoc::None) {
        return None;
    }
    let dir = match loc {
        VpLoc::Val | VpLoc::Lvn => TradeDir::Long,
        _ => TradeDir::Short,
    };
    Some(build(
        ctx.bid,
        ctx.ask,
        ctx.tick_size,
        ctx.bars,
        SetupId::Iceberg,
        dir,
        vp.poc,
        vp.poc,
        loc,
        0,
        "Iceberg",
    ))
}

/// Run all 25 detectors and collect every non-None candidate. The engine
/// orchestrator scores each one and picks the best.
pub fn run_all(
    ctx: DetectorContext,
    de: &DeltaEngine,
    vp: &VolumeProfile,
    fp: &FootprintAnalyzer,
) -> Vec<SetupCandidate> {
    let mut out = Vec::new();
    macro_rules! push {
        ($e:expr) => {
            if let Some(c) = $e {
                out.push(c);
            }
        };
    }
    push!(abs_bot(ctx, de, vp, fp));
    push!(abs_top(ctx, de, vp, fp));
    push!(cvd_bear(ctx, de, vp));
    push!(cvd_bull(ctx, de, vp));
    push!(val_bounce(ctx, de, vp));
    push!(vah_fade(ctx, de, vp));
    push!(poc_return(ctx, de, vp));
    push!(lvn_long(ctx, de, vp));
    push!(lvn_short(ctx, de, vp));
    push!(hvn_rej(ctx, de, vp));
    push!(stack_bull(ctx, de, vp, fp));
    push!(stack_bear(ctx, de, vp, fp));
    push!(pull_stack(ctx, de, vp));
    push!(spring(ctx, de, vp));
    push!(upthrust(ctx, de, vp));
    push!(sos(ctx, de, vp));
    push!(lpsy(ctx, de, vp));
    push!(liq_sweep(ctx, vp));
    push!(ob_return(ctx, de, vp));
    push!(smt_div(ctx, de, vp));
    push!(breaker(ctx, de, vp));
    push!(amd(ctx, de, vp));
    push!(unfinished_auction(ctx, fp, vp));
    push!(poor_hl(ctx, de, vp));
    push!(iceberg(ctx, de, vp));
    out
}
