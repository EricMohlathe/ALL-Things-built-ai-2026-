# Mt5_include these/ — chart aesthetic include files

Drop-in `.mqh` files that upgrade the GODMODE_OFEA EA's chart visuals. All
files share a single namespace (`OF_PREFIX = "GODMODE_"`) so a single
`ObjectsDeleteAll(0, "GODMODE_", 0, -1)` cleans the entire chart.

## Files

| File | Purpose | MT5 stdlib used |
|------|---------|-----------------|
| `OF_ChartTheme.mqh` | Colors, fonts, layout constants. Edit once, retheme everything. | — |
| `OF_CanvasDashboard.mqh` | Antialiased dashboard with rounded corners + gradient accent. | `<Canvas/Canvas.mqh>` |
| `OF_GlowLevels.mqh` | POC/VAH/VAL/LVN/HVN with soft halo effect. | `<ChartObjects/*>` (OBJ_TREND + OBJ_TEXT) |
| `OF_Toast.mqh` | Stacked corner notifications with auto-fade. | `<Canvas/Canvas.mqh>` |
| `OF_SessionShade.mqh` | Translucent LDN/NY session backgrounds. | `<ChartObjects/*>` (OBJ_RECTANGLE) |
| `OF_FootprintMarkers.mqh` | Stars, triangles, diamonds for absorption / stacked / iceberg. | `<ChartObjects/*>` (OBJ_ARROW Wingdings) |
| `OF_CvdSubwindow.mqh` | CVD polyline + divergence arrows in a sub-window. | OBJ_TREND + OBJ_ARROW |
| `OF_TradeLines.mqh` | Entry/SL/TP/partial/BE/trail badges. Brief §9.5. | OBJ_HLINE + OBJ_TEXT |
| `OF_VPHeatmap.mqh` | Bookmap-style horizontal VP heatmap bar. | `<Canvas/Canvas.mqh>` |

## How to install

### Step 1 — copy into MetaEditor

1. MT5 → top menu **File → Open Data Folder**
2. Navigate to `MQL5\Include\`
3. Create a subfolder `GODMODE\` (avoids collisions with other indicators)
4. Copy all the `.mqh` files from this folder into `MQL5\Include\GODMODE\`

Result:
```
MQL5\Include\GODMODE\
├── OF_ChartTheme.mqh
├── OF_CanvasDashboard.mqh
├── OF_GlowLevels.mqh
├── OF_Toast.mqh
├── OF_SessionShade.mqh
├── OF_FootprintMarkers.mqh
├── OF_CvdSubwindow.mqh
├── OF_TradeLines.mqh
└── OF_VPHeatmap.mqh
```

### Step 2 — include in your EA

At the top of `GODMODE_OFEA.mq5`:

```mql5
#include <GODMODE/OF_ChartTheme.mqh>          // must be first — defines constants others use
#include <GODMODE/OF_CanvasDashboard.mqh>
#include <GODMODE/OF_GlowLevels.mqh>
#include <GODMODE/OF_Toast.mqh>
#include <GODMODE/OF_SessionShade.mqh>
#include <GODMODE/OF_FootprintMarkers.mqh>
#include <GODMODE/OF_CvdSubwindow.mqh>
#include <GODMODE/OF_TradeLines.mqh>
#include <GODMODE/OF_VPHeatmap.mqh>
```

### Step 3 — instantiate + wire

Globals near the top of your EA:

```mql5
COFDashboard       g_dash;
COFGlow            g_levels;
COFToast           g_toast;
COFSessionShade    g_shade;
COFFootprint       g_fp;
COFCvdPanel        g_cvd;
COFVPHeatmap       g_heat;
```

In `OnInit()`:

```mql5
int OnInit() {
    g_dash.Init();
    g_levels.Init();
    g_toast.Init();
    g_shade.Init();
    g_fp.Init();
    g_cvd.Init(0, 1);          // sub-window 1
    g_heat.Init();
    return INIT_SUCCEEDED;
}
```

In `OnDeinit()`:

```mql5
void OnDeinit(const int reason) {
    g_dash.Destroy();
    g_toast.Destroy();
    g_heat.Destroy();
    g_levels.Clear();
    g_shade.Clear();
    g_fp.Clear();
    g_cvd.Clear();
    ObjectsDeleteAll(0, OF_PREFIX, 0, -1);   // belt + braces
}
```

In `OnTick()` (or `OnTimer()` for the dashboard refresh):

```mql5
// — dashboard, called ~250ms throttled —
g_dash.Clear();
g_dash.Title("GODMODE OFEA — " + _Symbol);
g_dash.Row(0, "State",     StateStr(),  StateOk()  ? OF_OK : OF_FAIL);
g_dash.Row(1, "Kill Zone", SessionStr(),InKZ()     ? OF_OK : OF_DIM);
g_dash.Row(2, "HTF",       BiasStr(),   HtfOk()    ? OF_OK : OF_FAIL);
g_dash.Row(3, "VP Loc",    LocStr(),    LocOk()    ? OF_OK : OF_DIM);
g_dash.Row(4, "CVD",       CvdStr(),    CvdOk()    ? OF_OK : OF_DIM);
g_dash.Row(5, "Footprint", FpStr(),     FpOk()     ? OF_OK : OF_WAIT);
g_dash.Row(6, "SL",        DoubleToString(g_sl, _Digits), OF_TEXT);
g_dash.Row(7, "R:R",       DoubleToString(g_rr, 2), g_rr >= 2 ? OF_OK : OF_FAIL);
g_dash.Sep(36 + 8*OF_DASH_ROW_H);
g_dash.Update();

