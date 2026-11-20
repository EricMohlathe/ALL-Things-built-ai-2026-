//+------------------------------------------------------------------+
//| RsiLevel.mq5                                                      |
//|                                                                   |
//| Built from templates\EA_Template.mq5.                             |
//| Specification: strategies\RsiLevel.md                             |
//|                                                                   |
//| RSI(14) level strategy on closed candles.                         |
//|   long  while RSI is below 30                                     |
//|   short while RSI is above 70                                     |
//| Exit on stop loss or take profit only. No early exit, no trailing.|
//|                                                                   |
//| Not the same as RsiReversal in this folder, which waits for a     |
//| cross through the level. This one acts on the level itself and    |
//| can therefore re-enter on every bar the level holds, which is why |
//| the daily entry cap matters here.                                 |
//|                                                                   |
//| Only the STRATEGY section differs from the template. Everything   |
//| else is the shared safety layer.                                  |
//+------------------------------------------------------------------+
#property copyright "MQL5 Workspace"
#property version   "1.00"
#property description "RSI level strategy on closed candles. See strategies/RsiLevel.md"

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
//| Inputs                                                            |
//+------------------------------------------------------------------+
input group "=== Strategy ===";
input int    InpRsiPeriod        = 14;      // RSI period
input double InpBuyLevel         = 30.0;    // Buy while RSI is below this
input double InpSellLevel        = 70.0;    // Sell while RSI is above this

input group "=== Risk management ===";
input double InpRiskPercent      = 1.0;     // Risk per trade, % of balance
input int    InpStopLossPoints   = 300;     // Stop loss, points
input int    InpTakeProfitPoints = 600;     // Take profit, points, 0 = none
input int    InpMaxPositions     = 1;       // Max simultaneous positions
input int    InpMaxTradesPerDay  = 5;       // Max entries per day, 0 = no limit

input group "=== Filters ===";
input int    InpMaxSpreadPoints  = 30;      // Max spread allowed, points

input group "=== Identity ===";
input long   InpMagic            = 20260808; // Magic number
input string InpComment          = "RsiLevel"; // Order comment

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
CTrade   trade;
int      rsiHandle   = INVALID_HANDLE;
datetime lastBarTime = 0;
bool     isHedging   = false;

// Indicator values for the last closed bars.
// Index 1 is the most recently closed bar, index 2 the one before it.
// Index 0 is the bar still forming and is deliberately not used.
double   rsi[];

//+------------------------------------------------------------------+
//| STRATEGY. This is the only section you normally change.           |
//|                                                                   |
//| Read rsi[1] for the last closed bar and rsi[2] for the one before.|
//+------------------------------------------------------------------+

//--- Return true to open a long position on this bar.
bool ShouldOpenLong()
{
   return(rsi[1] < InpBuyLevel);
}

//--- Return true to open a short position on this bar.
bool ShouldOpenShort()
{
   return(rsi[1] > InpSellLevel);
}

//--- The specification says exit on stop loss or take profit only.
bool ShouldCloseLong()  { return(false); }
bool ShouldCloseShort() { return(false); }

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
   if(InpStopLossPoints <= 0)
   {
      Print("InpStopLossPoints must be greater than zero. Lot sizing depends on it.");
      return(INIT_PARAMETERS_INCORRECT);
   }
   if(InpBuyLevel <= 0.0 || InpBuyLevel >= InpSellLevel || InpSellLevel >= 100.0)
   {
      Print("RSI levels must satisfy 0 < buy level < sell level < 100.");
      return(INIT_PARAMETERS_INCORRECT);
   }

   rsiHandle = iRSI(_Symbol, PERIOD_CURRENT, InpRsiPeriod, PRICE_CLOSE);
   if(rsiHandle == INVALID_HANDLE)
   {
      Print("Failed to create RSI handle, error ", GetLastError());
      return(INIT_FAILED);
   }

   ArraySetAsSeries(rsi, true);

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetTypeFilling(PickFillingMode());
   trade.SetDeviationInPoints(10);

   long marginMode = AccountInfoInteger(ACCOUNT_MARGIN_MODE);
   isHedging = (marginMode == ACCOUNT_MARGIN_MODE_RETAIL_HEDGING);

   LogBrokerCapabilities();

   // State is rebuilt from the account, never carried in memory.
   // See skill mql5-patterns, references/state-and-restart.md.
   PrintFormat("%s starting. %d open position(s), %d entry(ies) already today.",
               InpComment, CountMyPositions(), CountMyEntriesToday());

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(rsiHandle != INVALID_HANDLE) IndicatorRelease(rsiHandle);
   // Never close positions here. OnDeinit also runs on recompile and on a
   // chart template change, and closing then would be a disaster.
}

//+------------------------------------------------------------------+
void OnTick()
{
   // Act once per closed bar, not on every tick.
   datetime current = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(current == lastBarTime)
      return;

   if(!RefreshIndicators())
      return;                       // not enough bars yet, try again next bar

   lastBarTime = current;

   ManageOpenPositions();

   if(!IsSpreadAcceptable())
      return;
   if(CountMyPositions() >= InpMaxPositions)
      return;
   if(InpMaxTradesPerDay > 0 && CountMyEntriesToday() >= InpMaxTradesPerDay)
      return;

   if(ShouldOpenLong())
      OpenPosition(ORDER_TYPE_BUY);
   else if(ShouldOpenShort())
      OpenPosition(ORDER_TYPE_SELL);
}

