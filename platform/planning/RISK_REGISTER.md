# Risk Register

> Every project ships with risks. The unforgivable mistake is pretending
> they don't exist. This register is reviewed at every sprint retro.
>
> **Severity** = (probability × impact). 1 = trivial, 5 = ship-blocker.

| Severity legend | |
|------------------|--|
| 5 — Critical | Will likely block release; immediate mitigation required. |
| 4 — High     | Likely to cause significant slippage; mitigation in next sprint. |
| 3 — Medium   | Manageable; plan a mitigation for the relevant phase. |
| 2 — Low      | Worth tracking; revisit at phase boundaries. |
| 1 — Trivial  | Note it; no active mitigation. |

---

## R-01 — Conformance test fails ≥95% threshold

- **Severity**: 5
- **Probability**: Medium
- **Impact**: Critical — invalidates the "behaviourally identical" claim across MT5/cTrader/Rust.
- **Symptoms**: gate decisions diverge on edge cases (rounding, tick aggressor classification, EMA seeding).
- **Mitigation**:
  1. Run conformance daily once Sprint 3 lands; fail CI on regression.
  2. Track per-gate divergence rate; investigate any gate >5%.
  3. When divergence is found, write a fixture test capturing the disagreement before patching, so it cannot regress silently.
- **Owner**: RUST + QA
- **Trigger**: any conformance run below 95%.

## R-02 — RiskPct soft-clamp bypass via plugin or ML

- **Severity**: 5
- **Probability**: Low
- **Impact**: Critical — violates brief §12 rule 2; possible account-blowing trade.
- **Mitigation**:
  1. Hard-code clamp in `RiskManager::new`. Already done. ✅
  2. Property test: assert `risk.risk_pct <= 2.0` after construction with 1000 random inputs.
  3. RL action space must mask out invalid parameter sets at ingestion time.
- **Owner**: RUST
- **Trigger**: any code path that mutates `risk_pct` after construction.

## R-03 — Broker disconnect during open position

- **Severity**: 4
- **Probability**: High
- **Impact**: Cannot manage an open trade — partials/BE/trail stop firing.
- **Mitigation**:
  1. Server-side SL/TP placed at order entry (not client-managed).
  2. Adapter health monitor with 10s reconnect loop.
  3. Alert via N-L `KILL_SWITCH("BROKER_DISCONNECT")` if reconnect fails for >30s.
- **Owner**: RUST (adapters)
- **Trigger**: WBS 4.7 acceptance test must include simulated disconnect.

## R-04 — Footprint / heatmap rendering perf collapse

- **Severity**: 4
- **Probability**: Medium
- **Impact**: 60 FPS target missed; users perceive app as sluggish; competitors look better.
- **Mitigation**:
  1. WebGL shader-based renderer from day 1 (not Canvas2D).
  2. Aggressive culling — only render visible viewport tiles.
  3. Bench in CI with 1M-tick fixtures; fail PR if FPS drops below 45.
- **Owner**: TS
- **Trigger**: WBS 2.4, 2.7 — any commit touching renderer.

## R-05 — Mac/Windows code-signing delays

- **Severity**: 4
- **Probability**: Medium
- **Impact**: Release blocked; SmartScreen warns Windows users; Mac users see Gatekeeper block.
- **Mitigation**:
  1. Start Apple Developer + EV cert procurement on day 1, not Sprint 12.
  2. Self-signed builds in alpha while waiting; clear "Unsigned" banner.
  3. Notarisation script in CI; fail builds that aren't notarised.
- **Owner**: OPS
- **Trigger**: Sprint 12 release prep.

## R-06 — Anthropic API outage during demo

- **Severity**: 3
- **Probability**: Low
- **Impact**: Copilot dead; investor demo embarrassing.
- **Mitigation**:
  1. Cached recent responses in copilot.
  2. Fallback rule-based "explain why" for top-10 gate-fail reasons.
  3. Status check before demo; if API is degraded, swap to fallback automatically.
- **Owner**: ML
- **Trigger**: any LLM-dependent feature in Sprint 10+.

## R-07 — ML model drift breaks setup-quality classifier

- **Severity**: 3
- **Probability**: High
- **Impact**: Predicted R diverges from actual; users lose trust.
- **Mitigation**:
  1. Rolling 1000-trade retrain window.
  2. Track holdout AUC weekly; alert if drops below 0.60.
  3. UI displays model version + last-retrain date; users can disable.
- **Owner**: ML
- **Trigger**: AUC dashboard alert.

## R-08 — Tauri ecosystem regression

