# GODMODE_OFEA — TradingView Operator Guide

How to read all the indicators together, place a trade based on the signals,
and understand *why* you're placing it. This is the manual that turns the
indicator suite into a discretionary trading workflow.

## The five indicators

| # | File | Pane | Purpose |
|---|------|------|---------|
| 01 | `GODMODE_Dashboard.pine` | Overlay (price chart) | Main 8-gate confluence dashboard top-right. POC/VAH/VAL lines. Session shading. Setup markers. The brain. |
| 02 | `GODMODE_Footprint.pine` | Overlay (right of bars) | Sub-bar footprint cells. Shows aggression direction inside each main bar by aggregating lower-TF bars. |
| 03 | `GODMODE_CVD_Pane.pine` | Sub-window (below price) | Cumulative Volume Delta line with divergence detection. The "buyers vs sellers" running tally. |
| 04 | `GODMODE_Coach.pine` | Overlay (price chart) | Explanatory pop-up labels every time a gate transitions. Your in-chart tutor. |
| 05 | `GODMODE_RiskHelper.pine` | Overlay (price chart) | Lets you click entry/SL prices, draws the SL/TP rectangle, computes lot size. |

Add them in that order to a chart. Save the chart as a Template so every
future chart starts pre-loaded.

## Setup (one-time, ~10 minutes)

1. Open TradingView, log in.
2. Open any chart (start with EURUSD on M5).
3. Top toolbar → **Pine Editor** → **Open** → **New blank indicator**.
4. Paste contents of `01_GODMODE_Dashboard.pine` → click **Save** → name it `GODMODE Dashboard` → **Add to chart**.
5. Repeat for indicators 02 through 05.
6. Once all five are on the chart, right-click the chart → **Indicators and Strategies** → **Templates** tab → **Save indicator template as...** → call it **`GODMODE`**.
7. Future charts: right-click → Templates → **GODMODE** → all five load instantly.

## How to read a setup gate-by-gate

The dashboard top-right shows 8 numbered rows. **Each row is a gate.** A
trade fires only when all 8 dots are green. Read top-down:

### ① State — what type of market are we in?

- **BALANCED** (green) → Model 2 (mean reversion). Trade fades at VAH/VAL.
- **IMBALANCED** (green) → Model 1 (trend). Trade breakouts through LVN.
- **UNKNOWN** (grey) → no signal possible. Wait.

The mode you trade depends on what the profile shape says. Trading the
wrong model is a waste of an A+ setup.

### ② Kill Zone — is the timing right?

- **LDN_MAIN** (green): 11:00–15:30 SAST. Trade Model 2.
- **NY_MAIN** (green): 17:30–21:00 SAST. Trade Model 1.
- **NY_BLACKOUT** (red): first 20 min of NY open. NEVER trade here.
- **ASIAN / AFTER** (grey): low conviction. Default to no trade.

Outside a kill zone, 80% of setups have lower edge. Just wait.

### ③ HTF — are higher timeframes agreeing?

H4 EMA(20) + D1 EMA(50). If both BULL → only take longs. If both BEAR →
only take shorts. If they disagree → NEUTRAL → skip (or halve size).

This single gate adds ~20-25 percentage points of win rate. The bullishness
of a 5-minute spring at VAL is dramatically more reliable when daily is
also bull.

### ④ VP Loc — is price at a meaningful level?

You want price at **POC, VAH, VAL, LVN, or HVN** — not "OUT". A green dot
means price is currently within `LocTolATR × ATR(14)` of one of those
levels.

- **POC** (magenta line on chart): the price-magnet. Watch for rejection.
- **VAH** (blue dashed): value-area high. M2 fades here.
- **VAL** (blue dashed): value-area low. M2 bounces here.
- **LVN**: low-volume node. Price travels through fast. M1 acceleration.
- **HVN**: high-volume node. Strong S/R. Counter-trend bias.
- **MAN:label**: you defined a manual level — operator-curated S/R.

