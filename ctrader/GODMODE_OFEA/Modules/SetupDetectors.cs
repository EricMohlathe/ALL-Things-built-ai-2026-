// SetupDetectors.cs
// All 25 setup detectors (brief §6) — mirrors OF_SetupDetectors.mqh.

using System;
using cAlgo.API;
using cAlgo.API.Internals;

namespace GodmodeOfea
{
    public static class SetupDetectors
    {
        public static SetupCandidate Build(Symbol sym, Bars bars, SetupId id, TradeDir dir,
            double poc, double targetLevel, VpLoc loc, int absStars, string reason)
        {
            double bid = sym.Bid, ask = sym.Ask;
            double pt  = sym.TickSize;
            double aggH = bars.HighPrices.Last(1), aggL = bars.LowPrices.Last(1);
            var c = new SetupCandidate { SetupId = id, Direction = dir, AbsStars = absStars, Loc = loc, Reason = reason };
            if (dir == TradeDir.Long)  { c.Entry = ask; c.Sl = aggL - 2 * pt; c.Tp = targetLevel > 0 ? targetLevel : poc; }
            else                        { c.Entry = bid; c.Sl = aggH + 2 * pt; c.Tp = targetLevel > 0 ? targetLevel : poc; }
            return c;
        }

        public static SetupCandidate? AbsBot(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp,
            FootprintAnalyzer fp, double locTolPips, int minStars)
        {
            double c = b.ClosePrices.Last(1);
            var loc = vp.LocationAt(c, locTolPips);
            if (loc != VpLoc.Val && loc != VpLoc.Lvn) return null;
            if (!fp.BullishAbsorption(de)) return null;
            int stars = AbsorptionStars.Compute(b, de, TradeDir.Long);
            if (stars < minStars) return null;
            return Build(s, b, SetupId.AbsBot, TradeDir.Long, vp.Poc, vp.Poc, loc, stars, "AbsBot@VAL/LVN");
        }

        public static SetupCandidate? AbsTop(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp,
            FootprintAnalyzer fp, double locTolPips, int minStars)
        {
            double c = b.ClosePrices.Last(1);
            var loc = vp.LocationAt(c, locTolPips);
            if (loc != VpLoc.Vah && loc != VpLoc.Hvn) return null;
            if (!fp.BearishAbsorption(de)) return null;
            int stars = AbsorptionStars.Compute(b, de, TradeDir.Short);
            if (stars < minStars) return null;
            return Build(s, b, SetupId.AbsTop, TradeDir.Short, vp.Poc, vp.Poc, loc, stars, "AbsTop@VAH/HVN");
        }

        public static SetupCandidate? CvdBear(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double locTolPips)
        {
            if (!de.BearishDivergence()) return null;
            double c = b.ClosePrices.Last(1);
            return Build(s, b, SetupId.CvdBear, TradeDir.Short, vp.Poc, vp.Poc, vp.LocationAt(c, locTolPips), 0, "CVD bear div");
        }
        public static SetupCandidate? CvdBull(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double locTolPips)
        {
            if (!de.BullishDivergence()) return null;
            double c = b.ClosePrices.Last(1);
            return Build(s, b, SetupId.CvdBull, TradeDir.Long, vp.Poc, vp.Poc, vp.LocationAt(c, locTolPips), 0, "CVD bull div");
        }

