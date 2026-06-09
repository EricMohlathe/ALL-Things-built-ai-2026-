# Audit Pass 4 — full-repo god-level review

Four-agent parallel sweep over the four language stacks. Each agent owned one folder, fixed bugs + added safety hardening + did light behaviour-preserving refactors, then reported back.

| Area | Lane | Status |
|------|------|--------|
| MQL5 | `MT5_Unified/` (2 EAs, 7 indicators, 38 .mqh) | 9 bugs + 6 hardening + 7 recommendations |
| C# (cAlgo) | `ctrader/` + `Enhanced/cTrader/` (1 cBot + 20 modules + Enhanced) | 9 bugs + 8 hardening + parity fixes |
| Pine | `tradingview/` + `Enhanced/TradingView/` (16 files) | 6 bugs + 2 hardening + 6 recommendations |
| Rust + JS | `platform/godmode_engine/` + viewer | 6 fixes + 5 hardening; `cargo test` 17/17 green |

Build status after pass 4:
- **MT5:** before this pass the Enhanced EA + all 7 indicators **did not compile**. After: should compile clean in MetaEditor.
- **cTrader:** should build under Automate. `AccessRights.FullAccess` triggers a one-time grant prompt on first install.
- **TradingView:** all 16 Pine files should compile in Pine Editor on `//@version=6`.
- **Rust:** `cargo check` clean, `cargo clippy -D warnings` clean, `cargo test` 17/17.

---

## MQL5 — `MT5_Unified/`

### Bugs fixed

| File:line | Defect | Severity |
|---|---|---|
| `Experts/GODMODE_OFEA_Enhanced/GODMODE_OFEA_Enhanced.mq5:42,126` | `ENUM_OP_MODE`/`MODE_MANUAL`/`MODE_AUTO` undefined; replaced with `ENUM_OPMODE`/`OPMODE_*` from `OF_Common.mqh` | **Hard compile error** |
| `Indicators/GODMODE/*.mq5` (all 7) | Broken include paths `"../Include/..."` — regression from the consolidation move; corrected to `"../../Include/..."` | **Hard compile error** |
| `Indicators/GODMODE/GODMODE_SessionLight.mq5:27` | `Paint(NULL,0,NULL,NULL)` passed NULL to typed-array references (illegal in MQL5); refactored to no-args | **Hard compile error** |
| `Include/OF_Common.mqh:196-225` | `ATR()` leaked a fresh `iATR` handle on every call; replaced with 16-slot `(sym\|tf\|period)` cache + `OF_AtrCacheRelease()` for `OnDeinit` | **Critical — drained MT5 handle pool within hours** |
| `Include/OF_HTFAlignment.mqh:34-54` | F3 HTF bias read EMA + close at index 0 (forming bar) → repaint between ticks; switched to index 1 + `BarsCalculated()` + NaN guards | **Critical — gate flapped intra-bar** |
| `Indicators/GODMODE/GODMODE_ConfluenceDashboard.mq5:100-112` | Used `time[0]` (OLDEST, stable) as new-bar key, so per-bar updates fired once at attach then never again; switched to `time[rates_total-2]` (last closed) | **Critical — indicator was effectively static** |
| `Indicators/GODMODE/GODMODE_DeltaBars.mq5:46-58` + `GODMODE_VWAP.mq5:49-62` | `start = prev_calculated - 1` re-ran forming bar on every tick → CVD/VWAP re-accumulated thousands of times per bar; now advance model only on confirmed bars | **Critical — drew wrong values** |
| `Indicators/GODMODE/GODMODE_PriceActionLabels.mq5:38-50` | Same forming-bar issue + unchecked `CopyHigh/Low/Close`; switched to closed-bar index + size guards | High |
| `Include/OF_TradeManager.mqh:112-117` | `curSl == 0` exact-double comparison; broker FP normalisation can return non-zero "unset" SLs; replaced with `< _Point` epsilon | Medium |

### Hardening added

