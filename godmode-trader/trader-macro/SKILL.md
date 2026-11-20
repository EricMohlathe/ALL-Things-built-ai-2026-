---
name: trader-macro
description: >-
  Macro Backdrop. The numbers behind the month's direction, from free public
  sources: CPI, core CPI and core PCE year on year with their trend,
  unemployment and the Sahm rule, payrolls, the fed funds rate, the 2-year and
  10-year yields, the 10y-2y curve, the 10-year real yield, the broad dollar
  index and VIX (FRED); the 3-month interest-rate differential and its trend
  for any pair of USD, EUR, GBP, JPY, CAD, AUD, CHF and NZD (carry); a
  four-pillar US dollar compass (rates, real yields, growth, risk); the gold
  backdrop from real yields and the dollar; the crypto Fear & Greed index;
  and the latest Fed, ECB, BoE and BoJ press releases. Use when the user says
  "macro", "CPI", "inflation", "jobs", "NFP", "the Fed", "yields", "real
  yields", "the curve", "dollar", "DXY", "carry", "rate differential", "fear
  and greed", "central bank", or before a week of trading.
argument-hint: "[refresh|dashboard|dollar|gold|diff PAIR|feargreed|cb]"
---

# trader-macro

Macro says which way the wind blows this month: whether the dollar has the
rates and the growth behind it, whether gold has falling real yields, whether
a pair pays you to hold it. It does not say where price goes this hour; the
economic calendar (`/trader-calendar`) says WHEN the numbers land.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/macro.py" refresh                 # FRED series -> trader/data/macro/fred.json
python3 "${CLAUDE_SKILL_DIR}/macro.py" dashboard               # inflation, jobs, rates, curve, dollar, VIX
python3 "${CLAUDE_SKILL_DIR}/macro.py" dollar                  # the four-pillar dollar compass
python3 "${CLAUDE_SKILL_DIR}/macro.py" gold                    # real yields + the dollar
python3 "${CLAUDE_SKILL_DIR}/macro.py" diff EURUSD USDJPY AUDNZD   # rate differentials and carry
python3 "${CLAUDE_SKILL_DIR}/macro.py" feargreed               # crypto sentiment, 30 days
python3 "${CLAUDE_SKILL_DIR}/macro.py" cb --banks Fed ECB      # central-bank press releases
```

Run `refresh` once a week (FRED updates monthly series a few weeks after the
month ends; daily series a day later). Add `--json` to any command.

## The series

| Read | FRED series | Frequency |
|---|---|---|
| CPI, core CPI, core PCE | CPIAUCSL, CPILFESL, PCEPILFE | monthly |
| Unemployment, payrolls | UNRATE, PAYEMS | monthly |
| Fed funds | DFF | daily |
| 2-year, 10-year, curve, real yield | DGS2, DGS10, T10Y2Y, DFII10 | daily |
| Broad dollar index, VIX | DTWEXBGS, VIXCLS | daily |
| 3-month rates by currency | IR3TIB01{US,EZ,GB,JP,CA,AU,CH,NZ}M156N (OECD) | monthly |

The broad trade-weighted dollar (DTWEXBGS) stands in for the ICE DXY, whose
data is not free; they move together but are not the same index.

## The reads

- **Dashboard**: each number with its date and its 3-month trend, and a
  regime line (core inflation rising or falling, the curve inverted or not,
  volatility calm, normal or stressed, the Sahm rule if it has triggered).
- **Dollar compass**: +1 / 0 / -1 for rates (the 2-year's 3-month change),
  real yields, growth (payrolls and unemployment) and risk (VIX: haven demand
  helps the dollar, a calm market tends to soften it). +2 or more is a
  tailwind, -2 or less a headwind.
- **Differentials**: base minus quote 3-month rate and its 3-month change.
  The higher-yielder earns the carry; your broker's swap rates are what you
  actually pay or earn overnight.
- **Gold**: falling real yields and a softer dollar have historically
  supported gold; central-bank buying and geopolitics can override both.
- **Fear & Greed** (alternative.me, crypto): extremes have often come near
  turns, and have often lasted for weeks.

## Where it goes next

`/trader-desk` uses the dollar compass to raise or lower a USD idea that a
tested setup already supports. Macro alone never creates a trade.

Every source is free and can change or lag. Read the "as of" dates. This is
not financial advice.