### ⑤ CVD — are buyers/sellers actually delivering?

Look at the CVD pane (indicator 03). If you're considering a LONG, you
want CVD rising or showing a bullish divergence at the price low. SHORT:
opposite.

The dashboard row turns green when CVD slope agrees with the trade. If
it's red — buyers/sellers aren't behind your idea. Skip.

### ⑥ Footprint — is the trigger candle there?

Looks for one of the 11 setup detectors firing on the just-closed bar.
When fired, the dashboard shows the setup name + star rating (e.g.
`AbsBot ★4`). Stars are 0–5; you want ≥ 3.

If still showing `WAITING`, no trigger yet. Don't anticipate — wait for
the trigger.

### ⑦ Aggression — is there an institutional print?

Volume Z-score of ≥ 2.0 on the trigger bar. If the bar that fires the
setup also has a big print, it's an institution stepping in.

A setup without aggression is just retail noise.

### ⑧ R:R — is the trade worth taking?

SL is placed 2 ticks beyond the aggression candle. TP is set to the
opposite VP level (POC for M2 trades, VAH/VAL for M1). If the resulting
R:R is below 2.0, skip — the math doesn't pay even with a 70% win rate.

## The VERDICT cell at the bottom

- **A+ READY** (green) — all 8 gates passed. This is your trade. Click
  the entry on indicator 05 (Risk Helper), confirm the lot size, place
  the order with your broker.
- **WAIT** (amber) — setup formed but gates incomplete. Stay alert; the
  setup might mature, or get blocked.
- **SKIP** (grey) — no setup. Walk away from the chart for 5 minutes.

## What the Coach pop-ups tell you

The Coach indicator (04) paints labels above/below bars every time a gate
transitions. Hover any label for the tooltip with reasoning. Examples:

| Label | Means |
|-------|-------|
| ▶ **KZ active: LDN_MAIN** | Kill zone just opened — start watching for setups. |
| ▶ **VP VAL** | Price just touched VAL — Gate 4 condition met. |
| ▶ **HTF BULL** | H4 + D1 both turned bullish — Gate 3 condition met for longs. |
| ▶ **Bull div** | CVD divergence at price low — high-prob reversal cue. |
| ▶ **AGG 2.4σ** | Volume Z-score spiked — institutional print at this price. |
| ▶ **AbsBot ★4** | Absorption-bottom setup fired with 4-star confidence. |
| ▶ **A+ LONG** (yellow card) | All 8 gates pass. This is the entry trigger. |
| ▶ **AbsBot · BLOCKED** | Setup formed but some gates failed. Tooltip lists which. |

The labels accumulate; the indicator auto-cleans them after 50 bars (you
can adjust). Toggle `LabelDensity` between Verbose / Standard / Minimal
in the Coach settings if you want fewer labels.

## Placing the trade (manual workflow)

Once the dashboard says **A+ READY**:

1. **Note the direction** from the dashboard verdict cell.
2. **Open indicator 05 (Risk Helper) settings.**
3. **Click "Entry price"** in the settings → click on the chart at the
   current close → that fills the input.
4. **Click "SL price"** → click on the chart at the SL level shown by the
   dashboard → that fills the input.
