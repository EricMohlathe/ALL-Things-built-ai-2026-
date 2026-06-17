//+------------------------------------------------------------------+
//|  GODMODE UNIVERSAL CONTROLLER — full roster, all setups (MT5)     |
//|------------------------------------------------------------------|
//|  ONE EA running the ENTIRE validated D1 roster — every setup,     |
//|  every market, long AND short — from one editable roster. A        |
//|  portfolio of 60-120 validated edges aggregates to several         |
//|  trades/DAY; each individual edge trades ~weekly. All OOS-validated.|
//|                                                                   |
//|  Setups: SPRING UPTHRUST SOS STACKBULL AMD LIQSWEEP ORB POORHL     |
//|          TSMOM RSI2                                                |
//|  Slot:  SYMBOL:SETUP:stopATR:tpATR:trailATR  (slots split by ;)   |
//|  EDIT symbols to your broker. Attach to ONE D1 chart. Truth = MT5  |
//|  Strategy Tester per symbol.                                      |
//+------------------------------------------------------------------+
#property copyright "GODMODE OS"
#property version   "1.00"
#property strict
#include <Trade/Trade.mqh>

input string RosterStr  = "XAUUSD:AMD:3:1:0;XAGUSD:SPRING:0:0:0;XAUUSD:STACKBULL:3:1:0;DOGEUSD:STACKBULL:4:1.5:0;JP225:SOS:3:1:0;NATGAS:SPRING:3:1:0;NAS100:SOS:2:4:3;US500:SOS:3:1:0;US30:AMD:4:1.5:0;USOIL:AMD:2.5:0.8:0;XPTUSD:LIQSWEEP:2.5:0.8:0;XAGUSD:AMD:2.5:0.8:0;CHFJPY:SPRING:0:0:0;EURJPY:SPRING:0:0:0;US30:SPRING:4:1.5:0;SOLUSD:SOS:2:0:2.5;DOGEUSD:SOS:0:0:0;COPPER:STACKBULL:2.5:0.8:0;JP225:SPRING:0:0:0;US30:SOS:0:0:0;USDZAR:SPRING:0:0:0;EURCHF:UPTHRUST:3:1:0;AUDCHF:ORB:4:1.5:0;XAUUSD:SPRING:3:1:0;JP225:AMD:0:0:0;CADCHF:UPTHRUST:4:1.5:0;US500:RSI2:0:0:0;JP225:RSI2:0:0:0;NAS100:RSI2:0:0:0;XPTUSD:STACKBULL:3:1:0;JP225:STACKBULL:0:0:0;NATGAS:RSI2:3:1:0;NZDJPY:SPRING:1.5:3:2;GBPJPY:SPRING:0:0:0;GBPCHF:UPTHRUST:0:0:0;BNBUSD:SOS:0:0:0;DOGEUSD:ORB:0:0:0;XPTUSD:UPTHRUST:2.5:0.8:0;ETHUSD:STACKBULL:2:4:3;WHEAT:TSMOM:1.5:3:2;USDZAR:LIQSWEEP:2.5:0.8:0;US30:RSI2:0:0:0;USDSEK:TSMOM:2.5:0.8:0;UKOIL:SOS:2:4:3;ETHUSD:SOS:1.5:3:2;NAS100:TSMOM:0:0:0;XAGUSD:SOS:1.5:3:2;AUDCHF:TSMOM:2.5:0.8:0;NAS100:POORHL:3:6:0;GBPNZD:SPRING:1.5:3:2;LTCUSD:AMD:4:1.5:0;LINKUSD:STACKBULL:0:0:0;XRPUSD:SOS:0:0:0;USOIL:TSMOM:2:0:2.5;US500:SPRING:4:1.5:0;USDSGD:TSMOM:2:4:3;XRPUSD:STACKBULL:2.5:0.8:0;CHFJPY:TSMOM:2.5:0.8:0;NAS100:STACKBULL:3:6:0;NAS100:SPRING:4:1.5:0;SUGAR:SOS:1.5:3:2;AUDCHF:UPTHRUST:0:0:0;EURNZD:TSMOM:1.5:3:2;EURGBP:SPRING:0:0:0;JP225:ORB:3:1:0;BTCUSD:SOS:1:2:1.5;US2000:AMD:1:2:1.5;CHFJPY:ORB:3:1:0;ADAUSD:RSI2:4:1.5:0;EURJPY:ORB:1:2:1.5;BTCUSD:ORB:2.5:0.8:0;XAUUSD:POORHL:2:0:2.5;SOLUSD:ORB:0:0:0;CORN:ORB:2.5:0.8:0;NZDUSD:UPTHRUST:2.5:0.8:0;US500:ORB:2:4:3;EURJPY:TSMOM:3:6:0;COPPER:SOS:2:4:3;USDZAR:TSMOM:2.5:0.8:0;USOIL:SOS:2:0:2.5;EURNZD:LIQSWEEP:2:4:3;DOTUSD:ORB:2.5:0.8:0;DOTUSD:UPTHRUST:1:2:1.5;US30:POORHL:2:4:3;AUDUSD:LIQSWEEP:3:1:0;BNBUSD:ORB:0:0:0;US2000:RSI2:1.5:3:2;AVAXUSD:ORB:0:0:0;XAUUSD:SOS:2:4:3;AVAXUSD:POORHL:1.5:3:2;US30:STACKBULL:3:6:0;ETHUSD:ORB:3:1:0;US500:POORHL:2:0:2.5";
input int    LB         = 20;
input double K          = 1.0;
input int    Hold       = 10;
input double RiskPct    = 0.5;
input double SizingATR  = 3.0;
input int    AtrPeriod  = 14;
input double RsiBuy     = 10.0;
input double RsiExit    = 60.0;
input long   BaseMagic  = 815000;

