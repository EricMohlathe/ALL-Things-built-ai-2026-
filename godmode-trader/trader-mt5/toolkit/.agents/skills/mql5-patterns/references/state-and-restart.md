# Position lookup, trade results, surviving a restart

Verified by compile on 2026-08-05, MetaEditor build 5836.

The live terminal for this project runs on a home PC, not a VPS. It will be
restarted by power cuts, Windows updates and the user, sometimes while a
position is open. Everything here assumes that.

---

## Never trust a variable, ask the account

After a restart every global resets to its default. The positions on the
account do not. Any decision that depends on history must read the account.

The failure this prevents: an EA that limits itself with
`int tradesToday = 0;` restarts at midday, resets the counter to zero, and
opens a second full day of trades.

```cpp
// WRONG
int tradesToday = 0;
if(tradesToday < InpMaxPerDay) { ... tradesToday++; }

// RIGHT
if(CountMyDealsToday() < InpMaxPerDay) { ... }
```

---

## Open positions belonging to this EA

```cpp
int CountMyPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) == InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
         count++;
   }
   return(count);
}
```

Iterate **downwards**. Closing a position inside an ascending loop shifts the
indices and silently skips entries.

`PositionGetTicket(i)` selects the position as a side effect, which is why the
`PositionGetInteger` calls that follow need no ticket argument.

Filter on both magic number and symbol. Another EA, or the user trading by
hand, may hold positions on the same account.

---

## Deals closed today

```cpp
int CountMyDealsToday()
{
   MqlDateTime now;
   TimeToStruct(TimeCurrent(), now);
   now.hour = 0;
   now.min  = 0;
   now.sec  = 0;
   datetime dayStart = StructToTime(now);

   if(!HistorySelect(dayStart, TimeCurrent()))
      return(0);

   int count = 0;
   int total = HistoryDealsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket == 0)
         continue;
      if(HistoryDealGetInteger(ticket, DEAL_MAGIC) == InpMagic &&
         HistoryDealGetString(ticket, DEAL_SYMBOL) == _Symbol)
         count++;
   }
   return(count);
}
```

`TimeCurrent()` is **broker server time**, not the machine's local time. The
server's day boundary is what matters for a daily limit, and its GMT offset
differs by broker and shifts with daylight saving. Never use `TimeLocal()` for
this.

---

## Trade result codes

Every trade operation must be checked. `CTrade` exposes the code through
`trade.ResultRetcode()`.

```cpp
string RetcodeText(uint code)
{
   switch(code)
   {
      case TRADE_RETCODE_DONE:              return("DONE");
      case TRADE_RETCODE_DONE_PARTIAL:      return("PARTIAL FILL");
      case TRADE_RETCODE_REQUOTE:           return("REQUOTE");
      case TRADE_RETCODE_REJECT:            return("REJECTED");
      case TRADE_RETCODE_INVALID_STOPS:     return("INVALID STOPS");
      case TRADE_RETCODE_INVALID_VOLUME:    return("INVALID VOLUME");
      case TRADE_RETCODE_NO_MONEY:          return("NOT ENOUGH MONEY");
      case TRADE_RETCODE_MARKET_CLOSED:     return("MARKET CLOSED");
      case TRADE_RETCODE_TRADE_DISABLED:    return("TRADE DISABLED");
      case TRADE_RETCODE_INVALID_FILL:      return("UNSUPPORTED FILLING MODE");
      case TRADE_RETCODE_CONNECTION:        return("NO CONNECTION");
      case TRADE_RETCODE_PRICE_CHANGED:     return("PRICE CHANGED");
      case TRADE_RETCODE_TOO_MANY_REQUESTS: return("TOO MANY REQUESTS");
      default:                              return("UNKNOWN " + IntegerToString(code));
   }
}
```

What each one usually means in practice:

| Code | Meaning | Sensible response |
|---|---|---|
| 10004 requote | Price moved during the request | Retry a small number of times, then give up |
| 10006 rejected | Broker refused | Log and stop. Do not loop |
| 10014 invalid volume | Lot not normalised to the step | Fix the sizing code, not the retry logic |
| 10016 invalid stops | Stop closer than `SYMBOL_TRADE_STOPS_LEVEL` | Widen the stop |
| 10019 no money | Insufficient free margin | Stop trading, alert the user |
| 10018 market closed | Outside session hours | Wait |
| 10030 invalid fill | Wrong filling mode | See `broker-adaptation.md` |

Never retry in an unbounded loop. On a live account a tight retry loop against
a rejecting broker is how an EA generates hundreds of requests in a minute.

---

## Persisting something that genuinely must survive

Prefer rebuilding from the account. If a value truly cannot be derived, write
it to a file in `MQL5\Files\` or use `GlobalVariableSet`, and still treat the
account as the source of truth in `OnInit`.
