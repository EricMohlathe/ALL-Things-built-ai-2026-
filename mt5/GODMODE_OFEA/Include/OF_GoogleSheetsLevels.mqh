//+------------------------------------------------------------------+
//| OF_GoogleSheetsLevels.mqh                                        |
//| HTTP bridge for operator-curated key levels (Google Sheets CSV). |
//| Mirrors ctrader/Modules/GoogleSheetsLevels.cs.                   |
//|                                                                  |
//| Adapted from Frozen Tundra google_sheets_importer.cpp.           |
//| Sheet sharing: "Anyone with link can view".                      |
//|                                                                  |
//| MT5 prerequisite: add the Google Docs hostname to                |
//|   Tools → Options → Expert Advisors → "Allow WebRequest for      |
//|   listed URL"                                                    |
//| with entries:                                                    |
//|   https://docs.google.com                                        |
//|                                                                  |
//| Spreadsheet columns: Price, Price2, Note, Color, LineType,       |
//| LineWidth, TextAlignment.                                        |
//+------------------------------------------------------------------+
#property strict

struct ManualLevel
  {
   double            price;
   double            price2;        // 0 if not a rectangle
   string            note;
   string            color_name;
   int               line_type;
   int               line_width;
   int               text_alignment;
  };

class CGoogleSheetsLevels
  {
private:
   string            m_base_url;
   double            m_refresh_secs;
   datetime          m_last_fetch;
   ManualLevel       m_levels[];
   string            m_last_error;

public:
   void              Init(const string base_url, const double refresh_secs = 300.0)
     {
      // Strip trailing slash.
      string u = base_url;
      while(StringLen(u) > 0 && StringGetCharacter(u, StringLen(u) - 1) == '/')
         u = StringSubstr(u, 0, StringLen(u) - 1);
      m_base_url = u;
      m_refresh_secs = refresh_secs;
      m_last_fetch = 0;
      m_last_error = "";
      ArrayResize(m_levels, 0);
     }

   bool              Refresh(const datetime now)
     {
      if(StringLen(m_base_url) == 0) return(false);
      if((double)(now - m_last_fetch) < m_refresh_secs) return(false);
      m_last_fetch = now;

      string url = m_base_url + "/gviz/tq?tqx=out:csv";
      char post[];
      char result[];
      string headers = "";
      string result_headers;
      ResetLastError();
      int code = WebRequest("GET", url, headers, 15000, post, result, result_headers);
      if(code != 200)
        {
         m_last_error = StringFormat("WebRequest err code=%d, last=%d", code, GetLastError());
         return(false);
        }
      string body = CharArrayToString(result, 0, -1, CP_UTF8);
      ParseCsv(body);
      m_last_error = "";
      return(true);
     }

private:
   void              ParseCsv(const string body)
     {
      ArrayResize(m_levels, 0);
      string lines[];
      int n_lines = StringSplit(body, '\n', lines);
      for(int i = 0; i < n_lines; i++)
        {
         string line = lines[i];
         StringTrimRight(line);
         StringTrimLeft(line);
         if(StringLen(line) == 0) continue;
         // Strip leading/trailing quote (Google's gviz format).
         if(StringGetCharacter(line, 0) == '"' &&
            StringGetCharacter(line, StringLen(line) - 1) == '"')
            line = StringSubstr(line, 1, StringLen(line) - 2);
         // Split on the canonical "," sentinel between fields.
         string fields[];
         int nf = StringSplit(line, ',', fields);
         if(nf == 0) continue;
         double price = StringToDouble(fields[0]);
         if(price <= 0) continue;
         int idx = ArraySize(m_levels);
         ArrayResize(m_levels, idx + 1);
         m_levels[idx].price = price;
         m_levels[idx].price2 = (nf > 1) ? StringToDouble(fields[1]) : 0;
         m_levels[idx].note = (nf > 2) ? fields[2] : "";
         m_levels[idx].color_name = (nf > 3) ? fields[3] : "white";
         m_levels[idx].line_type = (nf > 4) ? (int)StringToInteger(fields[4]) : 0;
         m_levels[idx].line_width = (nf > 5) ? (int)StringToInteger(fields[5]) : 1;
         m_levels[idx].text_alignment = (nf > 6) ? (int)StringToInteger(fields[6]) : 1;
        }
     }

public:
   string            LastError() { return(m_last_error); }
   int               LevelCount() { return(ArraySize(m_levels)); }
   bool              GetLevel(const int idx, ManualLevel &out)
     {
      if(idx < 0 || idx >= ArraySize(m_levels)) return(false);
      out = m_levels[idx];
      return(true);
     }

   int               ClosestLevel(const double price, const double tolerance)
     {
      int best = -1;
      double bestDist = DBL_MAX;
      for(int i = 0; i < ArraySize(m_levels); i++)
        {
         double mid = m_levels[i].price2 > 0
                      ? 0.5 * (m_levels[i].price + m_levels[i].price2)
                      : m_levels[i].price;
         double d = MathAbs(mid - price);
         if(d < bestDist && d <= tolerance) { bestDist = d; best = i; }
        }
      return(best);
     }
  };
//+------------------------------------------------------------------+
