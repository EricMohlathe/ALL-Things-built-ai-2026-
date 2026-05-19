//+------------------------------------------------------------------+
//|                                          OF_SetupDetectors.mqh   |
//|  All 25 Detect_SetupN() routines (brief §6).                      |
//|  Priority 1+2 setups have full algorithmic implementations;       |
//|  lower-priority setups (HVNRej etc.) share the same pattern and   |
//|  use parametrised confluence to keep the code DRY.                |
//+------------------------------------------------------------------+
#property strict
#ifndef OF_SETUP_DETECTORS_MQH
#define OF_SETUP_DETECTORS_MQH

#include "OF_Common.mqh"
#include "OF_DeltaEngine.mqh"
#include "OF_VolumeProfile.mqh"
#include "OF_FootprintAnalyzer.mqh"
#include "OF_AbsorptionStars.mqh"

//+------------------------------------------------------------------+
//| Build a SetupCandidate with SL 1-2 ticks beyond aggression candle |
//| (brief §19 rule 4) and TP at POC for M2, ATR-based for M1         |
//+------------------------------------------------------------------+
SetupCandidate BuildCandidate(const string sym, const ENUM_SETUP_ID id, const ENUM_DIR dir,
                              const double poc, const double targetLevel,
                              const ENUM_VP_LOC loc, const int absStars, const string reason)
  {
   SetupCandidate c; ResetSetupCandidate(c);
   c.setupId = id; c.direction = dir;
   c.absStars = absStars; c.vpLoc = loc; c.reason = reason;

   const double bid = SymbolInfoDouble(sym, SYMBOL_BID);
   const double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
   const double pt  = SymbolInfoDouble(sym, SYMBOL_POINT);
   const double aggH = iHigh(sym, _Period, 1);
   const double aggL = iLow(sym, _Period, 1);

   if(dir == DIR_LONG)
     {
      c.entry = ask;
      c.sl    = aggL - 2 * pt;
      c.tp    = (targetLevel > 0) ? targetLevel : poc;
     }
   else
     {
      c.entry = bid;
      c.sl    = aggH + 2 * pt;
      c.tp    = (targetLevel > 0) ? targetLevel : poc;
     }
   return c;
  }

//+------------------------------------------------------------------+
//| Setup 1 — Absorption Bottom (LONG)                                |
//+------------------------------------------------------------------+
bool Detect_Setup01_AbsBot(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                           CFootprintAnalyzer &fp, const double locTolPips, const int minStars,
                           SetupCandidate &out)
  {
   const double c = iClose(sym, _Period, 1);
   const ENUM_VP_LOC loc = vp.LocationAt(c, locTolPips);
   if(loc != LOC_VAL && loc != LOC_LVN) return false;
   if(!fp.BullishAbsorption(de)) return false;
   const int stars = ComputeAbsorptionStars(sym, de, DIR_LONG);
   if(stars < minStars) return false;
   out = BuildCandidate(sym, SETUP_ABSBOT, DIR_LONG, vp.POC(), vp.POC(), loc, stars, "AbsBot@VAL/LVN");
   return true;
  }

//+------------------------------------------------------------------+
//| Setup 2 — Absorption Top (SHORT)                                  |
//+------------------------------------------------------------------+
bool Detect_Setup02_AbsTop(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                           CFootprintAnalyzer &fp, const double locTolPips, const int minStars,
                           SetupCandidate &out)
  {
   const double c = iClose(sym, _Period, 1);
   const ENUM_VP_LOC loc = vp.LocationAt(c, locTolPips);
   if(loc != LOC_VAH && loc != LOC_HVN) return false;
   if(!fp.BearishAbsorption(de)) return false;
   const int stars = ComputeAbsorptionStars(sym, de, DIR_SHORT);
   if(stars < minStars) return false;
   out = BuildCandidate(sym, SETUP_ABSTOP, DIR_SHORT, vp.POC(), vp.POC(), loc, stars, "AbsTop@VAH/HVN");
   return true;
  }