CTrade   trade;
string   gSym[], gSetup[];
double   gStop[], gTp[], gTrail[];
int      gAtr[], gSma50[], gSma200[], gRsi[], gEntryBar[], gBarCount[];
long     gMagic[];
datetime gLastBar[];
int      gN = 0;

int OnInit()
{
   string slots[]; int ns = StringSplit(RosterStr, ';', slots);
   for(int i=0;i<ns;i++)
   {
      string f[]; if(StringSplit(slots[i], ':', f) < 5) continue;
      string sym=f[0]; StringTrimLeft(sym); StringTrimRight(sym);
      if(!SymbolSelect(sym,true)){ Print("skip ",sym); continue; }
      string st=f[1]; StringTrimLeft(st); StringTrimRight(st); StringToUpper(st);
      int hA=iATR(sym,PERIOD_D1,AtrPeriod); if(hA==INVALID_HANDLE) continue;
      int h50=(st=="ORB")?iMA(sym,PERIOD_D1,50,0,MODE_SMA,PRICE_CLOSE):INVALID_HANDLE;
      int h200=(st=="RSI2")?iMA(sym,PERIOD_D1,200,0,MODE_SMA,PRICE_CLOSE):INVALID_HANDLE;
      int hR=(st=="RSI2")?iRSI(sym,PERIOD_D1,2,PRICE_CLOSE):INVALID_HANDLE;
      int k=gN; gN++;
      ArrayResize(gSym,gN);ArrayResize(gSetup,gN);ArrayResize(gStop,gN);ArrayResize(gTp,gN);ArrayResize(gTrail,gN);
      ArrayResize(gAtr,gN);ArrayResize(gSma50,gN);ArrayResize(gSma200,gN);ArrayResize(gRsi,gN);
      ArrayResize(gEntryBar,gN);ArrayResize(gBarCount,gN);ArrayResize(gMagic,gN);ArrayResize(gLastBar,gN);
      gSym[k]=sym; gSetup[k]=st; gStop[k]=StringToDouble(f[2]); gTp[k]=StringToDouble(f[3]); gTrail[k]=StringToDouble(f[4]);
      gAtr[k]=hA; gSma50[k]=h50; gSma200[k]=h200; gRsi[k]=hR;
      gEntryBar[k]=-1; gBarCount[k]=0; gMagic[k]=BaseMagic+k; gLastBar[k]=0;
   }
   PrintFormat("GODMODE Universal Controller — %d slots.", gN);
   return(gN>0?INIT_SUCCEEDED:INIT_FAILED);
}
void OnDeinit(const int r){ for(int i=0;i<gN;i++){ IndicatorRelease(gAtr[i]);
   if(gSma50[i]!=INVALID_HANDLE) IndicatorRelease(gSma50[i]);
   if(gSma200[i]!=INVALID_HANDLE) IndicatorRelease(gSma200[i]);
   if(gRsi[i]!=INVALID_HANDLE) IndicatorRelease(gRsi[i]); } }

