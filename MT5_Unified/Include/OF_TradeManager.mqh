//+------------------------------------------------------------------+
//|                                              OF_TradeManager.mqh |
//|  Partial close / BE move / trail / POC exit / session close      |
//|  Brief §5 (manage existing positions) + §12 rule 1                |
//+------------------------------------------------------------------+
#property strict
#ifndef OF_TRADE_MANAGER_MQH
#define OF_TRADE_MANAGER_MQH

#include "OF_Common.mqh"
#include <Trade/Trade.mqh>

class CTradeManager
  {
private:
   string m_sym;
   long   m_magic;
   string m_label;
   CTrade m_trade;

   bool   m_partialClose, m_useTrail, m_exitAtPoc;
   double m_partialPct, m_partialAtR, m_beAtR, m_trailAtrMult;

   // per-position state (single-position model — extend for pyramiding)
   ulong  m_pos;
   double m_entryPrice, m_initialSl, m_origLots;
   bool   m_partialDone, m_beMoved;
   ENUM_DIR m_dir;

public:
   void Init(const string sym, const long magic, const string label,
             const bool partial, const double partialPct, const double partialAtR,
             const double beAtR, const bool useTrail, const double trailAtr, const bool exitPoc)
     {
      m_sym = sym; m_magic = magic; m_label = label;
      m_partialClose = partial; m_partialPct = partialPct; m_partialAtR = partialAtR;
      m_beAtR = beAtR; m_useTrail = useTrail; m_trailAtrMult = trailAtr; m_exitAtPoc = exitPoc;
      m_trade.SetExpertMagicNumber(magic);
      m_pos = 0; m_partialDone = false; m_beMoved = false; m_dir = DIR_NONE;
     }

   bool HasOpenPosition()
     {
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         const ulong t = PositionGetTicket(i);
         if(!PositionSelectByTicket(t)) continue;
         if(PositionGetString(POSITION_SYMBOL) != m_sym) continue;
         if(PositionGetInteger(POSITION_MAGIC) != m_magic) continue;
         m_pos = t;
         m_dir = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? DIR_LONG : DIR_SHORT;
         return true;
        }
      m_pos = 0; m_dir = DIR_NONE;
      return false;
     }

   bool OpenPosition(const ENUM_DIR dir, const double lots, const double sl, const double tp, const string comment)
     {
      if(lots <= 0) return false;
      bool ok = false;
      if(dir == DIR_LONG)  ok = m_trade.Buy(lots, m_sym, 0, sl, tp, comment);
      if(dir == DIR_SHORT) ok = m_trade.Sell(lots, m_sym, 0, sl, tp, comment);
      if(!ok) { Print("OpenPosition err=", GetLastError()); return false; }
      // populate state from the just-opened position
      if(HasOpenPosition())
        {
         m_entryPrice = PositionGetDouble(POSITION_PRICE_OPEN);
         m_initialSl  = PositionGetDouble(POSITION_SL);
         m_origLots   = PositionGetDouble(POSITION_VOLUME);
         m_partialDone = false; m_beMoved = false;
        }
      return true;
     }

   //--- Walk-forward management called every bar
   void ManagePosition(const double poc)
     {
      if(!HasOpenPosition()) return;
      const double cur = m_dir == DIR_LONG
                       ? SymbolInfoDouble(m_sym, SYMBOL_BID)
                       : SymbolInfoDouble(m_sym, SYMBOL_ASK);
      const double risk = MathAbs(m_entryPrice - m_initialSl);
      if(risk <= 0) return;
      const double rMult = m_dir == DIR_LONG
                         ? (cur - m_entryPrice) / risk
                         : (m_entryPrice - cur) / risk;

      // 1R partial close + BE
      if(m_partialClose && !m_partialDone && rMult >= m_partialAtR)
        {
         const double closeLots = NormaliseLots(m_sym, m_origLots * (m_partialPct / 100.0));
         if(closeLots > 0) m_trade.PositionClosePartial(m_pos, closeLots);
         m_partialDone = true;
        }
      if(!m_beMoved && rMult >= m_beAtR)
        {
         const double pip = PipSize(m_sym);
         const double newSl = m_dir == DIR_LONG ? m_entryPrice + pip : m_entryPrice - pip;
         m_trade.PositionModify(m_pos, newSl, PositionGetDouble(POSITION_TP));
         m_beMoved = true;
        }

      // ATR trail
      if(m_useTrail && rMult >= m_beAtR)
        {
         const double atr = ATR(m_sym, _Period, 14);
         if(atr > 0)
           {
            const double newSl = m_dir == DIR_LONG ? cur - atr * m_trailAtrMult
                                                   : cur + atr * m_trailAtrMult;
            const double curSl = PositionGetDouble(POSITION_SL);
            // Symmetric tighter-or-unset check for both directions (precedence-safe).
            // Use epsilon comparison instead of ==0 — broker can return a tiny
            // non-zero SL after Buy(... ,0, ...) due to FP normalisation, which
            // would falsely satisfy "unset" and let us widen the stop.
            const bool slUnset = curSl < _Point;
            const bool tighter = (m_dir == DIR_LONG)
                                 ? (slUnset || newSl > curSl)
                                 : (slUnset || newSl < curSl);
            if(tighter) m_trade.PositionModify(m_pos, newSl, PositionGetDouble(POSITION_TP));
           }
        }

      // POC exit (Model 2 — 70% rule)
      if(m_exitAtPoc && poc > 0)
        {
         const bool reached = m_dir == DIR_LONG ? cur >= poc : cur <= poc;
         if(reached) m_trade.PositionClose(m_pos);
        }
     }

   void CloseAll()
     {
      if(!HasOpenPosition()) return;
      m_trade.PositionClose(m_pos);
     }
  };

#endif
