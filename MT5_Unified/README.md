# MT5_Unified — all MetaTrader 5 artifacts in one place

This folder consolidates everything that used to live in three separate places:

| Old path                  | New path                                  |
|---------------------------|-------------------------------------------|
| `mt5/GODMODE_OFEA/`       | `MT5_Unified/Experts/GODMODE_OFEA/` + `Include/` |
| `Enhanced/MT5/`           | `MT5_Unified/Experts/GODMODE_OFEA_Enhanced/` + `Include/` + `Indicators/GODMODE/` |
| `Mt5_include these/`      | `MT5_Unified/Include/` (visual overlays)  |

History was preserved via `git mv`. EA include paths (`"../../Include/OF_*.mqh"`) still resolve, no source changes were needed.

## Layout

```
MT5_Unified/
├── Experts/
│   ├── GODMODE_OFEA/                  base EA
│   │   └── GODMODE_OFEA.mq5
│   └── GODMODE_OFEA_Enhanced/         enhanced overlay EA
│       └── GODMODE_OFEA_Enhanced.mq5
├── Indicators/
│   └── GODMODE/                       chart-attachable indicators
│       ├── GODMODE_BidAskSpread.mq5
│       ├── GODMODE_ConfluenceDashboard.mq5
│       ├── GODMODE_DeltaBars.mq5
│       ├── GODMODE_HTFStrength.mq5
│       ├── GODMODE_PriceActionLabels.mq5
│       ├── GODMODE_SessionLight.mq5
│       └── GODMODE_VWAP.mq5
└── Include/                           all .mqh headers (loose, no subfolder)
    │
    │  -- base build (20 files, used by GODMODE_OFEA.mq5) --
    ├── OF_AbsorptionStars.mqh
    ├── OF_AutoRiskReward.mqh
    ├── OF_BookmapBridge.mqh
    ├── OF_ChartViz.mqh
    ├── OF_Common.mqh
    ├── OF_Dashboard.mqh
    ├── OF_DeltaEngine.mqh
    ├── OF_FootprintAnalyzer.mqh
    ├── OF_GoogleSheetsLevels.mqh
    ├── OF_HTFAlignment.mqh
    ├── OF_IcebergTracker.mqh
    ├── OF_Logger.mqh
    ├── OF_NotificationCenter.mqh
    ├── OF_PaceOfTape.mqh
    ├── OF_RiskManager.mqh
    ├── OF_SessionGate.mqh
    ├── OF_SetupDetectors.mqh
    ├── OF_SierraChartBridge.mqh
    ├── OF_TradeManager.mqh
    ├── OF_VolumeProfile.mqh
    │
    │  -- enhanced overlays (9 files, used by GODMODE_OFEA_Enhanced.mq5) --
    ├── OF_BidAsk.mqh
    ├── OF_DeltaEnhanced.mqh
    ├── OF_KellySizer.mqh
    ├── OF_PoolResilience.mqh
    ├── OF_PriceAction.mqh
    ├── OF_ProbabilityScore.mqh
    ├── OF_RegimeHMM.mqh
    ├── OF_SweepDetector.mqh
    ├── OF_VWAP.mqh
    │
    │  -- visual addons (9 files, optional drop-in chart aesthetic) --
    ├── OF_CanvasDashboard.mqh
    ├── OF_ChartTheme.mqh
    ├── OF_CvdSubwindow.mqh
    ├── OF_FootprintMarkers.mqh
    ├── OF_GlowLevels.mqh
    ├── OF_SessionShade.mqh
    ├── OF_Toast.mqh
    ├── OF_TradeLines.mqh
    └── OF_VPHeatmap.mqh
```

## Install on Windows MT5

