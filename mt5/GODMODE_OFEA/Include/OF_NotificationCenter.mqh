//+------------------------------------------------------------------+
//|                                       OF_NotificationCenter.mqh  |
//|  N-A through N-L cascade dispatcher (brief §4)                   |
//|  Edge-detected — each tag fires once per bar on FALSE→TRUE       |
//+------------------------------------------------------------------+
#property strict
#ifndef OF_NOTIFICATION_CENTER_MQH
#define OF_NOTIFICATION_CENTER_MQH

#include "OF_Common.mqh"

class CNotificationCenter
  {
private:
   bool m_enableSound, m_enablePush, m_enableEmail, m_enableNotif;
   string m_lastBarFiredTag[64];
   datetime m_lastBarFiredTime[64];
   int m_count;

   int IndexOf(const string tag)
     {
      for(int i = 0; i < m_count; i++) if(m_lastBarFiredTag[i] == tag) return i;
      if(m_count >= 64) return -1;
      m_lastBarFiredTag[m_count] = tag;
      m_lastBarFiredTime[m_count] = 0;
      return m_count++;
     }

   bool ShouldFire(const string tag)
     {
      const int i = IndexOf(tag);
      if(i < 0) return false;
      const datetime curBar = iTime(_Symbol, _Period, 0);
      if(m_lastBarFiredTime[i] == curBar) return false;
      m_lastBarFiredTime[i] = curBar;
      return true;
     }

public:
   void Init(const bool enableNotif, const bool sound, const bool push, const bool email)
     {
      m_enableNotif = enableNotif;
      m_enableSound = sound;
      m_enablePush = push;
      m_enableEmail = email;
      m_count = 0;
     }

   //--- Generic dispatcher
   void Fire(const string tag, const string msg, const string sound = "", const bool sendPush = false)
     {
      if(!m_enableNotif) return;
      if(!ShouldFire(tag)) return;
      const string text = StringFormat("[%s] %s — %s", _Symbol, tag, msg);
      Print(text);
      if(m_enableSound && sound != "") PlaySound(sound);
      if(m_enablePush && sendPush) SendNotification(text);
      Comment(text);    // simple toast — replaced by ChartViz draw routines
     }

   //--- Cascade tags (brief §4 table)
   void NA_VpLevel(const string lvl, const double price)
     { Fire("N-A", StringFormat("VP %s touch @ %.5f", lvl, price), "alert.wav", false); }

   void NB_TripleConfluence()
     { Fire("N-B", "Triple confluence achieved", "ok.wav", false); }

   void NC_KillZone(const ENUM_SESSION s)
     { Fire("N-C", StringFormat("Kill zone active: %s", SessionToStr(s))); }

   void ND_HTFAligned(const ENUM_HTF_BIAS bias)
     { Fire("N-D", StringFormat("HTF aligned: %s", BiasToStr(bias))); }

   void NE_CvdConfirm(const ENUM_DIR dir, const double cvd)
     { Fire("N-E", StringFormat("CVD confirms %s (CVD=%.0f)", DirToStr(dir), cvd), "tick.wav", false); }

   void NF_ProfileState(const ENUM_PROFILE_SHAPE sh, const ENUM_MARKET_STATE st)
     { Fire("N-F", StringFormat("Shape %s state %d", ShapeToStr(sh), (int)st)); }

   void NG_FootprintSignal(const string kind, const int stars)
     { Fire("N-G", StringFormat("Footprint %s ★%d", kind, stars), "alert2.wav", false); }

   void NH_AggressionTrigger(const double volZ)
     { Fire("N-H", StringFormat("Aggression vol Z=%.2f", volZ), "alert.wav", true); }

   void NI_AplusReady(const SetupCandidate &c, const double rr)
     {
      Fire("N-I", StringFormat("A+ READY %s setup=%d score=%d R:R=%.1f",
                               DirToStr(c.direction), (int)c.setupId, c.score, rr),
                  "stops.wav", true);
     }

   void NJ_TradeFired(const SetupCandidate &c, const double lots, const string mode)
     {
      Fire("N-J", StringFormat("%s %s %.2f lots @ %.5f SL %.5f TP %.5f [%s]",
                               DirToStr(c.direction), _Symbol, lots, c.entry, c.sl, c.tp, mode),
                  "expert.wav", true);
     }

   void NK_PositionEvent(const string ev)
     { Fire("N-K_" + ev, StringFormat("Position event: %s", ev), "ok.wav", false); }

   void NL_KillSwitch(const string reason)
     {
      Fire("N-L_" + reason, StringFormat("KILL SWITCH: %s", reason), "timeout.wav", true);
     }

   // N-V Pace-of-Tape elevated (brief §22 marginal-gain).
   void NV_PaceOfTape(const double pace)
     { Fire("N-V", StringFormat("Pace-of-Tape elevated pace=%.2f", pace), "ok.wav", false); }

   // N-W Bookmap-confirmed iceberg (true microstructure).
   void NW_BookmapIceberg(const string side, const double price, const int consec,
                          const double vol, const double maxDepth)
     {
      Fire("N-W", StringFormat("Bookmap iceberg %s @ %.5f consec=%d vol=%.0f maxDepth=%.0f",
                               side, price, consec, vol, maxDepth),
           "alert.wav", true);
     }

   // N-X Sierra Chart level proximity (POC/VAH/VAL/dVWAP/etc).
   void NX_SierraChartLevel(const string label, const double price)
     { Fire("N-X", StringFormat("Sierra Chart %s @ %.5f", label, price), "ok.wav", false); }

   // N-Y Operator manual level (Google Sheets).
   void NY_ManualLevel(const string note, const double price)
     { Fire("N-Y", StringFormat("Manual level '%s' @ %.5f", note, price), "ok.wav", false); }
  };

#endif