// — toasts on gate transitions (FALSE→TRUE edge) —
if(EdgeNA()) g_toast.Show("N-A · VAL touch", "EURUSD @ 1.0830", OF_ACCENT);
if(EdgeNI()) g_toast.Show("N-I · A+ READY", "LONG · 5/5 · RR 4.4", OF_OK);
g_toast.Tick();         // call every tick to fade

// — VP levels on bar close —
if(IsNewBar()) {
    g_levels.Clear();
    g_levels.POC(g_poc); g_levels.VAH(g_vah); g_levels.VAL(g_val);
    g_shade.Update(iTime(_Symbol, PERIOD_CURRENT, 0), SastMin());
}

// — footprint markers on detection —
if(g_absDetected) g_fp.Absorption(iTime(_Symbol, _Period, 0), iLow(_Symbol, _Period, 0),
                                  g_absDir == DIR_LONG, g_absStars);

// — trade lines on fill —
if(g_filledTicket > 0) {
    COFTradeLines tl; tl.Init(0, g_filledTicket);
    tl.DrawEntry(g_entry, DoubleToString(g_lots, 2));
    tl.DrawSL(g_sl, g_slPips);
    tl.DrawTP(g_tp, g_tpPips, g_rr);
}
```

## Customising the theme

Open `OF_ChartTheme.mqh`. Every visual lives there:

```mql5
#define OF_OK     C'43,200,140'    ← change to your preferred green
#define OF_FAIL   C'230,80,100'    ← change to your preferred red
#define OF_FONT   "Consolas"       ← change to your preferred mono font
#define OF_DASH_W 380              ← widen / narrow the panel
```

Recompile. Entire EA re-themes.

## Performance notes

- Canvas labels (`OF_CanvasDashboard`, `OF_Toast`, `OF_VPHeatmap`) cost ~0.5 ms
  per `Update()`. Throttle with a timer or a `GetTickCount()` guard.
- OBJ_* objects (`OF_GlowLevels`, `OF_FootprintMarkers`, `OF_TradeLines`,
  `OF_SessionShade`) are essentially free; redraw is GPU-side. Keep the
  total object count under ~2000 for smooth panning.
- `ObjectsDeleteAll(0, OF_PREFIX, ...)` in `OnDeinit` is the safety net.

## Brief mapping

| Section | Implementing file |
|---------|-------------------|
| §3 Dashboard | `OF_CanvasDashboard.mqh` |
| §4 Notification toast | `OF_Toast.mqh` |
| §9.1 VP lines | `OF_GlowLevels.mqh` |
| §9.2 CVD subwindow | `OF_CvdSubwindow.mqh` |
| §9.3 Footprint markers | `OF_FootprintMarkers.mqh` |
| §9.4 Session shading | `OF_SessionShade.mqh` |
| §9.5 Trade lines | `OF_TradeLines.mqh` |
| §9.6 Heatmap (extra) | `OF_VPHeatmap.mqh` |

Each file references its brief section in its own header.
