// TradeManager.cs
// Partial close / BE / trail / POC exit / session close (brief §5)
// Mirrors OF_TradeManager.mqh

using System;
using System.Collections.Generic;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace GodmodeOfea
{
    public sealed class TradeManager
    {
        private readonly Robot _robot;
        private readonly Symbol _symbol;
        private readonly string _label;
        private readonly bool _partialClose;
        private readonly double _partialPct, _partialAtR, _beAtR, _trailAtrMult;
        private readonly bool _useTrail, _exitAtPoc;
        private readonly AverageTrueRange _atr;
        // Track which positions have already had a partial — without this the
        // partial-close fires every tick once price is past _partialAtR R.
        private readonly HashSet<long> _partialDone = new HashSet<long>();

        public TradeManager(Robot robot, Symbol symbol, string label,
            bool partial, double partialPct, double partialAtR, double beAtR,
            bool useTrail, double trailAtr, bool exitPoc, AverageTrueRange atr)
        {
            _robot = robot; _symbol = symbol; _label = label;
            _partialClose = partial; _partialPct = partialPct; _partialAtR = partialAtR;
            _beAtR = beAtR; _useTrail = useTrail; _trailAtrMult = trailAtr;
            _exitAtPoc = exitPoc; _atr = atr;
        }

        public Position FindOpenPosition()
        {
            return _robot.Positions.FirstOrDefault(p => p.SymbolName == _symbol.Name && p.Label == _label);
        }

        public bool OpenPosition(TradeDir dir, double volume, double sl, double tp, string comment)
        {
            if (volume <= 0 || dir == TradeDir.None) return false;
            // Round to broker volume step and respect minimums; the caller should
            // already have done this but defence-in-depth is cheap.
            volume = _symbol.NormalizeVolumeInUnits(volume, RoundingMode.Down);
            if (volume < _symbol.VolumeInUnitsMin)
            {
                _robot.Print($"OpenPosition skipped: volume {volume} below symbol min {_symbol.VolumeInUnitsMin}");
                return false;
            }
            var type = dir == TradeDir.Long ? TradeType.Buy : TradeType.Sell;
            double pip = OFHelpers.PipSize(_symbol);
            if (pip <= 0) { _robot.Print("OpenPosition skipped: zero pip size"); return false; }
            double refPx = dir == TradeDir.Long ? _symbol.Ask : _symbol.Bid;
            if (refPx <= 0) { _robot.Print("OpenPosition skipped: no quote yet"); return false; }
            double slPips = dir == TradeDir.Long ? (refPx - sl) / pip : (sl - refPx) / pip;
            double tpPips = dir == TradeDir.Long ? (tp - refPx) / pip : (refPx - tp) / pip;
            // Both distances must be positive — an inverted SL/TP is a logic bug
            // upstream and should not silently flip the order.
            if (slPips <= 0 || tpPips <= 0 || double.IsNaN(slPips) || double.IsNaN(tpPips))
            {
                _robot.Print($"OpenPosition skipped: invalid SL/TP geometry slPips={slPips:F2} tpPips={tpPips:F2}");
                return false;
            }
            try
            {
                var r = _robot.ExecuteMarketOrder(type, _symbol.Name, volume, _label, slPips, tpPips, comment);
                if (r == null || !r.IsSuccessful)
                {
                    _robot.Print($"OpenPosition failed: {r?.Error}");
                    return false;
                }
                return true;
            }
            catch (Exception e)
            {
                _robot.Print($"OpenPosition err: {e.Message}");
                return false;
            }
        }

        public void ManagePosition(double poc)
        {
            var p = FindOpenPosition();
            if (p == null) return;
            double cur = p.TradeType == TradeType.Buy ? _symbol.Bid : _symbol.Ask;
            double risk = Math.Abs(p.EntryPrice - (p.StopLoss ?? p.EntryPrice));
            if (risk <= 0) return;
            double rMult = p.TradeType == TradeType.Buy
                ? (cur - p.EntryPrice) / risk
                : (p.EntryPrice - cur) / risk;

            if (_partialClose && rMult >= _partialAtR && !_partialDone.Contains(p.Id))
            {
                double closeVol = _symbol.NormalizeVolumeInUnits(p.VolumeInUnits * (_partialPct / 100.0), RoundingMode.Down);
                if (closeVol > 0 && closeVol >= _symbol.VolumeInUnitsMin)
                {
                    try { _robot.ClosePosition(p, closeVol); _partialDone.Add(p.Id); }
                    catch (Exception e) { _robot.Print($"Partial close err: {e.Message}"); }
                }
            }
            if (rMult >= _beAtR)
            {
                double pip = OFHelpers.PipSize(_symbol);
                double targetSl = p.EntryPrice + (p.TradeType == TradeType.Buy ? pip : -pip);
                // Only push to BE if SL is currently worse than BE — avoids spamming
                // ModifyPosition every tick (cTrader throttles + logs each call).
                double curSl = p.StopLoss ?? (p.TradeType == TradeType.Buy ? double.MinValue : double.MaxValue);
                bool needBE = p.TradeType == TradeType.Buy ? curSl < targetSl - 0.5 * pip
                                                            : curSl > targetSl + 0.5 * pip;
                if (needBE)
                {
                    try { _robot.ModifyPosition(p, targetSl, p.TakeProfit); }
                    catch (Exception e) { _robot.Print($"BE modify err: {e.Message}"); }
                }
            }
            if (_useTrail && rMult >= _beAtR)
            {
                double atr = _atr.Result.Last(0);
                if (atr > 0)
                {
                    double newSl = p.TradeType == TradeType.Buy
                        ? cur - atr * _trailAtrMult
                        : cur + atr * _trailAtrMult;
                    bool tighter = p.TradeType == TradeType.Buy
                        ? newSl > (p.StopLoss ?? double.NegativeInfinity)
                        : newSl < (p.StopLoss ?? double.PositiveInfinity);
                    if (tighter)
                    {
                        try { _robot.ModifyPosition(p, newSl, p.TakeProfit); }
                        catch (Exception e) { _robot.Print($"Trail modify err: {e.Message}"); }
                    }
                }
            }
            if (_exitAtPoc && poc > 0)
            {
                bool reached = p.TradeType == TradeType.Buy ? cur >= poc : cur <= poc;
                if (reached)
                {
                    try { _robot.ClosePosition(p); _partialDone.Remove(p.Id); }
                    catch (Exception e) { _robot.Print($"POC exit err: {e.Message}"); }
                }
            }
        }

        public void CloseAll()
        {
            var p = FindOpenPosition();
            if (p != null)
            {
                try { _robot.ClosePosition(p); _partialDone.Remove(p.Id); }
                catch (Exception e) { _robot.Print($"CloseAll err: {e.Message}"); }
            }
        }
    }
}
