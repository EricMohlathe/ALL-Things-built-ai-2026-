//+------------------------------------------------------------------+
//| EA_Template_Structural.mq5                                        |
//|                                                                   |
//| Starting point for strategies that place a PENDING order at a     |
//| price the strategy computes, with a stop and a target that also   |
//| come from structure rather than from a fixed point count.         |
//|                                                                   |
//| Use EA_Template.mq5 instead when the strategy enters at market    |
//| with a fixed stop distance. That one is smaller and simpler.      |
//|                                                                   |
//| Copy this file to src\Experts\<name>.mq5 and fill in FindSetup(). |
//| Everything outside the STRATEGY section is the safety layer:      |
//| risk sizing from the real stop distance, broker capability        |
//| detection, price normalisation, reward to risk enforcement,       |
//| pending order expiry, and state rebuilt from the account so the   |
//| EA survives a terminal restart. Do not rewrite it unless asked.   |
//|                                                                   |
//| The default strategy is a retest of yesterday's midpoint. It      |
//| exists only so the template compiles and trades. Replace it.      |
//+------------------------------------------------------------------+
#property copyright "MQL5 Workspace"
#property version   "1.00"
#property description "Structural template. Replace FindSetup()."

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
//| Inputs                                                            |
//+------------------------------------------------------------------+
input group "=== Risk management ===";
input double InpRiskPercent      = 0.25;    // Risk per trade, % of balance
input double InpMinRewardRisk    = 1.5;     // Skip the trade below this ratio
input double InpMaxRewardRisk    = 2.5;     // Cap the target above this ratio
input int    InpMaxPositions     = 1;       // Max simultaneous positions
input int    InpMaxTradesPerDay  = 2;       // Max entries per day, 0 = no limit
input int    InpLossLockoutMin   = 30;      // Minutes to stand down after a loss
input double InpMaxMarginPct     = 20.0;    // Cap the lot at this % of free margin

input group "=== Pending orders ===";
input int    InpOrderLifeBars    = 24;      // Delete the order after this many bars

input group "=== Filters ===";
input int    InpMaxSpreadPoints  = 20;      // Max spread allowed, points

input group "=== Identity ===";
input long   InpMagic            = 20260806; // Magic number
input string InpComment          = "Structural"; // Order comment

//+------------------------------------------------------------------+
//| A setup is the only thing the strategy section produces.          |
//| Prices are raw. The safety layer normalises and validates them.   |
//+------------------------------------------------------------------+
struct TradeSetup
{
   bool     valid;
   int      direction;      // +1 buy limit, -1 sell limit
   double   entry;
   double   stop;
   double   target;
   string   reason;         // one line, ends up in the journal
};

void ClearSetup(TradeSetup &s)
{
   s.valid     = false;
   s.direction = 0;
   s.entry     = 0.0;
   s.stop      = 0.0;
   s.target    = 0.0;
   s.reason    = "";
}

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
CTrade   trade;
datetime lastBarTime   = 0;
bool     isHedging     = false;
bool     canSetExpiry  = false;

//+------------------------------------------------------------------+
//| STRATEGY. This is the only section you normally change.           |
//|                                                                   |
//| Return a setup with valid = false when there is nothing to do.    |
//| Do not send orders here, do not size positions here, and do not   |
//| worry about the broker's minimum stop distance. That is the       |
//| safety layer's job and it will reject anything unsound.           |
//+------------------------------------------------------------------+

TradeSetup FindSetup()
{
   TradeSetup s;
   ClearSetup(s);

   // Placeholder: retest of yesterday's midpoint, targeting yesterday's extreme.
   double pdh = iHigh(_Symbol, PERIOD_D1, 1);
   double pdl = iLow(_Symbol, PERIOD_D1, 1);
   if(pdh <= 0.0 || pdl <= 0.0 || pdh <= pdl)
      return(s);

   double mid  = (pdh + pdl) / 2.0;
   double bid  = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double span = pdh - pdl;

   if(bid > mid)
   {
      s.valid     = true;
      s.direction = 1;
      s.entry     = mid;
      s.stop      = pdl - span * 0.1;
      s.target    = pdh;
      s.reason    = "retest of yesterday midpoint from above";
   }
   else
   {
      s.valid     = true;
      s.direction = -1;
      s.entry     = mid;
      s.stop      = pdh + span * 0.1;
      s.target    = pdl;
      s.reason    = "retest of yesterday midpoint from below";
   }
   return(s);
}

