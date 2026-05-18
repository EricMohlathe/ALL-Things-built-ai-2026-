//+------------------------------------------------------------------+
//| OF_DeltaEnhanced.mqh — 3-state CVD regime + climax + divergence  |
//| PDF Ch.2: trend-confirming / divergent / inverse-divergent.       |
//| Confirms existing OF_DeltaEngine.mqh and adds regime tagging.     |
//+------------------------------------------------------------------+
#ifndef __OF_DELTA_ENHANCED_MQH__
#define __OF_DELTA_ENHANCED_MQH__

enum ENUM_CVD_REGIME { CVD_TREND_CONFIRMING, CVD_DIVERGENT, CVD_INVERSE_DIVERGENT, CVD_NEUTRAL };

struct DeltaEnhancedState
{
   double  cvd;             // running CVD
   double  cvdSlope;        // (cvd_t − cvd_{t-W}) / W
   double  zScore;          // z-score of bar delta over lookback
   bool    climax;          // |z| ≥ climaxThr
   bool    deltaFlipped;    // delta sign changed within flipBars
   ENUM_CVD_REGIME regime;
};

class COF_DeltaEnhanced
{
private:
   double m_d[];            // rolling bar-delta window
   double m_p[];            // rolling price window
   double m_c[];             // rolling cvd window
   int    m_len, m_idx;
public:
   DeltaEnhancedState st;

   void Init(int lookback=20)
   {
      m_len = lookback; m_idx = 0;
      ArrayResize(m_d, m_len); ArrayInitialize(m_d, 0);
      ArrayResize(m_p, m_len); ArrayInitialize(m_p, 0);
      ArrayResize(m_c, m_len); ArrayInitialize(m_c, 0);
      st.cvd = 0;
   }
   void OnBar(double barDelta, double closePrice, double climaxThr=2.0, int flipBars=3)
   {
      st.cvd += barDelta;
      m_d[m_idx % m_len] = barDelta;
      m_p[m_idx % m_len] = closePrice;
      m_c[m_idx % m_len] = st.cvd;
      m_idx++;

      // z-score
      int n = MathMin(m_idx, m_len);
      double sum = 0, sum2 = 0;
      for (int i = 0; i < n; i++) { sum += m_d[i]; sum2 += m_d[i] * m_d[i]; }
      double mu = n > 0 ? sum / n : 0;
      double var = n > 0 ? (sum2 / n) - (mu * mu) : 0;
      double sd  = var > 0 ? MathSqrt(var) : 0;
      st.zScore = sd > 0 ? (barDelta - mu) / sd : 0;
      st.climax = MathAbs(st.zScore) >= climaxThr;

      // slope
      if (n >= 2)
      {
         int iNow = (m_idx - 1) % m_len;
         int iPast = (m_idx - n) % m_len;
         st.cvdSlope = (m_c[iNow] - m_c[iPast]) / (double)n;
      }
      else st.cvdSlope = 0;

      // delta flip detection
      st.deltaFlipped = false;
      if (n > flipBars)
      {
         int signNow = barDelta > 0 ? 1 : (barDelta < 0 ? -1 : 0);
         for (int k = 1; k <= flipBars && k < n; k++)
         {
            double d = m_d[(m_idx - 1 - k) % m_len];
            int s = d > 0 ? 1 : (d < 0 ? -1 : 0);
            if (s != 0 && signNow != 0 && s == -signNow) { st.deltaFlipped = true; break; }
         }
      }

      // regime classification (PDF Ch.2)
      ClassifyRegime();
   }
private:
   void ClassifyRegime()
   {
      int n = MathMin(m_idx, m_len);
      if (n < m_len) { st.regime = CVD_NEUTRAL; return; }
      int iNow = (m_idx - 1) % m_len;
      int iPast = (m_idx - n) % m_len;
      double dPrice = m_p[iNow] - m_p[iPast];
      double dCVD   = m_c[iNow] - m_c[iPast];
      // sign-agreement gives 4 states:
      //  - both same sign → trend-confirming
      //  - opposite signs → divergent (price makes new extreme, CVD doesn't)
      //  - cvd big, price flat → inverse-divergent (breakout failing)
      bool sameSign = (dPrice > 0 && dCVD > 0) || (dPrice < 0 && dCVD < 0);
      bool opposite = (dPrice > 0 && dCVD < 0) || (dPrice < 0 && dCVD > 0);
      double atrApprox = 0.0001 * MathAbs(m_p[iPast]);
      bool priceFlat   = MathAbs(dPrice) < atrApprox;
      bool cvdStrong   = MathAbs(dCVD) > st.cvd * 0.1;
      if (sameSign)              st.regime = CVD_TREND_CONFIRMING;
      else if (opposite)         st.regime = CVD_DIVERGENT;
      else if (priceFlat && cvdStrong) st.regime = CVD_INVERSE_DIVERGENT;
      else                       st.regime = CVD_NEUTRAL;
   }
};

#endif
