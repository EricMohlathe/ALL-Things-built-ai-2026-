#!/usr/bin/env python3
"""Position sizing for trader-budget: forex lots, CFD lots, futures contracts and
coins, long or short. Standard library only, no network.

Sizes ONE trade from trader/plan.json (trader-exit) to your account and your max
loss, converts every amount into your account currency, checks leverage and
margin, and writes one bracket order (entry, stop-loss, take-profit) to
trader/orders.json. It never places anything: trader-risk checks the order and
trader-broker asks you yes or no.

    python3 size.py                                  # trader/plan.json + trader/config.json
    python3 size.py --write                          # write trader/orders.json
    python3 size.py --limit                          # a limit order at the plan's entry
    python3 size.py --balance 10000 --rate USDJPY=154.2
    python3 size.py --now "2026-11-16 08:45 London" --json

How much. In units of the instrument (euros of EURUSD, ounces of XAUUSD, coins
of BTCUSD, $50-a-point multiples of ES), then rounded DOWN to the lot step
(0.01 lot, 1 contract, 0.0001 BTC). The smallest of:

  max loss      max_loss_per_trade / (risk per unit x quote-to-account rate)
  leverage      equity x max_account_leverage - notional already open, / notional per unit
  margin        equity x max_margin_use_pct - margin in use, / margin per unit,
                where margin = notional / the instrument's leverage cap (ESMA
                retail: 30:1 major FX, 20:1 other FX, gold and major indices,
                10:1 other commodities and indices, 2:1 crypto; futures: about
                the exchange margin; the broker's and your config's caps lower it)
  notional cap  max_position_notional / notional per unit (if you set one)

Conversion: a quote currency that is not your account currency is converted
with trader/prices.json (alerts.py quote ... --rates writes the pairs), the
config's "rates", or --rate PAIR=RATE. USDJPY in a USD account uses its own
price. A missing rate is a plain refusal, never a guess.

The entry it sizes at: a limit order's limit price; for a market order the
plan's entry, or a fresh price (under 15 minutes old) if it is WORSE for you
(higher for a long, lower for a short), because a price that ran since the plan
means a bigger loss at the same stop. Zero units, a reward:risk under
min_reward_risk, or a plan for another day is a plain refusal: no order.
"""

import argparse
import json
import os
import sys
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "trader-core"))
import tradercore as tc  # noqa: E402

FRESH_MINUTES = 15
D = tc.D


class SizeError(tc.TraderError):
    pass


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def fmt_lots(lots, inst):
    """0.4 -> '0.40' on a 0.01 step, 3 -> '3' contracts, 0.0005 BTC."""
    places = max(0, -tc.D(repr(float(inst["lot_step"]))).normalize().as_tuple().exponent)
    return "%.*f" % (places, float(lots))


def fmt_units(units):
    s = "{:,.6f}".format(float(units)).rstrip("0").rstrip(".")
    return "%s unit%s" % (s, "" if float(units) == 1 else "s")


def units_word(inst, lots):
    n = float(lots)
    if inst["unit"] == "contract":
        return "%s contract%s" % (fmt_lots(lots, inst), "" if n == 1 else "s")
    if inst["unit"] == "coin":
        return "%s %s" % (fmt_lots(lots, inst), inst["base"])
    return "%s lot%s" % (fmt_lots(lots, inst), "" if n == 1 else "s")


