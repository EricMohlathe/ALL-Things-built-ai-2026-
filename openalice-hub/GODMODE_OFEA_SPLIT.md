# GODMODE OFEA — Split Plan (decompose the monolith)

`GODMODE_OFEA..cs` is one 1,573-line cBot that scores **25 setups** into a single
counter and fires ≤1 trade/bar. Per the MASTER COMPENDIUM, that's *why the backtest
is un-diagnosable*: winners and losers share one equity curve. The fix is to rebuild
each setup as its **own EA with its own log**, then backtest/win-rate/rank in isolation.

The 25 setups are now registered (`registry/godmode_setups.json`) and listed by
`python3 hub.py godmode`. Each is tagged by **where it can honestly be tested**:

## Where each setup can be backtested
| Bucket | Count | Setups | How |
|---|---|---|---|
| 🟢 Hub OHLCV proxy | 9 | Spring, Upthrust, SOS, LPSY, LiqSweep, ObReturn, Breaker, AMD, PoorHL | price-structure → `hub.py backtest` (proxy) |
| 🟡 Hub approx VP | 6 | ValBnc, VahFade, PocRet, LvnLong, LvnShort, HvnRej | volume-profile from OHLCV (coarse) |
| 🔴 cTrader only | 10 | AbsBot, AbsTop, CvdBull, CvdBear, StackBull, StackBear, PullStack, UnfAuc, Iceberg | need tick/delta/footprint |
| 🔵 Multi-symbol | (in 🔴) | SMTDiv | needs a correlated 2nd feed |

> A hub proxy is a *price-only approximation* of the cBot's logic — useful for a fast
> relative read, **not** a substitute for the real per-setup cBot in cTrader's Strategy
> Tester. Truth = isolate the actual `[Parameter]` cBot and test it.

## The cut-list (one EA per setup)
For each `SetupId` (line 298) the monolith already has a detector
(`SetupDetectors.<Code>`) and an `EnableSetup_NN_*` flag (line 1459+). To split:
1. Create `GM_OFEA_NN_<Code>.cs` — a minimal cBot that calls **only** that one
   `SetupDetectors.<Code>` + the shared risk/management code.
2. Give it its own journal (entry **and skip**) so per-setup win-rate is measurable.
3. Backtest each in cAlgo per `EA_BACKTEST_OPTIMIZATION_MANUAL.md`; rank by real win-rate.
4. Auto-disable any setup whose rolling win-rate decays (compendium §22.8).

## Honest scope
This step **enumerated + categorized + registered** the 25 setups and gave the cut-list.
It did **not** auto-generate 25 compiling C# cBots — that's a real C# refactor (shared
modules, parameters, per-setup journals) best done one setup at a time against the
compendium's Part 7 map. The hub now tracks all 25 and can proxy-backtest the 9
price-structure ones today:
```
python3 hub.py godmode                       # list all 25, bucketed
python3 hub.py backtest donchian BTCUSDT     # closest proxy for breakout-family setups
```
