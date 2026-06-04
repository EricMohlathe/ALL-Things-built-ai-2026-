# REF-06: MASTER Order Flow Trading in 83 Minutes — Complete OFT Course
## Mind Math Money | Grade: A+ | 83 min | Systematic Mathematical Approach
> Source: Rqu-AoD9BUo.html | YouTube: Rqu-AoD9BUo | Channel: Mind Math Money

---

## OVERVIEW

Mind Math Money's 83-minute course is the most comprehensive single-video order flow curriculum available. It covers the complete journey: from market mechanics to footprint charts to building a full trading system. The systematic, mathematical approach makes it ideal for analytically-minded traders and EA developers.

**Core Thesis**: Order flow trading should be approached like a **statistical business**, not a prediction game. Define exact signals, backtest them, measure win rate and R:R, and execute consistently. The 83 minutes covers building this mathematical edge from scratch.

---

## 1. THE COMPLETE OFT SYSTEM FRAMEWORK

### Phase 1: Market Analysis
- HTF bias (Daily/4H)
- VP levels mapped (POC, VAH, VAL, HVN, LVN)
- Session context (pre-market, Kill Zone, afternoon)
- Today's PDRA levels identified
- Liquidity pools marked (equal highs/lows, BSL/SSL)

### Phase 2: OF Preparation
- Footprint charts ready (correct TF and settings)
- CVD indicator loaded
- VWAP anchored from day open
- DOM visible for scalp entries
- Alerts set at all key levels

### Phase 3: Execution
1. Wait for price at POI
2. Footprint absorption signal
3. CVD divergence confirmation
4. LTF CHOCH on 5M
5. Enter, define SL, set TP1/TP2

---

## 2. STATISTICAL FRAMEWORK — THE NUMBERS

### Backtested Results (500+ Trades)
| Metric | Value |
|--------|-------|
| Win Rate | 48–54% (market-condition dependent) |
| Average Win | 2.8R |
| Average Loss | 1.0R (full SL hit) |
| Expectancy | (0.51 × 2.8) − (0.49 × 1.0) = +0.94R per trade |

### Expectancy Calculation
```
Expectancy = (Win_Rate × Avg_Win) − (Loss_Rate × Avg_Loss)
           = (0.51 × 2.8) − (0.49 × 1.0)
           = 1.428 − 0.49
           = +0.94R per trade

// At 0.94R expectancy, 1% risk per trade, 100 trades:
Account growth = +94% average (100 trades)
```

**The mathematical argument for OFT done correctly: +94% account growth per 100 trades at 1% risk.**

---

## 3. FOOTPRINT CHART MASTERY — 5 SIGNALS

| Signal | Pattern | Meaning | Trade Direction |
|--------|---------|---------|----------------|
| **Absorption Bottom** | High sell volume at support, no new low | Passive buyers absorbing sellers | Long after confirmation close |
| **Absorption Top** | High buy volume at resistance, no new high | Passive sellers absorbing buyers | Short after confirmation close |
| **Stacked Bull Imbalances** | 3+ consecutive buy-dominant rows | Strong institutional buying conviction | Long on pullback to imbalance |
| **Stacked Bear Imbalances** | 3+ consecutive sell-dominant rows | Strong institutional selling conviction | Short on pullback to imbalance |
| **Unfinished Auction** | 0 volume at bar extreme (top or bottom) | One-sided exhaustion, must revisit | Fade the extreme / set target there |

### Signal Details

#### Absorption Bottom (Bullish)
```
Footprint example:
Price 1.2000: 850 Sell × 45 Buy  ← HIGH sell volume
Price 1.1998: 620 Sell × 38 Buy  ← HIGH sell volume
Price 1.1996: 410 Sell × 30 Buy  ← HIGH sell volume
BUT PRICE DOESN'T FALL BELOW 1.1996

→ Sellers can't push price down = buyers are absorbing
→ Delta is very negative BUT price is stable = ABSORPTION
→ CVD falling but price stable = BULLISH DIVERGENCE
→ Entry: when first bar closes green after absorption zone
→ SL: 2-3 ticks below absorption low
→ TP: Next VP level above / POC
```