def size_trade(plan, inst, cfg, state, rates, limit=None, price=None, today=None):
    """Pure: one plan + the account + your rules -> the sizing (a dict). lots may be 0."""
    if not isinstance(plan, dict):
        raise SizeError("the plan is not a JSON object")
    side = tc.side_word(plan.get("side") or "buy")
    long = side == "buy"
    acct = cfg["account_currency"]
    if today and plan.get("date") and str(plan["date"]) != today:
        raise SizeError("the plan is for %s and today is %s in the %s's zone: make a new plan with trader-exit"
                        % (plan["date"], today, plan.get("session") or "session"))
    entry_plan, stop, target = _f(plan.get("entry")), _f(plan.get("stop")), _f(plan.get("target"))
    for name, v in (("entry", entry_plan), ("stop", stop), ("target", target)):
        if v is None or v <= 0:
            raise SizeError("the plan needs a positive %s (run trader-exit): a bracket needs entry, stop and target"
                            % name)
    if inst["symbol"] in {str(b).upper() for b in cfg.get("blocked") or []}:
        raise SizeError("%s is on your blocked list" % inst["symbol"])
    tick = D(inst["tick"])
    if limit is not None:
        ref, ref_from = tc.to_tick(limit, tick), "limit"
    elif price is not None and ((long and price > entry_plan) or (not long and price < entry_plan)):
        ref, ref_from = tc.to_tick(price, tick), "price"
    else:
        ref, ref_from = tc.to_tick(entry_plan, tick), "plan"
    stop_d, target_d = tc.to_tick(stop, tick), tc.to_tick(target, tick)
    sgn = 1 if long else -1
    if (stop_d - ref) * sgn >= 0:
        raise SizeError("the stop %s is not %s the entry %s" % (tc.fmt_price(stop_d, inst),
                                                                "below" if long else "above", tc.fmt_price(ref, inst)))
    if (target_d - ref) * sgn <= 0:
        raise SizeError("the target %s is not %s the entry %s: the move has already happened. Skip it or make a "
                        "new plan with trader-exit" % (tc.fmt_price(target_d, inst), "above" if long else "below",
                                                       tc.fmt_price(ref, inst)))
    risk = (ref - stop_d) * sgn
    reward = (target_d - ref) * sgn
    conv = D(repr(tc.quote_to_account(inst, acct, rates, float(ref))))
    risk_unit_acct = risk * conv
    notional_unit = ref * conv
    lev = D(repr(tc.leverage_cap(inst, cfg)))
    margin_unit = notional_unit / lev
    equity = D(repr(state["equity"]))
    contract = D(repr(inst["contract"]))
    step = D(repr(inst["lot_step"]))

    limits = []

    def add(name, budget_acct, per_unit, how):
        if per_unit <= 0:
            return
        units = max(D(0), budget_acct / per_unit)
        lots = tc.floor_step(units / contract, step)
        limits.append({"name": name, "budget": float(budget_acct), "units_raw": float(units), "lots": lots,
                       "how": how})
    max_loss = _f(cfg.get("max_loss_per_trade"))
    if max_loss:
        add("max loss", D(repr(max_loss)), risk_unit_acct, "%s / %s risk a unit (%s%s)" % (
            tc.money(max_loss, acct), tc.money(float(risk_unit_acct), acct) if risk_unit_acct >= D("0.01") else
            "%s %s" % (tc.num(risk_unit_acct.quantize(Decimal("0.0000001"))), acct),
            tc.fmt_dist(risk, inst), (" at %s %s/%s" % (tc.num(conv.quantize(Decimal("0.000001"))), acct,
                                                       inst["quote"])) if inst["quote"] != acct else ""))
    lev_cap = _f(cfg.get("max_account_leverage"))
    if lev_cap:
        room = equity * D(repr(lev_cap)) - D(repr(state["notional"]))
        add("leverage", room, notional_unit, "%sx of %s equity%s" % (
            tc.num(D(repr(lev_cap))), tc.money(float(equity), acct),
            (" minus %s open" % tc.money(state["notional"], acct)) if state["notional"] else ""))
    mm = _f(cfg.get("max_margin_use_pct"))
    if mm:
        room = equity * D(repr(mm)) / 100 - D(repr(state["margin"]))
        add("margin", room, margin_unit, "%s%% of equity as margin at %s:1%s" % (
            tc.num(D(repr(mm))), tc.num(lev), (" minus %s in use" % tc.money(state["margin"], acct))
            if state["margin"] else ""))
    cap = _f(cfg.get("max_position_notional"))
    if cap:
        add("notional cap", D(repr(cap)), notional_unit, "%s max notional" % tc.money(cap, acct))
    if not limits:
        raise SizeError("no sizing limit at all: set max_loss_per_trade in trader/config.json")
    lots = min(l["lots"] for l in limits)
    lots = max(D(0), lots)
    bound = next(l["name"] for l in limits if l["lots"] == lots)
    for l in limits:
        l["binds"] = l["name"] == bound
        l["lots"] = float(l["lots"])
    refusal = None
    min_lot = D(repr(inst["min_lot"]))
    if lots < min_lot:
        if bound == "max loss":
            refusal = ("one %s (%s) risks %s at the stop, more than your %s max loss per trade. No order. Skip "
                       "this trade, or plan a closer stop with trader-exit." % (
                           units_word(inst, min_lot), fmt_units(min_lot * contract),
                           tc.money(float(min_lot * contract * risk_unit_acct), acct), tc.money(max_loss, acct)))
        else:
            refusal = ("the smallest size, %s, is over your %s limit (%s). No order." % (
                units_word(inst, min_lot), bound, next(l["how"] for l in limits if l["name"] == bound)))
        lots = D(0)
    units = lots * contract
    loss = units * risk_unit_acct
    rr = (reward / risk).quantize(Decimal("0.01"))
    mrr = _f(cfg.get("min_reward_risk"))
    if refusal is None and mrr and rr < D(repr(mrr)) - D("0.000001"):
        refusal = ("reward:risk %s (target %s, entry %s, stop %s) is under your minimum %s, so trader-risk would "
                   "block it. No order. Skip it, or make a new plan with trader-exit." % (
                       tc.num(rr), tc.fmt_price(target_d, inst), tc.fmt_price(ref, inst),
                       tc.fmt_price(stop_d, inst), tc.num(D(repr(mrr)))))
    if refusal is None and inst["kind"] == "future" and not cfg.get("allow_futures", True):
        refusal = "futures are off (\"allow_futures\": false). No order."
    notional = units * notional_unit
    margin = units * margin_unit
    return {
        "symbol": inst["symbol"], "class": inst["class"], "kind": inst["kind"], "side": side,
        "direction": tc.direction(side), "setup": plan.get("setup", ""), "date": plan.get("date"),
        "session": plan.get("session"), "tz": plan.get("tz"), "entry_time": plan.get("entry_time"),
        "entry_plan": entry_plan, "entry": float(ref), "entry_from": ref_from, "stop": float(stop_d),
        "target": float(target_d), "risk_per_unit": float(risk), "risk_pips": round(tc.pips(risk, inst), 2),
        "reward_pips": round(tc.pips(reward, inst), 2), "reward_risk": float(rr),
        "stop_label": plan.get("stop_label", ""), "target_label": plan.get("target_label", ""),
        "currency": acct, "conversion": float(conv), "equity": float(equity), "leverage_cap": float(lev),
        "limits": limits, "lots": float(lots), "units": float(units), "bound_by": bound,
        "max_loss": float(loss.quantize(Decimal("0.01"))), "notional": float(notional.quantize(Decimal("0.01"))),
        "margin": float(margin.quantize(Decimal("0.01"))),
        "account_leverage_after": float(((D(repr(state["notional"])) + notional) / equity).quantize(Decimal("0.01")))
        if equity > 0 else None,
        "flat_by": plan.get("flat_by"), "flat_by_utc": plan.get("flat_by_utc"),
        "order_type": "limit" if limit is not None else "market", "refusal": refusal,
        "max_loss_per_trade": max_loss,
    }