5. **Pick TP mode**: Manual (use the dashboard's TP), ATR multiple, or
   R multiple.
6. The Risk Helper draws the SL/TP rectangle and shows the position size
   in lots in the table at middle-right of chart.
7. **Switch to your broker's order ticket** (separate window/tab).
8. **Enter the order** with the size, entry, SL, TP shown.

Total time: ~20 seconds once you're used to it.

## What to do if the A+ never fires

Brief §22 honesty: A+ setups are rare. Expect 2–5 per day per symbol on
filtered settings. If you're going hours without seeing one:

- ✓ Add more symbols to your watchlist (multi-symbol scanning §23)
- ✓ Check whether your sessions are correctly configured for SAST
- ✗ Don't relax the gate thresholds
- ✗ Don't take WAIT/SKIP setups "just to do something"
- ✗ Don't widen MinRR below 2.0

The discipline of not taking the bad ones is itself part of the edge.

## What to do if the A+ fires but you don't take it

That's MODE_MANUAL working as designed. Brief §0 expects 30 days of
observe-only before flipping to MODE_AUTO. You're allowed to disagree
with the system. **Record why** in a notebook so you can review later:

- Did the A+ work out? (track the outcome in your journal)
- Why did you skip? (HTF context outside what the EA sees? News? Bad gut?)
- After 30 days, do your skips have better or worse outcomes than the
  A+ trades you took? That's your edge calibration.

## Auto-trading via webhook (optional, advanced)

Pine cannot place orders. But it can fire alerts to webhooks. Operators
who want hands-off execution:

1. Subscribe to a webhook-aware automation service:
   - **3Commas** (crypto)
   - **AutoView** (FX/CFD via OANDA, IG, etc.)
   - **Capitalise.ai** (broker-agnostic)
   - **TradingConnector** (MT4/MT5 bridge)
2. On the chart, right-click → **Create Alert**
3. Condition: GODMODE Dashboard → **Any alert() function call**
4. In **Notifications** tab → tick **Webhook URL** → paste your service's URL
5. In the **Message** field, paste a JSON template matching your service's
   format. Example for AutoView:
   ```
   e=oanda b=long s={{ticker}} t=market r=0.5%
   ```
6. Save the alert. Next time N-I fires, the alert hits the webhook, your
   service places the trade.

You're responsible for the brokerage chain. TradingView just emits the
signal.

## The Mac advantage

Pine runs entirely in your browser. **No Windows VM. No .algo
compilation. No Parallels. No drag-and-drop sync.** Just open
tradingview.com on Mac, paste the indicators once, save the template,
trade.

Trade-off: signal quality is materially lower than MT5/cTrader for
order-flow analysis because Pine has no native tick data. The
`volumedelta()` fallback chain in the Dashboard mitigates this on
symbols that expose it (CME futures, some stocks), but for retail FX
the close-position proxy is still the floor. If your symbol is a CME
future (ES, NQ, CL, GC, etc.) you're getting near-MT5 quality on Pine.
If it's a retail FX pair, accept the floor.

## Brief §-mapping (where each piece comes from)

| Brief § | Indicator |
|---------|-----------|
| §2 5-gate stack | 01 Dashboard logic + 04 Coach pop-ups |
| §3 8-row dashboard | 01 Dashboard `table.new()` block |
| §4 N-A..N-L alerts | 01 Dashboard `alert()` calls + 04 Coach labels |
| §5 Execution flow | 01 Dashboard gate ordering |
| §6 25 setup catalogue | 01 Dashboard (subset of 11 wired) |
| §9.1 VP levels | 01 Dashboard plots |
| §9.2 CVD subwindow | 03 CVD Pane |
| §9.3 Footprint markers | 02 Footprint + 01 Dashboard plotshapes |
| §9.4 Session shading | 01 Dashboard bgcolor |
| §9.5 Trade lines | 05 Risk Helper boxes |
| §11.1 Bar delta | 01/03/04 — volumedelta() chain |
| §11.2 Volume profile | 01 Dashboard VP block |
| §11.3 Shape classifier | 01 Dashboard skew + peak |
| §11.4 Absorption stars | 01 Dashboard + 04 Coach |
| §11.5 CVD divergence | 03 CVD Pane |
| §11.6 SAST sessions | 01 Dashboard sastMin() |
| §11.7 HTF alignment | 01 Dashboard request.security() |
| §11.8 Position sizing | 05 Risk Helper |
| §12 Kill switches | Strategy mode only (separate file) |
| §13 Journal | `log.info()` sink + journal sheet (manual) |
| §22 Marginal-gain stack | 01 Dashboard Pace-of-Tape + manual levels |
| §25 External data | 5× manual level slots in 01 Dashboard |
| §26 Pine deviations | This document |