#### Stacked Imbalances (Institutional Conviction)
```
Bull Stack (3+ consecutive):
Price 1.2005: 18 Sell × 380 Buy  [highlighted]
Price 1.2003: 25 Sell × 295 Buy  [highlighted]
Price 1.2001: 40 Sell × 245 Buy  [highlighted]
Price 1.1999: 180 Sell × 90 Buy  [normal]
→ 3+ stacked buy imbalances = institutional aggression
→ Trade: Long on pullback to stacked zone

Bear Stack (3+ consecutive):
Price 1.2005: 420 Sell × 15 Buy  [highlighted]
Price 1.2003: 310 Sell × 22 Buy  [highlighted]
Price 1.2001: 255 Sell × 38 Buy  [highlighted]
→ 3+ stacked sell imbalances = institutional selling
→ Trade: Short on pullback to stacked zone
```

#### Unfinished Auction
```
Bar extreme with 0 volume on one side:
Price 1.2010: 0 Sell × 0 Buy  ← ZERO bid volume at high
→ Buyers ran out at this tick — sellers took over
→ Market MUST return to complete this auction
→ Use as profit target on shorts / watch for reversal
```

---

## 4. RISK MANAGEMENT FRAMEWORK

### Position Sizing Formula
```
POSITION SIZE = (Account × Risk%) ÷ (SL_pips × pip_value_per_lot)

// Example:
Account = $50,000
Risk% = 1%
SL = 15 pips
Pip value = $10/lot (standard lot EURUSD)

Lots = ($50,000 × 0.01) ÷ (15 × $10)
     = $500 ÷ $150
     = 3.33 lots
```

### Daily Loss Rules
| Rule | Threshold | Action |
|------|-----------|--------|
| Maximum Daily Loss | 3% of account | Stop trading for the day |
| 3 Consecutive Losses | Any amount | Stop trading for the day |
| Daily Max Hit | 3% reached | Stop — no exceptions |
| Weekly Drawdown | 5% from week open | Reduce size by 50% |

### The Expectancy Business Model
```
// Treating trading as a statistical business:

Expectancy = +0.94R per trade
Risk per trade = 1% of account ($500 on $50K)
Trades per day = 2-3 (quality setups only)
Trades per month = 40-60 (20 trading days)

Monthly EV = 50 trades × 0.94R × $500 per R = $23,500

// Key insight: you don't need to predict direction.
// You need to execute your defined edge consistently.
```

---

## 5. THE COMPLETE OFT SYSTEM (STEP BY STEP)

### Pre-Session Setup
```
Before market opens:
1. Open daily chart → identify trend (HH/HL or LH/LL)
2. Mark prior day: POC, VAH, VAL, High, Low, Close
3. Calculate today's PDRA levels
4. Mark all visible equal highs (BSL) and equal lows (SSL)
5. Set alerts at each key level
6. Open footprint chart (5M or 15M depending on instrument)
7. Load CVD indicator
8. Anchor VWAP to today's open
9. Identify today's kill zones (London 2-5AM, NY 7-10AM EST)
```

### During Session — The Decision Tree
```
Is price at a key level? (LVN, HVN, POC, VAH, VAL, OB, FVG)
    NO  → Wait
    YES → Continue

Is this within a kill zone?
    NO  → Wait (unless exceptional setup)
    YES → Continue

Does CVD support the trade direction?
    NO  → Skip
    YES → Continue

What does the footprint show?
    Absorption (sell vol at low, no new low) → LONG SETUP
    Absorption (buy vol at high, no new high) → SHORT SETUP
    Stacked imbalances in direction → TREND ENTRY
    Unfinished auction below/above → FADE/TARGET
    No clear signal → Skip

Is there a 5M CHOCH confirming direction?
    NO  → Wait
    YES → EXECUTE with defined SL and TP
```

---

## 6. ADVANCED CONCEPTS

### The 4 Market Contexts (What to Look For)
| Context | Definition | Footprint Signal | Trade |
|---------|-----------|-----------------|-------|
| **Trending Up** | HH/HL structure, b-shape VP, CVD rising | Buy imbalances on pullbacks | Long at each HVN pullback |
| **Trending Down** | LH/LL structure, P-shape VP, CVD falling | Sell imbalances on rallies | Short at each LVN breakdown |
| **Ranging** | D-shape VP, CVD oscillating | Absorption at VAH/VAL extremes | Long at VAL, short at VAH |
| **Breakout** | Price exits value area with volume | Stacked imbalances through LVN | Enter after LVN cleared |

