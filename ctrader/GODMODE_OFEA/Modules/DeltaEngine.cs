// DeltaEngine.cs
// Tick-delta accumulator + CVD + divergence (brief §11.1, §11.5)
// Mirrors mt5/Include/OF_DeltaEngine.mqh

using System;
using System.Collections.Generic;
using cAlgo.API;
using cAlgo.API.Internals;

namespace GodmodeOfea
{
    public sealed class DeltaEngine
    {
        private readonly Symbol _symbol;
        private readonly int _lookback;
        private readonly Bars _bars;

        private double _tickBuy;
        private double _tickSell;
        // Cache last mid so we can classify the *next* tick as aggressor-buy/sell
        // based on direction of mid movement. cAlgo's SymbolTickEventArgs gives
        // only the current Bid/Ask snapshot — Ask is always > Bid, so the prior
        // implementation (Ask > Bid) was always true and _tickSell never incremented.
        private double _lastMid;
        private bool _hasLastMid;

        // newest-first lists; index 0 = most recently closed bar
        private readonly List<double> _barDelta;
        private readonly List<double> _volume;
        private readonly List<double> _cvd;

        public DeltaEngine(Symbol symbol, Bars bars, int lookback)
        {
            _symbol = symbol;
            _bars = bars;
            _lookback = Math.Max(lookback, 30);
            _barDelta = new List<double>(_lookback);
            _volume   = new List<double>(_lookback);
            _cvd      = new List<double>(_lookback);
            for (int i = 0; i < _lookback; i++)
            {
                _barDelta.Add(0); _volume.Add(0); _cvd.Add(0);
            }
            _symbol.Tick += OnTick;
        }

        public void Detach() { _symbol.Tick -= OnTick; }

        // Brief §11.1 — partition by ask/bid trade aggression.
        // cAlgo SymbolTickEventArgs exposes only the current Bid/Ask snapshot
        // (no per-tick volume, no aggressor flag). We approximate by comparing
        // the current mid to the previous mid: uptick = aggressor buy, downtick
        // = aggressor sell. Brokers without raw volume still get directional skew.
        private void OnTick(SymbolTickEventArgs args)
        {
            double mid = (args.Bid + args.Ask) * 0.5;
            if (!_hasLastMid) { _lastMid = mid; _hasLastMid = true; return; }
            const double v = 1.0;
            if (mid > _lastMid)      _tickBuy  += v;
            else if (mid < _lastMid) _tickSell += v;
            _lastMid = mid;
        }

        public void OnBarClose()
        {
            double bd = _tickBuy - _tickSell;
            double tv = _tickBuy + _tickSell;
            if (tv <= 0) tv = _bars.TickVolumes.Last(1);

            // shift right
            for (int i = _lookback - 1; i > 0; --i)
            {
                _barDelta[i] = _barDelta[i - 1];
                _volume[i]   = _volume[i - 1];
                _cvd[i]      = _cvd[i - 1];
            }
            _barDelta[0] = bd;
            _volume[0]   = tv;
            _cvd[0]      = _cvd[1] + bd;
            _tickBuy = 0; _tickSell = 0;
        }

        public double Cvd      => _cvd[0];
        public double BarDelta => _barDelta[0];
        public double Volume(int i) => (i >= 0 && i < _lookback) ? _volume[i] : 0;
        public double Delta(int i)  => (i >= 0 && i < _lookback) ? _barDelta[i] : 0;

        public double VolumeZ()
        {
            double mean = 0;
            for (int i = 0; i < _lookback; i++) mean += _volume[i];
            mean /= _lookback;
            double sd = 0;
            for (int i = 0; i < _lookback; i++) sd += (_volume[i] - mean) * (_volume[i] - mean);
            sd = Math.Sqrt(sd / _lookback);
            return sd < 1e-9 ? 0 : (_volume[0] - mean) / sd;
        }

        public double DeltaZ()
        {
            double mean = 0;
            for (int i = 0; i < _lookback; i++) mean += _barDelta[i];
            mean /= _lookback;
            double sd = 0;
            for (int i = 0; i < _lookback; i++) sd += (_barDelta[i] - mean) * (_barDelta[i] - mean);
            sd = Math.Sqrt(sd / _lookback);
            return sd < 1e-9 ? 0 : (_barDelta[0] - mean) / sd;
        }

        public double CvdSlope5()
        {
            int n = Math.Min(5, _lookback - 1);
            return _cvd[0] - _cvd[n];
        }

        public bool BullishDivergence()
        {
            int n = Math.Min(20, _lookback - 1);
            double pLow = _bars.LowPrices.Last(1);
            for (int i = 2; i <= n; i++) pLow = Math.Min(pLow, _bars.LowPrices.Last(i));
            double curLow = _bars.LowPrices.Last(1);
            double cvdMin = _cvd[1];
            for (int i = 2; i <= n; i++) if (_cvd[i] < cvdMin) cvdMin = _cvd[i];
            return curLow <= pLow + _symbol.TickSize && _cvd[1] > cvdMin + 1e-9;
        }

        public bool BearishDivergence()
        {
            int n = Math.Min(20, _lookback - 1);
            double pHigh = _bars.HighPrices.Last(1);
            for (int i = 2; i <= n; i++) pHigh = Math.Max(pHigh, _bars.HighPrices.Last(i));
            double curHigh = _bars.HighPrices.Last(1);
            double cvdMax = _cvd[1];
            for (int i = 2; i <= n; i++) if (_cvd[i] > cvdMax) cvdMax = _cvd[i];
            return curHigh >= pHigh - _symbol.TickSize && _cvd[1] < cvdMax - 1e-9;
        }
    }
}