- **Severity**: 3
- **Probability**: Low
- **Impact**: Forced Electron migration mid-build; weeks of rework.
- **Mitigation**:
  1. Pin Tauri version in `Cargo.toml`.
  2. Maintain a thin abstraction over Tauri APIs so the door stays open to Electron.
  3. Subscribe to Tauri release notes; review breaking changes per minor version.
- **Owner**: TS
- **Trigger**: Tauri major version release.

## R-09 — Regulatory exposure (live trading without disclaimers)

- **Severity**: 5
- **Probability**: Medium
- **Impact**: Legal liability; product takedown.
- **Mitigation**:
  1. Hard-coded "Risk disclosure accepted" gate before live trading is enabled.
  2. `MODE_MANUAL` is default for first 30 days; AUTO requires explicit opt-in dialog.
  3. Risk disclosure page in app + on landing site.
  4. Get legal review before any public release.
- **Owner**: OPS + (external legal)
- **Trigger**: pre-release checklist Sprint 12.

## R-10 — Open-source license incompatibility

- **Severity**: 3
- **Probability**: Low
- **Impact**: Cannot ship a commercial binary without untangling deps.
- **Mitigation**:
  1. `cargo deny` in CI with allowlist (MIT/Apache-2/BSD only).
  2. `npm` license check via `license-checker`.
  3. Avoid GPL/AGPL libraries.
- **Owner**: OPS
- **Trigger**: any new dependency added.

## R-11 — Order-placement bug in adapter (over-sized order)

- **Severity**: 5
- **Probability**: Low
- **Impact**: Real money loss; broker may freeze account.
- **Mitigation**:
  1. Two-layer volume sanity check: engine clamps, adapter re-clamps.
  2. Pre-trade dry-run validation against broker symbol metadata.
  3. AUTO mode default-disabled; user must opt in per session.
  4. Demo account testing for every adapter before live cert.
- **Owner**: RUST (adapters)
- **Trigger**: every adapter PR.

## R-12 — Copilot prompt-injection bypasses refusal

- **Severity**: 4
- **Probability**: Medium
- **Impact**: Operator believes copilot placed a trade when it didn't (or worse, an injected prompt leaks data).
- **Mitigation**:
  1. Hard-coded refusal in system prompt + post-response classifier.
  2. Copilot has no broker tools — physically cannot place orders.
  3. Red-team test of 100 jailbreak prompts in CI.
- **Owner**: ML
- **Trigger**: Sprint 10 acceptance.

## R-13 — Personal injury risk: solo dev burnout

- **Severity**: 4
- **Probability**: High (small team)
- **Impact**: Hidden until it happens; very expensive to recover from.
- **Mitigation**:
  1. Hard-stop at 8h/day; 5 days/week.
  2. No solo-on-call. If you can't pair, you can't ship.
  3. WIP limit of 2 tasks per engineer.
- **Owner**: All
- **Trigger**: any engineer working >50h in a week → mandatory rest week.

## R-14 — Scope creep from "just one more feature"

- **Severity**: 3
- **Probability**: High
- **Impact**: 22-week plan becomes 30 weeks.
- **Mitigation**:
  1. WBS.md + SPRINT_PLAN.md are the contract. New work goes to backlog.
  2. Demos show working software only; no slide promises.
  3. "Out of scope" list at end of WBS.md is read aloud at every sprint planning.
- **Owner**: All
- **Trigger**: any "while we're at it…" in code review.

## R-15 — Conformance test passes but trades behave differently in live conditions

- **Severity**: 4
- **Probability**: Medium
- **Impact**: 95% gate agreement on replay but real money slips, partial fills, broker quirks bite.
- **Mitigation**:
  1. Forward-test on demo for 2 weeks before live (TESTING.md Phase 5).
  2. Slippage model in replay; conformance run with non-zero slippage.
  3. Compare live PnL to replay PnL for first 30 trades; alert on >10% deviation.
- **Owner**: RUST + QA
- **Trigger**: first 30 live trades — manual review of every divergence.

---

## Top-3 ranked by severity × probability

1. **R-01** — Conformance failure. Run the test daily. (5 × Medium)
2. **R-09** — Regulatory exposure. Get legal review before public alpha. (5 × Medium)
3. **R-11** — Adapter over-sizing. Two-layer clamp + dry-run validation. (5 × Low, but catastrophic if it lands)

## Lowest-effort mitigations to apply this week

- ✅ Already done: RiskPct hard-clamp (R-02), MODE_MANUAL default (R-09 partial).
- 🔴 To do: pin Tauri version (R-08); add `cargo deny` to CI (R-10); start code-signing cert procurement (R-05).

## Re-review schedule

- **Every sprint retro**: top 3 risks revisited.
- **End of phase**: full register reviewed; new risks added.
- **Pre-release**: full register reviewed and signed off by all owners.
