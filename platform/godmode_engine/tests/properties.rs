//! Property tests for the hard invariants from brief §19.
//!
//! These are intended to catch regressions where someone "fixes" something
//! and accidentally relaxes a non-negotiable rule. The property suite
//! generates wide ranges of inputs and asserts the invariant always holds.

use chrono::{TimeZone, Utc};
use godmode_engine::common::{normalise_volume, AccountState, Bar};
use godmode_engine::engine::{BarCloseInput, Engine, EngineConfig, EngineEvent};
use godmode_engine::risk::RiskManager;
use proptest::prelude::*;

fn account() -> AccountState {
    AccountState {
        equity: 10_000.0,
        balance: 10_000.0,
        spread: 0.00002,
        pip_size: 0.0001,
        tick_size: 0.00001,
        pip_value: 10.0,
        volume_step: 0.01,
        volume_min: 0.01,
    }
}

proptest! {
    /// Brief §12 rule 2: RiskPct is hard-clamped at 2.0. No matter what
    /// the user passes in, the manager must never store > 2.0.
    #[test]
    fn risk_pct_never_exceeds_two(input in 0.0_f64..1000.0) {
        let r = RiskManager::new(
            input,
            input * 0.5,
            5.0,
            3,
            2.0,
            10_000.0,
            Utc.with_ymd_and_hms(2026, 5, 5, 0, 0, 0).unwrap(),
        );
        prop_assert!(r.risk_pct <= 2.0);
        prop_assert!(r.risk_pct >= 0.0);
        prop_assert!(r.risk_half_pct <= 2.0);
    }

    /// Brief §11.8 sizing: computed volume must never exceed the volume
    /// implied by `risk_amount / sl_pip_distance / pip_value`. Round-down
    /// in `normalise_volume` is the safety; round-up would overspend.
    #[test]
    fn normalise_never_rounds_up(
        raw in 0.0_f64..1_000.0,
        step in 0.001_f64..1.0,
        min in 0.0_f64..0.5,
    ) {
        let v = normalise_volume(raw, step, min);
        prop_assert!(v <= raw + 1e-12,
            "normalise rounded UP: raw={raw} step={step} -> {v}");
    }

    /// The CVD slope must equal cvd[0] - cvd[5] when ≥6 bars exist; this
    /// invariant underpins GATE 5 (F4 CVD confirmation).
    #[test]
    fn cvd_slope_5_matches_definition(seed in 0_u64..1000) {
        use godmode_engine::common::Tick;
        use godmode_engine::delta::DeltaEngine;
        let mut de = DeltaEngine::new(50, 0.00001);
        // Drive 100 ticks deterministically; bar-close every 10 ticks.
        let mut last_mid = 1.0_f64;
        for i in 0..100 {
            let drift = if (seed + i) % 3 == 0 { 0.0001 } else { -0.00005 };
            let mid = last_mid + drift;
            last_mid = mid;
            let t = Tick {
                ts: Utc.timestamp_opt(i as i64, 0).unwrap(),
                bid: mid - 0.00005,
                ask: mid + 0.00005,
                last: mid,
                volume: 1.0,
                is_buy_aggressor: None,
            };
            de.on_tick(&t);
            if i % 10 == 9 {
                de.on_bar_close(&Bar {
                    ts_open: Utc.timestamp_opt((i - 9) as i64, 0).unwrap(),
                    ts_close: Utc.timestamp_opt(i as i64, 0).unwrap(),
                    open: mid - 0.0001,
                    high: mid + 0.0002,
                    low: mid - 0.0002,
                    close: mid,
                    volume: 10.0,
                    bar_delta: None,
                });
            }
        }
        let s = de.cvd_slope_5();
        let manual = de.cvd_at(0) - de.cvd_at(5);
        prop_assert!((s - manual).abs() < 1e-9);
    }
}

#[test]
fn engine_pipeline_never_skips_kill_switches() {
    // Construct an engine with a wide range of equity drawdowns and
    // verify GATE 0 always fires before any other gate when a kill
    // switch is tripped.
    for dd_pct in [-1.0, -3.0, -5.0, -7.0, -10.0] {
        let cfg = EngineConfig::default();
        let starting = account();
        let now = Utc.with_ymd_and_hms(2026, 5, 5, 12, 0, 0).unwrap();
        let mut engine = Engine::new(cfg, starting, now);
        let mut drawn = starting;
        drawn.equity = starting.equity * (1.0 + dd_pct / 100.0);
        let bar = Bar {
            ts_open: now,
            ts_close: now + chrono::Duration::minutes(15),
            open: 1.083,
            high: 1.0833,
            low: 1.0828,
            close: 1.0832,
            volume: 1000.0,
            bar_delta: None,
        };
        let events = engine.on_bar_close(BarCloseInput {
            bars: &[bar],
            h4_closes: &[],
            d1_closes: &[],
            atr14: 0.0006,
            correlated_cvd_slope: 0.0,
            account: drawn,
        });
        // Expectation: if the DD breaches -5%, GATE 0 must be first
        // failed gate emitted.
        if dd_pct <= -5.0 {
            let first_failed = events
                .iter()
                .find_map(|e| match e {
                    EngineEvent::Gate(g) if !g.result.passed => Some(g.gate),
                    _ => None,
                });
            assert_eq!(
                first_failed,
                Some(0),
                "DD={dd_pct}%: kill switch should be first failed gate"
            );
        }
    }
}