double Bf(int h,int sh){ double b[]; if(h!=INVALID_HANDLE && CopyBuffer(h,0,sh,1,b)==1) return b[0]; return EMPTY_VALUE; }
double Atr(int i){ return Bf(gAtr[i],1); }
long   TV(string s,int sh){ long v[]; if(CopyTickVolume(s,PERIOD_D1,sh,1,v)==1) return v[0]; return 0; }
double D(string s,int sh){ double sg=(iClose(s,PERIOD_D1,sh)>=iOpen(s,PERIOD_D1,sh))?1.0:-1.0; return sg*(double)TV(s,sh); }
double MeanD(string s,int n){ double sum=0; for(int j=1;j<=n;j++) sum+=D(s,j); return sum/n; }
double LowC(string s,int f,int n){ double m=DBL_MAX; for(int i=f;i<f+n;i++){ double c=iClose(s,PERIOD_D1,i); if(c<m) m=c; } return m; }
double HighC(string s,int f,int n){ double m=-DBL_MAX; for(int i=f;i<f+n;i++){ double c=iClose(s,PERIOD_D1,i); if(c>m) m=c; } return m; }

int Signal(int i)
{
   string s=gSym[i]; double a=Atr(i); if(a<=0||a==EMPTY_VALUE) return 0;
   if(Bars(s,PERIOD_D1)<LB+6) return 0;
   double c1=iClose(s,PERIOD_D1,1),c2=iClose(s,PERIOD_D1,2),o1=iOpen(s,PERIOD_D1,1);
   double h1=iHigh(s,PERIOD_D1,1),l1=iLow(s,PERIOD_D1,1),h2=iHigh(s,PERIOD_D1,2),l2=iLow(s,PERIOD_D1,2);
   double rng=h1-l1; if(rng<=0) rng=a;
   string st=gSetup[i];
   if(st=="SPRING")    return (l1<LowC(s,2,LB) && c1>LowC(s,2,LB))?1:0;
   if(st=="UPTHRUST")  return (h1>HighC(s,2,LB) && c1<HighC(s,2,LB))?-1:0;
   if(st=="SOS")       return (rng>K*a && c1>o1 && D(s,1)>0 && c1>=HighC(s,2,LB))?1:0;
   if(st=="STACKBULL") return (D(s,1)>0 && D(s,2)>0 && D(s,3)>0 && D(s,1)>K*MathAbs(MeanD(s,LB)))?1:0;
   if(st=="AMD")       return (l2<LowC(s,3,LB) && c1>c2 && rng>K*a && D(s,1)>0)?1:0;
   if(st=="LIQSWEEP"){ if(l1<LowC(s,2,LB) && c1>l1+0.5*rng) return 1; if(h1>HighC(s,2,LB) && c1<h1-0.5*rng) return -1; return 0; }
   if(st=="ORB"){ double sma=Bf(gSma50[i],1),buf=K*a*0.2; if(sma==EMPTY_VALUE) return 0;
                  if(c1>HighC(s,2,LB)+buf && c1>sma) return 1; if(c1<LowC(s,2,LB)-buf && c1<sma) return -1; return 0; }
   if(st=="POORHL"){ if(MathAbs(l1-l2)<0.25*a && D(s,1)>0) return 1; if(MathAbs(h1-h2)<0.25*a && D(s,1)<0) return -1; return 0; }
   if(st=="TSMOM"){ double cl=iClose(s,PERIOD_D1,LB+1); return (c1>cl)?1:((c1<cl)?-1:0); }
   if(st=="RSI2"){ double r=Bf(gRsi[i],1),sma=Bf(gSma200[i],1); if(r==EMPTY_VALUE||sma==EMPTY_VALUE) return 0; return (r<RsiBuy && c1>sma)?1:0; }
   return 0;
}