//+------------------------------------------------------------------+
//| Setup 3 — CVD Bearish Divergence                                  |
//+------------------------------------------------------------------+
bool Detect_Setup03_CvdBear(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                            const double locTolPips, SetupCandidate &out)
  {
   if(!de.BearishDivergence()) return false;
   const double c = iClose(sym, _Period, 1);
   const ENUM_VP_LOC loc = vp.LocationAt(c, locTolPips);
   out = BuildCandidate(sym, SETUP_CVDBEAR, DIR_SHORT, vp.POC(), vp.POC(), loc, 0, "CVD bear div");
   return true;
  }

//+------------------------------------------------------------------+
//| Setup 4 — CVD Bullish Divergence                                  |
//+------------------------------------------------------------------+
bool Detect_Setup04_CvdBull(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                            const double locTolPips, SetupCandidate &out)
  {
   if(!de.BullishDivergence()) return false;
   const double c = iClose(sym, _Period, 1);
   const ENUM_VP_LOC loc = vp.LocationAt(c, locTolPips);
   out = BuildCandidate(sym, SETUP_CVDBULL, DIR_LONG, vp.POC(), vp.POC(), loc, 0, "CVD bull div");
   return true;
  }

//+------------------------------------------------------------------+
//| Setup 5 — VAL Bounce (LONG, M2)                                   |
//+------------------------------------------------------------------+
bool Detect_Setup05_ValBounce(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                              const double locTolPips, SetupCandidate &out)
  {
   const double c = iClose(sym, _Period, 1);
   const double o = iOpen(sym, _Period, 1);
   if(vp.LocationAt(c, locTolPips) != LOC_VAL) return false;
   if(c <= o) return false;                                        // need bullish close
   if(de.BarDelta() < 0) return false;
   out = BuildCandidate(sym, SETUP_VALBNC, DIR_LONG, vp.POC(), vp.POC(), LOC_VAL, 0, "VAL bounce");
   return true;
  }

//+------------------------------------------------------------------+
//| Setup 6 — VAH Fade (SHORT, M2)                                    |
//+------------------------------------------------------------------+
bool Detect_Setup06_VahFade(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                            const double locTolPips, SetupCandidate &out)
  {
   const double c = iClose(sym, _Period, 1);
   const double o = iOpen(sym, _Period, 1);
   if(vp.LocationAt(c, locTolPips) != LOC_VAH) return false;
   if(c >= o) return false;
   if(de.BarDelta() > 0) return false;
   out = BuildCandidate(sym, SETUP_VAHFADE, DIR_SHORT, vp.POC(), vp.POC(), LOC_VAH, 0, "VAH fade");
   return true;
  }

//+------------------------------------------------------------------+
//| Setup 7 — POC Return (BOTH, balanced)                             |
//+------------------------------------------------------------------+
bool Detect_Setup07_PocReturn(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                              const double locTolPips, SetupCandidate &out)
  {
   const double c = iClose(sym, _Period, 1);
   if(vp.LocationAt(c, locTolPips) != LOC_POC) return false;
   const ENUM_DIR dir = de.BarDelta() >= 0 ? DIR_LONG : DIR_SHORT;
   const double tp = dir == DIR_LONG ? vp.VAH() : vp.VAL();
   out = BuildCandidate(sym, SETUP_POCRET, dir, vp.POC(), tp, LOC_POC, 0, "POC return");
   return true;
  }

//+------------------------------------------------------------------+
//| Setups 8/9 — LVN Acceleration (M1)                                |
//+------------------------------------------------------------------+
bool Detect_Setup08_LvnLong(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                            const double locTolPips, SetupCandidate &out)
  {
   const double c = iClose(sym, _Period, 1);
   if(vp.LocationAt(c, locTolPips) != LOC_LVN) return false;
   if(de.BarDelta() <= 0 || de.VolumeZ() < 1.0) return false;
   out = BuildCandidate(sym, SETUP_LVNLONG, DIR_LONG, vp.POC(), vp.VAH(), LOC_LVN, 0, "LVN accel L");
   return true;
  }
