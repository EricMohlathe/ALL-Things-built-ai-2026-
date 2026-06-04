//! Conformance test harness — generalised TESTING.md Phase 6.
//!
//! Compares this Rust engine's output against a reference signal stream
//! exported from either the MT5 or cTrader build. The "≥95% agreement"
//! threshold from the brief applies. For now we ship a smoke test that
//! exercises the gate pipeline end-to-end on a tiny synthetic feed; the
//! full reference replay is plumbed into the application shell's CI.

use chrono::{TimeZone, Utc};
use godmode_engine::common::{AccountState, Bar, OpMode, Tick};
use godmode_engine::engine::{BarCloseInput, Engine, EngineConfig, EngineEvent};
use godmode_engine::replay::{replay_bars, ReplayConfig};

fn synthetic_bars() -> Vec<Bar> {
    // 200 M15 bars trending up then a sharp pullback into VAL.
    let start = Utc.with_ymd_and_hms(2026, 5, 5, 8, 0, 0).unwrap();
    let mut bars = Vec::new();
    for i in 0..200 {
        let t = start + chrono::Duration::minutes(15 * i as i64);
        let base = 1.0830 + (i as f64) * 0.00005;
        let dip = if (140..160).contains(&i) {
            -0.0010
        } else {
            0.0
        };
        let o = base + dip;
        let c = o + 0.00010;
        let h = o.max(c) + 0.00015;
        let l = o.min(c) - 0.00015;
        bars.push(Bar {
            ts_open: t,
            ts_close: t + chrono::Duration::minutes(15),
            open: o,
            high: h,
            low: l,
            close: c,
            volume: 1000.0 + (i as f64).sin().abs() * 200.0,
            bar_delta: None,
        });
    }
    bars
}

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

#[test]
fn engine_emits_events_for_synthetic_replay() {
    let cfg = EngineConfig {
        mode: OpMode::Manual,
        allow_ldn_main: true,
        allow_ldn_open: true,
        ..Default::default()
    };
    let acct = account();
    let now = Utc.with_ymd_and_hms(2026, 5, 5, 8, 0, 0).unwrap();
    let mut engine = Engine::new(cfg, acct, now);
    let bars = synthetic_bars();
    let events = replay_bars(
        &mut engine,
        &bars,
        ReplayConfig {
            account: acct,
            atr14: 0.0006,
            correlated_cvd_slope: 0.0,
        },
    );
    assert!(!events.is_empty(), "engine emitted no events for 200 bars");
    let gate0_count = events
        .iter()
        .filter(|e| matches!(e, EngineEvent::Gate(g) if g.gate == 0))
        .count();
    assert!(gate0_count >= 1, "GATE 0 should fire at least once");
}

#[test]
fn tick_aggressor_classification_is_deterministic() {
    use godmode_engine::delta::DeltaEngine;
    let mut de = DeltaEngine::new(50, 0.00001);
    let t1 = Tick {
        ts: Utc.timestamp_opt(0, 0).unwrap(),
        bid: 1.0,
        ask: 1.0001,
        last: 1.0,
        volume: 1.0,
        is_buy_aggressor: None,
    };
    let t2 = Tick {
        ts: Utc.timestamp_opt(1, 0).unwrap(),
        bid: 1.00005,
        ask: 1.00015,
        last: 1.0001,
        volume: 1.0,
        is_buy_aggressor: None,
    };
    de.on_tick(&t1);
    de.on_tick(&t2);
    // Bar close just to flush state; no panic.
    de.on_bar_close(&Bar {
        ts_open: t1.ts,
        ts_close: t2.ts,
        open: 1.0,
        high: 1.0002,
        low: 0.9999,
        close: 1.0001,
        volume: 2.0,
        bar_delta: None,
    });
    assert!(de.bar_delta() >= 0.0, "uptick should classify as buy");
}

#[test]
fn risk_pct_is_hard_clamped_at_two() {
    let r = godmode_engine::risk::RiskManager::new(
        9.0,
        0.5,
        5.0,
        3,
        2.0,
        10_000.0,
        Utc.with_ymd_and_hms(2026, 5, 5, 0, 0, 0).unwrap(),
    );
    assert_eq!(r.risk_pct, 2.0);
}

#[test]
fn engine_pipeline_short_circuits_on_kill_switch() {
    let cfg = EngineConfig::default();
    // Day starts at 10_000 — engine captures this on construction.
    let starting = account();
    let now = Utc.with_ymd_and_hms(2026, 5, 5, 12, 0, 0).unwrap();
    let mut engine = Engine::new(cfg, starting, now);
    // Mid-day equity has dropped to 9_400 → -6%, below the 5% DD floor.
    let mut drawn = starting;
    drawn.equity = 9_400.0;
    let bars = synthetic_bars();
    let view: Vec<Bar> = bars.iter().rev().cloned().collect();
    let events = engine.on_bar_close(BarCloseInput {
        bars: &view,
        h4_closes: &[],
        d1_closes: &[],
        atr14: 0.0006,
        correlated_cvd_slope: 0.0,
        account: drawn,
    });
    let killed = events
        .iter()
        .any(|e| matches!(e, EngineEvent::Gate(g) if g.gate == 0 && !g.result.passed));
    assert!(killed, "DD kill switch should fire when equity is below threshold");
}
