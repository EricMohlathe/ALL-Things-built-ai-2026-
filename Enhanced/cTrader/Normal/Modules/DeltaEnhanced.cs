using System;

namespace GodmodeOfea.Enhanced
{
    public enum CvdRegime { TrendConfirming, Divergent, InverseDivergent, Neutral }

    public class DeltaEnhanced
    {
        private readonly double[] _d, _p, _c;
        private ulong _idx;            // ulong wraps cleanly; year-scale safe
        public double Cvd, CvdSlope, ZScore;
        public bool Climax, DeltaFlipped;
        public CvdRegime Regime;

        public DeltaEnhanced(int lookback = 20) { _d = new double[lookback]; _p = new double[lookback]; _c = new double[lookback]; }

        public void OnBar(double barDelta, double closePrice, double climaxThr = 2.0, int flipBars = 3)
        {
            Cvd += barDelta;
            ulong L = (ulong)_d.Length;
            _d[(int)(_idx % L)] = barDelta;
            _p[(int)(_idx % L)] = closePrice;
            _c[(int)(_idx % L)] = Cvd;
            _idx++;
            int n = (int)Math.Min(_idx, L);
            double sum = 0, sum2 = 0;
            for (int i = 0; i < n; i++) { sum += _d[i]; sum2 += _d[i] * _d[i]; }
            var mu = n > 0 ? sum / n : 0;
            var v  = n > 0 ? (sum2 / n) - (mu * mu) : 0;
            if (v < 0 || double.IsNaN(v) || double.IsInfinity(v)) v = 0;  // FP guard
            var sd = v > 0 ? Math.Sqrt(v) : 0;
            ZScore = sd > 0 ? (barDelta - mu) / sd : 0;
            Climax = Math.Abs(ZScore) >= climaxThr;
            // Slope — normalised by mean absolute delta so CvdSlope ∈ ~[-1, +1]
            // and is unit-independent of symbol volume. cvdSlopeThr=0.5 then
            // means "more than half the lookback bars pull in one direction".
            if (n >= 2)
            {
                int iNow  = (int)((_idx - 1)        % L);
                int iPast = (int)((_idx - (ulong)n) % L);
                double rawSlope = (_c[iNow] - _c[iPast]) / (double)n;
                double sumAbs = 0;
                for (int j = 0; j < n; j++) sumAbs += Math.Abs(_d[j]);
                double meanAbsBd = n > 0 ? sumAbs / n : 0;
                CvdSlope = meanAbsBd > 0 ? rawSlope / meanAbsBd : 0;
            }
            DeltaFlipped = false;
            if (n > flipBars)
            {
                int signNow = barDelta > 0 ? 1 : (barDelta < 0 ? -1 : 0);
                for (int k = 1; k <= flipBars && k < n; k++)
                {
                    double d = _d[(int)((_idx - 1 - (ulong)k) % L)];
                    int s = d > 0 ? 1 : (d < 0 ? -1 : 0);
                    if (s != 0 && signNow != 0 && s == -signNow) { DeltaFlipped = true; break; }
                }
            }
            ClassifyRegime(n);
        }
        private void ClassifyRegime(int n)
        {
            ulong L = (ulong)_d.Length;
            if ((ulong)n < L) { Regime = CvdRegime.Neutral; return; }
            int iNow  = (int)((_idx - 1)        % L);
            int iPast = (int)((_idx - (ulong)n) % L);
            double dPrice = _p[iNow] - _p[iPast];
            double dCVD   = _c[iNow] - _c[iPast];
            bool same = (dPrice > 0 && dCVD > 0) || (dPrice < 0 && dCVD < 0);
            bool opp  = (dPrice > 0 && dCVD < 0) || (dPrice < 0 && dCVD > 0);
            bool flat = Math.Abs(dPrice) < 0.0001 * Math.Abs(_p[iPast]);
            bool strong = Math.Abs(dCVD) > Math.Abs(Cvd) * 0.1;
            if (same) Regime = CvdRegime.TrendConfirming;
            else if (opp) Regime = CvdRegime.Divergent;
            else if (flat && strong) Regime = CvdRegime.InverseDivergent;
            else Regime = CvdRegime.Neutral;
        }
    }
}
