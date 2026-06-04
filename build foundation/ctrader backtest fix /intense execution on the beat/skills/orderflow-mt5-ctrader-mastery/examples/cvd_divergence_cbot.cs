using System;
using System.Collections.Generic;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Internals;

namespace cAlgo.Robots
{
    [Robot(AccessRights = AccessRights.None, TimeZone = TimeZones.UTC)]
    public class CvdDivergenceBot : Robot
    {
        [Parameter("Risk %",   DefaultValue = 0.5)]   public double InpRiskPct { get; set; }
        [Parameter("Lookback", DefaultValue = 20)]    public int    InpLookback { get; set; }
        [Parameter("Label",    DefaultValue = "CVD")] public string InpLabel { get; set; }

        readonly List<double> _cvd = new List<double>();
        DateTime _lastBarOpen = DateTime.MinValue;
        double _prevAsk = 0, _prevBid = 0, _curDelta = 0;

        protected override void OnTick()
        {
            UpdateCvd();
            if (Bars.LastBar.OpenTime == _lastBarOpen) return;
            _lastBarOpen = Bars.LastBar.OpenTime;
            OnNewBarBookkeeping();
            if (Positions.FindAll(InpLabel, SymbolName).Length > 0) return;

            if (IsBearDivergence())
            {
                double slPips = 30;
                double tpPips = 60;
                double units = UnitsByRisk(slPips);
                if (units > 0) ExecuteMarketOrder(TradeType.Sell, SymbolName, units, InpLabel, slPips, tpPips);
            }
        }

        void UpdateCvd()
        {
            if (_prevAsk == 0) { _prevAsk = Symbol.Ask; _prevBid = Symbol.Bid; return; }
            int s = 0;
            if (Symbol.Ask > _prevAsk) s = 1;
            else if (Symbol.Bid < _prevBid) s = -1;
            _curDelta += s;
            _prevAsk = Symbol.Ask; _prevBid = Symbol.Bid;
        }

        void OnNewBarBookkeeping()
        {
            double prev = _cvd.Count > 0 ? _cvd[_cvd.Count - 1] : 0;
            _cvd.Add(prev + _curDelta);
            _curDelta = 0;
        }

        bool IsBearDivergence()
        {
            if (_cvd.Count < InpLookback + 2) return false;
            double pHigh = Bars[Bars.Count - 2].High;
            double dHigh = _cvd[_cvd.Count - 2];
            for (int i = 3; i <= InpLookback; i++)
            {
                double pi = Bars[Bars.Count - i].High;
                double di = _cvd[_cvd.Count - i];
                if (pi > pHigh && di < dHigh) return true;
            }
            return false;
        }

        double UnitsByRisk(double slPips)
        {
            double riskMoney = Account.Balance * InpRiskPct / 100.0;
            if (slPips <= 0 || Symbol.PipValue <= 0) return 0;
            double units = riskMoney / (slPips * Symbol.PipValue);
            units = Symbol.NormalizeVolumeInUnits(units, RoundingMode.Down);
            return Math.Max(units, Symbol.VolumeInUnitsMin);
        }
    }
}
