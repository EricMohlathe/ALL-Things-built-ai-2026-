---
name: trader-budget
description: >-
  Budget Manager. Sizes a trade to your account and your max loss in the
  instrument's own units: forex and CFD lots, futures contracts, coins. Takes
  the smallest of four limits (max loss at the stop, account leverage, margin
  use, a notional cap), converts every amount from the quote currency into
  your account currency (USDJPY, the DAX in euros, the FTSE in pounds),
  respects the instrument's leverage cap (ESMA retail, the broker's, your
  own), rounds DOWN to the lot step, and writes one bracket order (entry,
  stop-loss, take-profit) to trader/orders.json. Long or short. Use when the
  user says "how many lots", "position size", "size this trade", "how much
  can I risk", "what's my margin", "lot size for 50 dollars risk", or after
  /trader-exit and /trader-timemachine, before /trader-risk.
argument-hint: "[--balance N] [--limit [PRICE]] [--rate USDJPY=154.2] [--write]"
---

# trader-budget

The Budget Manager answers one question: how big, so that being wrong costs
no more than you decided. It sizes in what the market trades (0.01 lots of
EURUSD, 1 contract of ES, 0.0001 BTC), in your account's currency, under your
leverage and margin limits. It never places anything.

`${CLAUDE_SKILL_DIR}` below is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/size.py"                         # trader/plan.json + trader/config.json
python3 "${CLAUDE_SKILL_DIR}/size.py" --write                 # write trader/orders.json
python3 "${CLAUDE_SKILL_DIR}/size.py" --limit                 # a limit order at the plan's entry
python3 "${CLAUDE_SKILL_DIR}/size.py" --balance 10000         # size against this balance
python3 "${CLAUDE_SKILL_DIR}/size.py" --rate EURUSD=1.162     # a conversion rate for a EUR-quoted index
```

Copy `config.example.json` to `trader/config.json` and set your
`account_currency`, `balance` and limits first.

## How much

Units of the instrument (euros of EURUSD, ounces of XAUUSD, coins, $50-a-point
multiples of ES), rounded DOWN to the lot step, the smallest of:

| limit | budget | per unit |
| --- | --- | --- |
| max loss | `max_loss_per_trade` | risk (entry - stop) x quote-to-account rate |
| leverage | equity x `max_account_leverage` - notional already open | entry x rate |
| margin | equity x `max_margin_use_pct` - margin in use | entry x rate / the leverage cap |
| notional cap | `max_position_notional` (optional) | entry x rate |

The leverage cap is the smallest of the instrument's (ESMA retail: 30:1 major
forex, 20:1 other forex, gold and major indices, 10:1 other commodities and
indices, 2:1 crypto; futures about the exchange margin), the broker's (Alpaca
crypto 1:1) and your config's `leverage` by symbol or class.

**Currency.** A quote currency that is not the account's is converted with
trader/prices.json (`alerts.py quote --holdings --rates --write`), the
config's `rates`, or `--rate`. USDJPY in a USD account uses its own price. A
missing rate is a plain refusal, never a guess.

**The entry it sizes at.** A limit order's price; for a market order, the
plan's entry or a fresh quote (under 15 minutes old) if that is WORSE for you
(higher for a long, lower for a short).

## Refusals (no order is written)

Zero lots (one minimum lot already risks more than your max loss), a reward:risk
under `min_reward_risk`, a plan for another day, a blocked symbol, futures with
`"allow_futures": false`.

## Steps

1. After `/trader-exit` (and the Time Machine), run `size.py`.
2. Say the size in the instrument's units and in units, which limit bound it,
   the max loss at the stop in the account currency, the notional, the account
   leverage after it, and the margin.
3. `size.py --write`, then `/trader-risk`.

## Example (test fixture, synthetic bars, $5,000 account, $50 max loss)

EURUSD long at 1.16285, stop 1.16160 (12.5 pips): $50 / 0.00125 = 40,000 units
= 0.40 lots, $50.00 at the stop, notional $46,514 (9.30x), margin about $1,550
at 30:1. The gold short: 0.09 lots (9 oz) x 5.55 = $49.95. USDJPY short with a
15-pip stop: max loss allows 0.51 lots but the 10x account leverage binds at 0.50.

## Safety

- Education and tooling, not financial advice. A size is arithmetic, not a recommendation.
- Leverage multiplies losses as much as gains. The max loss is at the stop price; a gap can make it worse.
- Paper trading by default (`"paper": true`). Going live is the user's own decision, in their own config.
- Nothing in this pack places an order except trader-broker, and only when all three hold: trader-risk
  passed that exact order today, the user typed an explicit yes for that one order in the chat, and the
  user clicked Allow once on Claude's own card where a connector places it. Never set an order tool to
  "Always allow".