def bracket_order(s, inst, cfg):
    """The one proposed order, in the pack's broker-neutral shape. trader-broker turns it into
    the exact call for OANDA, Alpaca, MetaTrader 5, cTrader or IBKR."""
    if s["refusal"] or s["lots"] <= 0:
        return None
    prof = tc.broker_profile(cfg)
    o = {"symbol": s["symbol"], "class": s["class"], "kind": s["kind"], "side": s["side"], "type": s["order_type"],
         "time_in_force": "day" if inst["kind"] != "spot" or inst["class"] != "crypto" else "gtc",
         "lots": fmt_lots(s["lots"], inst), "units": tc.num(s["units"])}
    if s["order_type"] == "limit":
        o["limit_price"] = tc.fmt_price(s["entry"], inst)
    o["stop_loss"] = tc.fmt_price(s["stop"], inst)
    o["take_profit"] = tc.fmt_price(s["target"], inst)
    o["order_class"] = "bracket" if prof.get("bracket", True) else "simple"
    setup = {"range": "range breakout", "level": "level break"}.get(s["setup"], s["setup"] or "day trade")
    o["why"] = ("%s %s on %s: %s, bound by your %s (%s at the stop)" % (
        s["direction"], setup, s["symbol"], units_word(inst, s["lots"]), s["bound_by"],
        tc.money(s["max_loss"], s["currency"])))
    o["plan"] = {"entry": s["entry"], "stop": s["stop"], "target": s["target"], "risk_per_unit": s["risk_per_unit"],
                 "risk_pips": s["risk_pips"], "max_loss": s["max_loss"], "currency": s["currency"],
                 "conversion": s["conversion"], "notional": s["notional"], "margin": s["margin"],
                 "setup": s["setup"], "session": s["session"], "date": s["date"], "entry_time": s["entry_time"],
                 "flat_by": s["flat_by"], "flat_by_utc": s["flat_by_utc"], "tz": s["tz"]}
    return o


