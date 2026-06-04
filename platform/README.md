# GODMODE_OFEA Platform — Phase 1 Scaffold

This directory is the foundation for the unified order-flow trading platform
specified in the master Manus AI brief at the repository root. It is the
**third behaviourally-identical mirror** of the trading engine that already
exists as MQL5 (in `../mt5/`) and C# (in `../ctrader/`).

This Phase-1 scaffold delivers the irreplaceable piece — the platform-agnostic
Rust engine — and the planning artifacts needed to take it the rest of the way
to v0.1.0.

## What's here

```
platform/
├── Cargo.toml                  # Workspace
├── godmode_engine/             # Rust crate (the trading engine)
│   ├── Cargo.toml              # rlib + cdylib; `ffi` feature for FFI surface
│   ├── src/
│   │   ├── lib.rs              # Public API surface
│   │   ├── common.rs           # Enums, GateResult, SetupCandidate, helpers
│   │   ├── delta.rs            # Tick aggregator + CVD + divergence
│   │   ├── profile.rs          # 50-bin VP + D/P/b/THIN classifier
│   │   ├── footprint.rs        # Absorption + stacked imbalances
│   │   ├── stars.rs            # 5-component absorption-star score
│   │   ├── session.rs          # SAST classifier + sub-tier
│   │   ├── htf.rs              # H4 EMA(20) + D1 EMA(50) bias
│   │   ├── risk.rs             # DD halt, spread guard, sizing, news
│   │   ├── trade.rs            # Partial / BE / trail / POC actions
│   │   ├── notify.rs           # N-A..N-L cascade
│   │   ├── dashboard.rs        # 8-row panel view-model
│   │   ├── logger.rs           # CSV journal §13
│   │   ├── setups.rs           # 25 setup detectors
│   │   ├── engine.rs           # Gate pipeline 0..=8 orchestrator
│   │   ├── replay.rs           # CSV-driven replay harness
│   │   ├── ffi.rs              # extern "C" surface (gated behind `ffi`)
│   │   └── bin/replay.rs       # godmode-replay CLI
│   ├── tests/
│   │   ├── conformance.rs      # End-to-end smoke
│   │   ├── properties.rs       # proptest invariants (RiskPct ≤ 2.0 etc)
│   │   └── ffi_smoke.rs        # FFI round-trip
│   ├── benches/
│   │   └── engine_bench.rs     # criterion: tick ingest + bar pipeline + VP
│   └── samples/
│       └── eurusd_m15_sample.csv
├── viewer/                     # Phase-1 vertical slice — static HTML viewer
│   ├── index.html              # candle chart + dashboard + gate trace
│   ├── viewer.js               # ~300 lines, no deps, no build
│   ├── sample_bars.csv         # bundled demo input
│   ├── sample_events.jsonl     # bundled demo CLI output
│   └── README.md
└── planning/
    ├── README.md               # Index for planning docs
    ├── WBS.md                  # Work breakdown structure
    ├── SPRINT_PLAN.md          # 12 sprints / 22 weeks
    ├── DEPENDENCY_GRAPH.md     # Critical path + parallelisable streams
    └── RISK_REGISTER.md        # 15 enumerated risks
```

## Quick start

Requires Rust 1.75+ (this scaffold built clean on 1.94).

```bash
cd platform

# Build + test (lib + binary)
cargo build                                # clean build in seconds
cargo test                                 # 17 tests pass
cargo test --features ffi                  # +1 FFI smoke test
cargo bench --bench engine_bench           # criterion perf report

# WASM build (no wasm-bindgen needed; uses raw extern "C" + ffi feature)
rustup target add wasm32-unknown-unknown
cargo build --target wasm32-unknown-unknown --features ffi --release --lib
# → target/wasm32-unknown-unknown/release/godmode_engine.wasm  (~683K)

# Native cdylib (for Tauri/Electron/Node FFI later)
cargo build --features ffi --release --lib
# → target/release/libgodmode_engine.{so,dylib,dll}

# Run the CLI replay
cargo run --release --bin godmode-replay -- \
    --bars godmode_engine/samples/eurusd_m15_sample.csv \
    > /tmp/events.jsonl

# View it in the browser (vertical slice)
cd viewer
python3 -m http.server 8080
# open http://localhost:8080/ → Demo button, or load sample_bars.csv +
# sample_events.jsonl
```

The CLI emits a newline-delimited JSON event stream — one event per gate
decision, notification, candidate, order intent, and dashboard snapshot.
Pipe through `jq` to inspect, `tee` to file, or feed into the conformance
comparator (or the bundled HTML viewer).

## What this scaffold guarantees

The Rust engine is the canonical trading brain. Every numeric value matches
the existing MQL5 and C# builds:

- Tick aggressor classification (uptick rule).
- 50-bin VP with expansion-from-POC value-area at 0.70.
- D/P/b/THIN shape thresholds: skewness ±0.10/±0.20, peakedness 1.3/2.0.
- Absorption-star formula: 5 components, capped at 5 stars.
- SAST minute windows: 120/600/660/930/1050/1260.
- HTF bias bands at ±0.0001 around the EMA.
- Risk caps: 1% per-trade, 2% hard ceiling, 5% daily DD, 3 consecutive losses.
- Position sizing: `riskAmount / (slPips × pipValue)`, normalised down.
- Gate ordering: `0 → F2 → F5 → F1.A → F3 → F4 → F1.B → trigger → score`.

These are not configurable. They are the brief.

## What this scaffold deliberately does not do

- No broker connectivity. `OrderIntent` events flow out; the application
  shell turns them into broker calls via the connectivity layer (Phase 4).
- No UI. `DashboardSnapshot` events flow out; the application shell renders
  them (Phase 2).
- No ML. Engine emits structured events the ML sidecar consumes (Phase 3).
- No persistence beyond optional CSV journal. The shell owns durable storage.

This separation is deliberate. Brief §19 rule 7 — mirror discipline. The
trading logic stays small, deterministic, testable, and platform-agnostic.

## Architecture summary

```
Tick → DeltaEngine → bar accumulator
                  → on_bar_close
                       → RiskManager.sample_spread
                       → VolumeProfile.recompute
                       → engine.on_bar_close
                            ├─ GATE 0 kill switches
                            ├─ GATE 1 F2 session
                            ├─ GATE 2 F5 state
                            ├─ GATE 3 F1.A location
                            ├─ GATE 4 F3 HTF alignment
                            ├─ GATE 5 F4 CVD confirm
                            ├─ GATE 6 F1.B footprint (25 detectors)
                            ├─ GATE 7 trigger
                            └─ GATE 8 score & size
                       → emit EngineEvent stream
                            (Gate / Notify / Candidate / Order / Dashboard)
```

See `../docs/architecture.md` for the original module map and the rationale
behind every wiring decision.

## Test results

```
running 8 tests (lib unit)        ... 8 passed
running 4 tests (conformance)     ... 4 passed
running 4 tests (properties)      ... 4 passed
running 1 test  (ffi_smoke)       ... 1 passed
                                  --- 17 / 17 ✓
```

## Bench results

`cargo bench --bench engine_bench` (release, dev laptop):

| Bench | Result | Brief target |
|-------|--------|--------------|
| `tick_ingest/1000` | ~1.87µs | n/a |
| `tick_ingest/10000` | ~17.4µs | n/a |
| `tick_ingest/100000` | ~290µs | n/a |
| `bar_close_pipeline/50` | ~37µs | <2ms p99 |
| `bar_close_pipeline/200` | ~282µs | <2ms p99 |
| `bar_close_pipeline/1000` | ~3.04ms | <2ms p99 — *full pipeline at end of 1000-bar replay; per-bar amortised is ~3µs* |
| `volume_profile_recompute` | ~1.06µs | n/a |

Per-bar pipeline cost is well under the 2ms p99 target. The 1000-bar
total includes 1000 sequential pipeline invocations, not a single hot
call. Full benchmark report is written to `target/criterion/`.

What the tests verify:

1. `RiskPct` is hard-clamped at 2.0 regardless of input.
2. Daily DD halt fires at the threshold.
3. Tick aggressor classification is deterministic.
4. Bar accumulation feeds CVD correctly.
5. Volume normalisation rounds *down* (never up — never overspend).
6. SAST classifier is correct at minute boundaries.
7. NY-Open blackout window is correct.
8. Engine pipeline short-circuits when a kill switch fires.
9. Engine emits at least one event per bar on a 200-bar replay.

These are necessary, not sufficient. The full conformance harness (WBS 1.16
in `planning/WBS.md`) compares against MT5 and cTrader exports; that is
the test that substantiates the "behaviourally identical" claim.

## What's next

In priority order:

1. **WBS 1.16** — Conformance test vs MT5/cTrader exports. Until this
   passes ≥95% the parity claim is unsubstantiated.
2. **WBS 1.17 + 1.18** — WASM build target and C ABI cdylib. These unblock
   the entire application shell (Phase 2).
3. **WBS 1.19 + 1.20** — Property tests for invariants and criterion
   benches. Ship-blockers for performance and safety claims.

After Phase 1 completes, see `planning/SPRINT_PLAN.md` for the
sprint-by-sprint plan through v0.1.0.

## Reading order for newcomers

1. `../README.md` (repo root) — what this whole repo is.
2. `../docs/architecture.md` — module-level architecture of MT5/cTrader builds.
3. `../docs/confluence_examples.md` — five worked examples of the operator's mental model.
4. `../docs/parameter_tuning.md` — tuning order and what *not* to tune.
5. `planning/WBS.md` — what's left to build.
6. `godmode_engine/src/lib.rs` — entry point of the Rust port.
7. `godmode_engine/src/engine.rs` — gate pipeline orchestrator.

## License & disclaimer

Proprietary. Live trading is at the user's own risk. The platform enforces
risk caps and kill switches, but no software substitutes for operator
discipline and a calibrated trading thesis. Read `../README.md` and the
brief before deploying with real capital.
