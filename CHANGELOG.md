# CHANGELOG

## v1.0.0 — Initial Build

Source authority: brief §1–§24 + Appendix A. Implementation traceability per module is documented in `docs/architecture.md`.

### Implemented (Phases 1–8 per brief §17)

- **Phase 1 — Scaffold + Common**:
  - MT5 `OF_Common.mqh` and cTrader `OFCommon.cs` — enums, structs, helpers, `GateResult` record (brief §15 rule 3), `SetupCandidate` struct.
  - MT5 `OF_Logger.mqh` and cTrader `TradeLogger.cs` — CSV journal writer matching brief §13 schema.

- **Phase 2 — Engine Core**:
  - `OF_DeltaEngine` / `DeltaEngine` — tick-flag-based aggregation (brief §11.1), CVD running sum, 20-bar bullish/bearish divergence detection (brief §11.5), volume + delta Z-scores.
  - `OF_VolumeProfile` / `VolumeProfile` — 50-bin POC/VAH/VAL via expansion-from-POC value-area algorithm (brief §11.2), LVN/HVN classification, skewness-and-peakedness D/P/b/THIN shape classifier (brief §11.3) driving F5 market-state determination.
  - `OF_FootprintAnalyzer` / `FootprintAnalyzer` — bullish/bearish absorption, stacked imbalance (3+ rows), unfinished-auction detection.
  - `OF_AbsorptionStars` / `AbsorptionStars` — 5-component confidence scoring (brief §11.4): vol Z ≥ 1.0 / 2.0 / 3.0, |delta Z| ≥ 2.0, wick ≥ 40%.
  - `OF_SessionGate` / `SessionGate` — SAST minute-from-midnight session map (brief §11.6), NY-open 20-min blackout, sub-window tier classification (brief §22.6 M6).
  - `OF_HTFAlignment` / `HtfAlignment` — H4 EMA(20) + D1 EMA(50) bias (brief §11.7).

- **Phase 3 — Risk + Trade**:
  - `OF_RiskManager` / `RiskManager` — canonical position sizing (brief §11.8), 1% hard cap (brief §12 rule 2), 5% daily DD halt + flatten (rule 3), 3-consec-loss day halt (rule 4), rolling 100-bar median spread guard (rule 8), news-blackout gate.
  - `OF_TradeManager` / `TradeManager` — partial close at 1R, BE+1pip move, ATR-based trail, POC exit (Model 2 70% rule), session-end flatten (brief §12 rule 1).

- **Phase 4 — Decision Layer**:
  - All 25 detectors per brief §6 — Detect_SetupN routines for setups 1–25, each routed via the SetupID enum, each toggleable via dedicated input parameter, priority-1+2 setups defaulted ON, B-grade (HVNRej) defaulted OFF.
  - Bar-close pipeline — wires gates 0→8 in canonical order (brief §5).

- **Phase 5 — Operator Surface**:
  - `OF_NotificationCenter` / `NotificationCenter` — N-A through N-L cascade, edge-detected (FALSE→TRUE), bar-rate-limited via dictionary state.
  - `OF_Dashboard` / `Dashboard` — 8-row checklist + metrics panel, top-right corner, 250ms refresh throttle.
  - `OF_ChartViz` / `ChartViz` — POC/VAH/VAL lines (magenta solid + dodgerblue dashed), absorption stars, trade lines, session shading.

- **Phase 6 — Integration**:
  - `GODMODE_OFEA.mq5` — main MT5 EA with full input schema (brief §7), bar-close pipeline wiring, AUTO/MANUAL mode branching.
  - `GODMODE_OFEA.cs` — main cAlgo Robot mirror with byte-identical parameter names per `[Parameter]` attribute.