def plan_report(s, order, inst, notes=()):
    acct = s["currency"]
    p = lambda x: tc.fmt_price(x, inst)  # noqa: E731
    zl = tc.zone_label(s["tz"]) if s.get("tz") else ""
    lines = ["%s %s, %s, entry %s%s" % (s["symbol"], s["direction"], {"range": "range breakout"}.get(
        s["setup"], s["setup"] or "plan"), p(s["entry_plan"]), (" at %s %s" % (s["entry_time"], zl))
        if s["entry_time"] else "")]
    lines.append("Stop %s%s. Target %s%s." % (p(s["stop"]), (": " + s["stop_label"]) if s["stop_label"] else "",
                                             p(s["target"]), (": " + s["target_label"]) if s["target_label"] else ""))
    for n in notes:
        lines.append(n)
    src = {"plan": "the plan's entry", "price": "the latest price, worse than the plan's entry",
           "limit": "your limit price"}[s["entry_from"]]
    lines.append("Sized at %s (%s). Risk %s a unit. Reward:risk %.2f. Equity %s, %s:1 leverage cap on %s." % (
        p(s["entry"]), src, tc.fmt_dist(s["risk_per_unit"], inst), s["reward_risk"], tc.money(s["equity"], acct),
        tc.num(s["leverage_cap"]), s["symbol"]))
    lines.append("")
    lines.append("Limits (rounded down to the %s step; the smallest one wins):" % units_word(inst, inst["lot_step"]))
    for l in s["limits"]:
        lines.append("  %-13s %-66s %s%s" % (l["name"], l["how"][:66], units_word(inst, l["lots"]),
                                             "  <- binds" if l["binds"] else ""))
    lines.append("")
    if order is None:
        lines.append("No order: " + s["refusal"])
        lines.append(tc.NOTE_ADVICE)
        return "\n".join(lines)
    lines.append("Size: %s %s = %s, notional %s (%.2fx the account after this), margin about %s." % (
        units_word(inst, s["lots"]), s["symbol"], fmt_units(s["units"]),
        tc.money(s["notional"], acct), s["account_leverage_after"] or 0, tc.money(s["margin"], acct)))
    lines.append("Max loss at the stop: %s (%s x %s)." % (tc.money(s["max_loss"], acct), fmt_units(s["units"]),
                                                         tc.fmt_dist(s["risk_per_unit"], inst)))
    lines.append("A stop is an order, not a promise: a gap or a fast market can fill it past %s." % p(s["stop"]))
    lines.append("")
    lines.append("Proposed %s order (nothing has been placed):" % order["order_class"])
    how = "limit %s" % order["limit_price"] if order["type"] == "limit" else "market"
    lines.append("  %s %s %s, %s, %s, stop-loss %s, take-profit %s" % (
        order["side"], units_word(inst, s["lots"]), order["symbol"], how, order["time_in_force"],
        order["stop_loss"], order["take_profit"]))
    if order["order_class"] != "bracket":
        lines.append("  Your broker takes no bracket here: place the stop as its own order right after the fill, "
                     "and keep trader-alerts on the stop.")
    if s["flat_by"]:
        lines.append("Flat by %s %s: anything still open then gets closed (trader-alerts rings, ticket.py flatten)."
                     % (s["flat_by"], zl))
    lines.append("")
    lines.append("Next: trader-risk checks it, then trader-broker asks you yes or no.")
    lines.append(tc.NOTE_ADVICE)
    return "\n".join(lines)


