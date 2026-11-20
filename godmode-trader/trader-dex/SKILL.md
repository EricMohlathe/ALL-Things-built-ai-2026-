---
name: trader-dex
description: >-
  DEX Research Scanner, paper mode only. Takes timestamped snapshots of
  decentralized-exchange pairs (any chain: Solana, Ethereum, Base, BSC ...)
  from DEX Screener's documented public API: price, liquidity, 24-hour
  volume, price change, buys and sells, FDV and pool age. Checks pool
  identity (the same symbol on different token addresses or chains), thin
  liquidity, missing data, brand-new pools, one-sided flow, volume far above
  liquidity and big moves, then labels each row WATCH, REVIEW or SKIP for
  research. Prints the market-analyst and independent risk-review prompts
  with the real rows filled in, keeps every snapshot, and shows a pool's
  history across them. No wallet, no keys, no orders. Use when the user says
  "DEX", "DEX Screener", "memecoin", "new token", "Solana pairs", "liquidity
  pool", "web crawler", "AI trader scanner", or "scan SOL/USDC".
argument-hint: "[scan|pair|prompts|history] [\"SOL/USDC\" ...] [--chain solana] [--min-liquidity 50000]"
---

# trader-dex

A transparent research collector, after the AI Flow Lab "AI Trader + Web
Crawler" paper-trading guide: a documented public endpoint instead of
scraping random sites, every row timestamped, an AI analyst and a separate
skeptical reviewer, and a journal that records each decision before the
outcome. It is not a trading bot and it cannot place anything.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/dex.py" scan                                   # SOL/USDC and ETH/USDC
python3 "${CLAUDE_SKILL_DIR}/dex.py" scan "BONK/SOL" "WIF/SOL" --chain solana --min-liquidity 100000
python3 "${CLAUDE_SKILL_DIR}/dex.py" pair solana <pairAddress>              # one pool
python3 "${CLAUDE_SKILL_DIR}/dex.py" prompts                                # analyst + reviewer prompts
python3 "${CLAUDE_SKILL_DIR}/dex.py" history <pairAddress>                  # one pool across snapshots
```

Every scan writes `trader/dex/snapshot-<UTC>.csv` (never overwritten) and
`trader/dex/latest.json`. Open the CSV in any spreadsheet.

## The labels

| Label | When | Means |
|---|---|---|
| SKIP | missing price or liquidity, liquidity under `--min-liquidity` | the data cannot support a decision |
| REVIEW | same symbol on another token or chain, a pool under 72 hours old, one-sided buys or sells, volume over 5x liquidity, a 30 % move in 24 hours, low volume | a question to answer before anything else |
| WATCH | passes every check | worth researching; NOT a buy signal |

## The workflow

1. `scan` at consistent times. Keep every snapshot.
2. Open each row's url and confirm the chain, the pool and the token
   address. The same symbol is not proof of the same token.
3. `prompts` prints two prompts with the real rows. Run the **analyst** (in
   this conversation, as a separate pass, or in a fresh chat): it reports the
   fields exactly as given, flags problems and returns WATCH / REVIEW / SKIP.
   Then run the **reviewer** separately: it looks for reasons to reject and
   returns REJECT / NEEDS MORE DATA / PAPER TEST ONLY. Never let missing
   information turn into confidence.
4. `/trader-journal from-dex`, then for anything you would paper-trade,
   `journal.py add --decision PAPER` with the entry, stop, target, horizon
   and a cost estimate written BEFORE you look at what happened next.
5. Later, `journal.py observe`. Review false positives and missed risks; keep
   the prompts unchanged for the first sample so you do not fit to noise.

When Claude runs the analyst and reviewer itself, it reports only what the
rows say: no invented news, forecasts, fills or profits.

## Rules

- Paper mode only. This skill has no wallet connection, no keys, no order
  function, and none should be added to it.
- DEX Screener's search returns pools across chains; its API, limits and
  fields can change. Reference: https://docs.dexscreener.com/api/reference
- Liquidity on a DEX is the depth your own order would move. A pool with
  $20k of liquidity cannot absorb a $5k trade without a large price impact.
- A claim like "$63 to $8,980 in three nights" is a claim, not a record.
  Hypothetical results do not establish future performance.

This is not financial advice.
