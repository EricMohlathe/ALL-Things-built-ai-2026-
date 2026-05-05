# Dependency Graph

> Critical path through the build. Anything on the critical path that slips
> blocks everything downstream — fund those tasks first. Tasks off the
> critical path can be parallelised across team members.

## Module-level graph (engine + shell)

```
                         common.rs
                         /   |   \
                        /    |    \
                   delta.rs  |  session.rs
                        \    |    /
                    profile.rs  htf.rs
                          \  |  /
                       footprint.rs
                            |
                         stars.rs
                            |
                        setups.rs ─────────┐
                            |              │
                          risk.rs ──────── trade.rs
                            |              │
                        notify.rs ────── dashboard.rs
                            \             /
                             \           /
                            engine.rs (orchestrator)
                                  │
                            ┌─────┼─────┐
                            ▼     ▼     ▼
                       replay.rs  WASM  C ABI
                            │     │     │
                            ▼     ▼     ▼
                          CLI   Web   TS+Py FFI
                                  │
                             ┌────┴────┐
                             ▼         ▼
                        Tauri shell  ML sidecar
                             │         │
                             ▼         ▼
                          Charts     Classifier
                          DOM        Copilot
                          Heatmap    Anomaly
                          Journal    RL tuner
                             │         │
                             └────┬────┘
                                  ▼
                          Broker adapters
                          (cTrader / MT5 /
                           FIX / Crypto)
                                  │
                                  ▼
                            v0.1.0 release
```

## Critical path

The single longest chain of dependencies — slip any node and the release
date moves day-for-day:

`common.rs` → `delta.rs` → `profile.rs` → `setups.rs` → `engine.rs` →
`C ABI / WASM` → `Tauri IPC` → `Chart canvas` → `Footprint renderer` →
`Heatmap` → `cTrader adapter` → `Code-signed release`

**Critical-path effort**: ~60 dev-days. Everything else can run in parallel
if you have the headcount.

## Parallelisable streams

| Stream | Can start when | Members |
|--------|---------------|---------|
| Charting (WBS 2.3–2.7, 2.10) | After 2.1 + 2.2 | TS engineer 1 |
| Trading UI (WBS 2.8, 2.9, 2.13, 2.14) | After 2.1 + 2.2 | TS engineer 2 |
| ML sidecar (WBS 3.1–3.7) | After 1.13 (logger CSV format frozen) | ML engineer |
| Broker adapters (WBS 4.1–4.5) | After 1.18 (C ABI) | RUST engineer 2 |
| Documentation (WBS 5.1–5.8) | Continuous | OPS / QA |

## External dependencies

| Dependency | Risk if blocked | Mitigation |
|------------|-----------------|------------|
| Anthropic API access (Claude Opus 4.7) | Copilot can't ship | Stub copilot with rule-based fallback; ML sidecar still useful for classifier + anomaly + RL |
| cTrader Open API credentials | Live cTrader broken | Build against demo account; flip to live with credential swap |
| Rithmic / CQG / IBKR demo access | FIX adapter delayed | Already deferred to v0.2.0 |
| Mac code-signing certificate | Mac release blocked | Apple Developer enrollment 1–2 weeks; start day 1 |
| Windows code-signing (EV) | Win SmartScreen warnings | EV cert 1–2 weeks; start day 1 |
| Tick data (Polygon/Databento) | Backtest universe limited | Use broker historical bars in v0.1.0; integrate Polygon in v0.2.0 |

## What unblocks what

> Use this section in standups: "I'm blocked on X" → look up X here.

- **Engine WASM build** unblocks: web client replay, browser-based docs.
- **Engine C ABI** unblocks: Tauri IPC, every broker adapter.
- **Logger CSV schema frozen** unblocks: ML classifier training, journal UI,
  retrain pipeline. Don't change the schema after Sprint 2.
- **Conformance harness ≥95%** unblocks: any claim of feature parity with
  MT5/cTrader builds. Until this is green, the brand promise of
  "behaviourally identical" is unsubstantiated.
- **Adapter trait stable** unblocks: parallel adapter development.
- **Tauri IPC stable** unblocks: every UI panel.
- **Charting canvas at 60 FPS** unblocks: heatmap, footprint, replay scrubber.

## Anti-dependencies (things that should NOT block each other)

- **ML sidecar should not block app shell.** Engine works without sidecar;
  shell launches without sidecar. ML is opt-in.
- **Live brokers should not block paper trading.** Replay-only mode is
  always available, even with all adapters offline.
- **Copilot should not block trading.** Copilot is advisory; an outage
  must not prevent order entry.

## Failure modes if dependencies are not respected

- If `setups.rs` is touched after `engine.rs` is shipped, the conformance
  test must re-run end-to-end. Plan for a 1-day re-validation buffer per
  setup-detector change.
- If the logger CSV header changes after Sprint 2, the ML classifier needs
  full retraining and the journal viewer breaks. **Treat the schema as
  versioned.** Bump a version field if you must change it.
- If broker adapters are tightly coupled to engine internals instead of
  the trait, swapping brokers becomes a refactor instead of a config change.
  Hold the line on the adapter contract.
