# External Data Integration — §25 (cTrader & MT5)

This document describes how the GODMODE_OFEA EA on **cTrader** and **MT5**
consumes data from external order-flow platforms (Sierra Chart, Bookmap) and
operator-curated sources (Google Sheets) to strengthen the existing 5-gate
confluence stack — without departing from brief §19 rule 7 mirror discipline.

The EA's gate ordering, kill switches, sizing math, and journal schema remain
exactly as specified in §1–§24. These bridges are *additive* — when the
external feed is unavailable or stale, the EA falls back to its own native
calculations and continues to trade per the base brief.

---

## Why this exists

cTrader and MT5 are excellent execution platforms but limited for true order-
flow analysis. Sierra Chart and Bookmap deliver capabilities those platforms
cannot (real depth ladder, market-by-order, calibrated tick volume). Rather
than build a third or fourth platform, we bridge the *data*: Sierra Chart and
Bookmap export structured files; the cTrader cBot / MT5 EA reads them and
folds the signals into the existing pipeline.

The result: cTrader's execution + Bookmap's microstructure + Sierra Chart's
profile precision, all routed through the same gate cascade and the same
notification layer.

---

## Modules

### cTrader (`ctrader/GODMODE_OFEA/Modules/`)

| Module | Source pattern | Purpose |
|---|---|---|
| `IcebergTracker.cs` | `TapeOnChart.cpp` (Frozen Tundra) | Native microstructure iceberg detector — consec-prints + max-depth-observed. Replaces the price-pattern proxy in Setup #25. |
| `PaceOfTape.cs` | `pace_of_tape.cpp` (Frozen Tundra) | Lagging-max pace ratio. Surfaces N-V notification when pace ≥ threshold. |
| `SierraChartBridge.cs` | `JIGSAW_Export.cpp` (Frozen Tundra) | Reads CSV emitted by Sierra Chart's JIGSAW_Export study. Levels: POC, VAH, VAL, dVWAP, ±std-dev, ovnH/ovnL, dEQ/wEQ/mEQ. |
| `BookmapBridge.cs` | Bookmap Python API (companion addon) | Tails JSON-lines of DEPTH_BBO, DEPTH_SUM, ICEBERG, PRESSURE events. |
| `GoogleSheetsLevels.cs` | `google_sheets_importer.cpp` (Frozen Tundra) | Pulls operator-curated key levels from a shared Sheet via gviz CSV. |
| `AutoRiskReward.cs` | `auto_risk_reward.cpp` (Frozen Tundra) | Auto-draws SL/TP/entry/R:R rectangle on every fill. Implements §9.5. |

### MT5 (`MT5_Unified/Include/`)

| Module | Mirrors |
|---|---|
| `OF_IcebergTracker.mqh` | `IcebergTracker.cs` |
| `OF_PaceOfTape.mqh` | `PaceOfTape.cs` |
| `OF_SierraChartBridge.mqh` | `SierraChartBridge.cs` |
| `OF_BookmapBridge.mqh` | `BookmapBridge.cs` |
| `OF_GoogleSheetsLevels.mqh` | `GoogleSheetsLevels.cs` |
| `OF_AutoRiskReward.mqh` | `AutoRiskReward.cs` |

Same logic, MQL5 syntax. Brief §19 rule 7.

---

## Notification cascade extensions

Five new tags appended to the existing N-A through N-L cascade. Each is
edge-detected and rate-limited per bar like the original twelve.

| Tag | Meaning | Visual / sound |
|---|---|---|
| `N-V` | Pace-of-Tape elevated (`pace ≥ AggressionPaceThreshold`). | Soft chime, blue toast, dashboard row 13 turns green. |
| `N-W` | Bookmap-confirmed iceberg matching intended direction. | Purple diamond at price, double chime, push notification. Strengthens GATE 6 by one star. |
| `N-X` | Price within `LocTolATR` of a Sierra Chart-exported level. | Yellow "SC" badge next to price label. Bonuses GATE 3 score. |
| `N-Y` | Price within `LocTolATR` of an operator manual level (Google Sheets). | Gold "MAN" badge with the note text. Bonuses GATE 3 score. |