//+------------------------------------------------------------------+
//| END OF STRATEGY SECTION                                           |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpRiskPercent <= 0.0 || InpRiskPercent > 100.0)
   {
      Print("InpRiskPercent must be between 0 and 100.");
      return(INIT_PARAMETERS_INCORRECT);
   }
   if(InpMinRewardRisk <= 0.0 || InpMaxRewardRisk < InpMinRewardRisk)
   {
      Print("Reward to risk bounds are inconsistent.");
      return(INIT_PARAMETERS_INCORRECT);
   }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetTypeFilling(PickFillingMode());
   trade.SetDeviationInPoints(10);

   isHedging = (AccountInfoInteger(ACCOUNT_MARGIN_MODE) == ACCOUNT_MARGIN_MODE_RETAIL_HEDGING);

   // Not every broker accepts an expiry time on a pending order. When it is
   // unsupported the order goes out as GTC and this EA deletes it by bar count.
   int expMask  = (int)SymbolInfoInteger(_Symbol, SYMBOL_EXPIRATION_MODE);
   canSetExpiry = ((expMask & SYMBOL_EXPIRATION_SPECIFIED) != 0);

   LogBrokerCapabilities();
   PrintFormat("%s starting. %d position(s), %d pending, %d entry(ies) today.",
               InpComment, CountMyPositions(), CountMyOrders(), CountMyEntriesToday());

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Never close positions or delete orders here. OnDeinit also runs on
   // recompile and on a template change, and acting then would be a disaster.
}

//+------------------------------------------------------------------+
void OnTick()
{
   datetime current = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(current == lastBarTime)
      return;
   lastBarTime = current;

   ExpireStaleOrders();

   // Set and forget: an open position is never touched.
   if(CountMyPositions() >= InpMaxPositions)
      return;
   if(CountMyOrders() > 0)
      return;
   if(InpMaxTradesPerDay > 0 && CountMyEntriesToday() >= InpMaxTradesPerDay)
      return;
   if(IsInLossLockout())
      return;
   if(!IsSpreadAcceptable())
      return;

   TradeSetup s = FindSetup();
   if(!s.valid)
      return;

   PlaceSetup(s);
}

