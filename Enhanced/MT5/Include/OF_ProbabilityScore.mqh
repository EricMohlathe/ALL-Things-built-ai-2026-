//+------------------------------------------------------------------+
//| OF_ProbabilityScore.mqh — composite 0-100% setup grade           |
//| Aggregates F1-F5 gate stack + Enhanced gates (regime, sweep,     |
//| VWAP, PA, pool, spread) into a single probability number that    |
//| drives the visual Probability Bar indicator.                     |
//+------------------------------------------------------------------+
#ifndef __OF_PROB_SCORE_MQH__
#define __OF_PROB_SCORE_MQH__

struct ProbabilityWeights
{
   double f1_TripleConfluence;     // base build F1
   double f2_KillZone;              // base build F2
   double f3_HTFAlignment;          // base build F3
   double f4_CVDConfirmation;       // base build F4
   double f5_VPState;               // base build F5
   double f6_RegimeMatch;           // enhanced — HMM regime matches direction
   double f7_SweepPreconditions;    // enhanced — n/6 from OF_SweepDetector
   double f8_VWAPSide;              // enhanced — price on correct side of VWAP
   double f9_PriceAction;           // enhanced — BOS/CHoCH/EqH-L/FVG match
   double f10_PoolResilience;       // enhanced — pool exploitable
   double f11_SpreadAcceptable;     // enhanced — spread Z < 2σ
   double f12_RR;                   // R:R ≥ MinRR
};

class COF_ProbabilityScore
{
public:
   ProbabilityWeights w;
   double total;

   void DefaultWeights()
   {
      // Sum to 100. F1-F5 carry 50% (the base gate stack remains the spine).
      w.f1_TripleConfluence   = 12.0;
      w.f2_KillZone           =  8.0;
      w.f3_HTFAlignment       = 12.0;
      w.f4_CVDConfirmation    = 10.0;
      w.f5_VPState            =  8.0;
      w.f6_RegimeMatch        =  8.0;
      w.f7_SweepPreconditions = 12.0;
      w.f8_VWAPSide           =  6.0;
      w.f9_PriceAction        =  8.0;
      w.f10_PoolResilience    =  6.0;
      w.f11_SpreadAcceptable  =  4.0;
      w.f12_RR                =  6.0;
   }
   COF_ProbabilityScore() { DefaultWeights(); total = 0; }

   // Each gate input is in [0,1] — pass DOM-derived continuous values where possible,
   // or 0/1 for hard booleans.
   double Compute(double g1, double g2, double g3, double g4, double g5,
                  double g6, double g7, double g8, double g9, double g10, double g11, double g12)
   {
      total = w.f1_TripleConfluence   * Clamp01(g1)
            + w.f2_KillZone           * Clamp01(g2)
            + w.f3_HTFAlignment       * Clamp01(g3)
            + w.f4_CVDConfirmation    * Clamp01(g4)
            + w.f5_VPState            * Clamp01(g5)
            + w.f6_RegimeMatch        * Clamp01(g6)
            + w.f7_SweepPreconditions * Clamp01(g7)
            + w.f8_VWAPSide           * Clamp01(g8)
            + w.f9_PriceAction        * Clamp01(g9)
            + w.f10_PoolResilience    * Clamp01(g10)
            + w.f11_SpreadAcceptable  * Clamp01(g11)
            + w.f12_RR                * Clamp01(g12);
      return total;
   }

   // Letter grade for the dashboard.
   string Grade() const
   {
      if (total >= 85) return "A+";
      if (total >= 75) return "A";
      if (total >= 65) return "B";
      if (total >= 50) return "C";
      if (total >= 35) return "D";
      return "F";
   }
private:
   static double Clamp01(double x) { return x < 0 ? 0 : (x > 1 ? 1 : x); }
};

#endif
