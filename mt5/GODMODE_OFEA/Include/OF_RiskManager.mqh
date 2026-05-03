//+------------------------------------------------------------------+
//|                                              OF_RiskManager.mqh  |
//|  Sizing + DD halt + spread guard + consec losses + news blackout |
//|  Brief §12 (non-negotiable kill switches)                        |
//+------------------------------------------------------------------+
#property strict
#ifndef OF_RISK_MANAGER_MQH
#define OF_RISK_MANAGER_MQH

#include "OF_Common.mqh"

class CRiskManager
  {
private:
   string m_sym;
   long   m_magic;
   double m_riskPct, m_riskHalfPct;
   double m_maxDDPct;
   int    m_maxConsecLosses;
   double m_maxSpreadMult;
   int    m_consecLosses;
   double m_dayStartEquity;
   datetime m_dayStart;
   double m_spreadMedian;
   bool   m_dayHalted;

   //--- Rolling spread median (last 100 bars sampled per tick — lightweight)
   double m_spreadHist[100];
   int    m_spreadIdx;
   bool   m_spreadFilled;

public:
   void Init(const string sym, const long magic,
             const double riskPct, const double riskHalf,
             const double maxDD, const int maxConsec, const double spreadMult)
     {
      m_sym = sym; m_magic = magic;
      m_riskPct = MathMin(riskPct, 2.0);   // brief §12 rule 2 hard cap
      m_riskHalfPct = riskHalf;
      m_maxDDPct = maxDD;
      m_maxConsecLosses = maxConsec;
      m_maxSpreadMult = spreadMult;
      m_consecLosses = 0;
      m_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
      m_dayStart = TimeCurrent();
      m_spreadIdx = 0; m_spreadFilled = false;
      m_dayHalted = false;
      ArrayInitialize(m_spreadHist, 0);
     }

   //--- Reset on UTC day rollover
   void OnDayRollover()
     {
      m_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
      m_consecLosses = 0;
      m_dayHalted = false;
     }

   //--- Sample spread for median (call from OnBar)
   void SampleSpread()
     {
      const double s = (double)SymbolInfoInteger(m_sym, SYMBOL_SPREAD) * SymbolInfoDouble(m_sym, SYMBOL_POINT);
      m_spreadHist[m_spreadIdx] = s;
      m_spreadIdx = (m_spreadIdx + 1) % 100;
      if(m_spreadIdx == 0) m_spreadFilled = true;

      // recompute median
      const int n = m_spreadFilled ? 100 : (m_spreadIdx == 0 ? 1 : m_spreadIdx);
      double sorted[100]; ArrayInitialize(sorted, 0);
      for(int i = 0; i < n; i++) sorted[i] = m_spreadHist[i];
      ArraySort(sorted);
      m_spreadMedian = sorted[n/2];
     }

   GateResult CheckDailyDrawdown() const
     {
      const double eq = AccountInfoDouble(ACCOUNT_EQUITY);
      if(m_dayStartEquity <= 0) return GR(true, "DD ok");
      const double pct = ((eq - m_dayStartEquity) / m_dayStartEquity) * 100.0;
      if(pct <= -m_maxDDPct) return GR(false, StringFormat("Daily DD %.2f%%", pct), pct);
      return GR(true, StringFormat("Daily DD %.2f%%", pct), pct);
     }

   GateResult CheckSpread() const
     {
      const double cur = (double)SymbolInfoInteger(m_sym, SYMBOL_SPREAD) * SymbolInfoDouble(m_sym, SYMBOL_POINT);
      if(m_spreadMedian <= 0) return GR(true, "no median yet", cur);
      if(cur > m_spreadMedian * m_maxSpreadMult)
         return GR(false, StringFormat("Spread blowout %.5f vs %.5f×%.1f", cur, m_spreadMedian, m_maxSpreadMult), cur);
      return GR(true, StringFormat("Spread ok %.5f", cur), cur);
     }

   GateResult CheckConsecLosses() const
     {
      if(m_consecLosses >= m_maxConsecLosses)
         return GR(false, StringFormat("Consec losses %d", m_consecLosses), m_consecLosses);
      return GR(true, StringFormat("Consec losses %d", m_consecLosses), m_consecLosses);
     }

   void NotifyTradeClosed(const double pnl)
     {
      if(pnl < 0) m_consecLosses++; else m_consecLosses = 0;
     }

   void HaltDay() { m_dayHalted = true; }
   bool IsDayHalted() const { return m_dayHalted; }

   double DailyDDPct() const
     {
      const double eq = AccountInfoDouble(ACCOUNT_EQUITY);
      if(m_dayStartEquity <= 0) return 0.0;
      return ((eq - m_dayStartEquity) / m_dayStartEquity) * 100.0;
     }

   //--- Sizing — brief §11.8
   double ComputeLots(const double slPriceDistance, const bool halfSize) const
     {
      const double eq = AccountInfoDouble(ACCOUNT_EQUITY);
      const double pct = halfSize ? m_riskHalfPct : m_riskPct;
      const double riskAmount = eq * pct / 100.0;
      const double tickSize = SymbolInfoDouble(m_sym, SYMBOL_TRADE_TICK_SIZE);
      const double tickVal  = SymbolInfoDouble(m_sym, SYMBOL_TRADE_TICK_VALUE);
      if(slPriceDistance <= 0 || tickSize <= 0 || tickVal <= 0) return 0.0;
      const double valuePerLot = (slPriceDistance / tickSize) * tickVal;
      if(valuePerLot <= 0) return 0.0;
      return NormaliseLots(m_sym, riskAmount / valuePerLot);
     }

   //--- Tiered news blackout — brief §22.4 stub: full JSON parse in Phase-2,
   //    here we just expose the gate and read inputs from the EA layer
   GateResult CheckNewsBlackout(const datetime now, const datetime preStart, const datetime postEnd, const string desc) const
     {
      if(now >= preStart && now <= postEnd)
         return GR(false, StringFormat("News blackout: %s", desc), 0.0);
      return GR(true, "no news", 0.0);
     }
  };

#endif
