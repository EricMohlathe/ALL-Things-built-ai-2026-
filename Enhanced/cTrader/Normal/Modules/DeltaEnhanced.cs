using System;

namespace GodmodeOfea.Enhanced
{
    public enum CvdRegime { TrendConfirming, Divergent, InverseDivergent, Neutral }

    public class DeltaEnhanced
    {
        private readonly double[] _d, _p, _c;
        private int _idx;
        public double Cvd, CvdSlope, ZScore;
        public bool Climax, DeltaFlipped;
        public CvdRegime Regime;

        public DeltaEnhanced(int lookback = 20) { _d = new double[lookback]; _p = new double[lookback]; _c = new double[lookback]; }

        public void OnBar(double barDelta, double closePrice, double climaxThr = 2.0, int flipBars = 3)
        {
            Cvd += barDelta;
            int L = _d.Length;
            _d[_idx % L] = barDelta;
            _p[_idx % L] = closePrice;
            _c[_idx % L] = Cvd;
            _idx++;
            int n = Math.Min(_idx, L);
            double sum = 0, sum2 = 0;
            for (int i = 0; i < n; i++) { sum += _d[i]; sum2 += _d[i] * _d[i]; }
            var mu = n > 0 ? sum / n : 0;
            var v  = n > 0 ? (sum2 / n) - (mu * mu) : 0;
            var sd = v > 0 ? Math.Sqrt(v) : 0;
            ZScore = sd > 0 ? (barDelta - mu) / sd : 0;
            Climax = Math.Abs(ZScore) >= climaxThr;
            if (n >= 2)
            {
                int iNow = (_idx - 1) % L;
                int iPast = (_idx - n) % L;
                CvdSlope = (_c[iNow] - _c[iPast]) / (double)n;
            }
            DeltaFlipped = false;
            if (n > flipBars)
            {
                int signNow = barDelta > 0 ? 1 : (barDelta < 0 ? -1 : 0);
                for (int k = 1; k <= flipBars && k < n; k++)
                {
                    double d = _d[(_idx - 1 - k) % L];
                    int s = d > 0 ? 1 : (d < 0 ? -1 : 0);
                    if (s != 0 && signNow != 0 && s == -signNow) { DeltaFlipped = true; break; }
                }
            }
            ClassifyRegime(n);
        }
        private void ClassifyRegime(int n)
        {
            int L = _d.Length;
            if (n < L) { Regime = CvdRegime.Neutral; return; }
            int iNow = (_idx - 1) % L;
            int iPast = (_idx - n) % L;
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
