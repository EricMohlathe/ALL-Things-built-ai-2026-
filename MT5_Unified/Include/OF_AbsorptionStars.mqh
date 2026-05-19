//+------------------------------------------------------------------+
//|                                          OF_AbsorptionStars.mqh  |
//|  1–5 confidence scoring for absorption signals (brief §11.4)     |
//+------------------------------------------------------------------+
#property strict
#ifndef OF_ABSORPTION_STARS_MQH
#define OF_ABSORPTION_STARS_MQH

#include "OF_Common.mqh"
#include "OF_DeltaEngine.mqh"

int ComputeAbsorptionStars(const string sym, const CDeltaEngine &de, const ENUM_DIR dir)
  {
   int stars = 0;
   const double volZ = de.VolumeZ();
   const double dz   = de.DeltaZ();
   if(volZ < 1.0) return 0;

   stars = 1;
   if(volZ >= 2.0) stars++;
   if(volZ >= 3.0) stars++;
   if(MathAbs(dz) >= 2.0) stars++;

   const double o = iOpen(sym, _Period, 1);
   const double c = iClose(sym, _Period, 1);
   const double h = iHigh(sym, _Period, 1);
   const double l = iLow(sym, _Period, 1);
   const double range = MathMax(h - l, _Point);

   double wickPct = 0.0;
   if(dir == DIR_LONG)  wickPct = (MathMin(o, c) - l) / range;  // lower wick for bull
   if(dir == DIR_SHORT) wickPct = (h - MathMax(o, c)) / range;  // upper wick for bear
   if(wickPct >= 0.4) stars++;

   if(stars > 5) stars = 5;
   return stars;
  }

#endif