Brief §4 rate-limiting applies — `Dictionary<string, datetime>` keyed on the
tag, fire only on FALSE→TRUE per-bar edge transition.

---

## How each bridge folds into the gate pipeline

### Sierra Chart levels (`SierraChartBridge`) → GATE 3 enhancement

`OnBar` calls `Refresh(now)`. If a Sierra Chart level falls within `LocTolATR
× ATR(14)` of close, GATE 3 fires `N-X` and the candidate gets `score += 1`
(in addition to any native VP location score). When `IsStale(now) == true`,
the bridge contributes nothing — pipeline behaves exactly as in the base
brief.

### Bookmap iceberg + pressure (`BookmapBridge`) → GATE 6 enhancement

`OnTick` calls `Tail(now)` to drain new JSON events. At GATE 6 the cBot
queries:
1. `RecentIceberg(now, side, withinSeconds: 30)` — if true and side matches
   intended trade direction, `N-W` fires and `absStars` is bumped by 1
   (capped at 5).
2. `BuyPressure` / `SellPressure` — included as a tiebreaker between
   simultaneous candidates.
3. `DepthImbalance()` — feeds the existing F4 CVD-confirmation as a
   secondary input (e.g. depth imbalance ≥ 1.5 in trade direction = pass-
   plus).

When `IsStale(now)` the bridge contributes nothing.

### Google Sheets manual levels (`GoogleSheetsLevels`) → GATE 3 bonus

Operator maintains a single Sheet; every chart on every machine refreshes on
a 5-minute cadence. Schema mirrors the existing `news_blackout.json` pattern
(simple, human-editable, version-controlled).

`ClosestLevel(price, tolerance)` — when a manual level is within tolerance
the candidate gets `score += 1` and `N-Y` fires with the operator's note
text (e.g. "Weekly Open" / "IB High" / "Pivot S1").

### Pace-of-Tape (`PaceOfTape`) → GATE 6 supplementary check

Each trade tick feeds `OnTrade(ts, size)`. At GATE 6 if `Pace() ≥
AggressionPaceThreshold` and the candidate is direction-aligned, `N-V`
fires and the candidate's `score += 1`. Independent of the existing
`vol_z` check — this is microstructure tape velocity, not bar-level
volume distribution.

### Iceberg upgrade (`IcebergTracker`) → Setup #25 rewrite

The original Setup #25 detected iceberg statistically (low |δZ| + high
volZ + narrow range at VP level). It was a proxy because cTrader/MT5
cannot see depth depletion directly.

This module *can* see depth via the BookmapBridge top-of-book mirror
(`OnTopOfBook`) and via cTrader's `MarketDepth` event (when the broker
exposes it). When depth is unavailable it degrades gracefully to the
consec-prints + min-volume rule, which is still materially better than
the original price-pattern proxy.

### Auto R:R (`AutoRiskReward`) → §9.5 implementation

Hooks into TradeManager's position-opened / position-closed callbacks.
Draws a green TP rectangle, red SL rectangle, white entry line, and a
yellow info label with size + R:R + currency value. Cleans itself up
when the position closes.

---

## Companion components (operator-managed, out of EA scope)

These run on the operator's machine alongside Sierra Chart and Bookmap.
They are **not** part of the cTrader/MT5 build — they're data producers
that the EA consumes.

### Sierra Chart side

Use the unmodified `JIGSAW_Export.cpp` from the supplied corpus. Configure
its output path under `<Terminal>/MQL5/Files/` (for MT5) or any path
readable by your cTrader install.

### Bookmap side

Run a small Python addon using the Bookmap Python API (see the
`bookmap-python-api` reference). The addon should:

