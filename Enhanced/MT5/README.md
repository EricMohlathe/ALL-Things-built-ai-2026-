# Enhanced/MT5 — install on Windows MT5

## Folder mapping (one-to-one to `MQL5\`)

| Source path here | Destination in MT5 |
|------------------|--------------------|
| `Experts/GODMODE_OFEA_Enhanced/GODMODE_OFEA_Enhanced.mq5` | `MQL5\Experts\GODMODE_OFEA_Enhanced\` |
| `Include/OF_*.mqh`                                       | `MQL5\Include\` (loose — not in a subfolder) |
| `Indicators/GODMODE_*.mq5`                               | `MQL5\Indicators\GODMODE\` |

## Install (10 minutes)

1. Open MetaEditor → File → Open Data Folder → opens `MQL5\`.
2. Copy each `Include/OF_*.mqh` to `MQL5\Include\` (alongside the base build's `OF_*.mqh`).
3. Create `MQL5\Experts\GODMODE_OFEA_Enhanced\` and copy `GODMODE_OFEA_Enhanced.mq5` in.
4. Create `MQL5\Indicators\GODMODE\` and copy all `Indicators\GODMODE_*.mq5` into it.
5. In MetaEditor, open each `.mq5` and press **F7** (Compile). Look for `0 errors, 0 warnings` at the bottom.
6. In MT5, **Navigator → Indicators → GODMODE** — double-click each to attach.
7. **Navigator → Expert Advisors → GODMODE_OFEA_Enhanced** — drag onto chart. In the
   Common tab tick "Allow Algo Trading"; click OK.

## Verifying the visuals

Once attached, the chart should show, in order:

1. **GODMODE Confluence Dashboard** (top-left) — 12 numbered rows + Probability bar + Setup card.
2. **GODMODE VWAP** — yellow line with two aqua bands (±1σ) and two purple bands (±2σ).
3. **GODMODE Delta Bars** (separate window) — bar-delta histogram + yellow CVD line + magenta climax markers.
4. **GODMODE Bid/Ask Spread** — live spread monitor (mid-left).
5. **GODMODE Price Action Labels** — BOS↑/BOS↓ tags, dashed equal-H/L lines, FVG rectangles.
6. **GODMODE Session Light** — coloured square + current session name (bottom area).
7. **GODMODE HTF Strength** — M15/H1/H4/D1 with ▲/▼ arrows and ADX bars.

If anything fails to show, see the smoke-test in `../docs/smoke_test.md` (or the
base build's troubleshooting in the main README).
