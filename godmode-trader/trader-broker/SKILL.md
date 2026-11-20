---
name: trader-broker
description: >-
  Order Executor. Shows each risk-checked order as a plain ticket (side, lots,
  units, stop-loss and take-profit in pips, max loss in your currency,
  notional and margin) plus the exact call for your broker: an OANDA v20 order
  body, Alpaca's place_crypto_order, a MetaTrader 5 trade request and MQL5
  CTrade line, a cTrader Automate ExecuteMarketOrder, or an Interactive Brokers
  bracket. Nothing goes through until trader-risk passed that exact order and
  the user typed an explicit yes for it; paper trading is the default. Records
  fills (signed positions, average price, realized P&L in the account
  currency), builds flatten and stand-alone stop tickets. Use when the user
  says "place the order", "send it", "execute", "buy it", "sell it", "go long",
  "go short", "close my position", "flatten", or after /trader-risk passes.
argument-hint: "[show|approve|result|fill|flatten|protect|log]"
---

# trader-broker

The Order Executor is the only skill that can lead to an order, and it is
built around one moment: the user's yes. It never talks to a broker itself.
It renders the ticket, records the user's explicit yes for that one order, and
hands Claude the exact call. Where a connector places it, Claude's own
"Allow once / Deny" card asks one more time.

`${CLAUDE_SKILL_DIR}` below is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/ticket.py" show                       # every order, READY or not
python3 "${CLAUDE_SKILL_DIR}/ticket.py" approve --index 1 --reply "yes"
python3 "${CLAUDE_SKILL_DIR}/ticket.py" decline --index 1
python3 "${CLAUDE_SKILL_DIR}/ticket.py" result --index 1 --status placed --broker-id ID --filled-price 1.16287
python3 "${CLAUDE_SKILL_DIR}/ticket.py" fill --symbol EURUSD --side sell --lots 0.40 --price 1.16410
python3 "${CLAUDE_SKILL_DIR}/ticket.py" flatten --symbol EURUSD      # close the open position by flat_by
python3 "${CLAUDE_SKILL_DIR}/ticket.py" protect --symbol BTCUSD      # a stand-alone stop (no brackets)
python3 "${CLAUDE_SKILL_DIR}/ticket.py" log
```

## Brokers ("broker" in trader/config.json)

| broker | what the ticket gives | brackets | short |
| --- | --- | --- | --- |
| `paper` (default) | nothing to send: record the pretend fill | yes | yes |
| `oanda` | the v20 body for POST /v3/accounts/{id}/orders (signed units, stopLossOnFill, takeProfitOnFill) | yes | yes |
| `alpaca` | place_crypto_order arguments (crypto spot) | no: `protect` after the fill | no |
| `mt5` | a MetaTrader 5 trade request (Python order_send) and the MQL5 CTrade line | yes | yes |
| `ctrader` | a cTrader Automate C# ExecuteMarketOrder, stop and target as distance / Symbol.PipSize | yes | yes |
| `ibkr` | an IBKR bracket (parent, take-profit, stop) to draft with your IBKR connector | yes | yes |

Broker symbols: OANDA names (EUR_USD, XAU_USD, SPX500_USD ...) are mapped;
set `"symbol_suffix"` (".m", "-ECN") or an instrument's `"broker_symbol"` in
the config for MT5 and cTrader. Check your broker's contract size per lot.

## Steps

1. `ticket.py show`. Show the user the ticket for ONE order at a time, in
   plain words: side, size, symbol, stop-loss and take-profit with their pips,
   max loss in the account currency, notional and margin, paper or LIVE.
2. Only a READY order can be approved: trader-risk passed THIS exact order
   today (fingerprint) and nobody has decided on it.
3. Wait for the user's reply. Then `ticket.py approve --index N --reply
   "<their words, exactly>"`. It records a yes only if the reply starts with
   "yes", names no other instrument or size, and has no doubt in it ("yes
   but", "yes to all", "sure", "ok", a question: all refused).
4. Make the call it prints with the broker's tool or connector (OANDA, Alpaca,
   IBKR), or tell the user exactly what to enter in MT5 or cTrader. Paper: no call.
5. `ticket.py result --index N --status placed|denied|failed`, with the fill
   when there is one. A fill updates trader/portfolio.json.
6. Before the flat-by time: `ticket.py flatten --symbol SYM`, then
   `/trader-risk` and the user's yes again.

## What it never does

It never places an order without a READY risk check and an explicit yes for
that one order, never takes one yes for several orders, never retries a
denied order on its own, never asks for or prints a broker key, and never
runs from a background job.

## Safety

- Education and tooling, not financial advice.
- Paper trading by default (`"paper": true`). Going live is the user's own decision, in their own config;
  a LIVE ticket says LIVE ACCOUNT, REAL MONEY.
- Nothing in this pack places an order except trader-broker, and only when all three hold: trader-risk
  passed that exact order today, the user typed an explicit yes for that one order in the chat, and the
  user clicked Allow once on Claude's own card where a connector places it. Set the order tool to
  "Needs approval" (Customize > Connectors > tool permissions), never "Always allow".
- Broker keys live in environment variables or the connector's own settings, never in the chat.
- Leveraged products (forex, CFDs, futures) can lose money fast; most retail CFD accounts lose money.