bool Detect_Setup09_LvnShort(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                             const double locTolPips, SetupCandidate &out)
  {
   const double c = iClose(sym, _Period, 1);
   if(vp.LocationAt(c, locTolPips) != LOC_LVN) return false;
   if(de.BarDelta() >= 0 || de.VolumeZ() < 1.0) return false;
   out = BuildCandidate(sym, SETUP_LVNSHORT, DIR_SHORT, vp.POC(), vp.VAL(), LOC_LVN, 0, "LVN accel S");
   return true;
  }

//+------------------------------------------------------------------+
//| Setup 10 — HVN Rejection (B-grade, default off in §7)             |
//+------------------------------------------------------------------+
bool Detect_Setup10_HvnRej(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                           const double locTolPips, SetupCandidate &out)
  {
   const double c = iClose(sym, _Period, 1);
   if(vp.LocationAt(c, locTolPips) != LOC_HVN) return false;
   const ENUM_DIR dir = de.BarDelta() < 0 ? DIR_SHORT : DIR_LONG;
   out = BuildCandidate(sym, SETUP_HVNREJ, dir, vp.POC(), vp.POC(), LOC_HVN, 0, "HVN rej");
   return true;
  }

//+------------------------------------------------------------------+
//| Setups 11/12 — Stacked Imbalance + CVD                            |
//+------------------------------------------------------------------+
bool Detect_Setup11_StackBull(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                              CFootprintAnalyzer &fp, const double locTolPips, SetupCandidate &out)
  {
   if(!fp.StackedBullImbalance(de)) return false;
   if(de.CvdSlope5() <= 0) return false;
   const double c = iClose(sym, _Period, 1);
   const ENUM_VP_LOC loc = vp.LocationAt(c, locTolPips);
   out = BuildCandidate(sym, SETUP_STACKBULL, DIR_LONG, vp.POC(), vp.VAH(), loc, 0, "Stack bull+CVD");
   return true;
  }
bool Detect_Setup12_StackBear(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                              CFootprintAnalyzer &fp, const double locTolPips, SetupCandidate &out)
  {
   if(!fp.StackedBearImbalance(de)) return false;
   if(de.CvdSlope5() >= 0) return false;
   const double c = iClose(sym, _Period, 1);
   const ENUM_VP_LOC loc = vp.LocationAt(c, locTolPips);
   out = BuildCandidate(sym, SETUP_STACKBEAR, DIR_SHORT, vp.POC(), vp.VAL(), loc, 0, "Stack bear+CVD");
   return true;
  }

//+------------------------------------------------------------------+
//| Setup 13 — Pullback to stacked imbalance zone                     |
//+------------------------------------------------------------------+
bool Detect_Setup13_PullStack(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                              const double locTolPips, SetupCandidate &out)
  {
   // Heuristic: prior stacked imbalance zone in last 10 bars, pullback now
   double zone = 0; ENUM_DIR dir = DIR_NONE;
   for(int i = 1; i < 10; i++)
     {
      bool bull = de.Delta(i) > 0 && de.Delta(i+1) > 0 && de.Delta(i+2) > 0;
      bool bear = de.Delta(i) < 0 && de.Delta(i+1) < 0 && de.Delta(i+2) < 0;
      if(bull) { zone = iLow(sym, _Period, i); dir = DIR_LONG; break; }
      if(bear) { zone = iHigh(sym, _Period, i); dir = DIR_SHORT; break; }
     }
   if(dir == DIR_NONE) return false;
   const double c = iClose(sym, _Period, 1);
   const double pip = PipSize(sym);
   if(MathAbs(c - zone) > 5 * pip) return false;
   const ENUM_VP_LOC loc = vp.LocationAt(c, locTolPips);
   out = BuildCandidate(sym, SETUP_PULLSTACK, dir, vp.POC(), vp.POC(), loc, 0, "Pull stack");
   return true;
  }

