---
name: godmode-orderflow-mastery
version: 3.0
author: GODMODE SYNTHESIS — Compiled from 69+ source documents + REF-01-07
description: >
  GODMODE Order Flow Trading Mastery Expert Skill. Complete institutional-grade
  order flow framework for building EA trading robots on MetaTrader 5 (MQL5) and
  cTrader (cAlgo/C#). Synthesizes Fabio Valentini AMT methodology, Wyckoff 2.0,
  Volume Profile, Footprint/Delta analysis, all Pine Script indicator logic, and
  full language conversion tables, Triple-A framework, Wyckoff 2.0 deep verification, 83-min OFT system, 33-video routing index. Primary purpose: enable production EA generation.
triggers:
  - "order flow EA"
  - "cTrader bot"
  - "MT5 robot"
  - "orderflow indicator"
  - "build trading EA"
  - "delta divergence"
  - "volume profile EA"
  - "footprint chart robot"
  - "absorption signal"
  - "CVD strategy"
  - "GODMODE orderflow"
  - "institutional EA"
platforms: [MetaTrader5, cTrader, TradingView]
languages: [MQL5, cAlgo_CSharp, PineScript_v6]
---

# GODMODE ORDER FLOW TRADING MASTERY EXPERT SKILL v3.0

> **ACTIVATION**: When this skill is loaded, Claude operates as a master-level order flow trading engineer capable of building production EA robots for MT5 and cTrader. All knowledge below is internalized and active.

---

## PART 1: FOUNDATIONAL ORDER FLOW THEORY

### 1.1 Core Principle
Order flow reveals the REAL battle between buyers and sellers at the tick level — not lagging price patterns. Institutional actors leave footprints through volume, delta, and absorption. This skill reads those footprints and converts them to executable code.

### 1.2 The Market Auction Theory (AMT) — Fabio Valentini / ChartFanatics
**Source**: fabio-valentini-strategy-guide.pdf

Markets exist in two states only:
- **Balance (Equilibrium)**: 70-80% of time. Price consolidates. Institutions accumulate/distribute.
- **Imbalance (Directional)**: 20-30% of time. Price trends. Institutions execute.

**Key Insight**: Retail traders try to predict direction. Institutional traders REACT to state change.

**Two Trading Models**:
| Model | Market State | Session | Bias |
|-------|-------------|---------|------|
| Model 1 — Trend Following | Imbalanced | NY Main (17:30–21:00 SAST) | Trade WITH momentum |
| Model 2 — Mean Reversion | Balanced | London Main | Trade AGAINST extremes |

### 1.3 The 3-Step Pre-Trade Protocol (Fabio Valentini)
```
STEP 1: LOCATION
  → Identify VP structure: POC, VAH, VAL, LVN, HVN
  → Is price at a high-probability level?
  → Balance zone OR LVN rejection zone?

STEP 2: VALIDATION
  → CVD direction confirms price move?
  → Absorption detected? (large limit orders defending level)
  → Delta divergence present? (price makes new high but delta fails)

STEP 3: AGGRESSION TRIGGER
  → NQ: ≥30 contracts footprint spike at level
  → ES: ≥15 contracts footprint spike at level
  → Confirmed institutional aggression = ENTER
```

### 1.4 Session Timing Rules (SAST — South Africa Standard Time)
```
Asian Session (01:00–08:00 SAST):    DO NOT TRADE — low volume, noise
London Open (09:00–10:30 SAST):      SELECTIVE — Model 1 only if clear imbalance
London Main (10:30–14:00 SAST):      PRIMARY Model 2 window (mean reversion)
NY Open (15:30–17:30 SAST):          TRANSITION — reduce exposure
NY Main (17:30–21:00 SAST):          BEST Model 1 window (trend following)
After Market (21:00+ SAST):          CLOSE ALL — no overnight positions (HARD RULE)
```

---

## PART 2: ORDER FLOW CONCEPTS — COMPLETE REFERENCE

### 2.1 Delta
**Definition**: Aggressive Buy Volume − Aggressive Sell Volume per candle
- **Positive Delta**: More market buy orders hit the ask → buyers aggressive
- **Negative Delta**: More market sell orders hit the bid → sellers aggressive
- **Delta Divergence**: Price makes new high but delta doesn't → bearish absorption signal

**Pine Script**:
```pine
[openVolume, maxVolume, minVolume, bar_delta] = ta.requestVolumeDelta(timeframe)
```

**MQL5 Equivalent**:
```mql5
MqlTick ticks[];
CopyTicksRange(_Symbol, ticks, COPY_TICKS_TRADE, from_time, to_time);
double buy_vol = 0, sell_vol = 0;
for(int i = 0; i < ArraySize(ticks); i++) {
    if(ticks[i].flags & TICK_FLAG_BUY)  buy_vol  += ticks[i].volume_real;
    if(ticks[i].flags & TICK_FLAG_SELL) sell_vol += ticks[i].volume_real;
}
double bar_delta = buy_vol - sell_vol;
```

**cAlgo/cTrader C#**:
```csharp
var ticks = MarketData.GetTicks(Symbol.Name, from, to);
double buyVol = 0, sellVol = 0;
foreach(var tick in ticks) {
    if(tick.TickType == TickType.Ask) buyVol  += tick.Volume;
    if(tick.TickType == TickType.Bid) sellVol += tick.Volume;
}
double barDelta = buyVol - sellVol;
```

### 2.2 Cumulative Volume Delta (CVD)
**Definition**: Running total of all delta values. CVD divergence from price = institutional absorption.

**Pattern**: Price rises → CVD falls = Bearish (institutions absorbing buys with limit sells)
**Pattern**: Price falls → CVD rises = Bullish (institutions absorbing sells with limit buys)

**Pine Script**:
```pine
cvd = ta.cum(bar_delta)
cvd_divergence_bearish = ta.highest(close, 20) == close and cvd < ta.highest(cvd, 20)[1]
cvd_divergence_bullish = ta.lowest(close, 20)  == close and cvd > ta.lowest(cvd, 20)[1]
```

**MQL5**:
```mql5
// Maintain running CVD in buffer
static double cvd = 0;
cvd += bar_delta;  // Add each bar's delta to running total
```

**cAlgo**:
```csharp
private double _cvd = 0;
protected override void Calculate(int index) {
    _cvd += GetBarDelta(index);
    Result[index] = _cvd;
}
```

### 2.3 Volume Profile
**Definition**: Volume distributed across price levels over a period. Shows WHERE transactions occurred.

**Key Levels**:
| Level | Acronym | Meaning | EA Action |
|-------|---------|---------|-----------|
| Point of Control | POC | Highest volume price | Mean reversion target |
| Value Area High | VAH | Top of 70% volume zone | Resistance / Short level |
| Value Area Low | VAL | Bottom of 70% volume zone | Support / Long level |
| High Volume Node | HVN | Acceptance zone | Price returns here |
| Low Volume Node | LVN | Rejection zone | Price passes quickly |

**Profile Shapes** (Trader Dale / Villahermosa):
- **D-Profile**: Normal distribution, balanced — Model 2 (mean reversion)
- **P-Profile**: Thin bottom, fat top — bullish trend, look for longs at VAL
- **b-Profile**: Fat bottom, thin top — bearish trend, look for shorts at VAH
- **Thin Profile**: Very narrow — imbalanced, breakout likely

**Pine Script VP Approximation**:
```pine
// Volume Profile via fixed range
length = input.int(20, "VP Length")
var float[] price_levels = array.new_float(100, 0)
var float[] vol_levels   = array.new_float(100, 0)
// Bin prices into N buckets, accumulate volume
high_range = ta.highest(high, length)
low_range  = ta.lowest(low, length)
bucket_size = (high_range - low_range) / 100
bucket = math.floor((close - low_range) / bucket_size)
```

**MQL5 VP**:
```mql5
// Full tick-based VP
double price_min = iLow(_Symbol, PERIOD_D1, 0);
double price_max = iHigh(_Symbol, PERIOD_D1, 0);
int bins = 200;
double bin_size = (price_max - price_min) / bins;
double vol_profile[200] = {0};

MqlTick ticks[];
CopyTicksRange(_Symbol, ticks, COPY_TICKS_ALL, from_ms, to_ms);
for(int i = 0; i < ArraySize(ticks); i++) {
    int bin = (int)((ticks[i].bid - price_min) / bin_size);
    if(bin >= 0 && bin < bins)
        vol_profile[bin] += ticks[i].volume_real;
}
// Find POC
int poc_bin = ArrayMaximum(vol_profile, 0, bins);
double poc_price = price_min + poc_bin * bin_size;
```

**cAlgo VP**:
```csharp
var bars = MarketData.GetBars(TimeFrame.Hour, Symbol.Name);
var profile = new Dictionary<int, double>();
double tickSize = Symbol.TickSize;
foreach(var bar in bars) {
    int bin = (int)(bar.Close / tickSize);
    profile[bin] = profile.ContainsKey(bin) ? profile[bin] + bar.Volume : bar.Volume;
}
int pocBin = profile.MaxBy(kv => kv.Value).Key;
double poc = pocBin * tickSize;
```

### 2.4 Footprint Charts
**Definition**: Shows bid/ask volume at every price tick within each candle. The ultimate order flow tool.

**Reading Footprint**:
- Each row = one tick level
- Left number = sell volume (at bid) | Right number = buy volume (at ask)
- **Imbalance**: Buy vol > Sell vol by 300%+ = bullish footprint imbalance
- **Absorption**: Large sell vol at high prices, candle doesn't advance = bearish

**Pine Script (via requestVolumeDelta)**:
```pine
// Pine cannot access true tick-level footprint
// Best approximation using intrabar data:
[o, h, l, c, v, d] = request.security_lower_tf(syminfo.tickerid, "1", 
    [open, high, low, close, volume, ta.requestVolumeDelta("1")[3]])
```

**MQL5 Footprint**:
```mql5
// True footprint via tick data aggregation
struct FootprintRow {
    double price;
    double buy_vol;
    double sell_vol;
    double delta;
    bool imbalance;
};

FootprintRow BuildFootprint(datetime bar_time, double bar_high, double bar_low) {
    MqlTick ticks[];
    datetime next_bar = bar_time + PeriodSeconds(PERIOD_CURRENT);
    CopyTicksRange(_Symbol, ticks, COPY_TICKS_TRADE,
        (ulong)bar_time * 1000, (ulong)next_bar * 1000);
    
    int price_levels = (int)MathRound((bar_high - bar_low) / _Point);
    FootprintRow rows[];
    ArrayResize(rows, price_levels);
    
    for(int i = 0; i < ArraySize(ticks); i++) {
        int level = (int)MathRound((ticks[i].bid - bar_low) / _Point);
        if(level >= 0 && level < price_levels) {
            if(ticks[i].flags & TICK_FLAG_BUY)  rows[level].buy_vol  += ticks[i].volume_real;
            if(ticks[i].flags & TICK_FLAG_SELL) rows[level].sell_vol += ticks[i].volume_real;
        }
    }
    // Mark imbalances (buy > sell * 3)
    for(int i = 0; i < ArraySize(rows); i++)
        rows[i].imbalance = rows[i].buy_vol > rows[i].sell_vol * 3.0;
    
    return rows[ArrayMaximum(rows)];  // Return POC row
}
```

**cAlgo Footprint**:
```csharp
public class FootprintBuilder : Indicator {
    private Dictionary<double, (double Buy, double Sell)> _levels 
        = new Dictionary<double, (double, double)>();
    
    protected override void Initialize() {
        Symbol.Ticks.Subscribe(OnTick);
    }
    
    private void OnTick(SymbolTick tick) {
        double roundedPrice = Math.Round(tick.Bid / Symbol.TickSize) * Symbol.TickSize;
        if(!_levels.ContainsKey(roundedPrice))
            _levels[roundedPrice] = (0, 0);
        var (buy, sell) = _levels[roundedPrice];
        if(tick.TickType == TickType.Ask)
            _levels[roundedPrice] = (buy + tick.Volume, sell);
        else
            _levels[roundedPrice] = (buy, sell + tick.Volume);
    }
    
    public double GetDelta(double price) {
        if(_levels.ContainsKey(price))
            return _levels[price].Buy - _levels[price].Sell;
        return 0;
    }
}
```

### 2.5 Absorption
**Definition**: When limit orders defend a price level faster than market orders drain them. Price stalls despite aggression → reversal setup.

**Detection Logic** (from Absorption Signals by JacobS369):
```pine
// Bullish Absorption: negative delta + high volume + bullish close
abs_volume_lookback = input.int(20)
abs_zscore_threshold = input.float(1.5)

[openVolume, maxVolume, minVolume, bar_delta] = ta.requestVolumeDelta("1")

avg_volume   = ta.sma(volume, abs_volume_lookback)
stdev_volume = ta.stdev(volume, abs_volume_lookback)
volume_zscore = stdev_volume > 0 ? (volume - avg_volume) / stdev_volume : 0
volume_anomaly = volume_zscore >= abs_zscore_threshold

avg_delta    = ta.sma(bar_delta, abs_volume_lookback)
stdev_delta  = ta.stdev(bar_delta, abs_volume_lookback)
delta_zscore = stdev_delta > 0 ? (bar_delta - avg_delta) / stdev_delta : 0

bullish_absorption = bar_delta < 0 and volume_anomaly and (close >= open)
bearish_absorption = bar_delta > 0 and volume_anomaly and (close <= open)

// Confidence scoring (1-5 stars)
bull_confidence = 0.0
if bullish_absorption
    bull_confidence := 1.0
    if volume_zscore >= 2.0 : bull_confidence += 1.0
    if volume_zscore >= 3.0 : bull_confidence += 1.0
    if math.abs(delta_zscore) >= 2.0 : bull_confidence += 1.0
    if lower_wick_pct >= 0.4 : bull_confidence += 1.0
bull_confidence := math.min(bull_confidence, 5.0)
```

**MQL5 Absorption**:
```mql5
bool DetectBullishAbsorption(int bar, int lookback = 20) {
    double vol_mean = 0, vol_std = 0;
    double delta = GetBarDelta(bar);
    
    for(int i = bar; i < bar + lookback; i++) {
        vol_mean += iVolume(_Symbol, PERIOD_CURRENT, i);
    }
    vol_mean /= lookback;
    
    for(int i = bar; i < bar + lookback; i++) {
        double diff = iVolume(_Symbol, PERIOD_CURRENT, i) - vol_mean;
        vol_std += diff * diff;
    }
    vol_std = MathSqrt(vol_std / lookback);
    
    double vol_zscore = vol_std > 0 ? 
        (iVolume(_Symbol, PERIOD_CURRENT, bar) - vol_mean) / vol_std : 0;
    bool volume_anomaly = vol_zscore >= 1.5;
    
    double close_bar = iClose(_Symbol, PERIOD_CURRENT, bar);
    double open_bar  = iOpen(_Symbol, PERIOD_CURRENT, bar);
    
    return (delta < 0 && volume_anomaly && close_bar >= open_bar);
}
```

**cAlgo Absorption**:
```csharp
private bool IsBullishAbsorption(int index, int lookback = 20) {
    double delta = GetBarDelta(index);
    var volumes = Enumerable.Range(index, lookback)
        .Select(i => Bars.TickVolumes[i]).ToArray();
    double mean = volumes.Average();
    double std = Math.Sqrt(volumes.Select(v => Math.Pow(v - mean, 2)).Average());
    double zScore = std > 0 ? (Bars.TickVolumes[index] - mean) / std : 0;
    
    return delta < 0 
        && zScore >= 1.5 
        && Bars.ClosePrices[index] >= Bars.OpenPrices[index];
}
```

### 2.6 LVN Trading (Carmine Strategy)
**Definition**: Low Volume Nodes are price levels where very little trading occurred. Price passes through them RAPIDLY (acceleration zones).

**Setup**:
1. Identify LVN on Volume Profile
2. Price approaches LVN from HVN
3. Wait for price to breach LVN
4. Enter in direction of breakthrough with tight stop
5. Target: next HVN or POC

**MQL5 LVN Detection**:
```mql5
// Find LVN: bins with volume < 20% of POC volume
double poc_vol = vol_profile[poc_bin];
bool is_lvn[200];
for(int i = 0; i < 200; i++)
    is_lvn[i] = vol_profile[i] < poc_vol * 0.20;

// Trading: price enters LVN zone → accelerate entry
bool price_in_lvn = false;
for(int i = 0; i < 200; i++) {
    double level = price_min + i * bin_size;
    if(is_lvn[i] && MathAbs(Close[0] - level) < bin_size * 2) {
        price_in_lvn = true;
        break;
    }
}
```

### 2.7 Stacked Imbalances
**Definition**: Consecutive directional bars with dominant one-sided delta. High-probability continuation zones.

```pine
// Stacked Imbalance detection
bullish_imbalance = bar_delta > 0 and close > open and volume > ta.sma(volume, 20) * 1.5
stacked_bull = bullish_imbalance and bullish_imbalance[1] and bullish_imbalance[2]
```

### 2.8 Order Blocks
**Definition**: Last impulsive candle before significant price displacement. Institutional entry zone.

```pine
// Bullish Order Block: last bearish candle before strong up move
displacement = close - close[3]  // 3-bar move
bull_ob = close[1] < open[1] and displacement > ta.atr(14) * 1.5
```

### 2.9 VEP/CBP — Aegis Hybrid Framework
**Source**: Aegis VEP_CBP Hybrid indicator (wjdtks255)

**VEP** = Volume Expansion Pattern (거래량 폭발): Volume spike where current bar volume exceeds max volume of last N bars in same direction
**CBP** = Core Buying/Selling Pressure (실질 압력): Net pressure = volume × ((close - low) - (high - close)) / range

```pine
// VEP Calculation
lenMA = input.int(50)
lookback = input.int(10)
vMA = ta.sma(volume, lenMA)
isUp = close > close[1]
isDown = close < close[1]

float maxD = 0.0, maxU = 0.0
for i = 1 to lookback
    if close[i] < close[i+1]: maxD := math.max(maxD, volume[i])
    if close[i] > close[i+1]: maxU := math.max(maxU, volume[i])

isPPV = isUp and volume > maxD    // Positive Price-Volume (bullish VEP)
isBPV = isDown and volume > maxU  // Bearish VEP

// CBP Calculation
cRange = math.max(high - low, syminfo.mintick)
net_p = volume * ((close - low) - (high - close)) / cRange
sMA = ta.ema(net_p, 20)

bull_signal = isPPV and net_p > sMA  // Golden Bull (yellow triangle up)
bear_signal = isBPV and net_p < sMA  // Death Bear (purple triangle down)
```

**MQL5 VEP/CBP**:
```mql5
bool IsVEPBull(int bar, int lenMA = 50, int lookback = 10) {
    bool isUp = iClose(_Symbol, PERIOD_CURRENT, bar) > 
                iClose(_Symbol, PERIOD_CURRENT, bar+1);
    if(!isUp) return false;
    
    double maxD = 0;
    for(int i = 1; i <= lookback; i++) {
        if(iClose(_Symbol, PERIOD_CURRENT, bar+i) < 
           iClose(_Symbol, PERIOD_CURRENT, bar+i+1))
            maxD = MathMax(maxD, iVolume(_Symbol, PERIOD_CURRENT, bar+i));
    }
    return iVolume(_Symbol, PERIOD_CURRENT, bar) > maxD;
}

double GetCBP(int bar) {
    double h = iHigh(_Symbol, PERIOD_CURRENT, bar);
    double l = iLow(_Symbol, PERIOD_CURRENT, bar);
    double c = iClose(_Symbol, PERIOD_CURRENT, bar);
    double v = iVolume(_Symbol, PERIOD_CURRENT, bar);
    double range = MathMax(h - l, _Point);
    return v * ((c - l) - (h - c)) / range;
}
```

### 2.10 Bookmap Traps (Footprint Delta Trap)
**Definition**: Detect trapped/underwater participants using tick-level delta at candle extremes.

**Logic**: When price makes a new high with negative delta (sellers dominating at the top), longs are trapped. Reversal imminent.

```pine
// Trap detection at highs
upper_wick_delta = bar_delta  // Delta measured at upper wick region
trap_at_high = high == ta.highest(high, 20) and bar_delta < 0
trap_at_low  = low  == ta.lowest(low, 20)  and bar_delta > 0
```

### 2.11 Naive Bayes ML Delta (GainzAlgo)
**Definition**: Gaussian Naive Bayes applied to volume delta for probabilistic signal generation.

```pine
// Simplified Bayesian probability for delta signal
prior_bull = 0.5
likelihood_bull = bar_delta > 0 ? 
    math.exp(-0.5 * math.pow((bar_delta - avg_delta) / stdev_delta, 2)) : 0.1
posterior = (likelihood_bull * prior_bull) / 
    (likelihood_bull * prior_bull + (1 - likelihood_bull) * (1 - prior_bull))
bull_probability = posterior
```

---

## PART 3: WYCKOFF 2.0 INTEGRATION
**Source**: Wyckoff 2.0 — Rubén Villahermosa Chaves

### 3.1 Core Principle
Wyckoff 2.0 = Classic Wyckoff Phase Analysis + Volume Profile + Order Flow

**Wyckoff Phases**:
- **Phase A**: Stop of prior trend (PS, SC, AR, ST events)
- **Phase B**: Building cause (testing, backing and filling)
- **Phase C**: Test / Spring or Upthrust
- **Phase D**: Trend establishes within structure
- **Phase E**: Trend exits structure

**Wyckoff 2.0 Addition**: Use Volume Profile to OBJECTIVELY identify phase boundaries:
- Phase A SC (Selling Climax) → confirmed by bullish absorption on footprint
- Phase C Spring → must have LVN below and CVD divergence
- Phase D SOS (Sign of Strength) → must have stacked bullish imbalances

### 3.2 Structural Failure Pattern
**Shortening of the Thrust (SOT)**: Each thrust in direction gets shorter → exhaustion signal
**Implementation**: Compare swing amplitudes. If SOT[n] < SOT[n-1] < SOT[n-2] → fade next thrust

### 3.3 Wyckoff 2.0 Trading Rules
```
Accumulation Context:
  → Price at VAL or below → look for bullish absorption
  → CVD diverging upward while price stays flat → strong accumulation
  → Spring below support with immediate recovery → enter long

Distribution Context:
  → Price at VAH or above → look for bearish absorption
  → CVD diverging downward while price stays high → distribution
  → Upthrust above resistance with immediate rejection → enter short
```

---

## PART 4: PINE SCRIPT → MQL5 → cALGO LANGUAGE CONVERSION

### 4.1 Complete Conversion Reference Table

| Pine Script | MQL5 | cAlgo (C#) |
|-------------|------|-----------|
| `indicator()` | `OnInit()` in indicator | `[Indicator]` attribute |
| `strategy()` | `OnInit()` in EA | `[Robot]` attribute |
| `close`, `open`, `high`, `low` | `Close[0]`, `Open[0]`, `High[0]`, `Low[0]` | `Bars.ClosePrices[index]` |
| `volume` | `iVolume(_Symbol, period, bar)` | `Bars.TickVolumes[index]` |
| `ta.sma(src, len)` | `iMA(_Symbol, period, len, 0, MODE_SMA, PRICE_CLOSE)` | `Indicators.SimpleMovingAverage(src, len)` |
| `ta.ema(src, len)` | `iMA(_Symbol, period, len, 0, MODE_EMA, PRICE_CLOSE)` | `Indicators.ExponentialMovingAverage(src, len)` |
| `ta.atr(len)` | `iATR(_Symbol, period, len)` | `Indicators.AverageTrueRange(len, MovingAverageType.Simple)` |
| `ta.highest(src, len)` | `ArrayMaximum(buffer, len)` | `src.Maximum(len)` |
| `ta.lowest(src, len)` | `ArrayMinimum(buffer, len)` | `src.Minimum(len)` |
| `ta.crossover(a, b)` | `a[0] > b[0] && a[1] <= b[1]` | `a.IsRising() && a[0] > b[0]` |
| `ta.crossunder(a, b)` | `a[0] < b[0] && a[1] >= b[1]` | `a.IsFalling() && a[0] < b[0]` |
| `ta.stdev(src, len)` | Custom: MathSqrt(variance) | `Statistics.StdDev(values)` |
| `request.security(sym,tf,expr)` | `iClose(sym, tf, bar)` | `MarketData.GetBars(tf, sym)` |
| `ta.requestVolumeDelta(tf)` | `CopyTicksRange()` aggregation | `Symbol.Ticks` aggregation |
| `plotshape()` | `ObjectCreate()` ChartArrow | `Chart.DrawIcon()` |
| `plot()` | `SetIndexBuffer()` | `[Output]` attribute |
| `bgcolor()` | `ChartSetInteger(CHART_COLOR_BACKGROUND)` | `Chart.ColorSettings` |
| `label.new()` | `ObjectCreate()` OBJ_LABEL | `Chart.DrawText()` |
| `box.new()` | `ObjectCreate()` OBJ_RECTANGLE | `Chart.DrawRectangle()` |
| `line.new()` | `ObjectCreate()` OBJ_TREND | `Chart.DrawTrendLine()` |
| `strategy.entry()` | `OrderSend()` / CTrade | `ExecuteMarketOrder()` |
| `strategy.close()` | `OrderClose()` / CTrade | `ClosePosition()` |
| `strategy.exit()` | `OrderModify()` SL/TP | `ModifyPosition()` |
| `input.int()` | `input int` | `[Parameter]` attribute |
| `input.float()` | `input double` | `[Parameter]` attribute |
| `input.bool()` | `input bool` | `[Parameter]` attribute |
| `input.string()` | `input string` | `[Parameter]` attribute |
| `barstate.isrealtime` | `!IsTesting()` | `IsBacktesting == false` |
| `barstate.islast` | `bar == 0` (current) | check `IsLastBar` |
| `nz(x, y)` | `x == EMPTY_VALUE ? y : x` | `double.IsNaN(x) ? y : x` |
| `na` | `EMPTY_VALUE` or `NULL` | `double.NaN` |
| `math.abs(x)` | `MathAbs(x)` | `Math.Abs(x)` |
| `math.max(a,b)` | `MathMax(a,b)` | `Math.Max(a,b)` |
| `math.min(a,b)` | `MathMin(a,b)` | `Math.Min(a,b)` |
| `math.sqrt(x)` | `MathSqrt(x)` | `Math.Sqrt(x)` |
| `math.pow(x,y)` | `MathPow(x,y)` | `Math.Pow(x,y)` |
| `math.exp(x)` | `MathExp(x)` | `Math.Exp(x)` |
| `math.log(x)` | `MathLog(x)` | `Math.Log(x)` |
| `str.tostring(x)` | `DoubleToString(x)` | `x.ToString()` |
| `color.new(col,transp)` | `ColorSetAlpha(col, 255-transp)` | `Color.FromArgb(alpha,r,g,b)` |
| `syminfo.mintick` | `_Point` | `Symbol.TickSize` |
| `syminfo.ticksize` | `_Point` | `Symbol.TickSize` |
| `time` | `TimeCurrent()` | `Server.Time` |
| `bar_index` | `Bars - 1 - shift` | `index` parameter |
| `timenow` | `TimeCurrent()` | `Server.Time` |
| `alert()` | `Alert()` or `SendNotification()` | `Notifications.SendEmail()` |

### 4.2 Tick Data Access — Critical Platform Differences

**Pine Script** (limited — no true tick access):
```pine
// Pine cannot access real tick data mid-bar
// Use requestVolumeDelta for delta approximation
[openVol, maxVol, minVol, delta] = ta.requestVolumeDelta("1")
```

**MQL5** (full tick access):
```mql5
// Full historical tick data access
MqlTick ticks[];
ulong from_ms = (ulong)iTime(_Symbol, PERIOD_CURRENT, bar) * 1000;
ulong to_ms   = from_ms + PeriodSeconds(PERIOD_CURRENT) * 1000;
int count = CopyTicksRange(_Symbol, ticks, COPY_TICKS_TRADE, from_ms, to_ms);

// Real-time tick processing
void OnTick() {
    MqlTick tick;
    SymbolInfoTick(_Symbol, tick);
    bool is_buy  = tick.flags & TICK_FLAG_BUY;
    bool is_sell = tick.flags & TICK_FLAG_SELL;
}
```

**cAlgo/cTrader** (full tick access):
```csharp
// Historical ticks
var ticks = MarketData.GetTicks(Symbol.Name, startTime, endTime);
foreach(var tick in ticks) {
    bool isBuy  = tick.TickType == TickType.Ask; // Buys lift the ask
    bool isSell = tick.TickType == TickType.Bid; // Sells hit the bid
    double volume = tick.Volume;
}

// Real-time tick processing
protected override void OnTick() {
    var tick = Symbol.Ticks.LastTick;
    // Process current tick
}
```

### 4.3 Order Execution Conversion

**Pine Strategy**:
```pine
strategy.entry("Long", strategy.long, qty=1.0, 
    stop=low - atr, limit=close + atr*2)
strategy.exit("Long Exit", "Long", loss=atr/syminfo.mintick, 
    profit=atr*2/syminfo.mintick)
```

**MQL5 EA**:
```mql5
#include <Trade\Trade.mqh>
CTrade trade;

void EnterLong(double sl_price, double tp_price, double lot_size) {
    trade.SetExpertMagicNumber(MAGIC_NUMBER);
    trade.SetDeviationInPoints(10);
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    
    if(!trade.Buy(lot_size, _Symbol, ask, sl_price, tp_price, "OF Long")) {
        Print("Buy failed: ", trade.ResultRetcode(), " - ", trade.ResultRetcodeDescription());
    }
}

void ManagePositions() {
    for(int i = PositionsTotal()-1; i >= 0; i--) {
        if(PositionSelectByTicket(PositionGetTicket(i))) {
            if(PositionGetInteger(POSITION_MAGIC) == MAGIC_NUMBER) {
                // Trail stop, partial close, etc.
            }
        }
    }
}
```

**cAlgo EA**:
```csharp
private TradeResult EnterLong(double slPrice, double tpPrice, double volumeInLots) {
    return ExecuteMarketOrder(TradeType.Buy, SymbolName, 
        Symbol.QuantityToVolumeInUnits(volumeInLots),
        label: "OF Long",
        stopLossPips: (Symbol.Ask - slPrice) / Symbol.PipSize,
        takeProfitPips: (tpPrice - Symbol.Ask) / Symbol.PipSize);
}

private void ManagePosition(Position position) {
    // Trail stop
    double newSL = Symbol.Bid - TrailStopPips * Symbol.PipSize;
    if(newSL > position.StopLoss)
        ModifyPosition(position, newSL, position.TakeProfit);
}
```

---

## PART 5: COMPLETE EA BLUEPRINTS

### 5.1 MT5 Order Flow EA — Master Blueprint

```mql5
//+------------------------------------------------------------------+
//| OrderFlow_EA_v2.mq5                                              |
//| GODMODE Order Flow EA — MT5                                      |
//| Based on Fabio Valentini AMT + Volume Profile + Delta            |
//+------------------------------------------------------------------+
#property copyright "GODMODE OrderFlow v2.0"
#property version   "2.00"

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>

//--- Input Parameters
input group "=== STRATEGY ==="
input int    InpModel           = 1;      // 1=Trend Follow, 2=Mean Reversion
input int    InpSessionFilter   = 1;      // 1=NY Main, 2=London Main, 0=All

input group "=== ORDER FLOW ==="
input int    InpDeltaLookback   = 20;    // Delta Z-Score Lookback
input double InpDeltaZThresh    = 1.5;   // Delta Z-Score Threshold
input double InpVolZThresh      = 1.5;   // Volume Z-Score Threshold
input int    InpVPLength        = 100;   // Volume Profile Bars

input group "=== RISK ==="
input double InpRiskPct         = 1.0;   // Risk per trade (%)
input double InpRR              = 2.0;   // Risk:Reward ratio
input double InpMaxDDPct        = 5.0;   // Max daily drawdown %
input int    InpMagicNumber     = 202400; // Magic number

input group "=== TRADE MANAGEMENT ==="
input bool   InpTrailStop       = true;  // Use trailing stop
input double InpTrailATR        = 1.0;   // Trail stop ATR multiplier
input bool   InpPartialClose    = true;  // Partial close at 1R
input double InpPartialPct      = 50.0;  // Partial close percentage

//--- Global Variables
CTrade trade;
static double g_cvd = 0;
static double g_daily_start_equity = 0;
datetime g_last_bar_time = 0;
int g_atr_handle = INVALID_HANDLE;

//+------------------------------------------------------------------+
int OnInit() {
    trade.SetExpertMagicNumber(InpMagicNumber);
    trade.SetDeviationInPoints(10);
    g_atr_handle = iATR(_Symbol, PERIOD_CURRENT, 14);
    g_daily_start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
    if(g_atr_handle != INVALID_HANDLE) IndicatorRelease(g_atr_handle);
}

//+------------------------------------------------------------------+
void OnTick() {
    datetime current_bar = iTime(_Symbol, PERIOD_CURRENT, 0);
    if(current_bar == g_last_bar_time) return;  // New bar only
    g_last_bar_time = current_bar;
    
    // Daily drawdown check
    double current_equity = AccountInfoDouble(ACCOUNT_EQUITY);
    double dd_pct = (g_daily_start_equity - current_equity) / g_daily_start_equity * 100;
    if(dd_pct >= InpMaxDDPct) {
        Print("Max daily drawdown reached. Stopping.");
        CloseAllPositions();
        return;
    }
    
    // Session filter
    if(!IsValidSession()) return;
    
    // Get ATR
    double atr_buf[]; ArrayResize(atr_buf, 3);
    CopyBuffer(g_atr_handle, 0, 0, 3, atr_buf);
    double atr = atr_buf[0];
    
    // Get order flow signals
    double bar_delta = GetBarDelta(0);
    UpdateCVD(bar_delta);
    
    bool bull_abs = DetectBullishAbsorption(0);
    bool bear_abs = DetectBearishAbsorption(0);
    bool cvd_bull = IsCVDBullish();
    bool cvd_bear = IsCVDBearish();
    
    // Volume Profile levels
    double poc = GetPOC();
    double vah = GetVAH();
    double val = GetVAL();
    bool at_support = MathAbs(Close[0] - val) < atr * 0.5;
    bool at_resist  = MathAbs(Close[0] - vah) < atr * 0.5;
    bool at_poc     = MathAbs(Close[0] - poc) < atr * 0.3;
    
    // No existing positions
    if(CountMyPositions() == 0) {
        // Model 1: Trend Following
        if(InpModel == 1) {
            if(bull_abs && cvd_bull && !at_resist) {
                double sl = Close[0] - atr * 1.5;
                double tp = Close[0] + atr * InpRR * 1.5;
                double lots = CalculateLots(MathAbs(Close[0] - sl));
                EnterLong(sl, tp, lots);
            }
            if(bear_abs && cvd_bear && !at_support) {
                double sl = Close[0] + atr * 1.5;
                double tp = Close[0] - atr * InpRR * 1.5;
                double lots = CalculateLots(MathAbs(sl - Close[0]));
                EnterShort(sl, tp, lots);
            }
        }
        
        // Model 2: Mean Reversion
        if(InpModel == 2) {
            if(at_support && bull_abs) {
                double sl = val - atr;
                double tp = poc;  // Target POC for mean reversion
                double lots = CalculateLots(MathAbs(Close[0] - sl));
                EnterLong(sl, tp, lots);
            }
            if(at_resist && bear_abs) {
                double sl = vah + atr;
                double tp = poc;
                double lots = CalculateLots(MathAbs(sl - Close[0]));
                EnterShort(sl, tp, lots);
            }
        }
    }
    
    // Manage existing positions
    ManagePositions(atr);
}

//+------------------------------------------------------------------+
bool IsValidSession() {
    MqlDateTime dt;
    TimeToStruct(TimeCurrent(), dt);
    int hour = dt.hour;
    
    // SAST offset: UTC+2
    // NY Main: 15:30-19:00 UTC = 17:30-21:00 SAST
    // London Main: 08:30-12:00 UTC = 10:30-14:00 SAST
    
    if(InpSessionFilter == 1) // NY Main
        return (hour >= 15 && hour < 19);  // UTC
    if(InpSessionFilter == 2) // London Main
        return (hour >= 8 && hour < 12);   // UTC
    return true;
}

//+------------------------------------------------------------------+
double GetBarDelta(int bar) {
    datetime bar_time = iTime(_Symbol, PERIOD_CURRENT, bar);
    datetime next_bar = bar_time + PeriodSeconds(PERIOD_CURRENT);
    
    MqlTick ticks[];
    int count = CopyTicksRange(_Symbol, ticks, COPY_TICKS_TRADE,
        (ulong)bar_time * 1000, (ulong)next_bar * 1000);
    
    if(count <= 0) return 0;
    
    double buy_vol = 0, sell_vol = 0;
    for(int i = 0; i < count; i++) {
        if(ticks[i].flags & TICK_FLAG_BUY)  buy_vol  += ticks[i].volume_real;
        if(ticks[i].flags & TICK_FLAG_SELL) sell_vol += ticks[i].volume_real;
    }
    return buy_vol - sell_vol;
}

//+------------------------------------------------------------------+
void UpdateCVD(double delta) { g_cvd += delta; }

bool IsCVDBullish() {
    // CVD rising when price is neutral or falling = hidden strength
    static double prev_cvd = 0;
    bool rising = g_cvd > prev_cvd;
    prev_cvd = g_cvd;
    return rising;
}

bool IsCVDBearish() {
    static double prev_cvd2 = 0;
    bool falling = g_cvd < prev_cvd2;
    prev_cvd2 = g_cvd;
    return falling;
}

//+------------------------------------------------------------------+
bool DetectBullishAbsorption(int bar) {
    int lookback = InpDeltaLookback;
    double delta = GetBarDelta(bar);
    
    // Volume stats
    double vol_sum = 0;
    for(int i = bar; i < bar + lookback; i++)
        vol_sum += iVolume(_Symbol, PERIOD_CURRENT, i);
    double vol_mean = vol_sum / lookback;
    
    double vol_var = 0;
    for(int i = bar; i < bar + lookback; i++) {
        double d = iVolume(_Symbol, PERIOD_CURRENT, i) - vol_mean;
        vol_var += d * d;
    }
    double vol_std = MathSqrt(vol_var / lookback);
    double vol_z = vol_std > 0 ? 
        ((double)iVolume(_Symbol, PERIOD_CURRENT, bar) - vol_mean) / vol_std : 0;
    
    bool vol_anomaly = vol_z >= InpVolZThresh;
    bool neg_delta   = delta < 0;
    bool bull_close  = iClose(_Symbol, PERIOD_CURRENT, bar) >= 
                       iOpen(_Symbol, PERIOD_CURRENT, bar);
    
    return (neg_delta && vol_anomaly && bull_close);
}

//+------------------------------------------------------------------+
bool DetectBearishAbsorption(int bar) {
    int lookback = InpDeltaLookback;
    double delta = GetBarDelta(bar);
    
    double vol_sum = 0;
    for(int i = bar; i < bar + lookback; i++)
        vol_sum += iVolume(_Symbol, PERIOD_CURRENT, i);
    double vol_mean = vol_sum / lookback;
    
    double vol_var = 0;
    for(int i = bar; i < bar + lookback; i++) {
        double d = iVolume(_Symbol, PERIOD_CURRENT, i) - vol_mean;
        vol_var += d * d;
    }
    double vol_std = MathSqrt(vol_var / lookback);
    double vol_z = vol_std > 0 ? 
        ((double)iVolume(_Symbol, PERIOD_CURRENT, bar) - vol_mean) / vol_std : 0;
    
    bool vol_anomaly = vol_z >= InpVolZThresh;
    bool pos_delta   = delta > 0;
    bool bear_close  = iClose(_Symbol, PERIOD_CURRENT, bar) <= 
                       iOpen(_Symbol, PERIOD_CURRENT, bar);
    
    return (pos_delta && vol_anomaly && bear_close);
}

//+------------------------------------------------------------------+
// Simplified POC/VAH/VAL using tick volume bar aggregation
double GetPOC() {
    double high_range = iHigh(_Symbol, PERIOD_CURRENT, 
        iHighest(_Symbol, PERIOD_CURRENT, MODE_HIGH, InpVPLength, 0));
    double low_range  = iLow(_Symbol, PERIOD_CURRENT, 
        iLowest(_Symbol, PERIOD_CURRENT, MODE_LOW, InpVPLength, 0));
    
    int bins = 50;
    double bin_size = (high_range - low_range) / bins;
    if(bin_size <= 0) return iClose(_Symbol, PERIOD_CURRENT, 0);
    
    double vol_bins[50] = {0};
    for(int i = 0; i < InpVPLength; i++) {
        double c = iClose(_Symbol, PERIOD_CURRENT, i);
        long v = iVolume(_Symbol, PERIOD_CURRENT, i);
        int bin = (int)MathFloor((c - low_range) / bin_size);
        if(bin >= 0 && bin < bins) vol_bins[bin] += v;
    }
    
    int poc_bin = ArrayMaximum(vol_bins, 0, bins);
    return low_range + poc_bin * bin_size + bin_size * 0.5;
}

double GetVAH() { return GetPOC() + GetPOC() * 0.002; }  // Simplified
double GetVAL() { return GetPOC() - GetPOC() * 0.002; }  // Simplified

//+------------------------------------------------------------------+
double CalculateLots(double sl_distance) {
    double account_risk = AccountInfoDouble(ACCOUNT_EQUITY) * InpRiskPct / 100;
    double tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
    double tick_size  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
    
    if(sl_distance <= 0 || tick_value <= 0) return 0.01;
    
    double lots = account_risk / (sl_distance / tick_size * tick_value);
    lots = MathMax(SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN),
           MathMin(SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX), lots));
    
    return NormalizeDouble(lots, 2);
}

//+------------------------------------------------------------------+
void EnterLong(double sl, double tp, double lots) {
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    if(!trade.Buy(lots, _Symbol, ask, sl, tp, "OF_Long")) {
        Print("Long failed: ", trade.ResultRetcodeDescription());
    }
}

void EnterShort(double sl, double tp, double lots) {
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    if(!trade.Sell(lots, _Symbol, bid, sl, tp, "OF_Short")) {
        Print("Short failed: ", trade.ResultRetcodeDescription());
    }
}

//+------------------------------------------------------------------+
void ManagePositions(double atr) {
    for(int i = PositionsTotal()-1; i >= 0; i--) {
        ulong ticket = PositionGetTicket(i);
        if(PositionSelectByTicket(ticket)) {
            if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
            
            double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
            double current_sl = PositionGetDouble(POSITION_SL);
            double current_tp = PositionGetDouble(POSITION_TP);
            ENUM_POSITION_TYPE pos_type = 
                (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
            
            if(pos_type == POSITION_TYPE_BUY) {
                // Trail stop for long
                if(InpTrailStop) {
                    double new_sl = SymbolInfoDouble(_Symbol, SYMBOL_BID) - 
                                   atr * InpTrailATR;
                    if(new_sl > current_sl + _Point)
                        trade.PositionModify(ticket, new_sl, current_tp);
                }
                // Session close
                if(!IsValidSession())
                    trade.PositionClose(ticket);
            }
            else if(pos_type == POSITION_TYPE_SELL) {
                // Trail stop for short
                if(InpTrailStop) {
                    double new_sl = SymbolInfoDouble(_Symbol, SYMBOL_ASK) + 
                                   atr * InpTrailATR;
                    if(new_sl < current_sl - _Point || current_sl == 0)
                        trade.PositionModify(ticket, new_sl, current_tp);
                }
                if(!IsValidSession())
                    trade.PositionClose(ticket);
            }
        }
    }
}

//+------------------------------------------------------------------+
int CountMyPositions() {
    int count = 0;
    for(int i = PositionsTotal()-1; i >= 0; i--) {
        if(PositionSelectByTicket(PositionGetTicket(i)))
            if(PositionGetInteger(POSITION_MAGIC) == InpMagicNumber) count++;
    }
    return count;
}

void CloseAllPositions() {
    for(int i = PositionsTotal()-1; i >= 0; i--) {
        ulong ticket = PositionGetTicket(i);
        if(PositionSelectByTicket(ticket))
            if(PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
                trade.PositionClose(ticket);
    }
}
```

### 5.2 cTrader (cAlgo) Order Flow EA — Master Blueprint

```csharp
using System;
using System.Linq;
using System.Collections.Generic;
using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    public class OrderFlowEA : Robot
    {
        //--- Parameters
        [Parameter("Model (1=Trend, 2=MeanRev)", DefaultValue = 1, MinValue = 1, MaxValue = 2)]
        public int Model { get; set; }

        [Parameter("Session (1=NY, 2=London, 0=All)", DefaultValue = 1)]
        public int SessionFilter { get; set; }

        [Parameter("Delta Lookback", DefaultValue = 20, MinValue = 5)]
        public int DeltaLookback { get; set; }

        [Parameter("Vol Z-Score Threshold", DefaultValue = 1.5)]
        public double VolZThresh { get; set; }

        [Parameter("Risk % per trade", DefaultValue = 1.0)]
        public double RiskPct { get; set; }

        [Parameter("Risk:Reward", DefaultValue = 2.0)]
        public double RR { get; set; }

        [Parameter("Max Daily DD %", DefaultValue = 5.0)]
        public double MaxDDPct { get; set; }

        [Parameter("Trail Stop (ATR mult)", DefaultValue = 1.0)]
        public double TrailATR { get; set; }

        [Parameter("VP Bars", DefaultValue = 100)]
        public int VPBars { get; set; }

        //--- Indicators
        private AverageTrueRange _atr;
        private double _cvd = 0;
        private double _dailyStartEquity;
        private Dictionary<double, (double Buy, double Sell)> _footprint 
            = new Dictionary<double, (double, double)>();

        protected override void OnStart() {
            _atr = Indicators.AverageTrueRange(14, MovingAverageType.Simple);
            _dailyStartEquity = Account.Equity;
            
            // Subscribe to tick data for real-time delta
            Ticks.Subscribe(OnTick_Delta);
        }

        private double _tickBuyVol = 0, _tickSellVol = 0;
        
        private void OnTick_Delta(Tick tick) {
            // Accumulate tick volume by direction
            if(tick.TickType == TickType.Ask)
                _tickBuyVol += tick.Volume;
            else if(tick.TickType == TickType.Bid)
                _tickSellVol += tick.Volume;
        }

        protected override void OnBar() {
            // Daily DD check
            double ddPct = (_dailyStartEquity - Account.Equity) / _dailyStartEquity * 100;
            if(ddPct >= MaxDDPct) {
                CloseAllTrades();
                Print("Max DD reached.");
                return;
            }

            if(!IsValidSession()) return;

            double atr = _atr.Result.Last(0);
            
            // Get bar delta from accumulated tick data
            double barDelta = _tickBuyVol - _tickSellVol;
            _cvd += barDelta;
            
            // Reset tick accumulators for next bar
            _tickBuyVol = 0;
            _tickSellVol = 0;

            bool bullAbs = IsBullishAbsorption(barDelta);
            bool bearAbs = IsBearishAbsorption(barDelta);
            bool cvdBull = IsCVDBullDiverge();
            bool cvdBear = IsCVDBearDiverge();

            var vpLevels = CalculateVolumeProfile();
            double poc = vpLevels.poc, vah = vpLevels.vah, val = vpLevels.val;

            bool atSupport = Math.Abs(Symbol.Bid - val) < atr * 0.5;
            bool atResist  = Math.Abs(Symbol.Bid - vah) < atr * 0.5;

            // Only enter if no open positions
            if(Positions.Count == 0) {
                if(Model == 1) {  // Trend Following
                    if(bullAbs && cvdBull && !atResist) {
                        double sl = Symbol.Bid - atr * 1.5;
                        double tp = Symbol.Bid + atr * RR * 1.5;
                        double lots = CalculateLots(Math.Abs(Symbol.Bid - sl));
                        if(lots > 0)
                            ExecuteMarketOrder(TradeType.Buy, SymbolName, 
                                Symbol.QuantityToVolumeInUnits(lots), "OF_Long",
                                (Symbol.Bid - sl) / Symbol.PipSize,
                                (tp - Symbol.Bid) / Symbol.PipSize);
                    }
                    if(bearAbs && cvdBear && !atSupport) {
                        double sl = Symbol.Ask + atr * 1.5;
                        double tp = Symbol.Ask - atr * RR * 1.5;
                        double lots = CalculateLots(Math.Abs(sl - Symbol.Ask));
                        if(lots > 0)
                            ExecuteMarketOrder(TradeType.Sell, SymbolName,
                                Symbol.QuantityToVolumeInUnits(lots), "OF_Short",
                                (sl - Symbol.Ask) / Symbol.PipSize,
                                (Symbol.Ask - tp) / Symbol.PipSize);
                    }
                }
                else if(Model == 2) {  // Mean Reversion
                    if(atSupport && bullAbs) {
                        double sl = val - atr;
                        double tp = poc;
                        double lots = CalculateLots(Math.Abs(Symbol.Bid - sl));
                        if(lots > 0)
                            ExecuteMarketOrder(TradeType.Buy, SymbolName,
                                Symbol.QuantityToVolumeInUnits(lots), "OF_MR_Long",
                                (Symbol.Bid - sl) / Symbol.PipSize,
                                (tp - Symbol.Bid) / Symbol.PipSize);
                    }
                    if(atResist && bearAbs) {
                        double sl = vah + atr;
                        double tp = poc;
                        double lots = CalculateLots(Math.Abs(sl - Symbol.Ask));
                        if(lots > 0)
                            ExecuteMarketOrder(TradeType.Sell, SymbolName,
                                Symbol.QuantityToVolumeInUnits(lots), "OF_MR_Short",
                                (sl - Symbol.Ask) / Symbol.PipSize,
                                (Symbol.Ask - tp) / Symbol.PipSize);
                    }
                }
            }
            
            // Manage positions
            ManagePositions(atr);
        }

        private bool IsValidSession() {
            int hourUTC = Server.Time.Hour;
            switch(SessionFilter) {
                case 1: return hourUTC >= 15 && hourUTC < 19;  // NY Main
                case 2: return hourUTC >= 8  && hourUTC < 12;  // London Main
                default: return true;
            }
        }

        private bool IsBullishAbsorption(double barDelta) {
            var vols = Bars.TickVolumes.TakeLast(DeltaLookback).ToArray();
            double mean = vols.Average();
            double std = Math.Sqrt(vols.Select(v => Math.Pow(v - mean, 2)).Average());
            double zScore = std > 0 ? (Bars.TickVolumes.Last(0) - mean) / std : 0;
            
            return barDelta < 0 
                && zScore >= VolZThresh 
                && Bars.ClosePrices.Last(0) >= Bars.OpenPrices.Last(0);
        }

        private bool IsBearishAbsorption(double barDelta) {
            var vols = Bars.TickVolumes.TakeLast(DeltaLookback).ToArray();
            double mean = vols.Average();
            double std = Math.Sqrt(vols.Select(v => Math.Pow(v - mean, 2)).Average());
            double zScore = std > 0 ? (Bars.TickVolumes.Last(0) - mean) / std : 0;
            
            return barDelta > 0 
                && zScore >= VolZThresh 
                && Bars.ClosePrices.Last(0) <= Bars.OpenPrices.Last(0);
        }

        private double _prevCVD = 0;
        private bool IsCVDBullDiverge() {
            bool rising = _cvd > _prevCVD;
            _prevCVD = _cvd;
            return rising;
        }
        private bool IsCVDBearDiverge() { return _cvd < _prevCVD; }

        private (double poc, double vah, double val) CalculateVolumeProfile() {
            int bins = 50;
            double highRange = Bars.HighPrices.Maximum(VPBars);
            double lowRange  = Bars.LowPrices.Minimum(VPBars);
            double binSize   = (highRange - lowRange) / bins;
            
            if(binSize <= 0) return (Symbol.Bid, Symbol.Bid, Symbol.Bid);
            
            double[] volBins = new double[bins];
            for(int i = 0; i < VPBars; i++) {
                int bin = (int)Math.Floor((Bars.ClosePrices.Last(i) - lowRange) / binSize);
                if(bin >= 0 && bin < bins)
                    volBins[bin] += Bars.TickVolumes.Last(i);
            }
            
            int pocBin = Array.IndexOf(volBins, volBins.Max());
            double poc = lowRange + pocBin * binSize + binSize * 0.5;
            
            // Value Area = 70% of total volume around POC
            double totalVol = volBins.Sum();
            double targetVol = totalVol * 0.70;
            double vaVol = volBins[pocBin];
            int vahBin = pocBin, valBin = pocBin;
            
            while(vaVol < targetVol && (vahBin < bins-1 || valBin > 0)) {
                double upVol   = vahBin < bins-1 ? volBins[vahBin+1] : 0;
                double downVol = valBin > 0       ? volBins[valBin-1] : 0;
                if(upVol >= downVol && vahBin < bins-1) { vahBin++; vaVol += upVol; }
                else if(valBin > 0) { valBin--; vaVol += downVol; }
                else break;
            }
            
            double vah = lowRange + vahBin * binSize + binSize;
            double val = lowRange + valBin * binSize;
            
            return (poc, vah, val);
        }

        private double CalculateLots(double slDistance) {
            double riskAmount = Account.Equity * RiskPct / 100;
            double pipValue = Symbol.PipValue;
            double slPips = slDistance / Symbol.PipSize;
            
            if(slPips <= 0 || pipValue <= 0) return Symbol.VolumeInUnitsMin;
            
            double lots = riskAmount / (slPips * pipValue);
            double minLots = Symbol.VolumeInUnitsMin / Symbol.LotSize;
            double maxLots = Symbol.VolumeInUnitsMax / Symbol.LotSize;
            
            return Math.Max(minLots, Math.Min(maxLots, lots));
        }

        private void ManagePositions(double atr) {
            foreach(var pos in Positions) {
                if(pos.TradeType == TradeType.Buy) {
                    double newSL = Symbol.Bid - atr * TrailATR;
                    if(pos.StopLoss == null || newSL > pos.StopLoss)
                        ModifyPosition(pos, newSL, pos.TakeProfit);
                    if(!IsValidSession()) ClosePosition(pos);
                }
                else if(pos.TradeType == TradeType.Sell) {
                    double newSL = Symbol.Ask + atr * TrailATR;
                    if(pos.StopLoss == null || newSL < pos.StopLoss)
                        ModifyPosition(pos, newSL, pos.TakeProfit);
                    if(!IsValidSession()) ClosePosition(pos);
                }
            }
        }

        private void CloseAllTrades() {
            foreach(var pos in Positions) ClosePosition(pos);
        }
    }
}
```

---

## PART 6: ALL INDICATOR PINE SCRIPTS — REFERENCE

### 6.1 AI Smart Order Flow Volume Candles
**Source**: AI Smart Order Flow Volume Candles.pdf

```pine
//@version=6
indicator("AI Smart Order Flow Volume Candles", overlay=true, max_boxes_count=50)

volMultiplier = input.float(1.8, "Volume Spike Multiplier")
rr = input.float(2.0, "Risk Reward")

// Buy/Sell volume estimation
buyVol = close > open ? volume : volume * 0.4
sellVol = close < open ? volume : volume * 0.4
delta = buyVol - sellVol

// Volume spike
volMA = ta.sma(volume, 20)
volSpike = volume > volMA * volMultiplier

// Liquidity sweep detection
liqBuy = low < ta.lowest(low, 10)[1] and close > open
liqSell = high > ta.highest(high, 10)[1] and close < open

// Signal conditions
buySignal = liqBuy and delta > 0 and volSpike
sellSignal = liqSell and delta < 0 and volSpike

// ATR-based SL/TP
atr = ta.atr(14)
buySL = close - atr
buyTP = close + atr * rr
sellSL = close + atr
sellTP = close - atr * rr

// Candle coloring
candleColor = delta > 0 and volSpike ? color.lime :
              delta < 0 and volSpike ? color.red :
              close > open ? color.green : color.maroon
barcolor(candleColor)

plotshape(buySignal,  location=location.belowbar, style=shape.labelup,   color=color.green, text="BUY")
plotshape(sellSignal, location=location.abovebar,  style=shape.labeldown, color=color.red,   text="SELL")
```

### 6.2 Absorption Signals (JacobS369) — Full Source
**Source**: ilovepdf_merged-5.pdf (Pages 1-15)

```pine
//@version=6
indicator("Absorption Signals", shorttitle="Absorption", overlay=true, max_labels_count=500)
import TradingView/ta/8

// INPUTS
abs_volume_lookback   = input.int(20, "Volume Lookback Period", minval=10)
abs_zscore_threshold  = input.float(1.5, "Volume Z-Score Threshold", step=0.1, minval=1.0)
abs_wick_threshold    = input.float(0.30, "Minimum Wick Size %", step=0.05, minval=0.1, maxval=0.9)
abs_delta_ltf         = input.timeframe("1", "Delta Timeframe")
abs_min_confidence    = input.int(2, "Minimum Stars to Display", minval=1, maxval=5)
abs_require_multi_bar = input.bool(true, "Require Multi-Bar Confirmation")
abs_multi_bar_tolerance = input.float(0.3, "Multi-Bar Tolerance (% ATR)", step=0.1)
abs_show_bubbles      = input.bool(true, "Show Absorption Bubbles")
abs_show_labels       = input.bool(true, "Show Confidence Labels")
abs_show_dashboard    = input.bool(true, "Show Dashboard")
abs_bubble_transparency = input.int(30, "Bubble Transparency", minval=0, maxval=100)

// CALCULATIONS
abs_atr = ta.atr(14)
[openVolume, maxVolume, minVolume, bar_delta] = ta.requestVolumeDelta(abs_delta_ltf)

avg_volume    = ta.sma(volume, abs_volume_lookback)
stdev_volume  = ta.stdev(volume, abs_volume_lookback)
volume_zscore = stdev_volume > 0 ? (volume - avg_volume) / stdev_volume : 0
volume_anomaly = volume_zscore >= abs_zscore_threshold

bar_range      = high - low
upper_wick     = high - math.max(open, close)
lower_wick     = math.min(open, close) - low
upper_wick_pct = bar_range > 0 ? upper_wick / bar_range : 0
lower_wick_pct = bar_range > 0 ? lower_wick / bar_range : 0

avg_delta     = ta.sma(bar_delta, abs_volume_lookback)
stdev_delta   = ta.stdev(bar_delta, abs_volume_lookback)
delta_zscore  = stdev_delta > 0 ? (bar_delta - avg_delta) / stdev_delta : 0

bullish_absorption = bar_delta < 0 and volume_anomaly and (close >= open)
bearish_absorption = bar_delta > 0 and volume_anomaly and (close <= open)

// Confidence: 1-5 stars
var float bull_confidence = 0.0
var float bear_confidence = 0.0

if bullish_absorption
    bull_confidence := 1.0
    if volume_zscore >= 2.0 : bull_confidence += 1.0
    if volume_zscore >= 3.0 : bull_confidence += 1.0
    if math.abs(delta_zscore) >= 2.0 : bull_confidence += 1.0
    if lower_wick_pct >= 0.4 : bull_confidence += 1.0
    bull_confidence := math.min(bull_confidence, 5.0)
else
    bull_confidence := 0.0

if bearish_absorption
    bear_confidence := 1.0
    if volume_zscore >= 2.0 : bear_confidence += 1.0
    if volume_zscore >= 3.0 : bear_confidence += 1.0
    if math.abs(delta_zscore) >= 2.0 : bear_confidence += 1.0
    if upper_wick_pct >= 0.4 : bear_confidence += 1.0
    bear_confidence := math.min(bear_confidence, 5.0)
else
    bear_confidence := 0.0
```

### 6.3 Aegis VEP_CBP Hybrid
**Source**: ilovepdf_merged-5.pdf

```pine
//@version=5
indicator("Aegis VEP_CBP Hybrid [wjdtks255]")

lenMA = input.int(50, "Volume MA Period")
lookback = input.int(10, "Pivot Lookback")

vMA = ta.sma(volume, lenMA)
isUp = close > close[1]
isDown = close < close[1]

float maxD = 0.0, float maxU = 0.0
for i = 1 to lookback
    if close[i] < close[i+1]: maxD := math.max(maxD, volume[i])
    if close[i] > close[i+1]: maxU := math.max(maxU, volume[i])

isPPV = isUp and volume > maxD
isBPV = isDown and volume > maxU

cRange = math.max(high - low, syminfo.mintick)
net_p = volume * ((close - low) - (high - close)) / cRange
sMA = ta.ema(net_p, 20)

bull_signal = isPPV and net_p > sMA  // Golden Bull
bear_signal = isBPV and net_p < sMA  // Death Bear

bgcolor(net_p > 0 ? color.new(color.green, 95) : color.new(color.red, 95))
plotshape(bull_signal, "Golden Bull", shape.triangleup,   location.belowbar, color.yellow, 0)
plotshape(bear_signal, "Death Bear",  shape.triangledown, location.abovebar, color.purple, 0)
```

---

## PART 7: RISK MANAGEMENT RULES

### 7.1 Hard Rules (Non-Negotiable)
```
1. NO OVERNIGHT POSITIONS — Close all before market close (Fabio Valentini rule)
2. MAX 1% RISK PER TRADE — Never risk more than 1% of account per trade
3. MAX 5% DAILY DRAWDOWN — Stop trading if daily loss exceeds 5%
4. SESSION DISCIPLINE — Only trade designated session windows
5. ASIAN SESSION = NO TRADE — Do not trade 01:00-08:00 SAST
6. NEWS BLACKOUT — No trades 15 min before/after major news events
7. MAGIC NUMBER ISOLATION — All EA trades tagged with unique magic number
8. MAX SPREAD GUARD — Don't trade if spread > 2x normal
```

### 7.2 Position Sizing Formula
```
Risk Amount = Account Equity × Risk% / 100
SL Distance (pips) = Entry - Stop Loss
Pip Value = Contract Size × Tick Value / Tick Size
Lots = Risk Amount / (SL Pips × Pip Value)

Example:
Account: $10,000, Risk: 1% = $100
SL: 20 pips, Pip Value: $10/pip
Lots = $100 / (20 × $10) = 0.5 lots
```

### 7.3 Trade Scoring System
Before entering any trade, score it 1-5:
- +1: Price at key VP level (POC/VAH/VAL/LVN)
- +1: Delta confirms direction
- +1: CVD divergence confirms
- +1: Absorption signal present
- +1: Session timing correct

**Minimum Score to Enter**: 3/5
**A+ Setup (Full Position)**: 5/5
**B+ Setup (Half Position)**: 3-4/5

---

## PART 8: EA GENERATION INSTRUCTIONS FOR CLAUDE CODE

When a user asks to build an Order Flow EA, follow this sequence:

### Step 1: Determine Platform
- MT5 → Generate MQL5 `.mq5` file
- cTrader → Generate cAlgo C# `.cs` file
- Both → Generate both files

### Step 2: Strategy Parameters Required
Ask for or infer:
- Model (1=Trend, 2=MeanReversion, 3=Hybrid)
- Session (NY/London/Both)
- Primary signals (Delta, CVD, Absorption, VP, LVN, Footprint)
- Risk parameters (% risk, RR ratio, max DD)
- Timeframe (M1, M5, M15, H1)

### Step 3: Code Generation Checklist
```
□ Include all required libraries/imports
□ Add grouped input parameters with descriptions
□ Implement tick data access for delta calculation
□ Build Volume Profile from bar data
□ Implement absorption detection with Z-score
□ Add CVD tracking and divergence detection
□ Code session time filter (SAST or UTC)
□ Implement position sizing (% risk based)
□ Add trailing stop management
□ Add daily drawdown kill switch
□ Add magic number isolation
□ Add spread guard
□ Add dashboard/visualization (optional)
□ Include entry/exit logging
□ Compile-ready (no missing semicolons/brackets)
```

### Step 4: Volume Profile Implementation Priority
For MT5: Use `CopyTicksRange()` for true tick-based VP
For cTrader: Use `Symbol.Ticks` subscription + `MarketData.GetBars()`
For Pine: Use `ta.requestVolumeDelta()` + bar-based approximation

### Step 5: Testing Protocol
```
1. Backtest: Min 6 months data, matching native tick data
2. Optimize: Delta threshold, Vol Z-score, VP length
3. Forward test: 1 month demo before live
4. Live: Start at 0.25× position size for first 2 weeks
```

---

## PART 9: STRATEGY CATALOG

### Strategy 1: Absorption Reversal (Fabio Valentini + JacobS369)
**Type**: Mean Reversion (Model 2)
**Session**: London Main
**Entry**: Bullish absorption at VAL or bearish absorption at VAH
**Confirmation**: CVD divergence + volume Z-score ≥ 1.5
**Stop**: Below swing low (bull) / Above swing high (bear) + 0.5 ATR
**Target**: POC (mean reversion target)
**RR**: Minimum 1.5:1

### Strategy 2: LVN Acceleration (Carmine)
**Type**: Trend Following (Model 1)
**Session**: NY Main
**Entry**: Price breaks into LVN zone from HVN with delta confirmation
**Confirmation**: Stacked imbalances on lower TF
**Stop**: Back at HVN edge
**Target**: Next HVN or major POC
**RR**: Minimum 2:1

### Strategy 3: CVD Divergence Fade
**Type**: Mean Reversion
**Entry**: Price at new high/low but CVD diverges (not confirming)
**Confirmation**: Volume spike at extreme + absorption signal
**Stop**: Beyond the price extreme
**Target**: Previous session POC
**RR**: Minimum 1.8:1

### Strategy 4: VEP + CBP Breakout (Aegis)
**Type**: Trend Following
**Entry**: Golden Bull signal (isPPV + net_p > sMA) above VAH
**Confirmation**: Volume expansion + bullish close
**Stop**: Below VAH
**Target**: 2× ATR extension
**RR**: Minimum 2:1

### Strategy 5: Wyckoff Spring Long
**Type**: Accumulation Reversal
**Entry**: Price springs below accumulated support + immediate recovery + bullish absorption
**Confirmation**: CVD bullish divergence + volume climax at low
**Stop**: Below spring low × 1.5
**Target**: Top of trading range / Resistance
**RR**: Minimum 2.5:1

---

## PART 10: PLATFORM-SPECIFIC NOTES

### MT5 Specific
- Use `CopyTicksRange()` for REAL tick data (not simulated)
- Require symbol with COPY_TICKS_TRADE enabled
- `iVolume()` returns tick volume (approximate for forex)
- For CFDs/futures, volume is more accurate
- Test with `StrategyTester` using "Every tick based on real ticks" mode
- MT5 natively handles multiple timeframe analysis via `iClose(sym, tf, bar)`

### cTrader Specific
- cBot uses `[Robot]` attribute, Indicators use `[Indicator]`
- `Ticks.Subscribe()` enables real-time tick processing
- `MarketData.GetTicks()` for historical tick access
- `Symbol.QuantityToVolumeInUnits()` converts lots to units
- Use `TimeZones` parameter for session management
- All API calls are asynchronous — use `BeginInvokeOnMainThread` for UI
- cTrader has native Volume Profile in Pro plan charts

### Pine Script Specific
- `ta.requestVolumeDelta()` requires Premium subscription
- True tick-level footprint NOT available in Pine
- Use `request.security_lower_tf()` for intrabar data (limited)
- Pine runs on TradingView server — backtesting is OHLCV only
- Cannot connect to live broker directly (must use webhooks)

---

---

## PART 11: FABIO VALENTINI — EXPANDED PROTOCOLS (REF-04)

### 11.1 Triple-A Sequence (Absorption → Accumulation → Aggression)
```
PHASE 1: ABSORPTION
├─ Heavy one-sided flow hits level; price barely moves
├─ Large volume, low range = institution passively absorbing
└─ Footprint: massive sell vol at low but no new low (bullish)

PHASE 2: ACCUMULATION
├─ Volume contracts; range tightens
├─ Retail exits ("nothing happening")
└─ Institution finished building position — coil forming

PHASE 3: AGGRESSION  ← ENTRY TRIGGER
├─ ≥30 NQ / ≥50 ES contracts appear suddenly
├─ CVD spikes in direction
└─ Price breaks cleanly through accumulation zone → ENTER
```

### 11.2 Model 1 — Trend Continuation (5 Steps)
Activation: Open outside prior VA | trending CVD | NY session preferred
1. Mark impulse leg → find LVN in retracement zone → set alert
2. Wait for retracement to LVN/HVN (never enter on initial impulse)
3. Confirm absorption: sellers arriving but price not falling; CVD stalls
4. Enter on aggression print (≥30 NQ): SL = 1–2 ticks below aggression candle low
5. Target: prior POC (70% reversal probability there)

**Invalidation**: Price reclaims prior VA | CVD diverges against | large opposing absorption | 3rd consecutive loss

### 11.3 Model 2 — Mean Reversion (5 Steps)
Activation: Open inside prior VA | D-shape profile developing | CVD oscillating | London session
1. Identify balance zone (VAH/VAL boundaries; POC = primary target)
2. Watch for failed breakdown: price probes below VAL, sellers don't follow with CVD
3. Price reclaims inside VAL = confirmed false break
4. Enter at LVN on aggression (≥30 contracts): SL = 1–2 ticks beyond extreme of failed probe
5. Target: session POC (100% exit — never stretch further)

**Critical**: Stop NOT at obvious swing low. Stop 1–2 ticks beyond aggression candle.

### 11.4 LVN Execution Protocol
| Situation | Action |
|-----------|--------|
| LVN in imbalanced market | Support for Model 1 pullback re-entry |
| LVN in balanced market | Absorption check → potential Model 2 entry |
| Any LVN arrival | NEVER blind limit. Set alert 1–2 ticks early. Read OF on arrival. |

### 11.5 Session Timing (SAST / UTC+2) — Expanded
| Session | SAST | Model | Rule |
|---------|------|-------|------|
| Asian | 02:00–10:00 | — | No Trade |
| London Open | 10:00–11:00 | M1 Selective | Optional |
| **London Main** | **11:00–15:30** | **M2 Primary** | Primary window |
| NY Open | 15:30–15:50 | — | **20-min blackout** |
| **NY Main** | **15:50–21:00** | **M1 Primary** | Best trend window |
| After Market | 21:00+ | — | Close All (automate) |

**NY 20-Minute Rule**: No entry 15:30–15:50 SAST. Clarity forms 15:50–16:15.

### 11.6 Stop Loss Philosophy (Fabio)
- ❌ Retail trap: stop at obvious swing H/L → hunted by algos
- ✅ Aggression-based stop: 1–2 ticks beyond entry trigger candle
- Move to BE when: CVD confirms pressure OR price reaches 1:1
- If CVD reverses aggressively → manual exit before stop hits (never average down)

### 11.7 Exit Discipline — The 70% Rule
Exit 100% at target POC. Probability of reversal at POC ≈ 70%. Do not hold through POC hoping for extension.

---

## PART 12: WYCKOFF 2.0 DEEP VERIFICATION (REF-05)

### 12.1 Spring Confirmation Checklist (Modern OF Layer)
```
✅ Price breaks below SC (Selling Climax) level
✅ Volume on break is BELOW SC volume (less supply = genuine shakeout)
✅ Candle closes back ABOVE SC level (wick rejection)
✅ CVD bullish divergence: CVD higher low vs price lower low
✅ Footprint: heavy sell vol at spring low but price doesn't extend
✅ SOS follow-through within 3–5 bars
```
**Fail condition**: Spring bar volume > SC volume → genuine breakdown, not a Spring.

### 12.2 Spring Entry Protocol
```
Entry:  Close of recovery candle above SC (or LTF confirmation)
SL:     3–5 ticks below spring low (TIGHT — only invalidation)
TP1:    AR (Automatic Rally level)
TP2:    Top of accumulation range
TP3:    Extended markup (trail only after SOS confirmed)
R:R:    Minimum 4:1 → typical 6:1–10:1
```

### 12.3 Wyckoff + Volume Profile Integration
| Wyckoff Event | VP Equivalent | Model |
|---------------|--------------|-------|
| SC low | HVN / VAL | Climax volume = institutional buy zone |
| Phase B range | D-Shape profile | Balanced accumulation → apply Model 2 |
| Spring | Below VAL / LVN test | Highest-conviction Model 2 entry |
| SOS breakout | New value area developing | Switch to Model 1 above AR |

### 12.4 Distribution — Upthrust Protocol
- False break ABOVE Phase B range top (BC)
- Volume < BC volume (no real demand)
- Candle closes back below range top
- CVD bearish divergence at upthrust high
- Footprint: heavy buy vol absorbed but price doesn't advance
- Entry: close below range top | SL: 3–5 ticks above upthrust | TP: AR level

---

## PART 13: 83-MIN OFT SYSTEM — DECISION TREE & MATH (REF-06)

### 13.1 The OFT Edge Formula
```
Edge = Location × Signal × Context

Location: Key VP level (LVN/HVN/POC/VAH/VAL) or structural level
Signal:   Absorption | Stacked Imbalance | Unfinished Auction
Context:  Kill zone + HTF alignment + CVD direction

All three present → HIGH PROBABILITY SETUP
Any one missing → SKIP (or half size maximum)
```

### 13.2 Session Decision Tree
```
Price at key level?       NO → Wait
Kill zone active?         NO → Wait (exceptional only)
CVD supports direction?   NO → Skip
Footprint signal?
  Absorption bottom/top   → Reversal setup
  Stacked imbalances      → Trend continuation
  Unfinished auction      → Fade/target
  None                    → Skip
5M CHOCH confirming?      NO → Wait
All YES                   → EXECUTE (SL and TP defined BEFORE entry)
```

### 13.3 Footprint Signals Reference
| Signal | Pattern | Trade |
|--------|---------|-------|
| Absorption Bottom | High sell vol at support, no new low | Long after confirmation close |
| Absorption Top | High buy vol at resistance, no new high | Short after confirmation close |
| Stacked Bull Imbalance | 3+ consecutive buy-dominant rows | Long on pullback to zone |
| Stacked Bear Imbalance | 3+ consecutive sell-dominant rows | Short on pullback to zone |
| Unfinished Auction | 0 vol at bar extreme | Fade extreme / set as target |

### 13.4 Statistical Edge (500+ Trade Backtest)
```
Win Rate: 48–54%  |  Avg Win: 2.8R  |  Avg Loss: 1.0R
Expectancy = (0.51 × 2.8) − (0.49 × 1.0) = +0.94R per trade
At 50 trades/month, 1% risk → +$23,500/month EV on $50K account
```

### 13.5 Entry Priority Hierarchy
| Priority | Condition | Size |
|----------|-----------|------|
| 1 | Absorption at VP level + CVD divergence | Full |
| 2 | Stacked imbalance at VP level + CVD confirm | Full |
| 3 | Absorption at VP level only | Half |
| 4 | Stacked imbalance only (no VP level) | Skip |
| 5 | Single signal only | Skip |

---

## PART 14: ADVANCED GLOSSARY ADDENDUM (REF-03)

### Microstructure Terms
| Term | Definition |
|------|-----------|
| Iceberg Order | Large limit order, only small visible portion. Refreshes automatically. Footprint shows far more volume than DOM suggested. Legal. |
| Spoofing | Large DOM order placed with no intent to fill. Disappears before price arrives. Illegal. No footprint volume. |
| Unfinished Auction | Footprint extreme with 0 volume on one side. Price ALWAYS returns to complete. Use as profit target. |
| MBO (Market By Order) | Most granular data — each individual order in book. CME provides for futures. |

### ICT/SMC Terms (Addendum)
| Term | Definition |
|------|-----------|
| SMT Divergence | Two correlated pairs making opposite structure at key level (e.g. EURUSD new low, GBPUSD doesn't) → reversal signal |
| Breaker Block | Failed OB that gets violated — flips to opposing direction. Highest-probability POI in ICT. |
| IPDA | ICT's interbank price delivery algorithm. Price programmed to reach PDRA levels in defined time windows. |
| Poor High/Low | Profile extreme with single print, minimal volume. Price will always return to retest properly. |
| Single Print | TPO level occurring in one bracket only = LVN gap. Market will fill. |

### Wyckoff Terms (Addendum)
| Term | Definition |
|------|-----------|
| Composite Man | Conceptual institutional aggregate. Mental model for attributing institutional intent to price phases. |
| Initial Balance (IB) | AMT: price range of first trading hour. Breakouts above/below IB set directional expectations for session. |
| SOW (Sign of Weakness) | Wyckoff: price breaks below support with high volume. Confirms distribution complete. Short on next LPSY. |

---

## PART 15: VIDEO CURRICULUM INDEX (REF-01)

### Fastest Concept Routes
| Topic | Primary Video | Secondary |
|-------|--------------|-----------|
| OF Foundations | V01 Darius FX | V02 Trading Geek → V10 Mind Math |
| Volume Profile | V11 Fractal Flow | V15 ICT+VP fusion |
| Footprint/Delta | V01 → V02 | V10 Sections 3–4 |
| CVD | V01 Section 3 | V02 → V10 |
| Wyckoff | V20 Fractal Flow (definitive) | V07 Fabervaale AMT |
| SMC/ICT | V19 Trading Discussion | V21 Full SMC Course |
| Liquidity | V14 Fractal Flow | V27 Chart Fanatics |
| Market Structure | V22 JeaFx | V23 Fractal Flow |
| Live Execution | V18 Umar Ashraf | V25/V28/V29 Chart Fanatics |
| Bookmap/DOM | V09 MasiTrades | V08 Words of Rizdom |
| Algo/Systematic | V26 Chart Fanatics | — |
| AMT | V07 Fabervaale (2hr Italian) | V12 Fabervaale English |
| Prop Firm | V24 Chart Fanatics | V26 Algo |

### A+ Grade Setups (Cross-Video)
1. **Liquidity Sweep Reversal** (V14/V17/V27/V30): BSL/SSL sweep + rejection + CHOCH
2. **OB + CVD Confirmation** (V06/V15/V19/V21): OB return + OF confirm
3. **Wyckoff Spring at VP Support** (V20/V11): 4:1–8:1 R:R
4. **Absorption Reversal** (V01/V02/V10): Passive absorption + CVD divergence
5. **ICT AMD Model** (V30/V31): PDRA + Kill Zone + SMT divergence
6. **LVN Acceleration** (V11/V04): Clean breakout through thin volume
7. **CVD Divergence Fade** (V01/V02/V10): Price/CVD divergence at structural level

### Learning Paths
- **EA/Automation**: V01 → V10 → V11 → V26 → V04 → Fabio Valentini Encyclopedia
- **Prop Firm Fast Track**: V23 → V14 → V30 → V24 → V10 → V26 → V29
- **SMC→OF Integration**: V22 → V23 → V21 → V19 → V15 → V06 → V01 → V10

---

*GODMODE ORDER FLOW MASTERY SKILL v3.0 — Extended Reference Integration*
*Source documents: 69+ PDFs + REF-01 through REF-07 video curriculum + advanced glossary*
*Primary: Fabio Valentini AMT | Wyckoff 2.0 Villahermosa | JacobS369 Absorption*
*Supporting: Darius FX foundations | Mind Math Money 83-min system | Chart Fanatics live*
*REF Integration: 2026-04-21 | Token-efficient append via PULSE LEAN ENGINE*
