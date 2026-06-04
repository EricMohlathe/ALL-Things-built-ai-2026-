# Enhanced/TradingView — install on tradingview.com

Seven Pine v6 indicators. Pasted in this order, they form a self-contained
visual replica of the MT5 build's enhanced dashboard.

| # | File | Pane |
|---|------|------|
| 01 | `01_Enhanced_VWAP.pine`         | Overlay |
| 02 | `02_Enhanced_DeltaPane.pine`    | Sub-window |
| 03 | `03_Enhanced_PriceAction.pine`  | Overlay (BOS/CHoCH/EqH-L/FVG markers) |
| 04 | `04_Enhanced_ProbabilityBar.pine`| Overlay (right-middle 0-100% bar) |
| 05 | `05_Enhanced_SessionLight.pine` | Overlay (background shading + session name) |
| 06 | `06_Enhanced_HTFStrength.pine`  | Overlay (M15/H1/H4/D1 trend table left-middle) |
| 07 | `07_Enhanced_SetupCard.pine`    | Overlay (Entry + SL1-3 + TP1-3 lines + table) |

## Install (≈ 8 minutes)

1. Open tradingview.com, log in, open a chart (e.g. EURUSD M5).
2. Top bar → **Pine Editor** → **Open** → **New blank indicator**.
3. Paste contents of `01_Enhanced_VWAP.pine` → **Save** → name it
   `GODMODE Enhanced VWAP` → **Add to chart**.
4. Repeat for 02 through 07.
5. Right-click chart → **Indicators and Strategies → Templates tab →
   Save indicator template as → "GODMODE Enhanced"**. Every new chart
   will load all 7 instantly.

## Coexistence with the base TradingView build

The Enhanced indicators are additive. You can run them alongside the base
`tradingview/indicators/01-05_GODMODE_*.pine` indicators — the namespaces
don't clash. Common practice: base build on one chart, Enhanced template
on a second chart of the same symbol, watch both side by side.

## What they consume

These indicators use only built-in Pine v6 functions (`ta.atr`, `ta.ema`,
`request.security`, etc.) — no external library imports, no `ta.requestVolumeDelta`
(which previously caused CE10271 errors and was removed from the base
build). Delta is computed via the close-position proxy, which works on
every symbol in every market.
