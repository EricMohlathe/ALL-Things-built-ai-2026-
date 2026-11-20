# Time, session and market condition filters

Verified by compile on 2026-08-05, MetaEditor build 5836.

---

## Broker time is not your time

`TimeCurrent()` returns the **trade server's** time. `TimeLocal()` returns the
machine's. They are almost never the same, and the difference moves twice a
year when daylight saving changes on one side and not the other.

Every session filter must use server time. A filter written against local time
silently shifts by an hour twice a year, and the EA starts trading a session it
was told to avoid.

```cpp
MqlDateTime t;
TimeToStruct(TimeCurrent(), t);   // server time. Never TimeLocal for filters.
// t.hour, t.min, t.day_of_week (0 = Sunday), t.mon, t.day
```

Tell the user which server time zone the filter assumes, and put it in the
strategy file. `TimeGMTOffset()` gives the machine's offset from GMT, which is
not the same as the server's.

---

## Trading hours

```cpp
input int InpStartHour = 8;    // server time
input int InpEndHour   = 20;   // server time

bool IsWithinTradingHours()
{
   MqlDateTime t;
   TimeToStruct(TimeCurrent(), t);

   if(InpStartHour == InpEndHour)
      return(true);                       // no restriction

   if(InpStartHour < InpEndHour)
      return(t.hour >= InpStartHour && t.hour < InpEndHour);

   // Window crosses midnight, for example 22:00 to 04:00
   return(t.hour >= InpStartHour || t.hour < InpEndHour);
}
```

The midnight-crossing case is the one that gets forgotten, and it is exactly
the case an Asian-session strategy needs.

---

## Day of week

```cpp
bool IsTradingDay()
{
   MqlDateTime t;
   TimeToStruct(TimeCurrent(), t);

   if(t.day_of_week == 0 || t.day_of_week == 6)   // Sunday, Saturday
      return(false);

   // Many strategies avoid Friday's last hours, when liquidity thins out
   // and weekend gap risk begins.
   if(t.day_of_week == 5 && t.hour >= 20)
      return(false);

   return(true);
}
```

`day_of_week` is 0 for Sunday through 6 for Saturday. Some brokers open Sunday
evening in server time, so Sunday is not always empty.

---

## Spread

The cheapest and most important filter. Spread widens sharply at session opens
and around news, which is exactly when many strategies want to trade.

```cpp
bool IsSpreadAcceptable()
{
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   return(spread <= InpMaxSpreadPoints);
}
```

Note this is in **points**, not pips. On a 5-digit symbol, 30 points is 3 pips.

---

## Enough history to compute anything

Early in a backtest, and after a reconnect, the indicators do not have enough
bars yet. Reading them anyway produces signals from empty data.

```cpp
if(Bars(_Symbol, PERIOD_CURRENT) < InpSlowPeriod + 10)
   return;
```

`CopyBuffer` returning fewer elements than requested means the same thing, and
is the more reliable check. The template already returns early on it.

---

## Connection loss

On a home PC the internet will drop. The terminal reconnects by itself, but
while it is down, prices are stale and orders will fail.

```cpp
if(!TerminalInfoInteger(TERMINAL_CONNECTED))
   return;                        // no connection, do nothing this tick

if(!MQLInfoInteger(MQL_TRADE_ALLOWED))
   return;                        // AutoTrading is off

if(!AccountInfoInteger(ACCOUNT_TRADE_EXPERT))
   return;                        // the broker has disabled EA trading
```

These three checks belong at the top of `OnTick` in any EA that will run
unattended. They cost nothing and prevent a stream of failed orders.

Do not try to close positions when the connection is down. It will not work,
and the retries make the log unreadable.

---

## News

There is no reliable built-in way to know a news release is coming. MQL5 has an
economic calendar API, but it is not available during Strategy Tester runs, so
a filter built on it behaves differently in backtest and live. That difference
is worse than having no filter, because it makes the backtest meaningless.

The honest options, in order of preference:

1. **A manual time window.** The user names the dates and hours to avoid, and
   the EA skips them. Behaves identically in backtest and live.
2. **A wider spread filter.** Spread blows out during news, so the spread
   filter already blocks most of the danger without any calendar at all.

If the user asks for automatic news avoidance, explain the backtest problem
before building it. Do not silently produce a filter that only works live.