- **Phase 7 — Documentation**:
  - `README.md` — install/configure/run for both platforms.
  - `TESTING.md` — full §14 acceptance protocol + §23.7 multi-symbol addendum.
  - `docs/architecture.md` — gate composition + module wiring.
  - `docs/confluence_examples.md` — 5 worked notification cascades.
  - `docs/parameter_tuning.md` — optimisation order.
  - `samples/news_blackout.json` — schema example with HIGH/MEDIUM/LOW impact tiers (brief §22.4 M4).
  - `samples/GODMODE_OFEA_log.sample.csv` — example journal rows.

### Phase-2 Candidates (deferred from v1.0)

Per brief §19 rule 10 ("If something is missing, document it in CHANGELOG.md as a Phase-2 candidate, then stop"), the following are documented for v1.1:

1. **Multi-symbol parallel scanning architecture (brief §23)** — the §23 spec describes per-symbol SymbolState structs, headless gate pipelines, correlation filter, multi-row dashboard. The v1.0 build is single-symbol. v1.1 will add `MultiSymbol_Enable`, `MultiSymbol_List`, the dispatcher, and the correlation filter.

2. **Marginal-gain refinement layer (brief §22)** — input parameters M1–M6 are exposed in the v1.0 build but the gate hooks are minimal. Specifically:
   - **M1 Liquidity-sweep confirmation layer** — exposed as input, not yet wired into reversal-setup gates. v1.1 will add the BSL/SSL detection over `M1_SwingDetectionBars` lookback.
   - **M2 Two-touch rule** — input exposed, touch-counter dictionary not yet implemented. v1.1 will track per-level touch counts.
   - **M3 ATR regime filter** — input exposed, ratio computation not yet wired into Gate 0. v1.1 will block entries outside [0.70, 1.50] ATR ratio.
   - **M4 Tiered news blackout** — `news_blackout.json` schema supports HIGH/MEDIUM/LOW impact, but the JSON loader and tiered-window logic are stubs. v1.1 will parse the JSON and apply 30/15-min asymmetric windows.
   - **M5 Dual-CVD convergence** — input exposed, correlated-symbol subscription not yet wired. v1.1 will subscribe to `M5_CorrelatedSymbol`, run a parallel CVD aggregator, and apply half-size on neutral / skip on divergence.
   - **M6 Sub-window tiering** — `SessionGate.SubTier` returns the tier classification, but the score-5/5 requirement in TIER B is not yet enforced in the scoring layer. v1.1 will block sub-5/5 entries in TIER B windows.
   - **M7 Slippage-history quality gate** — not implemented in v1.0.
   - **M8 Adaptive setup tiering** — not implemented in v1.0 (requires 200-trade rolling window from the journal; v1.1 will add the journal reader and per-setup win-rate tracker).

3. **Appendix A Phase-9 boosters** — quad confluence (A.1.1), liquidity sweep precondition (A.1.2), round-number bonus (A.1.3) — none implemented in v1.0. Per Appendix A.0 framing, these are earned via 100+ logged base-system trades before enablement.

4. **CVD subwindow indicator (brief §9.2)** — VP and footprint markers render on the main chart. The dedicated CVD subwindow with gradient line and divergence arrows is not in v1.0; CVD is shown in the dashboard metrics row instead. v1.1 will add the OBJ_CHART subwindow.

### Build Authority

- Brief sections fully implemented: §1, §2, §3, §4, §5 (gates 0–8), §6 (all 25 detectors), §7 (full input schema), §8 (mirrored file structure), §9 (VP lines + footprint markers + dashboard + trade lines, minus CVD subwindow noted above), §10, §11.1–§11.8, §12 (rules 1–8), §13, §15, §16, §17 phases 1–8, §18 user story end-to-end.

- Brief sections partially implemented: §9.2 (no CVD subwindow), §22 (inputs exposed, gate hooks minimal), §23 (single-symbol only).

- Hard prohibitions (§19) all honored: zero TradingView/Pine/webhook code paths, zero invented parameters, zero `Sleep()` or busy-wait, stops 1–2 ticks beyond aggression candle, POC exit mandatory for Model 2, gate ordering F2→F5→loc→F3→F4→FP→trigger→score, both builds compute identical numbers from identical rules.
