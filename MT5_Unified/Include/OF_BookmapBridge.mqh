//+------------------------------------------------------------------+
//| OF_BookmapBridge.mqh                                             |
//| File-based bridge to a Bookmap Python addon export.              |
//| Mirrors ctrader/Modules/BookmapBridge.cs.                        |
//|                                                                  |
//| Tails JSON-lines emitted by the operator's companion Bookmap     |
//| addon (kinds: DEPTH_BBO, DEPTH_SUM, ICEBERG, PRESSURE) and       |
//| surfaces the data as accessors used by the gate pipeline.        |
//|                                                                  |
//| MT5 file must live under <Terminal>/MQL5/Files/.                 |
//+------------------------------------------------------------------+
#property strict

#define BMK_UNKNOWN     0
#define BMK_DEPTH_BBO   1
#define BMK_DEPTH_SUM   2
#define BMK_ICEBERG     3
#define BMK_PRESSURE    4

struct BookmapEvent
  {
   datetime          ts;
   int               kind;
   double            bid;
   double            bid_size;
   double            ask;
   double            ask_size;
   double            bid_sum;
   double            ask_sum;
   int               levels;
   double            price;
   string            side;          // "LONG" or "SHORT"
   int               consec_prints;
   double            volume;
   double            max_depth;
   double            buy_estimate;
   double            sell_estimate;
  };

