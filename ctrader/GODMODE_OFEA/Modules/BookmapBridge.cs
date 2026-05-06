// BookmapBridge.cs
//
// File-based bridge that consumes events exported by a companion Bookmap
// Python addon (using the Bookmap Python API's subscribe_to_depth, subscribe_
// to_mbo, broadcasting receivers, etc.). The Bookmap addon writes JSON-lines
// to a file; this bridge tails that file and surfaces structured events to
// the cTrader EA's gate pipeline.
//
// Why this matters for cTrader:
//   cTrader cannot natively access true bid/ask depth ladder, market-by-order
//   data, or liquidity heatmap intensity. Bookmap can. By bridging, the
//   cTrader EA gains:
//     - Real iceberg detection signals (Bookmap addon does the consec-print
//       + max-depth-observed math; cTrader just consumes the fired event).
//     - Cumulative depth imbalance at top N levels.
//     - Market Pulse / pressure events (consumed via Bookmap's broadcasting API
//       on the Python side and re-emitted into the bridge file).
//
// Expected JSON-lines format (one event per line):
//   {"ts":"2026-05-08T11:42:00Z","kind":"DEPTH_BBO","bid":1.08340,"bidSz":120,"ask":1.08342,"askSz":80}
//   {"ts":"2026-05-08T11:42:01Z","kind":"DEPTH_SUM","bidSum":4500,"askSum":2200,"levels":20}
//   {"ts":"2026-05-08T11:42:03Z","kind":"ICEBERG","price":1.08340,"side":"LONG","consec":7,"vol":3500,"maxDepth":1200}
//   {"ts":"2026-05-08T11:42:04Z","kind":"PRESSURE","buyEstimate":0.78,"sellEstimate":0.22}
//
// Companion Python addon (sketch — not built here per scope; lives operator-side):
//   import bookmap as bm, json, time
//   def write(ev): open(PATH,"a").write(json.dumps(ev)+"\n")
//   bm.add_depth_handler(addon, lambda *a: write({"kind":"DEPTH_BBO", ...}))
//   bm.add_mbo_handler(addon, ...)  # iceberg-tracking logic here
//   bm.add_broadcasting_handler(addon, ...)  # consume Market Pulse pressures
//
// File staleness: if no event in >30 seconds the bridge flags STALE and the
// EA falls back to its own footprint analyser. Brief §19 rule 7 mirror
// discipline preserved — Bookmap data is *additive* not *required*.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;

namespace GodmodeOfea
{
    public enum BookmapEventKind
    {
        Unknown,
        DepthBbo,        // top-of-book bid/ask + sizes
        DepthSum,        // summed liquidity over top-N levels (bid + ask)
        Iceberg,         // iceberg fired (price, side, consec_prints, vol, max_depth_observed)
        Pressure,        // Market Pulse / aggregated pressure event
    }

    public sealed class BookmapEvent
    {
        public DateTime Ts { get; set; }
        public BookmapEventKind Kind { get; set; }
        public double Bid { get; set; }
        public double BidSize { get; set; }
        public double Ask { get; set; }
        public double AskSize { get; set; }
        public double BidSum { get; set; }
        public double AskSum { get; set; }
        public int Levels { get; set; }
        public double Price { get; set; }
        public string Side { get; set; } = string.Empty; // "LONG" or "SHORT"
        public int ConsecPrints { get; set; }
        public double Volume { get; set; }
        public double MaxDepth { get; set; }
        public double BuyEstimate { get; set; }
        public double SellEstimate { get; set; }
    }

    public sealed class BookmapBridge
    {
        private readonly string _filePath;
        private readonly double _staleSeconds;
        private long _lastReadOffset;
        private DateTime _lastEventTs = DateTime.MinValue;
        private string _lastError = string.Empty;

        // Latest snapshot data — kept here for synchronous lookup from the gate pipeline.
        private double _bid, _bidSize, _ask, _askSize;
        private double _bidSum, _askSum;
        private int _depthLevels;
        private double _buyPressure, _sellPressure;
        private readonly Queue<BookmapEvent> _recentIcebergs = new Queue<BookmapEvent>();
        private const int MaxRecentIcebergs = 32;

        public BookmapBridge(string filePath, double staleSeconds = 30.0)
        {
            _filePath = filePath;
            _staleSeconds = staleSeconds;
        }

