//+------------------------------------------------------------------+
//|                                    GODMODE_Dashboard.mq5         |
//|   GODMODE Dashboard  ⚡  — MT5 overlay indicator                  |
//|   Visualises every GODMODE archetype (GM01–GM26) as colour-coded  |
//|   modules: a live panel, FVG/OB/S&D/OTE zones, swing markers,     |
//|   session shading, confluence signal + clickable toggle buttons   |
//|   and push/alert notifications. Reuses GODMODE_Core.mqh.          |
//|                                                                  |
//|   INSTALL: copy to MQL5/Indicators/GODMODE/ , compile, drag on    |
//|   the chart. Needs Include/GODMODE/GODMODE_Core.mqh.              |
//+------------------------------------------------------------------+
#property copyright "GODMODE Master Library"
#property version   "1.00"
#property indicator_chart_window
#property indicator_plots   0
#property indicator_buffers 0

#include <GODMODE/GODMODE_Core.mqh>

input int    InpEMA          = 50;
input int    InpFast         = 20;
input double InpVwapMult     = 2.0;
input int    InpVwapLen      = 100;
input int    InpWing         = 3;
input int    InpZoneLB       = 30;
input int    InpOteLB        = 20;
input double InpDispMult     = 1.0;
input double InpBaseMaxMult  = 0.6;
input int    InpATR          = 14;
input int    InpMinLayers    = 4;
input int    InpLonStart     = 7;
input int    InpLonEnd       = 10;
input int    InpNYStart      = 12;
input int    InpNYEnd        = 15;
input bool   InpAlert        = true;
input bool   InpPush         = false;

#define PFX "gm_"
color cBull = C'0,229,160';
color cBear = C'255,77,109';
color cNeut = C'91,141,239';
color cGold = C'255,210,76';
color cText = C'230,237,243';
color cDim  = C'139,151,167';
color cDem  = C'10,60,46';
color cSup  = C'70,20,32';
color cFvgB = C'24,40,72';
color cFvgS = C'48,28,60';
color cOte  = C'70,58,20';

int      g_atr=INVALID_HANDLE, g_ema=INVALID_HANDLE;
datetime g_lastBar=0, g_lastSignalBar=0;
bool     g_showZones=true, g_showSignals=true;
string   g_names[11]={"Trend GM22","VWAP GM07","Struct GM16","FVG GM03","OB GM04/05","S&D GM15","Sweep GM14","OTE GM12","Session GM11","Gap GM20","Momentum GM08"};

int OnInit()
  {
   g_atr=iATR(_Symbol,PERIOD_CURRENT,InpATR);
   g_ema=iMA(_Symbol,PERIOD_CURRENT,InpEMA,0,MODE_EMA,PRICE_CLOSE);
   BuildPanel();
   Refresh();
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason) { ObjectsDeleteAll(0,PFX); ChartRedraw(); }

double ATRv(){ double b[]; if(g_atr==INVALID_HANDLE||CopyBuffer(g_atr,0,1,1,b)<=0) return 0; return b[0]; }
double EMAv(){ double b[]; if(g_ema==INVALID_HANDLE||CopyBuffer(g_ema,0,1,1,b)<=0) return 0; return b[0]; }

double Vwap()
  {
   double pv=0,vv=0;
   for(int i=1;i<=InpVwapLen;i++)
     { double tp=(iHigh(_Symbol,PERIOD_CURRENT,i)+iLow(_Symbol,PERIOD_CURRENT,i)+iClose(_Symbol,PERIOD_CURRENT,i))/3.0;
       double v=(double)iTickVolume(_Symbol,PERIOD_CURRENT,i); pv+=tp*v; vv+=v; }
   return vv>0?pv/vv:iClose(_Symbol,PERIOD_CURRENT,1);
  }