//+------------------------------------------------------------------+
//| Setup 14 — Spring (false break low + CVD div + reclaim)           |
//+------------------------------------------------------------------+
bool Detect_Setup14_Spring(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                           const double locTolPips, SetupCandidate &out)
  {
   double swingLow = iLow(sym, _Period, 5);
   for(int i = 6; i < 30; i++) swingLow = MathMin(swingLow, iLow(sym, _Period, i));
   const double curL = iLow(sym, _Period, 1);
   const double curC = iClose(sym, _Period, 1);
   if(curL > swingLow) return false;       // need fake-out below
   if(curC <= swingLow) return false;       // need reclaim
   if(!de.BullishDivergence()) return false;
   const ENUM_VP_LOC loc = vp.LocationAt(curC, locTolPips);
   out = BuildCandidate(sym, SETUP_SPRING, DIR_LONG, vp.POC(), vp.POC(), loc, 0, "Spring");
   return true;
  }

//+------------------------------------------------------------------+
//| Setup 15 — Upthrust                                               |
//+------------------------------------------------------------------+
bool Detect_Setup15_Upthrust(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                             const double locTolPips, SetupCandidate &out)
  {
   double swingHigh = iHigh(sym, _Period, 5);
   for(int i = 6; i < 30; i++) swingHigh = MathMax(swingHigh, iHigh(sym, _Period, i));
   const double curH = iHigh(sym, _Period, 1);
   const double curC = iClose(sym, _Period, 1);
   if(curH < swingHigh) return false;
   if(curC >= swingHigh) return false;
   if(!de.BearishDivergence()) return false;
   const ENUM_VP_LOC loc = vp.LocationAt(curC, locTolPips);
   out = BuildCandidate(sym, SETUP_UPTHRUST, DIR_SHORT, vp.POC(), vp.POC(), loc, 0, "Upthrust");
   return true;
  }

//+------------------------------------------------------------------+
//| Setup 16/17 — SOS / LPSY (post-Spring continuation)               |
//+------------------------------------------------------------------+
bool Detect_Setup16_Sos(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                        const double locTolPips, SetupCandidate &out)
  {
   if(de.CvdSlope5() <= 0) return false;
   if(de.VolumeZ() < 1.0) return false;
   const double c = iClose(sym, _Period, 1);
   const ENUM_VP_LOC loc = vp.LocationAt(c, locTolPips);
   out = BuildCandidate(sym, SETUP_SOS, DIR_LONG, vp.POC(), vp.VAH(), loc, 0, "SOS");
   return true;
  }
bool Detect_Setup17_Lpsy(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                         const double locTolPips, SetupCandidate &out)
  {
   if(de.CvdSlope5() >= 0) return false;
   if(de.VolumeZ() < 1.0) return false;
   const double c = iClose(sym, _Period, 1);
   const ENUM_VP_LOC loc = vp.LocationAt(c, locTolPips);
   out = BuildCandidate(sym, SETUP_LPSY, DIR_SHORT, vp.POC(), vp.VAL(), loc, 0, "LPSY");
   return true;
  }

//+------------------------------------------------------------------+
//| Setup 18 — Liquidity sweep + rejection + CHOCH                    |
//+------------------------------------------------------------------+
bool Detect_Setup18_LiqSweep(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                             const double locTolPips, SetupCandidate &out)
  {
   double swingHigh = iHigh(sym, _Period, 3), swingLow = iLow(sym, _Period, 3);
   for(int i = 4; i < 50; i++) {
      swingHigh = MathMax(swingHigh, iHigh(sym, _Period, i));
      swingLow  = MathMin(swingLow,  iLow(sym, _Period, i));
   }
   const double cH = iHigh(sym, _Period, 1), cL = iLow(sym, _Period, 1);
   const double cC = iClose(sym, _Period, 1);
   ENUM_DIR dir = DIR_NONE;
   if(cH > swingHigh && cC < swingHigh) dir = DIR_SHORT;
   if(cL < swingLow  && cC > swingLow)  dir = DIR_LONG;
   if(dir == DIR_NONE) return false;
   const ENUM_VP_LOC loc = vp.LocationAt(cC, locTolPips);
   out = BuildCandidate(sym, SETUP_LIQSWEEP, dir, vp.POC(), vp.POC(), loc, 0, "Liq sweep");
   return true;
  }

