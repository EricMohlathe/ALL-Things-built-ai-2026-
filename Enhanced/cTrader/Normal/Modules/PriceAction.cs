using System;

namespace GodmodeOfea.Enhanced
{
    public enum PaStructure { None, BosUp, BosDown, ChochUp, ChochDown }

    public class PriceAction
    {
        public double LastSwingHigh, LastSwingLow;
        public PaStructure Structure;
        public bool EqualHighsCluster, EqualLowsCluster;
        public bool FvgUp, FvgDown;
        public double FvgUpTop, FvgUpBot, FvgDownTop, FvgDownBot;

        public void Update(double[] highs, double[] lows, double[] closes,
                           int lookbackSwing = 20, double tolEqualAtr = 0.10, double atr = 0)
        {
            if (highs.Length < lookbackSwing + 3) return;
            double curH = -1, curL = 1e18;
            int iH = -1, iL = -1;
            for (int i = 1; i < lookbackSwing - 1; i++)
            {
                if (highs[i] > highs[i - 1] && highs[i] > highs[i + 1] && highs[i] > curH)
                { curH = highs[i]; iH = i; }
                if (lows[i] < lows[i - 1] && lows[i] < lows[i + 1] && lows[i] < curL)
                { curL = lows[i]; iL = i; }
            }
            if (iH >= 0) LastSwingHigh = curH;
            if (iL >= 0) LastSwingLow  = curL;

            Structure = PaStructure.None;
            double c = closes[0];
            if (iH >= 0 && c > LastSwingHigh) Structure = PaStructure.BosUp;
            else if (iL >= 0 && c < LastSwingLow) Structure = PaStructure.BosDown;

            double tol = tolEqualAtr * (atr > 0 ? atr : 0.0001 * c);
            int eqH = 0, eqL = 0;
            for (int i = 1; i < lookbackSwing && i < highs.Length; i++)
            {
                if (iH >= 0 && Math.Abs(highs[i] - LastSwingHigh) <= tol) eqH++;
                if (iL >= 0 && Math.Abs(lows[i]  - LastSwingLow)  <= tol) eqL++;
            }
            EqualHighsCluster = eqH >= 2;
            EqualLowsCluster  = eqL >= 2;

            FvgUp = false; FvgDown = false;
            if (highs.Length >= 3)
            {
                if (lows[0] > highs[2])  { FvgUp = true;   FvgUpBot = highs[2];  FvgUpTop = lows[0]; }
                if (highs[0] < lows[2])  { FvgDown = true; FvgDownBot = highs[0]; FvgDownTop = lows[2]; }
            }
        }
    }
}
