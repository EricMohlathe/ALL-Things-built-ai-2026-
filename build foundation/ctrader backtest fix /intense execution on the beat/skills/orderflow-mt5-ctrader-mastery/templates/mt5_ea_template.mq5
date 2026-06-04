//+------------------------------------------------------------------+
//|                                       OrderFlowEA_Template.mq5  |
//|        Production scaffold — orderflow-mt5-ctrader-mastery       |
//+------------------------------------------------------------------+
#property copyright "OrderFlow Mastery Skill"
#property link      ""
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>
CTrade trade;

//================== INPUTS ========================================
input group "=== Risk ===";
input double  InpRiskPct           = 0.5;       // Risk per trade (%)
input double  InpMaxDailyLossPct   = 3.0;       // Max daily loss (%)
input double  InpMaxTotalDDPct     = 8.0;       // Max total drawdown from peak (%)
input int     InpMaxPositions      = 1;         // Max concurrent EA positions
input int     InpCooldownMin       = 15;        // Cooldown after close (minutes)

input group "=== Filters ===";
input int     InpMaxSpreadPts      = 30;        // Max spread (points)
input int     InpSlippagePts       = 10;        // Slippage (points)
input int     InpSessionStartMin   = 7*60;      // Session start (UTC minutes)
input int     InpSessionEndMin     = 16*60;     // Session end (UTC minutes)

input group "=== Order Flow ===";
input int     InpDeltaLookback     = 20;        // CVD slope lookback (bars)
input double  InpImbalanceRatio    = 3.0;       // Stacked imbalance ratio
input int     InpImbalanceCount    = 3;         // Stacked imbalance min count
input int     InpExhaustionBars    = 3;         // Bars for exhaustion check
input double  InpInitiativeVolMult = 1.5;       // Initiative vol multiplier

input group "=== Confluence ===";
input double  InpEntryThreshold    = 0.60;      // Final score required to enter

input group "=== Trade Management ===";
input int     InpBEDistancePts     = 100;       // BE trigger distance (points)
input int     InpBEBufferPts       = 5;         // BE buffer (points)
input int     InpTrailDistancePts  = 80;        // Trail distance (points)
input int     InpTimeStopMin       = 240;       // Time stop (minutes)

input group "=== Identification ===";
input int     InpMagic             = 20260430;
input string  InpComment           = "OFEA";

//================== GLOBALS =======================================
double    g_cvd[];
datetime  g_lastBarTime = 0;
double    g_dayStartEquity = 0;
datetime  g_dayKey = 0;
datetime  g_lastTradeCloseTime = 0;
double    g_peakEquity = 0;
double    g_curDelta = 0;
double    g_prevAsk = 0, g_prevBid = 0;

//================== INIT/DEINIT ====================================
int OnInit()
{
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippagePts);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.LogLevel(LOG_LEVEL_ALL);
   ArraySetAsSeries(g_cvd, false);
   g_peakEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(!MarketBookAdd(_Symbol)) Print("MarketBookAdd failed: ", GetLastError());
   Print("OFEA init OK: ", _Symbol, " ", EnumToString(_Period));
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason){ MarketBookRelease(_Symbol); }

//================== HELPERS ========================================
bool IsNewBar()
{
   datetime t = iTime(_Symbol, _Period, 0);
   if(t == g_lastBarTime) return false;
   g_lastBarTime = t;
   return true;
}

bool DailyLossOk()
{
   datetime d = iTime(_Symbol, PERIOD_D1, 0);
   if(d != g_dayKey) { g_dayKey = d; g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY); }
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   double dd = (g_dayStartEquity - eq) / g_dayStartEquity * 100.0;
   return dd < InpMaxDailyLossPct;
}

bool TotalDDOk()
{
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq > g_peakEquity) g_peakEquity = eq;
   double dd = (g_peakEquity - eq) / g_peakEquity * 100.0;
   return dd < InpMaxTotalDDPct;
}

bool SpreadOk()
{
   long sp = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   return sp <= InpMaxSpreadPts;
}