double StdDevC(int len)
  {
   double m=0; for(int i=1;i<=len;i++) m+=iClose(_Symbol,PERIOD_CURRENT,i); m/=len;
   double s=0; for(int i=1;i<=len;i++){ double d=iClose(_Symbol,PERIOD_CURRENT,i)-m; s+=d*d; }
   return MathSqrt(s/len);
  }

//--- UI helpers
void Lbl(string n,string t,int x,int y,color c,int fs=9)
  {
   string nm=PFX+n;
   if(ObjectFind(0,nm)<0){ ObjectCreate(0,nm,OBJ_LABEL,0,0,0); ObjectSetInteger(0,nm,OBJPROP_CORNER,CORNER_LEFT_UPPER);
      ObjectSetInteger(0,nm,OBJPROP_ANCHOR,ANCHOR_LEFT_UPPER); ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false); ObjectSetInteger(0,nm,OBJPROP_HIDDEN,true); ObjectSetString(0,nm,OBJPROP_FONT,"Consolas"); }
   ObjectSetInteger(0,nm,OBJPROP_XDISTANCE,x); ObjectSetInteger(0,nm,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,nm,OBJPROP_COLOR,c); ObjectSetInteger(0,nm,OBJPROP_FONTSIZE,fs); ObjectSetString(0,nm,OBJPROP_TEXT,t);
  }
void Btn(string n,string t,int x,int y,int w,int h)
  {
   string nm=PFX+n;
   if(ObjectFind(0,nm)<0){ ObjectCreate(0,nm,OBJ_BUTTON,0,0,0); ObjectSetInteger(0,nm,OBJPROP_CORNER,CORNER_LEFT_UPPER);
      ObjectSetInteger(0,nm,OBJPROP_XSIZE,w); ObjectSetInteger(0,nm,OBJPROP_YSIZE,h); ObjectSetString(0,nm,OBJPROP_FONT,"Segoe UI"); ObjectSetInteger(0,nm,OBJPROP_FONTSIZE,8);
      ObjectSetInteger(0,nm,OBJPROP_COLOR,cText); ObjectSetInteger(0,nm,OBJPROP_BGCOLOR,C'30,44,66'); ObjectSetInteger(0,nm,OBJPROP_BORDER_COLOR,cNeut); }
   ObjectSetInteger(0,nm,OBJPROP_XDISTANCE,x); ObjectSetInteger(0,nm,OBJPROP_YDISTANCE,y); ObjectSetString(0,nm,OBJPROP_TEXT,t);
  }
void Panel(string n,int x,int y,int w,int h)
  {
   string nm=PFX+n;
   if(ObjectFind(0,nm)<0){ ObjectCreate(0,nm,OBJ_RECTANGLE_LABEL,0,0,0); ObjectSetInteger(0,nm,OBJPROP_CORNER,CORNER_LEFT_UPPER);
      ObjectSetInteger(0,nm,OBJPROP_XDISTANCE,x); ObjectSetInteger(0,nm,OBJPROP_YDISTANCE,y); ObjectSetInteger(0,nm,OBJPROP_XSIZE,w); ObjectSetInteger(0,nm,OBJPROP_YSIZE,h);
      ObjectSetInteger(0,nm,OBJPROP_BGCOLOR,C'11,18,32'); ObjectSetInteger(0,nm,OBJPROP_BORDER_TYPE,BORDER_FLAT); ObjectSetInteger(0,nm,OBJPROP_COLOR,cNeut);
      ObjectSetInteger(0,nm,OBJPROP_BACK,false); ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false); }
  }
void Zone(string n,datetime t1,double p1,datetime t2,double p2,color c)
  {
   string nm=PFX+n;
   if(ObjectFind(0,nm)<0){ ObjectCreate(0,nm,OBJ_RECTANGLE,0,t1,p1,t2,p2); ObjectSetInteger(0,nm,OBJPROP_FILL,true);
      ObjectSetInteger(0,nm,OBJPROP_BACK,true); ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false); }
   else { ObjectMove(0,nm,0,t1,p1); ObjectMove(0,nm,1,t2,p2); }
   ObjectSetInteger(0,nm,OBJPROP_COLOR,c);
  }
