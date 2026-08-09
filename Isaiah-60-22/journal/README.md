# Journal

For the sessions you trade by hand. The EAs write this file for you; this is
the manual equivalent, in the same schema, so hand-traded sessions can be
graded by the same script.

```bash
python3 ../SessionRange_Forge/srf_forensics.py manual-journal-template.csv \
        --target-r 2.0 --variants 1
```

## The columns that actually matter

The schema has 29 columns because the EAs have that much to say. If you are
logging by hand, **six of them are load-bearing** and the rest are context:

| Column | Why it matters |
|---|---|
| `ny_day` | The unit of independence. Two trades on one morning are one bet, and the day-clustered bootstrap needs this to know that. |
| `r_realized` | The result in R. Not dollars — dollars measure your position size, R measures your edge. |
| `risk_points` | The stop distance. Without it the cost-survival gate cannot run. |
| `spread_pts_entry` | The spread you actually paid at entry. This is what makes the cost gate real rather than an assumption. |
| `mfe_r` | How far the trade went your way before it resolved. Tells you whether your target is reachable. |
| `mae_r` | How far it went against you first. Tells you whether your stop is doing work or just being wide. |

Leave a column blank and the script says which gate it had to skip, rather
than quietly guessing. Skipping `spread_pts_entry` disables the gate most
likely to fail — which is a good reason not to skip it.

## The pre-flight checklist

Run this before the session, not during it. If any answer is no, the session is
a no-trade — and a no-trade day is a result you should log too, because
"how often is there no setup" is a real property of a strategy.

### Both strategies

- [ ] I have checked the economic calendar. No high-impact release lands inside
      my entry window.
- [ ] My platform clock and the New York clock agree. I have confirmed which
      one of EST / EDT is currently in force.
- [ ] My risk per trade is set, in R, before I see a chart.
- [ ] I know what my stop invalidates — the level, not a pip count.
- [ ] I have written down what would make me sit out today.

### 9:30 opening range

- [ ] The 09:30–09:35 candle has **closed**. I have not drawn the range early.
- [ ] The range is not abnormally wide against recent ATR.
- [ ] I know the spread I am being quoted right now, and it is not a large
      fraction of my intended stop.
- [ ] My entry window ends at 10:30 and I have accepted that in advance.

### Asian range sweep

- [ ] I wrote down the daily and H4 bias **before** the sweep, not after.
- [ ] The bias is clear. If it is "sort of bullish," it is not clear.
- [ ] The Asian range is a consolidation, not a trend leg in disguise.
- [ ] I have marked the midnight open as well as the range extremes.
- [ ] I will not enter before the sweep, and I will not enter on a wick without
      a structure shift.
- [ ] My stop has the 10–20 pip buffer beyond the swing. Not at it.

## The one rule for the log itself

Write the row when the trade **closes**, not when you feel like it, and write
the losses first. A journal with the bad days missing is worse than no journal:
it will pass gates it should fail, and it will pass them convincingly.
