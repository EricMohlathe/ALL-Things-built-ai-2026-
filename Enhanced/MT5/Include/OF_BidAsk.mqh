//+------------------------------------------------------------------+
//| OF_BidAsk.mqh — Bid/Ask spread monitor + cost-aware gate         |
//| Rejects setups when spread > k × ATR — protects edge from costs. |
//+------------------------------------------------------------------+
#ifndef __OF_BIDASK_MQH__
#define __OF_BIDASK_MQH__

struct BidAskState
{
   double bid, ask, spread, spreadPts;
   double meanSpreadPts;
   double sdSpreadPts;
   double zSpread;
};

class COF_BidAsk
{
private:
   double m_buf[];          // rolling spread window
   int    m_idx;
   int    m_len;
public:
   BidAskState st;

   void Init(int window=120)
   {
      m_len = window; m_idx = 0;
      ArrayResize(m_buf, m_len); ArrayInitialize(m_buf, 0);
   }
   void Update(string sym)
   {
      st.bid = SymbolInfoDouble(sym, SYMBOL_BID);
      st.ask = SymbolInfoDouble(sym, SYMBOL_ASK);
      st.spread = st.ask - st.bid;
      st.spreadPts = st.spread / SymbolInfoDouble(sym, SYMBOL_POINT);

      m_buf[m_idx % m_len] = st.spreadPts;
      m_idx++;

      int n = MathMin(m_idx, m_len);
      double sum = 0, sum2 = 0;
      for (int i = 0; i < n; i++) { sum += m_buf[i]; sum2 += m_buf[i] * m_buf[i]; }
      st.meanSpreadPts = n > 0 ? sum / n : 0;
      double v = n > 0 ? (sum2 / n) - (st.meanSpreadPts * st.meanSpreadPts) : 0;
      st.sdSpreadPts = v > 0 ? MathSqrt(v) : 0;
      st.zSpread = st.sdSpreadPts > 0 ? (st.spreadPts - st.meanSpreadPts) / st.sdSpreadPts : 0;
   }

   // Gate: reject if current spread > k σ above mean (volatile/illiquid period).
   bool SpreadAcceptable(double maxZ=2.0) const { return st.zSpread <= maxZ; }
   // Gate: reject if spread cost > k % of ATR (would invalidate R:R).
   bool CostAcceptable(double atr, double maxFrac=0.20) const
   {
      return atr > 0 ? (st.spread / atr) < maxFrac : true;
   }
};

#endif
