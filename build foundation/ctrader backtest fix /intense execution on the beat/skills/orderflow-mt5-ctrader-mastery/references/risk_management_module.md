# Risk-Management Module

The risk module is non-optional. Every EA emitted must wire ALL of the following gates before any signal can fire an entry.

## Risk gates (evaluated in order)

1. **Connection healthy** — broker connected, depth feed alive (if used).
2. **Symbol tradable** — market open, not in `MARKET_CLOSED`.
3. **Spread guard** — current spread ≤ `InpMaxSpread`.
4. **Daily-loss kill switch** — equity drawdown today < `InpMaxDailyLossPct`.
5. **Total drawdown halt** — equity drawdown from peak < `InpMaxTotalDrawdownPct`.
6. **Max concurrent positions** — open EA-tagged positions < `InpMaxPositions`.
7. **Cooldown** — minutes since last close ≥ `InpCooldownMin`.
8. **News halt** — outside news-blackout window (`InpNewsHaltMinutes` around event).
9. **Session filter** — within enabled trading hours / sessions.
10. **Day-of-week filter** — within `InpEnabledDays` bitmask.

## Position sizing — fixed-risk

```
riskMoney  = balance * riskPct/100
slDistance = abs(entryPrice - slPrice)
units      = riskMoney / (slDistance * pipValuePerUnit)
units      = clamp(units, minVolume, maxVolume) and round to volume step
```

MQL5 implementation: see `mql5_orderflow_patterns.md §8`.
cAlgo implementation: see `ctrader_calgo_patterns.md §8`.

## Trade management — universal rules

| Stage | Action | Trigger |
|---|---|---|
| BE move | move SL to entry + `InpBEBufferPts` | price reaches entry + `InpBEDistancePts` |
| Partial 1 | close `InpPartial1Pct` of size | price reaches entry + `InpTP1Pts` |
| Partial 2 | close `InpPartial2Pct` of remainder | price reaches entry + `InpTP2Pts` |
| Trailing | `SL = max(SL, recentSwingLow − bufferPts)` | every new bar after BE |
| Time stop | close if not hit BE within `InpTimeStopMinutes` | bar timestamp diff |

## Configurable risk profiles

Expose presets via a single enum input:
```
enum RiskProfile { CONSERVATIVE, STANDARD, AGGRESSIVE, PROP_FIRM };
```

| Profile | Risk % | Max daily loss | Max DD | Cooldown |
|---|---|---|---|---|
| CONSERVATIVE | 0.25% | 1.5% | 5% | 30 min |
| STANDARD | 0.50% | 3.0% | 8% | 15 min |
| AGGRESSIVE | 1.00% | 5.0% | 12% | 5 min |
| PROP_FIRM | 0.40% | 4.0% | 8% | 10 min |

## Anti-patterns the EA must refuse

- No SL.
- Martingale / grid sizing without `InpAllowGrid = true` AND a hard daily-loss halt.
- Position size > 5% of equity per trade.
- Risk-of-ruin > 1% under default Monte Carlo (compute once at init, log it).

