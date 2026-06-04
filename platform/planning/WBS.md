# GODMODE_OFEA Platform — Work Breakdown Structure (WBS)

> Source-of-truth task hierarchy for the unified order-flow trading platform.
> Hand this to Manus AI or any external dev team. Every leaf task has an
> acceptance criterion and a parent epic so progress can be rolled up cleanly.
>
> **Total estimate**: ~22 person-weeks across 4 phases. Assumes one senior
> Rust engineer, one full-stack TS engineer, one Python ML engineer, and a
> shared QA/ops resource. Subtract or stretch proportionally.

## Conventions

- **Effort**: dev-days (1 day = ~6 focused hours).
- **Owner roles**: `RUST` (engine), `TS` (app shell + UI), `ML` (Python sidecar), `OPS` (infra/CI/release), `QA` (test).
- **Acceptance**: must be a checkable artifact (test passes, screenshot, log line, repo file).
- **Status**: 🟢 done, 🟡 in flight, 🔴 not started, ⚪ deferred to later phase.

---

## EPIC 1 — Engine Core (Rust)

| # | Task | Owner | Days | Acceptance | Status |
|---|------|-------|------|------------|--------|
| 1.1 | Cargo workspace scaffold | RUST | 0.5 | `cargo build` clean from `platform/` | 🟢 |
| 1.2 | `common.rs` — enums, GateResult, SetupCandidate, helpers | RUST | 1 | unit tests pass; values mirror MT5/cTrader byte-for-byte | 🟢 |
| 1.3 | `delta.rs` — tick aggregator + CVD + divergence | RUST | 2 | unit tests cover uptick rule + Z-score | 🟢 |
| 1.4 | `profile.rs` — 50-bin VP + D/P/b/THIN classifier | RUST | 2 | recompute matches cTrader on shared 100-bar fixture | 🟢 |
| 1.5 | `footprint.rs` + `stars.rs` — absorption + 5-component score | RUST | 1 | star count matches reference on 50-bar fixture | 🟢 |
| 1.6 | `session.rs` — SAST classifier + sub-tier + blackout | RUST | 1 | classify EVERY minute of one UTC day correctly | 🟢 |
| 1.7 | `htf.rs` — H4 EMA(20) + D1 EMA(50) bias snapshot | RUST | 0.5 | EMA matches reference within 1e-9 | 🟢 |
| 1.8 | `risk.rs` — DD halt + spread guard + consec + sizing + news | RUST | 2 | RiskPct hard-clamp at 2.0 enforced; sizing formula matches §11.8 | 🟢 |
| 1.9 | `trade.rs` — partial/BE/trail/POC actions (intent-only) | RUST | 1 | action stream matches cTrader on 5 scripted scenarios | 🟢 |
| 1.10 | `notify.rs` — N-A..N-L cascade with edge detection | RUST | 1 | each tag fires at most once per bar timestamp | 🟢 |
| 1.11 | `dashboard.rs` — view-model + 250ms throttle | RUST | 0.5 | snapshot serialises to JSON cleanly | 🟢 |
| 1.12 | `setups.rs` — 25 detectors | RUST | 4 | each detector has at least one fixture-positive + fixture-negative test | 🟡 (ported, fixtures pending) |
| 1.13 | `logger.rs` — CSV journal §13 | RUST | 0.5 | header byte-identical to MT5/cTrader builds | 🟢 |
| 1.14 | `engine.rs` — gate pipeline 0..=8 orchestrator | RUST | 3 | smoke replay emits expected gate sequence | 🟢 |
| 1.15 | `replay.rs` + `bin/replay.rs` — CSV-driven CLI | RUST | 1 | `godmode-replay --bars sample.csv` emits ≥1 event/bar | 🟢 |
| 1.16 | Conformance harness — compare to MT5/cTrader exports | RUST + QA | 3 | ≥95% gate-decision agreement on 30-day EURUSD M15 | 🔴 |
| 1.17 | WASM build target + size budget | RUST | 1 | `wasm32-unknown-unknown` builds; binary ≤ 500 KB compressed | 🟢 (683K uncompressed; gzip ~200K) |
| 1.18 | C ABI + cdylib for FFI to TS/Python | RUST | 2 | `gme_engine_new / gme_engine_on_bar / gme_engine_drop` callable; FFI smoke test passes | 🟢 |
| 1.19 | Property tests via `proptest` for invariants | RUST + QA | 2 | RiskPct never exceeds 2.0; CVD slope identity; kill switches always first | 🟢 |
| 1.20 | Bench harness (`criterion`) | RUST | 1 | per-bar pipeline ~3µs; tick ingest ~1.87µs/1000; well under 2ms p99 | 🟢 |

