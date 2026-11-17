#!/usr/bin/env python3
"""Order tickets and the decision log for trader-broker. Standard library only.

This tool never talks to a broker and never places anything. It does its work
around the one moment that matters, your yes:

  show      renders each proposed order as a plain-English ticket plus the exact
            call for your broker ("broker" in trader/config.json):
              oanda    the OANDA v20 order body (POST /v3/accounts/{id}/orders)
              alpaca   Alpaca's place_crypto_order arguments (crypto spot)
              mt5      a MetaTrader 5 trade request (Python order_send / MQL5 CTrade)
              ctrader  a cTrader Automate (cBot) ExecuteMarketOrder call
              ibkr     an Interactive Brokers bracket, drafted with your IBKR connector
              paper    no broker: you record the fill yourself
            An order is READY only if trader-risk passed THIS exact order today
            (matched by fingerprint) and nobody has decided on it yet.
  approve   records your explicit yes for ONE order, word for word. It refuses
            "yes to all", "sure", "ok", a yes that names a different symbol or
            size, and any order that is not READY.
  decline   records a no.
  result    records what happened after Claude's Allow once / Deny card:
            placed (with the broker's id), denied, or failed.
  fill      records a fill in trader/portfolio.json: signed units, average
            price, realized P&L into the balance (in the account currency).
  flatten   a closing ticket for a symbol's open position (long or short) by
            flat_by. It still goes through trader-risk and your yes.
  protect   a stand-alone stop-loss ticket for a broker without brackets
            (Alpaca crypto). Also through trader-risk and your yes.
  log       prints today's decisions.

    python3 ticket.py show
    python3 ticket.py approve --index 1 --reply "yes"
    python3 ticket.py result --index 1 --status placed --broker-id 61e6 --filled-price 1.16287
    python3 ticket.py fill --symbol EURUSD --side buy --lots 0.40 --price 1.16287
    python3 ticket.py flatten --symbol EURUSD
    python3 ticket.py log

Everything is written to trader/state/broker.json (append only). Dates are in the
config's "timezone"; --now "2026-11-16 08:45 London" pins the clock.
"""

import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "trader-core"))
import tradercore as tc  # noqa: E402

ORDER_FIELDS = ("symbol", "side", "type", "time_in_force", "lots", "units", "limit_price", "stop_price",
                "stop_loss", "take_profit", "order_class", "client_order_id")
TIF_WORDS = {"day": "good for today", "gtc": "good until canceled", "ioc": "immediate or cancel",
             "fok": "fill or kill", "gtd": "good until a date"}
YES_WORDS = ("yes", "y")
BATCH_WORDS = {"all", "every", "everything", "rest", "remaining", "them", "both", "batch", "each"}
DOUBT_WORDS = {"no", "not", "dont", "don't", "wait", "cancel", "stop", "but", "maybe", "later", "hold", "unless",
               "if"}
OANDA_NAMES = {"XAUUSD": "XAU_USD", "XAGUSD": "XAG_USD", "XPTUSD": "XPT_USD", "XPDUSD": "XPD_USD",
               "USOIL": "WTICO_USD", "UKOIL": "BCO_USD", "NATGAS": "NATGAS_USD", "COPPER": "XCU_USD",
               "US500": "SPX500_USD", "US100": "NAS100_USD", "US30": "US30_USD", "US2000": "US2000_USD",
               "GER40": "DE30_EUR", "UK100": "UK100_GBP", "FRA40": "FR40_EUR", "EU50": "EU50_EUR",
               "JPN225": "JP225_USD", "HK50": "HK33_HKD", "AUS200": "AU200_AUD"}


class TicketError(tc.TraderError):
    pass


