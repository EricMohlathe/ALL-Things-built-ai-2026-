// TradeManager.cs
// Partial close / BE / trail / POC exit / session close (brief §5)
// Mirrors OF_TradeManager.mqh

using System;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace GodmodeOfea
{
    public sealed class TradeManager
    {
        private readonly Algo _robot;
        private readonly Symbol _symbol;
        private readonly string _label;
        private readonly bool _partialClose;
        private readonly double _partialPct, _partialAtR, _beAtR, _trailAtrMult;
        private readonly bool _useTrail, _exitAtPoc;
        private readonly AverageTrueRange _atr;

        public TradeManager(Algo robot, Symbol symbol, string label,
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
            if (volume <= 0) return false;
            var type = dir == TradeDir.Long ? TradeType.Buy : TradeType.Sell;
            double slPips = Math.Abs((dir == TradeDir.Long ? _symbol.Ask - sl : sl - _symbol.Bid)) / OFHelpers.PipSize(_symbol);
            double tpPips = Math.Abs((dir == TradeDir.Long ? tp - _symbol.Ask : _symbol.Bid - tp)) / OFHelpers.PipSize(_symbol);
            try
            {
                var r = _robot.ExecuteMarketOrder(type, _symbol.Name, volume, _label, slPips, tpPips, comment);
                return r.IsSuccessful;
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

            if (_partialClose && rMult >= _partialAtR && (p.Comment ?? "").Contains("[P]") == false)
            {
                double closeVol = _symbol.NormalizeVolumeInUnits(p.VolumeInUnits * (_partialPct / 100.0), RoundingMode.Down);
                if (closeVol > 0) try { _robot.ClosePosition(p, closeVol); } catch { }
            }
            if (rMult >= _beAtR)
            {
                double pip = OFHelpers.PipSize(_symbol);
                double newSlPips = p.TradeType == TradeType.Buy
                    ? (p.EntryPrice + pip - cur) / pip * -1
                    : (cur - p.EntryPrice + pip) / pip;
                try { _robot.ModifyPosition(p, p.EntryPrice + (p.TradeType == TradeType.Buy ? pip : -pip), p.TakeProfit); } catch { }
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
                    if (tighter) try { _robot.ModifyPosition(p, newSl, p.TakeProfit); } catch { }
                }
            }
            if (_exitAtPoc && poc > 0)
            {
                bool reached = p.TradeType == TradeType.Buy ? cur >= poc : cur <= poc;
                if (reached) try { _robot.ClosePosition(p); } catch { }
            }
        }

        public void CloseAll()
        {
            var p = FindOpenPosition();
            if (p != null) try { _robot.ClosePosition(p); } catch { }
        }
    }
}
