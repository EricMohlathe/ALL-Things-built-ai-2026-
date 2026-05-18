//+------------------------------------------------------------------+
//| OF_VWAP.mqh — Volume-Weighted Average Price + bands              |
//| Session-anchored VWAP with 1σ/2σ bands. PDF Ch.1 / Ch.15.        |
//+------------------------------------------------------------------+
#ifndef __OF_VWAP_MQH__
#define __OF_VWAP_MQH__

struct VWAPState
{
   datetime anchor;        // session anchor (00:00 server time)
   double   cumPV;         // Σ price * volume
   double   cumV;          // Σ volume
   double   cumPV2;        // Σ price² * volume (for variance)
   double   vwap;
   double   sd;            // standard deviation
};

class COF_VWAP
{
public:
   VWAPState st;

   void Reset(datetime t)  { st.anchor = t; st.cumPV = 0; st.cumV = 0; st.cumPV2 = 0; st.vwap = 0; st.sd = 0; }
   bool IsNewSession(datetime t)
   {
      MqlDateTime a, n; TimeToStruct(st.anchor, a); TimeToStruct(t, n);
      return (a.day != n.day);
   }
   void Update(double typPrice, double vol, datetime t)
   {
      if (st.anchor == 0 || IsNewSession(t)) Reset(t);
      if (vol <= 0) return;
      st.cumPV  += typPrice * vol;
      st.cumPV2 += typPrice * typPrice * vol;
      st.cumV   += vol;
      if (st.cumV > 0)
      {
         st.vwap = st.cumPV / st.cumV;
         double var = (st.cumPV2 / st.cumV) - (st.vwap * st.vwap);
         // FP cancellation (var slightly negative when prices nearly constant) → 0.
         // Inf/NaN guard for extreme-priced symbols accumulating for very long.
         if (var < 0 || !MathIsValidNumber(var)) var = 0;
         st.sd   = var > 0 ? MathSqrt(var) : 0;
      }
   }
   double VWAP() const { return st.vwap; }
   double Upper(double k=1.0) const { return st.vwap + k * st.sd; }
   double Lower(double k=1.0) const { return st.vwap - k * st.sd; }

   // Distance from VWAP in units of σ — used as a "premium/discount" gate
   double ZScore(double price) const { return st.sd > 0 ? (price - st.vwap) / st.sd : 0; }
};

#endif