        public bool Tail(DateTime nowUtc)
        {
            if (string.IsNullOrEmpty(_filePath)) return false;
            try
            {
                var fi = new FileInfo(_filePath);
                if (!fi.Exists) { _lastError = "file not found"; return false; }
                // If the file was truncated/rotated, restart from beginning.
                if (fi.Length < _lastReadOffset) _lastReadOffset = 0;
                if (fi.Length == _lastReadOffset) return false;

                using (var fs = new FileStream(_filePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                using (var sr = new StreamReader(fs))
                {
                    fs.Seek(_lastReadOffset, SeekOrigin.Begin);
                    string line;
                    while ((line = sr.ReadLine()) != null)
                    {
                        var trimmed = line.Trim();
                        if (string.IsNullOrEmpty(trimmed)) continue;
                        var ev = ParseLine(trimmed);
                        if (ev != null) Apply(ev);
                    }
                    _lastReadOffset = fs.Position;
                }
                _lastError = string.Empty;
                return true;
            }
            catch (Exception e)
            {
                _lastError = e.Message;
                return false;
            }
        }

        // Minimal embedded JSON parser — no Newtonsoft dependency, only handles the
        // four event shapes we expect. Returns null on malformed lines.
        private static BookmapEvent ParseLine(string line)
        {
            string Get(string key)
            {
                int idx = line.IndexOf("\"" + key + "\"", StringComparison.Ordinal);
                if (idx < 0) return null;
                idx = line.IndexOf(':', idx);
                if (idx < 0) return null;
                int end;
                while (idx < line.Length && (line[idx] == ':' || line[idx] == ' ' || line[idx] == '"')) idx++;
                end = idx;
                while (end < line.Length && line[end] != ',' && line[end] != '}' && line[end] != '"') end++;
                return line.Substring(idx, end - idx);
            }

            string kindStr = Get("kind");
            if (kindStr == null) return null;
            var ev = new BookmapEvent();
            DateTime.TryParse(Get("ts"), CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var ts);
            ev.Ts = ts == default ? DateTime.UtcNow : ts;

            switch (kindStr)
            {
                case "DEPTH_BBO":
                    ev.Kind = BookmapEventKind.DepthBbo;
                    double.TryParse(Get("bid"), NumberStyles.Float, CultureInfo.InvariantCulture, out var bid); ev.Bid = bid;
                    double.TryParse(Get("bidSz"), NumberStyles.Float, CultureInfo.InvariantCulture, out var bsz); ev.BidSize = bsz;
                    double.TryParse(Get("ask"), NumberStyles.Float, CultureInfo.InvariantCulture, out var ask); ev.Ask = ask;
                    double.TryParse(Get("askSz"), NumberStyles.Float, CultureInfo.InvariantCulture, out var asz); ev.AskSize = asz;
                    return ev;
                case "DEPTH_SUM":
                    ev.Kind = BookmapEventKind.DepthSum;
                    double.TryParse(Get("bidSum"), NumberStyles.Float, CultureInfo.InvariantCulture, out var bs); ev.BidSum = bs;
                    double.TryParse(Get("askSum"), NumberStyles.Float, CultureInfo.InvariantCulture, out var ass); ev.AskSum = ass;
                    int.TryParse(Get("levels"), NumberStyles.Integer, CultureInfo.InvariantCulture, out var lv); ev.Levels = lv;
                    return ev;
                case "ICEBERG":
                    ev.Kind = BookmapEventKind.Iceberg;
                    double.TryParse(Get("price"), NumberStyles.Float, CultureInfo.InvariantCulture, out var pr); ev.Price = pr;
                    ev.Side = Get("side") ?? "";
                    int.TryParse(Get("consec"), NumberStyles.Integer, CultureInfo.InvariantCulture, out var cp); ev.ConsecPrints = cp;
                    double.TryParse(Get("vol"), NumberStyles.Float, CultureInfo.InvariantCulture, out var vol); ev.Volume = vol;
                    double.TryParse(Get("maxDepth"), NumberStyles.Float, CultureInfo.InvariantCulture, out var md); ev.MaxDepth = md;
                    return ev;
                case "PRESSURE":
                    ev.Kind = BookmapEventKind.Pressure;
                    double.TryParse(Get("buyEstimate"), NumberStyles.Float, CultureInfo.InvariantCulture, out var be); ev.BuyEstimate = be;
                    double.TryParse(Get("sellEstimate"), NumberStyles.Float, CultureInfo.InvariantCulture, out var se); ev.SellEstimate = se;
                    return ev;
            }
            return null;
        }

        private void Apply(BookmapEvent ev)
        {
            _lastEventTs = ev.Ts;
            switch (ev.Kind)
            {
                case BookmapEventKind.DepthBbo:
                    _bid = ev.Bid; _bidSize = ev.BidSize; _ask = ev.Ask; _askSize = ev.AskSize;
                    break;
                case BookmapEventKind.DepthSum:
                    _bidSum = ev.BidSum; _askSum = ev.AskSum; _depthLevels = ev.Levels;
                    break;
                case BookmapEventKind.Iceberg:
                    _recentIcebergs.Enqueue(ev);
                    while (_recentIcebergs.Count > MaxRecentIcebergs) _recentIcebergs.Dequeue();
                    break;
                case BookmapEventKind.Pressure:
                    _buyPressure = ev.BuyEstimate; _sellPressure = ev.SellEstimate;
                    break;
            }
        }

        public bool IsStale(DateTime nowUtc) =>
            (nowUtc - _lastEventTs).TotalSeconds > _staleSeconds || _lastEventTs == DateTime.MinValue;

        public string LastError => _lastError;

        // Snapshot accessors used by the gate pipeline.
        public double Bid => _bid;
        public double BidSize => _bidSize;
        public double Ask => _ask;
        public double AskSize => _askSize;
        public double BidSum => _bidSum;
        public double AskSum => _askSum;
        public int DepthLevels => _depthLevels;
        public double BuyPressure => _buyPressure;
        public double SellPressure => _sellPressure;

        // Returns true if Bookmap fired an iceberg matching this direction within the last `withinSeconds`.
        public bool RecentIceberg(DateTime nowUtc, string side, double withinSeconds, out BookmapEvent match)
        {
            match = null;
            foreach (var ev in _recentIcebergs)
            {
                if (!string.Equals(ev.Side, side, StringComparison.OrdinalIgnoreCase)) continue;
                if ((nowUtc - ev.Ts).TotalSeconds <= withinSeconds) { match = ev; return true; }
            }
            return false;
        }

        // Cumulative depth imbalance: ratio of bid-side to ask-side liquidity over top-N levels.
        // > 1.0 = bid-heavy (institutional support); < 1.0 = ask-heavy (institutional resistance).
        public double DepthImbalance() => _askSum > 0 ? _bidSum / _askSum : 0.0;
    }
}
