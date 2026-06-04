# cTrader / cAlgo (C#) — Order-Flow Implementation Patterns

Authoritative cAlgo idioms. These mirror `mql5_orderflow_patterns.md` line-for-line so the parity check passes.

## 0. Skeleton

```csharp
using System;
using System.Collections.Generic;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace cAlgo.Robots
{
    [Robot(AccessRights = AccessRights.None, AddIndicators = true)]
    public class OrderFlowBot : Robot
    {
        [Parameter("Magic Number",       DefaultValue = 20260430)]                 public int    InpMagic { get; set; }
        [Parameter("Risk %",             DefaultValue = 0.5,  MinValue = 0.01)]    public double InpRiskPct { get; set; }
        [Parameter("Max Daily Loss %",   DefaultValue = 3.0)]                      public double InpMaxDailyLossPct { get; set; }
        [Parameter("Max Spread (pips)",  DefaultValue = 2.0)]                      public double InpMaxSpread { get; set; }
        [Parameter("Slippage (pips)",    DefaultValue = 1.0)]                      public double InpSlippage { get; set; }
        [Parameter("Session Start (UTC)",DefaultValue =  7)]                       public int    InpSessionStart { get; set; }
        [Parameter("Session End (UTC)",  DefaultValue = 16)]                       public int    InpSessionEnd { get; set; }

        protected override void OnStart()    { Print("OF Bot started"); }
        protected override void OnTick()     { /* tick logic */ }
        protected override void OnBar()      { /* bar-close logic */ }
        protected override void OnStop()     { Print("OF Bot stopped"); }
    }
}
```

## 1. Tick classification

```csharp
double _prevAsk = 0, _prevBid = 0;
double _curDelta = 0;

protected override void OnTick()
{
    if (_prevAsk == 0) { _prevAsk = Symbol.Ask; _prevBid = Symbol.Bid; return; }

    // cAlgo gives no per-tick traded volume — approximate with tick count
    int sign = 0;
    if (Symbol.Ask > _prevAsk)      sign =  1;     // ask lifted
    else if (Symbol.Bid < _prevBid) sign = -1;     // bid hit

    _curDelta += sign;

    _prevAsk = Symbol.Ask;
    _prevBid = Symbol.Bid;
}
```

## 2. CVD per bar

```csharp
List<double> _cvd = new List<double>();
DateTime _lastBarOpen = DateTime.MinValue;

protected override void OnTick()
{
    var b = Bars.LastBar;
    if (b.OpenTime != _lastBarOpen)
    {
        _cvd.Add(0);
        _lastBarOpen = b.OpenTime;
    }
    // classify and add
    int sign = (Symbol.Ask > _prevAsk) ? 1 : (Symbol.Bid < _prevBid ? -1 : 0);
    _cvd[_cvd.Count - 1] += sign;
}
```

## 3. Footprint reconstruction

```csharp
struct FpLevel { public double Price; public long BidVol; public long AskVol; }
List<FpLevel> _curBarFp = new List<FpLevel>();

void AddTickToFootprint(double price, long vol, int signFlag)
{
    double tick = Symbol.TickSize;
    double rounded = Math.Round(price / tick) * tick;
    for (int i = 0; i < _curBarFp.Count; i++)
    {
        if (Math.Abs(_curBarFp[i].Price - rounded) < tick / 2)
        {
            var l = _curBarFp[i];
            if (signFlag > 0) l.AskVol += vol;
            else if (signFlag < 0) l.BidVol += vol;
            _curBarFp[i] = l;
            return;
        }
    }
    _curBarFp.Add(new FpLevel { Price = rounded,
                                BidVol = signFlag < 0 ? vol : 0,
                                AskVol = signFlag > 0 ? vol : 0 });
}
```

## 4. POC + POI

```csharp
(double Poc, double Poi) ComputePocPoi(List<FpLevel> fp)
{
    long maxV = -1, minV = long.MaxValue;
    double poc = 0, poi = 0;
    foreach (var l in fp)
    {
        long t = l.BidVol + l.AskVol;
        if (t > maxV) { maxV = t; poc = l.Price; }
        if (t < minV) { minV = t; poi = l.Price; }
    }
    return (poc, poi);
}
```

## 5. Stacked imbalance

```csharp
bool HasBullStackedImbalance(List<FpLevel> fp, int needed = 3, double ratio = 3.0)
{
    int run = 0;
    for (int i = 1; i < fp.Count; i++)
    {
        if (fp[i - 1].BidVol > 0 && fp[i].AskVol >= ratio * fp[i - 1].BidVol) run++;
        else run = 0;
        if (run >= needed) return true;
    }
    return false;
}
```

## 6. Level-2 / Market depth

```csharp
protected override void OnStart()
{
    Symbol.MarketDepth.Updated += OnDepthUpdated;
}

void OnDepthUpdated()
{
    var bids = Symbol.MarketDepth.BidEntries;
    var asks = Symbol.MarketDepth.AskEntries;
    // compare with prior snapshot, log consumed levels...
}
```

## 7. Order helpers

```csharp
void OpenLong(double slPrice, double tpPrice, string label)
{
    double slPips = Math.Round((Symbol.Ask - slPrice) / Symbol.PipSize, 1);
    double tpPips = Math.Round((tpPrice - Symbol.Ask) / Symbol.PipSize, 1);
    double volume = LotByRisk(slPips, InpRiskPct);
    var r = ExecuteMarketOrder(TradeType.Buy, Symbol.Name, volume, label, slPips, tpPips);
    if (!r.IsSuccessful) Print("Buy failed: " + r.Error);
}
```

## 8. Risk-based volume

```csharp
double LotByRisk(double slPips, double riskPct)
{
    double balance = Account.Balance;
    double riskMoney = balance * riskPct / 100.0;
    double pipValueForOneLot = Symbol.PipValue * Symbol.LotSize;
    double volumeUnits = riskMoney / (slPips * Symbol.PipValue);
    volumeUnits = Symbol.NormalizeVolumeInUnits(volumeUnits, RoundingMode.Down);
    return Math.Max(volumeUnits, Symbol.VolumeInUnitsMin);
}
```

## 9. Spread + session guard

```csharp
bool TradeAllowedNow()
{
    double spreadPips = (Symbol.Ask - Symbol.Bid) / Symbol.PipSize;
    if (spreadPips > InpMaxSpread) return false;
    int hour = Server.Time.Hour;
    return hour >= InpSessionStart && hour < InpSessionEnd;
}
```

## 10. Daily-loss kill switch

```csharp
DateTime _dayKey;
double   _dayStartEquity;

bool DailyLossOk()
{
    var today = Server.Time.Date;
    if (today != _dayKey) { _dayKey = today; _dayStartEquity = Account.Equity; }
    double dd = (_dayStartEquity - Account.Equity) / _dayStartEquity * 100.0;
    return dd < InpMaxDailyLossPct;
}
```

## 11. New-bar gate

```csharp
DateTime _lastBarSeen = DateTime.MinValue;
bool IsNewBar()
{
    if (Bars.LastBar.OpenTime == _lastBarSeen) return false;
    _lastBarSeen = Bars.LastBar.OpenTime;
    return true;
}
```

## 12. Multi-timeframe data

```csharp
Bars _htf;
protected override void OnStart()
{
    _htf = MarketData.GetBars(TimeFrame.Hour4);
}
```

