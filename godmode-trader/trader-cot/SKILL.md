---
name: trader-cot
description: >-
  COT Tracker. Reads the CFTC's weekly Commitments of Traders report and shows
  how the big speculators are positioned in the futures behind your forex
  pairs, gold, silver, oil, gas, copper, the S&P, the Nasdaq, the Dow, the
  Russell and bitcoin: their net long or short in contracts, the change on the
  week, a COT index (where this week's net sits in its own three-year range,
  0 to 100) and crowded-long or crowded-short flags. Reads each one in your
  instrument's direction: speculators long yen futures are short USDJPY. Use
  when the user says "COT report", "how are speculators positioned", "is the
  euro crowded", "who is long gold", "commitments of traders", "smart money
  positioning", or on Fridays after the report comes out.
argument-hint: "[latest|history] [--symbols EURUSD,XAUUSD] [--weeks 156]"
---

# trader-cot

Congress's stock trades were the original pack's look at what the insiders
hold. For forex and commodities the public look is the Commitments of
Traders: every Friday the CFTC publishes what large speculators and hedgers
held in each futures market on Tuesday. When speculators are all on one side,
the trade is crowded, and crowded trades can unwind hard.

`${CLAUDE_SKILL_DIR}` below is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/cot.py" latest                         # every mapped market
python3 "${CLAUDE_SKILL_DIR}/cot.py" latest --symbols EURUSD,USDJPY,XAUUSD,USOIL,BTCUSD
python3 "${CLAUDE_SKILL_DIR}/cot.py" latest --write                 # also save trader/cot.json
python3 "${CLAUDE_SKILL_DIR}/cot.py" history --symbol EURUSD --weeks 52
python3 "${CLAUDE_SKILL_DIR}/cot.py" latest --weeks 52              # a one-year COT index
```

## Source

The CFTC's Legacy "Futures Only" report on its public reporting site,
`https://publicreporting.cftc.gov/resource/6dca-aqww.json`, filtered by
contract market code: Euro FX 099741, British pound 096742, Japanese yen
097741, Swiss franc 092741, Canadian dollar 090741, Australian dollar 232741,
NZ dollar 112741, Mexican peso 095741, South African rand 122741, gold 088691,
silver 084691, platinum 076651, palladium 075651, copper 085692, WTI crude
067651, natural gas 023651, E-mini S&P 500 13874A, E-mini Nasdaq-100 209742,
E-mini Dow 124603, E-mini Russell 2000 239742, Bitcoin 133741. Free and
official, no key. Add a market with `"cot": "CODE"` (and `"cot_sign"`) in the
config's `instruments`.

## What it reports

| field | meaning |
| --- | --- |
| spec net | non-commercial longs minus shorts, in contracts |
| change | this week's net minus last week's |
| COT index | 0 = the most short, 100 = the most long, over `--weeks` (156) |
| read | specs long or short, in the instrument's direction |
| crowded | index 90 or more (long) / 10 or less (short) |

For a pair quoted the other way round (USDJPY, USDCHF, USDCAD, USDMXN,
USDZAR) everything is flipped and said so.

## Steps

1. On Friday evening or the weekend: `cot.py latest`. Lead with the crowded
   markets and the biggest weekly changes.
2. For one instrument: `cot.py history --symbol SYM` and say where its
   positioning sits in its range.
3. Put it next to the scanner's daily bias: a breakout against a crowded side
   is different from one with it. Say it as context, never as a signal.

## Rules

- The report is weekly and three days old when it comes out. Say the date.
- Crowded can stay crowded for months. A COT extreme is not a timing tool.
- Never call a crowded reading a reason to trade on its own.

## Safety

- Education and tooling, not financial advice. Positioning data is context, not a signal.
- Paper trading by default (`"paper": true`). Going live is the user's own decision, in their own config.
- Nothing in this pack places an order except trader-broker, and only with trader-risk's PASS and the
  user's explicit yes for that one order. This skill never places anything.