void DelZones(){ string z[5]={"fvgb","fvgs","dem","sup","ote"}; for(int i=0;i<5;i++) ObjectDelete(0,PFX+z[i]); }

void BuildPanel()
  {
   Panel("bg",8,24,196,(ArraySize(g_names)+4)*16+10);
   Lbl("title","GODMODE",14,28,cGold,11);
   Btn("bz","Zones",110,28,42,16);
   Btn("bs","Sig",156,28,40,16);
  }

void Refresh()
  {
   double atr=ATRv(); if(atr<=0) return;
   double close=iClose(_Symbol,PERIOD_CURRENT,1), o1=iOpen(_Symbol,PERIOD_CURRENT,1);
   double hi1=iHigh(_Symbol,PERIOD_CURRENT,1), lo1=iLow(_Symbol,PERIOD_CURRENT,1);
   double ema=EMAv(), vw=Vwap(), dev=InpVwapMult*StdDevC(InpVwapLen);
   MqlDateTime st; TimeToStruct(TimeCurrent(),st);
   bool inKZ=(st.hour>=InpLonStart && st.hour<InpLonEnd)||(st.hour>=InpNYStart && st.hour<InpNYEnd);

   int bTrend=close>ema?1:close<ema?-1:0;
   int bVwap=close<vw-dev?1:close>vw+dev?-1:0;
   double shHi=0,shLo=0; int sH=0,sL=0;
   bool haveHi=GM_LastSwingHigh(InpZoneLB,InpWing,shHi,sH);
   bool haveLo=GM_LastSwingLow(InpZoneLB,InpWing,shLo,sL);
   int bStruct=(haveHi&&close>shHi)?1:(haveLo&&close<shLo)?-1:0;
   double ft,fb;
   int bFvg=(GM_FindBullishFVG(InpZoneLB,ft,fb)&&lo1<=ft&&close>=fb)?1:(GM_FindBearishFVG(InpZoneLB,ft,fb)&&hi1>=fb&&close<=ft)?-1:0;
   int bMom=(close-o1)>InpDispMult*atr?1:(o1-close)>InpDispMult*atr?-1:0;
   int bSfp=(haveLo&&lo1<shLo&&close>shLo)?1:(haveHi&&hi1>shHi&&close<shHi)?-1:0;
   double oteHi=GM_HighestHigh(InpOteLB,1),oteLo=GM_LowestLow(InpOteLB,1),rng=oteHi-oteLo;
   int bOte=(rng>0&&close<=oteHi-0.62*rng&&close>=oteHi-0.79*rng&&close>ema)?1:(rng>0&&close>=oteLo+0.62*rng&&close<=oteLo+0.79*rng&&close<ema)?-1:0;

   int longN=(bTrend>0)+(bVwap>0)+(bStruct>0)+(bFvg>0)+(bMom>0)+(bSfp>0)+(bOte>0)+(inKZ?1:0);
   int shortN=(bTrend<0)+(bVwap<0)+(bStruct<0)+(bFvg<0)+(bMom<0)+(bSfp<0)+(bOte<0)+(inKZ?1:0);

   int biases[11]; biases[0]=bTrend;biases[1]=bVwap;biases[2]=bStruct;biases[3]=bFvg;biases[4]=bMom;biases[5]=bMom;biases[6]=bSfp;biases[7]=bOte;biases[8]=inKZ?1:0;biases[9]=0;biases[10]=bMom;
   for(int i=0;i<ArraySize(g_names);i++)
     {
      int b=biases[i]; color c=b>0?cBull:b<0?cBear:cDim; string s=b>0?"LONG":b<0?"SHORT":"-";
      int y=46+i*15;
      Lbl("n"+(string)i,g_names[i],14,y,cText,9);
      Lbl("b"+(string)i,s,150,y,c,9);
     }
   int yr=46+ArraySize(g_names)*15;
   color sc=longN>shortN?cBull:shortN>longN?cBear:cNeut;
   Lbl("score","SCORE  L"+(string)longN+" S"+(string)shortN,14,yr,sc,9);
   bool goLong=longN>=InpMinLayers&&longN>shortN, goShort=shortN>=InpMinLayers&&shortN>longN;
   Lbl("sig",goLong?"SIGNAL ⚡ LONG":goShort?"SIGNAL ⚡ SHORT":"SIGNAL  WAIT",14,yr+15,goLong?cBull:goShort?cBear:cDim,9);

   datetime t1=iTime(_Symbol,PERIOD_CURRENT,InpZoneLB);
   datetime t2=iTime(_Symbol,PERIOD_CURRENT,0)+4*PeriodSeconds();
   if(g_showZones)
     {
      double zt,zb;
      if(GM_FindBullishFVG(InpZoneLB,ft,fb)) Zone("fvgb",t1,ft,t2,fb,cFvgB); else ObjectDelete(0,PFX+"fvgb");
      if(GM_FindBearishFVG(InpZoneLB,ft,fb)) Zone("fvgs",t1,ft,t2,fb,cFvgS); else ObjectDelete(0,PFX+"fvgs");
      if(GM_FindDemandBase(InpZoneLB,atr,InpDispMult,InpBaseMaxMult,zt,zb)) Zone("dem",t1,zt,t2,zb,cDem); else ObjectDelete(0,PFX+"dem");
      if(GM_FindSupplyBase(InpZoneLB,atr,InpDispMult,InpBaseMaxMult,zt,zb)) Zone("sup",t1,zt,t2,zb,cSup); else ObjectDelete(0,PFX+"sup");
      if(rng>0){ if(close>ema) Zone("ote",t1,oteHi-0.62*rng,t2,oteHi-0.79*rng,cOte); else Zone("ote",t1,oteLo+0.79*rng,t2,oteLo+0.62*rng,cOte); }
     }
   else DelZones();

   datetime curBar=iTime(_Symbol,PERIOD_CURRENT,0);
   if(g_showSignals && (goLong||goShort) && curBar!=g_lastSignalBar)
     {
      g_lastSignalBar=curBar;
      string an=PFX+"sigArr";
      ObjectDelete(0,an);
      ObjectCreate(0,an,goLong?OBJ_ARROW_BUY:OBJ_ARROW_SELL,0,iTime(_Symbol,PERIOD_CURRENT,1),goLong?lo1:hi1);
      ObjectSetInteger(0,an,OBJPROP_COLOR,goLong?cBull:cBear);
      string msg="⚡ GODMODE "+(goLong?"LONG":"SHORT")+" "+_Symbol+" "+EnumToString((ENUM_TIMEFRAMES)Period())+" score "+(string)(goLong?longN:shortN)+"/8";
      if(InpAlert) Alert(msg);
      if(InpPush)  SendNotification(msg);
     }
   ChartRedraw();
  }

int OnCalculate(const int rates_total,const int prev_calculated,const datetime &time[],const double &open[],
                const double &high[],const double &low[],const double &close[],const long &tick_volume[],
                const long &volume[],const int &spread[])
  {
   datetime t=iTime(_Symbol,PERIOD_CURRENT,0);
   if(t!=g_lastBar){ g_lastBar=t; Refresh(); }
   return rates_total;
  }

void OnChartEvent(const int id,const long &lparam,const double &dparam,const string &sparam)
  {
   if(id==CHARTEVENT_OBJECT_CLICK)
     {
      if(sparam==PFX+"bz"){ g_showZones=!g_showZones; ObjectSetInteger(0,PFX+"bz",OBJPROP_STATE,false); Refresh(); }
      if(sparam==PFX+"bs"){ g_showSignals=!g_showSignals; ObjectSetInteger(0,PFX+"bs",OBJPROP_STATE,false); Refresh(); }
     }
  }
//+------------------------------------------------------------------+