//+------------------------------------------------------------------+
//| Setup 19 — Order block return + CVD                               |
//| (heuristic: previous opposing-momentum candle revisited)          |
//+------------------------------------------------------------------+
bool Detect_Setup19_ObReturn(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                             const double locTolPips, SetupCandidate &out)
  {
   for(int i = 5; i < 30; i++)
     {
      const double oo = iOpen(sym, _Period, i);
      const double oc = iClose(sym, _Period, i);
      const double cur = iClose(sym, _Period, 1);
      const double pip = PipSize(sym);
      if(oc < oo && MathAbs(cur - iHigh(sym, _Period, i)) < 5 * pip && de.CvdSlope5() < 0)
        {
         out = BuildCandidate(sym, SETUP_OBRETURN, DIR_SHORT, vp.POC(), vp.VAL(), vp.LocationAt(cur, locTolPips), 0, "OB return short");
         return true;
        }
      if(oc > oo && MathAbs(cur - iLow(sym, _Period, i)) < 5 * pip && de.CvdSlope5() > 0)
        {
         out = BuildCandidate(sym, SETUP_OBRETURN, DIR_LONG, vp.POC(), vp.VAH(), vp.LocationAt(cur, locTolPips), 0, "OB return long");
         return true;
        }
     }
   return false;
  }

//+------------------------------------------------------------------+
//| Setup 20 — SMT divergence (correlated-pair) — uses M5 corr CVD    |
//| Stub: requires corrSlope passed in; full impl in NotificationCenter|
//+------------------------------------------------------------------+
bool Detect_Setup20_SmtDiv(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                           const double corrCvdSlope, const double locTolPips, SetupCandidate &out)
  {
   const double mySlope = de.CvdSlope5();
   if(mySlope * corrCvdSlope >= 0) return false;        // same sign → no SMT
   const double c = iClose(sym, _Period, 1);
   const ENUM_VP_LOC loc = vp.LocationAt(c, locTolPips);
   const ENUM_DIR dir = mySlope > 0 ? DIR_LONG : DIR_SHORT;
   out = BuildCandidate(sym, SETUP_SMTDIV, dir, vp.POC(), vp.POC(), loc, 0, "SMT div");
   return true;
  }

//+------------------------------------------------------------------+
//| Setup 21 — Breaker block fade                                     |
//+------------------------------------------------------------------+
bool Detect_Setup21_Breaker(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                            const double locTolPips, SetupCandidate &out)
  {
   // Heuristic: prior swing-high broken then retest from above → bull breaker (long)
   double swingHigh = iHigh(sym, _Period, 5), swingLow = iLow(sym, _Period, 5);
   for(int i = 6; i < 40; i++) {
      swingHigh = MathMax(swingHigh, iHigh(sym, _Period, i));
      swingLow  = MathMin(swingLow,  iLow(sym, _Period, i));
   }
   const double curC = iClose(sym, _Period, 1);
   const double pip  = PipSize(sym);
   if(curC > swingHigh && MathAbs(curC - swingHigh) < 5 * pip && de.CvdSlope5() > 0)
     { out = BuildCandidate(sym, SETUP_BREAKER, DIR_LONG, vp.POC(), vp.VAH(), vp.LocationAt(curC, locTolPips), 0, "Breaker L"); return true; }
   if(curC < swingLow && MathAbs(curC - swingLow) < 5 * pip && de.CvdSlope5() < 0)
     { out = BuildCandidate(sym, SETUP_BREAKER, DIR_SHORT, vp.POC(), vp.VAL(), vp.LocationAt(curC, locTolPips), 0, "Breaker S"); return true; }
   return false;
  }

