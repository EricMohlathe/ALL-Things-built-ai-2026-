//+------------------------------------------------------------------+
//| GODMODE_OFEA_Enhanced.mq5 — v2 EA glue                           |
//| Wires the base build (Experts/GODMODE_OFEA/GODMODE_OFEA.mq5) to  |
//| the Enhanced/ includes: VWAP, BidAsk, DeltaEnhanced, RegimeHMM,  |
//| PriceAction, SweepDetector, KellySizer, ProbabilityScore.        |
//|                                                                  |
//| This file is a SUPERSET of the base EA — copy your base build's  |
//| body here and uncomment the Enhanced bindings, or load alongside |
//| the base build as a parallel "research" EA.                      |
//+------------------------------------------------------------------+
#property copyright "GODMODE_OFEA — Enhanced"
#property version   "2.00"
#property strict

// Base build modules (existing).
#include "../../Include/OF_Common.mqh"
#include "../../Include/OF_DeltaEngine.mqh"
#include "../../Include/OF_VolumeProfile.mqh"
#include "../../Include/OF_FootprintAnalyzer.mqh"
#include "../../Include/OF_AbsorptionStars.mqh"
#include "../../Include/OF_SessionGate.mqh"
#include "../../Include/OF_HTFAlignment.mqh"
#include "../../Include/OF_RiskManager.mqh"
#include "../../Include/OF_TradeManager.mqh"
#include "../../Include/OF_NotificationCenter.mqh"
#include "../../Include/OF_Dashboard.mqh"
#include "../../Include/OF_ChartViz.mqh"
#include "../../Include/OF_SetupDetectors.mqh"
#include "../../Include/OF_Logger.mqh"

// Enhanced modules (new).
#include "../../Include/OF_VWAP.mqh"
#include "../../Include/OF_BidAsk.mqh"
#include "../../Include/OF_DeltaEnhanced.mqh"
#include "../../Include/OF_RegimeHMM.mqh"
#include "../../Include/OF_PriceAction.mqh"
#include "../../Include/OF_SweepDetector.mqh"
#include "../../Include/OF_PoolResilience.mqh"
#include "../../Include/OF_KellySizer.mqh"
#include "../../Include/OF_ProbabilityScore.mqh"

input ENUM_OP_MODE  OpMode               = MODE_MANUAL;
input double        RiskPctMax           = 0.5;
input double        KellyKappa           = 0.25;
input bool          UseEnhancedGates     = true;
input int           SpreadMaxZ           = 2;
input int           BarDeltaLookback     = 20;
input int           VWAPBands_K1         = 1;
input int           VWAPBands_K2         = 2;

COF_VWAP             g_vwap;
COF_BidAsk           g_ba;
COF_DeltaEnhanced    g_dE;
COF_RegimeHMM        g_reg;
COF_PriceAction      g_pa;
COF_SweepDetector    g_sw;
COF_PoolResilience   g_pool;
COF_ProbabilityScore g_prob;

int OnInit()
{
   g_ba.Init();
   g_dE.Init(BarDeltaLookback);
   g_reg.Init();
   PrintFormat("GODMODE_OFEA Enhanced initialised — mode=%s κ=%.2f", EnumToString(OpMode), KellyKappa);
   return INIT_SUCCEEDED;
}
void OnDeinit(const int r) { PrintFormat("GODMODE_OFEA Enhanced shutdown (reason=%d)", r); }

void OnTick()
{
   g_ba.Update(_Symbol);
   // Defer the per-bar logic to OnBar() — call via new-bar detection.
   static datetime lastBar = 0;
   datetime t0[1]; CopyTime(_Symbol, _Period, 0, 1, t0);
   if (t0[0] == lastBar) return;
   lastBar = t0[0];
   OnBarClose();
}

void OnBarClose()
{
   MqlRates r[]; ArraySetAsSeries(r, true);
   if (CopyRates(_Symbol, _Period, 0, 50, r) < 30) return;

   // 1) Enhanced delta from prior closed bar (index 1, since 0 is now-forming).
   double rng = r[1].high - r[1].low;
   double bw  = rng > 0 ? (r[1].close - r[1].low) / rng : 0.5;
   double bd  = r[1].tick_volume * (bw - (1.0 - bw));
   g_dE.OnBar(bd, r[1].close);

   // 2) VWAP update.
   double typ = (r[1].high + r[1].low + r[1].close) / 3.0;
   g_vwap.Update(typ, (double)r[1].tick_volume, r[1].time);

   // 3) Regime HMM-lite.
   g_reg.Update(g_dE.st.cvdSlope, /*footImb=*/0, /*profileSkew=*/0, g_dE.st.zScore);

   // 4) Price action.
   double H[], L[], C[];
   ArraySetAsSeries(H, true); ArraySetAsSeries(L, true); ArraySetAsSeries(C, true);
   CopyHigh(_Symbol, _Period, 0, 50, H);
   CopyLow(_Symbol, _Period, 0, 50, L);
   CopyClose(_Symbol, _Period, 0, 50, C);
   double atrV[1]; CopyBuffer(iATR(_Symbol, _Period, 14), 0, 0, 1, atrV);
   g_pa.Update(H, L, C, 20, 0.10, atrV[0]);

   // 5) Composite probability.
   double pct = ComputeCompositeProbability();
   PrintFormat("[ENHANCED] regime=%s probScore=%.0f%% grade=%s", g_reg.Name(), pct, g_prob.Grade());

   // 6) Optional auto-fire (only if MODE_AUTO).
   if (OpMode == MODE_AUTO && pct >= 85.0) FireTradeIfReady(r);
}

double ComputeCompositeProbability()
{
   double g1 = (g_pa.st.equalHighsCluster || g_pa.st.equalLowsCluster) ? 1 : 0;
   double g2 = 1.0; // F2 KillZone — bind to OF_SessionGate
   double g3 = 1.0; // F3 HTF — bind to OF_HTFAlignment
   double g4 = MathAbs(g_dE.st.cvdSlope) > 0 ? 1 : 0;
   double g5 = 1.0; // F5 VP state — bind to OF_VolumeProfile
   double g6 = g_reg.st.justTransitioned ? 1 : 0.5;
   double g7 = g_sw.last.preconditionsPassed / 6.0;
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double g8 = MathAbs(g_vwap.ZScore(price)) < 2.0 ? 1 : 0;
   double g9 = (g_pa.st.fvgUp || g_pa.st.fvgDown) ? 1 : 0;
   double g10 = 0.5; // pool resilience
   double g11 = g_ba.SpreadAcceptable(SpreadMaxZ) ? 1 : 0;
   double g12 = 1.0; // R:R — bind to OF_RiskManager
   return g_prob.Compute(g1,g2,g3,g4,g5,g6,g7,g8,g9,g10,g11,g12);
}

void FireTradeIfReady(const MqlRates &r[])
{
   // SL placed 2 ticks beyond aggression candle per brief §15.
   // Sizing: fractional Kelly capped at RiskPctMax (≤ 2.0 per §12 rule 2).
   double winProb = g_sw.EmpiricalWinRate();
   double payoff  = g_sw.ExpectedR() > 0 ? g_sw.ExpectedR() + 1.0 : 2.0;
   double riskPct = COF_KellySizer::RiskPctFromKelly(winProb, payoff, KellyKappa);
   riskPct = MathMin(riskPct, RiskPctMax);
   PrintFormat("[ENHANCED] would-fire: kellyRiskPct=%.3f", riskPct);
   // Trade execution intentionally guarded — wire to OF_TradeManager when ready.
}