- `OF_Common.mqh` — `BarsCalculated()` + `MathIsValidNumber()` guards on ATR; rejects negatives before they propagate into `Detect_Setup25_Iceberg` and `Trail`.
- `OF_VolumeProfile.mqh:141-160` — `LocationAt` guards `m_binSize<=0`, `m_bins<=0`, POC/VAH/VAL=0 (Recompute failure mode) so F1.A gate doesn't spuriously match LOC_POC at price 0.
- `OF_SweepDetector.mqh` + `OF_PriceAction.mqh` + `OF_DeltaEnhanced.mqh` — default constructors zero-init state structs so composite probability doesn't read uninitialised fields on first tick.
- `GODMODE_HTFStrength.mq5` — fail-fast on any `INVALID_HANDLE`; per-row `BarsCalculated` + `CopyBuffer` + NaN guards in Render.
- `GODMODE_OFEA_Enhanced.mq5 OnBarClose` — `CopyHigh/Low/Close` return-value checks; abort the bar rather than feed undersized arrays into `g_pa.Update`.
- Both EAs `OnDeinit` — call `OF_AtrCacheRelease()` so optimisation sweeps don't accumulate leaked handles.

### Recommendations not actioned

1. `OF_DeltaEngine::OnBarClose` does O(N) array shifts every bar across three arrays. Convert to a ring buffer (matches `OF_DeltaEnhanced`'s layout).
2. `OF_RiskManager::SampleSpread` sorts a 100-element array each bar for median. Use a maintained-order structure.
3. `CDeltaEngine::Divergence*` walks 20 bars via `iLow`/`iHigh` per call; cache the swing extreme alongside rolling CVD min/max.
4. `OF_BookmapBridge.mqh::JsonGet` is a brittle inline parser; nested objects or escaped quotes silently misparse.
5. `OF_GoogleSheetsLevels.mqh` not audited line-by-line — operator-facing, flagged for next pass.
6. `HandleDayRollover` uses `TimeCurrent` (broker server day); add a `BrokerTimezoneOffset` input for US brokers.
7. Add `BarsCalculated(_Symbol, _Period) >= length` precondition at top of every `RunBarClose()` for first-tick insurance.

---

## C# (cAlgo) — `ctrader/` + `Enhanced/cTrader/`

### Bugs fixed

| File:line | Defect | Severity |
|---|---|---|
| `Modules/DeltaEngine.cs:50-72` | Tick-aggressor classifier compared `args.Ask > args.Bid` — always true. `_tickSell` never accumulated; CVD had no real sign. Replaced with mid-tick uptick/downtick. | **Critical — entire CVD signal was broken** |
| `Modules/HTFAlignment.cs:26-41` | H4/D1 bias read `Last(0)` (forming bar) → mid-bar flap. Now reads `Last(1)` with `Count<2` + NaN/EMA-zero guards. | **Critical — same forming-bar flap as MT5** |
| `Modules/SetupDetectors.cs:248-252` | `Iceberg` fell through to SHORT for any non-VAL/LVN loc (including POC). Now returns null outside Val/Lvn/Vah/Hvn. | High |
| `Modules/SetupDetectors.cs:188-197` | `SmtDiv` with `corrCvdSlope==0` (M5 off) silently passed sign-product test. Now returns null on zero. | High |
| `Modules/TradeManager.cs:72-99` | BE-modify called every tick even when SL already at BE → log flood + broker throttle. Added idempotency check. | High |
| `Modules/TradeManager.cs:67-71` | Partial-close used `Comment.Contains("[P]")` flag never set, so partial fired every tick after threshold. Switched to a `HashSet<long> _partialDone` keyed on Position.Id. | **Critical — repeated partials** |
| `Modules/TradeManager.cs:38-72` | `OpenPosition` had no failure log, no inverted-SL/TP guard, no min-volume check. Added all three. | High |
| `GODMODE_OFEA.cs:206+` | `MaxRR` parameter declared but never read; `_consecLosses` never incremented because `Positions.Closed` was never wired. Added `OnPositionClosedHook`, wired in lifecycle, now caps RR at `MaxRR`. | **Critical — daily loss circuit-breaker disabled** |

### Hardening added

- `Modules/VolumeProfile.cs:122` — `LocationAt` guards `_binSize<=0` and NaN price.
- `Modules/RiskManager.cs:51-67` — `SampleSpread` rejects non-positive/NaN/Inf; even-n median fixed to mean-of-middles.
- `Modules/RiskManager.cs:97-115` — `ComputeVolume` guards equity/pct/pip/NaN; rejects sub-`VolumeInUnitsMin` results so broker doesn't reject the order downstream.
- `Modules/GoogleSheetsLevels.cs:124-167` — strips UTF-8 BOM, falls back to bare-comma split when gviz quoted form absent, trims residual quotes, rejects NaN/Inf prices.
- `Modules/NotificationCenter.cs:38-44` — push routed through `SendMobileNotification` (cTrader mobile) not `SendEmail`; email path now gated behind `_email`.
- `Modules/Dashboard.cs:57-58` — wired previously-unused `_fail` colour to DD<0 condition.
- `Modules/PoolResilience.cs` — `Exploitable` no longer flips on zero-consumption (false positives on quiet markets).
- `GODMODE_OFEA.cs:28` — `[Robot]` declaration upgraded to `AccessRights = AccessRights.FullAccess` so HttpClient (GoogleSheetsLevels), file bridges, and email notifications actually run.

### MT5-parity drift fixed

Added to cTrader base build (now mirrors `MT5_Unified/Experts/GODMODE_OFEA/GODMODE_OFEA.mq5`):
`M1_SweepLookbackBars=10`, `M2_TouchLookbackBars=30`, `M2_TouchTolPips=3.0`, `M3_MinATRRatio=0.70`, `M3_MaxATRRatio=1.50`, `M5_HalfSizeOnNeutral=true`.

Added to Enhanced cTrader (mirrors `GODMODE_OFEA_Enhanced.mq5`):
`UseEnhancedGates=true` (now actually gates `ComputeCompositeProbability`), `VWAPBands_K1=1`, `VWAPBands_K2=2`. `SpreadMaxZ` retyped `int` (was `double`) to match MT5 optimiser ranges.

### Remaining parity drift NOT actioned

- `MagicNumber`: cTrader=`int`, MT5=`long`. 202604 fits an int so behaviour OK; cAlgo `[Parameter]` doesn't accept `long`.
- `DashboardColor_OK/FAIL/WAIT`: MT5 exposes; cTrader hardcodes. Promotable via `[Parameter] string` + `Color.FromName`.

### Recommendations not actioned

1. `M1`/`M2`/`M3`/`M5`/`M6` flags declared but not wired into gate stack (mirroring is parameter-only). Recommend `MRefinements.cs` so they actually filter.
2. `Symbol.Tick` aggressor is a proxy; for cTrader Premium, `Symbol.MarketDepth` snapshots give true depth-based aggressor labelling.
3. `RiskManager.SampleSpread` sorts a 100-sample array on every tick — switch to `OnBar` cadence.
4. `GoogleSheetsLevels.RefreshAsync` is async but never awaited from the sync `Robot` lifecycle; add `BeginInvokeOnMainThread` callback.
5. `BookmapBridge.ParseLine` hand-rolled JSON misses escaped quotes/unicode.

---

## Pine — `tradingview/` + `Enhanced/TradingView/`

### Bugs fixed

| File:line | Defect | Severity |
|---|---|---|
| `tradingview/GODMODE_OFEA.pine:469` | `runtime.error("ADVISORY")` halts script with red error banner in v6 (it is not a no-op placeholder). Intended path is the `alert()` above. | **Critical — script died on every A+ signal** |
| `tradingview/GODMODE_OFEA.pine:443-461` | `ta.change(series string)` — `ta.change()` is numeric-only in v6. Replaced with `x != x[1]` comparisons. | Compile error |
| `tradingview/GODMODE_OFEA_strategy.pine:179` | `(loc == "VAL" or loc == "VAL")` typo; simplified to single comparison. | Low |
| `tradingview/GODMODE_OFEA_Strategy_v2.pine:311` | Operator-precedence bug: `math.abs(entry_ - strategy.position_size > 0 ? slPrice : slPrice)` parsed as `abs(entry_ - position_size)` then ternary. Fixed to `math.abs(entry_ - slPrice)`. Added `partialDone` flag so `strategy.close()` fires once per position not every bar past 1R. | High |
| `tradingview/indicators/04_GODMODE_Coach.pine:246` | `for i = array.size(coachLabels) - 1 to 0` without `by -1` — v6 requires explicit negative step; without it the loop body never ran and labels never expired. | **High — memory + visual bug** |
| `tradingview/indicators/05_GODMODE_RiskHelper.pine:76` | `box.tostring(slBox) != "" or true` — `box.tostring()` not a Pine v6 builtin (compile error) and `or true` made guard a tautology. Replaced with `if not na(...)` guards. | Compile error |

### Hardening added

- `tradingview/indicators/01_GODMODE_Dashboard.pine:96` — `barstate.isconfirmed` guard on sub-TF delta summation (matches CVD Pane / Strategy v2). Prevents partially-populated lower-TF arrays causing CVD repaint.
- `Enhanced/TradingView/02_Enhanced_DeltaPane.pine:17` — `nz(cvd[1], 0.0)` na-safety on first bar.

### Recommendations not actioned

1. `Enhanced/TradingView/07_Enhanced_SetupCard.pine:24-36` — `line.new`/`label.new` inside `if barstate.islast` without object reuse; flickers every realtime tick. Should hold `var line`/`var label` handles (like `05_GODMODE_RiskHelper.pine` now does).
2. `01_GODMODE_Dashboard.pine:368-393` — `popupLabel()` creates labels with no cleanup; relies on `max_labels_count=500` auto-pruning. Coach has explicit `cleanup()` — mirror that.
3. `03_GODMODE_CVD_Pane.pine:91` — `plotshape(aggSpike, …, location.absolute, …)` draws at y=0; likely intent was `location.bottom` / `location.top`.
4. `Enhanced/TradingView/06_Enhanced_HTFStrength.pine:11` — comment says ADX but code computes ATR (`ta.rma(ta.tr, …)`); variable `a` is also unused downstream. Either compute true ADX (`ta.dmi`) or drop the unused value.
5. `04_GODMODE_Coach.pine:55` — `request.security_lower_tf(..., "1", subD())` hard-codes the sub-TF whereas Dashboard exposes it as an input. Wire to an input for parity, or document the lock.
6. `02_GODMODE_Footprint.pine:75` — `str.tostring(int(d / 100) * 100)` rounds delta to 100s; on low-volume FX symbols it prints "0". Use `str.tostring(d, "#")`.

---

## Rust + JS — `platform/godmode_engine/` + viewer

### Build status

- `cargo check --all-targets --all-features`: clean.
- `cargo clippy --all-targets --all-features -- -D warnings`: 7 errors → 0. Now clean.
- `cargo test --all-features`: **17/17 pass** (lib 8, conformance 4, ffi_smoke 1, properties 4).

### Bugs fixed

- `src/engine.rs:22,553` — removed unused `HtfBias` import + dead-code `const _: HtfBias = HtfBias::Neutral;` hack that existed only to silence the now-fixed clippy warning. `combined_bias` and dashboard `bias` field already keep `HtfBias` reachable.
- `src/replay.rs:99-121` — removed `b.clone()` on a `Copy` type, removed dead `let _ = len;`, reshaped inner loop. Previous code did `Vec<Bar>::iter().rev().cloned().collect()` on every bar — O(N²) allocations. Now uses `view.insert(0, *b)` against one persistent buffer.
- `src/logger.rs:1-15` — file-level `#![allow(clippy::derivable_impls)]` with comment explaining why explicit `Default` impls stay (the `common.rs` enums are the conformance surface mirrored to MT5/cTrader and must not carry `#[default]`).
- `src/setups.rs:32` + `src/trade.rs:42` — `#[allow(clippy::too_many_arguments)]` on `build()` (11 args) and `TradeManager::new()` (8 args). Conformance-locked signatures.
- `src/ffi.rs:146,134` — `iter().rev().cloned()` → `.copied()` (Bar is `Copy`); `unwrap_or(now_default())` → `unwrap_or_else(now_default)`.

### Hardening added

- `src/ffi.rs` — **every `extern "C"` function wrapped in `catch_unwind` (`ffi_guard`)**. Previously a panic inside the engine (poisoned `Mutex`, out-of-range `unwrap()`) would unwind across the C ABI = undefined behaviour.
- `src/ffi.rs:80` — `gme_engine_new` rejects null pointer + zero length before dereferencing; `Mutex::lock().unwrap()` replaced with `let Ok(...) else { return 0 }`; `wrapping_add(1).max(1)` hack replaced with explicit `if *next == 0 { *next = 1; }`.
- `src/ffi.rs:120` — `gme_engine_on_bar` rejects non-finite OHLC/volume/equity (returns -2). NaN propagation through `partial_cmp` in the profile / volume-Z math previously produced silent no-events. Also distinguishes mutex-poisoned (-3) vs handle-missing (-1).
- `src/ffi.rs` — `gme_events_ptr / _len / _clear / _drop` lost their `unwrap()`s; return safe defaults on poisoned mutex or missing handle.
- `platform/viewer/viewer.js` — `parseBarCsv` is now RFC-4180-aware (quoted fields with embedded commas / doubled quotes), refuses headerless files, refuses files missing required columns, filters non-finite rows.
- `platform/viewer/viewer.js` — `escape()` extended to cover `"` and `'`. All `innerHTML` interpolations of JSONL-sourced fields (`gg.gate`, `gg.name`, `n.Notify.tag`, dashboard `state/session/bias/loc/cvd_dir`, counts keys/values) now go through it. JSONL is user-loaded so this matters.

### Conformance / property test assessment

`tests/conformance.rs` is honest about being a *smoke test* in its module comment. It exercises end-to-end (synthetic 200 M15 bars, kill-switch short-circuit, tick-aggressor classifier, risk clamp) but **does not yet compare against an MT5/cTrader reference signal stream** — the ≥95% agreement target from brief §19 is deferred to the app shell's CI. As-is the test wouldn't catch a numeric divergence; it only catches "engine no longer fires events" / "kill switch ordering broken".

`tests/properties.rs` covers three brief-§19 invariants (2% risk cap, normalise round-down, CVD-slope identity) plus a deterministic loop over DD percentages. **Gaps:**
- No property test for gate ordering invariant (gate 0 must precede 1..8 every bar).
- No property test for `compute_volume` monotonicity in equity.
- No property test for `VolumeProfile::location_at` self-consistency (`location_at(poc, eps) == VpLoc::Poc`).
- No property test for NaN-resistance of the gate pipeline.

### Recommendations not actioned

1. **Replay window O(N²).** `replay.rs` still inserts at index 0 (linear memmove per bar). For long replays (>10k bars) switch to `VecDeque<Bar>` and pass `bars.make_contiguous()` to the engine, *or* cap window at max lookback (currently 96 VP + 50 liq_sweep ≈ 100). Behaviour-changing — needs conformance check first.
2. `engine.rs:198` — `delta.on_bar_close` shifts entire lookback array (`for i in (1..lookback).rev()`) every bar = O(N) per bar. Convert to a ring buffer.
3. `risk.rs:88` — sorts spread history on every tick sample (100 ticks → re-sorted). Use a maintained-order structure.
4. `profile.rs::classify_shape` — uses i64 `(low_bin + high_bin) / 2` then casts back to usize. Currently safe because `low_bin >= 0` is checked above; worth a comment.
5. `ffi.rs` — allocates fresh `view: Vec<Bar>` per bar. Cache in `Slot` and truncate-extend in place.
6. **Brief §19 says session-close 21:00 SAST** but no force-close at minute 1260 anywhere in `session.rs` / `engine.rs`. `approaching_ny_main_end` exists but isn't called. Probably owned by the app shell; flagged as TODO.

---

## Cross-cutting observations

- **Forming-bar bug pattern** showed up in *three* places and three different languages this pass: MT5 `OF_HTFAlignment`, cTrader `HTFAlignment.cs`, and TradingView `01_GODMODE_Dashboard.pine`. All three prior audit passes missed it. Worth a permanent assertion: any signal feeding a gate must use closed-bar indices (`[1]` / `Last(1)` / `barstate.isconfirmed`).
- **Dead parameter pattern** also showed up cross-build: cTrader `MaxRR` was declared but never read; cTrader `M1..M6` flags are declared but unwired; cTrader `_fail` color was unused; Rust `HtfBias` import was unused. A "no unused public input" lint would catch these.
- **Handle/resource leaks** in MT5 (`iATR` per-call) and Rust (per-bar `Vec` allocation) suggest the next pass should be a perf-focused sweep.
- **Conformance test is a smoke test**, not a parity test against MT5/cTrader. That gap is the single biggest risk to the project's "behaviourally-identical, parameter-mirrored" promise.

## Commits landed in this pass

```
6729c71 fix: audit pass 4 — final late edits (cTrader + MT5)
c548037 fix: audit pass 4 — late MT5 HTFStrength edit
db4a8fd fix: audit pass 4 — late edits (cTrader RiskManager/PoolResilience, MT5 HTFStrength)
cd924cf fix: rust platform audit pass 4
14d8a97 fix: ctrader audit pass 4
6d2c54a fix: mt5 audit pass 4
b4de5f7 fix: pine audit pass 4 — 6 bugs + 2 hardening guards
9e6141d refactor: consolidate MT5 artifacts into MT5_Unified/
```