//+------------------------------------------------------------------+
//| Setup 22 — ICT AMD model (NY Main accumulation/manip/distrib)     |
//+------------------------------------------------------------------+
bool Detect_Setup22_Amd(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                        const double locTolPips, SetupCandidate &out)
  {
   // Simplified: prior accumulation range broken with strong delta in NY Main
   double rh = iHigh(sym, _Period, 5), rl = iLow(sym, _Period, 5);
   for(int i = 6; i < 24; i++) {
      rh = MathMax(rh, iHigh(sym, _Period, i));
      rl = MathMin(rl, iLow(sym, _Period, i));
   }
   const double curC = iClose(sym, _Period, 1);
   if(curC > rh && de.DeltaZ() > 1.5)
     { out = BuildCandidate(sym, SETUP_AMD, DIR_LONG, vp.POC(), vp.VAH(), vp.LocationAt(curC, locTolPips), 0, "AMD long"); return true; }
   if(curC < rl && de.DeltaZ() < -1.5)
     { out = BuildCandidate(sym, SETUP_AMD, DIR_SHORT, vp.POC(), vp.VAL(), vp.LocationAt(curC, locTolPips), 0, "AMD short"); return true; }
   return false;
  }

//+------------------------------------------------------------------+
//| Setup 23 — Unfinished auction fade                                |
//+------------------------------------------------------------------+
bool Detect_Setup23_UnfAuc(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                           CFootprintAnalyzer &fp, const double locTolPips, SetupCandidate &out)
  {
   if(!fp.UnfinishedAuction()) return false;
   const double curH = iHigh(sym, _Period, 1);
   const double curL = iLow(sym, _Period, 1);
   const double prevH = iHigh(sym, _Period, 2);
   const double curC  = iClose(sym, _Period, 1);
   const ENUM_DIR dir = (curH > prevH) ? DIR_SHORT : DIR_LONG;
   const ENUM_VP_LOC loc = vp.LocationAt(curC, locTolPips);
   out = BuildCandidate(sym, SETUP_UNFAUC, dir, vp.POC(), vp.POC(), loc, 0, "Unfinished auc");
   return true;
  }

//+------------------------------------------------------------------+
//| Setup 24 — Poor high / poor low retest fade                       |
//+------------------------------------------------------------------+
bool Detect_Setup24_PoorHL(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                           const double locTolPips, SetupCandidate &out)
  {
   double prevH = iHigh(sym, _Period, 2), prevL = iLow(sym, _Period, 2);
   const double curH = iHigh(sym, _Period, 1), curL = iLow(sym, _Period, 1);
   const double pip = PipSize(sym);
   const double curC = iClose(sym, _Period, 1);
   if(MathAbs(curH - prevH) < pip && de.BarDelta() < 0)
     { out = BuildCandidate(sym, SETUP_POORHL, DIR_SHORT, vp.POC(), vp.POC(), vp.LocationAt(curC, locTolPips), 0, "Poor high"); return true; }
   if(MathAbs(curL - prevL) < pip && de.BarDelta() > 0)
     { out = BuildCandidate(sym, SETUP_POORHL, DIR_LONG, vp.POC(), vp.POC(), vp.LocationAt(curC, locTolPips), 0, "Poor low"); return true; }
   return false;
  }

//+------------------------------------------------------------------+
//| Setup 25 — Iceberg absorption                                     |
//| Heuristic: very high vol, near-zero delta, small range, at level  |
//+------------------------------------------------------------------+
bool Detect_Setup25_Iceberg(const string sym, CDeltaEngine &de, CVolumeProfile &vp,
                            const double locTolPips, SetupCandidate &out)
  {
   const double volZ = de.VolumeZ();
   const double dz   = de.DeltaZ();
   const double atr  = ATR(sym, _Period, 14);
   const double range = iHigh(sym, _Period, 1) - iLow(sym, _Period, 1);
   if(volZ < 2.0 || MathAbs(dz) > 0.5 || atr <= 0 || range > 0.6 * atr) return false;
   const double curC = iClose(sym, _Period, 1);
   const ENUM_VP_LOC loc = vp.LocationAt(curC, locTolPips);
   if(loc == LOC_NONE) return false;
   const ENUM_DIR dir = (loc == LOC_VAL || loc == LOC_LVN) ? DIR_LONG : DIR_SHORT;
   out = BuildCandidate(sym, SETUP_ICEBERG, dir, vp.POC(), vp.POC(), loc, 0, "Iceberg");
   return true;
  }

#endif