def fingerprint(order):
    """Same function as trader-risk/check.py: identifies the exact order."""
    core = {k: order[k] for k in ORDER_FIELDS if k in order and order[k] is not None}
    blob = json.dumps(core, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def rec_day(rec):
    return str(rec.get("date") or str(rec.get("at", ""))[:10])


def local_iso(now_utc, zone):
    off = tc.offset_minutes(zone, now_utc)
    return "%s%s%02d:%02d" % (tc.to_local(zone, now_utc).replace(microsecond=0).isoformat(), "+" if off >= 0 else "-",
                              abs(off) // 60, abs(off) % 60)


# ---------------------------------------------------------------- the order in words

def _inst(order, cfg):
    return tc.resolve(order.get("symbol"), cfg)


def broker_symbol(inst, cfg, broker):
    own = ((cfg.get("instruments") or {}).get(inst["symbol"]) or {}).get("broker_symbol")
    if own:
        return own
    if broker == "oanda":
        if inst["class"] == "forex":
            return "%s_%s" % (inst["base"], inst["quote"])
        return OANDA_NAMES.get(inst["symbol"], inst["symbol"])
    if broker == "alpaca":
        return "%s/%s" % (inst["base"], inst["quote"])
    return inst["symbol"] + (cfg.get("symbol_suffix") or "")


def max_loss(order, inst, cfg):
    """(account-currency loss at the stop, stop) or (None, stop)."""
    plan = order.get("plan") or {}
    stop = _f(order.get("stop_loss")) or _f(plan.get("stop"))
    units = _f(order.get("units"))
    if not stop or not units:
        return None, stop
    if order.get("type") == "limit" and _f(order.get("limit_price")):
        entry = _f(order["limit_price"])
    elif _f(plan.get("max_loss")) is not None:
        return round(_f(plan["max_loss"]), 2), stop
    else:
        entry = _f(plan.get("entry"))
    conv = _f(plan.get("conversion")) or 1.0
    if not entry:
        return None, stop
    return round(units * abs(entry - stop) * conv, 2), stop


def size_words(order, inst):
    lots = order.get("lots") or tc.num((_f(order.get("units")) or 0) / inst["contract"])
    if inst["unit"] == "contract":
        return "%s contract%s" % (lots, "" if _f(lots) == 1 else "s")
    if inst["unit"] == "coin":
        return "%s %s" % (lots, inst["base"])
    return "%s lot%s (%s units)" % (lots, "" if _f(lots) == 1 else "s",
                                   "{:,.6f}".format(_f(order.get("units")) or 0).rstrip("0").rstrip("."))


def plain_parts(order, inst, cfg):
    side = str(order.get("side", "")).upper()
    typ = str(order.get("type", "market"))
    tif = TIF_WORDS.get(str(order.get("time_in_force", "day")), order.get("time_in_force"))
    how = ("limit %s" % order["limit_price"]) if typ == "limit" and order.get("limit_price") else \
        ("stop %s" % order["stop_price"]) if typ == "stop" and order.get("stop_price") else typ
    parts = ["%s %s %s, %s, %s" % (side, size_words(order, inst), inst["symbol"], how, tif)]
    plan = order.get("plan") or {}
    entry = _f(order.get("limit_price")) or _f(plan.get("entry"))
    if order.get("stop_loss") is not None:
        d = (" (%s)" % tc.fmt_dist(abs(entry - _f(order["stop_loss"])), inst)) if entry else ""
        parts.append("stop-loss %s%s" % (order["stop_loss"], d))
    if order.get("take_profit") is not None:
        d = (" (%s)" % tc.fmt_dist(abs(_f(order["take_profit"]) - entry), inst)) if entry else ""
        parts.append("take-profit %s%s" % (order["take_profit"], d))
    loss, stop = max_loss(order, inst, cfg)
    if loss is not None:
        parts.append("max loss about %s if the stop fills at %s (it can fill worse in a fast market or a gap)"
                     % (tc.money(loss, plan.get("currency") or cfg["account_currency"]), tc.fmt_price(stop, inst)))
    if plan.get("notional"):
        parts.append("notional %s, margin about %s" % (
            tc.money(plan["notional"], plan.get("currency") or cfg["account_currency"]),
            tc.money(plan.get("margin") or 0, plan.get("currency") or cfg["account_currency"])))
    return parts


def plain(order, inst, cfg):
    return " / ".join(plain_parts(order, inst, cfg))


def amount_numbers(order, inst, cfg):
    nums = []
    for k in ("lots", "units", "limit_price", "stop_loss", "take_profit", "stop_price"):
        v = _f(order.get(k))
        if v is not None:
            nums.append(v)
    loss, _ = max_loss(order, inst, cfg)
    if loss is not None:
        nums.append(loss)
    return nums


def parse_yes(reply, order, inst, cfg, batch_symbols=()):
    """Is this reply an explicit yes for THIS one order? (ok, why)."""
    raw = (reply or "").strip()
    if not raw:
        return False, "the reply is empty"
    if "?" in raw:
        return False, "the reply is a question, not a yes"
    words = re.findall(r"[a-z']+", raw.lower())
    if not words or words[0] not in YES_WORDS:
        return False, "only a reply that starts with \"yes\" counts (not ok, sure, go, do it)"
    if BATCH_WORDS & set(words):
        return False, "a yes covers one order at a time, not a batch"
    if DOUBT_WORDS & set(words[1:]):
        return False, "the reply has a condition or a doubt in it; ask again"
    sym = inst["symbol"]
    tokens = set(re.findall(r"[A-Z0-9][A-Z0-9/_.\-=^&]{1,11}", raw.upper()))
    idx = tc._alias_index(tc.registry(cfg))
    named = set()
    for t in tokens:                      # any instrument the reply names that is not this one
        other = idx.get(t) or idx.get(re.sub(r"[^A-Z0-9]", "", t))
        if other and other != sym and not (len(t) < 3 and t.isdigit()):
            named.add(other)
    for s in set(batch_symbols) - {sym}:
        if str(s).upper() in tokens:
            named.add(str(s).upper())
    if named:
        return False, "the reply names %s, but this order is for %s" % (", ".join(sorted(named)), sym)
    nums = [float(n.replace(",", "")) for n in re.findall(r"(?<![A-Za-z])\d[\d,]*(?:\.\d+)?", raw)]
    nums = [n for n in nums if not any(n == float(d) for d in re.findall(r"\d+", sym))]
    if nums:
        want = amount_numbers(order, inst, cfg)
        def same(n, w):
            return abs(n - w) < 1e-9 or (abs(w) >= 1 and abs(n - w) < 0.005)
        if not any(same(n, w) for n in nums for w in want):
            return False, "the reply says %s, but this order is %s" % (", ".join(tc.num(n) for n in nums),
                                                                       plain(order, inst, cfg))
    return True, "explicit yes for %s" % plain(order, inst, cfg)


# ---------------------------------------------------------------- broker calls

def tool_call(order, inst, cfg):
    """{"broker", "tool", "input", "notes"}: the exact call for the configured broker."""
    b = tc.broker_profile(cfg)["name"]
    sym = broker_symbol(inst, cfg, b)
    side = order.get("side")
    typ = order.get("type", "market")
    units = _f(order.get("units")) or 0
    out = {"broker": b, "notes": []}
    if b == "oanda":
        signed = units if side == "buy" else -units
        body = {"type": "LIMIT" if typ == "limit" else "MARKET", "instrument": sym, "units": tc.num(signed),
                "timeInForce": "GTC" if typ == "limit" else "FOK", "positionFill": "DEFAULT"}
        if typ == "limit":
            body["price"] = order["limit_price"]
        if order.get("stop_loss"):
            body["stopLossOnFill"] = {"price": order["stop_loss"], "timeInForce": "GTC"}
        if order.get("take_profit"):
            body["takeProfitOnFill"] = {"price": order["take_profit"]}
        out.update(tool="OANDA v20: POST /v3/accounts/{accountID}/orders", input={"order": body})
        out["notes"].append("OANDA units are signed (negative = sell) and in the base unit: %s." %
                            ("euros of EUR_USD" if inst["class"] == "forex" else "1 unit = 1 %s" % inst["unit"]))
    elif b == "alpaca":
        body = {"symbol": sym, "side": side, "type": typ, "time_in_force": "gtc", "qty": order.get("lots")}
        if typ == "limit":
            body["limit_price"] = order["limit_price"]
        out.update(tool="place_crypto_order", input=body)
        out["notes"].append("Alpaca takes no bracket on crypto: once it fills, place the stop with "
                            "ticket.py protect --symbol %s (a stop-limit sell), and keep the alert on." % inst["symbol"])
    elif b == "mt5":
        vol = _f(order.get("lots"))
        is_buy = side == "buy"
        req = {"action": "TRADE_ACTION_PENDING" if typ == "limit" else "TRADE_ACTION_DEAL", "symbol": sym,
               "volume": vol, "type": ("ORDER_TYPE_BUY" if is_buy else "ORDER_TYPE_SELL") +
               ("_LIMIT" if typ == "limit" else ""), "sl": _f(order.get("stop_loss")), "tp": _f(order.get("take_profit")),
               "deviation": 20, "magic": 20261116, "comment": "godmode-trader", "type_time": "ORDER_TIME_GTC",
               "type_filling": "ORDER_FILLING_IOC"}
        if typ == "limit":
            req["price"] = _f(order["limit_price"])
        out.update(tool="MetaTrader 5 order_send (Python) / MqlTradeRequest", input=req)
        out["mql5"] = 'trade.%s(%s, "%s", %s, %s, %s, "godmode-trader");' % (
            ("Buy" if is_buy else "Sell") + ("Limit" if typ == "limit" else ""), tc.num(vol), sym,
            order.get("limit_price") or "0.0", order.get("stop_loss") or "0.0", order.get("take_profit") or "0.0")
        out["notes"].append("Check the broker's contract size for %s in MT5 (SymbolInfo, trade contract size): "
                            "this pack assumes %s units a lot." % (sym, tc.num(inst["contract"])))
    elif b == "ctrader":
        plan = order.get("plan") or {}
        entry = _f(order.get("limit_price")) or _f(plan.get("entry")) or 0
        sl = abs(entry - (_f(order.get("stop_loss")) or entry))
        tp = abs((_f(order.get("take_profit")) or entry) - entry)
        tt = "TradeType.Buy" if side == "buy" else "TradeType.Sell"
        code = ('var s = Symbols.GetSymbol("%s");\nExecuteMarketOrder(%s, s.Name, %s, "godmode-trader", '
                '%s / s.PipSize, %s / s.PipSize);' % (sym, tt, tc.num(units), tc.num(round(sl, 10)),
                                                      tc.num(round(tp, 10))))
        if typ == "limit":
            code = ('var s = Symbols.GetSymbol("%s");\nPlaceLimitOrder(%s, s.Name, %s, %s, "godmode-trader", '
                    '%s / s.PipSize, %s / s.PipSize);' % (sym, tt, tc.num(units), order["limit_price"],
                                                          tc.num(round(sl, 10)), tc.num(round(tp, 10))))
        out.update(tool="cTrader Automate (cBot) C#", input={"code": code, "volume_in_units": tc.num(units)})
        out["notes"].append("The stop and target go in as price distances divided by the symbol's own PipSize, so "
                            "they are right whatever pip size your cTrader broker uses.")
    elif b == "ibkr":
        sec = {"future": "FUT", "cfd": "CFD", "spot": "CASH" if inst["class"] == "forex" else "CRYPTO"}[inst["kind"]]
        qty = _f(order.get("lots")) if inst["kind"] == "future" else units
        parent = {"action": side.upper(), "totalQuantity": qty, "orderType": "LMT" if typ == "limit" else "MKT",
                  "tif": "DAY"}
        if typ == "limit":
            parent["lmtPrice"] = _f(order["limit_price"])
        legs = []
        if order.get("take_profit"):
            legs.append({"action": "SELL" if side == "buy" else "BUY", "orderType": "LMT",
                         "lmtPrice": _f(order["take_profit"]), "totalQuantity": qty})
        if order.get("stop_loss"):
            legs.append({"action": "SELL" if side == "buy" else "BUY", "orderType": "STP",
                         "auxPrice": _f(order["stop_loss"]), "totalQuantity": qty})
        contract = {"symbol": sym, "secType": sec, "currency": inst["quote"]}
        if sec == "CASH":
            contract = {"symbol": inst["base"], "secType": "CASH", "currency": inst["quote"], "exchange": "IDEALPRO"}
        elif sec == "FUT":
            contract["note"] = "front month; IBKR needs the contract month (lastTradeDateOrContractMonth)"
        out.update(tool="Interactive Brokers connector (draft a bracket order)",
                   input={"contract": contract, "parent": parent, "children": legs})
        out["notes"].append("IBKR sends it to your account, and it only goes to the market after you approve it there.")
    else:
        out.update(tool=None, input={k: order[k] for k in ORDER_FIELDS if k in order})
        out["notes"].append("Paper: no broker. Pretend-fill it at the next price and record it with "
                            "ticket.py result --index N --status placed --filled-price P.")
    return out


# ---------------------------------------------------------------- state

def load_state(path):
    return tc.read_json(path, "broker state", required=False) or {"orders": []}


def latest(state, fp, today):
    found = None
    for rec in state.get("orders", []):
        if rec.get("fingerprint") == fp and rec_day(rec) == today:
            found = rec
    return found


def risk_verdict(risk, fp, today):
    if not risk:
        return None, "trader-risk has not checked these orders (run check.py)"
    if risk.get("date") != today:
        return None, "the risk check is from %s, not today; run check.py again" % risk.get("date")
    for r in risk.get("results", []):
        if r.get("fingerprint") == fp:
            return r, None
    return None, "this exact order was not in the last risk check (it changed or is new); run check.py again"


def status_of(order, risk, state, today):
    fp = fingerprint(order)
    rv, why = risk_verdict(risk, fp, today)
    if rv is None:
        return False, "NOT READY: " + why, None
    if rv.get("verdict") != "PASS":
        return False, "BLOCKED by trader-risk: " + "; ".join(rv.get("reasons", [])), rv
    rec = latest(state, fp, today)
    if rec:
        if rec.get("status") == "approved":
            return False, "APPROVED by you at %s, waiting for the broker call" % rec.get("at"), rv
        return False, "DONE: %s at %s" % (rec.get("status"), rec.get("at")), rv
    return True, "READY: trader-risk PASS, waiting for your yes", rv


def render(order, idx, total, cfg, risk, state, today):
    inst = _inst(order, cfg)
    ready, label, rv = status_of(order, risk, state, today)
    call = tool_call(order, inst, cfg)
    paper = cfg.get("paper", True)
    lines = ["ORDER %d of %d, %s, %s" % (idx, total, "PAPER account" if paper else "LIVE ACCOUNT, REAL MONEY",
                                        tc.broker_profile(cfg)["label"])]
    for part in plain_parts(order, inst, cfg):
        lines.append("  " + part)
    if order.get("why"):
        lines.append("  why: " + order["why"])
    lines.append("  " + label)
    for w in (rv or {}).get("warnings", []):
        lines.append("  note: " + w)
    if call["tool"]:
        lines.append("  %s, exactly:" % call["tool"])
        if call["broker"] == "ctrader":
            for l in call["input"]["code"].splitlines():
                lines.append("    " + l)
        else:
            for l in json.dumps(call["input"], indent=2).splitlines():
                lines.append("    " + l)
        if call.get("mql5"):
            lines.append("  MQL5 (CTrade): " + call["mql5"])
    for n in call["notes"]:
        lines.append("  " + n)
    if ready:
        lines.append("  Reply \"yes\" to place this one order, or \"no\" to skip it.")
    return "\n".join(lines), ready


def ticket_json(order, idx, cfg, risk, state, today):
    inst = _inst(order, cfg)
    ready, label, rv = status_of(order, risk, state, today)
    loss, stop = max_loss(order, inst, cfg)
    call = tool_call(order, inst, cfg)
    return {"index": idx, "ready": ready, "status": label, "plain": plain(order, inst, cfg),
            "fingerprint": fingerprint(order), "paper": bool(cfg.get("paper", True)), "broker": call["broker"],
            "tool": call["tool"], "tool_input": call["input"], "mql5": call.get("mql5"), "notes": call["notes"],
            "why": order.get("why", ""), "max_loss": loss, "stop": stop}


# ---------------------------------------------------------------- fills -> portfolio

def apply_fill(path, cfg, symbol, side, units, price, date, rates):
    """A fill in trader/portfolio.json: signed units and average price per symbol; a fill
    against the position realizes P&L into the balance, converted to the account currency."""
    pf = tc.read_json(path, "portfolio", required=False)
    acct = cfg["account_currency"]
    if pf is None:
        if not cfg.get("balance"):
            raise TicketError("no %s yet and no \"balance\" in the config to start it from" % path)
        pf = {"currency": acct, "balance": float(cfg["balance"]), "positions": [], "realized": []}
    inst = tc.resolve(symbol, cfg)
    units, price = float(units), float(price)
    if units <= 0 or price <= 0:
        raise TicketError("a fill needs positive units and a positive price")
    signed = units if tc.side_word(side) == "buy" else -units
    pos = next((p for p in pf.setdefault("positions", []) if str(p.get("symbol", "")).upper() == inst["symbol"]), None)
    if pos is None:
        pos = {"symbol": inst["symbol"], "units": 0.0, "avg_price": price, "opened": date}
        pf["positions"].append(pos)
    held = float(pos.get("units", 0))
    realized = 0.0
    if held == 0 or (held > 0) == (signed > 0):
        new = held + signed
        pos["avg_price"] = (abs(held) * float(pos.get("avg_price") or price) + abs(signed) * price) / abs(new)
        pos["units"] = new
    else:
        closing = min(abs(held), abs(signed))
        conv = tc.quote_to_account(inst, acct, rates, price)
        direction = 1 if held > 0 else -1
        realized = (price - float(pos["avg_price"])) * closing * direction * conv
        rest = held + signed
        if abs(rest) < 1e-9:
            pf["positions"].remove(pos)
        elif (rest > 0) == (held > 0):
            pos["units"] = rest
        else:
            pos.update(units=rest, avg_price=price, opened=date)
        pf["balance"] = round(float(pf.get("balance", 0)) + realized, 2)
        pf.setdefault("realized", []).append({"date": date, "symbol": inst["symbol"], "units": closing,
                                              "price": price, "pnl": round(realized, 2), "currency": acct})
    for p in pf["positions"]:
        p["units"] = round(float(p["units"]), 8)
        p["avg_price"] = round(float(p["avg_price"]), inst["digits"] + 3)
    tc.write_json(path, pf)
    return pf, realized


def log_fill(state_path, now, today, zone, symbol, side, units, price):
    state = load_state(state_path)
    state.setdefault("orders", []).append({
        "at": local_iso(now, zone), "date": today, "status": "filled", "symbol": symbol.upper(), "side": side,
        "units": tc.num(units), "price": float(price),
        "plain": "%s %s %s at %s" % (side.upper(), tc.num(units), symbol.upper(), tc.num(price))})
    tc.write_json(state_path, state)


# ---------------------------------------------------------------- commands

def _clock(a, cfg):
    now = tc.parse_now(getattr(a, "now", None), cfg["timezone"])
    today = getattr(a, "today", None) or tc.to_local(cfg["timezone"], now).date().isoformat()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", today):
        raise TicketError("--today wants a date like 2026-11-16")
    return now, today


def _load(a):
    cfg = tc.load_config(a.config)
    doc = tc.read_json(a.orders, "orders file (run trader-budget, or ticket.py flatten, first)")
    orders = doc.get("orders", doc) if isinstance(doc, dict) else doc
    if not isinstance(orders, list) or not orders:
        raise TicketError("no orders in %s" % a.orders)
    risk = tc.read_json(a.risk, "risk check", required=False)
    state = load_state(a.state)
    now, today = _clock(a, cfg)
    return orders, cfg, risk, state, today, now


def _pick(orders, index):
    if index is None:
        raise TicketError("say which order: --index N")
    if not 1 <= index <= len(orders):
        raise TicketError("there is no order %d (there are %d)" % (index, len(orders)))
    return orders[index - 1]


def cmd_show(a):
    orders, cfg, risk, state, today, now = _load(a)
    picks = [(a.index, _pick(orders, a.index))] if a.index else list(enumerate(orders, 1))
    if a.json:
        out = [ticket_json(o, i, cfg, risk, state, today) for i, o in picks]
        print(json.dumps(out[0] if a.index else out, indent=2))
        return 0 if any(t["ready"] for t in out) else 1
    blocks, any_ready = [], False
    for i, o in picks:
        text, ready = render(o, i, len(orders), cfg, risk, state, today)
        blocks.append(text)
        any_ready = any_ready or ready
    print("\n\n".join(blocks))
    print("\nOne order at a time: a yes covers one ticket, never the batch. %s" % tc.NOTE_ADVICE)
    return 0 if any_ready else 1


def cmd_approve(a):
    orders, cfg, risk, state, today, now = _load(a)
    order = _pick(orders, a.index)
    inst = _inst(order, cfg)
    ready, label, rv = status_of(order, risk, state, today)
    if not ready:
        raise TicketError("order %d is not ready: %s" % (a.index, label))
    ok, why = parse_yes(a.reply, order, inst, cfg, [str(o.get("symbol", "")) for o in orders])
    if not ok:
        print("Not recorded: %s. Ask the user again with the ticket for order %d." % (why, a.index))
        return 1
    loss, stop = max_loss(order, inst, cfg)
    rec = {"at": local_iso(now, cfg["timezone"]), "date": today, "index": a.index, "fingerprint": fingerprint(order),
           "symbol": inst["symbol"], "side": order.get("side"), "lots": order.get("lots"), "units": order.get("units"),
           "kind": (rv or {}).get("kind", "entry"), "max_loss": loss, "stop": stop, "plain": plain(order, inst, cfg),
           "status": "approved", "reply": a.reply, "paper": bool(cfg.get("paper", True)),
           "broker": tc.broker_profile(cfg)["name"]}
    state.setdefault("orders", []).append(rec)
    tc.write_json(a.state, state)
    call = tool_call(order, inst, cfg)
    print("Recorded your yes for order %d: %s." % (a.index, plain(order, inst, cfg)))
    if call["tool"]:
        print("Now send it with %s, exactly:" % call["tool"])
        print(call["input"]["code"] if call["broker"] == "ctrader" else json.dumps(call["input"], indent=2))
        print("Claude's own card asks again (Allow once / Deny) where a connector places it. Then: ticket.py result "
              "--index %d --status placed|denied|failed" % a.index)
    else:
        print("Paper: record the fill with ticket.py result --index %d --status placed --filled-price P" % a.index)
    return 0


def cmd_decline(a):
    orders, cfg, risk, state, today, now = _load(a)
    order = _pick(orders, a.index)
    inst = _inst(order, cfg)
    state.setdefault("orders", []).append({
        "at": local_iso(now, cfg["timezone"]), "date": today, "index": a.index, "fingerprint": fingerprint(order),
        "symbol": inst["symbol"], "side": order.get("side"), "plain": plain(order, inst, cfg), "status": "declined",
        "reply": a.reply or "no"})
    tc.write_json(a.state, state)
    print("Recorded: you said no to order %d (%s). Nothing was sent." % (a.index, plain(order, inst, cfg)))
    return 0


def _rates(a, cfg):
    pdoc = tc.read_json(getattr(a, "prices", "trader/prices.json"), "prices", required=False)
    return tc.rates_from(pdoc, cfg, tc.parse_rates(getattr(a, "rate", None)))


def cmd_result(a):
    orders, cfg, risk, state, today, now = _load(a)
    order = _pick(orders, a.index)
    fp = fingerprint(order)
    rec = latest(state, fp, today)
    if not rec or rec.get("status") != "approved":
        raise TicketError("order %d has no yes recorded today; a result can only follow an approval" % a.index)
    new = {"at": local_iso(now, cfg["timezone"]), "date": today, "index": a.index, "fingerprint": fp,
           "symbol": rec["symbol"], "side": rec["side"], "plain": rec["plain"], "status": a.status}
    for k in ("lots", "units", "kind", "max_loss", "stop"):
        if rec.get(k) is not None:
            new[k] = rec[k]
    if a.broker_id:
        new["broker_order_id"] = a.broker_id
    if a.note:
        new["note"] = a.note
    state["orders"].append(new)
    tc.write_json(a.state, state)
    print("Recorded order %d as %s." % (a.index, a.status))
    if a.status == "placed" and a.filled_price:
        units = _f(a.filled_units) or _f(rec.get("units"))
        pf, realized = apply_fill(a.portfolio, cfg, rec["symbol"], rec["side"], units, a.filled_price, today,
                                  _rates(a, cfg))
        log_fill(a.state, now, today, cfg["timezone"], rec["symbol"], rec["side"], units, a.filled_price)
        print("Added the fill to %s (balance %s)." % (a.portfolio, tc.money(pf["balance"], cfg["account_currency"])))
    elif a.status == "placed":
        print("When it fills, record it: ticket.py fill --symbol %s --side %s --units U --price P"
              % (rec["symbol"], rec["side"]))
    return 0


def cmd_fill(a):
    cfg = tc.load_config(a.config)
    now, today = _clock(a, cfg)
    date = a.date or today
    inst = tc.resolve(a.symbol, cfg)
    if (a.units is None) == (a.lots is None):
        raise TicketError("give --units or --lots")
    units = _f(a.units) if a.units is not None else _f(a.lots) * inst["contract"]
    pf, realized = apply_fill(a.portfolio, cfg, inst["symbol"], tc.side_word(a.side), units, a.price, date,
                              _rates(a, cfg))
    log_fill(a.state, now, date, cfg["timezone"], inst["symbol"], tc.side_word(a.side), units, a.price)
    acct = cfg["account_currency"]
    print("Recorded %s %s %s at %s on %s in %s.%s Balance %s." % (
        tc.side_word(a.side), tc.num(units), inst["symbol"], tc.fmt_price(a.price, inst), date, a.portfolio,
        (" Realized %s." % tc.money(realized, acct)) if realized else "", tc.money(pf["balance"], acct)))
    return 0


def _write_ticket(a, cfg, now, order, source):
    old = tc.read_json(a.orders, "orders", required=False)
    replaced = len(old.get("orders", [])) if isinstance(old, dict) else 0
    tc.write_json(a.orders, {"created_by": "trader-broker", "created_at": tc.iso(now), "status": "proposed",
                             "paper": bool(cfg.get("paper", True)), "broker": cfg.get("broker", "paper"),
                             "note": "Nothing is placed until trader-risk passes it and you say yes in the chat.",
                             "source": source, "orders": [order]})
    return replaced


def _held(a, cfg, sym, inst):
    if a.units is not None:
        u = _f(a.units)
        if u is None or u == 0:
            raise TicketError("--units wants the signed units you hold, e.g. 40000 or -9")
        return u, "--units"
    pf = tc.read_json(a.portfolio, "portfolio", required=False) or {}
    u = sum(p["units"] for p in tc.portfolio_positions(pf) if p["symbol"] == sym)
    if abs(u) < 1e-12:
        raise TicketError("nothing to close: no %s position in %s. Check the broker and pass --units if you hold "
                          "some (negative for a short)" % (sym, a.portfolio))
    return u, a.portfolio


def cmd_flatten(a):
    cfg = tc.load_config(a.config)
    now, today = _clock(a, cfg)
    inst = tc.resolve(a.symbol, cfg)
    sym = inst["symbol"]
    held, source = _held(a, cfg, sym, inst)
    units = abs(held)
    plan = tc.read_json(a.plan, "plan", required=False) or {}
    flat_by = plan.get("flat_by") if str(plan.get("symbol", "")).upper() == sym else None
    lots = units / inst["contract"]
    order = {"symbol": sym, "class": inst["class"], "kind": inst["kind"], "side": "sell" if held > 0 else "buy",
             "type": "market", "time_in_force": "day" if inst["class"] != "crypto" else "gtc",
             "lots": tc.num(round(lots, 8)), "units": tc.num(units),
             "why": "flatten: closes the %s %s (%s units, from %s)%s" % (
                 "long" if held > 0 else "short", sym, tc.num(units), source,
                 (" by the plan's flat-by %s" % flat_by) if flat_by else "")}
    replaced = _write_ticket(a, cfg, now, order, "ticket.py flatten %s on %s" % (sym, today))
    print("Flatten %s: %s." % (sym, plain(order, inst, cfg)))
    print("Wrote it to %s%s." % (a.orders, (" (it replaced %d earlier proposal%s)" % (
        replaced, "" if replaced == 1 else "s")) if replaced else ""))
    print("Next: check.py (closing only what you hold is never blocked by the daily limits, the window or the "
          "news blackout), then ticket.py show and the user's yes for this one order.")
    print("If the bracket's stop-loss and take-profit are still working at the broker, cancel them first (or close "
          "the position itself, which cancels them at OANDA, MT5 and cTrader).")
    return 0


def cmd_protect(a):
    cfg = tc.load_config(a.config)
    now, today = _clock(a, cfg)
    inst = tc.resolve(a.symbol, cfg)
    held, source = _held(a, cfg, inst["symbol"], inst)
    plan = tc.read_json(a.plan, "plan", required=False) or {}
    stop = _f(a.stop) or (_f(plan.get("stop")) if str(plan.get("symbol", "")).upper() == inst["symbol"] else None)
    if not stop:
        raise TicketError("no stop: pass --stop PRICE or keep the plan in %s" % a.plan)
    long = held > 0
    slip = tc.D(inst["tick"]) * 20
    limit = tc.to_tick(tc.D(stop) - slip if long else tc.D(stop) + slip, inst["tick"])
    order = {"symbol": inst["symbol"], "class": inst["class"], "kind": inst["kind"],
             "side": "sell" if long else "buy", "type": "stop", "time_in_force": "gtc",
             "lots": tc.num(abs(held) / inst["contract"]), "units": tc.num(abs(held)),
             "stop_price": tc.fmt_price(stop, inst), "limit_price": tc.fmt_price(limit, inst),
             "why": "protect: a stand-alone stop for the %s %s (%s units, from %s)" % (
                 "long" if long else "short", inst["symbol"], tc.num(abs(held)), source)}
    _write_ticket(a, cfg, now, order, "ticket.py protect %s on %s" % (inst["symbol"], today))
    print("Protect %s: %s, stop %s (limit %s)." % (inst["symbol"], plain(order, inst, cfg), order["stop_price"],
                                                   order["limit_price"]))
    print("Wrote it to %s. Next: check.py, ticket.py show, and the user's yes." % a.orders)
    return 0


def cmd_log(a):
    cfg = tc.load_config(a.config)
    state = load_state(a.state)
    now, today = _clock(a, cfg)
    rows = [r for r in state.get("orders", []) if a.all or rec_day(r) == today]
    if not rows:
        print("No decisions recorded%s." % ("" if a.all else " today"))
        return 1
    for r in rows:
        extra = (" id " + r["broker_order_id"]) if r.get("broker_order_id") else ""
        reply = (' reply "%s"' % r["reply"]) if r.get("reply") and r["status"] in ("approved", "declined") else ""
        idx = ("#%s" % r["index"]) if r.get("index") is not None else "  "
        print("%s  %s %-9s %s%s%s" % (r.get("at"), idx, r.get("status"), r.get("plain"), reply, extra))
    print("%d placed%s." % (sum(1 for r in rows if r.get("status") == "placed"), "" if a.all else " today"))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Order tickets and your yes (trader-broker). Never places orders.")
    sub = ap.add_subparsers(dest="cmd")

    def clock(p):
        p.add_argument("--now", help='pretend it is this time, e.g. "2026-11-16 08:45 London"')
        p.add_argument("--today", help="YYYY-MM-DD (default: today in the config's time zone)")
        p.add_argument("--config", default="trader/config.json")

    def common(p):
        p.add_argument("--orders", default="trader/orders.json")
        p.add_argument("--risk", default="trader/state/risk.json")
        p.add_argument("--state", default="trader/state/broker.json")
        clock(p)

    p = sub.add_parser("show", help="render the tickets")
    common(p)
    p.add_argument("--index", type=int)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("approve", help="record the user's explicit yes for one order")
    common(p)
    p.add_argument("--index", type=int, required=True)
    p.add_argument("--reply", required=True, help="the user's reply, word for word")
    p = sub.add_parser("decline", help="record a no")
    common(p)
    p.add_argument("--index", type=int, required=True)
    p.add_argument("--reply")
    p = sub.add_parser("result", help="record what happened after the Allow once / Deny card")
    common(p)
    p.add_argument("--index", type=int, required=True)
    p.add_argument("--status", required=True, choices=["placed", "denied", "failed"])
    p.add_argument("--broker-id")
    p.add_argument("--note")
    p.add_argument("--filled-units")
    p.add_argument("--filled-price")
    p.add_argument("--portfolio", default="trader/portfolio.json")
    p.add_argument("--prices", default="trader/prices.json")
    p.add_argument("--rate", action="append", metavar="PAIR=RATE")
    p = sub.add_parser("fill", help="record a fill in trader/portfolio.json")
    p.add_argument("--symbol", required=True)
    p.add_argument("--side", required=True)
    p.add_argument("--units")
    p.add_argument("--lots")
    p.add_argument("--price", required=True)
    p.add_argument("--date", help="YYYY-MM-DD (default: today)")
    p.add_argument("--portfolio", default="trader/portfolio.json")
    p.add_argument("--state", default="trader/state/broker.json")
    p.add_argument("--prices", default="trader/prices.json")
    p.add_argument("--rate", action="append", metavar="PAIR=RATE")
    clock(p)
    for name, hlp in (("flatten", "a closing ticket for a symbol's open position"),
                      ("protect", "a stand-alone stop ticket (brokers without brackets)")):
        p = sub.add_parser(name, help=hlp)
        p.add_argument("--symbol", required=True)
        p.add_argument("--units", help="signed units you hold (default: trader/portfolio.json); negative = short")
        p.add_argument("--orders", default="trader/orders.json", help="where the ticket is written")
        p.add_argument("--portfolio", default="trader/portfolio.json")
        p.add_argument("--plan", default="trader/plan.json")
        if name == "protect":
            p.add_argument("--stop", help="the stop price (default: the plan's)")
        clock(p)
    p = sub.add_parser("log", help="today's decisions")
    p.add_argument("--state", default="trader/state/broker.json")
    p.add_argument("--all", action="store_true")
    clock(p)
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        return {"show": cmd_show, "approve": cmd_approve, "decline": cmd_decline, "result": cmd_result,
                "fill": cmd_fill, "flatten": cmd_flatten, "protect": cmd_protect, "log": cmd_log}[a.cmd](a)
    except tc.TraderError as e:
        print("ticket.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
