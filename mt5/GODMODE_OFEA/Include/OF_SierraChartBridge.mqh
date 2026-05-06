//+------------------------------------------------------------------+
//| OF_SierraChartBridge.mqh                                         |
//| File-based bridge for Sierra Chart-exported VP levels.           |
//| Mirrors ctrader/Modules/SierraChartBridge.cs.                    |
//|                                                                  |
//| Reads CSV produced by Sierra Chart's JIGSAW_Export study:        |
//|   PRICE,LABEL,COLOR                                              |
//| One level per line. Sierra Chart writes via the existing         |
//| JIGSAW_Export.cpp (POC/VAH/VAL/dVWAP/std-dev/OvN H/L etc).       |
//|                                                                  |
//| MT5 file access requires the file to be under                    |
//| <Terminal>/MQL5/Files/. Configure JIGSAW_Export to write there,  |
//| or symlink in.                                                   |
//+------------------------------------------------------------------+
#property strict

struct SierraChartLevel
  {
   double            price;
   string            label;
   string            color;
  };

class CSierraChartBridge
  {
private:
   string            m_file_name;
   double            m_stale_seconds;
   datetime          m_last_read_attempt;
   datetime          m_last_file_mtime;
   SierraChartLevel  m_levels[];
   string            m_last_error;

public:
   void              Init(const string file_name, const double stale_secs = 120.0)
     {
      m_file_name = file_name;
      m_stale_seconds = stale_secs;
      m_last_read_attempt = 0;
      m_last_file_mtime = 0;
      m_last_error = "";
      ArrayResize(m_levels, 0);
     }

   //+----------------------------------------------------------------+
   //| Refresh — call from OnTimer. Returns true on re-read.          |
   //+----------------------------------------------------------------+
   bool              Refresh(const datetime now, const double min_secs_between_reads = 5.0)
     {
      if(m_file_name == "") return(false);
      if((double)(now - m_last_read_attempt) < min_secs_between_reads) return(false);
      m_last_read_attempt = now;

      int handle = FileOpen(m_file_name, FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ |
                            FILE_SHARE_WRITE | FILE_COMMON);
      if(handle == INVALID_HANDLE)
        {
         m_last_error = StringFormat("FileOpen err %d", GetLastError());
         return(false);
        }
      // Use file size as a cheap change-check; FileGetInteger returns 0 reliably.
      ulong fsize = (ulong)FileSize(handle);

      // Parse all lines.
      SierraChartLevel fresh[];
      ArrayResize(fresh, 0);
      while(!FileIsEnding(handle))
        {
         string line = FileReadString(handle);
         if(StringLen(line) == 0) continue;
         string parts[];
         int n = StringSplit(line, ',', parts);
         if(n < 2) continue;
         double price = StringToDouble(parts[0]);
         if(price <= 0) continue;
         int idx = ArraySize(fresh);
         ArrayResize(fresh, idx + 1);
         fresh[idx].price = price;
         fresh[idx].label = parts[1];
         fresh[idx].color = (n > 2) ? parts[2] : "White";
        }
      FileClose(handle);

      ArrayResize(m_levels, ArraySize(fresh));
      for(int i = 0; i < ArraySize(fresh); i++) m_levels[i] = fresh[i];
      m_last_file_mtime = now;
      m_last_error = "";
      return(true);
     }

   bool              IsStale(const datetime now)
     {
      if(m_last_file_mtime == 0) return(true);
      return((double)(now - m_last_file_mtime) > m_stale_seconds);
     }

   string            LastError() { return(m_last_error); }
   int               LevelCount() { return(ArraySize(m_levels)); }
   bool              GetLevel(const int idx, SierraChartLevel &out)
     {
      if(idx < 0 || idx >= ArraySize(m_levels)) return(false);
      out = m_levels[idx];
      return(true);
     }

   //+----------------------------------------------------------------+
   //| ClosestLevel — return index of nearest level within tolerance, |
   //| or -1.                                                         |
   //+----------------------------------------------------------------+
   int               ClosestLevel(const double price, const double tolerance)
     {
      int best = -1;
      double bestDist = DBL_MAX;
      for(int i = 0; i < ArraySize(m_levels); i++)
        {
         double d = MathAbs(m_levels[i].price - price);
         if(d < bestDist && d <= tolerance) { bestDist = d; best = i; }
        }
      return(best);
     }

   //+----------------------------------------------------------------+
   //| FindByLabel — linear scan, first match. Returns index or -1.   |
   //+----------------------------------------------------------------+
   int               FindByLabel(const string label)
     {
      for(int i = 0; i < ArraySize(m_levels); i++)
         if(StringCompare(m_levels[i].label, label, false) == 0) return(i);
      return(-1);
     }
  };
//+------------------------------------------------------------------+
