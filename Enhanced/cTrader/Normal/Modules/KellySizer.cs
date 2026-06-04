using System;

namespace GodmodeOfea.Enhanced
{
    public static class KellySizer
    {
        // Inputs validated — garbage in would otherwise propagate silently into
        // RiskPct (brief §12 rule 2). p ∈ [0,1], b > 0 required.
        public static double FullKelly(double p, double b)
        {
            if (b <= 0) return 0;
            if (p < 0 || p > 1.0) return 0;
            return (p * (b + 1.0) - 1.0) / b;
        }

        public static double FractionalKelly(double p, double b, double kappa = 0.25)
        {
            if (kappa <= 0) return 0;
            return Math.Max(0, FullKelly(p, b)) * Math.Max(0, Math.Min(kappa, 1.0));
        }

        // Hard-capped at 2.0 per brief §12 rule 2.
        public static double RiskPctFromKelly(double p, double b, double kappa = 0.25)
            => Math.Min(2.0, FractionalKelly(p, b, kappa) * 100.0);

        public static double VolTargetLots(double targetVolPct, double equity, double perLotSigma)
        {
            if (perLotSigma <= 0 || equity <= 0) return 0;
            return equity * (targetVolPct / 100.0) / perLotSigma;
        }
    }
}
