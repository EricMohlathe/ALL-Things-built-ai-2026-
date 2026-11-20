# When the EA never trades

A backtest reporting zero trades tells you nothing about *which* condition
refused. For a strategy with two conditions you can guess. For one with ten you
cannot, and guessing costs a full compile and test cycle each time.

Instrument the refusals instead. This is cheap, it belongs in the EA rather
than in a debugger, and it turns a day of guessing into one run.

## Counter per gate, tally at the end

```cpp
#define DIAG_COUNT 8
long   g_diag[DIAG_COUNT];
string g_diagName[DIAG_COUNT] =
{
   "outside trading hours", "not enough history", "spread too wide",
   "no signal", "wrong side of the trend filter", "stop too tight",
   "reward to risk below minimum", "daily limit reached"
};

// In the signal function, every early exit is numbered.
if(nowMinute < InpFromMinute) { g_diag[0]++; return(false); }
if(bars < 300)                { g_diag[1]++; return(false); }
// ...

void PrintDiagnostics()
{
   long total = 0;
   for(int i = 0; i < DIAG_COUNT; i++) total += g_diag[i];
   if(total == 0) return;

   Print("--- where signals were refused, in bars ---");
   for(int i = 0; i < DIAG_COUNT; i++)
      if(g_diag[i] > 0)
         PrintFormat("  %-32s %8d  %5.1f%%",
                     g_diagName[i], (int)g_diag[i], 100.0 * g_diag[i] / total);
}

void OnDeinit(const int reason) { PrintDiagnostics(); }
```

Real output from a strategy that had produced zero trades:

```
--- where setups were refused, in bars ---
  outside trading hours              4845   33.9%
  bias balanced                      2778   19.4%
  against the higher timeframe       2556   17.9%
  no liquidity raid                  3968   27.7%
  break the wrong way                  98    0.7%
  stop too tight                       15    0.1%
```

The counters are **sequential**, so each one only sees what the previous ones
let through. Read them that way: of the bars that reached the fourth gate, 96%
died there. That is the bottleneck, and everything before it is background.

## Zero trades does not mean zero orders

Check this before changing any logic. In MetaTrader a *trade* is a position
that opened. A pending order that was placed and expired unfilled contributes
nothing to the trade count.

A strategy entering on limit orders can place a dozen and fill none, and the
report will say zero trades exactly as if the entry conditions never fired.
Those are completely different problems with completely different fixes.

Count them separately from the log:

```powershell
$placed  = @($log | Where-Object { $_ -match 'BUY|SELL limit' }).Count
$expired = @($log | Where-Object { $_ -match 'order expired' }).Count
```

Measured on one strategy: 18 orders placed, 8 filled. Reading only the trade
count would have sent the search into the entry conditions, which were fine.

## Log the reason on every rejection in the order layer

Counters cover the signal. The order layer needs sentences, because each
rejection there has a specific and different fix.

```cpp
PrintFormat("Setup skipped: reward to risk %.2f below %.2f. %s", rr, InpMinRR, reason);
PrintFormat("Setup skipped: buy limit %.*f is not below ask %.*f by the stops level.",
            _Digits, entry, _Digits, ask);
```

Grouping those lines afterwards tells you immediately whether the problem is
the target rule, the entry price, or the broker's minimum distance.

## Change one thing per run

Make every threshold an input, then vary them from the command line rather than
by editing and recompiling. Editing source to test a threshold is slow and, on
MetaTrader specifically, unreliable: without a parameter file the tester ignores
your compiled defaults entirely. See `scripts/backtest.ps1`, note 8.

```powershell
.\scripts\backtest.ps1 -Expert "MyEA.ex5" -Symbol EURUSD -Period M5 `
    -From 2025.02.01 -To 2026.08.01 -Inputs @{ InpUseTrendFilter = $false }
```
