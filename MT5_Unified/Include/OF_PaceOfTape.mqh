//+------------------------------------------------------------------+
//| OF_PaceOfTape.mqh                                                |
//| Pace-of-Tape microstructure rate vs lagging-max.                 |
//| Mirrors ctrader/Modules/PaceOfTape.cs.                            |
//|                                                                  |
//| Adapted from Frozen Tundra pace_of_tape.cpp.                     |
//| Lagging-max excludes the most recent fraction so live spikes do  |
//| not immediately reset the comparison ceiling.                    |
//+------------------------------------------------------------------+
#property strict

class CPaceOfTape
  {
private:
   int               m_window_seconds;
   int               m_lagging_fraction;
   datetime          m_ts[];
   double            m_size[];
   double            m_lagging_max;

public:
   void              Init(const int window_seconds = 60, const int lagging_fraction = 5)
     {
      m_window_seconds = MathMax(10, window_seconds);
      m_lagging_fraction = MathMax(2, lagging_fraction);
      m_lagging_max = 0.0;
     }

   void              OnTrade(const datetime ts, const double size)
     {
      int n = ArraySize(m_ts);
      ArrayResize(m_ts, n + 1);
      ArrayResize(m_size, n + 1);
      m_ts[n] = ts;
      m_size[n] = size;

      // Drop records older than window from the front.
      datetime cutoff = ts - m_window_seconds;
      int drop = 0;
      while(drop < ArraySize(m_ts) && m_ts[drop] < cutoff) drop++;
      if(drop > 0)
        {
         int newSize = ArraySize(m_ts) - drop;
         for(int i = 0; i < newSize; i++)
           {
            m_ts[i] = m_ts[i + drop];
            m_size[i] = m_size[i + drop];
           }
         ArrayResize(m_ts, newSize);
         ArrayResize(m_size, newSize);
        }

      // Lagging-max: only consider records older than (window / fraction) seconds.
      datetime maxCutoff = ts - (m_window_seconds / m_lagging_fraction);
      double recentSum = 0.0;
      for(int i = 0; i < ArraySize(m_ts); i++)
         if(m_ts[i] <= maxCutoff) recentSum += m_size[i];
      if(recentSum > m_lagging_max) m_lagging_max = recentSum;
     }

   double            Pace()
     {
      if(m_lagging_max <= 0) return(0.0);
      double cur = 0.0;
      for(int i = 0; i < ArraySize(m_size); i++) cur += m_size[i];
      return(cur / m_lagging_max);
     }

   double            LaggingMax() { return(m_lagging_max); }
   int               RecordCount() { return(ArraySize(m_ts)); }
  };
//+------------------------------------------------------------------+
