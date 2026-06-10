# Strategy cross-talk: what works (measured, this repo's data)

| mode | example | verdict |
|---|---|---|
| **Voting** (co-sign entries) | gm_confluence (5 setups vote) | ✅ WF survivor +33% |
| **Gating** (one vetoes another) | gm_gated (checklist gates confluence) | ❌ WF −49% — starves the edge |
| **Portfolio** (each trades its market, capital combines) | deity_trend GOLD + archon_orb NQ 50/50 | ✅ **Sharpe 0.92 > both solos (0.76 / 0.60)**, +120.6%, maxDD −17.3% |

Diversification is the only "free lunch": uncorrelated edges smooth each other's drawdowns,
so the combined risk-adjusted return EXCEEDS every component. That is strategies "talking"
at the only level that reliably pays — capital allocation, not signal contamination.

gm_confluence note: it survives WALK-FORWARD (re-fit per fold) but not fixed params over
1000 days → trade it with quarterly re-optimization (godmode-rank), then add as 3rd leg.
