# Planning Artifacts (Option D)

This directory is the planning bundle for the unified order-flow trading
platform. It is intended for handoff to Manus AI or any external dev team
that needs to take this project from scaffold to v0.1.0.

## Contents

| Document | Purpose | Audience |
|----------|---------|----------|
| [`WBS.md`](./WBS.md) | Full work-breakdown structure: 5 epics, ~60 leaf tasks with effort estimates and acceptance criteria. | PMs, leads, Manus |
| [`SPRINT_PLAN.md`](./SPRINT_PLAN.md) | 12 two-week sprints across 22 weeks, with definition-of-done and slow-down rules. | Engineering team |
| [`DEPENDENCY_GRAPH.md`](./DEPENDENCY_GRAPH.md) | Module-level and stream-level critical path; what unblocks what. | Engineers + PMs |
| [`RISK_REGISTER.md`](./RISK_REGISTER.md) | 15 enumerated risks with severity, mitigation, owner, trigger. | Leads + ops + legal |

## How to use

1. Read `WBS.md` first to understand the scope.
2. Read `SPRINT_PLAN.md` to see how the scope unfolds across calendar time.
3. Read `DEPENDENCY_GRAPH.md` to identify the critical path your team
   protects above all else.
4. Read `RISK_REGISTER.md` and pick the three risks that most threaten
   your context — start mitigations on Day 1.

Then read `../../README.md` (repository root) and the existing
`docs/architecture.md`, `docs/confluence_examples.md`, and
`docs/parameter_tuning.md` to understand the trading domain. Only after
that, open the source in `mt5/` and `ctrader/` (the existing builds) and
`platform/godmode_engine/` (the Rust port now scaffolded).

## What's already done

Phase 1 of WBS.md is mostly complete — the engine core is ported, compiles
clean, and ships with 12 passing tests + a working CLI replay tool. See
[../godmode_engine/](../godmode_engine/) for source.

What remains in Phase 1: conformance harness vs MT5/cTrader (WBS 1.16),
property tests (1.19), criterion benches (1.20), WASM target (1.17),
C ABI cdylib (1.18). These unblock the application shell.

## What this is not

- This is not a substitute for the brief or the source-authority compendium.
  Every algorithm in the build traces back to those documents. This bundle
  describes how to *deliver* the platform; the brief describes what the
  platform must *do*.

- This is not a marketing document. There are no projected returns, no
  user counts, no "10x productivity" claims. If you want those, pair this
  with a separate go-to-market plan.

- This is not a substitute for legal review. Risk **R-09** explicitly
  flags regulatory exposure as a critical pre-release item. Get legal
  review before any public alpha.
