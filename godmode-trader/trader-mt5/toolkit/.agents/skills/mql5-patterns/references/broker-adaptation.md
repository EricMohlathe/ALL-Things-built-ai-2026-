# Broker adaptation

Read every one of these at runtime. None of them can be assumed.

All snippets verified by compile on 2026-08-05, MetaEditor build 5836.

---

## Symbol suffix

Brokers rename instruments. The Exness demo used for verification exposes
`EURUSDm`, `XAUUSDm`, `BTCUSDm`. Every symbol carries the `m` suffix, with no
exceptions. Other brokers use `.m`, `.raw`, `x`, or nothing.

A wrong symbol name is not a warning. The Strategy Tester aborts:

```
Tester   symbol EURUSD not exist
Terminal shutdown with -1000012358 (tester symbol does not exist)
```

**Never hardcode a symbol.** Take it from `_Symbol` for the attached chart, or
from an input for anything else.

---

## Netting or hedging

Netting accounts hold at most one position per symbol; an opposite order
reduces or reverses it rather than opening a second position. Hedging accounts
allow many. Code written for one is wrong on the other.

```cpp
long marginMode = AccountInfoInteger(ACCOUNT_MARGIN_MODE);

if(marginMode == ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
   ; // multiple positions per symbol are allowed
else if(marginMode == ACCOUNT_MARGIN_MODE_RETAIL_NETTING)
   ; // one net position per symbol only
else
   ; // ACCOUNT_MARGIN_MODE_EXCHANGE, an exchange account
```

If the strategy needs simultaneous opposite positions, refuse to run on a
netting account rather than silently misbehaving.

---

## Filling mode

The wrong filling mode gets every order rejected with
`TRADE_RETCODE_INVALID_FILL` (10030). The compiler cannot catch it.

`SYMBOL_FILLING_MODE` is a bit mask, so test bits, do not compare.

```cpp
int filling = (int)SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
bool canFOK = (filling & SYMBOL_FILLING_FOK) != 0;
bool canIOC = (filling & SYMBOL_FILLING_IOC) != 0;

ENUM_ORDER_TYPE_FILLING PickFilling()
{
   int mask = (int)SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((mask & SYMBOL_FILLING_FOK) != 0)
      return(ORDER_FILLING_FOK);
   if((mask & SYMBOL_FILLING_IOC) != 0)
      return(ORDER_FILLING_IOC);
   return(ORDER_FILLING_RETURN);
}
```

With `CTrade`:

```cpp
trade.SetTypeFilling(PickFilling());
```

---

## Volume constraints

```cpp
double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
```

Rounding to the step is mandatory. See `risk-sizing.md` for `NormalizeLot`.

---

## Stops level and freeze level

Two different limits. Both apply.

```cpp
long stopsLevel  = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
long freezeLevel = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
```

- **Stops level**: minimum distance in points between the current price and a
  stop loss or take profit. Closer than this and the order is rejected with
  `TRADE_RETCODE_INVALID_STOPS` (10016).
- **Freeze level**: how close to the price an existing order may be before the
  broker forbids modifying or closing it. Ignoring this produces modification
  failures that look random.

Both are frequently zero on retail accounts, which is exactly why code that
ignores them appears to work until it meets a broker where they are not.

---

## Tick value and tick size

The basis of correct position sizing. Never derive lot size from points alone.

```cpp
double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
```

`tickValue` is already expressed in the account currency, which is what makes
it safe for cross pairs and metals. Deriving money risk from pip counts is not.

---

## Spread filter

```cpp
long spreadPoints = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
if(spreadPoints > InpMaxSpreadPoints)
   return; // do not trade in this tick
```

Spread widens sharply around session opens and news. Every EA needs this.
