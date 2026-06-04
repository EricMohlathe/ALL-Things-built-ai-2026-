# GODMODE_OFEA — TradingView Quick Reference Cheat Sheet

Print this. Tape it next to your monitor. Read in 30 seconds.

## Dashboard rows (top-right) at a glance

```
╔═══════════════════════════════════════╗
║ GODMODE — EURUSD · MANUAL  Δ: subTF   ║   ← title bar
║ ① State        ●  BALANCED            ║   ← profile state (Model 1 vs 2)
║ ② Kill Zone    ●  LDN_MAIN            ║   ← timing (session)
║ ③ HTF          ●  BULL                ║   ← higher-timeframe bias
║ ④ VP Loc       ●  VAL                 ║   ← location (POC/VAH/VAL/LVN/HVN)
║ ⑤ CVD          ●  BULL                ║   ← buyer/seller delivery
║ ⑥ Footprint    ●  AbsBot ★4           ║   ← trigger candle + stars
║ ⑦ Aggression   ●  2.4σ★               ║   ← institutional print
║ ⑧ R:R          ●  3.4:1               ║   ← reward vs risk
║ CONF           5/5                    ║   ← total confluence
║ Pace-of-Tape   0.87                   ║   ← tape velocity (>0.85 active)
║ POC/VAH/VAL    1.0867/1.0892/1.0830   ║   ← VP levels live
║ SL → TP        1.0822 → 1.0867        ║   ← geometry
║ Risk %         0.5%                   ║   ← current setting
║ VERDICT        A+ READY               ║   ← what to do
╚═══════════════════════════════════════╝
```

## Verdict cell decoder

| Cell shows | Meaning | Action |
|------------|---------|--------|
| **A+ READY** (green) | All 8 gates pass | Enter the trade |
| **WAIT** (amber) | Setup formed but ≥ 1 gate failing | Watch this bar — gate may flip |
| **SKIP** (grey) | No setup | Step away, don't force |

## Coach pop-up symbols decoded

These appear above/below bars on the chart. Each has a hover tooltip with detail.

| Symbol | Means |
|--------|-------|
| ▶ **KZ active: XXX** | Kill zone XXX just started |
| ▶ **VP XXX** | Price reached VP level XXX |
| ▶ **HTF XXX** | H4 + D1 both aligned XXX direction |
| ▶ **State: XXX** | Profile classified as XXX |
| ▶ **Bull div** / **Bear div** | CVD diverging from price extreme |
| ▶ **AGG X.Xσ** | Volume Z-score spiked (institutional print) |
| ▶ **XXX ★N** | Setup XXX fired with N-star confidence |
| ▶ **A+ LONG/SHORT** (yellow card) | All gates pass — enter trade |
| ▶ **XXX · BLOCKED** | Setup formed but gates incomplete |

## Footprint cell colors (indicator 02)

The 5 cells stacked to the right of each main bar:

| Color | Means |
|-------|-------|
| Bright green | Bull-aggressive sub-bar (buyers crossing the offer) |
| Bright red | Bear-aggressive sub-bar (sellers crossing the bid) |
| Dim green/red | Same direction, normal size |
| Highlighted (saturated) | Stacked imbalance — institutional aggression |

## CVD pane (indicator 03)

| What you see | Means |
|--------------|-------|
| Green line rising | Buyers in control |
| Red line falling | Sellers in control |
| Yellow MA line | Smoothed trend |
| Green triangle up | Bullish divergence (price LL, CVD HL) |
| Red triangle down | Bearish divergence (price HH, CVD LH) |
| Purple circle | Aggression spike (vol Z ≥ 2.0) |
| Top-right table | Vol Z, Delta Z, Bar Δ, source |

## The 5-gate-stack short version

```
F1  Triple Confluence  →  VP × Footprint × Kill Zone
F2  Kill Zone Discipline → only LDN_MAIN or NY_MAIN
F3  HTF Alignment       → H4 + D1 must both agree
F4  CVD Confirmation    → CVD slope must match trade direction
F5  Volume Profile State → BALANCED→M2, IMBALANCED→M1
```

Missing one → skip. Missing two → not even worth looking.

## Setup card (when A+ fires)

Click the yellow A+ card on the chart, hover for tooltip:

```
■ A+ READY · LONG · AbsBot
Entry: 1.08340
SL:    1.08220
TP:    1.08670
R:R:   3.4:1
★:     4/5
HTF:   BULL
```