class CBookmapBridge
  {
private:
   string            m_file_name;
   double            m_stale_seconds;
   ulong             m_last_read_offset;
   datetime          m_last_event_ts;
   string            m_last_error;

   double            m_bid, m_bid_size, m_ask, m_ask_size;
   double            m_bid_sum, m_ask_sum;
   int               m_depth_levels;
   double            m_buy_pressure, m_sell_pressure;
   BookmapEvent      m_recent_icebergs[];

   //+----------------------------------------------------------------+
   //| Tiny embedded JSON helper — extracts the value of a key from   |
   //| a flat one-line object. Handles only string/number primitives. |
   //+----------------------------------------------------------------+
   string            JsonGet(const string body, const string key)
     {
      string needle = "\"" + key + "\"";
      int idx = StringFind(body, needle);
      if(idx < 0) return("");
      idx = StringFind(body, ":", idx);
      if(idx < 0) return("");
      idx++;
      while(idx < StringLen(body))
        {
         ushort ch = StringGetCharacter(body, idx);
         if(ch == ' ' || ch == '"') { idx++; continue; }
         break;
        }
      int end = idx;
      while(end < StringLen(body))
        {
         ushort ch = StringGetCharacter(body, end);
         if(ch == ',' || ch == '}' || ch == '"') break;
         end++;
        }
      return(StringSubstr(body, idx, end - idx));
     }

   bool              ParseLine(const string line, BookmapEvent &ev)
     {
      string kind_str = JsonGet(line, "kind");
      if(kind_str == "") return(false);
      string ts_str = JsonGet(line, "ts");
      ev.ts = (StringLen(ts_str) > 0) ? StringToTime(ts_str) : TimeCurrent();
      if(kind_str == "DEPTH_BBO")
        {
         ev.kind = BMK_DEPTH_BBO;
         ev.bid = StringToDouble(JsonGet(line, "bid"));
         ev.bid_size = StringToDouble(JsonGet(line, "bidSz"));
         ev.ask = StringToDouble(JsonGet(line, "ask"));
         ev.ask_size = StringToDouble(JsonGet(line, "askSz"));
         return(true);
        }
      if(kind_str == "DEPTH_SUM")
        {
         ev.kind = BMK_DEPTH_SUM;
         ev.bid_sum = StringToDouble(JsonGet(line, "bidSum"));
         ev.ask_sum = StringToDouble(JsonGet(line, "askSum"));
         ev.levels = (int)StringToInteger(JsonGet(line, "levels"));
         return(true);
        }
      if(kind_str == "ICEBERG")
        {
         ev.kind = BMK_ICEBERG;
         ev.price = StringToDouble(JsonGet(line, "price"));
         ev.side = JsonGet(line, "side");
         ev.consec_prints = (int)StringToInteger(JsonGet(line, "consec"));
         ev.volume = StringToDouble(JsonGet(line, "vol"));
         ev.max_depth = StringToDouble(JsonGet(line, "maxDepth"));
         return(true);
        }
      if(kind_str == "PRESSURE")
        {
         ev.kind = BMK_PRESSURE;
         ev.buy_estimate = StringToDouble(JsonGet(line, "buyEstimate"));
         ev.sell_estimate = StringToDouble(JsonGet(line, "sellEstimate"));
         return(true);
        }
      return(false);
     }

   void              Apply(BookmapEvent &ev)
     {
      m_last_event_ts = ev.ts;
      switch(ev.kind)
        {
         case BMK_DEPTH_BBO:
            m_bid = ev.bid; m_bid_size = ev.bid_size;
            m_ask = ev.ask; m_ask_size = ev.ask_size;
            break;
         case BMK_DEPTH_SUM:
            m_bid_sum = ev.bid_sum; m_ask_sum = ev.ask_sum;
            m_depth_levels = ev.levels;
            break;
         case BMK_ICEBERG:
           {
            int n = ArraySize(m_recent_icebergs);
            ArrayResize(m_recent_icebergs, n + 1);
            m_recent_icebergs[n] = ev;
            // Trim to last 32.
            if(ArraySize(m_recent_icebergs) > 32)
              {
               for(int i = 0; i < 32; i++)
                  m_recent_icebergs[i] = m_recent_icebergs[ArraySize(m_recent_icebergs) - 32 + i];
               ArrayResize(m_recent_icebergs, 32);
              }
            break;
           }
         case BMK_PRESSURE:
            m_buy_pressure = ev.buy_estimate;
            m_sell_pressure = ev.sell_estimate;
            break;
        }
     }

public:
   void              Init(const string file_name, const double stale_secs = 30.0)
     {
      m_file_name = file_name;
      m_stale_seconds = stale_secs;
      m_last_read_offset = 0;
      m_last_event_ts = 0;
      m_last_error = "";
      m_bid = m_bid_size = m_ask = m_ask_size = 0;
      m_bid_sum = m_ask_sum = 0; m_depth_levels = 0;
      m_buy_pressure = m_sell_pressure = 0;
      ArrayResize(m_recent_icebergs, 0);
     }

   bool              Tail(const datetime now)
     {
      if(m_file_name == "") return(false);
      int handle = FileOpen(m_file_name, FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ |
                            FILE_SHARE_WRITE | FILE_COMMON);
      if(handle == INVALID_HANDLE)
        {
         m_last_error = StringFormat("FileOpen err %d", GetLastError());
         return(false);
        }
      ulong total = (ulong)FileSize(handle);
      if(total < m_last_read_offset) m_last_read_offset = 0; // rotated
      if(total == m_last_read_offset) { FileClose(handle); return(false); }
      FileSeek(handle, m_last_read_offset, SEEK_SET);
      while(!FileIsEnding(handle))
        {
         string line = FileReadString(handle);
         if(StringLen(line) == 0) continue;
         BookmapEvent ev;
         if(ParseLine(line, ev)) Apply(ev);
        }
      m_last_read_offset = (ulong)FileTell(handle);
      FileClose(handle);
      m_last_error = "";
      return(true);
     }

   bool              IsStale(const datetime now)
     {
      if(m_last_event_ts == 0) return(true);
      return((double)(now - m_last_event_ts) > m_stale_seconds);
     }

   string            LastError() { return(m_last_error); }
   double            Bid()       { return(m_bid); }
   double            BidSize()   { return(m_bid_size); }
   double            Ask()       { return(m_ask); }
   double            AskSize()   { return(m_ask_size); }
   double            BidSum()    { return(m_bid_sum); }
   double            AskSum()    { return(m_ask_sum); }
   int               DepthLevels() { return(m_depth_levels); }
   double            BuyPressure() { return(m_buy_pressure); }
   double            SellPressure() { return(m_sell_pressure); }
   double            DepthImbalance() { return(m_ask_sum > 0 ? m_bid_sum / m_ask_sum : 0); }

   bool              RecentIceberg(const datetime now, const string side,
                                   const double within_secs, BookmapEvent &out)
     {
      for(int i = ArraySize(m_recent_icebergs) - 1; i >= 0; i--)
        {
         if(StringCompare(m_recent_icebergs[i].side, side, false) != 0) continue;
         if((double)(now - m_recent_icebergs[i].ts) <= within_secs)
           {
            out = m_recent_icebergs[i];
            return(true);
           }
        }
      return(false);
     }
  };
//+------------------------------------------------------------------+
