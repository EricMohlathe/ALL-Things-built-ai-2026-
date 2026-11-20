# EA lifecycle, indicator handles, new bar

Verified by compile on 2026-08-05, MetaEditor build 5836.

---

## Skeleton

```cpp
#property copyright "..."
#property version   "1.00"

#include <Trade\Trade.mqh>

input long   InpMagic    = 20260805;
input double InpRiskPct  = 1.0;
input int    InpMaPeriod = 20;

CTrade   trade;
int      maHandle    = INVALID_HANDLE;
datetime lastBarTime = 0;

int OnInit()
{
   maHandle = iMA(_Symbol, PERIOD_CURRENT, InpMaPeriod, 0, MODE_SMA, PRICE_CLOSE);
   if(maHandle == INVALID_HANDLE)
   {
      Print("Failed to create MA handle, error ", GetLastError());
      return(INIT_FAILED);
   }

   trade.SetExpertMagicNumber(InpMagic);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   if(maHandle != INVALID_HANDLE)
      IndicatorRelease(maHandle);
}

void OnTick()
{
   // work here
}
```

Note there is no `#property strict`. That is MQL4 only and the agent adds it
out of habit.

---

## Indicator handles

The rule that breaks most generated code: **in MQL5 an indicator function
returns a handle, not a value.**

```cpp
// WRONG. This is MQL4. iMA returns a handle, so this cannot compile,
// and even corrected it would leak a handle on every tick.
double ma = iMA(_Symbol, PERIOD_H1, 20, 0, MODE_SMA, PRICE_CLOSE, 0);
```

Correct: create once, read many, release once.

```cpp
// in OnInit
maHandle = iMA(_Symbol, PERIOD_CURRENT, InpMaPeriod, 0, MODE_SMA, PRICE_CLOSE);
if(maHandle == INVALID_HANDLE)
   return(INIT_FAILED);

// in OnTick
double ma[];
ArraySetAsSeries(ma, true);
if(CopyBuffer(maHandle, 0, 0, 3, ma) < 3)
{
   Print("CopyBuffer failed, error ", GetLastError());
   return;                 // not enough bars yet, try again next tick
}
// ma[0] current bar, ma[1] previous, ma[2] the one before

// in OnDeinit
if(maHandle != INVALID_HANDLE)
   IndicatorRelease(maHandle);
```

Always check the `CopyBuffer` return. Early in a backtest, and after a
reconnect, there are simply not enough bars yet. Returning is correct; treating
an empty array as zeros is not.

---

## New bar detection

Most strategies act on closed bars. Without this an EA re-evaluates and often
re-enters on every tick.

```cpp
datetime lastBarTime = 0;   // global

void OnTick()
{
   datetime cur = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(cur == lastBarTime)
      return;               // still inside the same bar
   lastBarTime = cur;

   // runs exactly once per bar
}
```

If the strategy genuinely needs tick-by-tick behaviour, say so explicitly in
the strategy file. Defaulting to it is almost always a mistake.

Note `lastBarTime` is deliberately not persisted. After a restart it is zero,
so the first tick is treated as a new bar. That is the safe direction: the EA
re-evaluates rather than silently skipping a bar. Anything that must survive a
restart belongs in `state-and-restart.md`.

---

## Deinit reasons

```cpp
void OnDeinit(const int reason)
{
   // REASON_PROGRAM, REASON_REMOVE, REASON_RECOMPILE, REASON_CHARTCHANGE,
   // REASON_PARAMETERS, REASON_ACCOUNT, REASON_TEMPLATE, REASON_INITFAILED,
   // REASON_CLOSE
   if(maHandle != INVALID_HANDLE)
      IndicatorRelease(maHandle);
}
```

Release handles unconditionally. Do not close positions here: `OnDeinit` runs
when the chart template changes or the EA recompiles, and closing on those
would be a disaster on a live account.