bool SessionOk()
{
   MqlDateTime mt; TimeToStruct(TimeCurrent(), mt);
   int m = mt.hour*60 + mt.min;
   return (m >= InpSessionStartMin && m <= InpSessionEndMin);
}

bool CooldownOk()
{
   if(g_lastTradeCloseTime == 0) return true;
   return (TimeCurrent() - g_lastTradeCloseTime) >= InpCooldownMin*60;
}

int EaPositionsCount()
{
   int n = 0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk = PositionGetTicket(i);
      if(PositionSelectByTicket(tk) && PositionGetInteger(POSITION_MAGIC)==InpMagic)
         if(PositionGetString(POSITION_SYMBOL)==_Symbol) n++;
   }
   return n;
}

double LotByRisk(double slPoints)
{
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double tv  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double pt  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double riskMoney = bal * InpRiskPct/100.0;
   double pointValue = tv * (pt/ts);
   if(slPoints<=0 || pointValue<=0) return 0;
   double lots = riskMoney / (slPoints * pointValue);
   double minL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   lots = MathFloor(lots/step)*step;
   if(lots < minL) lots = minL;
   if(lots > maxL) lots = maxL;
   return lots;
}

bool AllGuardsPass()
{
   return DailyLossOk() && TotalDDOk() && SpreadOk() && SessionOk()
       && CooldownOk() && (EaPositionsCount() < InpMaxPositions);
}

//================== ORDER-FLOW PRIMITIVES ==========================
void UpdateDeltaCvd()
{
   MqlTick tk;
   if(!SymbolInfoTick(_Symbol, tk)) return;
   if(g_prevAsk==0){ g_prevAsk=tk.ask; g_prevBid=tk.bid; return; }

   double sign = 0;
   if(tk.last >= g_prevAsk)      sign =  1.0;
   else if(tk.last <= g_prevBid) sign = -1.0;
   double v = (tk.volume>0 ? (double)tk.volume : 1.0);
   g_curDelta += sign * v;

   g_prevAsk = tk.ask;
   g_prevBid = tk.bid;
}

void OnNewBar()
{
   ArrayResize(g_cvd, ArraySize(g_cvd)+1);
   int last = ArraySize(g_cvd)-1;
   g_cvd[last] = (last>0 ? g_cvd[last-1] : 0) + g_curDelta;
   g_curDelta = 0;
}

//================== SIGNAL LOGIC (drop your detector here) =========
double ComputeEntryScore(int &dirOut)   // dirOut: +1 long, -1 short, 0 none
{
   dirOut = 0;
   if(ArraySize(g_cvd) < InpDeltaLookback+2) return 0;

   // Example confluence: bullish initiative + CVD higher-high
   double o1 = iOpen(_Symbol,_Period,1), c1 = iClose(_Symbol,_Period,1);
   long   v1 = iVolume(_Symbol,_Period,1);
   double avgV = 0;
   for(int i=2;i<2+InpDeltaLookback;i++) avgV += (double)iVolume(_Symbol,_Period,i);
   avgV /= InpDeltaLookback;

   bool bullInit = (c1>o1) && ((double)v1 >= avgV*InpInitiativeVolMult);
   bool bearInit = (c1<o1) && ((double)v1 >= avgV*InpInitiativeVolMult);

   int last = ArraySize(g_cvd)-1;
   bool cvdUp   = (last>=1 && g_cvd[last-1] > g_cvd[MathMax(0,last-InpDeltaLookback)]);
   bool cvdDown = (last>=1 && g_cvd[last-1] < g_cvd[MathMax(0,last-InpDeltaLookback)]);

   if(bullInit && cvdUp)  { dirOut =  1; return 0.7; }
   if(bearInit && cvdDown){ dirOut = -1; return 0.7; }
   return 0;
}

