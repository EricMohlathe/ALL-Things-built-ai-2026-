// IcebergTracker.cs
// Upgraded iceberg detection adapted from Frozen Tundra TapeOnChart.cpp pattern.
//
// Brief §6 Setup #25 originally specified iceberg detection via low |delta_z|
// + high vol_z + narrow range at a VP level (a price-pattern proxy because
// MT5/cTrader cannot see real depth depletion). This module upgrades that to
// a *true* microstructure detector by tracking, per price level:
//
//   - Consecutive trade prints at the same price within a 30s window
//   - Total volume traded against that price
//   - Maximum depth ever observed at that price during the absorption
//
// An iceberg fires when:
//   total_volume_traded >= max(min_total, max_depth_observed * refill_ratio)
//   AND consec_prints >= min_consec
//
// This is the canonical signature: the price level was being refilled by an
// institution beyond what was ever visible in the book.
//
// cTrader limitation: only the top-of-book bid/ask is reliably exposed via
// Symbol.Bid/Ask. Real depth ladder is not available on most retail brokers.
// This module degrades gracefully — when depth is unavailable, max_depth_observed
// stays at 0 and we fall back to the consec_prints + min_total threshold,
// which is still better than the original price-pattern proxy.

using System;
using System.Collections.Generic;
using cAlgo.API;
using cAlgo.API.Internals;

namespace GodmodeOfea
{
    public sealed class IcebergRecord
    {
        public double Price { get; set; }
        public TradeDir Side { get; set; }       // direction of the absorption (buyers absorbed = LONG side)
        public int     ConsecPrints { get; set; }
        public double  TotalVolume { get; set; }
        public double  MaxDepthObserved { get; set; }
        public DateTime LastTickTime { get; set; }
    }

    public sealed class IcebergTracker
    {
        private readonly Symbol _symbol;
        private readonly int _minConsec;
        private readonly double _minTotalVol;
        private readonly double _refillRatio;       // total_vol must exceed max_depth * this
        private readonly double _staleSeconds;
        private readonly double _consecResetSeconds;

        // Key = (rounded price, side). Use string for cross-side dedupe.
        private readonly Dictionary<string, IcebergRecord> _records = new Dictionary<string, IcebergRecord>();
        private readonly Dictionary<double, double> _lastDepthAtPrice = new Dictionary<double, double>();

        public IcebergTracker(Symbol symbol, int minConsec, double minTotalVol,
                              double refillRatio, double staleSeconds, double consecResetSeconds)
        {
            _symbol = symbol;
            _minConsec = Math.Max(2, minConsec);
            _minTotalVol = Math.Max(1.0, minTotalVol);
            _refillRatio = Math.Max(1.0, refillRatio);
            _staleSeconds = staleSeconds;
            _consecResetSeconds = consecResetSeconds;
        }

        private string MakeKey(double price, TradeDir side)
        {
            // Round to tick size to avoid float-key drift.
            double tick = Math.Max(_symbol.TickSize, 1e-9);
            double rounded = Math.Round(price / tick) * tick;
            return $"{rounded:F8}|{(int)side}";
        }

        // Call from a Symbol.Tick handler to maintain the depth-at-price observation.
        // For brokers that do not expose ladder depth, simply pass the BBO size as size.
        public void OnTopOfBook(double bidPrice, double bidSize, double askPrice, double askSize)
        {
            _lastDepthAtPrice[Round(bidPrice)] = bidSize;
            _lastDepthAtPrice[Round(askPrice)] = askSize;
        }

        private double Round(double price)
        {
            double tick = Math.Max(_symbol.TickSize, 1e-9);
            return Math.Round(price / tick) * tick;
        }

        // Call from your trade-tick handler. Returns a non-null record when the
        // iceberg condition fires. Side = LONG when sellers were absorbed at a bid
        // (i.e. buyers refilled), SHORT when buyers were absorbed at an ask.
        public IcebergRecord OnTrade(DateTime now, double price, double size, bool isBidAggressor)
        {
            // bid-aggressor = sellers crossing the bid; absorption against bid means buyers refilling →
            // bullish microstructure. Conventional convention.
            TradeDir side = isBidAggressor ? TradeDir.Long : TradeDir.Short;
            string key = MakeKey(price, side);
            double depthSeen = _lastDepthAtPrice.TryGetValue(Round(price), out var d) ? d : 0.0;

            IcebergRecord r;
            if (_records.TryGetValue(key, out r))
            {
                if ((now - r.LastTickTime).TotalSeconds <= _consecResetSeconds)
                {
                    r.ConsecPrints += 1;
                    r.TotalVolume += size;
                    if (depthSeen > r.MaxDepthObserved) r.MaxDepthObserved = depthSeen;
                    r.LastTickTime = now;
                }
                else
                {
                    r = StartFresh(price, side, size, depthSeen, now);
                    _records[key] = r;
                }
            }
            else
            {
                r = StartFresh(price, side, size, depthSeen, now);
                _records[key] = r;
            }

            double threshold = Math.Max(_minTotalVol, r.MaxDepthObserved * _refillRatio);
            if (r.ConsecPrints >= _minConsec && r.TotalVolume >= threshold)
            {
                // Fire once per record by clearing it so a new accumulation must start.
                _records.Remove(key);
                return r;
            }
            return null;
        }

        private static IcebergRecord StartFresh(double price, TradeDir side, double size, double depth, DateTime now)
        {
            return new IcebergRecord
            {
                Price = price,
                Side = side,
                ConsecPrints = 1,
                TotalVolume = size,
                MaxDepthObserved = depth,
                LastTickTime = now,
            };
        }

        public void CleanupStale(DateTime now)
        {
            var stale = new List<string>();
            foreach (var kv in _records)
            {
                if ((now - kv.Value.LastTickTime).TotalSeconds > _staleSeconds)
                    stale.Add(kv.Key);
            }
            foreach (var k in stale) _records.Remove(k);
        }
    }
}