//+------------------------------------------------------------------+
//| Validate, size and send. Every rejection prints its reason, so a  |
//| backtest with no trades can be diagnosed from the log alone.      |
//+------------------------------------------------------------------+
void PlaceSetup(TradeSetup &s)
{
   if(s.direction != 1 && s.direction != -1)
   {
      Print("Setup rejected: direction must be +1 or -1.");
      return;
   }

   double entry  = NormalizePrice(s.entry);
   double stop   = NormalizePrice(s.stop);
   double target = NormalizePrice(s.target);

   // The stop must sit on the losing side of entry, the target on the winning
   // side. Getting this backwards is the classic sign flip and it would
   // otherwise be sent to the broker and rejected with an opaque code.
   if(s.direction == 1 && !(stop < entry && target > entry))
   {
      PrintFormat("Setup rejected: long with entry %.*f stop %.*f target %.*f",
                  _Digits, entry, _Digits, stop, _Digits, target);
      return;
   }
   if(s.direction == -1 && !(stop > entry && target < entry))
   {
      PrintFormat("Setup rejected: short with entry %.*f stop %.*f target %.*f",
                  _Digits, entry, _Digits, stop, _Digits, target);
      return;
   }

   double risk = MathAbs(entry - stop);
   if(risk <= 0.0)
   {
      Print("Setup rejected: zero stop distance.");
      return;
   }

   double reward = MathAbs(target - entry);
   double rr     = reward / risk;
   if(rr < InpMinRewardRisk)
   {
      PrintFormat("Setup skipped: reward to risk %.2f below %.2f. %s",
                  rr, InpMinRewardRisk, s.reason);
      return;
   }
   if(rr > InpMaxRewardRisk)
   {
      target = NormalizePrice(s.direction == 1 ? entry + risk * InpMaxRewardRisk
                                               : entry - risk * InpMaxRewardRisk);
      PrintFormat("Target capped from %.2fR to %.2fR.", rr, InpMaxRewardRisk);
   }

   // A limit order has to rest on the far side of the market from price.
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0)
      return;

   long   stopsLevel = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minGap     = (stopsLevel + 1) * _Point;

   if(s.direction == 1 && entry > ask - minGap)
   {
      PrintFormat("Setup skipped: buy limit %.*f is not below ask %.*f by the stops level.",
                  _Digits, entry, _Digits, ask);
      return;
   }
   if(s.direction == -1 && entry < bid + minGap)
   {
      PrintFormat("Setup skipped: sell limit %.*f is not above bid %.*f by the stops level.",
                  _Digits, entry, _Digits, bid);
      return;
   }
   if(MathAbs(entry - stop) < minGap || MathAbs(target - entry) < minGap)
   {
      Print("Setup skipped: stop or target closer than the broker's minimum distance.");
      return;
   }

   double lot = CalculateLot(risk);
   lot = CapLotByMargin(lot, (s.direction == 1 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL), entry);
   if(lot <= 0.0)
   {
      Print("Setup skipped: calculated lot is zero. Risk too small or balance too low.");
      return;
   }

   ENUM_ORDER_TYPE_TIME timeType  = ORDER_TIME_GTC;
   datetime             expiry    = 0;
   if(canSetExpiry && InpOrderLifeBars > 0)
   {
      timeType = ORDER_TIME_SPECIFIED;
      expiry   = (datetime)(TimeCurrent() + (long)InpOrderLifeBars * PeriodSeconds(PERIOD_CURRENT));
   }

   bool ok = (s.direction == 1)
           ? trade.BuyLimit (lot, entry, _Symbol, stop, target, timeType, expiry, InpComment)
           : trade.SellLimit(lot, entry, _Symbol, stop, target, timeType, expiry, InpComment);

   uint code = trade.ResultRetcode();
   if(ok && (code == TRADE_RETCODE_DONE || code == TRADE_RETCODE_PLACED))
   {
      PrintFormat("%s %s limit %.2f lot at %.*f  SL %.*f  TP %.*f  RR %.2f  | %s",
                  InpComment, (s.direction == 1 ? "BUY" : "SELL"), lot,
                  _Digits, entry, _Digits, stop, _Digits, target,
                  MathAbs(target - entry) / risk, s.reason);
   }
   else
   {
      PrintFormat("Order rejected: %s (retcode %u)", RetcodeText(code), code);
   }
}

//+------------------------------------------------------------------+
//| Delete pending orders that have outlived their setup.             |
//| Needed even when the broker accepts an expiry time, because a bar |
//| close beyond the stop kills the setup before the clock does.      |
//+------------------------------------------------------------------+
void ExpireStaleOrders()
{
   int barSeconds = PeriodSeconds(PERIOD_CURRENT);

   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;
      if(OrderGetInteger(ORDER_MAGIC)  != InpMagic) continue;
      if(OrderGetString(ORDER_SYMBOL)  != _Symbol)  continue;

      bool kill = false;

      if(InpOrderLifeBars > 0)
      {
         datetime placed = (datetime)OrderGetInteger(ORDER_TIME_SETUP);
         if(TimeCurrent() - placed >= (long)InpOrderLifeBars * barSeconds)
            kill = true;
      }

      if(!kill)
      {
         double stop = OrderGetDouble(ORDER_SL);
         double last = iClose(_Symbol, PERIOD_CURRENT, 1);
         long   type = OrderGetInteger(ORDER_TYPE);
         if(stop > 0.0 && last > 0.0)
         {
            if(type == ORDER_TYPE_BUY_LIMIT  && last < stop) kill = true;
            if(type == ORDER_TYPE_SELL_LIMIT && last > stop) kill = true;
         }
      }

      if(kill && !trade.OrderDelete(ticket))
         PrintFormat("Delete failed for #%I64u: %s", ticket, RetcodeText(trade.ResultRetcode()));
   }
}

