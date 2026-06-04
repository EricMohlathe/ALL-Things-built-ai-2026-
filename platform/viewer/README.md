# Viewer — Phase 1 Vertical Slice

A zero-build static HTML viewer that renders bar candles + GODMODE_OFEA
gate annotations from the engine's JSON event stream.

This is the **vertical-slice taste-test** for the platform: it proves the
engine output is consumable by a UI without committing to Tauri/React/etc.
The full WebGL chart canvas (WBS 2.3) and Tauri shell (WBS 2.1) are Phase-2
work; this viewer is the bridge.

## Run it

```bash
# 1. Generate an event stream from any bar CSV
cd ../godmode_engine
cargo run --release --bin godmode-replay -- \
    --bars samples/eurusd_m15_sample.csv \
    > /tmp/events.jsonl

# 2. Open the viewer
cd ../viewer
python3 -m http.server 8080      # or any static file server
# then open http://localhost:8080/ in a browser

# 3. In the viewer:
#    - Click "Load bars.csv" → choose ../godmode_engine/samples/eurusd_m15_sample.csv
#    - Click "Load events.jsonl" → choose /tmp/events.jsonl
```

Alternatively click **Demo** to see the viewer rendering a synthetic dataset
without any backend interaction.

## What's rendered

| Element | Source | Meaning |
|---------|--------|---------|
| Candles | bars.csv | OHLC per bar |
| Magenta solid line | latest `Dashboard` event | POC |
| Blue dashed lines | latest `Dashboard` event | VAH / VAL |
| Green dot above bar | `N-I` notification | A+ entry ready |
| Orange triangle above bar | `Order` event | Order placed (AUTO mode) |
| Red dot above bar | `N-L_*` notification | Kill switch |
| Sidebar: dashboard | latest `Dashboard` snapshot | Mirrors §3 panel |
| Sidebar: gate trace | last 9 `Gate` events | What just happened |
| Sidebar: notifications | last 12 `Notify` events | The cascade in action |
| Sidebar: counts | all events | Event-type totals |

## Why this isn't WebGL yet

WBS 2.3 (WebGL canvas at 60 FPS, 50k candles) is a Phase-2 deliverable
estimated at 5 dev-days. This Phase-1 viewer is plain Canvas2D in <300
lines of JS — enough to inspect a 1-day replay, not enough to scrub
50k-bar history. That's intentional: ship a working slice now, swap in
the WebGL renderer when the rest of the app shell lands.

## Limitations

- Event-to-bar mapping is heuristic. The CLI emits events bar-by-bar but
  doesn't tag them with a bar index in the JSON. The viewer buckets
  events evenly — works fine for visual sanity-checking, not precise
  enough for click-on-event drill-down.
- No replay scrubber. Phase 2 (WBS 2.10) wires the scrubber across all
  panels.
- No real-time tick stream. Reads static files. Phase 4 (broker adapters)
  introduces live data.

## Files

```
viewer/
├── index.html    # layout + style
├── viewer.js     # parsing, rendering, demo data — no deps
└── README.md     # this file
```

No `package.json`, no node_modules. Open in a browser.
