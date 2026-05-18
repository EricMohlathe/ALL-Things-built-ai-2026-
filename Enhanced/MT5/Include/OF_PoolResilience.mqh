//+------------------------------------------------------------------+
//| OF_PoolResilience.mqh — Liquidity-pool resilience score          |
//| PDF Ch.3 (V06): density, depth, resilience = refilled/consumed. |
//| Extends OF_IcebergTracker.mqh — low resilience = exploitable.    |
//+------------------------------------------------------------------+
#ifndef __OF_POOL_RESILIENCE_MQH__
#define __OF_POOL_RESILIENCE_MQH__

struct PoolMetrics
{
   double density;          // orders / tick within ±k ticks
   double depth;             // total resting size within range
   double resilience;        // refilled / consumed ratio (0 = exhausted, ≥1 = iceberg)
   bool   exploitable;       // density high, depth high, resilience low
};

class COF_PoolResilience
{
public:
   PoolMetrics last;

   // size_consumed: aggregate size that crossed this level in the last N bars
   // size_refilled: aggregate resting size that re-appeared at the level after consumption
   void Compute(double consumed, double refilled, double levelSize, int orderCount, int tickRange)
   {
      last.depth      = levelSize;
      last.density    = tickRange > 0 ? (double)orderCount / (double)tickRange : 0;
      last.resilience = consumed > 0 ? refilled / consumed : 0;
      // PDF: exploitable iff density × depth large, resilience small
      last.exploitable = (last.density > 0.5 && last.depth > 0 && last.resilience < 0.30);
   }
};

#endif
