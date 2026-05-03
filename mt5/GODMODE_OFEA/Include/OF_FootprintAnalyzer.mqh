//+------------------------------------------------------------------+
//|                                       OF_FootprintAnalyzer.mqh   |
//|  Absorption / Stacked imbalance / Unfinished auction detection   |
//|  Brief §5 GATE 6                                                 |
//+------------------------------------------------------------------+
#property strict
#ifndef OF_FOOTPRINT_ANALYZER_MQH
#define OF_FOOTPRINT_ANALYZER_MQH

#include "OF_Common.mqh"
#include "OF_DeltaEngine.mqh"

class CFootprintAnalyzer
  {
private:
   string m_sym;
   double m_volZThr;
   double m_deltaZThr;
   int    m_minStackedRows;
   double m_imbalanceRatio;

public:
   void Init(const string sym, const double volZ, const double deltaZ,
             const int stackedRows, const double imbalanceRatio)
     {
      m_sym = sym;
      m_volZThr = volZ;
      m_deltaZThr = deltaZ;
      m_minStackedRows = stackedRows;
      m_imbalanceRatio = imbalanceRatio;
     }

   //--- Bullish absorption: large vol, negative delta, but body closes up
   bool BullishAbsorption(const CDeltaEngine &de) const
     {
      const double volZ = de.VolumeZ();
      const double bd   = de.BarDelta();
      const double o = iOpen(m_sym, _Period, 1);
      const double c = iClose(m_sym, _Period, 1);
      return (bd < 0) && (volZ >= m_volZThr) && (c >= o);
     }

   bool BearishAbsorption(const CDeltaEngine &de) const
     {
      const double volZ = de.VolumeZ();
      const double bd   = de.BarDelta();
      const double o = iOpen(m_sym, _Period, 1);
      const double c = iClose(m_sym, _Period, 1);
      return (bd > 0) && (volZ >= m_volZThr) && (c <= o);
     }

   //--- 3+ consecutive same-sign delta bars → stacked imbalance
   bool StackedBullImbalance(const CDeltaEngine &de) const
     {
      for(int i = 0; i < m_minStackedRows; i++)
         if(de.Delta(i) <= 0) return false;
      return true;
     }
   bool StackedBearImbalance(const CDeltaEngine &de) const
     {
      for(int i = 0; i < m_minStackedRows; i++)
         if(de.Delta(i) >= 0) return false;
      return true;
     }

   //--- Unfinished auction: 0-volume row at bar extreme proxy =
   //    bar's range extends into a price area with no follow-through (low ATR-relative move next bar)
   bool UnfinishedAuction() const
     {
      const double prevH = iHigh(m_sym, _Period, 2);
      const double prevL = iLow(m_sym, _Period, 2);
      const double curH  = iHigh(m_sym, _Period, 1);
      const double curL  = iLow(m_sym, _Period, 1);
      // High pokes above prior with weak follow-through: cur high > prev high but cur close near prev close
      const double curC  = iClose(m_sym, _Period, 1);
      const double prevC = iClose(m_sym, _Period, 2);
      const double atr   = ATR(m_sym, _Period, 14);
      if(atr <= 0) return false;
      bool poorHigh = (curH > prevH) && (curC - prevC) < 0.25 * atr;
      bool poorLow  = (curL < prevL) && (prevC - curC) < 0.25 * atr;
      return poorHigh || poorLow;
     }
  };

#endif
