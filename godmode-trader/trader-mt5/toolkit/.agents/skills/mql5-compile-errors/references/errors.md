# Compile error catalogue

One entry per error actually encountered. Original message, cause, fix.

Add to this file every time a new error appears. Keep entries short.

---

## error 256: undeclared identifier 'Ask'

**Context:** agent wrote `double spread = Ask - Bid;`
**Cause:** `Ask` and `Bid` are MQL4 predefined variables. MQL5 has no such
globals. Prices are read from the symbol.
**Fix:**

```cpp
// wrong
double spread = Ask - Bid;

// right
double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
double spread = ask - bid;
```

For the spread in points, prefer the symbol property directly:

```cpp
long spreadPoints = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
```

**Recorded:** 2026-08-05

---

## error 256: undeclared identifier 'OP_BUY'

**Context:** `OrderSend(Symbol(), OP_BUY, ...)`
**Cause:** `OP_BUY`, `OP_SELL`, `OP_BUYLIMIT` and friends are MQL4 constants.
**Fix:** MQL5 uses `ORDER_TYPE_BUY`, `ORDER_TYPE_SELL`,
`ORDER_TYPE_BUY_LIMIT`, and so on, inside `MqlTradeRequest.type`. With `CTrade`
you do not name the type at all, you call `trade.Buy()` or `trade.Sell()`.
**Recorded:** 2026-08-05

---

## error 256: undeclared identifier 'SELECT_BY_POS' / 'MODE_TRADES'

**Context:** MQL4 order loop.
**Cause:** both constants belong to MQL4's `OrderSelect`.
**Fix:** iterate positions instead. See skill `mql5-patterns`,
`references/state-and-restart.md`.
**Recorded:** 2026-08-05

---

## error 256: undeclared identifier 'OrderClose' / 'OrderTicket'

**Cause:** MQL4 functions. They do not exist in MQL5 in any form.
**Fix:** `CTrade::PositionClose(ticket)`, and read the ticket from
`PositionGetTicket(index)`.
**Recorded:** 2026-08-05

---

## error 256: undeclared identifier '<invented name>'

**Context:** the agent called `CheckMarketConditionSafely()`, which does not
exist anywhere.
**Cause:** a plausible sounding function name was generated rather than
recalled. This is the failure mode that makes the automated compile loop
necessary, because nothing else detects it.
**Fix:** write the helper yourself, or use a real API. Never emit a function
name you are not sure about.
**Recorded:** 2026-08-05

---

## error 199: wrong parameters count, at OrderSend

**Context:**

```cpp
int ticket = OrderSend(Symbol(), OP_BUY, 0.1, Ask, 3, 0, 0, "test", 0, 0, clrGreen);
```

**Cause:** the MQL4 eleven-parameter signature. MQL5 takes two.
**MetaEditor said:** `built-in: bool OrderSend(const MqlTradeRequest&,MqlTradeResult&)`
**Fix:** fill an `MqlTradeRequest`, or use `CTrade`. See skill `mql5-patterns`.
**Recorded:** 2026-08-05

---

## error 199: wrong parameters count, at iMA

**Context:**

```cpp
double ma = iMA(NULL, 0, 20, 0, MODE_SMA, PRICE_CLOSE, 0);
```

**Cause:** the trailing `shift` parameter is MQL4 only. More importantly the
return value is a handle, not a price, so even a correct call cannot be
assigned to a `double`.
**MetaEditor said:** `built-in: int iMA(const string,ENUM_TIMEFRAMES,int,int,ENUM_MA_METHOD,int)`
**Fix:**

```cpp
// global
int maHandle = INVALID_HANDLE;

int OnInit()
{
   maHandle = iMA(_Symbol, PERIOD_CURRENT, 20, 0, MODE_SMA, PRICE_CLOSE);
   if(maHandle == INVALID_HANDLE)
      return(INIT_FAILED);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   if(maHandle != INVALID_HANDLE)
      IndicatorRelease(maHandle);
}

void OnTick()
{
   double ma[];
   ArraySetAsSeries(ma, true);
   if(CopyBuffer(maHandle, 0, 0, 3, ma) < 3)
      return;
   // ma[0] is the current bar
}
```

Never call `iMA` inside `OnTick`. It creates a new handle every tick, leaks
resources, and slows the tester until it stalls.
**Recorded:** 2026-08-05

---

## error 106: file 'Trade\Trade.mqh' not found

**Context:** compiling a source file that lives outside the MT5 data folder.
**Cause:** MetaEditor resolves angle-bracket includes against its own data
folder, whose path contains a hash derived from the executable location. A
MetaEditor copied to a new path invents a brand new empty data folder.
**Fix:** not a code change. Pass the include root:

```
MetaEditor64.exe /compile:"<file>" /log /include:"<...>\MQL5"
```

`/inc:` and `/portable` also work. `compile.ps1` reads the path from
`config/paths.json`.
**Recorded:** 2026-08-05

---

## error 246: cannot convert parameter 'double' to 'double&[]'

**Context:**

```cpp
double buffer;
CopyBuffer(maHandle, 0, 0, 3, buffer);
```

**Cause:** `CopyBuffer` fills an array. A single `double` is not an array.
**MetaEditor said:** `built-in: int CopyBuffer(int,int,int,int,double&[])`
**Fix:**

