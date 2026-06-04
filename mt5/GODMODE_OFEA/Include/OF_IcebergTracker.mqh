//+------------------------------------------------------------------+
//| OF_IcebergTracker.mqh                                            |
//| Upgraded iceberg detection adapted from Frozen Tundra            |
//| TapeOnChart.cpp pattern. Mirrors ctrader/Modules/IcebergTracker. |
//| cs.                                                              |
//|                                                                  |
//| Tracks per-price-level: consecutive prints, total volume, and    |
//| max depth observed during the absorption. Fires when total       |
//| volume exceeds max_depth × refill_ratio AND consec >= min_consec.|
//|                                                                  |
//| Brief §19 rule 7 mirror discipline.                              |
//+------------------------------------------------------------------+
#property strict

#include "OF_Common.mqh"

struct IcebergRecord
  {
   double            price;
   ENUM_DIR          side;            // LONG or SHORT
   int               consec_prints;
   double            total_volume;
   double            max_depth_observed;
   datetime          last_tick_time;
  };

class CIcebergTracker
  {
private:
   string            m_symbol;
   double            m_tick_size;
   int               m_min_consec;
   double            m_min_total_vol;
   double            m_refill_ratio;
   double            m_stale_seconds;
   double            m_consec_reset_seconds;

   // Parallel arrays for keys + records (MQL5 has no Dictionary<>).
   string            m_keys[];
   IcebergRecord     m_records[];

   string            m_depth_keys[];   // rounded-price strings
   double            m_depth_sizes[];

   string            MakeKey(const double price, const ENUM_DIR side)
     {
      double rounded = MathRound(price / m_tick_size) * m_tick_size;
      return StringFormat("%.8f|%d", rounded, (int)side);
     }

   string            RoundKey(const double price)
     {
      double rounded = MathRound(price / m_tick_size) * m_tick_size;
      return StringFormat("%.8f", rounded);
     }

   int               FindRecord(const string key)
     {
      for(int i = 0; i < ArraySize(m_keys); i++)
         if(m_keys[i] == key) return(i);
      return(-1);
     }

   int               FindDepth(const string key)
     {
      for(int i = 0; i < ArraySize(m_depth_keys); i++)
         if(m_depth_keys[i] == key) return(i);
      return(-1);
     }

public:
   void              Init(const string symbol, const double tick_size,
                          const int min_consec, const double min_total_vol,
                          const double refill_ratio, const double stale_secs,
                          const double consec_reset_secs)
     {
      m_symbol = symbol;
      m_tick_size = MathMax(tick_size, 1e-9);
      m_min_consec = MathMax(2, min_consec);
      m_min_total_vol = MathMax(1.0, min_total_vol);
      m_refill_ratio = MathMax(1.0, refill_ratio);
      m_stale_seconds = stale_secs;
      m_consec_reset_seconds = consec_reset_secs;
     }

   //+----------------------------------------------------------------+
   //| OnTopOfBook — call from OnBookEvent or OnTick to record the    |
   //| largest depth ever seen at each price level. MT5 retail brokers|
   //| typically expose only the BBO via SymbolInfoTick; pass that as |
   //| size when MarketBookGet returns no data.                       |
   //+----------------------------------------------------------------+
   void              OnTopOfBook(const double bid_price, const double bid_size,
                                 const double ask_price, const double ask_size)
     {
      string bk = RoundKey(bid_price);
      string ak = RoundKey(ask_price);
      int idx = FindDepth(bk);
      if(idx < 0)
        {
         int n = ArraySize(m_depth_keys);
         ArrayResize(m_depth_keys, n + 1);
         ArrayResize(m_depth_sizes, n + 1);
         m_depth_keys[n] = bk;
         m_depth_sizes[n] = bid_size;
        }
      else
         m_depth_sizes[idx] = bid_size;
      idx = FindDepth(ak);
      if(idx < 0)
        {
         int n = ArraySize(m_depth_keys);
         ArrayResize(m_depth_keys, n + 1);
         ArrayResize(m_depth_sizes, n + 1);
         m_depth_keys[n] = ak;
         m_depth_sizes[n] = ask_size;
        }
      else
         m_depth_sizes[idx] = ask_size;
     }

   //+----------------------------------------------------------------+
   //| OnTrade — call from your tick-aware accumulator when a trade   |
   //| fires. Returns true and fills `out` when the iceberg condition |
   //| is met.                                                        |
   //+----------------------------------------------------------------+
   bool              OnTrade(const datetime now, const double price, const double size,
                             const bool is_bid_aggressor, IcebergRecord &out)
     {
      ENUM_DIR side = is_bid_aggressor ? DIR_LONG : DIR_SHORT;
      string key = MakeKey(price, side);
      string dkey = RoundKey(price);
      int didx = FindDepth(dkey);
      double depth_seen = (didx >= 0) ? m_depth_sizes[didx] : 0.0;

      int idx = FindRecord(key);
      if(idx < 0)
        {
         int n = ArraySize(m_keys);
         ArrayResize(m_keys, n + 1);
         ArrayResize(m_records, n + 1);
         m_keys[n] = key;
         m_records[n].price = price;
         m_records[n].side = side;
         m_records[n].consec_prints = 1;
         m_records[n].total_volume = size;
         m_records[n].max_depth_observed = depth_seen;
         m_records[n].last_tick_time = now;
         idx = n;
        }
      else
        {
         double age = (double)(now - m_records[idx].last_tick_time);
         if(age <= m_consec_reset_seconds)
           {
            m_records[idx].consec_prints += 1;
            m_records[idx].total_volume += size;
            if(depth_seen > m_records[idx].max_depth_observed)
               m_records[idx].max_depth_observed = depth_seen;
            m_records[idx].last_tick_time = now;
           }
         else
           {
            m_records[idx].price = price;
            m_records[idx].side = side;
            m_records[idx].consec_prints = 1;
            m_records[idx].total_volume = size;
            m_records[idx].max_depth_observed = depth_seen;
            m_records[idx].last_tick_time = now;
           }
        }

      double threshold = MathMax(m_min_total_vol,
                                 m_records[idx].max_depth_observed * m_refill_ratio);
      if(m_records[idx].consec_prints >= m_min_consec &&
         m_records[idx].total_volume >= threshold)
        {
         // Fire and remove so a fresh accumulation must start.
         out = m_records[idx];
         RemoveAt(idx);
         return(true);
        }
      return(false);
     }

   //+----------------------------------------------------------------+
   //| CleanupStale — call periodically to evict abandoned records.   |
   //+----------------------------------------------------------------+
   void              CleanupStale(const datetime now)
     {
      for(int i = ArraySize(m_keys) - 1; i >= 0; i--)
        {
         double age = (double)(now - m_records[i].last_tick_time);
         if(age > m_stale_seconds) RemoveAt(i);
        }
     }

private:
   void              RemoveAt(const int idx)
     {
      int n = ArraySize(m_keys);
      if(idx < 0 || idx >= n) return;
      for(int i = idx; i < n - 1; i++)
        {
         m_keys[i] = m_keys[i + 1];
         m_records[i] = m_records[i + 1];
        }
      ArrayResize(m_keys, n - 1);
      ArrayResize(m_records, n - 1);
     }
  };
//+------------------------------------------------------------------+
