// SierraChartBridge.cs
//
// File-based bridge that consumes data exported by a Sierra Chart custom study
// (the JIGSAW_Export.cpp pattern) and feeds the levels into the cTrader EA's
// gate pipeline. This gives cTrader access to Sierra Chart's superior tick
// data and Volume Profile calculations (overnight high/low, prior-day VWAP,
// session VWAP, ±std-dev bands, daily/weekly/monthly EQ levels) without
// needing Sierra Chart to be open on the same chart.
//
// Expected file format (one level per line):
//   PRICE,LABEL,COLOR
// Example:
//   1.08670,POC,Magenta
//   1.08920,VAH,DodgerBlue
//   1.08300,VAL,DodgerBlue
//   1.08540,dVWAP,Cyan
//   1.08720,DV+,MediumTurquoise
//   1.08360,DV-,MediumTurquoise
//   1.08800,ovnH,DarkSeaGreen
//   1.08200,ovnL,IndianRed
//
// Sierra Chart writes this file via JIGSAW_Export every N seconds. The cTrader
// EA polls it on a configurable interval and merges the levels with its own
// VP calculation. When a level matches one we already have, the Sierra Chart
// version takes precedence (its tick data is better). When we have a level
// Sierra Chart doesn't (e.g. session-derived LVN), ours is kept.
//
// File staleness: if the file hasn't been touched in >2 minutes the levels
// are flagged STALE and the dashboard shows a warning. The EA continues to
// trade on its own VP calculation.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;

namespace GodmodeOfea
{
    public sealed class SierraChartLevel
    {
        public double Price { get; set; }
        public string Label { get; set; } = string.Empty;
        public string Color { get; set; } = string.Empty;
    }

    public sealed class SierraChartBridge
    {
        private readonly string _filePath;
        private readonly double _staleSeconds;
        private DateTime _lastReadAttempt = DateTime.MinValue;
        private DateTime _lastFileWriteUtc = DateTime.MinValue;
        private List<SierraChartLevel> _levels = new List<SierraChartLevel>();
        private string _lastError = string.Empty;

        public SierraChartBridge(string filePath, double staleSeconds = 120.0)
        {
            _filePath = filePath;
            _staleSeconds = staleSeconds;
        }

        // Call from OnBar (or a timer). Returns true when levels were re-read.
        public bool Refresh(DateTime nowUtc, double minSecondsBetweenReads = 5.0)
        {
            if ((nowUtc - _lastReadAttempt).TotalSeconds < minSecondsBetweenReads) return false;
            _lastReadAttempt = nowUtc;

            if (string.IsNullOrEmpty(_filePath)) return false;
            try
            {
                var fi = new FileInfo(_filePath);
                if (!fi.Exists) { _lastError = "file not found"; return false; }
                if (fi.LastWriteTimeUtc == _lastFileWriteUtc) return false; // unchanged
                _lastFileWriteUtc = fi.LastWriteTimeUtc;

                var fresh = new List<SierraChartLevel>();
                var inv = CultureInfo.InvariantCulture;
                using (var fs = new FileStream(_filePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                using (var sr = new StreamReader(fs))
                {
                    string line;
                    while ((line = sr.ReadLine()) != null)
                    {
                        var trimmed = line.Trim();
                        if (string.IsNullOrEmpty(trimmed)) continue;
                        var parts = trimmed.Split(',');
                        if (parts.Length < 2) continue;
                        // Sierra Chart formats some prices as fractional (e.g. ZN/ZB) — we only consume
                        // decimal-formatted prices here. Skip lines that don't parse as a double.
                        if (!double.TryParse(parts[0], NumberStyles.Float, inv, out var price)) continue;
                        fresh.Add(new SierraChartLevel
                        {
                            Price = price,
                            Label = parts[1].Trim(),
                            Color = parts.Length > 2 ? parts[2].Trim() : "White",
                        });
                    }
                }
                _levels = fresh;
                _lastError = string.Empty;
                return true;
            }
            catch (Exception e)
            {
                _lastError = e.Message;
                return false;
            }
        }

        public bool IsStale(DateTime nowUtc) =>
            (nowUtc - _lastFileWriteUtc).TotalSeconds > _staleSeconds || _lastFileWriteUtc == DateTime.MinValue;

        public string LastError => _lastError;
        public IReadOnlyList<SierraChartLevel> Levels => _levels;

        // Convenience: find the level closest to a given price within a tolerance.
        public SierraChartLevel ClosestLevel(double price, double tolerance)
        {
            SierraChartLevel best = null;
            double bestDist = double.MaxValue;
            foreach (var lv in _levels)
            {
                double d = Math.Abs(lv.Price - price);
                if (d < bestDist && d <= tolerance) { bestDist = d; best = lv; }
            }
            return best;
        }

        // Lookup by label (POC, VAH, VAL, dVWAP, ovnH, ovnL, etc.) — first match.
        public SierraChartLevel FindByLabel(string label)
        {
            foreach (var lv in _levels)
                if (string.Equals(lv.Label, label, StringComparison.OrdinalIgnoreCase)) return lv;
            return null;
        }
    }
}
