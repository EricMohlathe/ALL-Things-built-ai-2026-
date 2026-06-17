// ============================================================================
//  GODMODE DEITY CONTROLLER — multi-market, multi-setup (cTrader / cAlgo)
// ----------------------------------------------------------------------------
//  ONE cBot that runs all 4 validated D1 setups across all their validated
//  markets at once, from an editable roster. The honest way to get MORE trades:
//  ~20-30 real trades/year aggregate, every one from a validated edge — instead
//  of ~1000 cost-losing intraday trades.
//
//  Setups (long-only, all validated on Daily — see GODMODE_DEITY_EAs/README):
//    SPRING    = GM14 Wyckoff spring / liquidity sweep reclaim
//    STACKBULL = GM11 footprint buy-delta stack
//    SOS       = GM16 Wyckoff sign-of-strength expansion
//    AMD       = GM22 ICT accumulation-manipulation-distribution
//
//  Roster format (one slot per ; ) :  SYMBOL:SETUP:stopATR:tpATR:trailATR
//  Default roster = the validated winners. EDIT SYMBOLS to match your broker
//  (XAGUSD/XAUUSD/NAS100/US500/US30 are common names — yours may differ).
//
//  Attach to ONE Daily (D1) chart of ANY symbol. The bot pulls each roster
//  symbol's own D1 bars and trades them independently. Risk% sized per slot.
//  Truth = your broker's Strategy Tester per symbol.
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
    public class GODMODE_DeityController : Robot
    {
        // Default roster = 14 D1 winners validated across metals + indices (PF>=1.5, trd>=30,
        // net-positive full-period AND out-of-sample). EDIT symbols to your broker's names.
        [Parameter("Roster", Group = "Roster", DefaultValue =
            "XAGUSD:SPRING:0:0:0;XAUUSD:AMD:3:1:0;XAUUSD:STACKBULL:3:1:0;XAUUSD:SPRING:3:1:0;XAGUSD:AMD:2.5:0.8:0;XAGUSD:SOS:1.5:3:2;NAS100:SOS:2:4:3;US500:SOS:3:1:0;US30:AMD:4:1.5:0;US30:SPRING:4:1.5:0;US30:SOS:0:0:0;NAS100:STACKBULL:3:6:0;US500:SPRING:4:1.5:0;NAS100:SPRING:4:1.5:0")]
        public string RosterStr { get; set; }

        [Parameter("Lookback (LB)", Group = "Common", DefaultValue = 20, MinValue = 5)] public int LB { get; set; }
        [Parameter("K", Group = "Common", DefaultValue = 1.0, MinValue = 0.0)] public double K { get; set; }
        [Parameter("Hold Bars", Group = "Common", DefaultValue = 10, MinValue = 1)] public int Hold { get; set; }
        [Parameter("Risk % / slot", Group = "Common", DefaultValue = 1.0, MinValue = 0.05)] public double RiskPct { get; set; }
        [Parameter("Sizing ATR (if no stop)", Group = "Common", DefaultValue = 3.0)] public double SizingATR { get; set; }
        [Parameter("ATR Period", Group = "Common", DefaultValue = 14)] public int AtrPeriod { get; set; }

        private class Slot
        {
            public string Sym, Setup, Label;
            public double Stop, Tp, Trail;
            public Bars Bars;
            public AverageTrueRange Atr;
            public Symbol Symbol;
            public int EntryBar = -1;
            public DateTime LastBar = DateTime.MinValue;
        }
        private readonly List<Slot> _slots = new List<Slot>();

        protected override void OnStart()
        {
            foreach (var raw in RosterStr.Split(';'))
            {
                var t = raw.Trim().Split(':');
                if (t.Length < 5) continue;
                var sym = Symbols.GetSymbol(t[0].Trim());
                if (sym == null) { Print("Roster: unknown symbol {0} — skipped", t[0]); continue; }
                var bars = MarketData.GetBars(TimeFrame.Daily, sym.Name);
                var slot = new Slot
                {
                    Sym = t[0].Trim(), Setup = t[1].Trim().ToUpper(),
                    Stop = double.Parse(t[2]), Tp = double.Parse(t[3]), Trail = double.Parse(t[4]),
                    Bars = bars, Symbol = sym,
                    Atr = Indicators.AverageTrueRange(bars, AtrPeriod, MovingAverageType.Simple),
                    Label = "GMD_" + t[1].Trim().ToUpper() + "_" + t[0].Trim()
                };
                _slots.Add(slot);
                Print("Slot: {0} {1} stop{2}/tp{3}/trail{4}", slot.Sym, slot.Setup, slot.Stop, slot.Tp, slot.Trail);
            }
            Print("GODMODE Deity Controller started — {0} slots.", _slots.Count);
        }

        protected override void OnTick()
        {
            foreach (var s in _slots)
            {
                if (s.Bars.Count < LB + 6) continue;
                var bt = s.Bars.OpenTimes.Last(0);
                if (bt == s.LastBar) { Trail(s); continue; }  // same bar — just trail
                s.LastBar = bt;
                Manage(s);
                if (Position(s) != null) continue;
                if (Signal(s) == 1) Enter(s);
            }
        }

        // ---- per-symbol helpers ----
        private double LowC(Bars b, int from, int n) { double m = double.MaxValue; for (int i = from; i < from + n; i++) m = Math.Min(m, b.ClosePrices.Last(i)); return m; }
        private double HighC(Bars b, int from, int n) { double m = double.MinValue; for (int i = from; i < from + n; i++) m = Math.Max(m, b.ClosePrices.Last(i)); return m; }
        private double D(Bars b, int sh) { double sign = b.ClosePrices.Last(sh) >= b.OpenPrices.Last(sh) ? 1.0 : -1.0; return sign * b.TickVolumes.Last(sh); }
        private double MeanD(Bars b, int n) { double s = 0; for (int j = 1; j <= n; j++) s += D(b, j); return s / n; }

        private int Signal(Slot s)
        {
            var b = s.Bars; double a = s.Atr.Result.Last(1); if (a <= 0) return 0;
            double c1 = b.ClosePrices.Last(1), o1 = b.OpenPrices.Last(1), h1 = b.HighPrices.Last(1), l1 = b.LowPrices.Last(1);
            double rng = h1 - l1;
            switch (s.Setup)
            {
                case "SPRING":    return (l1 < LowC(b, 2, LB) && c1 > LowC(b, 2, LB)) ? 1 : 0;
                case "STACKBULL": return (D(b, 1) > 0 && D(b, 2) > 0 && D(b, 3) > 0 && D(b, 1) > K * Math.Abs(MeanD(b, LB))) ? 1 : 0;
                case "SOS":       return (rng > K * a && c1 > o1 && D(b, 1) > 0 && c1 >= HighC(b, 2, LB)) ? 1 : 0;
                case "AMD":       return (b.LowPrices.Last(2) < LowC(b, 3, LB) && c1 > b.ClosePrices.Last(2) && rng > K * a && D(b, 1) > 0) ? 1 : 0;
                default:          return 0;
            }
        }

        private Position Position(Slot s) => Positions.FirstOrDefault(p => p.Label == s.Label);

        private void Enter(Slot s)
        {
            double a = s.Atr.Result.Last(1); if (a <= 0) return;
            double riskRef = (s.Stop > 0 ? s.Stop : SizingATR) * a;
            double vol = s.Symbol.NormalizeVolumeInUnits(Account.Equity * (RiskPct / 100.0) / riskRef, RoundingMode.Down);
            if (vol < s.Symbol.VolumeInUnitsMin) vol = s.Symbol.VolumeInUnitsMin;
            double? slPips = s.Stop > 0 ? (double?)(s.Stop * a / s.Symbol.PipSize) : null;
            double? tpPips = s.Tp > 0 ? (double?)(s.Tp * a / s.Symbol.PipSize) : null;
            var r = ExecuteMarketOrder(TradeType.Buy, s.Sym, vol, s.Label, slPips, tpPips);
            if (r.IsSuccessful) s.EntryBar = s.Bars.Count - 1;
        }

        private void Trail(Slot s)
        {
            var pos = Position(s); if (pos == null || s.Trail <= 0) return;
            double a = s.Atr.Result.Last(1);
            double nsl = s.Symbol.Bid - s.Trail * a;
            if (!pos.StopLoss.HasValue || nsl > pos.StopLoss.Value) ModifyPosition(pos, nsl, pos.TakeProfit);
        }

        private void Manage(Slot s)
        {
            var pos = Position(s);
            if (pos == null) { s.EntryBar = -1; return; }
            Trail(s);
            if (s.EntryBar >= 0 && (s.Bars.Count - 1 - s.EntryBar) >= Hold) ClosePosition(pos);
        }
    }
}