//+------------------------------------------------------------------+
//| Lot size from a percentage of balance and the real stop distance. |
//+------------------------------------------------------------------+
double CalculateLot(double stopDistancePrice)
{
   if(stopDistancePrice <= 0.0) return(0.0);

   double balance   = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney = balance * InpRiskPercent / 100.0;

   // Tick value is already in the account currency, which is what makes this
   // correct for cross pairs and metals. Deriving risk from pips is not.
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue <= 0.0 || tickSize <= 0.0) return(0.0);

   double lossPerLot = (stopDistancePrice / tickSize) * tickValue;
   if(lossPerLot <= 0.0) return(0.0);

   return(NormalizeLot(riskMoney / lossPerLot));
}

//+------------------------------------------------------------------+
//| A last rail under the risk maths. Lot size is risk divided by the |
//| stop distance, so a stop that comes out far smaller than intended |
//| does not produce a small loss, it produces an enormous position.  |
//| Percent-of-balance sizing cannot catch that on its own. This can. |
//+------------------------------------------------------------------+
double CapLotByMargin(double lot, const ENUM_ORDER_TYPE type, const double price)
{
   if(lot <= 0.0 || InpMaxMarginPct <= 0.0) return(lot);

   double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   double allowed    = freeMargin * InpMaxMarginPct / 100.0;

   double needed = 0.0;
   if(!OrderCalcMargin(type, _Symbol, lot, price, needed) || needed <= 0.0)
      return(lot);                     // cannot tell, do not silently shrink
   if(needed <= allowed)
      return(lot);

   double capped = NormalizeLot(lot * allowed / needed);
   PrintFormat("Lot cut from %.2f to %.2f. Margin %.2f exceeded %.0f%% of free margin %.2f.",
               lot, capped, needed, InpMaxMarginPct, freeMargin);
   return(capped);
}

//+------------------------------------------------------------------+
double NormalizeLot(double lot)
{
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(lotStep <= 0.0) return(0.0);

   lot = MathFloor(lot / lotStep) * lotStep;
   if(lot < minLot) return(0.0);          // refuse rather than risk more than asked
   if(lot > maxLot) lot = maxLot;

   return(NormalizeDouble(lot, 2));
}

//+------------------------------------------------------------------+
//| Round to the broker's tick size, not just to digits. On symbols   |
//| whose tick size is not one point, a price rounded only to digits  |
//| is rejected as an invalid price.                                  |
//+------------------------------------------------------------------+
double NormalizePrice(double price)
{
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickSize <= 0.0)
      return(NormalizeDouble(price, _Digits));
   return(NormalizeDouble(MathRound(price / tickSize) * tickSize, _Digits));
}

//+------------------------------------------------------------------+
bool IsSpreadAcceptable()
{
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   return(spread <= InpMaxSpreadPoints);
}

//+------------------------------------------------------------------+
int CountMyPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) == InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
         count++;
   }
   return(count);
}

//+------------------------------------------------------------------+
int CountMyOrders()
{
   int count = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;
      if(OrderGetInteger(ORDER_MAGIC) == InpMagic &&
         OrderGetString(ORDER_SYMBOL) == _Symbol)
         count++;
   }
   return(count);
}