**Phase-1 deliverable**: `cargo test` green, conformance ≥95%, WASM + C ABI builds.

---

## EPIC 2 — Application Shell (Tauri + React)

| # | Task | Owner | Days | Acceptance | Status |
|---|------|-------|------|------------|--------|
| 2.1 | Tauri scaffold (Mac/Win/Linux), React+Vite app | TS | 1 | `tauri dev` launches blank window on all 3 OS | 🔴 |
| 2.2 | IPC bridge: TS ↔ Rust engine (via FFI from 1.18) | TS + RUST | 2 | round-trip tick→gate event in <5ms | 🔴 |
| 2.3 | WebGL chart canvas (lightweight-charts fork) | TS | 5 | render 50k candles at 60 FPS | 🔴 |
| 2.4 | Footprint cell renderer (per-bar bid/ask grid) | TS | 4 | DeepCharts-class footprint visible | 🔴 |
| 2.5 | Volume profile overlay (POC/VAH/VAL/LVN/HVN) | TS | 2 | levels persist across timeframe switches | 🔴 |
| 2.6 | CVD + delta histogram pane | TS | 2 | series scrolls in lockstep with main chart | 🔴 |
| 2.7 | Liquidity heatmap (Bookmap-class) | TS | 7 | resting size heatmap renders 1M data points | 🔴 |
| 2.8 | DOM ladder + one-click trading panel | TS | 4 | place/modify/cancel via UI, observe broker echo | 🔴 |
| 2.9 | Dashboard panel (8-row + dots) | TS | 2 | matches `confluence_examples.md` Example 1 visually | 🔴 |
| 2.10 | Replay scrubber (synced across panels) | TS | 3 | scrub 1 day of M5 data without dropped frames | 🔴 |
| 2.11 | Drawing tools (trendline, fib, rect, text) | TS | 4 | drawings persist per-symbol across sessions | 🔴 |
| 2.12 | Multi-chart layout / tile grid | TS | 3 | drag-resize works; layouts saveable | 🔴 |
| 2.13 | Settings UI (mirrors EngineConfig) | TS | 2 | round-trips engine config JSON | 🔴 |
| 2.14 | Journal viewer (CSV table + filters) | TS | 2 | sort + filter by setup_id, score, R | 🔴 |
| 2.15 | Auto-update channel (Tauri updater) | OPS + TS | 1 | signed update applies on relaunch | 🔴 |
| 2.16 | Telemetry / crash report (optional, opt-in) | OPS | 1 | Sentry/PostHog wired, no-op if disabled | 🔴 |

**Phase-2 deliverable**: usable desktop app on all 3 OS, end-to-end CSV replay → on-screen chart + dashboard + journal.

---

## EPIC 3 — AI / ML Layer (Python sidecar)

| # | Task | Owner | Days | Acceptance | Status |
|---|------|-------|------|------------|--------|
| 3.1 | `pyproject.toml` + sidecar gRPC server skeleton | ML | 1 | `python -m godmode_ml.server` accepts a health-check RPC | 🔴 |
| 3.2 | Setup-quality classifier (XGBoost) | ML | 4 | `predicted_R` returned for every Candidate; AUC >0.65 on holdout | 🔴 |
| 3.3 | Retraining pipeline (rolling-1000-trade window) | ML + OPS | 2 | scheduled cron retrain; model artefacts versioned to S3/GCS | 🔴 |
| 3.4 | LLM copilot (Anthropic SDK + prompt caching) | ML + TS | 3 | "why did gate 4 block?" returns coherent answer using gate history | 🔴 |
| 3.5 | Hard-coded refusal: copilot cannot place orders | ML | 0.5 | unit test asserts refusal across 20 jailbreak prompts | 🔴 |
| 3.6 | Anomaly detector (isolation forest on tick stream) | ML | 3 | flash-crash 2010 fixture triggers anomaly score >0.95 | 🔴 |
| 3.7 | RL parameter tuner (PPO via stable-baselines3) | ML | 5 | 10k-step training shows reward improvement; never recommends RiskPct >2.0 | 🔴 |
| 3.8 | Wire ML hooks into engine via opt-in config flags | RUST + ML | 1 | `M9_MLFilter_Enabled = false` by default; engine works without sidecar | 🔴 |
| 3.9 | Model card + ML_GUIDE.md | ML | 1 | every model has a card listing inputs/outputs/limitations | 🔴 |

