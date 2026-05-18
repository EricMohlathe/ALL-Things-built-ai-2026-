//+------------------------------------------------------------------+
//| OF_PriceAction.mqh — 100%-aligned PA: BOS, CHoCH, EqH/L, FVG     |
//| Per PDF Ch.9 Rosetta. Each concept has an order-flow analogue;   |
//| we add the price-action eye that complements the OF stack.       |
//+------------------------------------------------------------------+
#ifndef __OF_PRICE_ACTION_MQH__
#define __OF_PRICE_ACTION_MQH__

enum ENUM_PA_STRUCTURE { PA_NONE, PA_BOS_UP, PA_BOS_DOWN, PA_CHOCH_UP, PA_CHOCH_DOWN };

struct PriceActionState
{
   double  lastSwingHigh, lastSwingLow;
   datetime swingHighT,    swingLowT;
   ENUM_PA_STRUCTURE structure;
   bool    equalHighsCluster;     // ≥2 equal highs within tolEqual
   bool    equalLowsCluster;
   bool    fvgUp;                  // bullish FVG just formed
   bool    fvgDown;
   double  fvgUpTop, fvgUpBot;
   double  fvgDownTop, fvgDownBot;
};

class COF_PriceAction
{
public:
   PriceActionState st;

   // Call once per closed bar with current high/low/close arrays (index 0 = newest).
   void Update(const double &highs[], const double &lows[], const double &closes[],
               int lookbackSwing=20, double tolEqualATR=0.10, double atr=0.0)
   {
      if (ArraySize(highs) < lookbackSwing + 3) return;

      // Detect swings (3-bar fractal).
      double curSwingH = -1, curSwingL = 1e18;
      int    iH = -1, iL = -1;
      for (int i = 1; i < lookbackSwing - 1; i++)
      {
         if (highs[i] > highs[i-1] && highs[i] > highs[i+1] && highs[i] > curSwingH)
         { curSwingH = highs[i]; iH = i; }
         if (lows[i]  < lows[i-1]  && lows[i]  < lows[i+1]  && lows[i]  < curSwingL)
         { curSwingL = lows[i];   iL = i; }
      }
      if (iH >= 0) st.lastSwingHigh = curSwingH;
      if (iL >= 0) st.lastSwingLow  = curSwingL;

      // BOS / CHoCH detection.
      // BOS_UP: prior structure was lower-highs, new bar closes above last swing high.
      // CHoCH_UP: prior structure was lower-highs *and* lower-lows, new close above lastSwingHigh.
      st.structure = PA_NONE;
      double c = closes[0];
      if (iH >= 0 && c > st.lastSwingHigh)
         st.structure = (st.structure == PA_BOS_DOWN ? PA_CHOCH_UP : PA_BOS_UP);
      else if (iL >= 0 && c < st.lastSwingLow)
         st.structure = (st.structure == PA_BOS_UP ? PA_CHOCH_DOWN : PA_BOS_DOWN);

      // Equal highs / lows cluster — within tolEqualATR × ATR of each other.
      double tol = tolEqualATR * (atr > 0 ? atr : 0.0001 * c);
      st.equalHighsCluster = false;
      st.equalLowsCluster  = false;
      int eqH = 0, eqL = 0;
      for (int i = 1; i < lookbackSwing && i < ArraySize(highs); i++)
      {
         if (iH >= 0 && MathAbs(highs[i] - st.lastSwingHigh) <= tol) eqH++;
         if (iL >= 0 && MathAbs(lows[i]  - st.lastSwingLow)  <= tol) eqL++;
      }
      st.equalHighsCluster = (eqH >= 2);
      st.equalLowsCluster  = (eqL >= 2);

      // FVG = three-bar imbalance.
      // Bullish FVG: low[0] > high[2] → wick-only single-print region (high[2] .. low[0]).
      st.fvgUp = false; st.fvgDown = false;
      if (ArraySize(highs) >= 3)
      {
         if (lows[0] > highs[2])
         { st.fvgUp = true; st.fvgUpBot = highs[2]; st.fvgUpTop = lows[0]; }
         if (highs[0] < lows[2])
         { st.fvgDown = true; st.fvgDownBot = highs[0]; st.fvgDownTop = lows[2]; }
      }
   }
};

#endif