Use these numbers in the Risk Helper (indicator 05) to compute lot size.

## Manual trade execution (10 seconds)

1. Yellow A+ card appears.
2. Open Risk Helper settings → click chart to set Entry → click chart to set SL.
3. Read lot size from the table.
4. Open broker, enter order with that size + Entry + SL + TP.
5. Walk away. Trade managed itself by SL/TP.

## Manual key levels (replace external data bridges)

Indicator 01 → Settings → "Manual key levels" group. Up to 5 levels with
labels. Operator types in significant prices (weekly opens, prior IB high,
pivot levels, etc.). Lines plot on chart. Dashboard recognises proximity
and bonuses GATE 3.

Update these weekly. They're your equivalent of the Sierra Chart / Google
Sheets bridge from MT5/cTrader §25.

## Daily routine (operator's checklist)

**Pre-session (5 min):**
- [ ] Update manual key levels for the day (prior day H/L, weekly open, news levels)
- [ ] Update RiskPct if equity changed
- [ ] Confirm session toggles match what you want to trade
- [ ] Note any high-impact news in your calendar

**During session (passive):**
- [ ] Glance at dashboard every 5-15 min
- [ ] When A+ pops, you have ~1-2 bars to decide → take or skip
- [ ] Record skips in a notebook with the reason

**Post-session (10 min):**
- [ ] Review the Pine Log pane for the day's A+ events (paste into spreadsheet)
- [ ] Note which were taken, which were skipped
- [ ] Tally wins/losses
- [ ] Update equity input for tomorrow

## Hard prohibitions (brief §19, still apply)

- ✗ Never raise RiskPct above 2.0 (hard-clamped anyway)
- ✗ Never place SL at obvious swing high/low — 1-2 ticks beyond aggression candle
- ✗ Never override the F1-F5 stack to "feel" a trade
- ✗ Never take WAIT or SKIP setups
- ✗ Never trade NY_BLACKOUT period (first 20 min of NY)
- ✗ Never pyramid (one open position max, default config)

## When to suspect Pine is misleading you

Pine's delta is a proxy. The Dashboard top-right shows the source:

- **`Δ: volumedelta()`** → near-MT5 quality. Trust it.
- **`Δ: sub-TF`** → moderate quality. Sanity-check against price action.
- **`Δ: proxy`** → close-position only. Treat all OF signals with extra
  scepticism. Consider switching to MT5 on Mac for that symbol.

CME futures (ES, NQ, CL, GC, ZB, ZN, ZS, ZW): `volumedelta()` works.
Crypto on Binance/Coinbase: `volumedelta()` works.
Retail FX (most brokers): `volumedelta()` does NOT work — falls back to sub-TF or proxy.

## Brief acceptance test (§18 user story)

Open EURUSD M5, attach all 5 indicators, save template. Wait for an A+
LONG setup at VAL during London Main. Dashboard verdict reads **A+ READY**.
A yellow card appears on the chart with entry/SL/TP. The Coach has painted
8 supporting labels above the prior 5 bars. The CVD pane shows a bullish
divergence triangle. The Footprint cells show stacked green at the trigger
bar.

You take the trade with the Risk Helper. SL hits the magenta POC line in
your favor 40 minutes later. You close at +2.7R. You journal it.

That's the acceptance moment per brief §18 — fully reproducible in
TradingView with these five indicators.

## Help index

| Question | Answer |
|----------|--------|
| Where is the source code? | `tradingview/indicators/*.pine` in the repo |
| How do I update an indicator? | Open Pine Editor → load the saved indicator → paste new code → Save → click "Update on chart" |
| How do I move all indicators to a new chart? | Right-click → Templates → GODMODE → applies all 5 |
| Why is my CVD flat? | Symbol doesn't expose `volumedelta()` and sub-TF aggregation isn't available. Switch source manually to "Close-position proxy" |
| How do I add a 6th manual level? | Increase the manual-levels inputs in 01_GODMODE_Dashboard.pine source → paste back |
| How do I get the journal CSV? | Pine Log pane → copy lines starting with "A+ ENTRY" → paste into Excel |
| Can I trade on autopilot? | Yes via webhook alerts + a 3rd-party automation service. See Operator Guide |
| Why is the lot size wrong? | Check `PipValue` and `AcctEquity` inputs in Risk Helper. EURUSD on USD acct ≈ $10/lot/pip |
