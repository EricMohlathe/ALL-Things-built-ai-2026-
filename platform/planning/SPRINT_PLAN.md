# Sprint Plan — 22 weeks to v0.1.0

> Two-week sprints. Each sprint has a single, demo-able goal. If you can't
> demo it on Friday of week N+1, the sprint failed and you owe the next
> sprint a retro before adding scope.

## Cadence

- **Sprint length**: 10 working days.
- **Planning**: Monday week 1, ≤2h, locked at end of meeting.
- **Mid-sprint check**: Wednesday week 1, 30 min, can drop scope but not add.
- **Demo**: Friday week 2, 1h, working software only — no slides.
- **Retro**: Friday week 2 immediately after demo, 30 min.

## Definition of Done

A task is "done" when:
1. Code merged to `main` behind a feature flag if user-facing.
2. Tests added (unit + integration as appropriate) and green in CI.
3. Documentation updated in the same PR.
4. Acceptance criterion in WBS.md met and ticked.

If any one of these is missing, the task is in-progress, not done.

---

## Phase 1 — Engine Core (weeks 1–6)

### Sprint 1 (weeks 1–2) — "Skeleton compiles"
- [x] WBS 1.1 Workspace scaffold
- [x] WBS 1.2 `common.rs`
- [x] WBS 1.3 `delta.rs`
- [x] WBS 1.6 `session.rs`
- [x] WBS 1.7 `htf.rs`
- **Demo**: `cargo test` green; `godmode-replay` runs on a 20-bar fixture.

### Sprint 2 (weeks 3–4) — "Profile + Footprint"
- [x] WBS 1.4 `profile.rs`
- [x] WBS 1.5 `footprint.rs` + `stars.rs`
- [x] WBS 1.8 `risk.rs`
- [x] WBS 1.9 `trade.rs`
- [x] WBS 1.10 `notify.rs`
- [x] WBS 1.11 `dashboard.rs`
- **Demo**: replay shows full N-A..N-L cascade firing on EURUSD M15 fixture.

### Sprint 3 (weeks 5–6) — "Pipeline + conformance"
- [x] WBS 1.12 25 detectors (logic ported)
- [x] WBS 1.14 `engine.rs`
- [x] WBS 1.15 CLI replay
- [ ] WBS 1.16 conformance harness vs MT5/cTrader
- [ ] WBS 1.19 property tests for invariants
- [ ] WBS 1.20 criterion benches
- **Demo**: ≥95% gate-decision agreement vs cTrader on 30-day EURUSD M15
  replay; tick→gate latency <2ms p99.

### Sprint 4 (week 6 buffer / WASM + FFI prep)
- [ ] WBS 1.17 WASM build
- [ ] WBS 1.18 C ABI cdylib
- **Demo**: `engine.wasm` loaded in a browser console; `node` invokes
  `engine_create()` via N-API.

---

## Phase 2 — Application Shell (weeks 7–14)

### Sprint 5 (weeks 7–8) — "Tauri shell + IPC"
- [ ] WBS 2.1 Tauri scaffold
- [ ] WBS 2.2 IPC bridge to engine
- [ ] WBS 2.13 settings UI (config round-trip)
- **Demo**: launch app on Mac+Win, change RiskPct in UI, see engine reflect it.

### Sprint 6 (weeks 9–10) — "Charts I — candles + VP"
- [ ] WBS 2.3 WebGL chart canvas
- [ ] WBS 2.5 Volume profile overlay
- [ ] WBS 2.9 Dashboard panel
- **Demo**: live EURUSD chart with POC/VAH/VAL lines + 8-row dashboard.

### Sprint 7 (weeks 11–12) — "Charts II — footprint + CVD"
- [ ] WBS 2.4 Footprint cell renderer
- [ ] WBS 2.6 CVD + delta histogram
- [ ] WBS 2.10 Replay scrubber
- **Demo**: scrub one trading day; footprint and CVD update in lockstep.

