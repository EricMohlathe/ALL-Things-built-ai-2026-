// Absorption cBot — cTrader / cAlgo C# mirror of absorption_ea_mt5.mq5
using System;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace cAlgo.Robots
{
    [Robot(AccessRights = AccessRights.None, AddIndicators = true, TimeZone = TimeZones.UTC)]
    public class AbsorptionBot : Robot
    {
        [Parameter("Risk %",            DefaultValue = 0.5)]  public double InpRiskPct { get; set; }
        [Parameter("Label",             DefaultValue = "ABS")] public string InpLabel { get; set; }
        [Parameter("Max Spread (pips)", DefaultValue = 3.0)]  public double InpMaxSpread { get; set; }
        [Parameter("Min Signed Delta",  DefaultValue = 1500)] public double InpMinSignedDelta { get; set; }
        [Parameter("Max Range x ATR",   DefaultValue = 0.5)]  public double InpMaxRangeATR { get; set; }
        [Parameter("ATR Period",        DefaultValue = 14)]   public int InpATRPeriod { get; set; }

        AverageTrueRange _atr;
        DateTime _lastBarOpen = DateTime.MinValue;

        protected override void OnStart()
        {
            _atr = Indicators.AverageTrueRange(InpATRPeriod, MovingAverageType.Simple);
        }

        bool IsNewBar()
        {
            if (Bars.LastBar.OpenTime == _lastBarOpen) return false;
            _lastBarOpen = Bars.LastBar.OpenTime;
            return true;
        }

        bool IsAbsorptionBearish(int shift)
        {
            var b = Bars[Bars.Count - 1 - shift];
            double signedDelta = (b.Close >= b.Open) ? b.TickVolume : -b.TickVolume;
            double range = b.High - b.Low;
            double atr = _atr.Result.Last(shift);
            if (atr <= 0) return false;
            return (signedDelta >= InpMinSignedDelta && b.Close < b.Open && range <= atr * InpMaxRangeATR);
        }

        double UnitsByRisk(double slPips)
        {
            double riskMoney = Account.Balance * InpRiskPct / 100.0;
            if (slPips <= 0 || Symbol.PipValue <= 0) return 0;
            double units = riskMoney / (slPips * Symbol.PipValue);
            units = Symbol.NormalizeVolumeInUnits(units, RoundingMode.Down);
            return Math.Max(units, Symbol.VolumeInUnitsMin);
        }

        protected override void OnTick()
        {
            if (!IsNewBar()) return;
            if ((Symbol.Ask - Symbol.Bid) / Symbol.PipSize > InpMaxSpread) return;
            if (Positions.FindAll(InpLabel, SymbolName).Length > 0) return;

            if (IsAbsorptionBearish(1))
            {
                double atrPips = _atr.Result.Last(1) / Symbol.PipSize;
                double slPips  = Math.Max(20, atrPips * 1.2);
                double tpPips  = slPips * 2.0;
                double units   = UnitsByRisk(slPips);
                if (units > 0)
                    ExecuteMarketOrder(TradeType.Sell, SymbolName, units, InpLabel, slPips, tpPips);
            }
        }
    }
}
