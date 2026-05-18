using System;

namespace GodmodeOfea.Enhanced
{
    public enum OfRegime { InitBuy, InitSell, Absorption, Rotation }

    public class RegimeHMM
    {
        public OfRegime Current = OfRegime.Rotation;
        public OfRegime Prior   = OfRegime.Rotation;
        public int BarsInState;
        public bool JustTransitioned;

        public void Update(double cvdSlope, int footImb, double profileSkew, double volZ,
                           double cvdSlopeThr = 0.5, int footImbThr = 3, double volZThr = 1.5)
        {
            var next = Current;
            bool aggressiveBuy  = cvdSlope >  cvdSlopeThr && footImb >= footImbThr;
            bool aggressiveSell = cvdSlope < -cvdSlopeThr && footImb >= footImbThr;
            bool absorbing      = Math.Abs(cvdSlope) > cvdSlopeThr && volZ > volZThr && Math.Abs(profileSkew) < 0.3;
            bool balanced       = Math.Abs(cvdSlope) < cvdSlopeThr * 0.5;
            if (absorbing) next = OfRegime.Absorption;
            else if (aggressiveBuy) next = OfRegime.InitBuy;
            else if (aggressiveSell) next = OfRegime.InitSell;
            else if (balanced) next = OfRegime.Rotation;
            JustTransitioned = next != Current;
            if (JustTransitioned) { Prior = Current; Current = next; BarsInState = 0; }
            else BarsInState++;
        }
        public bool ExhaustionLongFromAbsorption  => Current == OfRegime.Absorption && Prior == OfRegime.InitSell && JustTransitioned;
        public bool ExhaustionShortFromAbsorption => Current == OfRegime.Absorption && Prior == OfRegime.InitBuy  && JustTransitioned;
    }
}
