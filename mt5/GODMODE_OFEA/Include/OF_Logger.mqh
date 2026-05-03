//+------------------------------------------------------------------+
//|                                                    OF_Logger.mqh |
//|  CSV journal writer — schema per brief §13                       |
//+------------------------------------------------------------------+
#property strict
#ifndef OF_LOGGER_MQH
#define OF_LOGGER_MQH

#include "OF_Common.mqh"

#define OFLOG_FILE "GODMODE_OFEA_log.csv"

string g_logHeader =
   "timestamp_utc,symbol,event_type,setup_id,score,priority,"
   "direction,entry_price,sl,tp,lots,risk_pct,"
   "session,market_state,htf_bias,profile_shape,"
   "poc,vah,val,"
   "cvd_at_entry,bar_delta,vol_z,delta_z,abs_stars,"
   "notif_cascade_completed,mode,"
   "result_pnl_pips,result_pnl_pct,result_R,hold_minutes";

//+------------------------------------------------------------------+
//| Append a journal row — common-flag CSV; Excel-readable           |
//+------------------------------------------------------------------+
void OFLog_AppendCsv(const string row)
  {
   const int flags = FILE_WRITE | FILE_READ | FILE_CSV | FILE_COMMON | FILE_ANSI;
   const int h = FileOpen(OFLOG_FILE, flags, ',');
   if(h == INVALID_HANDLE) { Print("OFLog: open failed err=", GetLastError()); return; }
   if(FileSize(h) == 0) FileWriteString(h, g_logHeader + "\r\n");
   FileSeek(h, 0, SEEK_END);
   FileWriteString(h, row + "\r\n");
   FileClose(h);
  }

string OFLog_FmtRow(const string evType, const SetupCandidate &c, const string sym,
                    const ENUM_SESSION sess, const ENUM_MARKET_STATE state,
                    const ENUM_HTF_BIAS bias, const ENUM_PROFILE_SHAPE shape,
                    const double poc, const double vah, const double val,
                    const double cvd, const double barDelta, const double volZ,
                    const double deltaZ, const string mode, const double riskPct,
                    const double lots,
                    const double resultPips = 0.0, const double resultPct = 0.0,
                    const double resultR = 0.0, const double holdMin = 0.0)
  {
   string ts = TimeToString(TimeGMT(), TIME_DATE | TIME_SECONDS);
   string row = StringFormat(
      "%s,%s,%s,%d,%d,%d,%s,%.5f,%.5f,%.5f,%.2f,%.2f,"
      "%s,%d,%s,%s,%.5f,%.5f,%.5f,%.0f,%.0f,%.2f,%.2f,%d,1,%s,"
      "%.2f,%.4f,%.2f,%.1f",
      ts, sym, evType, (int)c.setupId, c.score, (int)c.priority, DirToStr(c.direction),
      c.entry, c.sl, c.tp, lots, riskPct,
      SessionToStr(sess), (int)state, BiasToStr(bias), ShapeToStr(shape),
      poc, vah, val, cvd, barDelta, volZ, deltaZ, c.absStars, mode,
      resultPips, resultPct, resultR, holdMin);
   return row;
  }

#endif
