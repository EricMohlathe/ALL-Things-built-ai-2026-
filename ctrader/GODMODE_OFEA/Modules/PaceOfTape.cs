// PaceOfTape.cs
// Pace-of-Tape microstructure indicator adapted from Frozen Tundra pace_of_tape.cpp.
//
// What it does:
//   Tracks tick/volume rate over a rolling window and compares to a *lagging*
//   maximum (i.e. the max excludes the most recent fraction of the window).
//   This avoids the "we always seem to be at max" feedback loop that breaks
//   naive max-tracking under sustained volatility.
//
// Why it's a real edge addition (brief §22 marginal-gain stack candidate):
//   Pace = current_volume / lagging_max ∈ [0..1]. When pace > 0.85 during an
//   absorption setup, you have an institutional aggression confirmation that
//   was previously only loosely captured by the existing volume Z-score.
//
// Wired as:
//   - New input AggressionPaceThreshold (default 0.85)
//   - New gate condition appended to GATE 6 footprint signal
//   - New notification N-V (Pace-of-Tape elevated)

using System;
using System.Collections.Generic;

namespace GodmodeOfea
{
    public sealed class PaceOfTape
    {
        private readonly int _windowSeconds;
        private readonly int _laggingFraction;   // lagging-max excludes this 1/N fraction of window
        private readonly Queue<(DateTime ts, double size)> _records = new Queue<(DateTime, double)>();
        private double _laggingMax = 0.0;

        public PaceOfTape(int windowSeconds = 60, int laggingFraction = 5)
        {
            _windowSeconds = Math.Max(10, windowSeconds);
            _laggingFraction = Math.Max(2, laggingFraction);
        }

        public void OnTrade(DateTime ts, double size)
        {
            _records.Enqueue((ts, size));
            DateTime cutoff = ts.AddSeconds(-_windowSeconds);
            while (_records.Count > 0 && _records.Peek().ts < cutoff) _records.Dequeue();

            // Lagging-max: only consider trades older than (window / fraction) seconds.
            DateTime maxCutoff = ts.AddSeconds(-(_windowSeconds / (double)_laggingFraction));
            double recentSum = 0.0;
            foreach (var (t, s) in _records)
            {
                if (t <= maxCutoff) recentSum += s;
            }
            if (recentSum > _laggingMax) _laggingMax = recentSum;
        }

        public double Pace()
        {
            if (_laggingMax <= 0) return 0.0;
            double cur = 0.0;
            foreach (var (_, s) in _records) cur += s;
            return cur / _laggingMax;
        }

        public double LaggingMax => _laggingMax;
        public int RecordCount => _records.Count;
    }
}
