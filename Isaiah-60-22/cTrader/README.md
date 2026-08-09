# cTrader build — Isaiah 60:22

Two cBots, each a single self-contained file. No shared library, because
cTrader's Automate editor compiles one robot per file and a dropped-in `.cs`
should just build.

| File | Strategy |
|---|---|
| `Isaiah6022_NY0930_ORB.cs` | Strategy 01 — the 9:30 NY opening range |
| `Isaiah6022_AsianSweep.cs` | Strategy 02 — the Asian range liquidity sweep |

## Install

1. cTrader → **Automate** → **New cBot**.
2. Delete the template contents, paste the file, rename the cBot to match the
   class name.
3. **Build (F6).**
4. Add an instance, pick your symbol, set parameters, **Start**.

The robots declare `AccessRights = AccessRights.FullAccess` because they write
the journal CSV. cTrader will prompt for this the first time. Setting
`Write journal CSV = false` removes the need, and also removes the only way to
grade the strategy — do not.

## The clock advantage

Both robots declare `TimeZone = TimeZones.UTC`, so `Server.Time` is UTC and the
conversion to New York applies the real US daylight-saving rule directly.

**There is no broker-offset input to get wrong.** This is a genuine advantage
over the MT5 build for session strategies, and it is the reason the cTrader
version is the better one to trust when the two disagree about *when* a
session starts.

Everything else about the clock — which windows, why they wrap midnight, why
the Asian range belongs to the following session — is in
`../strategies/00-session-clock.md` and applies identically.

## First run

**ORB:**
```
Entry model     = BreakDirect
Bias filter     = Off            (get a baseline before filtering)
Risk % of equity= 0.5
Target in R     = 2.0
Run tag         = orb_direct_ct_v1     ← change every run
```

**Sweep:**
```
Entry model     = SweepMss
Bias filter     = HtfEma         (not optional on this strategy)
No bias, no trade = true
Max trades per session = 1
Run tag         = asian_sweep_ct_v1
```

## Backtest settings

- **Data:** tick data from the server, not m1 bars
- **Commission and spread:** your account's real values
- **Period:** two years minimum

## The journal

Written to your **Documents** folder as `I22_ORB_journal.csv` /
`I22_Sweep_journal.csv`, using the same schema as the MT5 build:

```bash
python3 ../SessionRange_Forge/srf_forensics.py \
        ~/Documents/I22_ORB_journal.csv --target-r 2.0 --variants 1
```

Same script, same gates, either platform. That is deliberate — see Part 4 of
`../strategies/03-risk-and-evidence-protocol.md` for what it buys you.

## The falsification run

**ORB:** re-run with `Entry model = Retest`, everything else identical.

**Sweep:** re-run with `Bias filter = Off` and `No bias, no trade = false`,
everything else identical. This is the most informative backtest in the
workspace: if the bias filter does not improve the result, the sweep carries no
directional information on your instrument.

## Pip conventions

The cTrader build states distances in **pips** where the MT5 build uses
**points**. This is not an inconsistency to fix, it is each platform's native
unit. It matters in exactly two places:

| Input | MT5 | cTrader |
|---|---|---|
| Stop buffer beyond the MSS swing | `InpStopBufferPts = 150` (points) | `StopBufferPips = 15.0` (pips) |
| Max spread | `InpMaxSpreadPts = 30` (points) | `MaxSpreadPips = 3.0` (pips) |

On a 5-digit forex symbol one pip is ten points, so those pairs are equivalent.
On gold and indices, check your symbol's `PipSize` before assuming.

## Notes

- **Labels** are `I22_ORB` and `I22_SWEEP`. Each robot manages only its own
  positions, so both can run on one account.
- **Both robots drive off `OnTick`** with explicit new-bar detection on the
  entry timeframe, rather than `OnBar`. That way the chart timeframe you
  attach to has no effect on the signals — only the `Entry timeframe`
  parameter does.