        public static SetupCandidate? ValBounce(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double locTolPips)
        {
            double c = b.ClosePrices.Last(1), o = b.OpenPrices.Last(1);
            if (vp.LocationAt(c, locTolPips) != VpLoc.Val) return null;
            if (c <= o || de.BarDelta < 0) return null;
            return Build(s, b, SetupId.ValBnc, TradeDir.Long, vp.Poc, vp.Poc, VpLoc.Val, 0, "VAL bounce");
        }
        public static SetupCandidate? VahFade(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double locTolPips)
        {
            double c = b.ClosePrices.Last(1), o = b.OpenPrices.Last(1);
            if (vp.LocationAt(c, locTolPips) != VpLoc.Vah) return null;
            if (c >= o || de.BarDelta > 0) return null;
            return Build(s, b, SetupId.VahFade, TradeDir.Short, vp.Poc, vp.Poc, VpLoc.Vah, 0, "VAH fade");
        }
        public static SetupCandidate? PocReturn(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double locTolPips)
        {
            double c = b.ClosePrices.Last(1);
            if (vp.LocationAt(c, locTolPips) != VpLoc.Poc) return null;
            var dir = de.BarDelta >= 0 ? TradeDir.Long : TradeDir.Short;
            double tp = dir == TradeDir.Long ? vp.Vah : vp.Val;
            return Build(s, b, SetupId.PocRet, dir, vp.Poc, tp, VpLoc.Poc, 0, "POC return");
        }
        public static SetupCandidate? LvnLong(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double locTolPips)
        {
            double c = b.ClosePrices.Last(1);
            if (vp.LocationAt(c, locTolPips) != VpLoc.Lvn) return null;
            if (de.BarDelta <= 0 || de.VolumeZ() < 1.0) return null;
            return Build(s, b, SetupId.LvnLong, TradeDir.Long, vp.Poc, vp.Vah, VpLoc.Lvn, 0, "LVN accel L");
        }
        public static SetupCandidate? LvnShort(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double locTolPips)
        {
            double c = b.ClosePrices.Last(1);
            if (vp.LocationAt(c, locTolPips) != VpLoc.Lvn) return null;
            if (de.BarDelta >= 0 || de.VolumeZ() < 1.0) return null;
            return Build(s, b, SetupId.LvnShort, TradeDir.Short, vp.Poc, vp.Val, VpLoc.Lvn, 0, "LVN accel S");
        }
        public static SetupCandidate? HvnRej(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double locTolPips)
        {
            double c = b.ClosePrices.Last(1);
            if (vp.LocationAt(c, locTolPips) != VpLoc.Hvn) return null;
            var dir = de.BarDelta < 0 ? TradeDir.Short : TradeDir.Long;
            return Build(s, b, SetupId.HvnRej, dir, vp.Poc, vp.Poc, VpLoc.Hvn, 0, "HVN rej");
        }
        public static SetupCandidate? StackBull(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp,
            FootprintAnalyzer fp, double locTolPips)
        {
            if (!fp.StackedBullImbalance(de) || de.CvdSlope5() <= 0) return null;
            double c = b.ClosePrices.Last(1);
            return Build(s, b, SetupId.StackBull, TradeDir.Long, vp.Poc, vp.Vah, vp.LocationAt(c, locTolPips), 0, "Stack bull+CVD");
        }
        public static SetupCandidate? StackBear(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp,
            FootprintAnalyzer fp, double locTolPips)
        {
            if (!fp.StackedBearImbalance(de) || de.CvdSlope5() >= 0) return null;
            double c = b.ClosePrices.Last(1);
            return Build(s, b, SetupId.StackBear, TradeDir.Short, vp.Poc, vp.Val, vp.LocationAt(c, locTolPips), 0, "Stack bear+CVD");
        }
        public static SetupCandidate? PullStack(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double locTolPips)
        {
            double zone = 0; var dir = TradeDir.None;
            for (int i = 1; i < 10; i++)
            {
                bool bull = de.Delta(i) > 0 && de.Delta(i + 1) > 0 && de.Delta(i + 2) > 0;
                bool bear = de.Delta(i) < 0 && de.Delta(i + 1) < 0 && de.Delta(i + 2) < 0;
                if (bull) { zone = b.LowPrices.Last(i); dir = TradeDir.Long; break; }
                if (bear) { zone = b.HighPrices.Last(i); dir = TradeDir.Short; break; }
            }
            if (dir == TradeDir.None) return null;
            double c = b.ClosePrices.Last(1);
            double pip = OFHelpers.PipSize(s);
            if (Math.Abs(c - zone) > 5 * pip) return null;
            return Build(s, b, SetupId.PullStack, dir, vp.Poc, vp.Poc, vp.LocationAt(c, locTolPips), 0, "Pull stack");
        }
        public static SetupCandidate? Spring(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double locTolPips)
        {
            double swingLow = b.LowPrices.Last(5);
            for (int i = 6; i < 30; i++) swingLow = Math.Min(swingLow, b.LowPrices.Last(i));
            double curL = b.LowPrices.Last(1), curC = b.ClosePrices.Last(1);
            if (curL > swingLow || curC <= swingLow || !de.BullishDivergence()) return null;
            return Build(s, b, SetupId.Spring, TradeDir.Long, vp.Poc, vp.Poc, vp.LocationAt(curC, locTolPips), 0, "Spring");
        }
        public static SetupCandidate? Upthrust(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double locTolPips)
        {
            double swingHigh = b.HighPrices.Last(5);
            for (int i = 6; i < 30; i++) swingHigh = Math.Max(swingHigh, b.HighPrices.Last(i));
            double curH = b.HighPrices.Last(1), curC = b.ClosePrices.Last(1);
            if (curH < swingHigh || curC >= swingHigh || !de.BearishDivergence()) return null;
            return Build(s, b, SetupId.Upthrust, TradeDir.Short, vp.Poc, vp.Poc, vp.LocationAt(curC, locTolPips), 0, "Upthrust");
        }
        public static SetupCandidate? Sos(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double locTolPips)
        {
            if (de.CvdSlope5() <= 0 || de.VolumeZ() < 1.0) return null;
            double c = b.ClosePrices.Last(1);
            return Build(s, b, SetupId.Sos, TradeDir.Long, vp.Poc, vp.Vah, vp.LocationAt(c, locTolPips), 0, "SOS");
        }
        public static SetupCandidate? Lpsy(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double locTolPips)
        {
            if (de.CvdSlope5() >= 0 || de.VolumeZ() < 1.0) return null;
            double c = b.ClosePrices.Last(1);
            return Build(s, b, SetupId.Lpsy, TradeDir.Short, vp.Poc, vp.Val, vp.LocationAt(c, locTolPips), 0, "LPSY");
        }
        public static SetupCandidate? LiqSweep(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double locTolPips)
        {
            double sH = b.HighPrices.Last(3), sL = b.LowPrices.Last(3);
            for (int i = 4; i < 50; i++) {
                sH = Math.Max(sH, b.HighPrices.Last(i));
                sL = Math.Min(sL, b.LowPrices.Last(i));
            }
            double cH = b.HighPrices.Last(1), cL = b.LowPrices.Last(1), cC = b.ClosePrices.Last(1);
            TradeDir dir = TradeDir.None;
            if (cH > sH && cC < sH) dir = TradeDir.Short;
            if (cL < sL && cC > sL) dir = TradeDir.Long;
            if (dir == TradeDir.None) return null;
            return Build(s, b, SetupId.LiqSweep, dir, vp.Poc, vp.Poc, vp.LocationAt(cC, locTolPips), 0, "Liq sweep");
        }
        public static SetupCandidate? ObReturn(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double locTolPips)
        {
            for (int i = 5; i < 30; i++) {
                double oo = b.OpenPrices.Last(i), oc = b.ClosePrices.Last(i);
                double cur = b.ClosePrices.Last(1), pip = OFHelpers.PipSize(s);
                if (oc < oo && Math.Abs(cur - b.HighPrices.Last(i)) < 5 * pip && de.CvdSlope5() < 0)
                    return Build(s, b, SetupId.ObReturn, TradeDir.Short, vp.Poc, vp.Val, vp.LocationAt(cur, locTolPips), 0, "OB return short");
                if (oc > oo && Math.Abs(cur - b.LowPrices.Last(i)) < 5 * pip && de.CvdSlope5() > 0)
                    return Build(s, b, SetupId.ObReturn, TradeDir.Long, vp.Poc, vp.Vah, vp.LocationAt(cur, locTolPips), 0, "OB return long");
            }
            return null;
        }
        public static SetupCandidate? SmtDiv(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double corrCvdSlope, double locTolPips)
        {
            // Requires a *real* correlated CVD slope to compare against — when
            // the caller passes 0 (M5_UseCorrelatedCVD disabled) we must abstain,
            // otherwise mySlope * 0 == 0 lets the gate fall through silently.
            if (corrCvdSlope == 0.0) return null;
            double mySlope = de.CvdSlope5();
            if (mySlope * corrCvdSlope >= 0) return null;
            double c = b.ClosePrices.Last(1);
            var dir = mySlope > 0 ? TradeDir.Long : TradeDir.Short;
            return Build(s, b, SetupId.SmtDiv, dir, vp.Poc, vp.Poc, vp.LocationAt(c, locTolPips), 0, "SMT div");
        }
        public static SetupCandidate? Breaker(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double locTolPips)
        {
            double sH = b.HighPrices.Last(5), sL = b.LowPrices.Last(5);
            for (int i = 6; i < 40; i++) { sH = Math.Max(sH, b.HighPrices.Last(i)); sL = Math.Min(sL, b.LowPrices.Last(i)); }
            double curC = b.ClosePrices.Last(1), pip = OFHelpers.PipSize(s);
            if (curC > sH && Math.Abs(curC - sH) < 5 * pip && de.CvdSlope5() > 0)
                return Build(s, b, SetupId.Breaker, TradeDir.Long, vp.Poc, vp.Vah, vp.LocationAt(curC, locTolPips), 0, "Breaker L");
            if (curC < sL && Math.Abs(curC - sL) < 5 * pip && de.CvdSlope5() < 0)
                return Build(s, b, SetupId.Breaker, TradeDir.Short, vp.Poc, vp.Val, vp.LocationAt(curC, locTolPips), 0, "Breaker S");
            return null;
        }
        public static SetupCandidate? Amd(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double locTolPips)
        {
            double rh = b.HighPrices.Last(5), rl = b.LowPrices.Last(5);
            for (int i = 6; i < 24; i++) { rh = Math.Max(rh, b.HighPrices.Last(i)); rl = Math.Min(rl, b.LowPrices.Last(i)); }
            double curC = b.ClosePrices.Last(1);
            if (curC > rh && de.DeltaZ() > 1.5)
                return Build(s, b, SetupId.Amd, TradeDir.Long, vp.Poc, vp.Vah, vp.LocationAt(curC, locTolPips), 0, "AMD long");
            if (curC < rl && de.DeltaZ() < -1.5)
                return Build(s, b, SetupId.Amd, TradeDir.Short, vp.Poc, vp.Val, vp.LocationAt(curC, locTolPips), 0, "AMD short");
            return null;
        }
        public static SetupCandidate? UnfAuc(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp,
            FootprintAnalyzer fp, cAlgo.API.Indicators.AverageTrueRange atrInd, double locTolPips)
        {
            if (!fp.UnfinishedAuction(atrInd.Result)) return null;
            double curH = b.HighPrices.Last(1), prevH = b.HighPrices.Last(2);
            double curC = b.ClosePrices.Last(1);
            var dir = curH > prevH ? TradeDir.Short : TradeDir.Long;
            return Build(s, b, SetupId.UnfAuc, dir, vp.Poc, vp.Poc, vp.LocationAt(curC, locTolPips), 0, "Unfinished auc");
        }
        public static SetupCandidate? PoorHL(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp, double locTolPips)
        {
            double prevH = b.HighPrices.Last(2), prevL = b.LowPrices.Last(2);
            double curH = b.HighPrices.Last(1), curL = b.LowPrices.Last(1), curC = b.ClosePrices.Last(1);
            double pip = OFHelpers.PipSize(s);
            if (Math.Abs(curH - prevH) < pip && de.BarDelta < 0)
                return Build(s, b, SetupId.PoorHL, TradeDir.Short, vp.Poc, vp.Poc, vp.LocationAt(curC, locTolPips), 0, "Poor high");
            if (Math.Abs(curL - prevL) < pip && de.BarDelta > 0)
                return Build(s, b, SetupId.PoorHL, TradeDir.Long, vp.Poc, vp.Poc, vp.LocationAt(curC, locTolPips), 0, "Poor low");
            return null;
        }
        public static SetupCandidate? Iceberg(Symbol s, Bars b, DeltaEngine de, VolumeProfile vp,
            cAlgo.API.Indicators.AverageTrueRange atrInd, double locTolPips)
        {
            double volZ = de.VolumeZ(), dz = de.DeltaZ();
            double atr = atrInd.Result.Last(0);
            double range = b.HighPrices.Last(1) - b.LowPrices.Last(1);
            if (volZ < 2.0 || Math.Abs(dz) > 0.5 || atr <= 0 || range > 0.6 * atr) return null;
            double curC = b.ClosePrices.Last(1);
            var loc = vp.LocationAt(curC, locTolPips);
            // Only fire iceberg at a defendable level; POC / unknown were
            // previously bucketed into SHORT by the catch-all `else`.
            TradeDir dir;
            if (loc == VpLoc.Val || loc == VpLoc.Lvn) dir = TradeDir.Long;
            else if (loc == VpLoc.Vah || loc == VpLoc.Hvn) dir = TradeDir.Short;
            else return null;
            return Build(s, b, SetupId.Iceberg, dir, vp.Poc, vp.Poc, loc, 0, "Iceberg");
        }
    }
}
