// ============================================================================
//  GODMODE UNIVERSAL CONTROLLER — full roster, all setups (cTrader / cAlgo)
// ----------------------------------------------------------------------------
//  ONE cBot that runs the ENTIRE validated D1 roster — every setup, every market,
//  long AND short — from one editable roster string. A portfolio of 60-120
//  validated edges aggregates to several trades/DAY while each individual edge
//  trades ~weekly. Every trade is OOS-validated; nothing is intraday/cost-eaten.
//
//  Setups: SPRING UPTHRUST SOS STACKBULL AMD LIQSWEEP ORB POORHL TSMOM RSI2
//  (delta setups SOS/STACKBULL/AMD/POORHL use signed tick-volume — meaningful on
//   futures/crypto/metals; on spot forex prefer SPRING/UPTHRUST/LIQSWEEP/ORB/TSMOM/RSI2.)
//
//  Roster slot:  SYMBOL:SETUP:stopATR:tpATR:trailATR   (slots separated by ;)
//  The default roster is the validated universe (auto-loaded from the scan).
//  EDIT symbols to your broker's names. Attach to ONE D1 chart; each slot pulls
//  its own symbol's D1 bars + indicators and trades independently, risk%-sized.
//  Truth = your broker's Strategy Tester, per symbol.
// ============================================================================
using System;
using System.Collections.Generic;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None, AddIndicators = true)]
    public class GODMODE_UniversalController : Robot
    {
        [Parameter("Roster", Group = "Roster", DefaultValue = "XAUUSD:AMD:3:1:0;XAGUSD:SPRING:0:0:0;XAUUSD:STACKBULL:3:1:0;DOGEUSD:STACKBULL:4:1.5:0;JP225:SOS:3:1:0;NATGAS:SPRING:3:1:0;NAS100:SOS:2:4:3;US500:SOS:3:1:0;US30:AMD:4:1.5:0;USOIL:AMD:2.5:0.8:0;XPTUSD:LIQSWEEP:2.5:0.8:0;XAGUSD:AMD:2.5:0.8:0;CHFJPY:SPRING:0:0:0;EURJPY:SPRING:0:0:0;US30:SPRING:4:1.5:0;SOLUSD:SOS:2:0:2.5;DOGEUSD:SOS:0:0:0;COPPER:STACKBULL:2.5:0.8:0;JP225:SPRING:0:0:0;US30:SOS:0:0:0;USDZAR:SPRING:0:0:0;EURCHF:UPTHRUST:3:1:0;AUDCHF:ORB:4:1.5:0;XAUUSD:SPRING:3:1:0;JP225:AMD:0:0:0;CADCHF:UPTHRUST:4:1.5:0;US500:RSI2:0:0:0;JP225:RSI2:0:0:0;NAS100:RSI2:0:0:0;XPTUSD:STACKBULL:3:1:0;JP225:STACKBULL:0:0:0;NATGAS:RSI2:3:1:0;NZDJPY:SPRING:1.5:3:2;GBPJPY:SPRING:0:0:0;GBPCHF:UPTHRUST:0:0:0;BNBUSD:SOS:0:0:0;DOGEUSD:ORB:0:0:0;XPTUSD:UPTHRUST:2.5:0.8:0;ETHUSD:STACKBULL:2:4:3;WHEAT:TSMOM:1.5:3:2;USDZAR:LIQSWEEP:2.5:0.8:0;US30:RSI2:0:0:0;USDSEK:TSMOM:2.5:0.8:0;UKOIL:SOS:2:4:3;ETHUSD:SOS:1.5:3:2;NAS100:TSMOM:0:0:0;XAGUSD:SOS:1.5:3:2;AUDCHF:TSMOM:2.5:0.8:0;NAS100:POORHL:3:6:0;GBPNZD:SPRING:1.5:3:2;LTCUSD:AMD:4:1.5:0;LINKUSD:STACKBULL:0:0:0;XRPUSD:SOS:0:0:0;USOIL:TSMOM:2:0:2.5;US500:SPRING:4:1.5:0;USDSGD:TSMOM:2:4:3;XRPUSD:STACKBULL:2.5:0.8:0;CHFJPY:TSMOM:2.5:0.8:0;NAS100:STACKBULL:3:6:0;NAS100:SPRING:4:1.5:0;SUGAR:SOS:1.5:3:2;AUDCHF:UPTHRUST:0:0:0;EURNZD:TSMOM:1.5:3:2;EURGBP:SPRING:0:0:0;JP225:ORB:3:1:0;BTCUSD:SOS:1:2:1.5;US2000:AMD:1:2:1.5;CHFJPY:ORB:3:1:0;ADAUSD:RSI2:4:1.5:0;EURJPY:ORB:1:2:1.5;BTCUSD:ORB:2.5:0.8:0;XAUUSD:POORHL:2:0:2.5;SOLUSD:ORB:0:0:0;CORN:ORB:2.5:0.8:0;NZDUSD:UPTHRUST:2.5:0.8:0;US500:ORB:2:4:3;EURJPY:TSMOM:3:6:0;COPPER:SOS:2:4:3;USDZAR:TSMOM:2.5:0.8:0;USOIL:SOS:2:0:2.5;EURNZD:LIQSWEEP:2:4:3;DOTUSD:ORB:2.5:0.8:0;DOTUSD:UPTHRUST:1:2:1.5;US30:POORHL:2:4:3;AUDUSD:LIQSWEEP:3:1:0;BNBUSD:ORB:0:0:0;US2000:RSI2:1.5:3:2;AVAXUSD:ORB:0:0:0;XAUUSD:SOS:2:4:3;AVAXUSD:POORHL:1.5:3:2;US30:STACKBULL:3:6:0;ETHUSD:ORB:3:1:0;US500:POORHL:2:0:2.5")]
        public string RosterStr { get; set; }

        [Parameter("Lookback (LB)", Group = "Common", DefaultValue = 20, MinValue = 5)] public int LB { get; set; }
        [Parameter("K", Group = "Common", DefaultValue = 1.0, MinValue = 0.0)] public double K { get; set; }
        [Parameter("Hold Bars", Group = "Common", DefaultValue = 10, MinValue = 1)] public int Hold { get; set; }
        [Parameter("Risk % / slot", Group = "Common", DefaultValue = 0.5, MinValue = 0.05)] public double RiskPct { get; set; }
        [Parameter("Sizing ATR (if no stop)", Group = "Common", DefaultValue = 3.0)] public double SizingATR { get; set; }
        [Parameter("ATR Period", Group = "Common", DefaultValue = 14)] public int AtrPeriod { get; set; }
        [Parameter("RSI2 Buy<", Group = "RSI2", DefaultValue = 10.0)] public double RsiBuy { get; set; }
        [Parameter("RSI2 Exit>", Group = "RSI2", DefaultValue = 60.0)] public double RsiExit { get; set; }

        private class Slot
        {
            public string Sym, Setup, Label;
            public double Stop, Tp, Trail;
            public Bars Bars; public Symbol Symbol;
            public AverageTrueRange Atr;
            public SimpleMovingAverage Sma50, Sma200;
            public RelativeStrengthIndex Rsi2;
            public int EntryBar = -1; public DateTime LastBar = DateTime.MinValue;
        }
        private readonly List<Slot> _slots = new List<Slot>();

        protected override void OnStart()
        {
            foreach (var raw in RosterStr.Split(';'))
            {
                var t = raw.Trim().Split(':');
                if (t.Length < 5) continue;
                var sym = Symbols.GetSymbol(t[0].Trim());
                if (sym == null) { Print("skip unknown symbol {0}", t[0]); continue; }
                var bars = MarketData.GetBars(TimeFrame.Daily, sym.Name);
                var setup = t[1].Trim().ToUpper();
                var s = new Slot
                {
                    Sym = t[0].Trim(), Setup = setup, Bars = bars, Symbol = sym,
                    Stop = double.Parse(t[2]), Tp = double.Parse(t[3]), Trail = double.Parse(t[4]),
                    Atr = Indicators.AverageTrueRange(bars, AtrPeriod, MovingAverageType.Simple),
                    Label = "GMU_" + setup + "_" + t[0].Trim()
                };
                if (setup == "ORB") s.Sma50 = Indicators.SimpleMovingAverage(bars.ClosePrices, 50);
                if (setup == "RSI2") { s.Sma200 = Indicators.SimpleMovingAverage(bars.ClosePrices, 200); s.Rsi2 = Indicators.RelativeStrengthIndex(bars.ClosePrices, 2); }
                _slots.Add(s);
            }
            Print("GODMODE Universal Controller — {0} slots loaded.", _slots.Count);
        }

        protected override void OnTick()
        {
            foreach (var s in _slots)
            {
                if (s.Bars.Count < LB + 6) continue;
                var bt = s.Bars.OpenTimes.Last(0);
                if (bt == s.LastBar) { Trail(s); continue; }
                s.LastBar = bt;
                Manage(s);
                var pos = Pos(s);
                int sig = Signal(s);
                if (pos == null) { if (sig != 0) Enter(s, sig); }
                else { int dir = pos.TradeType == TradeType.Buy ? 1 : -1; if (sig != 0 && sig != dir) { ClosePosition(pos); Enter(s, sig); } }
            }
        }

        // helpers on a slot's Bars
        private double LowC(Bars b, int f, int n) { double m = double.MaxValue; for (int i = f; i < f + n; i++) m = Math.Min(m, b.ClosePrices.Last(i)); return m; }
        private double HighC(Bars b, int f, int n) { double m = double.MinValue; for (int i = f; i < f + n; i++) m = Math.Max(m, b.ClosePrices.Last(i)); return m; }
        private double D(Bars b, int sh) { double sg = b.ClosePrices.Last(sh) >= b.OpenPrices.Last(sh) ? 1.0 : -1.0; return sg * b.TickVolumes.Last(sh); }
        private double MeanD(Bars b, int n) { double s = 0; for (int j = 1; j <= n; j++) s += D(b, j); return s / n; }

        private int Signal(Slot s)
        {
            var b = s.Bars; double a = s.Atr.Result.Last(1); if (a <= 0) return 0;
            double c1 = b.ClosePrices.Last(1), c2 = b.ClosePrices.Last(2), o1 = b.OpenPrices.Last(1);
            double h1 = b.HighPrices.Last(1), l1 = b.LowPrices.Last(1), h2 = b.HighPrices.Last(2), l2 = b.LowPrices.Last(2);
            double rng = h1 - l1; if (rng <= 0) rng = a;
            switch (s.Setup)
            {
                case "SPRING":    return (l1 < LowC(b, 2, LB) && c1 > LowC(b, 2, LB)) ? 1 : 0;
                case "UPTHRUST":  return (h1 > HighC(b, 2, LB) && c1 < HighC(b, 2, LB)) ? -1 : 0;
                case "SOS":       return (rng > K * a && c1 > o1 && D(b, 1) > 0 && c1 >= HighC(b, 2, LB)) ? 1 : 0;
                case "STACKBULL": return (D(b, 1) > 0 && D(b, 2) > 0 && D(b, 3) > 0 && D(b, 1) > K * Math.Abs(MeanD(b, LB))) ? 1 : 0;
                case "AMD":       return (l2 < LowC(b, 3, LB) && c1 > c2 && rng > K * a && D(b, 1) > 0) ? 1 : 0;
                case "LIQSWEEP":  if (l1 < LowC(b, 2, LB) && c1 > l1 + 0.5 * rng) return 1;
                                  if (h1 > HighC(b, 2, LB) && c1 < h1 - 0.5 * rng) return -1; return 0;
                case "ORB":       { double sma = s.Sma50.Result.Last(1), buf = K * a * 0.2;
                                    if (c1 > HighC(b, 2, LB) + buf && c1 > sma) return 1;
                                    if (c1 < LowC(b, 2, LB) - buf && c1 < sma) return -1; return 0; }
                case "POORHL":    if (Math.Abs(l1 - l2) < 0.25 * a && D(b, 1) > 0) return 1;
                                  if (Math.Abs(h1 - h2) < 0.25 * a && D(b, 1) < 0) return -1; return 0;
                case "TSMOM":     return c1 > b.ClosePrices.Last(LB + 1) ? 1 : (c1 < b.ClosePrices.Last(LB + 1) ? -1 : 0);
                case "RSI2":      return (s.Rsi2.Result.Last(1) < RsiBuy && c1 > s.Sma200.Result.Last(1)) ? 1 : 0;  // long-only
                default:          return 0;
            }
        }

        private Position Pos(Slot s) => Positions.FirstOrDefault(p => p.Label == s.Label);

        private void Enter(Slot s, int dir)
        {
            double a = s.Atr.Result.Last(1); if (a <= 0) return;
            double riskRef = (s.Stop > 0 ? s.Stop : SizingATR) * a;
            double vol = s.Symbol.NormalizeVolumeInUnits(Account.Equity * (RiskPct / 100.0) / riskRef, RoundingMode.Down);
            if (vol < s.Symbol.VolumeInUnitsMin) vol = s.Symbol.VolumeInUnitsMin;
            double? slPips = s.Stop > 0 ? (double?)(s.Stop * a / s.Symbol.PipSize) : null;
            double? tpPips = s.Tp > 0 ? (double?)(s.Tp * a / s.Symbol.PipSize) : null;
            var tt = dir > 0 ? TradeType.Buy : TradeType.Sell;
            var r = ExecuteMarketOrder(tt, s.Sym, vol, s.Label, slPips, tpPips);
            if (r.IsSuccessful) s.EntryBar = s.Bars.Count - 1;
        }

        private void Trail(Slot s)
        {
            var pos = Pos(s); if (pos == null || s.Trail <= 0) return;
            double a = s.Atr.Result.Last(1);
            if (pos.TradeType == TradeType.Buy) { double n = s.Symbol.Bid - s.Trail * a; if (!pos.StopLoss.HasValue || n > pos.StopLoss.Value) ModifyPosition(pos, n, pos.TakeProfit); }
            else { double n = s.Symbol.Ask + s.Trail * a; if (!pos.StopLoss.HasValue || n < pos.StopLoss.Value) ModifyPosition(pos, n, pos.TakeProfit); }
        }

        private void Manage(Slot s)
        {
            var pos = Pos(s);
            if (pos == null) { s.EntryBar = -1; return; }
            Trail(s);
            if (s.Setup == "RSI2") { if (s.Rsi2.Result.Last(1) > RsiExit) ClosePosition(pos); return; }  // RSI exit
            if (s.EntryBar >= 0 && (s.Bars.Count - 1 - s.EntryBar) >= Hold) ClosePosition(pos);            // time exit
        }
    }
}
