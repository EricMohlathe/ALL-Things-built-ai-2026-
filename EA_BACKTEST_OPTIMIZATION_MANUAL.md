# GODMODE EA Backtest & Optimization Manual (cTrader)

**Scope:** every cBot in [cTrader_MasterLibrary/](cTrader_MasterLibrary/) — GM01 → GM26.
**Reader:** the user, opening cAlgo's Strategy Tester / Optimizer.
**Honesty:** these are *starting* configurations grounded in the brief + the cBot's actual `[Parameter(...)]` defaults, not promises. Run §0.E before trusting any number.

---

## 0. Master settings (apply to every EA)

### 0.A — Account
| Field | Value |
|---|---|
| Account | **Spotware Demo 5824189** (your existing demo) |
| Start Balance | **€200** (mirrors the OFEA backtest baseline) |
| Leverage | **1:100** |
| Hedging | Off (cTrader = netting; that's correct) |

### 0.B — Strategy Tester
| Field | Value |
|---|---|
| Period | **2024-01-01 → 2026-06-01** (24 months) |
| Bar period | **m15** (universal) — except GM09 (**Tick**), GM01 (**m5**), GM17 (**m5**), GM23 (**Daily for gap detection, m15 entry**) |
| Data type | **Tick data from server** (or m1-bar as last resort) |
| Spread | **Variable** (do not override) |
| Commission | Broker default |
| Visual mode | Off (slow); use only to sanity-check one trade |

### 0.C — Universal cBot inputs (same on every GM01–GM26)
| Group | Param | First-pass value |
|---|---|---|
| Risk | Risk Mode | `Conservative` |
| Risk | Risk % Conservative | `1.0` |
| Risk | Risk % Aggressive | `3.0` |
| Risk | Risk % Flip | `8.0` |
| Risk | Max MinLot Risk Mult | `3.0` |
| Session | Offset Hours | **`2` (SAST). All hour inputs below are in SAST.** |
| Manage | BE at R | `1.0` |
| Manage | Partial at R | `1.0` |
| Manage | Partial % | `50` |
| Manage | Use Trail | `false` (turn on per EA — noted) |
| Manage | Trail ATR Mult | `1.5` |
| Guards | Max Daily DD % | `6.0` |
| Guards | Max Consec Losses | `3` |
| Guards | Max Spread Pips | `0` (off first pass; set 2.0 after observing your broker) |

### 0.D — Optimizer setup (cTrader: Strategy Tester → Optimization)
- Algorithm: **Genetic** (Exhaustive only when ≤3 params).
- Optimization criteria: **Net Profit**.
- **Min trades:** `200`.
- Walk-forward: not native in cAlgo — do it manually (see §0.F).
- **Don't optimize:** Risk Mode, Risk %, Offset Hours, Max Daily DD %, Max MinLot Risk Mult. These are policy.

### 0.E — Acceptance gates (keep only if ALL pass)
| Metric | Threshold |
|---|---|
| Trades | ≥ 200 |
| Profit Factor | ≥ 1.5 |
| Expectancy / trade | > 0 R |
| Max Drawdown | ≤ 20% start equity |
| Recovery Factor | ≥ 2.0 |
| Sharpe (info only) | ≥ 1.0 |

### 0.F — Walk-forward (manual)
1. Optimize on **2024-01-01 → 2025-09-01** (~70%, in-sample).
2. Run those exact inputs on **2025-09-01 → 2026-06-01** (~30%, out-of-sample).
3. Keep only if **PF_OOS ≥ 0.7 × PF_IS**. Below 0.5× → curve-fit, discard.

### 0.G — Portfolio
Run final survivors together on the same account, same period. Reject any pair of EAs with **equity-curve correlation |ρ| > 0.6** unless one dominates the other on PF.

---

## 1. GM01 — Opening Range Breakout

**Family:** ORB (Casper, Ginger, JDUB, RP-Profits).
**Symbol / TF:** EURUSD / **m5** (also good: NAS100 m5, XAUUSD m15).

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | OR Start Hour | `17` (SAST = 15:00 UTC = NY equity open) |
| Session | OR Start Minute | `30` |
| Session | OR Duration Min | `15` |
| Session | Trade End Hour | `23` |
| Session | Force Close Hour | `24` |
| Entry | Reverse | `false` |
| Entry | SL Type | `0` (opposite range) |
| Entry | ATR Mult SL | `2.0` |
| Entry | ATR Period | `14` |
| Entry | Reward:Risk | `2.0` |
| Entry | SL Padding Pips | `1.0` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Reward:Risk | 1.5 | 3.5 | 0.25 |
| ATR Period | 10 | 20 | 2 |
| ATR Mult SL | 1.0 | 3.0 | 0.5 |
| SL Type | 0 | 2 | 1 |
| OR Duration Min | 10 | 30 | 5 |
| BE at R | 0.5 | 2.0 | 0.25 |

---

## 2. GM02 — Session Sweep → Reclaim (Judas / CRT / PO3)

**Family:** ICT, TJR Asia Sweep.
**Symbol / TF:** EURUSD m15, GBPUSD m15.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Range Start Hour | `2` (Asia begin SAST) |
| Session | Range End Hour | `8` (London open SAST) |
| Session | Trade Start Hour | `8` |
| Session | Trade End Hour | `13` |
| Session | Force Close Hour | `14` |
| Entry | Require Reclaim | `true` |
| Entry | SL Type | `0` (swept extreme) |
| Entry | ATR Mult SL | `1.5` |
| Entry | ATR Period | `14` |
| Entry | SL Padding Pips | `1.0` |
| Entry | TP Type | `0` (opposite edge) |
| Entry | Reward:Risk | `2.5` |
| Entry | Min R:R | `1.5` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Reward:Risk | 1.5 | 4.0 | 0.25 |
| Min R:R | 1.0 | 2.0 | 0.25 |
| ATR Period | 10 | 20 | 2 |
| Range End Hour | 7 | 10 | 1 |
| Trade End Hour | 11 | 14 | 1 |
| BE at R | 0.5 | 2.0 | 0.25 |

---

## 3. GM03 — FVG Entry

**Family:** ICT FVG mitigation.
**Symbol / TF:** EURUSD m15, GBPUSD m15.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Use Session | `true` |
| Session | Trade Start Hour | `8` |
| Session | Trade End Hour | `22` |
| Session | Force Close Hour | `23` |
| Entry | FVG Lookback | `20` |
| Entry | Min Gap Pips | `2.0` |
| Entry | Use EMA Bias | `true` |
| Entry | EMA Period | `50` |
| Entry | ATR Period | `14` |
| Entry | SL Padding Pips | `1.0` |
| Entry | Reward:Risk | `2.0` |
| Entry | Max Trades/Day | `2` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| FVG Lookback | 10 | 30 | 5 |
| Min Gap Pips | 1.0 | 5.0 | 0.5 |
| EMA Period | 20 | 200 | 20 |
| Reward:Risk | 1.5 | 3.5 | 0.25 |
| Max Trades/Day | 1 | 4 | 1 |
| BE at R | 0.5 | 2.0 | 0.25 |

---

## 4. GM04 — Order Block Return

**Family:** ICT/SMC.
**Symbol / TF:** EURUSD m15, NAS100 m15.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Trade Start Hour | `8` |
| Session | Trade End Hour | `22` |
| Session | Force Close Hour | `23` |
| Entry | OB Lookback | `30` |
| Entry | Displacement xATR | `0.8` |
| Entry | ATR Period | `14` |
| Entry | Use EMA Bias | `true` |
| Entry | EMA Period | `50` |
| Entry | SL Padding Pips | `1.0` |
| Entry | Reward:Risk | `2.0` |
| Entry | Max Trades/Day | `2` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| OB Lookback | 15 | 50 | 5 |
| Displacement xATR | 0.5 | 1.5 | 0.1 |
| EMA Period | 20 | 200 | 20 |
| Reward:Risk | 1.5 | 3.5 | 0.25 |
| BE at R | 0.5 | 2.0 | 0.25 |

---

## 5. GM05 — ICT Unicorn (OB + FVG overlap)

**Symbol / TF:** EURUSD m15, GBPUSD m15.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Trade Start Hour | `9` |
| Session | Trade End Hour | `19` |
| Session | Force Close Hour | `20` |
| Entry | Lookback | `30` |
| Entry | Displacement xATR | `0.8` |
| Entry | ATR Period | `14` |
| Entry | Use EMA Bias | `true` |
| Entry | EMA Period | `50` |
| Entry | SL Padding Pips | `1.0` |
| Entry | Reward:Risk | `2.5` |
| Entry | Max Trades/Day | `2` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Lookback | 15 | 50 | 5 |
| Displacement xATR | 0.6 | 1.4 | 0.1 |
| EMA Period | 20 | 200 | 20 |
| Reward:Risk | 1.5 | 4.0 | 0.25 |
| BE at R | 0.5 | 2.0 | 0.25 |

---

## 6. GM06 — Wyckoff Spring / Upthrust

**Symbol / TF:** EURUSD m15, XAUUSD m15.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Trade Start Hour | `8` |
| Session | Trade End Hour | `22` |
| Session | Force Close Hour | `23` |
| Entry | Range Length | `20` |
| Entry | Range Start Shift | `2` |
| Entry | Max Range xATR | `4.0` |
| Entry | ATR Period | `14` |
| Entry | SL Padding Pips | `1.0` |
| Entry | TP Type | `0` (opposite edge) |
| Entry | Reward:Risk | `2.5` |
| Entry | Min R:R | `1.5` |
| Entry | Max Trades/Day | `2` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Range Length | 12 | 30 | 2 |
| Max Range xATR | 2.5 | 6.0 | 0.5 |
| Reward:Risk | 1.5 | 4.0 | 0.25 |
| TP Type | 0 | 1 | 1 |
| BE at R | 0.5 | 2.0 | 0.25 |

---

## 7. GM07 — VWAP Mean Reversion

**Symbol / TF:** EURUSD m15, NAS100 m15.
**Notes:** native cAlgo VWAP not standard; cBot uses session VWAP. Pair best with ranging days.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Trade Start Hour | `10` |
| Session | Trade End Hour | `19` |
| Session | Force Close Hour | `20` |
| Entry | Band SD | `2.0` |
| Entry | Require Rejection | `true` |
| Entry | ATR Period | `14` |
| Entry | SL ATR Mult | `1.0` |
| Entry | TP Type | `0` (VWAP) |
| Entry | Reward:Risk | `1.5` |
| Entry | Min R:R | `1.0` |
| Entry | Max Trades/Day | `3` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Band SD | 1.5 | 3.0 | 0.25 |
| SL ATR Mult | 0.5 | 2.0 | 0.25 |
| Reward:Risk | 1.0 | 2.5 | 0.25 |
| TP Type | 0 | 1 | 1 |
| Max Trades/Day | 1 | 5 | 1 |

---

## 8. GM08 — Momentum Displacement

**Symbol / TF:** EURUSD m15, GBPJPY m15, XAUUSD m15.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Trade Start Hour | `9` |
| Session | Trade End Hour | `22` |
| Session | Force Close Hour | `23` |
| Entry | Range xATR | `1.5` |
| Entry | Min Body % | `0.6` |
| Entry | Max Opposing Wick % | `0.25` |
| Entry | ATR Period | `14` |
| Entry | Use EMA Bias | `true` |
| Entry | EMA Period | `50` |
| Entry | SL ATR Mult | `1.5` |
| Entry | Reward:Risk | `2.0` |
| Entry | Max Trades/Day | `3` |
| Manage | Use Trail | **`true`** (default for this EA) |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Range xATR | 1.0 | 2.5 | 0.25 |
| Min Body % | 0.4 | 0.8 | 0.1 |
| Max Opposing Wick % | 0.1 | 0.4 | 0.05 |
| SL ATR Mult | 1.0 | 2.5 | 0.25 |
| Reward:Risk | 1.5 | 3.5 | 0.25 |
| Trail ATR Mult | 1.0 | 3.0 | 0.25 |

---

## 9. GM09 — Order Flow Absorption (TICK ONLY)

**Symbol / TF:** EURUSD **Tick**.
**MANDATORY:** Strategy Tester data type = **Tick data from server**. Anything else = synthetic ticks = noise (reproduces the original blow-up).

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Trade Start Hour | `10` |
| Session | Trade End Hour | `19` |
| Session | Force Close Hour | `20` |
| Entry | Delta Lookback | `20` |
| Entry | Vol Z Threshold | `1.5` |
| Entry | Use Absorption | `true` |
| Entry | Use CVD Divergence | `true` |
| Entry | ATR Period | `14` |
| Entry | SL ATR Mult | `1.0` |
| Entry | Reward:Risk | `2.0` |
| Entry | Max Trades/Day | `3` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Delta Lookback | 10 | 40 | 5 |
| Vol Z Threshold | 1.0 | 3.0 | 0.25 |
| SL ATR Mult | 0.5 | 2.0 | 0.25 |
| Reward:Risk | 1.5 | 3.0 | 0.25 |
| Use Absorption | 0 | 1 | 1 |
| Use CVD Divergence | 0 | 1 | 1 |

---

## 10. GM10 — Power of 3 / CRT + CISD

**Symbol / TF:** EURUSD m15, GBPUSD m15.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Range Start Hour | `2` |
| Session | Range End Hour | `8` |
| Session | Trade Start Hour | `8` |
| Session | Trade End Hour | `14` |
| Session | Force Close Hour | `15` |
| Entry | Require CISD | `true` |
| Entry | SL Padding Pips | `1.0` |
| Entry | TP Type | `1` (SD projection) — try `0` and `2` in opt |
| Entry | SD Mult | `1.0` |
| Entry | Reward:Risk | `2.5` |
| Entry | Min R:R | `1.5` |
| Entry | ATR Period | `14` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| TP Type | 0 | 2 | 1 |
| SD Mult | 0.5 | 2.5 | 0.25 |
| Reward:Risk | 1.5 | 4.0 | 0.25 |
| Range End Hour | 7 | 10 | 1 |
| Require CISD | 0 | 1 | 1 |
| BE at R | 0.5 | 2.0 | 0.25 |

---

## 11. GM11 — Silver Bullet (macro windows)

**Symbol / TF:** EURUSD m5 or m15, NAS100 m5.
**Note:** EA uses three **window** pairs, not a single Trade Start/End. Hours below in SAST.

### Inputs
| Group | Param | Value |
|---|---|---|
| Windows | W1 Enable | `true` |
| Windows | W1 Start | `12` (London SB 10–11 UTC = 12–13 SAST) |
| Windows | W1 End | `13` |
| Windows | W2 Enable | `true` |
| Windows | W2 Start | `16` (NY AM SB 14–15 UTC = 16–17 SAST) |
| Windows | W2 End | `17` |
| Windows | W3 Enable | `false` (Asia SB — only enable for crypto/Asia FX) |
| Windows | W3 Start | `5` |
| Windows | W3 End | `6` |
| Windows | Force Close Hour | `24` |
| Entry | Sweep Lookback | `12` |
| Entry | FVG Lookback | `8` |
| Entry | Min Gap Pips | `1.5` |
| Entry | SL Padding Pips | `1.0` |
| Entry | Reward:Risk | `2.0` |
| Entry | ATR Period | `14` |
| Entry | Max Trades/Day | `2` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Sweep Lookback | 8 | 20 | 2 |
| FVG Lookback | 5 | 15 | 2 |
| Min Gap Pips | 1.0 | 3.0 | 0.25 |
| Reward:Risk | 1.5 | 3.5 | 0.25 |
| W3 Enable | 0 | 1 | 1 |

---

## 12. GM12 — Optimal Trade Entry (Fib 0.62–0.79)

**Symbol / TF:** EURUSD m15, GBPUSD m15.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Trade Start Hour | `8` |
| Session | Trade End Hour | `22` |
| Session | Force Close Hour | `23` |
| Entry | Swing Lookback | `20` |
| Entry | Use EMA Bias | `true` |
| Entry | EMA Period | `50` |
| Entry | Require FVG | `false` |
| Entry | FVG Lookback | `15` |
| Entry | SL Padding Pips | `1.0` |
| Entry | TP Type | `0` (swing origin) |
| Entry | Reward:Risk | `2.0` |
| Entry | Min R:R | `1.5` |
| Entry | ATR Period | `14` |
| Entry | Max Trades/Day | `2` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Swing Lookback | 10 | 40 | 5 |
| EMA Period | 20 | 200 | 20 |
| Require FVG | 0 | 1 | 1 |
| FVG Lookback | 10 | 25 | 5 |
| Reward:Risk | 1.5 | 3.5 | 0.25 |
| TP Type | 0 | 1 | 1 |

---

## 13. GM13 — Price Action (Pin / Engulf)

**Symbol / TF:** EURUSD m15, XAUUSD m15.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Trade Start Hour | `8` |
| Session | Trade End Hour | `22` |
| Session | Force Close Hour | `23` |
| Signals | Use Pin | `true` |
| Signals | Use Engulf | `true` |
| Signals | Use EMA Bias | `true` |
| Signals | EMA Period | `50` |
| Signals | SL Padding Pips | `1.0` |
| Signals | Reward:Risk | `2.0` |
| Signals | ATR Period | `14` |
| Signals | Max Trades/Day | `3` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Use Pin | 0 | 1 | 1 |
| Use Engulf | 0 | 1 | 1 |
| EMA Period | 20 | 200 | 20 |
| Reward:Risk | 1.5 | 3.5 | 0.25 |
| Max Trades/Day | 1 | 5 | 1 |
| BE at R | 0.5 | 2.0 | 0.25 |

---

## 14. GM14 — Turtle Soup / SFP

**Symbol / TF:** EURUSD m15, NAS100 m15.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Trade Start Hour | `8` |
| Session | Trade End Hour | `22` |
| Session | Force Close Hour | `23` |
| Entry | Swing Lookback | `30` |
| Entry | Swing Wing | `2` |
| Entry | Use EMA Bias | `false` |
| Entry | EMA Period | `50` |
| Entry | SL Padding Pips | `1.0` |
| Entry | Reward:Risk | `2.0` |
| Entry | ATR Period | `14` |
| Entry | Max Trades/Day | `3` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Swing Lookback | 15 | 50 | 5 |
| Swing Wing | 1 | 4 | 1 |
| Use EMA Bias | 0 | 1 | 1 |
| Reward:Risk | 1.5 | 3.5 | 0.25 |
| Max Trades/Day | 2 | 5 | 1 |

---

## 15. GM15 — Supply & Demand

**Symbol / TF:** EURUSD m15, XAUUSD m15.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Trade Start Hour | `8` |
| Session | Trade End Hour | `22` |
| Session | Force Close Hour | `23` |
| Entry | Zone Lookback | `30` |
| Entry | Displacement ATR Mult | `1.2` |
| Entry | Base Max ATR Mult | `0.6` |
| Entry | Use EMA Bias | `true` |
| Entry | EMA Period | `50` |
| Entry | SL Padding Pips | `1.0` |
| Entry | Reward:Risk | `2.0` |
| Entry | ATR Period | `14` |
| Entry | Max Trades/Day | `3` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Zone Lookback | 20 | 60 | 5 |
| Displacement ATR Mult | 0.8 | 2.0 | 0.2 |
| Base Max ATR Mult | 0.3 | 1.0 | 0.1 |
| EMA Period | 20 | 200 | 20 |
| Reward:Risk | 1.5 | 3.5 | 0.25 |

---

## 16. GM16 — Market Structure (BOS / CHoCH)

**Symbol / TF:** EURUSD m15, GBPUSD m15.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Trade Start Hour | `8` |
| Session | Trade End Hour | `22` |
| Session | Force Close Hour | `23` |
| Entry | Structure Lookback | `40` |
| Entry | Swing Wing | `2` |
| Entry | Mode | `0` (BOS continuation) — try `1` (CHoCH reversal) in opt |
| Entry | SL Padding Pips | `1.0` |
| Entry | Reward:Risk | `2.0` |
| Entry | ATR Period | `14` |
| Entry | Max Trades/Day | `3` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Mode | 0 | 1 | 1 |
| Structure Lookback | 20 | 80 | 10 |
| Swing Wing | 1 | 4 | 1 |
| Reward:Risk | 1.5 | 3.5 | 0.25 |
| BE at R | 0.5 | 2.0 | 0.25 |

---

## 17. GM17 — Initial Balance

**Symbol / TF:** NAS100 **m5**, ES m5, EURUSD m5.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | IB Start Hour | `17` (SAST = 15:00 UTC = NY equity open) |
| Session | IB End Hour | `18` |
| Session | Trade End Hour | `23` |
| Session | Force Close Hour | `24` |
| Entry | SL Padding Pips | `2.0` |
| Entry | SL = opposite IB edge | `false` |
| Entry | Reward:Risk | `2.0` |
| Entry | ATR Period | `14` |
| Entry | Max Trades/Day | `2` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| IB Start Hour | 15 | 18 | 1 |
| IB End Hour | 16 | 19 | 1 |
| SL = opposite IB edge | 0 | 1 | 1 |
| Reward:Risk | 1.5 | 3.5 | 0.25 |
| SL Padding Pips | 1.0 | 5.0 | 0.5 |

---

## 18. GM18 — Harmonic (XABCD)

**Symbol / TF:** EURUSD m15, GBPUSD m15, XAUUSD H1.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Trade Start Hour | `8` |
| Session | Trade End Hour | `22` |
| Session | Force Close Hour | `23` |
| Entry | Swing Lookback | `120` |
| Entry | Swing Wing | `3` |
| Entry | Ratio Tolerance | `0.09` |
| Entry | Max D Age Bars | `5` |
| Entry | PRZ ATR Mult | `1.0` |
| Entry | SL Padding Pips | `2.0` |
| Entry | Reward:Risk | `2.0` |
| Entry | ATR Period | `14` |
| Entry | Max Trades/Day | `2` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Swing Lookback | 60 | 200 | 20 |
| Swing Wing | 2 | 5 | 1 |
| Ratio Tolerance | 0.05 | 0.15 | 0.01 |
| Max D Age Bars | 2 | 10 | 1 |
| PRZ ATR Mult | 0.5 | 2.0 | 0.25 |
| Reward:Risk | 1.5 | 4.0 | 0.25 |

---

## 19. GM19 — Connors RSI(2) Mean Reversion

**Symbol / TF:** SPX/ES m15, NAS100 m15, EURUSD m15.
**Note:** designed for equity-index style mean reversion in a long-EMA trend.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Trade Start Hour | `8` |
| Session | Trade End Hour | `22` |
| Session | Force Close Hour | `23` |
| Entry | RSI Period | `2` |
| Entry | RSI Oversold | `10.0` |
| Entry | RSI Overbought | `90.0` |
| Entry | Trend EMA Period | `200` |
| Entry | SL ATR Mult | `2.0` |
| Entry | Reward:Risk | `1.5` |
| Entry | ATR Period | `14` |
| Entry | Max Trades/Day | `3` |
| Manage | BE at R | `0.0` (off — let MR run to TP) |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| RSI Period | 2 | 4 | 1 |
| RSI Oversold | 5 | 25 | 5 |
| RSI Overbought | 75 | 95 | 5 |
| Trend EMA Period | 100 | 300 | 25 |
| SL ATR Mult | 1.0 | 3.0 | 0.25 |
| Reward:Risk | 1.0 | 2.5 | 0.25 |

---

## 20. GM20 — Gap Fade / Gap Go

**Symbol / TF:** NAS100 m15, US30 m15, US500 m15 (equities have real gaps; FX doesn't).
**Note:** **set MaxWeeklyGap** by enabling Monday gap detection — gap mostly fires Mondays in FX, daily in indices.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Session Start Hour | `17` (SAST = NY equity open) |
| Session | Entry Window Hours | `3` |
| Session | Force Close Hour | `24` |
| Entry | Mode | `0` (Fade) — try `1` (Gap Go) in opt |
| Entry | Min Gap ATR Mult | `0.8` |
| Entry | SL ATR Mult | `1.5` |
| Entry | Reward:Risk | `2.0` (only used when Mode=1) |
| Entry | ATR Period | `14` |
| Entry | Max Trades/Day | `1` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Mode | 0 | 1 | 1 |
| Min Gap ATR Mult | 0.4 | 2.0 | 0.2 |
| SL ATR Mult | 1.0 | 2.5 | 0.25 |
| Reward:Risk | 1.5 | 3.0 | 0.25 |
| Entry Window Hours | 2 | 6 | 1 |

---

## 21. GM21 — Prev-Day / Prev-Week H/L

**Symbol / TF:** EURUSD m15, GBPUSD m15, XAUUSD m15.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Trade Start Hour | `9` |
| Session | Trade End Hour | `22` |
| Session | Force Close Hour | `23` |
| Entry | Use PDH/PDL | `true` |
| Entry | Use Prev-Week H/L | `false` (turn on for daily TF) |
| Entry | SL Padding Pips | `1.0` |
| Entry | Reward:Risk | `2.0` |
| Entry | ATR Period | `14` |
| Entry | Max Trades/Day | `2` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Use PDH/PDL | 0 | 1 | 1 |
| Use Prev-Week H/L | 0 | 1 | 1 |
| Reward:Risk | 1.5 | 3.5 | 0.25 |
| SL Padding Pips | 0.5 | 3.0 | 0.5 |
| BE at R | 0.5 | 2.0 | 0.25 |

---

## 22. GM22 — EMA Pullback

**Symbol / TF:** EURUSD m15, GBPUSD m15, NAS100 m15.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Trade Start Hour | `9` |
| Session | Trade End Hour | `22` |
| Session | Force Close Hour | `23` |
| Entry | Fast EMA | `20` |
| Entry | Slow EMA | `50` |
| Entry | SL Padding Pips | `1.0` |
| Entry | Reward:Risk | `2.0` |
| Entry | ATR Period | `14` |
| Entry | Max Trades/Day | `3` |
| Manage | Use Trail | **`true`** (default for this EA) |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Fast EMA | 8 | 30 | 2 |
| Slow EMA | 40 | 100 | 10 |
| Reward:Risk | 1.5 | 3.5 | 0.25 |
| Trail ATR Mult | 1.0 | 3.0 | 0.25 |
| BE at R | 0.5 | 2.0 | 0.25 |

---

## 23. GM23 — NDOG / NWOG (Opening Gap CE)

**Symbol / TF:** EURUSD m15, NAS100 m15.
**Notes:** detection uses Daily/Weekly bars; entry on m15. CE = consequent encroachment = gap midpoint.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Trade Start Hour | `2` |
| Session | Trade End Hour | `22` |
| Session | Force Close Hour | `23` |
| Entry | Min Gap ATR Mult | `0.5` |
| Entry | SL Padding Pips | `2.0` |
| Entry | Reward:Risk | `2.0` |
| Entry | ATR Period | `14` |
| Entry | Max Trades/Day | `1` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Min Gap ATR Mult | 0.3 | 1.5 | 0.1 |
| Reward:Risk | 1.5 | 3.5 | 0.25 |
| SL Padding Pips | 1.0 | 4.0 | 0.5 |
| BE at R | 0.5 | 2.0 | 0.25 |

---

## 24. GM24 — SMT Divergence (correlated pair)

**Symbol / TF:** EURUSD m15 (with GBPUSD as the correlated symbol).
**Notes:** **Other Symbol must be subscribed** in cTrader's MarketWatch (you can't backtest against a symbol that isn't loaded).

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Trade Start Hour | `9` |
| Session | Trade End Hour | `19` |
| Session | Force Close Hour | `20` |
| Entry | Correlated Symbol | `"GBPUSD"` |
| Entry | Positive Correlation | `true` |
| Entry | Window Bars | `12` |
| Entry | SL Padding Pips | `1.0` |
| Entry | Reward:Risk | `2.0` |
| Entry | ATR Period | `14` |
| Entry | Max Trades/Day | `2` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Window Bars | 6 | 30 | 2 |
| Positive Correlation | 0 | 1 | 1 |
| Reward:Risk | 1.5 | 3.5 | 0.25 |
| BE at R | 0.5 | 2.0 | 0.25 |

**Other pairs to test:** EUR/USD ↔ GBP/USD (positive); USD/CHF ↔ EUR/USD (negative — set PosCorr=false); XAU ↔ DXY (negative).

---

## 25. GM25 — Breakout-Retest

**Symbol / TF:** EURUSD m15, NAS100 m15, XAUUSD m15.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Trade Start Hour | `9` |
| Session | Trade End Hour | `22` |
| Session | Force Close Hour | `23` |
| Entry | Range Lookback | `20` |
| Entry | Retest Tol Pips | `2.0` |
| Entry | Max Wait Bars | `8` |
| Entry | SL Padding Pips | `1.0` |
| Entry | Reward:Risk | `2.0` |
| Entry | ATR Period | `14` |
| Entry | Max Trades/Day | `3` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Range Lookback | 12 | 40 | 4 |
| Retest Tol Pips | 1.0 | 5.0 | 0.5 |
| Max Wait Bars | 4 | 16 | 2 |
| Reward:Risk | 1.5 | 4.0 | 0.25 |
| BE at R | 0.5 | 2.0 | 0.25 |

---

## 26. GM26 — Confluence Stack (the meta-edge)

**Symbol / TF:** EURUSD m15, GBPUSD m15.
**Hard rule:** keep `Min Layers ≥ 4`. This is the whole edge — lowering it makes it a generic trend EA.

### Inputs
| Group | Param | Value |
|---|---|---|
| Session | Trade Start Hour | `9` |
| Session | Trade End Hour | `18` |
| Session | Force Close Hour | `20` |
| Confluence | Min Layers | `4` |
| Confluence | Layer: Trend EMA | `true` |
| Confluence | Layer: FVG | `true` |
| Confluence | Layer: Zone | `true` |
| Confluence | Layer: Swing Sweep | `true` |
| Confluence | Layer: Session | `true` |
| Confluence | Layer: Momentum | `true` |
| Params | EMA Period | `50` |
| Params | FVG Lookback | `15` |
| Params | Zone Lookback | `30` |
| Params | Swing Lookback | `30` |
| Params | Swing Wing | `2` |
| Params | Displacement ATR Mult | `1.0` |
| Params | Base Max ATR Mult | `0.6` |
| Params | SL ATR Mult (fallback) | `1.5` |
| Params | SL Padding Pips | `1.0` |
| Params | Reward:Risk | `2.0` |
| Params | ATR Period | `14` |
| Params | Max Trades/Day | `3` |

### Optimize
| Param | Min | Max | Step |
|---|---|---|---|
| Min Layers | 4 | 6 | 1 |
| EMA Period | 20 | 200 | 20 |
| FVG Lookback | 10 | 25 | 5 |
| Zone Lookback | 20 | 60 | 5 |
| Swing Lookback | 20 | 50 | 5 |
| Displacement ATR Mult | 0.6 | 1.6 | 0.2 |
| Reward:Risk | 1.5 | 4.0 | 0.25 |
| SL ATR Mult (fallback) | 1.0 | 2.5 | 0.25 |

**Tip:** also run a sweep with each individual layer toggled `false` (one at a time) to learn which layer is doing the work.

---

## 27. Suggested first-pass order (today / this week)

Run these five **first** — they're the "expected higher win-rate band" candidates from the honest ranking:

1. **GM26 Confluence Stack** (the meta — baseline truth-check).
2. **GM19 RSI(2)** (mean-rev classic).
3. **GM14 Turtle Soup / SFP**.
4. **GM07 VWAP Mean Reversion**.
5. **GM12 OTE**.

Then the trend-continuation cluster:
6. GM22 EMA Pullback.
7. GM04 OB Return.
8. GM03 FVG Entry.
9. GM05 ICT Unicorn.
10. GM25 Breakout-Retest.

Then session-anchored:
11. GM02 Sweep Reversal.
12. GM10 PO3/CRT.
13. GM11 Silver Bullet.
14. GM01 ORB.
15. GM17 Initial Balance.

Then the rest (GM06, GM08, GM13, GM15, GM16, GM18, GM20, GM21, GM23, GM24). **GM09 last** — only after you have tick data confirmed.

---

## 28. Notes

- Every EA writes a CSV journal to `~/Documents/GODMODE_GMxx_*_log.csv`. After the run, open the file — it logs **entries AND skips**. If skips ≫ entries (10:1), filters are too tight; loosen *one* knob, not all.
- Backtester results show **gross win rate** — read in conjunction with **Profit Factor** and **Expectancy**, not in isolation.
- Risk Mode = `Conservative` always for testing. Promote to `Aggressive` only after the EA clears §0.E. **Never test in `Flip`** — that mode is for live-only conviction trades after you trust the system.
- For the SAST timezone — set `Offset Hours = 2` once at the top of each cBot's input panel; then all hour fields above are SAST hours.

---

**End. Run, log, rank by PF, repeat.**
