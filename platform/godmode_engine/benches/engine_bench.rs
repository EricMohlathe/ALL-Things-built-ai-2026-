//! Performance benches for the trading engine.
//!
//! Brief target: tick→gate-decision latency ≤2ms p99 on a mid-tier laptop.
//! Use `cargo bench` to run; results land in `target/criterion/`.

use chrono::{TimeZone, Utc};
use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use godmode_engine::{
    common::{AccountState, Bar, Tick},
    engine::{BarCloseInput, Engine, EngineConfig},
};

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

fn synthetic_bars(n: usize) -> Vec<Bar> {
    let start = Utc.with_ymd_and_hms(2026, 5, 5, 8, 0, 0).unwrap();
    (0..n)
        .map(|i| {
            let t = start + chrono::Duration::minutes(15 * i as i64);
            let base = 1.0830 + (i as f64) * 0.00005;
            let dip = if (140..160).contains(&i) { -0.0010 } else { 0.0 };
            let o = base + dip;
            let c = o + 0.00010;
            Bar {
                ts_open: t,
                ts_close: t + chrono::Duration::minutes(15),
                open: o,
                high: o.max(c) + 0.00015,
                low: o.min(c) - 0.00015,
                close: c,
                volume: 1000.0 + (i as f64).sin().abs() * 200.0,
                bar_delta: None,
            }
        })
        .collect()
}

fn synthetic_ticks(n: usize) -> Vec<Tick> {
    let mut ticks = Vec::with_capacity(n);
    let mut last = 1.0830_f64;
    for i in 0..n {
        let drift = if i % 3 == 0 { 0.00002 } else { -0.00001 };
        last += drift;
        ticks.push(Tick {
            ts: Utc.timestamp_opt(i as i64, 0).unwrap(),
            bid: last - 0.00001,
            ask: last + 0.00001,
            last,
            volume: 1.0,
            is_buy_aggressor: None,
        });
    }
    ticks
}

fn bench_tick_ingest(c: &mut Criterion) {
    let mut group = c.benchmark_group("tick_ingest");
    for n in [1_000, 10_000, 100_000] {
        let ticks = synthetic_ticks(n);
        group.throughput(Throughput::Elements(n as u64));
        group.bench_with_input(BenchmarkId::from_parameter(n), &ticks, |b, ticks| {
            b.iter(|| {
                use godmode_engine::delta::DeltaEngine;
                let mut de = DeltaEngine::new(100, 0.00001);
                for t in ticks {
                    de.on_tick(black_box(t));
                }
            });
        });
    }
    group.finish();
}

fn bench_bar_close_pipeline(c: &mut Criterion) {
    let mut group = c.benchmark_group("bar_close_pipeline");
    for n_bars in [50, 200, 1000] {
        group.bench_with_input(
            BenchmarkId::from_parameter(n_bars),
            &n_bars,
            |b, &n_bars| {
                b.iter_batched(
                    || {
                        let cfg = EngineConfig::default();
                        let acct = account();
                        let now = Utc.with_ymd_and_hms(2026, 5, 5, 8, 0, 0).unwrap();
                        let engine = Engine::new(cfg, acct, now);
                        let bars = synthetic_bars(n_bars);
                        (engine, bars, acct)
                    },
                    |(mut engine, bars, acct)| {
                        let mut events = 0;
                        for i in 0..bars.len() {
                            let view: Vec<Bar> =
                                bars[..=i].iter().rev().cloned().collect();
                            events += engine
                                .on_bar_close(BarCloseInput {
                                    bars: &view,
                                    h4_closes: &[],
                                    d1_closes: &[],
                                    atr14: 0.0006,
                                    correlated_cvd_slope: 0.0,
                                    account: acct,
                                })
                                .len();
                        }
                        black_box(events)
                    },
                    criterion::BatchSize::SmallInput,
                );
            },
        );
    }
    group.finish();
}

fn bench_volume_profile(c: &mut Criterion) {
    use godmode_engine::profile::VolumeProfile;
    let bars: Vec<Bar> = synthetic_bars(96).into_iter().rev().collect();
    c.bench_function("volume_profile_recompute", |b| {
        b.iter(|| {
            let mut vp = VolumeProfile::new(50, 96, 0.70, 0.30, 0.80);
            vp.recompute(black_box(&bars));
        });
    });
}

criterion_group!(
    benches,
    bench_tick_ingest,
    bench_bar_close_pipeline,
    bench_volume_profile
);
criterion_main!(benches);