//+------------------------------------------------------------------+
//| Entries today, read from history. Never from a counter in memory. |
//| This is what makes the EA survive a terminal restart.             |
//| Override DayStartServerTime() to count days in another zone.      |
//+------------------------------------------------------------------+
int CountMyEntriesToday()
{
   datetime dayStart = DayStartServerTime();
   if(!HistorySelect(dayStart, TimeCurrent()))
      return(0);

   int count = 0;
   int total = HistoryDealsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket == 0) continue;
      if(HistoryDealGetInteger(ticket, DEAL_MAGIC)  != InpMagic) continue;
      if(HistoryDealGetString(ticket, DEAL_SYMBOL)  != _Symbol)  continue;
      if(HistoryDealGetInteger(ticket, DEAL_ENTRY)  == DEAL_ENTRY_IN)
         count++;
   }
   return(count);
}

//+------------------------------------------------------------------+
datetime DayStartServerTime()
{
   MqlDateTime now;
   TimeToStruct(TimeCurrent(), now);   // broker server time, not local time
   now.hour = 0;
   now.min  = 0;
   now.sec  = 0;
   return(StructToTime(now));
}

//+------------------------------------------------------------------+
//| Stand down for a while after a loss. Read from history so that a  |
//| restart does not hand the EA a clean slate it has not earned.     |
//+------------------------------------------------------------------+
bool IsInLossLockout()
{
   if(InpLossLockoutMin <= 0)
      return(false);

   datetime from = (datetime)(TimeCurrent() - (long)InpLossLockoutMin * 60);
   if(!HistorySelect(from, TimeCurrent()))
      return(false);

   int total = HistoryDealsTotal();
   for(int i = total - 1; i >= 0; i--)
   {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket == 0) continue;
      if(HistoryDealGetInteger(ticket, DEAL_MAGIC) != InpMagic) continue;
      if(HistoryDealGetString(ticket, DEAL_SYMBOL) != _Symbol)  continue;
      if(HistoryDealGetInteger(ticket, DEAL_ENTRY) != DEAL_ENTRY_OUT) continue;

      double profit = HistoryDealGetDouble(ticket, DEAL_PROFIT)
                    + HistoryDealGetDouble(ticket, DEAL_SWAP)
                    + HistoryDealGetDouble(ticket, DEAL_COMMISSION);
      if(profit < 0.0)
         return(true);
   }
   return(false);
}

//+------------------------------------------------------------------+
ENUM_ORDER_TYPE_FILLING PickFillingMode()
{
   int mask = (int)SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((mask & SYMBOL_FILLING_FOK) != 0) return(ORDER_FILLING_FOK);
   if((mask & SYMBOL_FILLING_IOC) != 0) return(ORDER_FILLING_IOC);
   return(ORDER_FILLING_RETURN);
}

//+------------------------------------------------------------------+
void LogBrokerCapabilities()
{
   PrintFormat("Symbol %s  digits %d  point %.*f  tick size %.*f",
               _Symbol, _Digits, _Digits, _Point,
               _Digits, SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE));
   PrintFormat("Account mode: %s", isHedging ? "HEDGING" : "NETTING or EXCHANGE");
   PrintFormat("Volume min %.2f  max %.2f  step %.2f",
               SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN),
               SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX),
               SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP));
   PrintFormat("Stops level %d  freeze level %d  pending expiry %s",
               (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL),
               (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL),
               canSetExpiry ? "supported" : "NOT supported, deleting by bar count");
}

//+------------------------------------------------------------------+
string RetcodeText(uint code)
{
   switch(code)
   {
      case TRADE_RETCODE_DONE:              return("DONE");
      case TRADE_RETCODE_PLACED:            return("PLACED");
      case TRADE_RETCODE_DONE_PARTIAL:      return("PARTIAL FILL");
      case TRADE_RETCODE_REQUOTE:           return("REQUOTE");
      case TRADE_RETCODE_REJECT:            return("REJECTED");
      case TRADE_RETCODE_INVALID_STOPS:     return("INVALID STOPS");
      case TRADE_RETCODE_INVALID_PRICE:     return("INVALID PRICE");
      case TRADE_RETCODE_INVALID_VOLUME:    return("INVALID VOLUME");
      case TRADE_RETCODE_INVALID_EXPIRATION:return("INVALID EXPIRATION");
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
//+------------------------------------------------------------------+
