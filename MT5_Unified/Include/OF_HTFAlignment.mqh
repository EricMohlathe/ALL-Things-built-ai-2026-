//+------------------------------------------------------------------+
//|                                            OF_HTFAlignment.mqh   |
//|  H4 EMA(20) + D1 EMA(50) bias check (brief §11.7)                |
//+------------------------------------------------------------------+
#property strict
#ifndef OF_HTF_ALIGNMENT_MQH
#define OF_HTF_ALIGNMENT_MQH

#include "OF_Common.mqh"

class CHtfAlignment
  {
private:
   string m_sym;
   int    m_h4Ema;
   int    m_d1Ema;
   int    m_hH4, m_hD1;

public:
   bool Init(const string sym)
     {
      m_sym = sym;
      m_hH4 = iMA(sym, PERIOD_H4, 20, 0, MODE_EMA, PRICE_CLOSE);
      m_hD1 = iMA(sym, PERIOD_D1, 50, 0, MODE_EMA, PRICE_CLOSE);
      return (m_hH4 != INVALID_HANDLE && m_hD1 != INVALID_HANDLE);
     }

   void Deinit()
     {
      if(m_hH4 != INVALID_HANDLE) IndicatorRelease(m_hH4);
      if(m_hD1 != INVALID_HANDLE) IndicatorRelease(m_hD1);
     }

   // HTF bias must read CLOSED bars (index 1) — the current forming bar
   // (index 0) repaints intra-period and would flip BIAS between ticks,
   // poisoning the F3 gate. Brief §11.7 explicitly: "evaluated at close".
   // Also require BarsCalculated() to avoid reading uninitialised EMA buffer.
   ENUM_HTF_BIAS H4Bias()
     {
      if(m_hH4 == INVALID_HANDLE || BarsCalculated(m_hH4) <= 1) return BIAS_NEUTRAL;
      double buf[]; ArraySetAsSeries(buf, true);
      if(CopyBuffer(m_hH4, 0, 1, 1, buf) <= 0) return BIAS_NEUTRAL;
      if(!MathIsValidNumber(buf[0])) return BIAS_NEUTRAL;
      const double ema = buf[0];
      const double cls = iClose(m_sym, PERIOD_H4, 1);
      if(cls <= 0 || ema <= 0) return BIAS_NEUTRAL;
      if(cls > ema * 1.0001) return BIAS_BULL;
      if(cls < ema * 0.9999) return BIAS_BEAR;
      return BIAS_NEUTRAL;
     }

   ENUM_HTF_BIAS D1Bias()
     {
      if(m_hD1 == INVALID_HANDLE || BarsCalculated(m_hD1) <= 1) return BIAS_NEUTRAL;
      double buf[]; ArraySetAsSeries(buf, true);
      if(CopyBuffer(m_hD1, 0, 1, 1, buf) <= 0) return BIAS_NEUTRAL;
      if(!MathIsValidNumber(buf[0])) return BIAS_NEUTRAL;
      const double ema = buf[0];
      const double cls = iClose(m_sym, PERIOD_D1, 1);
      if(cls <= 0 || ema <= 0) return BIAS_NEUTRAL;
      if(cls > ema * 1.0001) return BIAS_BULL;
      if(cls < ema * 0.9999) return BIAS_BEAR;
      return BIAS_NEUTRAL;
     }

   bool IsAligned(const ENUM_DIR dir)
     {
      const ENUM_HTF_BIAS h4 = H4Bias();
      const ENUM_HTF_BIAS d1 = D1Bias();
      if(h4 != d1) return false;
      if(dir == DIR_LONG)  return h4 == BIAS_BULL;
      if(dir == DIR_SHORT) return h4 == BIAS_BEAR;
      return false;
     }

   ENUM_HTF_BIAS Combined()
     {
      const ENUM_HTF_BIAS h4 = H4Bias();
      const ENUM_HTF_BIAS d1 = D1Bias();
      return (h4 == d1) ? h4 : BIAS_NEUTRAL;
     }
  };

#endif