//+------------------------------------------------------------------+
//| Load the last three indicator values. False means not ready.     |
//+------------------------------------------------------------------+
bool RefreshIndicators()
{
   if(CopyBuffer(rsiHandle, 0, 0, 3, rsi) < 3) return(false);
   return(true);
}

//+------------------------------------------------------------------+
//| Close positions the strategy no longer wants.                    |
//+------------------------------------------------------------------+
void ManageOpenPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)   // downwards, indices shift
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;

      long type = PositionGetInteger(POSITION_TYPE);
      bool wantClose = (type == POSITION_TYPE_BUY)  ? ShouldCloseLong()
                     : (type == POSITION_TYPE_SELL) ? ShouldCloseShort()
                     : false;

      if(wantClose)
      {
         if(!trade.PositionClose(ticket))
            PrintFormat("Close failed for #%I64u: %s", ticket, RetcodeText(trade.ResultRetcode()));
      }
   }
}

//+------------------------------------------------------------------+
//| Send a market order with normalised volume and stops.            |
//+------------------------------------------------------------------+
void OpenPosition(ENUM_ORDER_TYPE type)
{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0)
      return;

   // Respect the broker's minimum stop distance.
   long   stopsLevel = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   int    slPoints   = (int)MathMax((double)InpStopLossPoints,   (double)stopsLevel + 1);
   int    tpPoints   = InpTakeProfitPoints;
   if(tpPoints > 0)
      tpPoints = (int)MathMax((double)tpPoints, (double)stopsLevel + 1);

   double slDistance = slPoints * _Point;
   double lot = CalculateLot(slDistance);
   if(lot <= 0.0)
   {
      Print("Calculated lot is zero. Risk too small, or balance too low for the minimum lot.");
      return;
   }

   double price, sl, tp = 0.0;
   if(type == ORDER_TYPE_BUY)
   {
      price = ask;
      sl = NormalizeDouble(price - slDistance, _Digits);
      if(tpPoints > 0) tp = NormalizeDouble(price + tpPoints * _Point, _Digits);
   }
   else
   {
      price = bid;
      sl = NormalizeDouble(price + slDistance, _Digits);
      if(tpPoints > 0) tp = NormalizeDouble(price - tpPoints * _Point, _Digits);
   }

   bool ok = (type == ORDER_TYPE_BUY)
           ? trade.Buy(lot, _Symbol, 0.0, sl, tp, InpComment)
           : trade.Sell(lot, _Symbol, 0.0, sl, tp, InpComment);

   uint code = trade.ResultRetcode();
   if(ok && (code == TRADE_RETCODE_DONE || code == TRADE_RETCODE_DONE_PARTIAL))
   {
      PrintFormat("%s %s %.2f lot at %.*f, SL %.*f, TP %.*f, RSI %.1f",
                  InpComment, (type == ORDER_TYPE_BUY ? "BUY" : "SELL"),
                  lot, _Digits, price, _Digits, sl, _Digits, tp, rsi[1]);
   }
   else
   {
      PrintFormat("Order rejected: %s (retcode %u)", RetcodeText(code), code);
   }
}

//+------------------------------------------------------------------+
//| Lot size from a percentage of balance and the stop distance.     |
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
//| Round down to the lot step and clamp to the broker's limits.     |
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
bool IsSpreadAcceptable()
{
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   return(spread <= InpMaxSpreadPoints);
}

//+------------------------------------------------------------------+
//| Open positions belonging to this EA on this symbol.              |
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
//| Entries made today, read from history. Never from a counter.     |
//| This is what makes the EA survive a terminal restart.            |
//+------------------------------------------------------------------+
int CountMyEntriesToday()
{
   MqlDateTime now;
   TimeToStruct(TimeCurrent(), now);   // broker server time, not local time
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
      if(ticket == 0) continue;
      if(HistoryDealGetInteger(ticket, DEAL_MAGIC)  != InpMagic) continue;
      if(HistoryDealGetString(ticket, DEAL_SYMBOL)  != _Symbol)  continue;
      if(HistoryDealGetInteger(ticket, DEAL_ENTRY)  == DEAL_ENTRY_IN)
         count++;
   }
   return(count);
}

//+------------------------------------------------------------------+
//| Pick a filling mode the broker actually supports.                |
//| Getting this wrong rejects every order with retcode 10030.       |
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
   PrintFormat("Symbol %s  digits %d  point %.*f", _Symbol, _Digits, _Digits, _Point);
   PrintFormat("Account mode: %s", isHedging ? "HEDGING" : "NETTING or EXCHANGE");
   PrintFormat("Volume min %.2f  max %.2f  step %.2f",
               SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN),
               SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX),
               SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP));
   PrintFormat("Stops level %d  freeze level %d",
               (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL),
               (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL));
}

//+------------------------------------------------------------------+
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
//+------------------------------------------------------------------+
