//+------------------------------------------------------------------+
//|                                              OF_SessionGate.mqh  |
//|  SAST window detection + kill-zone tagging                       |
//|  Brief §11.6, §22.6 (sub-window tiering)                         |
//+------------------------------------------------------------------+
#property strict
#ifndef OF_SESSION_GATE_MQH
#define OF_SESSION_GATE_MQH

#include "OF_Common.mqh"

class CSessionGate
  {
private:
   int  m_offsetHours;       // SAST_OffsetFromBroker
   int  m_nyOpenBlackoutMin;
   bool m_tradeAsian, m_tradeLdnOpen, m_tradeLdnMain, m_tradeNyOpen, m_tradeNyMain;
   ENUM_SESSION m_lastSession;

public:
   void Init(const int offset, const int nyBlackout,
             const bool asian, const bool ldnO, const bool ldnM,
             const bool nyO, const bool nyM)
     {
      m_offsetHours = offset;
      m_nyOpenBlackoutMin = nyBlackout;
      m_tradeAsian = asian; m_tradeLdnOpen = ldnO; m_tradeLdnMain = ldnM;
      m_tradeNyOpen = nyO;  m_tradeNyMain = nyM;
      m_lastSession = SESSION_NONE;
     }

   //--- Compute SAST minute-from-midnight from broker time
   int SastMinute() const
     {
      MqlDateTime t; TimeToStruct(TimeCurrent(), t);
      int h = t.hour + m_offsetHours;
      while(h >= 24) h -= 24;
      while(h < 0)   h += 24;
      return h * 60 + t.min;
     }

   ENUM_SESSION Classify(int &outSastMin) const
     {
      const int m = SastMinute();
      outSastMin = m;
      // Brief §11.6 windows in minutes-from-midnight (SAST)
      if(m >= 120  && m < 600)  return SESSION_ASIAN;
      if(m >= 600  && m < 660)  return SESSION_LDN_OPEN;
      if(m >= 660  && m < 930)  return SESSION_LDN_MAIN;
      if(m >= 930  && m < 1050) return SESSION_NY_OPEN;
      if(m >= 1050 && m < 1260) return SESSION_NY_MAIN;
      return SESSION_AFTER;
     }

   bool IsSessionEnabled(const ENUM_SESSION s) const
     {
      switch(s)
        {
         case SESSION_ASIAN:    return m_tradeAsian;
         case SESSION_LDN_OPEN: return m_tradeLdnOpen;
         case SESSION_LDN_MAIN: return m_tradeLdnMain;
         case SESSION_NY_OPEN:  return m_tradeNyOpen;
         case SESSION_NY_MAIN:  return m_tradeNyMain;
        }
      return false;
     }

   //--- NY-Open blackout — first N minutes after 15:30 SAST
   bool InNyOpenBlackout() const
     {
      const int m = SastMinute();
      return m >= 930 && m < (930 + m_nyOpenBlackoutMin);
     }

   //--- §22.6 sub-window tier
   ENUM_SUBTIER SubTier() const
     {
      const int m = SastMinute();
      if(m >= 660  && m < 810)  return SUBTIER_A;  // LDN 11:00-13:30
      if(m >= 810  && m < 930)  return SUBTIER_B;  // LDN 13:30-15:30
      if(m >= 1050 && m < 1140) return SUBTIER_A;  // NY 17:30-19:00
      if(m >= 1140 && m < 1260) return SUBTIER_B;  // NY 19:00-21:00
      return SUBTIER_NONE;
     }

   //--- Session-end-of-NY-Main = 21:00 SAST = 1260 min
   bool ApproachingNyMainEnd(const int minutesBefore) const
     {
      const int m = SastMinute();
      return m >= (1260 - minutesBefore) && m < 1260;
     }

   //--- Edge detection for N-C notification
   bool SessionChanged(const ENUM_SESSION newS)
     {
      bool changed = (newS != m_lastSession);
      m_lastSession = newS;
      return changed;
     }

   ENUM_ACTIVE_MODEL ModelForSession(const ENUM_SESSION s) const
     {
      // Brief §5 GATE 1
      if(s == SESSION_LDN_MAIN) return MODEL_M2_MEANREV;
      if(s == SESSION_NY_MAIN)  return MODEL_M1_TREND;
      if(s == SESSION_LDN_OPEN) return MODEL_M1_TREND;
      return MODEL_NONE;
     }
  };

#endif