**Phase-3 deliverable**: sidecar live, copilot answering operator questions, classifier emitting predictions, RL tuner producing recommendations (not auto-applied).

---

## EPIC 4 — Connectivity (Broker Adapters)

| # | Task | Owner | Days | Acceptance | Status |
|---|------|-------|------|------------|--------|
| 4.1 | Adapter trait definition (subscribe/order/state) | RUST | 1 | trait compiled, mock impl passes contract tests | 🔴 |
| 4.2 | cTrader Open API adapter | RUST | 5 | live tick stream + order placement on a demo account | 🔴 |
| 4.3 | MT5 bridge (ZMQ pipe + helper EA) | RUST + MQL5 | 5 | tick stream from running MT5 → Rust engine; order roundtrip | 🔴 |
| 4.4 | FIX 4.4 adapter (Rithmic/CQG/IBKR) | RUST | 7 | demo session connects, tick + order works | 🔴 |
| 4.5 | Crypto: Binance + Bybit (WebSocket+REST) | RUST | 4 | BTCUSDT live tick stream + market order on Bybit testnet | 🔴 |
| 4.6 | Polygon.io / Databento historical loader | RUST | 2 | back-fill 30 days of EURUSD ticks on first launch | 🔴 |
| 4.7 | Adapter health monitor + reconnect | RUST | 2 | broker disconnect → auto-reconnect within 10s with no engine restart | 🔴 |
| 4.8 | Multi-broker simultaneous connection support | RUST + TS | 3 | run cTrader + Binance simultaneously; unified PnL table | 🔴 |

**Phase-4 deliverable**: trade live on at least cTrader and Binance from one app instance.

---

## EPIC 5 — Documentation & Release

| # | Task | Owner | Days | Acceptance | Status |
|---|------|-------|------|------------|--------|
| 5.1 | `ARCHITECTURE.md` — extends existing `docs/architecture.md` | RUST | 1 | covers WASM, FFI, sidecar wiring | 🟡 (skeleton in place) |
| 5.2 | `OPERATOR_MANUAL.md` — full UI walkthrough | TS + QA | 3 | screenshots for every panel; matches `confluence_examples.md` cascade | 🔴 |
| 5.3 | `ML_GUIDE.md` — model overviews + retrain workflow | ML | 2 | runnable retrain example documented | 🔴 |
| 5.4 | `DEVELOPER_SDK.md` — plugin authoring | RUST + TS | 2 | sample plugin compiles + loads | 🔴 |
| 5.5 | `TESTING.md` extension — Phase 9–12 (latency, multi-broker) | QA | 2 | each phase has runnable test command | 🔴 |
| 5.6 | Code-signed release builds (Mac + Win) | OPS | 2 | first signed release downloadable from GitHub Releases | 🔴 |
| 5.7 | Public landing site + changelog | OPS + TS | 2 | `/releases` page lists v0.1.0 with download links | 🔴 |
| 5.8 | Disclosure + risk page | OPS | 0.5 | clearly states "live trading is at user's own risk" | 🔴 |

---

## Cross-cutting

| Theme | Activities |
|-------|-----------|
| **Security** | dependency audit (`cargo audit`, `npm audit`, `pip-audit`); secret-scanning in CI; signed releases; reproducible builds |
| **Performance** | criterion benches gated in CI; tick→gate latency <2ms p99; chart 60 FPS at 50k candles |
| **Observability** | tracing spans through Rust + TS + Python; OTLP exporter; structured JSON logs |
| **Testing** | unit (per module); integration (per epic); end-to-end replay; conformance vs MT5/cTrader; property; fuzz on tick parser |
| **Release cadence** | weekly internal builds; biweekly external alpha; v0.1.0 = end of Phase 2 |

---

## Out of scope (explicit)

- Mobile app (iOS/Android) — Phase 5 candidate.
- Cloud-hosted multi-tenant offering — Phase 6 candidate.
- Strategy marketplace — Phase 6 candidate.
- Auto-funded prop-firm integration — Phase 7 candidate.

These appear here so they don't sneak in as scope creep mid-build.
