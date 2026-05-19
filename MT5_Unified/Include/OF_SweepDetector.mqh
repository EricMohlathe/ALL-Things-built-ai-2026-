//+------------------------------------------------------------------+
//| OF_SweepDetector.mqh — 6-precondition liquidity-sweep detector   |
//| Per PDF Ch.6 (V06): equal-level + HTF + session + momentum +     |
//| absorption + delta-flip. Six gates compounded.                   |
//+------------------------------------------------------------------+
#ifndef __OF_SWEEP_DETECTOR_MQH__
#define __OF_SWEEP_DETECTOR_MQH__

struct SweepResult
{
   bool fired;
   int  direction;        // +1 = buy-side sweep (short setup), -1 = sell-side sweep (long setup)
   int  preconditionsPassed; // 0..6
   double sweepExtreme;   // level swept (for SL placement +/- spread)
   double absorptionScore; // volume at extreme / mean volume
};

class COF_SweepDetector
{
public:
   SweepResult last;
   // Zero-initialise on construction — callers (e.g. ComputeCompositeProbability)
   // read `last.preconditionsPassed` before Evaluate() runs on the first bar
   // and would otherwise see uninitialised memory.
   COF_SweepDetector()
   {
      last.fired = false;
      last.direction = 0;
      last.preconditionsPassed = 0;
      last.sweepExtreme = 0.0;
      last.absorptionScore = 0.0;
   }

   // All inputs are bools/numbers the caller has already computed via OF_*.mqh modules.
   // This keeps the sweep detector platform-agnostic and unit-testable.
   void Evaluate(
      bool   equalLevelCluster,     // ≥2 equal H/L (from OF_PriceAction)
      bool   htfLevelProximity,     // sweep at H4 or D1 level (from OF_HTFAlignment)
      bool   inKillZone,            // LDN_MAIN or NY_MAIN (from OF_SessionGate)
      bool   momentumExhaustion,    // RSI extreme / CVD divergence (from OF_DeltaEnhanced)
      bool   absorptionConfirmed,   // high vol at extreme, no progress (from OF_AbsorptionStars)
      bool   deltaFlipped,          // CVD reversed within 3 bars (from OF_DeltaEnhanced)
      int    dir,                   // proposed direction (+1 short / -1 long)
      double extremePrice,
      double absorptionScore=0)
   {
      last.preconditionsPassed = 0;
      if (equalLevelCluster)   last.preconditionsPassed++;
      if (htfLevelProximity)   last.preconditionsPassed++;
      if (inKillZone)          last.preconditionsPassed++;
      if (momentumExhaustion)  last.preconditionsPassed++;
      if (absorptionConfirmed) last.preconditionsPassed++;
      if (deltaFlipped)        last.preconditionsPassed++;

      last.fired           = (last.preconditionsPassed == 6);
      last.direction       = dir;
      last.sweepExtreme    = extremePrice;
      last.absorptionScore = absorptionScore;
   }

   // PDF Ch.8 empirical edge table:
   // 6/6 preconditions: E[R] ≈ +1.18, win% ≈ 67%
   // 5/6 preconditions: E[R] ≈ +0.94, win% ≈ 63%
   // 4/6 preconditions: E[R] ≈ +0.55, win% ≈ 58%
   // <4/6: not actionable.
   double ExpectedR() const
   {
      switch (last.preconditionsPassed)
      {
         case 6: return 1.18;
         case 5: return 0.94;
         case 4: return 0.55;
         case 3: return 0.31;
         default: return 0.08;
      }
   }
   double EmpiricalWinRate() const
   {
      switch (last.preconditionsPassed)
      {
         case 6: return 0.67;
         case 5: return 0.63;
         case 4: return 0.58;
         case 3: return 0.54;
         default: return 0.49;
      }
   }
};

#endif