```python
# Pseudo. Not part of the EA build.
import bookmap as bm, json, datetime
PATH = "/path/to/bookmap_export.jsonl"

def write(ev):
    with open(PATH, "a") as f:
        f.write(json.dumps(ev, default=str) + "\n")

# DEPTH_BBO from subscribe_to_depth callback
def on_depth(addon, alias, is_bid, price, size):
    write({"ts": datetime.datetime.utcnow().isoformat()+"Z",
           "kind": "DEPTH_BBO", "bid": ..., "bidSz": ..., "ask": ..., "askSz": ...})

# ICEBERG from subscribe_to_mbo + consec-print tracker
def on_iceberg(side, price, consec, vol, max_depth):
    write({"ts": ..., "kind": "ICEBERG", "side": side, "price": price,
           "consec": consec, "vol": vol, "maxDepth": max_depth})

# PRESSURE from add_broadcasting_handler (Market Pulse provider)
```

Operators run this addon once on their Bookmap chart; it writes to a single
file the cTrader and MT5 EAs both tail.

### Google Sheets side

A single shared Google Sheet with the schema (Price, Price2, Note, Color,
LineType, LineWidth, TextAlignment). Sharing: "Anyone with link can view".

For MT5: add `https://docs.google.com` to *Tools → Options → Expert Advisors
→ Allow WebRequest for listed URL*. cTrader cBot needs `AccessRights.
FullAccess` granted in the cBot configuration.

---

## New input parameters (cTrader + MT5)

Add to §7 input schema:

```
=== EXTERNAL DATA BRIDGES (§25) ===
EnableSierraChartBridge   : bool   default false
SierraChart_FilePath      : string default ""
EnableBookmapBridge       : bool   default false
Bookmap_FilePath          : string default ""
EnableGoogleSheetsLevels  : bool   default false
GoogleSheets_BaseURL      : string default ""
GoogleSheets_RefreshSecs  : int    default 300

=== ICEBERG / PACE (§25) ===
Iceberg_MinConsecPrints   : int    default 5
Iceberg_MinTotalVolume    : double default 100.0
Iceberg_RefillRatio       : double default 2.0
AggressionPaceThreshold   : double default 0.85
PaceOfTape_WindowSeconds  : int    default 60
PaceOfTape_LaggingFraction: int    default 5

=== AUTO R:R DRAWING (§9.5) ===
AutoRiskReward_Enabled    : bool   default true
AutoRiskReward_FontSize   : int    default 11
AutoRiskReward_LineWidth  : int    default 1
AutoRiskReward_ShowCurrency : bool default true
```

All bridges default OFF. The base build per §1–§24 remains unchanged.
Operators earn enablement of each bridge through measured journal data
(brief §22 discipline).

---

## Acceptance criteria

Add to `TESTING.md`:

1. **Bridge-disabled regression**: with all `Enable*Bridge` set to false,
   gate decisions and journal output match a pre-§25 reference replay
   exactly. No behavioural change.

2. **Bridge-stale fallback**: kill the Sierra Chart export process mid-
   replay. After `staleSeconds` (default 120s) the EA logs a warning,
   stops contributing N-X/N-Y, and continues trading on its native VP.
   No stuck states, no crashes.

3. **Bridge-enabled lift**: with all bridges enabled and feeding clean
   data, expect approximately +1 to +3 percentage points on filtered
   win rate per Appendix A.2 stacking math (mid-point estimate). Per
   Appendix A.6 honesty contract — measure your own data, don't trust
   the estimate.

4. **N-W cooldown**: same iceberg event fired by Bookmap must not
   trigger N-W twice within the same bar. Edge-detection per brief §4
   applies identically to the new tags.

---

## What this section deliberately does not change

- Brief §1–§24 trading thesis, gate ordering, kill switches, sizing math.
- Mirror discipline between MT5 and cTrader.
- The 25 setup detector enumeration (Setup #25 is *upgraded internally* but
  retains the same SetupID and outward contract).
- The CSV journal schema. New events route through existing event types
  (`SKIP_F1` for stale-bridge skips, `ENTRY` for fills with bridge-bonus
  scoring, `KILL_*` for any kill-switch deferred from a bridge anomaly).
