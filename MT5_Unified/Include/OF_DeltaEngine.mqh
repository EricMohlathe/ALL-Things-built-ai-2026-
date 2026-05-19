//+------------------------------------------------------------------+
//|                                              OF_DeltaEngine.mqh  |
//|  Tick-delta accumulator + CVD + divergence  (brief §11.1, §11.5) |
//+------------------------------------------------------------------+
#property strict
#ifndef OF_DELTA_ENGINE_MQH
#define OF_DELTA_ENGINE_MQH

#include "OF_Common.mqh"

class CDeltaEngine
  {
private:
   string m_sym;
   int    m_lookback;

   // tick-level accumulators (reset each new bar — brief §10.1)
   double m_tickBuy;
   double m_tickSell;
   datetime m_lastBarTime;

   // bar-level series (brief §10.2)
   double m_barDelta[];
   double m_volume[];
   double m_cvd[];

public:
   void Init(const string sym, const int lookback)
     {
      m_sym = sym;
      m_lookback = MathMax(lookback, 30);
      m_tickBuy = 0; m_tickSell = 0; m_lastBarTime = 0;
      ArrayResize(m_barDelta, m_lookback);  ArrayInitialize(m_barDelta, 0.0);
      ArrayResize(m_volume,   m_lookback);  ArrayInitialize(m_volume, 0.0);
      ArrayResize(m_cvd,      m_lookback);  ArrayInitialize(m_cvd, 0.0);
      ArraySetAsSeries(m_barDelta, true);
      ArraySetAsSeries(m_volume,   true);
      ArraySetAsSeries(m_cvd,      true);
     }

   //--- Direction-flag based aggregation (brief §11.1)
   void OnTickAccumulate()
     {
      MqlTick t;
      if(!SymbolInfoTick(m_sym, t)) return;
      const double v = (t.volume_real > 0.0) ? t.volume_real : (double)t.volume;
      if((t.flags & TICK_FLAG_BUY)  != 0) m_tickBuy  += v;
      if((t.flags & TICK_FLAG_SELL) != 0) m_tickSell += v;
     }

   //--- Returns true on first call inside a new bar
   bool DetectNewBar()
     {
      const datetime cur = iTime(m_sym, _Period, 0);
      if(cur == m_lastBarTime) return false;
      m_lastBarTime = cur; return true;
     }

   //--- Snapshot the bar that just closed; reset accumulators
   void OnBarClose()
     {
      const double bd = m_tickBuy - m_tickSell;
      const double tv = m_tickBuy + m_tickSell;
      // shift series right (newest at [0])
      for(int i = m_lookback - 1; i > 0; --i)
        {
         m_barDelta[i] = m_barDelta[i-1];
         m_volume[i]   = m_volume[i-1];
         m_cvd[i]      = m_cvd[i-1];
        }
      m_barDelta[0] = bd;
      m_volume[0]   = (tv > 0.0) ? tv : (double)iVolume(m_sym, _Period, 1);
      m_cvd[0]      = m_cvd[1] + bd;
      m_tickBuy = 0; m_tickSell = 0;
     }

   double Cvd()        const { return m_cvd[0]; }
   double BarDelta()   const { return m_barDelta[0]; }
   double Volume(int i) const { return (i >= 0 && i < m_lookback) ? m_volume[i] : 0.0; }
   double Delta(int i)  const { return (i >= 0 && i < m_lookback) ? m_barDelta[i] : 0.0; }

   //--- Z-scores over the lookback window
   double VolumeZ() const
     {
      double mean = 0, sd = 0;
      for(int i = 0; i < m_lookback; i++) mean += m_volume[i];
      mean /= m_lookback;
      for(int i = 0; i < m_lookback; i++) sd += (m_volume[i]-mean)*(m_volume[i]-mean);
      sd = MathSqrt(sd / m_lookback);
      if(sd < 1e-9) return 0.0;
      return (m_volume[0] - mean) / sd;
     }

   double DeltaZ() const
     {
      double mean = 0, sd = 0;
      for(int i = 0; i < m_lookback; i++) mean += m_barDelta[i];
      mean /= m_lookback;
      for(int i = 0; i < m_lookback; i++) sd += (m_barDelta[i]-mean)*(m_barDelta[i]-mean);
      sd = MathSqrt(sd / m_lookback);
      if(sd < 1e-9) return 0.0;
      return (m_barDelta[0] - mean) / sd;
     }

   //--- Slope = simple last-5-bar net change
   double CvdSlope5() const
     {
      const int n = MathMin(5, m_lookback - 1);
      return m_cvd[0] - m_cvd[n];
     }

   //--- Divergence detection — brief §11.5
   bool BullishDivergence() const
     {
      double pLow = m_lookback > 0 ? iLow(m_sym, _Period, 1) : 0;
      for(int i = 2; i < 20 && i < m_lookback; i++)
         pLow = MathMin(pLow, iLow(m_sym, _Period, i));
      const double curLow = iLow(m_sym, _Period, 1);
      double cvdMin = m_cvd[1];
      for(int i = 2; i < 20 && i < m_lookback; i++)
         if(m_cvd[i] < cvdMin) cvdMin = m_cvd[i];
      return (curLow <= pLow + Point()) && (m_cvd[1] > cvdMin + 1e-9);
     }

   bool BearishDivergence() const
     {
      double pHigh = iHigh(m_sym, _Period, 1);
      for(int i = 2; i < 20 && i < m_lookback; i++)
         pHigh = MathMax(pHigh, iHigh(m_sym, _Period, i));
      const double curHigh = iHigh(m_sym, _Period, 1);
      double cvdMax = m_cvd[1];
      for(int i = 2; i < 20 && i < m_lookback; i++)
         if(m_cvd[i] > cvdMax) cvdMax = m_cvd[i];
      return (curHigh >= pHigh - Point()) && (m_cvd[1] < cvdMax - 1e-9);
     }
  };

#endif
