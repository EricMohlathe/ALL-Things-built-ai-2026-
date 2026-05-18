//+------------------------------------------------------------------+
//| OF_KellySizer.mqh — Fractional Kelly + vol-target sizing         |
//| PDF Ch.11. RiskPct hard-cap @2.0 preserved per brief §12 rule 2.|
//+------------------------------------------------------------------+
#ifndef __OF_KELLY_SIZER_MQH__
#define __OF_KELLY_SIZER_MQH__

class COF_KellySizer
{
public:
   // Full Kelly: f* = (p*(b+1) - 1) / b
   static double FullKelly(double winProb, double payoffOdds)
   {
      if (payoffOdds <= 0) return 0;
      return (winProb * (payoffOdds + 1.0) - 1.0) / payoffOdds;
   }
   // Fractional Kelly: f_use = κ × f*. κ ∈ {0.25, 0.5} for safety.
   static double FractionalKelly(double winProb, double payoffOdds, double kappa=0.25)
   {
      double f = FullKelly(winProb, payoffOdds);
      return MathMax(0.0, f) * MathMax(0.0, MathMin(kappa, 1.0));
   }
   // RiskPct from Kelly, hard-capped at 2.0 (brief §12 rule 2).
   static double RiskPctFromKelly(double winProb, double payoffOdds, double kappa=0.25)
   {
      double f = FractionalKelly(winProb, payoffOdds, kappa);
      double pct = f * 100.0;
      if (pct > 2.0) pct = 2.0;
      return pct;
   }
   // Volatility-target sizing: σ_pos × √N = target_pct × equity.
   // Returns lots that achieve target portfolio σ given symbol's per-lot σ in account ccy.
   static double VolTargetLots(double targetVolPct, double equity, double perLotSigma)
   {
      if (perLotSigma <= 0 || equity <= 0) return 0;
      double targetDollarSigma = equity * (targetVolPct / 100.0);
      return targetDollarSigma / perLotSigma;
   }
};

#endif