def write_orders(path, orders, cfg, source="", now_utc=None):
    tc.write_json(path, {
        "created_by": "trader-budget", "created_at": tc.iso(now_utc or tc.utc_now()), "status": "proposed",
        "paper": bool(cfg.get("paper", True)), "broker": cfg.get("broker", "paper"),
        "note": "Proposals only. Nothing is placed until trader-risk passes each order and you say yes to it in the chat.",
        "source": source, "orders": orders})


def run(a):
    cfg = tc.load_config(a.config)
    if a.balance is not None:
        cfg["balance"] = a.balance
    plan = tc.read_json(a.plan, "plan (run trader-exit first)")
    inst = tc.resolve(plan.get("symbol"), cfg)
    tz = plan.get("tz") or tc.session_def(plan.get("session") or inst["session"], cfg)["tz"]
    now = tc.parse_now(a.now, tz)
    today = tc.to_local(tz, now).date().isoformat()
    pdoc = tc.read_json(a.prices, "prices", required=False) if a.prices else None
    prices, times = tc.load_prices(pdoc)
    rates = tc.rates_from(pdoc, cfg, tc.parse_rates(a.rate))
    portfolio = tc.read_json(a.portfolio, "portfolio", required=False) if a.portfolio and a.balance is None else None
    state = tc.account_state(cfg, portfolio, rates, prices)
    limit = None
    if a.limit is not None:
        limit = _f(plan.get("entry")) if a.limit == "plan" else _f(a.limit)
        if limit is None or limit <= 0:
            raise SizeError("--limit wants a price, like --limit 1.16280")
    notes, price = [], None
    if limit is None and inst["symbol"] in prices:
        if tc.fresh(times, inst["symbol"], now, FRESH_MINUTES):
            price = prices[inst["symbol"]]
            long = tc.side_word(plan.get("side")) == "buy"
            if (long and price > float(plan["entry"])) or (not long and price < float(plan["entry"])):
                notes.append("%s last %s is past the plan's entry %s, so the risk is bigger: sized at %s." % (
                    inst["symbol"], tc.fmt_price(price, inst), tc.fmt_price(plan["entry"], inst),
                    tc.fmt_price(price, inst)))
        else:
            notes.append("%s in %s is older than %d minutes: not used. Sized at the plan's entry." % (
                inst["symbol"], a.prices, FRESH_MINUTES))
    for w in state["warnings"]:
        notes.append("Note: " + w + ".")
    s = size_trade(plan, inst, cfg, state, rates, limit, price, today)
    order = bracket_order(s, inst, cfg)
    if order and a.write:
        write_orders(a.write, [order], cfg, "trader/plan.json (%s %s %s)" % (s["symbol"], s["setup"] or "plan",
                                                                             s["date"] or today), now)
    if a.json:
        print(json.dumps({"sizing": dict(s, limits=s["limits"]), "orders": [order] if order else [], "notes": notes},
                         indent=2, default=float))
    else:
        print(plan_report(s, order, inst, notes))
        if order and a.write:
            print("Wrote 1 proposed order to %s" % a.write)
    return 0 if order else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Size a trade to your account and max loss (trader-budget).")
    ap.add_argument("--plan", default="trader/plan.json")
    ap.add_argument("--config", default="trader/config.json")
    ap.add_argument("--balance", type=float, help="size against this balance instead of trader/portfolio.json")
    ap.add_argument("--limit", nargs="?", const="plan", metavar="PRICE",
                    help="a limit order instead of market, at the plan's entry or at PRICE")
    ap.add_argument("--prices", default="trader/prices.json", help="prices and conversion rates (alerts.py quote)")
    ap.add_argument("--rate", action="append", metavar="PAIR=RATE", help="a conversion rate, e.g. USDJPY=154.2")
    ap.add_argument("--portfolio", default="trader/portfolio.json")
    ap.add_argument("--now", help='pretend it is this time, e.g. "2026-11-16 08:45 London"')
    ap.add_argument("--write", nargs="?", const="trader/orders.json", metavar="PATH")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        return run(a)
    except tc.TraderError as e:
        print("size.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
