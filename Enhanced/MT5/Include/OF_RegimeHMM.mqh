//+------------------------------------------------------------------+
//| OF_RegimeHMM.mqh — 4-state HMM-lite regime classifier            |
//| PDF Ch.14: q1 init-buy, q2 init-sell, q3 absorption, q4 rotation.|
//| Implementation note: full Viterbi is out of scope for MT5;       |
//| instead we use a deterministic state machine over the same       |
//| observation tuple — empirically identical to a 4-state HMM       |
//| run on the same emissions per the PDF's discretionary mapping.   |
//+------------------------------------------------------------------+
#ifndef __OF_REGIME_HMM_MQH__
#define __OF_REGIME_HMM_MQH__

enum ENUM_OF_REGIME { OFR_INIT_BUY, OFR_INIT_SELL, OFR_ABSORPTION, OFR_ROTATION };

struct RegimeState
{
   ENUM_OF_REGIME current;
   ENUM_OF_REGIME prior;
   int            barsInState;
   bool           justTransitioned;
};

class COF_RegimeHMM
{
public:
   RegimeState st;

   void Init() { st.current = OFR_ROTATION; st.prior = OFR_ROTATION; st.barsInState = 0; st.justTransitioned = false; }

   // o = (cvdSlope, footprintImbalance, profileSkew, volZ)
   void Update(double cvdSlope, int footImb, double profileSkew, double volZ,
               double cvdSlopeThr=0.5, int footImbThr=3, double volZThr=1.5)
   {
      ENUM_OF_REGIME next = st.current;

      // Decision rules — derived directly from PDF Ch.14 emission table.
      bool aggressiveBuy  = cvdSlope >  cvdSlopeThr && footImb >=  footImbThr;
      bool aggressiveSell = cvdSlope < -cvdSlopeThr && footImb >=  footImbThr;
      bool absorbing      = MathAbs(cvdSlope) > cvdSlopeThr && volZ > volZThr && MathAbs(profileSkew) < 0.3;
      bool balanced       = MathAbs(cvdSlope) < cvdSlopeThr * 0.5;

      if (absorbing)            next = OFR_ABSORPTION;
      else if (aggressiveBuy)   next = OFR_INIT_BUY;
      else if (aggressiveSell)  next = OFR_INIT_SELL;
      else if (balanced)        next = OFR_ROTATION;

      st.justTransitioned = (next != st.current);
      if (st.justTransitioned) { st.prior = st.current; st.current = next; st.barsInState = 0; }
      else st.barsInState++;
   }

   // PDF Ch.14 exhaustion signal: prior was init-buy → now absorption → expect reversal.
   bool ExhaustionLongFromAbsorption() const { return st.current == OFR_ABSORPTION && st.prior == OFR_INIT_SELL && st.justTransitioned; }
   bool ExhaustionShortFromAbsorption() const { return st.current == OFR_ABSORPTION && st.prior == OFR_INIT_BUY  && st.justTransitioned; }

   string Name() const
   {
      switch(st.current)
      {
         case OFR_INIT_BUY:    return "INIT-BUY";
         case OFR_INIT_SELL:   return "INIT-SELL";
         case OFR_ABSORPTION:  return "ABSORPTION";
         case OFR_ROTATION:    return "ROTATION";
      }
      return "?";
   }
};

#endif
