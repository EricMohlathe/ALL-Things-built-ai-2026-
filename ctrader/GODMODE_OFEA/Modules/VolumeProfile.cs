// VolumeProfile.cs
// POC / VAH / VAL / LVN / HVN + shape classifier (brief §11.2 + §11.3)
// Mirrors OF_VolumeProfile.mqh

using System;
using cAlgo.API;
using cAlgo.API.Internals;

namespace GodmodeOfea
{
    public sealed class VolumeProfile
    {
        private readonly Symbol _symbol;
        private readonly Bars _bars;
        private readonly int _bins;
        private readonly int _length;
        private readonly double _va;
        private readonly double _lvnRatio;
        private readonly double _hvnRatio;

        private double[] _binVol;
        private bool[] _lvnFlag;
        private bool[] _hvnFlag;
        private double _lo, _hi, _binSize;

        public double Poc { get; private set; }
        public double Vah { get; private set; }
        public double Val { get; private set; }
        public ProfileShape Shape { get; private set; } = ProfileShape.Unknown;
        public MarketState State => Shape == ProfileShape.D ? MarketState.Balanced
            : (Shape == ProfileShape.Unknown ? MarketState.Unknown : MarketState.Imbalanced);

        public VolumeProfile(Symbol s, Bars bars, int bins, int length, double va, double lvnR, double hvnR)
        {
            _symbol = s; _bars = bars; _bins = bins; _length = length;
            _va = va; _lvnRatio = lvnR; _hvnRatio = hvnR;
            _binVol  = new double[bins];
            _lvnFlag = new bool[bins];
            _hvnFlag = new bool[bins];
        }

        public bool Recompute()
        {
            Array.Clear(_binVol, 0, _binVol.Length);
            Array.Clear(_lvnFlag, 0, _lvnFlag.Length);
            Array.Clear(_hvnFlag, 0, _hvnFlag.Length);

            if (_bars.Count < _length + 2) return false;
            double hi = _bars.HighPrices.Last(1), lo = _bars.LowPrices.Last(1);
            for (int i = 1; i <= _length; i++)
            {
                hi = Math.Max(hi, _bars.HighPrices.Last(i));
                lo = Math.Min(lo, _bars.LowPrices.Last(i));
            }
            _lo = lo; _hi = hi;
            _binSize = (hi - lo) / _bins;
            if (_binSize <= 0) return false;

            for (int i = 1; i <= _length; i++)
            {
                double c = _bars.ClosePrices.Last(i);
                int b = (int)Math.Floor((c - lo) / _binSize);
                if (b < 0) b = 0; if (b >= _bins) b = _bins - 1;
                _binVol[b] += _bars.TickVolumes.Last(i);
            }

            int pocBin = 0;
            for (int i = 1; i < _bins; i++) if (_binVol[i] > _binVol[pocBin]) pocBin = i;
            Poc = lo + (pocBin + 0.5) * _binSize;

            double total = 0;
            for (int i = 0; i < _bins; i++) total += _binVol[i];
            double target = total * _va;
            double acc = _binVol[pocBin];
            int hiBin = pocBin, loBin = pocBin;
            while (acc < target && (hiBin < _bins - 1 || loBin > 0))
            {
                double up = hiBin + 1 < _bins ? _binVol[hiBin + 1] : -1;
                double dn = loBin - 1 >= 0   ? _binVol[loBin - 1] : -1;
                if (up >= dn && up >= 0) { hiBin++; acc += up; }
                else if (dn >= 0)         { loBin--; acc += dn; }
                else break;
            }
            Vah = lo + (hiBin + 1) * _binSize;
            Val = lo + loBin * _binSize;

            double pocVol = _binVol[pocBin];
            for (int i = 0; i < _bins; i++)
            {
                _lvnFlag[i] = _binVol[i] < pocVol * _lvnRatio;
                _hvnFlag[i] = _binVol[i] > pocVol * _hvnRatio;
            }

            ClassifyShape(pocBin, pocVol);
            return true;
        }

        private void ClassifyShape(int pocBin, double pocVol)
        {
            int lowBin = -1, highBin = -1;
            for (int i = 0; i < _bins; i++)
                if (_binVol[i] > 0) { if (lowBin < 0) lowBin = i; highBin = i; }
            if (lowBin < 0) { Shape = ProfileShape.Unknown; return; }
            int midBin = (lowBin + highBin) / 2;
            double upper = 0, lower = 0;
            for (int i = midBin; i <= highBin; i++) upper += _binVol[i];
            for (int i = lowBin; i < midBin; i++)  lower += _binVol[i];
            double tot = upper + lower;
            double skew = tot > 0 ? (upper - lower) / tot : 0;

            double sum = 0; int nz = 0;
            for (int i = 0; i < _bins; i++) if (_binVol[i] > 0) { sum += _binVol[i]; nz++; }
            double peak = (nz > 0 && sum > 0) ? pocVol / (sum / nz) : 1.0;

            if (Math.Abs(skew) < 0.10 && peak > 2.0) Shape = ProfileShape.D;
            else if (skew > 0.20)                    Shape = ProfileShape.P;
            else if (skew < -0.20)                   Shape = ProfileShape.b;
            else if (peak < 1.3)                     Shape = ProfileShape.Thin;
            else                                     Shape = ProfileShape.D;
        }

        public VpLoc LocationAt(double price, double tolPips)
        {
            // Guard: callers may invoke this from OnTick before the first
            // Recompute() runs at bar close. _binSize == 0 would NaN the index.
            if (_binSize <= 0 || double.IsNaN(price)) return VpLoc.None;
            double tol = tolPips * OFHelpers.PipSize(_symbol);
            if (Math.Abs(price - Poc) < tol) return VpLoc.Poc;
            if (Math.Abs(price - Vah) < tol) return VpLoc.Vah;
            if (Math.Abs(price - Val) < tol) return VpLoc.Val;
            int bin = (int)Math.Floor((price - _lo) / _binSize);
            if (bin >= 0 && bin < _bins)
            {
                if (_lvnFlag[bin]) return VpLoc.Lvn;
                if (_hvnFlag[bin]) return VpLoc.Hvn;
            }
            return VpLoc.None;
        }
    }
}
