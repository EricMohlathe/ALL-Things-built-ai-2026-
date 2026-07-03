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
        [Parameter("Roster", Group = "Roster", DefaultValue = "XAUUSD:AMD:3:1:0;XAGUSD:SPRING:0:0:0;XAUUSD:STACKBULL:4:1.5:0:200;XAGUSD:AMD:0:0:0:200;XAUUSD:SPRING:3:1:0:100;XAGUSD:SOS:1.5:3:2:100;INTC:SPRING:3:1:0;INTC:AMD:3:1:0;CA60:STACKBULL:3:1:0;CA60:AMD:2.5:0.8:0;CA60:RSI2:3:6:0;APTUSD:UPTHRUST:4:1.5:0;V:RSI2:0:0:0;V:SPRING:4:1.5:0;V:AMD:2.5:0.8:0;V:TSMOM:2.5:0.8:0;DIS:TSMOM:3:6:0;DIS:SOS:2:0:2.5;MSFT:RSI2:3:1:0;JP225:SOS:3:1:0;NVDA:RSI2:0:0:0;NAS100:SOS:2:4:3:50;US500:SOS:3:1:0:200;NVDA:SOS:4:1.5:0;WMT:SPRING:2.5:0.8:0;WMT:LIQSWEEP:3:6:0;WMT:STACKBULL:0:0:0;WMT:RSI2:0:0:0;RUNEUSD:STACKBULL:3:1:0;AAVEUSD:RSI2:0:0:0;AAVEUSD:LIQSWEEP:2.5:0.8:0;LINKUSD:STACKBULL:0:0:0;DOGEUSD:STACKBULL:4:1.5:0;DOGEUSD:SOS:0:0:0;DOGEUSD:ORB:0:0:0;ETHUSD:STACKBULL:2:4:3;ETHUSD:SOS:1.5:3:2;BTCUSD:SOS:1:2:1.5;JPM:STACKBULL:3:1:0;US30:AMD:0:0:0:200;US30:SPRING:4:1.5:0;US30:SOS:0:0:0;JPM:LIQSWEEP:3:6:0;JPM:SOS:1:2:1.5;NATGAS:SPRING:3:1:0;NATGAS:RSI2:3:1:0;JP225:AMD:0:0:0;USOIL:AMD:2.5:0.8:0;UKOIL:SOS:2:4:3;USOIL:TSMOM:2:0:2.5;XPTUSD:LIQSWEEP:2.5:0.8:0;XPTUSD:STACKBULL:3:1:0;XPTUSD:UPTHRUST:2.5:0.8:0;FTMUSD:RSI2:3:6:0;FTMUSD:SOS:3:6:0;TSLA:SOS:0:0:0;TSLA:RSI2:0:0:0;CHFJPY:SPRING:0:0:0;EURJPY:SPRING:3:1:0:50;CHFJPY:TSMOM:2.5:0.8:0;AUS200:AMD:2:0:2.5;AUS200:STACKBULL:3:1:0;AUS200:SPRING:2:0:2.5;SOLUSD:SOS:2:0:2.5;MCD:TSMOM:3:6:0;MCD:AMD:1:2:1.5;COPPER:STACKBULL:2.5:0.8:0;ESP35:SPRING:4:1.5:0;DE40:SPRING:0:0:0;ESP35:SOS:1.5:3:2;DE40:AMD:3:1:0;DE40:RSI2:3:1:0;DE40:TSMOM:3:1:0;USDZAR:SPRING:0:0:0;USDZAR:LIQSWEEP:2.5:0.8:0;EURCHF:UPTHRUST:3:1:0;BA:TSMOM:3:6:0;BA:AMD:1.5:3:2;BA:SOS:3:6:0;BA:SPRING:4:1.5:0;AUDCHF:ORB:4:1.5:0;AUDCHF:TSMOM:2.5:0.8:0;AUDCHF:UPTHRUST:0:0:0;AXSUSD:SOS:0:0:0;ATOMUSD:SOS:3:1:0;CAT:STACKBULL:1.5:3:2;CAT:SPRING:0:0:0;CAT:ORB:4:1.5:0;CAT:SOS:4:1.5:0;COST:AMD:3:1:0;COST:SOS:1:2:1.5;COST:POORHL:2:4:3;COST:SPRING:3:6:0;NEARUSD:SOS:1:2:1.5;NEARUSD:ORB:3:1:0;FILUSD:SOS:2.5:0.8:0;FILUSD:TSMOM:2:0:2.5;FILUSD:UPTHRUST:4:1.5:0;AMD:AMD:3:1:0;AMD:RSI2:0:0:0;AMD:SPRING:0:0:0;CADCHF:UPTHRUST:4:1.5:0;CSCO:SOS:0:0:0;CSCO:SPRING:1:2:1.5;NFLX:AMD:0:0:0;META:SOS:4:1.5:0;PFE:POORHL:3:6:0;NZDJPY:SPRING:1.5:3:2;GBPJPY:SPRING:0:0:0;GBPCHF:UPTHRUST:0:0:0;HD:STACKBULL:2.5:0.8:0;HD:AMD:4:1.5:0;BNBUSD:SOS:0:0:0;WHEAT:TSMOM:1.5:3:2;USDSEK:TSMOM:2.5:0.8:0;USDSGD:TSMOM:2:4:3;SUI20:TSMOM:3:6:0;SUI20:SPRING:0:0:0;CVX:AMD:3:6:0;CVX:SPRING:2.5:0.8:0;XOM:STACKBULL:1.5:3:2;GBPNZD:SPRING:1.5:3:2;LTCUSD:AMD:4:1.5:0;OPUSD:TSMOM:2:0:2.5;XRPUSD:SOS:0:0:0;XRPUSD:STACKBULL:2.5:0.8:0;GRTUSD:UPTHRUST:2.5:0.8:0;INJUSD:RSI2:2:4:3;ORCL:STACKBULL:0:0:0;SOYBEAN:SOS:0:0:0;HK50:LIQSWEEP:2:0:2.5;SUGAR:SOS:1.5:3:2;EURNZD:TSMOM:1.5:3:2;EURGBP:SPRING:0:0:0;KO:LIQSWEEP:2:4:3")]
        public string RosterStr { get; set; }

        [Parameter("Lookback (LB)", Group = "Common", DefaultValue = 20, MinValue = 5)] public int LB { get; set; }
        [Parameter("K", Group = "Common", DefaultValue = 1.0, MinValue = 0.0)] public double K { get; set; }
        [Parameter("Hold Bars", Group = "Common", DefaultValue = 10, MinValue = 1)] public int Hold { get; set; }
        [Parameter("Risk % / slot", Group = "Common", DefaultValue = 0.5, MinValue = 0.05)] public double RiskPct { get; set; }
        [Parameter("Sizing ATR (if no stop)", Group = "Common", DefaultValue = 3.0)] public double SizingATR { get; set; }
        [Parameter("ATR Period", Group = "Common", DefaultValue = 14)] public int AtrPeriod { get; set; }
        [Parameter("RSI2 Buy<", Group = "RSI2", DefaultValue = 10.0)] public double RsiBuy { get; set; }
        [Parameter("RSI2 Exit>", Group = "RSI2", DefaultValue = 60.0)] public double RsiExit { get; set; }
        [Parameter("Max Open Positions", Group = "Portfolio Risk", DefaultValue = 30, MinValue = 1)] public int MaxOpen { get; set; }
        [Parameter("Max Per Symbol", Group = "Portfolio Risk", DefaultValue = 2, MinValue = 1)] public int MaxPerSym { get; set; }
        [Parameter("Daily Loss Halt %", Group = "Portfolio Risk", DefaultValue = 4.0, MinValue = 0.0)] public double DailyHalt { get; set; }

        private DateTime _day; private double _dayEq; private bool _halted;

        private class Slot
        {
            public string Sym, Setup, Label;
            public double Stop, Tp, Trail;
            public Bars Bars; public Symbol Symbol;
            public AverageTrueRange Atr;
            public SimpleMovingAverage Sma50, Sma200, TrendMA;
            public RelativeStrengthIndex Rsi2;
            public int TrendN = 0;
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
                if (t.Length >= 6) { int.TryParse(t[5].Trim(), out s.TrendN); if (s.TrendN > 0) s.TrendMA = Indicators.SimpleMovingAverage(bars.ClosePrices, s.TrendN); }
                _slots.Add(s);
            }
            Print("GODMODE Universal Controller — {0} slots loaded.", _slots.Count);
        }

        private int OpenN() => Positions.Count(p => p.Label != null && p.Label.StartsWith("GMU_"));
        private int SymN(string sym) => Positions.Count(p => p.Label != null && p.Label.StartsWith("GMU_") && p.SymbolName == sym);
        private bool CanEnter(Slot s) => !_halted && OpenN() < MaxOpen && SymN(s.Sym) < MaxPerSym;

        protected override void OnTick()
        {
            var today = Server.Time.Date;
            if (today != _day) { _day = today; _dayEq = Account.Equity; }
            _halted = DailyHalt > 0 && _dayEq > 0 && Account.Equity <= _dayEq * (1 - DailyHalt / 100.0);

            foreach (var s in _slots)
            {
                if (s.Bars.Count < LB + 6) continue;
                var bt = s.Bars.OpenTimes.Last(0);
                if (bt == s.LastBar) { Trail(s); continue; }
                s.LastBar = bt;
                Manage(s);
                var pos = Pos(s);
                int sig = TrendGate(s, Signal(s));
                if (pos == null) { if (sig != 0 && CanEnter(s)) Enter(s, sig); }
                else { int dir = pos.TradeType == TradeType.Buy ? 1 : -1; if (sig != 0 && sig != dir) { ClosePosition(pos); if (CanEnter(s)) Enter(s, sig); } }
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

        private int TrendGate(Slot s, int sig)
        {
            if (sig == 0 || s.TrendMA == null) return sig;
            double c = s.Bars.ClosePrices.Last(1), m = s.TrendMA.Result.Last(1);
            if (sig > 0 && c <= m) return 0;
            if (sig < 0 && c >= m) return 0;
            return sig;
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
