//+------------------------------------------------------------------+
//|  GODMODE DEITY CONTROLLER — multi-market, multi-setup (MT5)       |
//|------------------------------------------------------------------|
//|  ONE EA running all 4 validated D1 setups across all their        |
//|  markets from an editable roster. The honest way to MORE trades:   |
//|  ~20-30 real trades/yr aggregate, each a validated edge.           |
//|                                                                   |
//|  Setups (long-only, validated D1 — see DEITY README):             |
//|   SPRING=GM14 spring  STACKBULL=GM11 delta-stack                   |
//|   SOS=GM16 sign-of-strength  AMD=GM22 ICT power-of-three           |
//|                                                                   |
//|  Roster: SYMBOL:SETUP:stopATR:tpATR:trailATR  (slots split by ;)  |
//|  EDIT symbols to your broker's names. Attach to ONE D1 chart;      |
//|  the EA pulls each roster symbol's own D1 bars + trades them.      |
//|  Truth = MT5 Strategy Tester per symbol (test one at a time).     |
//+------------------------------------------------------------------+
#property copyright "GODMODE OS"
#property version   "1.00"
#property strict
#include <Trade/Trade.mqh>

// Default roster = 14 D1 winners validated across metals + indices (PF>=1.5, trd>=30,
// net-positive full-period AND out-of-sample). EDIT symbols to your broker's names.
input string RosterStr = "XAGUSD:SPRING:0:0:0;XAUUSD:AMD:3:1:0;XAUUSD:STACKBULL:3:1:0;XAUUSD:SPRING:3:1:0;XAGUSD:AMD:2.5:0.8:0;XAGUSD:SOS:1.5:3:2;NAS100:SOS:2:4:3;US500:SOS:3:1:0;US30:AMD:4:1.5:0;US30:SPRING:4:1.5:0;US30:SOS:0:0:0;NAS100:STACKBULL:3:6:0;US500:SPRING:4:1.5:0;NAS100:SPRING:4:1.5:0";
input int    LB         = 20;
input double K          = 1.0;
input int    Hold       = 10;
input double RiskPct    = 1.0;
input double SizingATR  = 3.0;
input int    AtrPeriod  = 14;
input long   BaseMagic  = 814000;

CTrade   trade;
string   gSym[], gSetup[];
double   gStop[], gTp[], gTrail[];
int      gAtr[], gEntryBar[], gBarCount[];
long     gMagic[];
datetime gLastBar[];
int      gN = 0;

int OnInit()
{
   string slots[]; int ns = StringSplit(RosterStr, ';', slots);
   for(int i=0;i<ns;i++)
   {
      string f[]; int nf = StringSplit(slots[i], ':', f);
      if(nf < 5) continue;
      string sym = f[0]; StringTrimLeft(sym); StringTrimRight(sym);
      if(!SymbolSelect(sym, true)){ Print("Roster: cannot select ", sym, " — skipped"); continue; }
      int h = iATR(sym, PERIOD_D1, AtrPeriod);
      if(h==INVALID_HANDLE){ Print("ATR handle fail ", sym); continue; }
      int k = gN; gN++;
      ArrayResize(gSym,gN); ArrayResize(gSetup,gN); ArrayResize(gStop,gN); ArrayResize(gTp,gN);
      ArrayResize(gTrail,gN); ArrayResize(gAtr,gN); ArrayResize(gEntryBar,gN); ArrayResize(gBarCount,gN);
      ArrayResize(gMagic,gN); ArrayResize(gLastBar,gN);
      string st = f[1]; StringTrimLeft(st); StringTrimRight(st); StringToUpper(st);
      gSym[k]=sym; gSetup[k]=st; gStop[k]=StringToDouble(f[2]); gTp[k]=StringToDouble(f[3]);
      gTrail[k]=StringToDouble(f[4]); gAtr[k]=h; gEntryBar[k]=-1; gBarCount[k]=0;
      gMagic[k]=BaseMagic + k; gLastBar[k]=0;
      PrintFormat("Slot %d: %s %s stop%.1f/tp%.1f/trail%.1f", k, gSym[k], gSetup[k], gStop[k], gTp[k], gTrail[k]);
   }
   PrintFormat("GODMODE Deity Controller — %d slots.", gN);
   return(gN>0 ? INIT_SUCCEEDED : INIT_FAILED);
}
void OnDeinit(const int r){ for(int i=0;i<gN;i++) IndicatorRelease(gAtr[i]); }

double Atr(int i){ double b[]; if(CopyBuffer(gAtr[i],0,1,1,b)==1) return b[0]; return 0; }
double Cl(string s,int sh){ return iClose(s,PERIOD_D1,sh); }
long   TV(string s,int sh){ long v[]; if(CopyTickVolume(s,PERIOD_D1,sh,1,v)==1) return v[0]; return 0; }
double D(string s,int sh){ double sg=(iClose(s,PERIOD_D1,sh)>=iOpen(s,PERIOD_D1,sh))?1.0:-1.0; return sg*(double)TV(s,sh); }
double MeanD(string s,int n){ double sum=0; for(int j=1;j<=n;j++) sum+=D(s,j); return sum/n; }
double LowC(string s,int from,int n){ double m=DBL_MAX; for(int i=from;i<from+n;i++){ double c=iClose(s,PERIOD_D1,i); if(c<m) m=c; } return m; }
double HighC(string s,int from,int n){ double m=-DBL_MAX; for(int i=from;i<from+n;i++){ double c=iClose(s,PERIOD_D1,i); if(c>m) m=c; } return m; }

