// ===================================================================
//  OrderFlowBot Template — orderflow-mt5-ctrader-mastery
//  Production scaffold mirroring mt5_ea_template.mq5 line-for-line
// ===================================================================
using System;
using System.Collections.Generic;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace cAlgo.Robots
{
    [Robot(AccessRights = AccessRights.None, AddIndicators = true, TimeZone = TimeZones.UTC)]
    public class OrderFlowBot : Robot
    {
        // ===== Risk =====
        [Parameter("Risk %",                Group = "Risk", DefaultValue = 0.5,  MinValue = 0.01)] public double InpRiskPct { get; set; }
        [Parameter("Max Daily Loss %",      Group = "Risk", DefaultValue = 3.0)]                  public double InpMaxDailyLossPct { get; set; }
        [Parameter("Max Total Drawdown %",  Group = "Risk", DefaultValue = 8.0)]                  public double InpMaxTotalDDPct { get; set; }
        [Parameter("Max EA Positions",      Group = "Risk", DefaultValue = 1)]                    public int    InpMaxPositions { get; set; }
        [Parameter("Cooldown (min)",        Group = "Risk", DefaultValue = 15)]                   public int    InpCooldownMin { get; set; }

        // ===== Filters =====
        [Parameter("Max Spread (pips)",     Group = "Filters", DefaultValue = 3.0)]               public double InpMaxSpread { get; set; }
        [Parameter("Slippage (pips)",       Group = "Filters", DefaultValue = 1.0)]               public double InpSlippage { get; set; }
        [Parameter("Session Start (UTC h)", Group = "Filters", DefaultValue = 7)]                 public int    InpSessionStart { get; set; }
        [Parameter("Session End (UTC h)",   Group = "Filters", DefaultValue = 16)]                public int    InpSessionEnd { get; set; }

        // ===== Order Flow =====
        [Parameter("Delta Lookback",        Group = "OrderFlow", DefaultValue = 20)]              public int    InpDeltaLookback { get; set; }
        [Parameter("Imbalance Ratio",       Group = "OrderFlow", DefaultValue = 3.0)]             public double InpImbalanceRatio { get; set; }
        [Parameter("Imbalance Min Count",   Group = "OrderFlow", DefaultValue = 3)]               public int    InpImbalanceCount { get; set; }
        [Parameter("Exhaustion Bars",       Group = "OrderFlow", DefaultValue = 3)]               public int    InpExhaustionBars { get; set; }
        [Parameter("Initiative Vol Mult",   Group = "OrderFlow", DefaultValue = 1.5)]             public double InpInitiativeVolMult { get; set; }

        // ===== Confluence =====
        [Parameter("Entry Threshold",       Group = "Confluence", DefaultValue = 0.60)]           public double InpEntryThreshold { get; set; }

        // ===== Trade Management =====
        [Parameter("BE Distance (pips)",    Group = "TradeMgmt", DefaultValue = 10.0)]            public double InpBEDistancePips { get; set; }
        [Parameter("BE Buffer (pips)",      Group = "TradeMgmt", DefaultValue = 0.5)]             public double InpBEBufferPips { get; set; }
        [Parameter("Trail Distance (pips)", Group = "TradeMgmt", DefaultValue = 8.0)]             public double InpTrailDistancePips { get; set; }
        [Parameter("Time Stop (min)",       Group = "TradeMgmt", DefaultValue = 240)]             public int    InpTimeStopMin { get; set; }

        // ===== Identification =====
        [Parameter("Magic / Label",         Group = "Identity", DefaultValue = "OFBot")]          public string InpLabel { get; set; }

        // ===== State =====
        readonly List<double> _cvd = new List<double>();
        DateTime _lastBarOpen = DateTime.MinValue;
        DateTime _dayKey;
        double   _dayStartEquity;
        double   _peakEquity;
        DateTime _lastTradeCloseTime = DateTime.MinValue;
        double   _curDelta = 0;
        double   _prevAsk = 0, _prevBid = 0;

        AverageTrueRange _atr;

        protected override void OnStart()
        {
            _peakEquity = Account.Equity;
            _atr = Indicators.AverageTrueRange(14, MovingAverageType.Simple);

            // depth feed (optional — MarketDepth requires broker support; disabled by default)
            // Symbol.MarketDepth.Updated += OnDepthUpdated;

            Positions.Closed += OnPositionsClosed;

            Print("OFBot started: {0} {1}", SymbolName, TimeFrame);
        }

        protected override void OnStop()
        {
            Print("OFBot stopped");
        }

        // ===== Helpers =====
        bool IsNewBar()
        {
            if (Bars.LastBar.OpenTime == _lastBarOpen) return false;
            _lastBarOpen = Bars.LastBar.OpenTime;
            return true;
        }

        bool DailyLossOk()
        {
            var d = Server.Time.Date;
            if (d != _dayKey) { _dayKey = d; _dayStartEquity = Account.Equity; }
            double dd = (_dayStartEquity - Account.Equity) / _dayStartEquity * 100.0;
            return dd < InpMaxDailyLossPct;
        }

        bool TotalDDOk()
        {
            if (Account.Equity > _peakEquity) _peakEquity = Account.Equity;
            double dd = (_peakEquity - Account.Equity) / _peakEquity * 100.0;
            return dd < InpMaxTotalDDPct;
        }

        bool SpreadOk()
        {
            double sp = (Symbol.Ask - Symbol.Bid) / Symbol.PipSize;
            return sp <= InpMaxSpread;
        }

        bool SessionOk()
        {
            int h = Server.Time.Hour;
            return h >= InpSessionStart && h < InpSessionEnd;
        }

        bool CooldownOk()
        {
            if (_lastTradeCloseTime == DateTime.MinValue) return true;
            return (Server.Time - _lastTradeCloseTime).TotalMinutes >= InpCooldownMin;
        }

        int EaPositionsCount()
        {
            return Positions.FindAll(InpLabel, SymbolName).Length;
        }

        double UnitsByRisk(double slPips)
        {
            double riskMoney = Account.Balance * InpRiskPct / 100.0;
            if (slPips <= 0 || Symbol.PipValue <= 0) return 0;
            double units = riskMoney / (slPips * Symbol.PipValue);
            units = Symbol.NormalizeVolumeInUnits(units, RoundingMode.Down);
            return Math.Max(units, Symbol.VolumeInUnitsMin);
        }

        bool AllGuardsPass()
        {
            return DailyLossOk() && TotalDDOk() && SpreadOk() && SessionOk()
                && CooldownOk() && (EaPositionsCount() < InpMaxPositions);
        }

        // ===== Order-flow primitives =====
        void UpdateDeltaCvd()
        {
            if (_prevAsk == 0) { _prevAsk = Symbol.Ask; _prevBid = Symbol.Bid; return; }
            int sign = 0;
            if (Symbol.Ask > _prevAsk)      sign =  1;
            else if (Symbol.Bid < _prevBid) sign = -1;
            _curDelta += sign;
            _prevAsk = Symbol.Ask;
            _prevBid = Symbol.Bid;
        }

        void OnNewBarBookkeeping()
        {
            double prev = _cvd.Count > 0 ? _cvd[_cvd.Count - 1] : 0;
            _cvd.Add(prev + _curDelta);
            _curDelta = 0;
        }

        // ===== Signal logic (drop your detector here) =====
        (double score, int dir) ComputeEntryScore()
        {
            if (_cvd.Count < InpDeltaLookback + 2) return (0, 0);
            var b1 = Bars[Bars.Count - 2]; // last closed bar
            double avgV = 0;
            for (int i = 3; i < 3 + InpDeltaLookback; i++) avgV += Bars[Bars.Count - i].TickVolume;
            avgV /= InpDeltaLookback;

            bool bullInit = (b1.Close > b1.Open) && (b1.TickVolume >= avgV * InpInitiativeVolMult);
            bool bearInit = (b1.Close < b1.Open) && (b1.TickVolume >= avgV * InpInitiativeVolMult);

            int last = _cvd.Count - 1;
            int back = Math.Max(0, last - InpDeltaLookback);
            bool cvdUp   = _cvd[last] > _cvd[back];
            bool cvdDown = _cvd[last] < _cvd[back];

            if (bullInit && cvdUp)   return (0.7,  1);
            if (bearInit && cvdDown) return (0.7, -1);
            return (0, 0);
        }

        // ===== Entry =====
        void TryEnter(int dir)
        {
            double atrPips = _atr.Result.LastValue / Symbol.PipSize;
            double slPips  = Math.Max(20, atrPips * 1.2);
            double tpPips  = slPips * 2.0;
            double units   = UnitsByRisk(slPips);
            if (units <= 0) return;
            var side = dir > 0 ? TradeType.Buy : TradeType.Sell;
            var r = ExecuteMarketOrder(side, SymbolName, units, InpLabel, slPips, tpPips);
            if (!r.IsSuccessful) Print("Order failed: " + r.Error);
        }

        // ===== Trade management =====
        void ManagePositions()
        {
            foreach (var p in Positions.FindAll(InpLabel, SymbolName))
            {
                double cur = p.TradeType == TradeType.Buy ? Symbol.Bid : Symbol.Ask;
                double favorablePips = p.TradeType == TradeType.Buy
                    ? (cur - p.EntryPrice) / Symbol.PipSize
                    : (p.EntryPrice - cur) / Symbol.PipSize;

                // BE move
                double bePrice = p.TradeType == TradeType.Buy
                    ? p.EntryPrice + InpBEBufferPips * Symbol.PipSize
                    : p.EntryPrice - InpBEBufferPips * Symbol.PipSize;
                bool needBe = (p.TradeType == TradeType.Buy && (p.StopLoss == null || p.StopLoss < bePrice))
                           || (p.TradeType == TradeType.Sell && (p.StopLoss == null || p.StopLoss > bePrice));
                if (favorablePips >= InpBEDistancePips && needBe)
                    ModifyPosition(p, bePrice, p.TakeProfit, ProtectionType.Absolute);

                // Trailing
                if (favorablePips > InpTrailDistancePips)
                {
                    double newSl = p.TradeType == TradeType.Buy
                        ? cur - InpTrailDistancePips * Symbol.PipSize
                        : cur + InpTrailDistancePips * Symbol.PipSize;
                    bool tighter = (p.TradeType == TradeType.Buy && (p.StopLoss == null || newSl > p.StopLoss))
                                || (p.TradeType == TradeType.Sell && (p.StopLoss == null || newSl < p.StopLoss));
                    if (tighter) ModifyPosition(p, newSl, p.TakeProfit, ProtectionType.Absolute);
                }
            }
        }

        // ===== Dashboard =====
        void DrawDashboard(double score, int dir)
        {
            string txt = string.Format(
                "OFBot  {0}  {1}\nScore: {2:0.00} (thresh {3:0.00})\nDir: {4}\n" +
                "Spread: {5:0.0} pips  (max {6:0.0})\n" +
                "Daily PL: {7:0.00}%  (halt {8:0.0}%)\n" +
                "EA pos: {9} / {10}",
                SymbolName, TimeFrame,
                score, InpEntryThreshold, dir > 0 ? "LONG" : dir < 0 ? "SHORT" : "--",
                (Symbol.Ask - Symbol.Bid) / Symbol.PipSize, InpMaxSpread,
                _dayStartEquity > 0 ? (_dayStartEquity - Account.Equity) / _dayStartEquity * 100.0 : 0, InpMaxDailyLossPct,
                EaPositionsCount(), InpMaxPositions);
            Chart.DrawStaticText("OFBot_DB", txt, VerticalAlignment.Top, HorizontalAlignment.Left, Color.White);
        }

        // ===== Events =====
        protected override void OnTick()
        {
            UpdateDeltaCvd();

            if (IsNewBar())
            {
                OnNewBarBookkeeping();
                ManagePositions();

                var (score, dir) = ComputeEntryScore();
                DrawDashboard(score, dir);

                if (score >= InpEntryThreshold && dir != 0 && AllGuardsPass())
                    TryEnter(dir);
            }
        }

        void OnDepthUpdated() { /* hook for sweep / book-aware logic */ }

        void OnPositionsClosed(PositionClosedEventArgs args)
        {
            if (args.Position.Label == InpLabel) _lastTradeCloseTime = Server.Time;
        }
    }
}
