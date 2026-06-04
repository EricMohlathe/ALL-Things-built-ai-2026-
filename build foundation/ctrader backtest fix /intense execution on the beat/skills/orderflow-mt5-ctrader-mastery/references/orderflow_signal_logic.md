# Order-Flow Signal Logic — Detection Pseudocode → MQL5 + C# cAlgo

Each detector is presented in three forms: (a) the principle, (b) MQL5 inline, (c) cAlgo C# inline. Drop these into the `// SIGNAL LOGIC` region of the templates.

## A. Absorption (per-candle, signed-volume approximation)

**Principle.** High one-sided aggression + opposing close = absorbed.

### MQL5
```mql5
bool IsAbsorptionBearish(int shift, double minDelta, double maxRange)
{
   double o = iOpen(_Symbol,_Period,shift);
   double c = iClose(_Symbol,_Period,shift);
   double h = iHigh(_Symbol,_Period,shift);
   double l = iLow(_Symbol,_Period,shift);
   long   v = iVolume(_Symbol,_Period,shift);
   double signedDelta = (c >= o) ? (double)v : -(double)v;     // approximation
   double range       = (h - l);
   // strong + delta but bearish close, small range = sellers absorbed buyers
   return (signedDelta >= minDelta && c < o && range <= maxRange);
}
```

### cAlgo C#
```csharp
bool IsAbsorptionBearish(int shift, double minDelta, double maxRange)
{
    var b = Bars[Bars.Count - 1 - shift];
    double signedDelta = (b.Close >= b.Open) ? b.TickVolume : -b.TickVolume;
    double range       = b.High - b.Low;
    return (signedDelta >= minDelta && b.Close < b.Open && range <= maxRange);
}
```

> If the broker streams real bid/ask volume (rare on retail), replace `signedDelta` with the per-tick classification from `orderflow_primitives.md §1`.

## B. Exhaustion (declining volume + delta with new extremes)

### MQL5
```mql5
bool IsBullExhaustion(int n)
{
   if(Bars(_Symbol,_Period) < n+2) return false;
   for(int i=1;i<n;i++)
   {
      if(iHigh(_Symbol,_Period,i)   <= iHigh(_Symbol,_Period,i+1))   return false; // higher highs
      if(iVolume(_Symbol,_Period,i) >= iVolume(_Symbol,_Period,i+1)) return false; // declining volume
   }
   return true;
}
```

### cAlgo C#
```csharp
bool IsBullExhaustion(int n)
{
    if (Bars.Count < n + 2) return false;
    for (int i = 1; i < n; i++)
    {
        var cur  = Bars[Bars.Count - 1 - i];
        var prev = Bars[Bars.Count - 1 - (i + 1)];
        if (cur.High <= prev.High) return false;
        if (cur.TickVolume >= prev.TickVolume) return false;
    }
    return true;
}
```

## C. Initiative Auction

### MQL5
```mql5
bool IsBullInitiative(int shift, double avgVol, double volMult, double minBodyRatio)
{
   double o = iOpen(_Symbol,_Period,shift);
   double c = iClose(_Symbol,_Period,shift);
   double h = iHigh(_Symbol,_Period,shift);
   double l = iLow(_Symbol,_Period,shift);
   long   v = iVolume(_Symbol,_Period,shift);
   if((double)v < avgVol*volMult) return false;
   double body = MathAbs(c-o), range = h-l;
   if(range <= 0 || body/range < minBodyRatio) return false;
   return (c > o); // bullish close + high vol + dominant body
}
```

### cAlgo C#
```csharp
bool IsBullInitiative(int shift, double avgVol, double volMult, double minBodyRatio)
{
    var b = Bars[Bars.Count - 1 - shift];
    if (b.TickVolume < avgVol * volMult) return false;
    double body = Math.Abs(b.Close - b.Open);
    double range = b.High - b.Low;
    if (range <= 0 || body / range < minBodyRatio) return false;
    return b.Close > b.Open;
}
```

## D. Book Sweep

Tick-driven detection (depth-of-market required).

### MQL5 (OnBookEvent + ring buffer)
```mql5
struct BookEvt { datetime t; double price; long vol; bool consumed; };
BookEvt sweepBuf[64]; int sweepIdx = 0;

void OnBookEvent(const string &sym)
{
   if(sym!=_Symbol) return;
   MqlBookInfo book[]; if(!MarketBookGet(_Symbol, book)) return;
   // Compare with prior snapshot, log levels removed in last 1s into sweepBuf...
}

bool IsBullSweep(int minLevels, int withinMs)
{
   datetime cutoff = TimeCurrent() - 1; // adjust for tick-precision
   int hits = 0;
   for(int i=0;i<ArraySize(sweepBuf);i++)
      if(sweepBuf[i].consumed && sweepBuf[i].t >= cutoff) hits++;
   return hits >= minLevels;
}
```

### cAlgo C#
```csharp
private readonly Queue<DepthEvent> _sweepBuf = new Queue<DepthEvent>(64);

protected override void OnStart()
{
    Symbol.MarketDepth.Updated += OnDepthUpdated;
}

private void OnDepthUpdated()
{
    // Compare current vs last snapshot, log consumed asks/bids with timestamp...
}

bool IsBullSweep(int minLevels, int withinMs)
{
    var cutoff = Server.Time.AddMilliseconds(-withinMs);
    return _sweepBuf.Count(d => d.Consumed && d.Time >= cutoff) >= minLevels;
}
```

## E. Delta Divergence

### MQL5
```mql5
double cvd[]; // sized to bar count, recomputed on bar close

bool IsBearDelta Divergence(int lookback)
{
   int last = 1;
   double pHigh = iHigh(_Symbol,_Period,last);
   double dHigh = cvd[ArraySize(cvd)-1-last];
   for(int i=last+1;i<=lookback;i++)
   {
      double pi = iHigh(_Symbol,_Period,i);
      double di = cvd[ArraySize(cvd)-1-i];
      if(pi > pHigh && di < dHigh) return true;
   }
   return false;
}
```

### cAlgo C#
```csharp
private readonly List<double> _cvd = new List<double>();

bool IsBearDeltaDivergence(int lookback)
{
    if (Bars.Count < lookback + 2) return false;
    var pHigh = Bars[Bars.Count - 2].High;
    var dHigh = _cvd[_cvd.Count - 2];
    for (int i = 3; i <= lookback; i++)
    {
        var pi = Bars[Bars.Count - i].High;
        var di = _cvd[_cvd.Count - i];
        if (pi > pHigh && di < dHigh) return true;
    }
    return false;
}
```

## F. POC magnetism

After computing the developing-session POC, fire a signal whenever price drifts ≥ N ticks below the POC during balance phase, biasing long toward the POC.

## G. Stop run / Liquidity grab

`(High[1] > swingHigh && Close[1] < swingHigh && DeltaDivergence(...))` for bearish.
Mirror for bullish (sweep of swingLow + bullish CVD divergence).

## Confluence stacking

Each signal returns `0..1` confidence. Final entry confidence = weighted sum:
```
final = w_abs*abs + w_init*init + w_div*div + w_sweep*sweep + w_phase*amtPhaseFit
```
Trigger entries only when `final >= entryThreshold` (default 0.6).
