# Parameter Tuning — Optimisation Order

Honest framing first: per brief §21.3, win rate is a downstream consequence, not a tuning target. Optimise expectancy and profit factor; refuse to drive on win rate alone.

## Order of operations

Tune in this order. Don't skip ahead.

### 1. Session windows (RiskPct = 0.0, MODE_MANUAL)

Run the EA in MANUAL mode for 5 trading days. Watch which sub-windows produce the most A+ confluences. Default windows from brief §11.6 are:

- LDN_MAIN: 11:00–15:30 SAST
- NY_MAIN: 17:30–21:00 SAST

If your broker's tick stream shows clean order flow during, say, 12:30–14:30 SAST but choppy noise outside that, consider enabling `M6_UseSubWindowTiering = true` and accepting only 5/5 score in TIER B windows.

**Don't** widen the session windows to capture more trades. Wider sessions ≠ better edge.

### 2. VolZThreshold (default 1.5)

This is the absorption-detection floor. Brief §11.4 + §17.2 says delta Z-score >2.0 is institutional, >3.0 is extreme. Volume Z works similarly.

Tuning:

| Value | Effect |
|-------|--------|
| 1.0 | More signals, lower quality, expect win rate ~65% |
| 1.5 (default) | Brief target — 72-78% win rate band |
| 2.0 | Fewer signals, higher quality, expect win rate ~75-80% but trade count drops 30-40% |

Do not optimise this value below 1.0 — you'll start triggering on noise.

### 3. MinAbsorptionStars (default 3)

The 5-component confidence score from brief §11.4. Higher = stricter.

| Value | Effect |
|-------|--------|
| 2 | Brief §22.8 minimum recommended for trading |
| 3 (default) | Brief §17.2 — institutional activity threshold |
| 4 | Conservative — only 4-star+ absorptions, ~50% volume reduction |
| 5 | Almost no setups — extreme absorption only |

The brief calibrates this to 3 because it's the upper edge of what disciplined human execution achieves on order-flow setups.

### 4. LocTolATR (default 0.5)

How close the bar's close must be to a VP level to count as "at" the level. In ATR units.

| Value | Effect |
|-------|--------|
| 0.3 | Tight — only exact-level touches register |
| 0.5 (default) | Brief target — within half an ATR |
| 1.0 | Loose — generates more "near level" hits |

If you backtest and see the EA missing setups where price approached but didn't quite touch VAL, raise to 0.7. If you see false positives where price was near a level but never really tested it, drop to 0.4.

### 5. MinRR (default 2.0)

The minimum reward-to-risk ratio for entry. Hard rejection floor.

| Value | Effect |
|-------|--------|
| 1.5 | More entries, but the marginal trade hovers near coin-flip — Appendix A trap A.1.9 |
| 2.0 (default) | Brief calibration — eliminates negative-EV entries |
| 2.5 | Stricter — drops trade count ~15-20% but average R increases |

Per Appendix A.1.9: cutting marginal-R setups improves both win rate AND average R simultaneously. This is one of the highest-EV tuning moves.

### 6. RiskPct (start 0.5, then 1.0)

The brief defaults this to 1.0 with a hard cap at 2.0 in `RiskManager.Init`. Do not raise above 2.0.

Phased approach:

| Phase | RiskPct | Why |
|-------|---------|-----|
| Backtest | 1.0 | Match the brief's expectancy model |
| Demo forward-test | 0.25 | Quarter size while validating |
| Live first 30 days | 0.5 | Half size while building confidence |
| Live after 30 days, win rate confirmed | 1.0 | Brief default |

Never raise RiskPct because of a winning streak. Brief §21.3 trap "Survivorship".

## Things you should not tune

Per brief §19, the following are non-negotiable and not subject to optimisation:

- Gate ordering (F2 → F5 → location → F3 → F4 → footprint → trigger → score)
- Stop placement rule (1–2 ticks beyond aggression candle, not swing extremes)
- POC exit for Model 2 (70% rule)
- 5% daily DD halt
- 3-consecutive-loss day halt
- 1% per-trade cap (hard-clamped to 2% even if you set higher)
- NY-Open 20-minute blackout
- Session close at 21:00 SAST

If you find yourself wanting to relax any of these, the answer is "no." The brief is the law.

## When to enable the marginal-gain stack (M1–M6)

Per brief §22 and Appendix A.0: do NOT enable any of M1–M6 by default. Earn enablement via your own logged data.

Decision tree:

```
Run base 5-gate system for 100+ trades.
  ├─ Win rate < 70%? → fix the base setup, don't add filters
  ├─ Win rate 70-78%? → at brief target, hold steady
  └─ Win rate ≥ 78%?
        Enable ONE of M1, M2, or M3 (start with M1).
        Run another 100 trades.
          ├─ Win rate stays ≥ 78%? → keep M1, try M2
          ├─ Win rate drops? → disable M1, you over-filtered
          └─ Trade count drops below 5/day? → enable multi-symbol (v1.1)
```

This is the discipline that distinguishes 78% real from 80% noise.

## Diminishing returns

Brief §22.9 stacked-lift estimate is +4 to +6 pp from full M1–M8 stack. Each additional filter contributes less than the last because they overlap. The brief is honest about this — don't over-engineer.

If your CSV log says you're at 78% and adding M3 doesn't move the needle in 100 trades, stop adding filters. The discipline of not adding more is itself part of the edge (Appendix A.8).
