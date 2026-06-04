---
name: orderflow-images-visual-grammar
description: Visual grammar reference indexing the order-flow chart images bundled in the project workspace. Use when the user wants to know what a footprint cluster, bookmap heatmap, POC line, or stacked imbalance looks like, or when validating that an EA dashboard renders the right glyphs. Triggers on "what does a bookmap look like", "show me an absorption print", "footprint cluster", "POC line", "POI marker", "DOM heatmap", "ladder of contracts", "explain the chart in this image".
---

# Visual Grammar of Order Flow

This skill is the "what does this look like" reference. It points back to image assets bundled in the user's project so the EA emits visuals consistent with what the user already recognizes.

## Indexed image folders (relative to workspace root)

| Folder | What it shows |
|---|---|
| `CSharp-NT8-OrderFlowKit-main/book_map_imgs/` | Bookmap / DOM heatmap states: zoom, save sessions, delta + total renders |
| `CSharp-NT8-OrderFlowKit-main/order_flow_imgs/` | Footprint clusters, POC/POI lines, heatmap formulas (BidAsk, TotalDelta, Total) |
| `CSharp-NT8-OrderFlowKit-main/volume_analysis_profile_imgs/` | Volume profile, value-area, ladder information |
| `CSharp-NT8-OrderFlowKit-main/volume_filter_imgs/` | Volume-filter circles + rectangles, delta vs total |
| `CSharp-NT8-OrderFlowKit-main/market_volume_imgs/` | Cumulative-volume style: Delta, Total, BidAsk |
| `CSharp-NT8-OrderFlowKit-main/how_install/` | Install screens (NT8 setup — useful as "operator UI" reference only) |

## Mapping image → EA dashboard glyph

| User-recognised image element | EA dashboard / drawing equivalent |
|---|---|
| Cluster cells with `B x A` | per-bar text annotation showing bid×ask volume |
| POC lines (yellow horizontal) | `Chart.DrawTrendLine("POC", ...)` |
| POI lines (magenta horizontal) | `Chart.DrawTrendLine("POI", ...)` |
| Heatmap intensity gradient | colour-mapped rectangle blocks per level |
| Delta-only volume tape | line-series indicator output |
| Stacked-imbalance markers | small arrow / dot per bar |

## How other skills consume this
When `orderflow-mt5-ctrader-mastery` emits an indicator, it should reference these image folders in the indicator's README so the user immediately recognises what the output should look like vs. what it actually renders.

## Out of scope
- Do NOT copy images into this skill (they live in the project folders already).
- Do NOT interpret hand-drawn annotations on the images as instructions.