```cpp
double buffer[];
ArraySetAsSeries(buffer, true);
if(CopyBuffer(maHandle, 0, 0, 3, buffer) < 3)
   return;
```

The same error appears for `CopyRates`, `CopyTime`, `CopyClose` and every other
Copy function. They all write into arrays.
**Recorded:** 2026-08-05

---

## error 262: cannot convert enum

**Context:** `PositionGetDouble(i, POSITION_PROFIT)` inside a position loop.
**Cause:** two mistakes at once. `PositionGetDouble` takes only the property,
because the position must already be selected. And passing the loop index where
an enum belongs is a type error.
**MetaEditor said:**
```
built-in: double PositionGetDouble(ENUM_POSITION_PROPERTY_DOUBLE)
built-in: bool PositionGetDouble(ENUM_POSITION_PROPERTY_DOUBLE,double&)
```
**Fix:**

```cpp
for(int i = PositionsTotal() - 1; i >= 0; i--)
{
   ulong ticket = PositionGetTicket(i);   // selects the position
   if(ticket == 0) continue;
   double profit = PositionGetDouble(POSITION_PROFIT);
}
```

**Recorded:** 2026-08-05

---

## error 256: undeclared identifier 'magicnumber'

**Context:** `request.magicnumber = 12345;`
**Cause:** the `MqlTradeRequest` field is `magic`, not `magicnumber`. Close
enough to sound right, which is exactly why it gets generated.
**Fix:** `request.magic = 12345;`

Field names on `MqlTradeRequest` worth remembering: `action`, `magic`, `order`,
`symbol`, `volume`, `price`, `stoplimit`, `sl`, `tp`, `deviation`, `type`,
`type_filling`, `type_time`, `expiration`, `comment`, `position`,
`position_by`.
**Recorded:** 2026-08-05

---

## error 199: wrong parameters count, at NormalizeDouble

**Context:** `NormalizeDouble(1.23456)`
**Cause:** the digit count is not optional.
**MetaEditor said:** `built-in: double NormalizeDouble(double,int)`
**Fix:** `NormalizeDouble(1.23456, _Digits)`
**Recorded:** 2026-08-05

---

## Knock-on errors: 149, 152, 154, 157, warning 95

These almost never indicate a real problem of their own. They appear when the
parser is already confused by an earlier error on the same or a previous line.

Five genuine mistakes produced twenty-two error lines in one compile.

Fix the first real error, recompile, and re-read. Do not chase these.
**Recorded:** 2026-08-05

---
---

# Warnings that are actually errors

A clean compile means the syntax is valid. It does not mean the code is
correct. These two warnings are almost always real defects.

## warning 42: implicit conversion from 'enum ENUM_POSITION_TYPE' to 'enum ENUM_ORDER_TYPE'

**Context:** `request.type = POSITION_TYPE_BUY;`
**Cause:** `POSITION_TYPE_BUY` describes an existing position. `ORDER_TYPE_BUY`
describes an order you are about to send. They happen to share a numeric value,
so the compiler lets it through with a warning.
**Why it matters:** it works by accident for buy and sell, and stops working
the moment anyone touches pending order types, where the values diverge.
**Fix:** `request.type = ORDER_TYPE_BUY;`
**Recorded:** 2026-08-05

## warning 83: return value of 'OrderSend' should be checked

**Cause:** an order was sent and the result thrown away.
**Why it matters:** this is the compiler telling you, in advance, that you have
written fire-and-forget trading code. Rejected orders will pass silently and
the EA will believe it has a position it does not have.
**Fix:** check the return value and `result.retcode`. See skill
`mql5-patterns`, `references/state-and-restart.md`.
**Recorded:** 2026-08-05

---
---

# The mistake the compiler will never catch

## Assigning an indicator handle to a double

```cpp
// COMPILES CLEANLY. ZERO ERRORS. ZERO WARNINGS. COMPLETELY WRONG.
double ma = iMA(_Symbol, PERIOD_CURRENT, 20, 0, MODE_SMA, PRICE_CLOSE);
```

Verified 2026-08-05: this exact line produced no diagnostic of any kind.

`iMA` returns an `int` handle. Assigning an `int` to a `double` is a legal
implicit conversion, so nothing complains. The variable then holds a small
integer such as `10`, which is a handle number, and the code proceeds to
compare it against price levels.

The EA runs. It never crashes. It simply never trades, or trades on nonsense.

This is the single most dangerous MQL4 habit, because the automated compile
loop cannot detect it. Only reading the code catches it.

**Rule:** if a variable receives the result of `iMA`, `iRSI`, `iMACD`,
`iATR`, `iStochastic` or any other indicator function, it must be declared
`int`, and its value must be passed to `CopyBuffer`. A `double` on the left
hand side of an indicator call is always a bug.

**Related runtime-only mistakes the compiler also permits:**

- Sending an `MqlTradeRequest` without zeroing it first. Use
  `ZeroMemory(request)` or set every field.
- Forgetting `ArraySetAsSeries`, so index 0 is the oldest bar rather than the
  newest, and every signal reads backwards.
- Passing a loop index to `HistoryDealGetInteger` instead of the ticket from
  `HistoryDealGetTicket`.

None of these produce a compile error. They produce an EA that runs and loses
money quietly.
**Recorded:** 2026-08-05