int Signal(int i)
{
   string s=gSym[i]; double a=Atr(i); if(a<=0) return 0;
   if(Bars(s,PERIOD_D1) < LB+6) return 0;
   double c1=iClose(s,PERIOD_D1,1), o1=iOpen(s,PERIOD_D1,1), h1=iHigh(s,PERIOD_D1,1), l1=iLow(s,PERIOD_D1,1);
   double rng=h1-l1;
   string st=gSetup[i];
   if(st=="SPRING")    return (l1<LowC(s,2,LB) && c1>LowC(s,2,LB)) ? 1 : 0;
   if(st=="STACKBULL") return (D(s,1)>0 && D(s,2)>0 && D(s,3)>0 && D(s,1)>K*MathAbs(MeanD(s,LB))) ? 1 : 0;
   if(st=="SOS")       return (rng>K*a && c1>o1 && D(s,1)>0 && c1>=HighC(s,2,LB)) ? 1 : 0;
   if(st=="AMD")       return (iLow(s,PERIOD_D1,2)<LowC(s,3,LB) && c1>iClose(s,PERIOD_D1,2) && rng>K*a && D(s,1)>0) ? 1 : 0;
   return 0;
}

bool HasPos(int i){ for(int p=PositionsTotal()-1;p>=0;p--){ ulong tk=PositionGetTicket(p);
   if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==gSym[i]&&PositionGetInteger(POSITION_MAGIC)==gMagic[i]) return true; } return false; }
void CloseSlot(int i){ for(int p=PositionsTotal()-1;p>=0;p--){ ulong tk=PositionGetTicket(p);
   if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==gSym[i]&&PositionGetInteger(POSITION_MAGIC)==gMagic[i]) trade.PositionClose(tk); } }

double Lots(string s,double stopDist){
   double ts=SymbolInfoDouble(s,SYMBOL_TRADE_TICK_SIZE), tv=SymbolInfoDouble(s,SYMBOL_TRADE_TICK_VALUE);
   if(ts<=0||tv<=0||stopDist<=0) return SymbolInfoDouble(s,SYMBOL_VOLUME_MIN);
   double lossPerLot=(stopDist/ts)*tv;
   double lots=AccountInfoDouble(ACCOUNT_EQUITY)*(RiskPct/100.0)/lossPerLot;
   double step=SymbolInfoDouble(s,SYMBOL_VOLUME_STEP), mn=SymbolInfoDouble(s,SYMBOL_VOLUME_MIN), mx=SymbolInfoDouble(s,SYMBOL_VOLUME_MAX);
   if(step>0) lots=MathFloor(lots/step)*step; return MathMax(mn,MathMin(mx,lots)); }

void Enter(int i){
   string s=gSym[i]; double a=Atr(i); if(a<=0) return;
   double stopDist=(gStop[i]>0?gStop[i]:SizingATR)*a;
   double lots=Lots(s,stopDist); if(lots<=0) return;
   double ask=SymbolInfoDouble(s,SYMBOL_ASK);
   double sl=(gStop[i]>0)?ask-gStop[i]*a:0.0, tp=(gTp[i]>0)?ask+gTp[i]*a:0.0;
   trade.SetExpertMagicNumber(gMagic[i]);
   if(trade.Buy(lots,s,0.0,sl,tp,gSetup[i])) gEntryBar[i]=gBarCount[i]; }

void Trail(int i){ if(gTrail[i]<=0 || !HasPos(i)) return;
   string s=gSym[i]; double a=Atr(i), bid=SymbolInfoDouble(s,SYMBOL_BID), nsl=bid-gTrail[i]*a;
   for(int p=PositionsTotal()-1;p>=0;p--){ ulong tk=PositionGetTicket(p);
      if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==s&&PositionGetInteger(POSITION_MAGIC)==gMagic[i]){
         double cur=PositionGetDouble(POSITION_SL); if(nsl>cur) trade.PositionModify(tk,nsl,PositionGetDouble(POSITION_TP)); } } }

void Manage(int i){ if(!HasPos(i)){ gEntryBar[i]=-1; return; }
   Trail(i);
   if(gEntryBar[i]>=0 && (gBarCount[i]-gEntryBar[i])>=Hold) CloseSlot(i); }

void OnTick()
{
   for(int i=0;i<gN;i++)
   {
      datetime t=iTime(gSym[i],PERIOD_D1,0);
      if(t!=gLastBar[i]){ gLastBar[i]=t; gBarCount[i]++; Manage(i); if(!HasPos(i) && Signal(i)==1) Enter(i); }
      else Trail(i);
   }
}
//+------------------------------------------------------------------+
