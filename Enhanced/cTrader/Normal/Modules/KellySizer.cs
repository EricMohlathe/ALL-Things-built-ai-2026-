using System;

namespace GodmodeOfea.Enhanced
{
    public static class KellySizer
    {
        public static double FullKelly(double p, double b)
            => b <= 0 ? 0 : (p * (b + 1.0) - 1.0) / b;

        public static double FractionalKelly(double p, double b, double kappa = 0.25)
            => Math.Max(0, FullKelly(p, b)) * Math.Max(0, Math.Min(kappa, 1.0));

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
