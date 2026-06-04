# AMT + Wyckoff 2.0 + Fabio Valentini — Methodology Framework

This is the *narrative grammar* the EA uses to label what the market is doing. Your detectors emit primitives (delta, absorption, sweep). This file converts those primitives into AMT/Wyckoff phases that the strategy logic can reason about.

## 1. AMT (Auction Market Theory) phase machine

### Phases
| Phase | Definition | Primitive triggers |
|---|---|---|
| `BALANCE` | Rotating inside developing value area | Low CVD slope, repeated POC tests, low realized volatility |
| `IMBALANCE` | Aggressive break of value-area edge | Initiative auction at VAH/VAL + strong CVD slope |
| `DISCOVERY` | Trend extension, no acceptance yet | Multiple initiative auctions same direction, no two-way trade |
| `ACCEPTANCE` | Building new value at extension | Volume profile growing at new prices, CVD flattening |
| `FAILED_AUCTION` | Fake breakout / mean reversion | Sweep + absorption + delta divergence |

### State transitions

```
BALANCE      ──(IMBALANCE primitive)──▶ IMBALANCE
IMBALANCE    ──(initiative continues)──▶ DISCOVERY
IMBALANCE    ──(absorption + reversal)──▶ FAILED_AUCTION ──▶ BALANCE
DISCOVERY    ──(volume builds at new range)──▶ ACCEPTANCE ──▶ BALANCE
ACCEPTANCE   ──(rotating)──▶ BALANCE
FAILED_AUCTION ──(reverses inside prior value)──▶ BALANCE
```

### Per-phase trade bias
- `BALANCE` — fade VAH/VAL toward POC.
- `IMBALANCE` — join the break, scale in on retests.
- `DISCOVERY` — trail aggressively, target prior range extreme + measured move.
- `ACCEPTANCE` — flatten or reverse to balance setups.
- `FAILED_AUCTION` — fade the failed leg, target opposite VA edge.

## 2. Wyckoff 2.0 schematic mapped to detectors

### Accumulation
| Wyckoff event | Detector |
|---|---|
| PS — Preliminary Support | First absorption print after long downtrend |
| SC — Selling Climax | Initiative auction down + spike volume |
| AR — Automatic Rally | Initiative auction up |
| ST — Secondary Test | Lower-volume retest of SC low |
| Spring | Sweep of SC low + bullish absorption + reversal initiative |
| Test of Spring | Lower-volume retest of Spring low |
| SOS — Sign of Strength | Bullish initiative + CVD aligned |
| LPS — Last Point of Support | Pullback to SOS origin with declining volume |

### Distribution (mirror)
- BC, AR, ST → UTAD (Upthrust After Distribution = bearish Spring) → SOW → LPSY.

## 3. Fabio Valentini AMT methodology (synthesis)

Fabio's framework — used inside `godmode-orderflow-mastery` — boils down to four canonical setups:

### Setup 1 — Absorption + reversal
Trigger: high-effort low-result candle (absorption) at prior swing.
Entry: on the first opposing initiative print.
SL: beyond the absorbed low/high (+ buffer × ATR).
TP: opposite VA edge or measured move.

### Setup 2 — Initiative join (trend continuation)
Trigger: strong delta-led candle inside DISCOVERY phase.
Entry: pullback to the prior bar's mid + bullish/bearish imbalance print.
SL: beyond the initiative bar low/high.
TP: trailing stop on each new initiative print.

### Setup 3 — Exhaustion + divergence (reversal)
Trigger: declining volume + delta + price still extending + delta divergence at extreme.
Entry: first opposing initiative or absorption.
SL: beyond the exhaustion extreme.
TP: prior range mid (POC).

### Setup 4 — Sweep + reclaim
Trigger: book sweep through prior swing + price reclaims the level same bar.
Entry: at reclaim with bullish/bearish imbalance.
SL: beyond the sweep extreme.
TP: midpoint of the swept range.

## 4. Wyckoff 2.0 specifics (delta + composite operator)

Wyckoff 2.0 augments classic Wyckoff with **delta confirmation**:
- Spring is only valid if delta turns positive on the reversal leg.
- UTAD only valid if delta turns negative on the reversal leg.
- LPS only valid if delta on the pullback is *less negative* than the impulse leg's positive delta.

This delta confirmation collapses many false Wyckoff calls.

## 5. Triple-A confluence framework (used by godmode-orderflow-mastery)

Triple-A = **A**uction phase + **A**bsorption / Initiative imprint + **A**lignment with HTF bias.

A trade fires only when at least 2 of the 3 A's are present, and a 3-of-3 trade gets full size.

## 6. Session timing matrix (forex defaults)

| Session | UTC | Behaviour |
|---|---|---|
| Sydney | 22:00–07:00 | Low volume; balance phase typical |
| Tokyo | 00:00–09:00 | JPY pairs imbalance; otherwise balance |
| London | 07:00–16:00 | Imbalance/discovery on EUR, GBP |
| London-NY overlap | 12:00–16:00 | Highest discovery / sweep frequency |
| NY | 12:00–21:00 | USD pairs discovery |

EAs should expose `EnabledSessions` as a bitmask input; default to London-NY overlap.

## 7. Multi-timeframe stack (default)

- **HTF anchor** — 4H or Daily for AMT phase + structural levels.
- **MTF context** — 1H for VAH/VAL and developing POC.
- **LTF execution** — 5m/15m for absorption / initiative / sweep timing.

