# ORDERFLOW DIVE 2.0
## The Complete Institutional-Grade Order Flow Mastery Reference
### Synthesized from 69+ Source Documents — GODMODE Edition

> **Compiled**: April 2026 | **Sources**: 69 PDFs, Pine Script indicators, academic papers, strategy guides
> **Author Framework**: Fabio Valentini (AMT) + Rubén Villahermosa Chaves (Wyckoff 2.0) + JacobS369 (Absorption) + Trader Dale (Volume Profile) + Carmine (LVN) + Multiple institutional frameworks
> **Purpose**: Master reference for order flow trading and EA robot development on MT5 & cTrader

---

## TABLE OF CONTENTS

1. [What Is Order Flow Trading](#1-what-is-order-flow-trading)
2. [Market Microstructure](#2-market-microstructure)
3. [Market Auction Theory (AMT)](#3-market-auction-theory-amt)
4. [Delta & Cumulative Volume Delta](#4-delta--cumulative-volume-delta)
5. [Volume Profile — Complete System](#5-volume-profile--complete-system)
6. [Footprint Charts](#6-footprint-charts)
7. [Absorption Theory & Detection](#7-absorption-theory--detection)
8. [Wyckoff 2.0 Integration](#8-wyckoff-20-integration)
9. [Order Flow Indicators — Full Catalog](#9-order-flow-indicators--full-catalog)
10. [Trading Strategies — Complete Playbook](#10-trading-strategies--complete-playbook)
11. [Session Timing & Market Structure](#11-session-timing--market-structure)
12. [Risk Management System](#12-risk-management-system)
13. [Platform Comparison: MT5 vs cTrader vs TradingView](#13-platform-comparison-mt5-vs-ctrader-vs-tradingview)
14. [Pine Script → MQL5 → cAlgo Conversion](#14-pine-script--mql5--calgo-conversion)
15. [EA Building Blueprints](#15-ea-building-blueprints)
16. [Prop Firm Compliance Rules](#16-prop-firm-compliance-rules)
17. [Academic & Institutional Research](#17-academic--institutional-research)

---

## 1. WHAT IS ORDER FLOW TRADING

Order flow trading is the analysis of actual buy and sell orders as they occur in the market — not lagging price patterns or statistical indicators derived from historical closes. It is the art of reading the war between aggressive buyers and sellers at the tick level.

**The Fundamental Insight** (Trader Dale, Volume Profile Insider Guide):
Price moves because of AGGRESSION, not because there are more buyers than sellers. At any price, there is always a buyer AND a seller. What matters is who is aggressive — the market order sender — versus who is passive — the limit order provider.

**Why 96.5% of forex retail volume is institutional** (Bank for International Settlements data): Retail traders represent only 3.5% of daily forex volume. The remaining 96.5% is controlled by institutions: banks, hedge funds, central banks, sovereign wealth funds. Order flow analysis is the method of tracking what institutions are actually doing — not what they say.

**The Three Pillars of Order Flow**:
1. **Where** transactions occur → Volume Profile (horizontal volume distribution)
2. **Who** is aggressive vs passive → Delta and Footprint (directional aggression)
3. **When** the balance shifts → Absorption and CVD divergence (reversal timing)

**Key Advantage Over Technical Analysis** (Technical Analysis vs Order Flow guide):
- TA uses lagging price derivatives (MA, RSI, MACD)
- Order flow uses REAL-TIME transaction data
- TA sees what happened; Order flow sees WHY it happened
- TA is reactive; Order flow is causal

---

## 2. MARKET MICROSTRUCTURE

### 2.1 The Order Book
The order book is the central nervous system of any market. It contains:
- **Bid Side**: Limit buy orders stacked at prices below current
- **Ask Side**: Limit sell orders stacked at prices above current
- **Spread**: Gap between best bid and best ask
- **Depth**: Volume of orders at each level

**How Price Moves**:
- Market buy order hits the ask → consumes ask liquidity → price ticks up
- Market sell order hits the bid → consumes bid liquidity → price ticks down
- Large limit orders defend levels → price bounces (absorption)
- Liquidity vacuum (thin order book area) → price accelerates through

### 2.2 Types of Orders
| Order Type | Description | Who Uses It | Effect |
|------------|-------------|-------------|--------|
| Market Order | Execute immediately at best available price | Aggressive traders | Moves price |
| Limit Order | Execute at specific price or better | Passive traders, institutions | Provides liquidity |
| Stop Order | Triggered when price reaches level | Breakout traders, stops | Can cascade moves |
| Stop Limit | Limit order triggered by stop | Precision entry | Hybrid |
| Iceberg Order | Large order hidden, shows only portion | Institutions | Concealed accumulation |
| Dark Pool | Off-exchange execution | Large institutions | Off-book |

### 2.3 Tick Data — The Foundation
**Definition**: Every individual transaction at the lowest granularity level.
- Each tick = one matched order (buyer + seller meeting)
- Tick data reveals: exact price, volume, direction (buy/sell classification)
- **Trade Classification**: If price = ask → buyer aggressive (uptick). If price = bid → seller aggressive (downtick).
- **Lee-Ready Algorithm**: Standard method for classifying trades as buyer or seller initiated

### 2.4 Electronic Market Ecosystem (Wyckoff 2.0 / Villahermosa)
Modern markets are dominated by:
- **HFT (High Frequency Trading)**: Microsecond execution, market making, statistical arbitrage
- **Algorithmic Trading**: Rule-based systems executing at millisecond speeds
- **Dark Pools**: Off-exchange venues for large institutional block trades (avoid price impact)
- **OTC Markets**: Bilateral agreements, especially in forex (decentralized)

**Implication for Order Flow**: In electronic markets, the order book is dynamic and subject to spoofing (fake orders placed then cancelled). True committed volume only shows up in the TAPE (executed transactions) — which is what delta and volume profile capture.

---

## 3. MARKET AUCTION THEORY (AMT)

### 3.1 Foundation (Fabio Valentini / ChartFanatics)
**Source**: fabio-valentini-strategy-guide.pdf — 500%+ annual return documented

Market Auction Theory states that markets are continuous two-sided auctions seeking fair value. Price moves to attract trade and discover where buyers and sellers find equilibrium.

**The Two States of Market**:

**BALANCE (Equilibrium)** — 70-80% of time:
- Buyers and sellers roughly equal in aggression
- Price oscillates in a range
- Institutions are accumulating or distributing
- Opportunity: Mean Reversion (Model 2)
- Indicators: Low directional delta, CVD flat, tight volume profile

**IMBALANCE (Directional)** — 20-30% of time:
- One side is significantly more aggressive
- Price trends directionally
- Institutions are executing large positions
- Opportunity: Trend Following (Model 1)
- Indicators: High directional delta, CVD diverging, expanding volume profile

### 3.2 The Two Trading Models

**Model 1 — Trend Following** (NY Main Session Primary):
- Wait for clear market imbalance
- Enter in direction of dominant delta
- Use CVD confirmation
- Trail stop as momentum continues
- Close at session end
- Best instruments: NQ (Nasdaq-100 Futures), ES (S&P 500 Futures)

**Model 2 — Mean Reversion** (London Main Session Primary):
- Wait for balanced market at extremes
- Enter AGAINST price at VAH/VAL with absorption confirmation
- Target POC as reversion point
- Tight stop outside value area
- Risk:Reward minimum 1.5:1

### 3.3 Auction Market Four Steps (Villahermosa)
1. **Consolidation**: Price finds equilibrium, volume builds at fair value
2. **Breakout**: Price leaves value area with high volume — imbalance begins
3. **Trend**: New value area being created in new territory
4. **Return to Value**: If breakout fails, price auctions back to old value

### 3.4 VWAP as Auction Anchor
**VWAP (Volume Weighted Average Price)**: The volume-weighted mean of all transactions. Institutional benchmark.
- Price above VWAP = buyers dominating, long bias
- Price below VWAP = sellers dominating, short bias
- Price at VWAP = equilibrium, directional decision point
- **Anchored VWAP**: VWAP from significant pivot (earnings, market open, swing high/low)

---

## 4. DELTA & CUMULATIVE VOLUME DELTA

### 4.1 Bar Delta
**Formula**: Delta = Aggressive Buy Volume − Aggressive Sell Volume

Calculated per bar by aggregating all tick data within that bar's time window.

**Interpretation**:
| Delta | Implication |
|-------|-------------|
| Large positive, price up | Normal bullish — trend likely continuing |
| Large positive, price down | Bearish absorption — institutions selling into buys |
| Large negative, price down | Normal bearish — trend continuing |
| Large negative, price up | Bullish absorption — institutions buying into sells |
| Near zero, price unchanged | Equilibrium — no conviction |
| Near zero, price moving | Passive trend — iceberg orders driving move |

### 4.2 CVD (Cumulative Volume Delta)
**Formula**: CVD[n] = CVD[n-1] + Delta[n] (running sum)

**The Most Powerful Signal — CVD Divergence**:

**Bearish CVD Divergence**: Price makes new HIGH but CVD is LOWER than previous high
→ Interpretation: Sellers absorbing every buy push. Institutions distributing. Price reversal likely.
→ Trade: Short at new high, stop above high, target previous support

**Bullish CVD Divergence**: Price makes new LOW but CVD is HIGHER than previous low
→ Interpretation: Buyers absorbing every sell push. Institutions accumulating. Price reversal likely.
→ Trade: Long at new low, stop below low, target previous resistance

### 4.3 Institutional Size Filters (Fabio Valentini)
Not all delta spikes are institutional. Use these filters:
- **NQ (Nasdaq-100)**: Minimum 30 contracts for institutional footprint
- **ES (S&P 500)**: Minimum 15 contracts for institutional footprint
- **Forex**: 500+ lots for institutional signal
- Context matters — apply during key time windows only

### 4.4 Delta Indicators in the Catalog

**AI Smart Order Flow Volume Candles** (VenusJ):
- Estimates buyVol = volume if close > open, else volume × 0.4
- Detects liquidity sweeps (liqBuy = low breaks 10-bar low then recovers)
- Signal: liqBuy AND delta > 0 AND volume spike = BUY
- Colors candles: lime (bullish delta spike), red (bearish delta spike)

**Delta Flow Volume Profile (UAlgo)**:
- Combines real-time delta with volume profile display
- Shows positive/negative delta at each VP price level
- Identifies delta imbalance within value area

**Institutional Delta Sweeps (BOSWaves)**:
- Detects large delta sweeps at structural levels
- Multi-timeframe delta alignment
- Generates sweep signals for trend confirmation

---

## 5. VOLUME PROFILE — COMPLETE SYSTEM

### 5.1 What Volume Profile Shows
Volume Profile displays how much volume was traded at each price level over a defined period. It answers the question: WHERE do buyers and sellers agree on value?

This is fundamentally different from regular (vertical) volume:
- Regular volume: Volume per TIME period (each bar)
- Volume Profile: Volume per PRICE level (horizontal distribution)

### 5.2 Key Levels

**Point of Control (POC)**:
- The price level with the MOST volume traded
- Represents fair value — where most transactions occurred
- Price gravitates back to POC (mean reversion)
- Acts as support/resistance after being broken

**Value Area (VA)**:
- Price range containing 70% of total session volume (±1 standard deviation principle from Market Profile)
- **VAH** (Value Area High): Upper boundary of value area
- **VAL** (Value Area Low): Lower boundary of value area
- Principle: 80% of time, price returns to value area if broken

**High Volume Node (HVN)**:
- Price level with ABOVE-AVERAGE volume
- Markets spent significant time here → acceptance/equilibrium
- Acts as price magnet — strong support/resistance
- Mean reversion targets

**Low Volume Node (LVN)**:
- Price level with BELOW-AVERAGE volume
- Markets passed through quickly → rejection/imbalance
- Price accelerates THROUGH LVNs (poor location = fast move)
- Key for LVN trading strategy (Carmine)

### 5.3 Profile Shapes (Trader Dale)
| Shape | Description | Market Condition | Trade Approach |
|-------|-------------|-----------------|----------------|
| D-Profile | Normal bell curve | Balanced, fair value accepted | Model 2 — mean reversion from extremes |
| P-Profile | Thin bottom, fat top | Bullish trend, buying above old range | Buy pullbacks to VAL |
| b-Profile | Fat bottom, thin top | Bearish trend, selling below old range | Sell rallies to VAH |
| Thin Profile | Very narrow distribution | Imbalance, breakout likely | Model 1 — trade the breakout |
| Double Distribution | Two peaks | Bimodal, uncertain direction | Wait for resolution |

### 5.4 Volume Profile Trading Setups (Trader Dale / Villahermosa)

**Setup 1: Volume Accumulation (Mean Reversion)**
- Identify POC and Value Area on daily/weekly profile
- Price moves away from value area (above VAH or below VAL)
- Wait for price to stall and show absorption at extreme
- Enter back toward POC
- Stop: Beyond the extreme level
- Target: POC (or opposite value area boundary)

**Setup 2: Trend (P or b Profile Continuation)**
- Price in trend (P or b profile shape)
- Price pulls back to VAL (in uptrend) or VAH (in downtrend)
- Confirm with bullish/bearish absorption at value area boundary
- Enter in trend direction from value area
- Stop: Below VAL (long) or above VAH (short)
- Target: Previous swing high/low or next week's profile

**Setup 3: Rejection (Failed Auction)**
- Price approaches significant HVN from outside
- Volume decreases as price approaches (no commitment)
- Delta shows opposite direction (sellers at resistance)
- Enter rejection trade
- Stop: Beyond HVN
- Target: LVN below (next significant speed zone)

**Setup 4: LVN Acceleration (Carmine Strategy)**
- Identify LVN on session/daily profile
- Price approaches LVN from a HVN
- Any momentum bar through LVN with confirming delta
- Enter immediately — price will accelerate through thin zone
- Stop: Just back inside HVN
- Target: Next HVN on the other side

### 5.5 VPOC Migration (Villahermosa)
The POC migrates upward in bullish trends and downward in bearish trends.
- Upward VPOC migration: Healthy bull trend — buy dips to VPOC
- Downward VPOC migration: Healthy bear trend — sell rallies to VPOC
- VPOC stops migrating: Trend losing momentum, expect mean reversion

### 5.6 Multi-Timeframe VP Analysis
```
Weekly VP:  Defines major POC/VA for swing context
Daily VP:   Primary trading range and levels
Session VP: Intraday POC and VA (reset each session)
Fixed Range: User-defined period — great for balance/breakout detection
```

---

## 6. FOOTPRINT CHARTS

### 6.1 What Footprints Reveal
Footprint charts show bid/ask volume at every tick level within each candle. They are the ultimate order flow tool — revealing what's happening INSIDE each candle, not just the OHLC summary.

**Structure**: Each row = one tick level
- Left column = Volume at bid (sellers hitting bids)
- Right column = Volume at ask (buyers lifting asks)
- Bold numbers = Delta = Right − Left

**Example Footprint Reading**:
```
Price 4800: 45 x 28   (Delta = -17, sellers dominant)
Price 4799: 23 x 67   (Delta = +44, buyers dominant)  ← IMBALANCE
Price 4798: 12 x 89   (Delta = +77, buyers dominant)  ← STRONG IMBALANCE
Price 4797: 34 x 21   (Delta = -13, balanced)
```

### 6.2 Key Footprint Patterns

**Bullish Imbalance Stack**:
- Multiple consecutive rows showing buy volume > sell volume by 300%+
- Usually at demand levels (VAL, LVN bounce)
- Signals institutional buying — high probability long entry

**Bearish Imbalance Stack**:
- Multiple consecutive rows showing sell volume > buy volume by 300%+
- Usually at supply levels (VAH, LVN rejection)
- Signals institutional selling — high probability short entry

**Absorption (High Volume, Low Delta)**:
- Huge total volume (buy + sell) but delta near zero
- Institutions are both buying AND selling at same level
- Classic sign of institutional accumulation/distribution
- Creates strong support/resistance

**Exhaustion Candle**:
- Candle makes new extreme (high or low) with diminishing delta
- Shows momentum is dying — reversal incoming
- Look for: Delta smaller on last new extreme vs previous extreme

**Stacked Imbalances (Multiple Candles)**:
- BOSWaves indicator: Consecutive delta-dominant candles
- Pine: bullish_imbalance[0] and bullish_imbalance[1] and bullish_imbalance[2]
- = High probability continuation zone

### 6.3 Bookmap Traps (Footprint Delta Trap / PakunFX)
**Definition**: Detecting when traders are trapped at price extremes using footprint delta data.

**Long Trap at High**:
- Price reaches new session high
- Footprint shows NEGATIVE delta at the high (sellers dominating at extreme)
- This means: Breakout buyers got trapped — they bought the high but sellers absorbed all of it
- Trade: Short the failure — trapped longs will fuel the reversal

**Short Trap at Low**:
- Price reaches new session low
- Footprint shows POSITIVE delta at low (buyers absorbing all sells)
- This means: Breakdown sellers got trapped — they shorted the low but buyers absorbed
- Trade: Long the failure — trapped shorts will fuel the reversal

---

## 7. ABSORPTION THEORY & DETECTION

### 7.1 What Is Absorption
Absorption occurs when limit orders defending a price level are replenished faster than market orders can drain them. The net effect: price STALLS despite high aggression in one direction.

**Mechanics**:
1. Market orders push price down aggressively (negative delta)
2. Large limit buy orders absorb the selling (price doesn't fall much)
3. The close ends above the open despite negative delta = BULLISH ABSORPTION
4. This is institutional buying — they are accumulating

### 7.2 Absorption Signal Detection Algorithm (JacobS369)

**Five-Factor Confidence Scoring System**:

```
Factor 1: Absorption Condition (required)
  Bullish: delta < 0 AND volume_anomaly AND close >= open
  Bearish: delta > 0 AND volume_anomaly AND close <= open

Factor 2: Volume Z-Score ≥ 2.0  (+1 star)
  Volume Z = (current_volume - avg_volume) / stdev_volume
  Z ≥ 2.0 = volume significantly above average

Factor 3: Volume Z-Score ≥ 3.0  (+1 star)
  Extreme volume = even higher institutional confidence

Factor 4: Delta Z-Score ≥ 2.0 in magnitude  (+1 star)
  Large delta opposition = more institutional absorption

Factor 5: Wick ≥ 40% of bar range  (+1 star)
  Large wick = price rejection, confirms absorption at level

Total Stars: 1-5 (minimum 2 stars recommended for trading)
```

**Multi-Bar Confirmation** (bonus confidence):
When two consecutive bars show absorption at approximately the same level (within 0.3 ATR), confidence increases — institutions are defending the level persistently.

### 7.3 Institutional CVD Divergence (Eduardo T.)
Special case of absorption where the divergence is visible on cumulative delta:
- Long-term CVD shows rising floor while price makes lower lows
- Institutions absorbing retail selling at lows
- Eventually price must agree with CVD → explosive bullish reversal

---

## 8. WYCKOFF 2.0 INTEGRATION

### 8.1 Classic Wyckoff Framework
Richard Wyckoff (1873-1934) developed market phase analysis based on composite operator (institutional trader) behavior:

**Accumulation Schematic**:
- **Phase A**: Preliminary Support (PS) → Selling Climax (SC) → Automatic Rally (AR) → Secondary Test (ST) — trend stops
- **Phase B**: Building cause — range trading, testing extremes
- **Phase C**: Spring — final shakeout below support (last chance to accumulate cheap)
- **Phase D**: Sign of Strength (SOS), Last Point of Supply (LPSY)
- **Phase E**: Markup — full trend begins

**Distribution Schematic** (inverse of accumulation):
- Phase A: Preliminary Supply (PSY) → Buying Climax (BC) → Automatic Reaction (AR) → ST
- Phase B: Building distribution
- Phase C: Upthrust (UT) or Upthrust After Distribution (UTAD)
- Phase D: Sign of Weakness (SOW), Last Point of Supply (LPSY)
- Phase E: Markdown

### 8.2 Wyckoff 2.0 Enhancements (Villahermosa)
The critical upgrade: Use Volume Profile and Order Flow to VERIFY Wyckoff events objectively.

**Spring Verification**:
- Classic Wyckoff: Price breaks below Phase B support briefly then recovers
- Wyckoff 2.0 Addition: MUST see bullish absorption on footprint at spring level
- MUST have CVD bullish divergence during the spring
- Volume Profile: LVN should exist below, HVN above (spring through thin area)

**SOS Verification**:
- Classic: High volume, decisive move out of trading range
- Wyckoff 2.0: MUST see stacked bullish imbalances on footprint
- Delta: Strongly positive on breakout candles
- VP: Price moving through LVN above the range = acceleration expected

**VPOC as Phase Indicator**:
- VPOC migrating down in distribution range → confirms distribution
- VPOC migrating up in accumulation range → confirms accumulation
- VPOC at extremes = end of building cause, imminent breakout

### 8.3 Market Context Analysis (Villahermosa)
Before ANY trade:
1. **Identify Context**: Are we in a trading range or trend?
2. **If Range**: Is it accumulation or distribution? (Use Wyckoff + VP)
3. **If Trend**: Is it healthy (VPOC migrating) or exhausted (SOT pattern)?
4. **Trading Zone**: Identify key levels (Creek line, Ice line, POC, VAH/VAL)
5. **Scenarios**: Plan BOTH bullish AND bearish scenarios with invalidation points

### 8.4 Shortening of Thrust (SOT) — Trend Exhaustion
When each successive push in trend direction is SMALLER than the previous:
- 1st thrust: 50 points
- 2nd thrust: 35 points
- 3rd thrust: 20 points
→ Trend exhausting. Prepare for reversal setup.

---

## 9. ORDER FLOW INDICATORS — FULL CATALOG

### 9.1 Indicator References Directory

All indicators below are sourced from `/Indicator references/` and the main orderflow directory.

**AI Smart Order Flow Volume Candles (VenusJ)**
- Platform: TradingView Pine Script v6
- Function: Liquidity sweep detection + delta-based candle coloring
- Key Feature: Identifies liqBuy/liqSell + volume spike confirmation
- Signal: BUY when liqBuy + delta > 0 + volSpike; SELL inverse
- SL/TP: ATR-based, configurable RR ratio (default 2.0)
- Best For: Entry signal at swept liquidity levels

**Absorption Signals (JacobS369)**
- Platform: TradingView Pine Script v6
- Function: Multi-factor absorption confidence scoring (1-5 stars)
- Key Feature: Z-score volume anomaly detection + multi-bar confirmation
- Signal: Bullish (delta<0 + vol anomaly + bull close) / Bearish inverse
- Best For: Reversal entries at VP levels with confirmation

**Big Order Bubbles (Trading IQ)**
- Platform: TradingView Pine Script v6
- Function: Visualizes large order execution as bubbles on chart
- Key Feature: Dollar-based or percentage-based order size threshold
- Modes: Live tick (no history), 1-second, 1-tick, Auto
- Best For: Real-time identification of institutional orders

**Delta Flow Volume Profile (UAlgo)**
- Platform: TradingView Pine Script v5/v6
- Function: Combined delta heatmap + volume profile display
- Key Feature: Shows delta at each VP price level — identifies which levels have strong directional flow
- Best For: Finding delta-confirmed POC/HVN/LVN levels

**Footprint Delta Trap (PakunFX)**
- Platform: TradingView Pine Script v6
- Function: Detects trapped traders at price extremes via delta analysis
- Key Feature: Identifies high delta at price extremes = trapped participants
- Signal: Trap at high (neg delta at new high) / Trap at low (pos delta at new low)
- Best For: Counter-trend entries at extremes

**Fractal Structure Model Pro (ZakAlgoTrade)**
- Platform: TradingView Pine Script v6
- Function: Multi-timeframe SMC (Smart Money Concepts) + Order Flow structure
- Key Feature: Fractal-based BOS (Break of Structure) + CHoCH (Change of Character) with volume confirmation
- Best For: Multi-timeframe structure analysis and trade direction bias

**Institutional CVD Divergence (Eduardo T.)**
- Platform: TradingView Pine Script v6
- Function: Long-term CVD divergence detection
- Key Feature: Identifies when CVD trend diverges from price trend over extended periods
- Signal: Sustained CVD bull divergence at lows / Bear divergence at highs
- Best For: Swing trade entries and major reversal identification

**Institutional Delta Sweeps (BOSWaves)**
- Platform: TradingView Pine Script v6
- Function: Large delta sweep detection at structural levels
- Key Feature: Multi-timeframe delta alignment + sweep identification
- Best For: Trend confirmation after breakouts

**Institutional Multi-Timeframe Dashboard (JOAT)**
- Platform: TradingView Pine Script v6
- Function: Dashboard showing MTF trend and volume alignment
- Key Feature: Color-coded table showing bullish/bearish alignment across timeframes
- Best For: Session setup — check alignment before trading

**Institutional Zone Mapper (JOAT)**
- Platform: TradingView Pine Script v6
- Function: Maps institutional order blocks and zones
- Key Feature: Identifies last impulsive candle before major moves (order blocks)
- Best For: Identifying high-probability support/resistance zones

**Intrabar Order Pressure (custom)**
- Platform: TradingView Pine Script v6
- Function: Measures buy/sell pressure within individual bars using lower TF data
- Key Feature: Shows real intrabar momentum shifts invisible on regular charts
- Best For: Precision entry timing

**LVN Finder (custom)**
- Platform: TradingView Pine Script v6
- Function: Automatically identifies Low Volume Nodes on any timeframe
- Key Feature: Highlights LVN zones with configurable sensitivity
- Best For: Carmine-style LVN acceleration trades

**Naive Bayes DNA Heatmap (GainzAlgo)**
- Platform: TradingView Pine Script v6
- Function: Gaussian Naive Bayes ML applied to volume delta
- Key Feature: Probabilistic signal scoring (bull probability 0-100%)
- Best For: Quantified signal confidence, backtesting with ML edge

**NOA Sessions Footprints (custom)**
- Platform: TradingView Pine Script v6
- Function: Session-specific footprint analysis (New York, London, Asian sessions)
- Key Feature: Tracks delta accumulation per session
- Best For: Session-to-session CVD comparison

**ORDER Flow Footprint Delta Split PRO (BumT)**
- Platform: TradingView Pine Script v6
- Function: Professional footprint visualization with delta split display
- Key Feature: Shows bid/ask split + cumulative delta per price level
- Best For: Advanced footprint reading within TradingView

**Orderflow Synthesis Pro (JOAT)**
- Platform: TradingView Pine Script v6
- Function: Combines multiple OF signals into single synthesized output
- Key Feature: Multi-factor confluence scoring
- Best For: One-indicator solution for OF confluence

**Stacked Imbalance Zones (BOSWaves)**
- Platform: TradingView Pine Script v6
- Function: Detects zones where multiple consecutive bars show one-sided delta
- Key Feature: Highlights stacked imbalance zones as support/resistance
- Best For: Continuation trade entries in strong trends

**Volume Profile Fixed Range + Dynamic Anchored VWAP (Integrated)**
- Platform: TradingView Pine Script v6
- Function: Combined fixed-range VP with dynamic VWAP anchoring
- Key Feature: Flexible VP period selection + VWAP anchored to key pivots
- Best For: Intraday VP + VWAP combined analysis

**Aegis VEP_CBP Hybrid (wjdtks255)**
- Platform: TradingView Pine Script v5
- Function: Volume Expansion Pattern + Core Buying Pressure hybrid
- Key Feature: VEP identifies volume breakouts; CBP measures net buying/selling pressure; combined = high-conviction signals
- Signals: "Golden Bull" (yellow triangle up) and "Death Bear" (purple triangle down)
- Best For: Institutional-quality entry signals with volume expansion

**Delta Absorption Scanner (MarkitTick)**
- Platform: TradingView Pine Script v6
- Function: Scans for delta absorption across multiple price levels simultaneously
- Key Feature: Real-time absorption heatmap
- Best For: Finding hidden absorption that regular indicators miss

**Nexus — SMC Order Flow Confluence Engine**
- Platform: TradingView Pine Script v6
- Function: Smart Money Concepts + Order Flow multi-factor confluence
- Key Feature: Combines order blocks, liquidity zones, delta, and volume profile
- Best For: High-confluence setups with SMC structure

---

## 10. TRADING STRATEGIES — COMPLETE PLAYBOOK

### Strategy 1: Fabio Valentini AMT Scalping
**Source**: fabio-valentini-strategy-guide.pdf

**Overview**: The primary strategy from ChartFanatics. Achieves 500%+ annual returns through disciplined execution of the 3-step protocol.

**Instruments**: NQ (Nasdaq-100 Futures), ES (S&P 500 Futures)
**Timeframe**: 1-minute to 5-minute charts
**Session**: NY Main (17:30-21:00 SAST), selective London

**3-Step Protocol**:
```
STEP 1 — LOCATION
  Identify market state: Balance vs Imbalance
  Mark key VP levels: POC, VAH, VAL, LVN zones
  Question: Is price at a high-probability structural level?

STEP 2 — VALIDATION  
  Check CVD: Does CVD confirm or diverge from price?
  Check Absorption: Is there a volume anomaly with counter-delta close?
  Check Higher TF: Does higher timeframe context support the trade?

STEP 3 — AGGRESSION TRIGGER
  Wait for institutional footprint:
  NQ: ≥30 contracts in single trade → enter
  ES: ≥15 contracts in single trade → enter
  Enter on the NEXT bar after trigger confirmation
```

**Entry Rules**:
- Model 1 (Trend): Enter pullback to VP level in trend direction after absorption
- Model 2 (Reversion): Enter at VAH/VAL/POC with absorption + CVD divergence

**Exit Rules**:
- Stop: Below/above nearest structural level (LVN, swing point) + 0.5 ATR
- Target 1: 1:1 RR (partial close 50%)
- Target 2: 1:2 RR or next VP level
- Session Close: MANDATORY — no overnight holds

### Strategy 2: Carmine LVN Acceleration
**Source**: Order Flow Masterclass by Camrine PDF, LVN Finder indicator

**Overview**: Trade the SPEED of price through Low Volume Nodes. LVNs are like air pockets — price falls/rises rapidly through them.

**Setup Identification**:
1. Find LVN on session or daily Volume Profile
2. Price is approaching LVN from the dense HVN above/below
3. Pre-trade: Delta is building in direction of expected move
4. Trigger: First momentum bar with volume spike entering LVN

**Entry**:
- Long: Enter when price breaks above LVN bottom with positive delta
- Short: Enter when price breaks below LVN top with negative delta
- Use limit order or aggressive market order (price moves fast)

**Stop**:
- Long: Below LVN bottom (back in the HVN) + 2 ticks
- Short: Above LVN top (back in the HVN) + 2 ticks

**Target**:
- Next HVN on the other side of LVN
- Or next session POC
- LVN exit: As soon as price reaches HVN, tighten stop aggressively

**Risk**: 0.5% per trade (tighter than usual due to precise levels)

### Strategy 3: CVD Divergence Reversal
**Source**: Multiple sources including Institutional CVD Divergence indicator, Wyckoff 2.0

**Overview**: Trade exhausted trends by identifying when CVD confirms the trend is losing institutional support.

**Setup**:
1. Price is in established trend (5+ bars in one direction)
2. Price makes new extreme (high or low)
3. CVD does NOT make new extreme in same direction
4. Volume at new extreme = anomalous (Z-score ≥ 2.0) — climax volume
5. Absorption signal fires at the extreme

**Entry**:
- Short: At new price high with CVD failure + bearish absorption confirmation
- Long: At new price low with CVD failure + bullish absorption confirmation
- Enter ONLY on bar CLOSE (not at the trigger — wait for candle to close confirming)

**Stop**:
- 1 ATR beyond the extreme

**Target**:
- Previous session POC
- Or 61.8% retracement of the last thrust

### Strategy 4: Wyckoff 2.0 Spring Long
**Source**: Wyckoff 2.0 (Villahermosa) + Volume Profile

**Overview**: The classic Wyckoff accumulation entry, enhanced with VP and OF confirmation.

**Prerequisites**:
1. Price in trading range for ≥20 bars
2. Clear range boundaries identifiable (support/resistance)
3. Volume Profile: HVN inside the range, LVN below support

**Spring Setup**:
1. Price breaks BELOW support (Creek level) — Spring event
2. Footprint at spring low: POSITIVE delta (buyers absorbing the breakdown)
3. CVD: Making higher lows while price makes lower lows (divergence)
4. Volume: Selling climax (volume spike at spring low)
5. Recovery: Price reclaims support level within 1-3 bars

**Entry**: First bar to close back ABOVE the spring level (support reclaimed)

**Stop**: Below the spring low × 1.5

**Target**:
- Phase D: Top of trading range (Creek resistance)
- Phase E: 1× the height of the trading range above the Creek

**Confidence Required**: 4/5 stars (tight setup, high conviction needed)

### Strategy 5: VEP + CBP Momentum (Aegis)
**Source**: Aegis VEP_CBP Hybrid indicator

**Overview**: Trade institutional momentum when Volume Expansion Pattern aligns with strong Core Buying/Selling Pressure.

**Golden Bull Setup** (Long):
1. isPPV = true (bullish VEP — volume breaks above max bearish volume of lookback)
2. net_p > sMA (CBP above its EMA — sustained buying pressure)
3. Price above VAH (above value = momentum confirmed)

**Entry**: Market order on bar close
**Stop**: Below previous swing low or VAH
**Target**: 2× ATR extension

**Death Bear Setup** (Short): Inverse of above

### Strategy 6: Session Open Drive (Volume Profile Insider Guide)
**Source**: VOLUME-PROFILE insider guide

**Overview**: Trade the opening session momentum when it's backed by institutional commitment.

**Setup**:
1. Price gaps or drives aggressively from session open
2. Volume significantly above session average
3. Delta confirms direction of drive
4. Price staying ABOVE (bull) or BELOW (bear) previous day's POC

**Entry**: 5-10 minute pullback to VWAP or session POC after initial drive

**Stop**: Below session low (bull) or above session high (bear)

**Target**: 1:1.5 RR minimum, trail to previous session's extreme

### Strategy 7: Absorption at Value Area Extremes
**Source**: JacobS369 Absorption Signals + Trader Dale VP + CMC Markets guide

**Overview**: The workhorse mean-reversion strategy. Trade absorption at VAH/VAL.

**Long at VAL**:
1. Price at or slightly below VAL (value area low)
2. Absorption Signals indicator: 3+ star bullish absorption
3. CVD: Not making new lows (holding)
4. Profile shape: D-profile or P-profile (value area well-defined)

**Entry**: Market order or limit at VAL
**Stop**: Below VAL - 1 ATR (outside value completely)
**Target**: POC (mean reversion)

**Short at VAH**:
1. Price at or slightly above VAH (value area high)
2. Absorption Signals: 3+ star bearish absorption
3. CVD: Not making new highs (holding)
4. Profile shape: D-profile or b-profile

**Entry**: Market order or limit at VAH
**Stop**: Above VAH + 1 ATR
**Target**: POC

### Strategy 8: Bookmap Trap Reversal
**Source**: Footprint Delta Trap (PakunFX), BOOKMAP TRAPS INDICATOR REFERENCE.pdf

**Overview**: Trade trapped participants. When breakout traders are absorbed by institutions, trapped longs/shorts fuel the reversal.

**Long Trap at High (Short Setup)**:
- Price makes new high (breaks out above resistance)
- Footprint at high: Negative delta (sellers dominating at the extreme)
- Volume: High (climax buying being absorbed)
- Price cannot hold above resistance for more than 2-3 bars

**Enter Short**: On first bar to close back below the broken resistance
**Stop**: Above the new high
**Target**: Return to VAL or session mean

### Strategy 9: JadeCap Liquidity Strategy
**Source**: JadeCap Liquidity Trading Strategy PDF

**Overview**: Target liquidity pools — areas where stop orders accumulate — and trade the institutional sweep-and-reverse pattern.

**Liquidity Levels**:
- Equal highs/lows (multiple touches at same level = stops stacking)
- Previous day/week/month highs and lows
- Round numbers (psychological stops)
- Moving average touch points

**Trade**:
1. Identify liquidity pool (equal highs = buy stops above)
2. Price sweeps through liquidity pool (triggers stops)
3. Institutions sell INTO the liquidity sweep (absorb the breakout)
4. Price reverses sharply after sweep
5. Enter in reversal direction after first candle close back through the level

---

## 11. SESSION TIMING & MARKET STRUCTURE

### 11.1 Global Session Times (SAST = UTC+2)

| Session | UTC | SAST | Character |
|---------|-----|------|-----------|
| Asian | 00:00-08:00 | 02:00-10:00 | Low volume, range-bound, AVOID |
| London Open | 08:00-09:30 | 10:00-11:30 | Volatile open, gap fills, selective |
| London Main | 09:30-12:00 | 11:30-14:00 | Model 2 primary (mean reversion) |
| London/NY Overlap | 13:00-17:00 | 15:00-19:00 | High volume, trend and reversal |
| NY Main | 14:30-19:00 | 16:30-21:00 | Model 1 primary (trend following) |
| NY Close | 19:00-21:00 | 21:00-23:00 | Reduce exposure, close positions |
| After Hours | 21:00-01:00 | 23:00-03:00 | NO TRADING |

**Rule from Fabio Valentini**: Asian session = DO NOT TRADE. Low volume, noise, unpredictable.

### 11.2 Session Characteristics for Order Flow

**London Main (Model 2 — Mean Reversion)**:
- Institutions are active building and defending positions
- Markets often consolidate in ranges → perfect for absorption at extremes
- Volume Profile: Clear D-profile with well-defined VAH/VAL
- Strategy: Wait for price to reach VAH or VAL with absorption, trade back to POC

**NY Main (Model 1 — Trend Following)**:
- Largest volume session globally
- Clear directional moves driven by institutional order flow
- Delta: Sustained directional delta (one side dominant for hours)
- Strategy: Identify direction, trade pullbacks to VP levels with delta confirmation

### 11.3 Pre-Trade Checklist
Before every single trade:
```
□ Current session? (Only trade during approved session)
□ Higher TF trend direction? (D1 and H4 bias)
□ Volume Profile levels identified? (POC, VAH, VAL, LVN marked)
□ Price at meaningful level? (Score ≥3/5 per scoring system)
□ CVD direction confirmed?
□ Absorption signal present? (≥2 stars)
□ News check? (No major news in next 30 minutes)
□ Daily P&L check? (Not in drawdown >3% today)
□ Position size calculated? (Risk ≤1% of account)
□ Stop and target set BEFORE entry?
```

---

## 12. RISK MANAGEMENT SYSTEM

### 12.1 The Core Rules (Absolute — Never Violate)

1. **No Overnight Positions** (Fabio Valentini): All positions close before market close. No exceptions.
2. **1% Maximum Risk Per Trade**: Never lose more than 1% of account on any single trade.
3. **5% Maximum Daily Drawdown**: If daily loss reaches 5%, stop trading immediately for that day.
4. **No Asian Session Trades**: Zero trades during Asian session hours.
5. **News Blackout**: No new entries 15 minutes before or after major news (NFP, CPI, FOMC, etc.).
6. **No Revenge Trading**: If stopped out 3 times in a row, pause for 1 hour minimum.

### 12.2 Position Sizing Formula
```
Risk per trade = Account Balance × Risk% (typically 1%)
Stop Loss distance (in account currency) = Entry − Stop
Lot Size = Risk Amount / Stop Distance in pips / Pip Value

Example (Forex):
  Account: $10,000
  Risk: 1% = $100
  Entry: 1.1000, Stop: 1.0980 → 20 pip SL
  EUR/USD pip value: $10/pip (1 lot)
  Lots = $100 / (20 × $10) = 0.5 lots

Example (Futures NQ):
  Account: $25,000
  Risk: 1% = $250
  Entry: 18,500, Stop: 18,460 → 40 points SL
  NQ point value: $20/point
  Contracts = $250 / (40 × $20) = 0.3125 → round DOWN to 0 (need bigger account for NQ)
```

### 12.3 Trade Scoring System (Minimum 3/5 to Enter)
| Factor | Points |
|--------|--------|
| Price at key VP level (POC, VAH, VAL, LVN) | +1 |
| Delta confirms direction (Z-score ≥ 1.5) | +1 |
| CVD divergence or confirmation | +1 |
| Absorption signal (≥2 stars on JacobS369) | +1 |
| Session timing correct (approved window) | +1 |

**Enter at 3/5**: Half position size
**Enter at 4/5**: Full position size
**Enter at 5/5**: Full position + pyramid on first TP hit

### 12.4 Risk:Reward Targets by Strategy
| Strategy | Minimum RR | Typical RR |
|----------|-----------|------------|
| Absorption at VA | 1.5:1 | 2.0:1 |
| LVN Acceleration | 2.0:1 | 3.0:1 |
| CVD Divergence | 1.8:1 | 2.5:1 |
| Wyckoff Spring | 2.5:1 | 4.0:1 |
| VEP + CBP | 2.0:1 | 3.0:1 |
| Bookmap Trap | 1.5:1 | 2.0:1 |

### 12.5 Trailing Stop Management
After 1:1 RR achieved:
- Move stop to break-even
- Partial close: 50% position at 1:1
- Remaining position: Trail by 1× ATR
- Session close: Close all regardless of position

### 12.6 Four Types of Trades (Trader Dale Psychology)
1. **Good Winning Trade**: Followed all rules, profit → reinforce the process
2. **Bad Winning Trade**: Broke rules, still profited → do NOT reward, analyze
3. **Good Losing Trade**: Followed all rules, stopped out → acceptable loss, process correct
4. **Bad Losing Trade**: Broke rules, got stopped out → double lesson, analyze and fix

**Mental Rule**: Judge trades by PROCESS quality, not outcome. Good process with bad outcome = still success.

---

## 13. PLATFORM COMPARISON: MT5 vs CTRADER vs TRADINGVIEW

### 13.1 MetaTrader 5 (MT5)

**Strengths**:
- Industry standard for CFD and Forex brokers globally
- Full MQL5 language for EAs, indicators, scripts
- CopyTicksRange() provides true historical tick data
- Strategy Tester with "Every tick based on real ticks" mode
- Massive broker ecosystem (200+ brokers)
- Free

**Weaknesses**:
- No native footprint chart (need third-party add-on)
- Volume Profile requires custom coding (no built-in)
- MQL5 is verbose compared to Pine Script
- Multi-symbol EAs complex to manage

**Key APIs**:
- `CopyTicksRange()` — tick history access
- `CTrade` — order execution
- `PositionInfo` — position management
- `iMA`, `iATR`, `iRSI` — standard indicators

**Best For**: Forex, CFDs, complex EA development, prop firm trading

### 13.2 cTrader / cAlgo

**Strengths**:
- C# language (modern, powerful, full .NET ecosystem)
- Native tick data via `Symbol.Ticks` and `MarketData.GetTicks()`
- Built-in Volume Profile in Pro charts
- Superior ECN execution (true market access at many brokers)
- Clean API with strong documentation
- cTrader Copy for social trading
- FIX protocol support

**Weaknesses**:
- Fewer brokers than MT5
- More limited third-party indicator ecosystem
- Higher technical bar (C# vs scripting languages)

**Key APIs**:
- `Ticks.Subscribe()` — real-time tick processing
- `MarketData.GetTicks()` — historical tick access
- `ExecuteMarketOrder()` — entry
- `ModifyPosition()` — management
- `Indicators.*` — built-in indicator library

**Best For**: Order flow EAs (best tick data access), ECN trading, institutional-style execution

### 13.3 TradingView / Pine Script

**Strengths**:
- Largest indicator library in the world
- Pine Script v6 is approachable and powerful
- `ta.requestVolumeDelta()` for delta approximation (Premium)
- Best charting and visualization
- Alert system for webhook-based automation

**Weaknesses**:
- CANNOT execute trades directly (need broker integration via webhooks)
- NO true tick data access (only OHLCV per bar)
- Pine runs on server — no live trading logic
- Volume data quality varies by data provider
- requestVolumeDelta = estimated, not tick-accurate

**Best For**: Strategy development, indicator testing, visual analysis, signal generation for manual or webhook execution

### 13.4 Platform Selection Guide for EA Development

| Requirement | Recommended Platform |
|-------------|---------------------|
| True tick-level delta | cTrader or MT5 |
| Fastest execution | cTrader (ECN) |
| Most broker compatibility | MT5 |
| Best volume profile native | cTrader Pro |
| Easiest EA coding | MT5 (MQL5 scripting) |
| Professional footprint charts | ATAS or Bookmap (separate apps) |
| Signal visualization | TradingView |
| Prop firm compliance | Both MT5 and cTrader supported |

---

## 14. PINE SCRIPT → MQL5 → cALGO CONVERSION

*(See SKILL.md Part 4 for complete conversion table)*

### 14.1 Critical Differences in Volume Data

**Volume Data Quality Comparison**:
| Platform | Volume Type | Quality for OF |
|----------|-------------|----------------|
| MT5 (Forex) | Tick volume (proxy) | Medium — not true lot volume |
| MT5 (Futures) | Real traded contracts | High — institutional grade |
| cTrader | Real-time ticks with volume | High — best for forex |
| TradingView | Exchange/broker dependent | Variable |
| ATAS | Full Level 2 + footprint | Highest (dedicated OF platform) |

**For Forex Order Flow EAs**: Use cTrader for most accurate data
**For Futures Order Flow EAs**: MT5 with CopyTicksRange on CME-connected brokers

### 14.2 Delta Calculation Methods by Platform

**Method 1 — Tick Classification (cTrader, best)**:
```csharp
if(tick.TickType == TickType.Ask) buyVol += tick.Volume;
if(tick.TickType == TickType.Bid) sellVol += tick.Volume;
barDelta = buyVol - sellVol;
```

**Method 2 — Tick Flags (MT5)**:
```mql5
if(ticks[i].flags & TICK_FLAG_BUY)  buy_vol  += ticks[i].volume_real;
if(ticks[i].flags & TICK_FLAG_SELL) sell_vol += ticks[i].volume_real;
```

**Method 3 — Candle Estimation (Pine Script)**:
```pine
buyVol  = close > open ? volume : volume * 0.4
sellVol = close < open ? volume : volume * 0.4
delta   = buyVol - sellVol
```
*Note: Method 3 is an approximation only. Methods 1 and 2 are tick-accurate.*

---

## 15. EA BUILDING BLUEPRINTS

*(See SKILL.md Parts 5.1 and 5.2 for complete MT5 and cTrader EA code)*

### 15.1 EA Architecture Template (Both Platforms)

```
OrderFlowEA Architecture:
│
├── INPUTS
│   ├── Strategy Model (1=Trend, 2=MeanRev)
│   ├── Session Filter (NY/London/All)
│   ├── Order Flow Parameters (delta lookback, vol Z-score, absorption threshold)
│   ├── Volume Profile (bars, bins, VA %)
│   └── Risk (% per trade, RR, max DD, trail ATR)
│
├── INITIALIZATION
│   ├── Load indicators (ATR)
│   ├── Initialize delta/CVD accumulators
│   └── Record daily start equity
│
├── ON_BAR (main logic — new bar event only)
│   ├── DD Check → CloseAll if exceeded
│   ├── Session Check → Return if outside session
│   ├── Calculate Bar Delta (via tick aggregation)
│   ├── Update CVD
│   ├── Detect Absorption (bullish/bearish)
│   ├── Calculate Volume Profile (POC, VAH, VAL)
│   ├── Score Trade Setup (1-5)
│   └── Enter If Score ≥ 3 AND No Open Position
│
├── POSITION MANAGEMENT
│   ├── Trail Stop (ATR-based)
│   ├── Partial Close (at 1:1 RR)
│   └── Session Close (force close at session end)
│
└── UTILS
    ├── CalculateLots (% risk based)
    ├── GetBarDelta (tick aggregation)
    ├── GetVolumeProfile (bar-based approximation)
    └── IsValidSession (time filter)
```

### 15.2 Advanced Features for Production EAs

**Feature 1: Spread Guard**
```mql5
double current_spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * _Point;
double normal_spread  = /* baseline from initialization */ 0.0002;
if(current_spread > normal_spread * 2.0) return;  // Don't trade wide spreads
```

**Feature 2: News Filter** (requires calendar data or time blackout)
```csharp
// Blackout 15 min before/after high-impact news
// Either hardcode times or use economic calendar API
DateTime nfpTime = /* Friday 08:30 ET */;
if(Math.Abs((Server.Time - nfpTime).TotalMinutes) < 15) return;
```

**Feature 3: Multi-Symbol Delta Correlation**
For NQ/ES correlation (Fabio Valentini technique):
- When NQ shows strong bullish absorption AND ES confirms positive delta → A+ setup
- Divergence between NQ and ES = mixed signal, reduce size

**Feature 4: Volume Profile Cache**
Recalculate VP only when new session begins (not every bar) to save computation:
```csharp
private DateTime _lastVPCalc = DateTime.MinValue;
private (double poc, double vah, double val) _cachedVP;

if(Server.Time.Date != _lastVPCalc.Date) {
    _cachedVP = CalculateVolumeProfile();
    _lastVPCalc = Server.Time;
}
```

**Feature 5: Dashboard Display**
Add visual dashboard showing real-time:
- Current session
- CVD direction
- Last absorption confidence
- VP levels
- P&L for the day
- Number of trades taken

---

## 16. PROP FIRM COMPLIANCE RULES

### 16.1 Standard Prop Firm Rules (Applies to Most Firms)
| Rule | Typical Limit | EA Compliance |
|------|--------------|---------------|
| Max Daily Loss | 4-5% | Hard kill switch in EA |
| Max Overall Drawdown | 8-10% | Check equity vs starting balance |
| Minimum Trading Days | 5-10 days | Log all trading days |
| Minimum Trade Duration | Usually 0 | Order flow EAs trade seconds to hours |
| News Trading | Often restricted | Implement news blackout filter |
| Overnight Positions | Sometimes restricted | Fabio Valentini rule = always close |
| Weekend Positions | Mostly restricted | Close Friday before market close |
| Copy Trading | Prohibited | Each account = unique EA instance |
| Lot Scaling | Usually fine | Use % risk based sizing |

### 16.2 EA Settings for Prop Firms
```
InpRiskPct = 0.5 (conservative, use half normal size)
InpMaxDDPct = 3.0 (more conservative than personal trading)
InpSessionFilter = 1 (NY Main only — most controlled session)
InpTrailStop = true (don't let winners turn to losers)
InpMagicNumber = unique per account (isolation)
```

### 16.3 Prop Firm Evaluation Phase vs Funded Phase
**Evaluation**: Be more conservative
- Reduce risk per trade to 0.5%
- Only take 4-5 star setups
- Focus on consistency, not maximum profit

**Funded Phase**: Normal trading
- Full 1% risk per trade
- Trade all 3+ star setups
- Maintain discipline on daily loss limit

---

## 17. ACADEMIC & INSTITUTIONAL RESEARCH

### 17.1 Key Academic Findings

**BIS Paper (bispap02j.pdf)** — Bank for International Settlements:
- Studies on foreign exchange market microstructure
- Electronic market trading and information flow
- Dealer-customer relationship in price discovery
- Key finding: Order flow is the primary driver of exchange rate movements in the short term

**Pecchiari (701851_PECCHIARI_MATTEO.pdf)**:
- Academic thesis on order flow trading
- Empirical analysis of delta and volume metrics
- Institutional flow signatures vs retail flow
- Statistical evidence for absorption patterns

**Market Auction Theory (Four Steps)**:
- Markets alternate between balance and imbalance
- Volume Profile provides objective measurement of balance
- The adaptive markets hypothesis: markets aren't perfectly efficient but adapt over time
- Wyckoff 2.0 context: exploiting the non-random behavioral patterns of institutions

### 17.2 Key Statistical Properties of Order Flow

**Delta Z-Score Distribution**:
- Normal trading: Delta Z-score < ±1.5
- Unusual activity: Z-score > ±1.5 (top/bottom 13% of occurrences)
- Institutional activity: Z-score > ±2.0 (top/bottom 2.3%)
- Extreme absorption: Z-score > ±3.0 (top/bottom 0.13%)

**Volume Profile Value Area Statistical Basis**:
- The 70% Value Area mirrors the ±1 standard deviation rule from normal distribution
- Markets spend 70-80% of time in value area (empirically validated)
- Failed auctions beyond value area have 78%+ return-to-value probability (Trader Dale)

**LVN Velocity**:
- Price passes through LVNs at 3-5× the velocity of HVN traversal
- LVN zones have <30% of POC volume — virtually no resistance
- LVN trades have highest velocity but require tightest timing

### 17.3 Market Participants Hierarchy

**Tier 1 — Market Makers** (Central Banks, Primary Dealers):
- Define the macro directional bias
- Use order flow data to size positions
- Leave tracks via anomalous volume patterns

**Tier 2 — Institutional Funds** (Hedge Funds, Prop Desks, CTAs):
- Medium-term positions (days to weeks)
- Absorb retail flow at strategic levels
- Create order blocks and absorption zones

**Tier 3 — Algorithmic Traders** (HFT, Stat Arb):
- Microsecond execution
- Market making and gap exploitation
- Create the noise but not the trend

**Tier 4 — Retail Traders** (3.5% of forex volume):
- Provide liquidity through predictable behavior (stop placement, breakout chasing)
- Institutions USE retail stops as liquidity for their own entries
- Trading the opposite of retail = often correct (follow the institutional money)

---

## APPENDIX A: QUICK REFERENCE SIGNALS

### Entry Signal Hierarchy (Strongest to Weakest)
1. Absorption Signal (≥4 stars) + CVD divergence + VP level = A+ (full position)
2. Absorption Signal (3 stars) + one confirmation = A (full position)
3. Absorption Signal (2 stars) + two confirmations = B (half position)
4. Single confirmation only = DO NOT TRADE

### Stop Loss Placement Guide
| Scenario | Stop Placement |
|----------|----------------|
| Reversal at VAH | VAH + 1.0 ATR |
| Reversal at VAL | VAL - 1.0 ATR |
| LVN Acceleration | Back into HVN + 2 ticks |
| Breakout trade | Below breakout level - 0.5 ATR |
| Wyckoff Spring | Below spring low - 1.5 ATR |
| Trend continuation | Below previous swing low |

### Profit Target Guide
| Scenario | Primary Target | Secondary Target |
|----------|---------------|-----------------|
| At VAL (long) | POC | VAH |
| At VAH (short) | POC | VAL |
| LVN acceleration | Next HVN | POC |
| Absorption reversal | 50% retracement | Full retracement |
| Session range trade | Opposite value area | POC |

---

## APPENDIX B: GLOSSARY

| Term | Definition |
|------|-----------|
| AMT | Auction Market Theory — markets continuously seek price equilibrium |
| Absorption | When limit orders absorb aggressive market orders, stalling price |
| Bar Delta | Net difference between aggressive buy and sell volume per candle |
| CBP | Core Buying Pressure — net pressure = vol × ((close-low)-(high-close))/range |
| CVD | Cumulative Volume Delta — running sum of all delta values |
| D-Profile | Bell-shaped Volume Profile indicating market balance |
| Delta | Aggressive Buy Volume − Aggressive Sell Volume |
| Footprint | Bid/ask volume displayed at every tick level within each candle |
| HFT | High Frequency Trading — algorithmic trading at microsecond speeds |
| HVN | High Volume Node — price level with above-average volume |
| Imbalance | Market state where one side is aggressively dominant |
| LVN | Low Volume Node — price level with below-average volume |
| Order Block | Last impulsive candle before significant price displacement |
| P-Profile | Thin bottom, fat top VP shape indicating bullish trend |
| POC | Point of Control — price with highest volume in profile |
| b-Profile | Fat bottom, thin top VP shape indicating bearish trend |
| SAST | South Africa Standard Time (UTC+2) |
| SOT | Shortening of Thrust — diminishing momentum signal |
| Spring | Wyckoff event — brief breakdown below support that quickly reverses |
| Stacked Imbalance | Consecutive candles with dominant one-sided delta |
| Trap | When breakout traders are absorbed by institutions at extremes |
| Upthrust | Wyckoff event — brief breakout above resistance that quickly reverses |
| VA | Value Area — price range containing 70% of session volume |
| VAH | Value Area High — upper boundary of 70% volume zone |
| VAL | Value Area Low — lower boundary of 70% volume zone |
| VEP | Volume Expansion Pattern — volume breaks above recent directional maximum |
| VWAP | Volume Weighted Average Price — institutional benchmark |
| Wyckoff 2.0 | Combining Wyckoff phases with Volume Profile and Order Flow (Villahermosa) |

---

## APPENDIX C: SOURCE DOCUMENT INDEX

All 69+ documents absorbed and integrated into this reference:

**Strategy Guides**: fabio-valentini-strategy-guide.pdf, Order Flow Masterclass Camrine (×2), JadeCap Liquidity Trading Strategy, Carmine LVN Trading Strategy, LVN Finder, Trader Kane 50% Reversal, Wyckoff 2.0 (Villahermosa), Breakout Trading Power, Liq strat, Ord strat, Vol strat

**Order Flow Fundamentals**: Order-Flow-Trading.pdf (HowToTrade), Order Flow Trading Guide CMC Markets, Mastering Order Flow Trading (TheStockDork), What is Order Flow Trading (×3 versions), Order Flow Trading Strategy (Earn2Trade), Order Flow Comprehensive Guide (OneFunded), Order Flow Stop Guessing Entries 2026, Order Flow Read Market Like Institutions 2026, Order Flow Strategies FXOpen, Top 4 Order Flow Strategies, Order Flow Strategies Market Success, Order Flow Backtest Analysis, Order Flow $70 Million Profits, Order-Flow-Trading-Setups-1

**Volume Profile**: VOLUME-PROFILE Insider Guide (Trader Dale), Volume Profile Forrest Knight, Market Profile Unlocking Secrets

**Indicators**: All 9 indicator reference PDFs from Indicator references/, plus: AI Smart Order Flow Volume Candles, Absorption Signals, Aegis VEP_CBP Hybrid, BOOKMAP TRAPS INDICATOR REFERENCE, Big Order Bubbles (×2), Delta Absorption Scanner, Delta Flow Volume Profile, ES Algorithmic Order Flow, Footprint Delta Trap, Fractal Structure Model Pro, Institutional CVD Divergence, Institutional Delta Sweeps, Institutional Multi-Timeframe Dashboard, Institutional Zone Mapper, Intrabar Order Pressure, LVN Finder, Naive Bayes DNA Heatmap, NOA Sessions Footprints, Nexus SMC Order Flow, ORDER Flow Footprint Delta Split PRO, Orderflow Synthesis Pro, Stacked Imbalance Zones, Volume Profile Fixed Range + VWAP

**Platform References**: Leading Charting Software ATAS, Liquidity Analysis ATAS, MotiveWave Volume Analysis, Order Flow Trading NinjaTrader, Order Flow Trading What Is It, Technical Analysis vs Order Flow, Trading Indicators ATAS, Trading Interface ATAS

**Academic**: 701851_PECCHIARI_MATTEO.pdf, bispap02j.pdf (BIS)

**Other**: Safari captures (×2), ilovepdf_merged-4 (compiled strategies), ilovepdf_merged-5 (Pine Script source code)

---

*ORDERFLOW DIVE 2.0 — GODMODE Edition*
*April 2026 | Synthesized from 69+ institutional-grade sources*
*For EA development: Reference SKILL.md for complete code implementation*
*Skill location: /orderflow/skills/godmode-orderflow-mastery/SKILL.md*
