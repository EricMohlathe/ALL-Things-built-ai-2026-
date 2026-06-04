# Production EA Architecture Blueprint

Every EA shipped by this skill follows this exact module stack. Skipping a layer is a bug.

## Module stack (top → bottom)

```
┌────────────────────────────────────────────────────────────┐
│  1. Inputs / Parameters block                               │
│     – grouped by purpose, ALL with sane defaults             │
├────────────────────────────────────────────────────────────┤
│  2. Globals + state                                         │
│     – cvd[], footprint cache, dayKey, lastBarSeen, ...       │
├────────────────────────────────────────────────────────────┤
│  3. OnInit / OnStart                                        │
│     – validate inputs, register MarketBook/Depth, set magic  │
├────────────────────────────────────────────────────────────┤
│  4. Risk / Guard layer                                      │
│     – DailyLossOk, SpreadOk, SessionOk, NewsOk, MaxPositions │
├────────────────────────────────────────────────────────────┤
│  5. Order-flow primitives layer                             │
│     – Delta, CVD, Footprint, POC/POI, Imbalance              │
├────────────────────────────────────────────────────────────┤
│  6. Pattern detectors                                       │
│     – Absorption, Exhaustion, Initiative, Sweep, Divergence  │
├────────────────────────────────────────────────────────────┤
│  7. AMT phase classifier                                    │
│     – BALANCE / IMBALANCE / DISCOVERY / ACCEPTANCE / FAILED  │
├────────────────────────────────────────────────────────────┤
│  8. Confluence scorer                                       │
│     – weighted sum → entryScore                              │
├────────────────────────────────────────────────────────────┤
│  9. Signal gate + entry trigger                             │
│     – entryScore ≥ threshold && all guards pass              │
├────────────────────────────────────────────────────────────┤
│ 10. Trade management                                        │
│     – BE move, partial close, trailing stop                  │
├────────────────────────────────────────────────────────────┤
│ 11. Dashboard + logging                                     │
│     – on-chart text panel + file log + alerts                │
├────────────────────────────────────────────────────────────┤
│ 12. OnDeinit / OnStop                                       │
│     – release MarketBook, flush logs                         │
└────────────────────────────────────────────────────────────┘
```

## Inputs grouping convention

```
//=== Risk ===
//=== Strategy / Confluence ===
//=== Filters (Session, News, Spread) ===
//=== Order-flow (Delta, Imbalance, CVD) ===
//=== Trade Management (BE, Trail, Partial) ===
//=== Diagnostics (Dashboard, Verbose) ===
```

Use `///` group headers in cAlgo (`[Parameter("...", Group = "Risk")]`) and `input group "Risk";` markers in MQL5.

## Magic + comment + label

- MQL5: `InpMagic` (int), `InpComment` (string), pass to `CTrade`.
- cAlgo: `InpMagic` (int), `InpLabel` (string), pass as `label` to `ExecuteMarketOrder`.

Magic is used to filter "our trades only" inside `OnTimer`/`OnTick` so the EA never closes a manual position.

## Dashboard contract

A single on-chart text block that always shows:

```
============== <EA name> ==============
Phase   : DISCOVERY
Score   : 0.74 (thresh 0.60)
Bias    : LONG
Spread  : 0.8 pips (max 2.0)
Daily PL: −0.41% (halt at 3.00%)
CVD     : +1240
POC     : 1.07842
Last    : SOS @ 09:14
=======================================
```

## Logging contract

Every entry, exit, BE move, partial, trail must log:
```
yyyy-mm-dd HH:MM:SS | <EVENT> | <symbol> | <ticket> | <price> | <reason>
```
File path: `Files/<EaName>_<Symbol>_<TF>.log` on MT5; `<EaName>_<Symbol>_<TF>.log` in cAlgo `Logs` folder.

## Alert contract

Push on:
- Entry, BE move, partial, exit (every state change).
- Risk halt fired (max-daily-loss).
- Connection / depth-feed loss.

## Backtest contract

Always bundle:
- `<EaName>.set` (MQL5) / `<EaName>.params` (cAlgo) with conservative defaults.
- A README block at the top of the EA that lists tested broker, symbol, TF, period.
- A "first-tick sanity test": what should print on the first tick to confirm input wiring.

## Failure modes & graceful degradation

| Failure | Behaviour |
|---|---|
| No depth feed | Disable sweep / book-aware logic, dashboard shows `Depth: OFFLINE`, continue with bar-level signals |
| No tick volume / real volume | Fall back to signed-tick-count delta; dashboard flags `Delta: APPROX` |
| Connection drop | Pause new entries; existing positions left to broker SL/TP |
| Spread spike | Skip cycle, log `WIDE_SPREAD` |
| News halt | Cancel pending orders, freeze for `InpNewsHaltMin` minutes around event |

## File / folder layout

```
<EaName>/
├── <EaName>.mq5            # MT5 EA
├── <EaName>.set            # MT5 default inputs
├── <EaName>.cs             # cAlgo cBot
├── <EaName>.params         # cAlgo defaults
├── README.md               # symbol/TF, default risk, expectations
└── tests/
    ├── strategy_tester_runs.md
    └── live_forward_log.md
```