### CVD Divergence — The Timing Tool
```
SETUP TIMING:
1. Price reaches key level (POI)
2. CVD is diverging (price making extreme, CVD not confirming)
3. Absorption visible on footprint
4. Divergence peak/trough = timing signal
5. Enter when CVD shows first reversal move

// The sequence: Location → Divergence → Absorption → Reversal
```

### Volume Profile Integration Points
- **At VAL** (long): absorption + CVD divergence → Target POC (min) then VAH
- **At VAH** (short): absorption + CVD divergence → Target POC (min) then VAL
- **At LVN** (trending): stacked imbalances → target next HVN
- **At POC** (ranging): fade extremes → target POC reversal

---

## 7. THE 83-MINUTE FRAMEWORK — SUMMARIZED

### The OFT Edge Formula
```
Edge = Location × Signal × Context

Location: Key VP level (LVN, HVN, POC, VAH, VAL) OR key structural level
Signal:   OF confirmation (Absorption / Stacked Imbalance / Unfinished Auction)
Context:  Kill zone timing + HTF alignment + CVD direction

When all three align = HIGH PROBABILITY SETUP
When any one is missing = SKIP (take partial or no position)
```

### The Non-Negotiables
1. **Never trade without a defined SL** — every trade has an invalidation point BEFORE entry
2. **Never risk more than 3% per day** — mathematical ruin prevention
3. **Never trade against the footprint** — if OF says NO, price says yes → still wait for OF
4. **Always use the kill zones** — institutional liquidity = where your setups live
5. **Always journal** — feedback loop is mandatory for improvement

---

## 8. EA IMPLEMENTATION NOTES

### Signal Detection Logic for Code
```
// Absorption Detection (MQL5/cAlgo concept)
bool IsBullishAbsorption(double deltaRatio, double priceMove, double volumeZ) {
    return (deltaRatio < -0.5)   // sell-heavy delta
        && (priceMove < 0.2 * ATR) // price barely moved
        && (volumeZ > 1.5);       // volume spike
}

bool IsBearishAbsorption(double deltaRatio, double priceMove, double volumeZ) {
    return (deltaRatio > 0.5)    // buy-heavy delta
        && (priceMove < 0.2 * ATR) // price barely moved
        && (volumeZ > 1.5);       // volume spike
}

// Stacked Imbalance Detection
bool HasStackedBullImbalance(int consecutiveCount = 3) {
    // Check last N footprint rows for buy > sell by threshold
    // consecutiveCount >= 3 = confirmed institutional signal
}

// Unfinished Auction
bool HasUnfinishedAuction(bool atHigh) {
    // If atHigh: check if top tick has 0 sell volume
    // If at low: check if bottom tick has 0 buy volume
    return (atHigh ? topTickSellVol == 0 : bottomTickBuyVol == 0);
}
```

### Entry Logic Hierarchy
```
Priority 1: Absorption at Key Level + CVD Divergence = Full Size Entry
Priority 2: Stacked Imbalance at Key Level + CVD Confirm = Full Size
Priority 3: Absorption at Key Level only = Half Size
Priority 4: Stacked Imbalance only (no VP level) = Skip / Quarter Size
Priority 5: Single signal only = Skip
```

---

## 9. KEY TAKEAWAYS

1. **OFT has a proven mathematical edge**: ~0.94R expectancy per trade across 500+ backtested trades
2. **The 5 footprint signals are mechanical**: Absorption Bottom/Top, Stacked Bull/Bear, Unfinished Auction
3. **Trading is a statistical business**: define exact signals, measure everything, execute consistently
4. **The decision tree never changes**: Location → Kill Zone → CVD → Footprint → CHOCH → Execute
5. **Risk management is the foundation**: 3% daily max loss = mathematical protection against ruin
6. **Expectancy of +0.94R**: at 50 trades/month, 1% risk = major compounding over time
7. **Never predict direction**: read the footprint, let the market tell you — react, don't forecast
8. **The unfinished auction is your highest-probability target**: price always returns to complete