//================== ENTRY ==========================================
void TryEnter(int dir)
{
   double atr = 0; int hAtr = iATR(_Symbol,_Period,14);
   double atrBuf[]; if(CopyBuffer(hAtr,0,1,1,atrBuf)>0) atr = atrBuf[0];
   double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double slPts = MathMax(200, atr/pt * 1.2);

   double price = (dir>0) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl = (dir>0) ? price - slPts*pt : price + slPts*pt;
   double tp = (dir>0) ? price + 2*slPts*pt : price - 2*slPts*pt;
   double lots = LotByRisk(slPts);
   if(lots<=0) return;

   if(dir>0) trade.Buy(lots,_Symbol,price,sl,tp,InpComment);
   else      trade.Sell(lots,_Symbol,price,sl,tp,InpComment);
}

//================== TRADE MANAGEMENT ===============================
void ManagePositions()
{
   double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk = PositionGetTicket(i);
      if(!PositionSelectByTicket(tk)) continue;
      if(PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol) continue;

      ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double entry = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl    = PositionGetDouble(POSITION_SL);
      double tp    = PositionGetDouble(POSITION_TP);
      double cur   = (type==POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol,SYMBOL_BID) : SymbolInfoDouble(_Symbol,SYMBOL_ASK);

      // BE move
      if(type==POSITION_TYPE_BUY  && cur-entry >= InpBEDistancePts*pt && sl < entry+InpBEBufferPts*pt)
         trade.PositionModify(tk, entry+InpBEBufferPts*pt, tp);
      if(type==POSITION_TYPE_SELL && entry-cur >= InpBEDistancePts*pt && (sl > entry-InpBEBufferPts*pt || sl==0))
         trade.PositionModify(tk, entry-InpBEBufferPts*pt, tp);

      // Trailing
      if(type==POSITION_TYPE_BUY && cur-entry > InpTrailDistancePts*pt)
      {
         double newSl = cur - InpTrailDistancePts*pt;
         if(newSl > sl) trade.PositionModify(tk, newSl, tp);
      }
      if(type==POSITION_TYPE_SELL && entry-cur > InpTrailDistancePts*pt)
      {
         double newSl = cur + InpTrailDistancePts*pt;
         if(newSl < sl || sl==0) trade.PositionModify(tk, newSl, tp);
      }
   }
}

//================== DASHBOARD ======================================
void DrawDashboard(double score, int dir)
{
   string txt = StringFormat(
      "OFEA  %s  %s\n"
      "Score: %.2f (thresh %.2f)\nDir: %s\n"
      "Spread: %d pts  (max %d)\n"
      "Daily PL: %.2f%%  (halt %.1f%%)\n"
      "EA pos: %d / %d",
      _Symbol, EnumToString(_Period),
      score, InpEntryThreshold, (dir>0?"LONG":dir<0?"SHORT":"--"),
      (int)SymbolInfoInteger(_Symbol,SYMBOL_SPREAD), InpMaxSpreadPts,
      ((g_dayStartEquity>0)?(g_dayStartEquity-AccountInfoDouble(ACCOUNT_EQUITY))/g_dayStartEquity*100.0:0.0), InpMaxDailyLossPct,
      EaPositionsCount(), InpMaxPositions);
   Comment(txt);
}

//================== EVENTS =========================================
void OnTick()
{
   UpdateDeltaCvd();

   if(IsNewBar())
   {
      OnNewBar();
      ManagePositions();

      int dir = 0;
      double score = ComputeEntryScore(dir);
      DrawDashboard(score, dir);

      if(score >= InpEntryThreshold && dir != 0 && AllGuardsPass())
         TryEnter(dir);
   }
   else
   {
      // could call ManagePositions() here for tighter trailing
   }
}

void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &req, const MqlTradeResult &res)
{
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD)
   {
      // capture close events for cooldown
      if(HistoryDealSelect(trans.deal))
      {
         long ent = HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
         if(ent == DEAL_ENTRY_OUT) g_lastTradeCloseTime = TimeCurrent();
      }
   }
}

void OnBookEvent(const string &symbol)
{
   if(symbol != _Symbol) return;
   // hook for sweep / book-aware logic
}