The folder structure here mirrors MetaTrader's `MQL5\` directory one-to-one.
Copy each subfolder into the matching location under `MQL5\`.

1. In MetaEditor: **File → Open Data Folder** → opens `MQL5\`.
2. Copy `MT5_Unified/Include/*.mqh` → `MQL5\Include\` (all files loose, no subfolder).
3. Copy `MT5_Unified/Experts/GODMODE_OFEA/` → `MQL5\Experts\GODMODE_OFEA\`.
4. Copy `MT5_Unified/Experts/GODMODE_OFEA_Enhanced/` → `MQL5\Experts\GODMODE_OFEA_Enhanced\`.
5. Copy `MT5_Unified/Indicators/GODMODE/` → `MQL5\Indicators\GODMODE\`.
6. In MetaEditor, open each `.mq5` and press **F7** (Compile). Confirm `0 errors, 0 warnings`.
7. Restart MT5 (or right-click Navigator → Refresh).
8. Attach indicators: `Navigator → Indicators → GODMODE` → double-click each onto the chart.
9. Attach EA: `Navigator → Expert Advisors` → drag your chosen EA (base or Enhanced) onto the chart. In the **Common** tab, tick **"Allow Algo Trading"** → OK. Confirm the global Algo Trading toolbar button is green.

## Verify the visuals

After attaching the Enhanced EA + all 7 indicators, the chart should show, in order:

1. **GODMODE Confluence Dashboard** — top-left, 12 numbered rows + Probability bar + Setup card.
2. **GODMODE VWAP** — yellow line with two aqua bands (±1σ) and two purple bands (±2σ).
3. **GODMODE Delta Bars** — separate subwindow with delta histogram, yellow CVD line, magenta climax markers.
4. **GODMODE Bid/Ask Spread** — live spread monitor (mid-left).
5. **GODMODE Price Action Labels** — BOS↑/BOS↓ tags, dashed EQH/EQL lines, FVG rectangles.
6. **GODMODE Session Light** — coloured square + current session name (bottom).
7. **GODMODE HTF Strength** — M15/H1/H4/D1 with ▲/▼ arrows and ADX bars.

If anything is missing, see `docs/smoke_test.md` and the troubleshooting section of the top-level `README.md`.

## Optional: wiring the visual addons into the EA

The 9 `OF_Canvas*/OF_*Shade/OF_Glow*/OF_Toast/OF_TradeLines/OF_VPHeatmap` headers
are an optional aesthetic upgrade. They share the prefix `OF_PREFIX = "GODMODE_"`
so a single `ObjectsDeleteAll(0, "GODMODE_", 0, -1)` cleans the entire chart.

At the top of `GODMODE_OFEA.mq5`:

```mql5
#include "../../Include/OF_ChartTheme.mqh"        // must be first — defines colours/fonts/sizes
#include "../../Include/OF_CanvasDashboard.mqh"
#include "../../Include/OF_GlowLevels.mqh"
#include "../../Include/OF_Toast.mqh"
#include "../../Include/OF_SessionShade.mqh"
#include "../../Include/OF_FootprintMarkers.mqh"
#include "../../Include/OF_CvdSubwindow.mqh"
#include "../../Include/OF_TradeLines.mqh"
#include "../../Include/OF_VPHeatmap.mqh"
```

Globals:

```mql5
COFDashboard    g_dash;
COFGlow         g_levels;
COFToast        g_toast;
COFSessionShade g_shade;
COFFootprint    g_fp;
COFCvdPanel     g_cvd;
COFVPHeatmap    g_heat;
```

`OnInit`:

```mql5
g_dash.Init(); g_levels.Init(); g_toast.Init();
g_shade.Init(); g_fp.Init(); g_cvd.Init(0, 1); g_heat.Init();
```

`OnDeinit`:

```mql5
g_dash.Destroy(); g_toast.Destroy(); g_heat.Destroy();
g_levels.Clear(); g_shade.Clear(); g_fp.Clear(); g_cvd.Clear();
ObjectsDeleteAll(0, OF_PREFIX, 0, -1);
```

`OnTick` / `OnTimer` (~250 ms throttle on the dashboard):

```mql5
g_dash.Clear();
g_dash.Title("GODMODE OFEA — " + _Symbol);
g_dash.Row(0, "State",     StateStr(),  StateOk() ? OF_OK : OF_FAIL);
g_dash.Row(1, "Kill Zone", SessionStr(),InKZ()    ? OF_OK : OF_DIM);
g_dash.Row(2, "HTF",       BiasStr(),   HtfOk()   ? OF_OK : OF_FAIL);
g_dash.Row(7, "R:R",       DoubleToString(g_rr, 2), g_rr >= 2 ? OF_OK : OF_FAIL);
g_dash.Update();

if(EdgeNI()) g_toast.Show("N-I · A+ READY", "LONG · 5/5 · RR 4.4", OF_OK);
g_toast.Tick();
```

## Customising the theme

Open `Include/OF_ChartTheme.mqh`:

```mql5
#define OF_OK     C'43,200,140'    // green
#define OF_FAIL   C'230,80,100'    // red
#define OF_FONT   "Consolas"
#define OF_DASH_W 380              // panel width
```

Recompile — the entire EA re-themes.

## Performance notes

- Canvas labels (`OF_CanvasDashboard`, `OF_Toast`, `OF_VPHeatmap`) cost ~0.5 ms per `Update()`. Throttle them on a timer or `GetTickCount()` guard.
- OBJ_* objects (`OF_GlowLevels`, `OF_FootprintMarkers`, `OF_TradeLines`, `OF_SessionShade`) are essentially free; redraw is GPU-side. Keep total object count under ~2000 for smooth panning.
- `ObjectsDeleteAll(0, OF_PREFIX, ...)` in `OnDeinit` is the safety net.

## Brief mapping (for the visual addons)

| Section | File |
|---------|------|
| §3 Dashboard           | `OF_CanvasDashboard.mqh`  |
| §4 Notification toast  | `OF_Toast.mqh`            |
| §9.1 VP lines          | `OF_GlowLevels.mqh`       |
| §9.2 CVD subwindow     | `OF_CvdSubwindow.mqh`     |
| §9.3 Footprint markers | `OF_FootprintMarkers.mqh` |
| §9.4 Session shading   | `OF_SessionShade.mqh`     |
| §9.5 Trade lines       | `OF_TradeLines.mqh`       |
| §9.6 VP heatmap        | `OF_VPHeatmap.mqh`        |