int CurDir(int i){ for(int p=PositionsTotal()-1;p>=0;p--){ ulong tk=PositionGetTicket(p);
   if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==gSym[i]&&PositionGetInteger(POSITION_MAGIC)==gMagic[i])
      return (PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY)?1:-1; } return 0; }
void CloseSlot(int i){ for(int p=PositionsTotal()-1;p>=0;p--){ ulong tk=PositionGetTicket(p);
   if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==gSym[i]&&PositionGetInteger(POSITION_MAGIC)==gMagic[i]) trade.PositionClose(tk); } }

double Lots(string s,double stopDist){
   double ts=SymbolInfoDouble(s,SYMBOL_TRADE_TICK_SIZE),tv=SymbolInfoDouble(s,SYMBOL_TRADE_TICK_VALUE);
   if(ts<=0||tv<=0||stopDist<=0) return SymbolInfoDouble(s,SYMBOL_VOLUME_MIN);
   double lots=AccountInfoDouble(ACCOUNT_EQUITY)*(RiskPct/100.0)/((stopDist/ts)*tv);
   double step=SymbolInfoDouble(s,SYMBOL_VOLUME_STEP),mn=SymbolInfoDouble(s,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(s,SYMBOL_VOLUME_MAX);
   if(step>0) lots=MathFloor(lots/step)*step; return MathMax(mn,MathMin(mx,lots)); }

void Enter(int i,int dir){
   string s=gSym[i]; double a=Atr(i); if(a<=0) return;
   double stopDist=(gStop[i]>0?gStop[i]:SizingATR)*a, lots=Lots(s,stopDist); if(lots<=0) return;
   trade.SetExpertMagicNumber(gMagic[i]);
   if(dir>0){ double ask=SymbolInfoDouble(s,SYMBOL_ASK);
      double sl=(gStop[i]>0)?ask-stopDist:0.0, tp=(gTp[i]>0)?ask+gTp[i]*a:0.0;
      if(trade.Buy(lots,s,0.0,sl,tp,gSetup[i])) gEntryBar[i]=gBarCount[i]; }
   else{ double bid=SymbolInfoDouble(s,SYMBOL_BID);
      double sl=(gStop[i]>0)?bid+stopDist:0.0, tp=(gTp[i]>0)?bid-gTp[i]*a:0.0;
      if(trade.Sell(lots,s,0.0,sl,tp,gSetup[i])) gEntryBar[i]=gBarCount[i]; } }

void Trail(int i){ if(gTrail[i]<=0) return; int dir=CurDir(i); if(dir==0) return;
   string s=gSym[i]; double a=Atr(i);
   for(int p=PositionsTotal()-1;p>=0;p--){ ulong tk=PositionGetTicket(p);
      if(PositionSelectByTicket(tk)&&PositionGetString(POSITION_SYMBOL)==s&&PositionGetInteger(POSITION_MAGIC)==gMagic[i]){
         double cur=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);
         if(dir>0){ double n=SymbolInfoDouble(s,SYMBOL_BID)-gTrail[i]*a; if(n>cur) trade.PositionModify(tk,n,tp); }
         else     { double n=SymbolInfoDouble(s,SYMBOL_ASK)+gTrail[i]*a; if(cur==0||n<cur) trade.PositionModify(tk,n,tp); } } } }

void Manage(int i){ int dir=CurDir(i); if(dir==0){ gEntryBar[i]=-1; return; }
   Trail(i);
   if(gSetup[i]=="RSI2"){ double r=Bf(gRsi[i],1); if(r!=EMPTY_VALUE && r>RsiExit) CloseSlot(i); return; }
   if(gEntryBar[i]>=0 && (gBarCount[i]-gEntryBar[i])>=Hold) CloseSlot(i); }

void OnTick(){
   for(int i=0;i<gN;i++){
      datetime t=iTime(gSym[i],PERIOD_D1,0);
      if(t!=gLastBar[i]){ gLastBar[i]=t; gBarCount[i]++; Manage(i);
         int dir=CurDir(i), sig=Signal(i);
         if(dir==0){ if(sig!=0) Enter(i,sig); }
         else if(sig!=0 && sig!=dir){ CloseSlot(i); Enter(i,sig); } }
      else Trail(i);
   }
}
//+------------------------------------------------------------------+
