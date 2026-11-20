---
name: trader-risk
description: >-
  Risk Manager. Checks every proposed order against your limits and stops
  anything over them, for forex, commodities, indices and crypto, long and
  short: max loss at the stop in your account currency, daily loss, trades and
  orders per day, reward to risk, account leverage, margin use, net exposure
  to any one currency or asset (two USD shorts are one big USD short), the
  session's entry window, the FX week's hours, and a news blackout around
  High-impact releases from the economic calendar. Exits that only reduce a
  position are never blocked. PASS or BLOCK with the reasons, fingerprinted so
  only that exact order can go to the broker. Use when the user says "check
  this order", "is this within my limits", "risk check", "am I over-leveraged",
  "what's my exposure", or always after /trader-budget and before /trader-broker.
argument-hint: "[--orders trader/orders.json] [--now TIME] [--json]"
---

# trader-risk

The Risk Manager is the gate. Every order passes through it, and an order it
blocks never reaches the broker. It checks the order as if every earlier
order in the batch had filled, so trades that are fine one by one but too
much together are caught.

`${CLAUDE_SKILL_DIR}` below is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/check.py"                       # writes trader/state/risk.json
python3 "${CLAUDE_SKILL_DIR}/check.py" --json --no-write
python3 "${CLAUDE_SKILL_DIR}/check.py" --now "2026-11-16 08:45 London"
```

## What it reads

| file | what |
| --- | --- |
| `trader/orders.json` | the proposed orders (trader-budget, or ticket.py flatten / protect) |
| `trader/config.json` | your limits (see below) |
| `trader/portfolio.json` | balance and open positions (signed units, average price); else the config's `balance` |
| `trader/prices.json` | prices and conversion rates (trader-alerts); a price over 15 minutes old is not used for the entry |
| `trader/calendar.json` | the week's events (trader-calendar), for the news blackout |
| `trader/journal.csv` | your journal (trader-journal), for the losing-streak pause |
| `trader/propfirm.json` | a tracked prop challenge (trader-propfirm), for its daily room |
| `trader/state/broker.json` | what was placed today (trader-broker) |

## What blocks an order

Any order: an unknown symbol; lots and units that disagree; a size off the lot
step or under the minimum; a bad type or time in force; a bracket missing a
leg; a class outside `allowed_classes`; futures with `"allow_futures": false`;
something your broker does not carry; a sell that opens a short when shorting
is off or impossible (crypto spot at Alpaca).

An entry, on top:

| check | rule |
| --- | --- |
| stop | none while `require_stop`, or on the wrong side |
| loss | units x \|entry - stop\| x the conversion rate over `max_loss_per_trade` |
| reward:risk | under `min_reward_risk` |
| daily loss | today's max losses at the stops plus this one over `max_daily_loss` |
| trades / orders | over `max_trades_per_day` / `max_orders_per_day`; a duplicate |
| streak | `max_consecutive_losses` (3) losing results in a row today in `trader/journal.csv`: stop for the day |
| prop firm | with `trader/propfirm.json` tracked: no room left today, or a loss at the stop over the guardian's largest safe risk |
| leverage | total notional after over `max_account_leverage` x equity |
| margin | margin in use after over `max_margin_use_pct` of equity |
| exposure | net long or short in one currency or asset over `max_currency_exposure_x` x equity |
| window | before the range ends, after the entry cutoff, or the session closed |
| news | a `news_blackout_impact` event for the instrument's currencies within `news_blackout_minutes` |

An exit (it only reduces what you hold) is checked for format and asset only;
everything else becomes a warning. Getting out must always be possible.

## Steps

1. After `/trader-budget`, and after `/trader-calendar` wrote this week's
   calendar, run `check.py`.
2. Say PASS or BLOCK per order with the reasons in plain words, and the
   warnings (correlated positions, an event coming up, a Friday, a live account).
3. A BLOCK goes no further. Say what would fix it (a smaller size, a closer
   stop, waiting out the news), never how to get around the rule.
4. On PASS: `/trader-broker`. The user still says yes to each order.

## Example (test fixture, synthetic bars)

At 08:45 London the EURUSD long passes: $50.00 at the stop, 9.30x the account,
margin $1,550 at 30:1, net EUR long $46,514, inside the London window 08:30 to
16:30, with a warning that the ECB President speaks in 75 minutes. The same
order at 09:45 London is BLOCKED: the speech is 15 minutes away, inside the
30-minute blackout.

## Safety

- Education and tooling, not financial advice. A PASS is a rules check, not a recommendation.
- Paper trading by default (`"paper": true`). Going live is the user's own decision, in their own config.
- Nothing in this pack places an order except trader-broker, and only when all three hold: trader-risk
  passed that exact order today, the user typed an explicit yes for that one order in the chat, and the
  user clicked Allow once on Claude's own card where a connector places it. Never set an order tool to
  "Always allow".
- Never loosen a limit in the config to make an order pass without the user asking for that change.
- Leveraged products (forex, CFDs, futures) can lose money fast; most retail CFD accounts lose money.
