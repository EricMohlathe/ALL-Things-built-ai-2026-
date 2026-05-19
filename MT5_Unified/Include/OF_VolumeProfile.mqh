//+------------------------------------------------------------------+
//|                                            OF_VolumeProfile.mqh  |
//|  POC / VAH / VAL / LVN / HVN + shape classifier                  |
//|  Brief §11.2 (algorithm) and §11.3 (D/P/b/THIN classifier)       |
//+------------------------------------------------------------------+
#property strict
#ifndef OF_VOLUME_PROFILE_MQH
#define OF_VOLUME_PROFILE_MQH

#include "OF_Common.mqh"

class CVolumeProfile
  {
private:
   string m_sym;
   int    m_bins;
   int    m_length;
   double m_va;       // value area % (e.g. 0.70)
   double m_lvnRatio;
   double m_hvnRatio;

   double m_binVol[];
   int    m_lvnFlag[];
   int    m_hvnFlag[];
   double m_lo, m_hi, m_binSize;
   double m_poc, m_vah, m_val;
   ENUM_PROFILE_SHAPE m_shape;
   double m_skew, m_peak;

public:
   void Init(const string sym, const int bins, const int length,
             const double va, const double lvnR, const double hvnR)
     {
      m_sym = sym; m_bins = bins; m_length = length;
      m_va = va; m_lvnRatio = lvnR; m_hvnRatio = hvnR;
      ArrayResize(m_binVol, m_bins);
      ArrayResize(m_lvnFlag, m_bins);
      ArrayResize(m_hvnFlag, m_bins);
      m_poc = m_vah = m_val = 0; m_shape = SHAPE_UNKNOWN;
     }

   //--- Recompute on bar close. Returns true on success.
   bool Recompute()
     {
      ArrayInitialize(m_binVol, 0.0);
      ArrayInitialize(m_lvnFlag, 0);
      ArrayInitialize(m_hvnFlag, 0);

      if(m_length < 5) return false;
      double hi = iHigh(m_sym, _Period, 1), lo = iLow(m_sym, _Period, 1);
      for(int i = 1; i <= m_length; i++)
        {
         hi = MathMax(hi, iHigh(m_sym, _Period, i));
         lo = MathMin(lo, iLow(m_sym, _Period, i));
        }
      m_lo = lo; m_hi = hi;
      m_binSize = (hi - lo) / m_bins;
      if(m_binSize <= 0) return false;

      for(int i = 1; i <= m_length; i++)
        {
         const double c = iClose(m_sym, _Period, i);
         int b = (int)MathFloor((c - lo) / m_binSize);
         if(b < 0) b = 0; if(b >= m_bins) b = m_bins - 1;
         m_binVol[b] += (double)iVolume(m_sym, _Period, i);
        }

      // POC = bin with max volume
      int pocBin = 0;
      for(int i = 1; i < m_bins; i++) if(m_binVol[i] > m_binVol[pocBin]) pocBin = i;
      m_poc = lo + (pocBin + 0.5) * m_binSize;

      // Value area expansion outward from POC until VA% reached
      double total = 0;
      for(int i = 0; i < m_bins; i++) total += m_binVol[i];
      const double target = total * m_va;
      double acc = m_binVol[pocBin];
      int hiBin = pocBin, loBin = pocBin;
      while(acc < target && (hiBin < m_bins - 1 || loBin > 0))
        {
         double up = (hiBin + 1 < m_bins) ? m_binVol[hiBin + 1] : -1;
         double dn = (loBin - 1 >= 0)     ? m_binVol[loBin - 1] : -1;
         if(up >= dn && up >= 0) { hiBin++; acc += up; }
         else if(dn >= 0)        { loBin--; acc += dn; }
         else break;
        }
      m_vah = lo + (hiBin + 1) * m_binSize;
      m_val = lo + loBin * m_binSize;

      // LVN/HVN classification
      const double pocVol = m_binVol[pocBin];
      for(int i = 0; i < m_bins; i++)
        {
         if(m_binVol[i] < pocVol * m_lvnRatio) m_lvnFlag[i] = 1;
         if(m_binVol[i] > pocVol * m_hvnRatio) m_hvnFlag[i] = 1;
        }

      ClassifyShape(pocBin, pocVol);
      return true;
     }

private:
   void ClassifyShape(const int pocBin, const double pocVol)
     {
      // Use lowest- and highest-filled bin (bins with vol > 0) for skew direction
      int lowBin = -1, highBin = -1;
      for(int i = 0; i < m_bins; i++)
         if(m_binVol[i] > 0) { if(lowBin < 0) lowBin = i; highBin = i; }
      if(lowBin < 0) { m_shape = SHAPE_UNKNOWN; return; }

      const int midBin = (lowBin + highBin) / 2;
      double upper = 0, lower = 0;
      for(int i = midBin; i <= highBin; i++) upper += m_binVol[i];
      for(int i = lowBin; i < midBin; i++)  lower += m_binVol[i];
      const double tot = upper + lower;
      m_skew = (tot > 0) ? (upper - lower) / tot : 0.0;

      // Peakedness = poc vs mean of non-zero bins
      double sum = 0; int nz = 0;
      for(int i = 0; i < m_bins; i++) if(m_binVol[i] > 0) { sum += m_binVol[i]; nz++; }
      m_peak = (nz > 0 && sum > 0) ? pocVol / (sum / nz) : 1.0;

      if(MathAbs(m_skew) < 0.10 && m_peak > 2.0) m_shape = SHAPE_D;
      else if(m_skew > 0.20)                     m_shape = SHAPE_P;
      else if(m_skew < -0.20)                    m_shape = SHAPE_b;
      else if(m_peak < 1.3)                      m_shape = SHAPE_THIN;
      else                                       m_shape = SHAPE_D;
     }

public:
   double POC() const { return m_poc; }
   double VAH() const { return m_vah; }
   double VAL() const { return m_val; }
   ENUM_PROFILE_SHAPE Shape() const { return m_shape; }

   ENUM_MARKET_STATE State() const
     { return (m_shape == SHAPE_D) ? STATE_BALANCED :
              (m_shape == SHAPE_UNKNOWN ? STATE_UNKNOWN : STATE_IMBALANCED); }

   //--- Test which key level the price is at within tolerance pips
   ENUM_VP_LOC LocationAt(const double price, const double tolPips)
     {
      const double tol = tolPips * PipSize(m_sym);
      if(MathAbs(price - m_poc) < tol) return LOC_POC;
      if(MathAbs(price - m_vah) < tol) return LOC_VAH;
      if(MathAbs(price - m_val) < tol) return LOC_VAL;

      const int bin = (int)MathFloor((price - m_lo) / m_binSize);
      if(bin >= 0 && bin < m_bins)
        {
         if(m_lvnFlag[bin] != 0) return LOC_LVN;
         if(m_hvnFlag[bin] != 0) return LOC_HVN;
        }
      return LOC_NONE;
     }
  };

#endif
