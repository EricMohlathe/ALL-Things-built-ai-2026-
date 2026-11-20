# Risk sizing, and the ways it silently fails

Verified on MetaEditor build 5836, and every failure described here was
measured, not imagined.

## The correct calculation

Risk is a percentage of balance divided by the **real** stop distance. Derive
the money value from tick value, never from an assumed pip size, because tick
value is already denominated in the account currency and therefore stays
correct for cross pairs, metals and indices.

```cpp
double CalculateLot(double stopDistancePrice)
{
   if(stopDistancePrice <= 0.0) return(0.0);

   double balance   = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney = balance * InpRiskPercent / 100.0;

   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue <= 0.0 || tickSize <= 0.0) return(0.0);

   double lossPerLot = (stopDistancePrice / tickSize) * tickValue;
   if(lossPerLot <= 0.0) return(0.0);

   return(NormalizeLot(riskMoney / lossPerLot));
}

double NormalizeLot(double lot)
{
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(lotStep <= 0.0) return(0.0);

   lot = MathFloor(lot / lotStep) * lotStep;
   if(lot < minLot) return(0.0);      // refuse rather than risk more than asked
   if(lot > maxLot) lot = maxLot;

   return(NormalizeDouble(lot, 2));
}
```

Rounding **down** to the lot step and refusing below the minimum both matter.
Rounding up, or clamping up to the minimum, quietly risks more than the user
asked for. Returning zero and logging is the honest failure.

## The trap: a percentage can be obeyed exactly and still ruin you

Lot size is risk divided by stop distance. As the stop shrinks toward zero the
lot grows without limit. Percent-of-balance sizing does not protect against
this, because the percentage is still being computed correctly.

**Measured.** A strategy computed its stop from market structure. On one bar
the structural level landed 0.4 pip from the entry. Risking a nominal 0.25% of
a 10,000 account, the sizing maths asked for **6.24 lots**, roughly twenty
times the intended position, and the order went out.

Nothing in the calculation was wrong. The input was.

This is the dangerous shape of bug in trading code: it does not throw, it does
not fail a compile, and the log line looks like every other log line. It only
becomes visible when you read the lot number and it surprises you.

## Two rails, and you want both

**1. A minimum stop distance, enforced by the strategy.**

Any strategy that derives its stop from price structure must reject a stop that
comes out implausibly tight, rather than sizing up to fit it. Scale the floor
to the instrument so it carries over from forex to metals.

```cpp
double minStop = MathMax(InpMinStopAtr * atrDaily,
                         (SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) + 2) * _Point);
if(MathAbs(entry - stop) < minStop)
   return;                            // no trade, not a bigger trade
```

**2. A margin cap, enforced by the safety layer.**

Independent of whatever the strategy believed. This catches the case the first
rail missed.

```cpp
double CapLotByMargin(double lot, const ENUM_ORDER_TYPE type, const double price)
{
   if(lot <= 0.0 || InpMaxMarginPct <= 0.0) return(lot);

   double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   double allowed    = freeMargin * InpMaxMarginPct / 100.0;

   double needed = 0.0;
   if(!OrderCalcMargin(type, _Symbol, lot, price, needed) || needed <= 0.0)
      return(lot);                    // cannot tell, do not silently shrink
   if(needed <= allowed)
      return(lot);

   double capped = NormalizeLot(lot * allowed / needed);
   PrintFormat("Lot cut from %.2f to %.2f. Margin %.2f exceeded %.0f%% of free margin %.2f.",
               lot, capped, needed, InpMaxMarginPct, freeMargin);
   return(capped);
}
```

`OrderCalcMargin` returning false means the terminal could not compute it. Keep
the original lot in that case rather than shrinking on missing information, and
let the broker reject the order if it is genuinely unaffordable.

## How to tell it is working

Read the average loss in the backtest report and divide by the money risked per
trade. It should sit on 1.0 for every sample you look at, and the **largest**
loss should be barely above it. A largest loss well beyond one unit of risk
means either the stop is not being respected or the sizing is being fed a bad
stop distance.

Measured on a working EA across three separate periods: average loss −1.01R,
−1.00R and −0.97R, largest single loss in eighteen months −1.06R. That
tightness is the evidence, not the profit.