### Sprint 8 (weeks 13–14) — "Heatmap + DOM + journal"
- [ ] WBS 2.7 Liquidity heatmap
- [ ] WBS 2.8 DOM ladder + one-click trading
- [ ] WBS 2.14 Journal viewer
- [ ] WBS 2.11 Drawing tools (basic)
- [ ] WBS 2.12 Multi-chart layout
- **Demo**: full trading workspace — chart + footprint + heatmap + DOM
  + dashboard + journal — all synced.

**End of Phase 2 = v0.1.0-alpha**: usable app, paper-trade only.

---

## Phase 3 — AI/ML Layer (weeks 15–18)

### Sprint 9 (weeks 15–16) — "Sidecar + classifier"
- [ ] WBS 3.1 Sidecar gRPC server
- [ ] WBS 3.2 XGBoost setup-quality classifier
- [ ] WBS 3.3 Retrain pipeline
- [ ] WBS 3.8 Engine ML hook (opt-in)
- **Demo**: classifier emits `predicted_R` for every candidate; AUC >0.65.

### Sprint 10 (weeks 17–18) — "Copilot + anomaly + RL"
- [ ] WBS 3.4 LLM copilot
- [ ] WBS 3.5 Order-placement refusal
- [ ] WBS 3.6 Anomaly detector
- [ ] WBS 3.7 RL parameter tuner
- [ ] WBS 3.9 Model card + ML_GUIDE.md
- **Demo**: copilot answers "why did gate 4 block?" with gate history;
  RL recommends a parameter set and reports expected expectancy lift.

---

## Phase 4 — Connectivity + Release (weeks 19–22)

### Sprint 11 (weeks 19–20) — "Brokers I"
- [ ] WBS 4.1 Adapter trait
- [ ] WBS 4.2 cTrader Open API
- [ ] WBS 4.3 MT5 bridge
- [ ] WBS 4.7 Health monitor + reconnect
- **Demo**: live tick stream + order roundtrip on cTrader demo and MT5.

### Sprint 12 (weeks 21–22) — "Brokers II + release"
- [ ] WBS 4.5 Crypto (Binance + Bybit)
- [ ] WBS 4.8 Multi-broker simultaneous
- [ ] WBS 5.2 Operator manual
- [ ] WBS 5.6 Code-signed release
- [ ] WBS 5.7 Landing + changelog
- [ ] WBS 5.8 Risk disclosure
- **Demo**: signed v0.1.0 download; new user installs, paper-trades, journals.

**End of Phase 4 = v0.1.0**: public alpha.

FIX 4.4 (WBS 4.4) and Polygon/Databento (WBS 4.6) slip to v0.2.0 unless
team capacity allows them in Sprint 12 buffer.

---

## Burn-down assumptions

| Sprint | Planned dev-days | Cumulative | % of WBS effort |
|--------|------------------|------------|-----------------|
| 1 | 5 | 5 | 5% |
| 2 | 6 | 11 | 11% |
| 3 | 7 | 18 | 18% |
| 4 | 4 | 22 | 22% |
| 5 | 5 | 27 | 27% |
| 6 | 9 | 36 | 36% |
| 7 | 11 | 47 | 47% |
| 8 | 16 | 63 | 63% |
| 9 | 8 | 71 | 71% |
| 10 | 12 | 83 | 83% |
| 11 | 13 | 96 | 96% |
| 12 | 10 | 106 | 106% |

The 6% overrun is the buffer. It will be consumed by hardening, perf
work, and scope cleanup. Don't pre-spend it.

---

## How to slow down responsibly

If a sprint slips, drop in this order before extending:

1. **First**: drop polish (animations, theme variants, fancy charting controls).
2. **Second**: drop optional broker adapters (FIX, Polygon).
3. **Third**: defer mobile/cloud work — already out of scope, keep it that way.
4. **Last resort**: defer ML features, BUT never disable the hard
   constraints in `EngineConfig`. Ship without ML. Never ship without DD halt.

What you don't drop:

- Conformance test (Sprint 3).
- Order-placement refusal in copilot (Sprint 10).
- Hard risk caps and gate ordering — non-negotiable per brief §19.
