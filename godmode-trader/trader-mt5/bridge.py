#!/usr/bin/env python3
"""The MetaTrader 5 bridge for trader-mt5: read the terminal, pull its history into the
trader-data cache, and send ONE order that trader-risk passed and you approved today.
Needs Windows, a running MetaTrader 5 terminal and `pip install MetaTrader5`; everything
else in the pack runs without it.

    python3 bridge.py status                              # terminal, account, positions, pending orders
    python3 bridge.py symbols --match XAU                 # broker names, contract sizes, steps -> config overrides
    python3 bridge.py export EURUSD --tf M15 --from 2024-01-01    # the broker's own bars -> trader/data
    python3 bridge.py ticks EURUSD --from 2026-11-16 --hours 2    # ticks -> M1 with tick-rule delta and spread
    python3 bridge.py send --index 1                      # dry run: the exact request and order_check's answer
    python3 bridge.py send --index 1 --live               # sends it, only if every gate below is open

The gates for `send --live`, all of them, every time:
  1. "broker": "mt5" in trader/config.json;
  2. trader-risk PASSED this exact order today (same fingerprint in trader/state/risk.json);
  3. you approved this exact order today in the chat (trader/state/broker.json, via ticket.py approve),
     and it has not been sent, declined or reported since;
  4. "paper": false in the config, OR the terminal is logged in to a DEMO account;
  5. MetaTrader's own order_check accepts the request.
Anything else stops it and says which gate. The result (or the failure) is written back to
trader/state/broker.json, so a second `send` of the same order is refused.

Bar times from MetaTrader are the broker's server time; --server-tz (default MT5, i.e.
UTC+2 / +3 with New York's DST dates) converts them to UTC for the cache.
"""

import argparse
import datetime
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "trader-core"))
import tradercore as tc  # noqa: E402
import history as hist  # noqa: E402
import orderflow as of  # noqa: E402
from bars import Bars, TF_NAME, tf_seconds  # noqa: E402

TF_CONST = {60: "TIMEFRAME_M1", 300: "TIMEFRAME_M5", 900: "TIMEFRAME_M15", 1800: "TIMEFRAME_M30",
            3600: "TIMEFRAME_H1", 14400: "TIMEFRAME_H4", 86400: "TIMEFRAME_D1"}


class BridgeError(tc.TraderError):
    pass


def mt5_module():
    try:
        import MetaTrader5 as mt5  # noqa: N813
    except ImportError:
        raise BridgeError("the MetaTrader5 package is not installed: on Windows with MT5 running, "
                          "pip install MetaTrader5")
    return mt5


def connect(mt5, cfg):
    kw = {}
    prof = cfg.get("mt5") or {}
    if prof.get("path"):
        kw["path"] = prof["path"]
    if not mt5.initialize(**kw):
        raise BridgeError("MetaTrader 5 did not start or answer: %s" % (mt5.last_error(),))
    return mt5


def ticket_module():
    spec = importlib.util.spec_from_file_location("trader_broker_ticket_for_mt5",
                                                  os.path.join(HERE, "..", "trader-broker", "ticket.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def mask(login):
    s = str(login or "")
    return ("*" * max(0, len(s) - 3)) + s[-3:]


def server_to_utc(t, zone, cache):
    """Broker server seconds (wall clock written as if UTC) -> unix seconds UTC."""
    day = t // 86400
    if day not in cache:
        noon = datetime.datetime(1970, 1, 1) + datetime.timedelta(days=day, hours=12)
        cache[day] = tc.offset_minutes(zone, noon - datetime.timedelta(hours=2)) * 60
    return int(t - cache[day])


def field(r, name, default=0.0):
    try:
        return r[name]
    except (KeyError, IndexError, ValueError, TypeError):
        return getattr(r, name, default)


# ---------------------------------------------------------------- commands

def cmd_status(a, cfg):
    mt5 = connect(mt5_module(), cfg)
    try:
        ti, ac = mt5.terminal_info(), mt5.account_info()
        pos = mt5.positions_get() or ()
        ords = mt5.orders_get() or ()
        doc = {"terminal": {"company": getattr(ti, "company", None), "connected": getattr(ti, "connected", None),
                            "trade_allowed": getattr(ti, "trade_allowed", None)},
               "account": {"login": mask(getattr(ac, "login", "")), "server": getattr(ac, "server", None),
                           "demo": getattr(ac, "trade_mode", None) == getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0),
                           "currency": getattr(ac, "currency", None), "balance": getattr(ac, "balance", None),
                           "equity": getattr(ac, "equity", None), "margin": getattr(ac, "margin", None),
                           "margin_free": getattr(ac, "margin_free", None), "leverage": getattr(ac, "leverage", None)},
               "positions": [{"ticket": p.ticket, "symbol": p.symbol, "side": "buy" if p.type == 0 else "sell",
                              "volume": p.volume, "price_open": p.price_open, "sl": p.sl, "tp": p.tp,
                              "profit": p.profit} for p in pos],
               "orders": [{"ticket": o.ticket, "symbol": o.symbol, "type": o.type, "volume": o.volume_current,
                           "price": o.price_open, "sl": o.sl, "tp": o.tp} for o in ords]}
    finally:
        mt5.shutdown()
    if a.json:
        print(json.dumps(doc, indent=2))
        return 0
    t, ac = doc["terminal"], doc["account"]
    print("MetaTrader 5 (%s), %s, trading %s. Account %s on %s, %s." % (
        t["company"], "connected" if t["connected"] else "NOT connected", "allowed" if t["trade_allowed"] else "OFF",
        ac["login"], ac["server"], "DEMO" if ac["demo"] else "REAL MONEY"))
    print("  balance %s, equity %s, margin %s, free %s, leverage 1:%s" % (
        ac["balance"], ac["equity"], ac["margin"], ac["margin_free"], ac["leverage"]))
    for p in doc["positions"]:
        print("  position #%s %s %s %s at %s, SL %s TP %s, P/L %s" % (p["ticket"], p["side"], p["volume"], p["symbol"],
                                                                     p["price_open"], p["sl"], p["tp"], p["profit"]))
    for o in doc["orders"]:
        print("  pending #%s %s %s at %s" % (o["ticket"], o["symbol"], o["volume"], o["price"]))
    if not doc["positions"] and not doc["orders"]:
        print("  no open positions or pending orders")
    return 0


def cmd_symbols(a, cfg):
    mt5 = connect(mt5_module(), cfg)
    try:
        syms = mt5.symbols_get() or ()
        rows = []
        for s in syms:
            if a.match and a.match.upper() not in s.name.upper():
                continue
            rows.append({"name": s.name, "digits": s.digits, "point": s.point, "contract": s.trade_contract_size,
                         "volume_min": s.volume_min, "volume_step": s.volume_step, "spread_points": s.spread,
                         "currency_profit": s.currency_profit})
    finally:
        mt5.shutdown()
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    for r in rows[:200]:
        print("  %-14s digits %d, contract %s, lots %s step %s, spread %s points, profit in %s" % (
            r["name"], r["digits"], r["contract"], r["volume_min"], r["volume_step"], r["spread_points"],
            r["currency_profit"]))
    print("Where a name or contract differs from the pack's registry, set it under \"instruments\" in "
          "trader/config.json, e.g. {\"XAUUSD\": {\"broker_symbol\": \"XAUUSD.m\", \"contract\": 100}}.")
    return 0


def _range(a):
    d0 = datetime.datetime.combine(datetime.date.fromisoformat(a.frm), datetime.time())
    d1 = datetime.datetime.combine(datetime.date.fromisoformat(a.to), datetime.time()) + datetime.timedelta(days=1) \
        if a.to else d0 + datetime.timedelta(hours=a.hours) if getattr(a, "hours", None) else tc.utc_now()
    return d0, d1


def broker_name(inst, cfg):
    return ((cfg.get("instruments") or {}).get(inst["symbol"]) or {}).get("broker_symbol") or \
        inst.get("broker_symbol") or (inst["symbol"] + (cfg.get("symbol_suffix") or ""))


def cmd_export(a, cfg):
    inst = tc.resolve(a.symbol, cfg)
    step = tf_seconds(a.tf)
    if step not in TF_CONST:
        raise BridgeError("--tf is one of %s" % ", ".join(TF_NAME[s] for s in sorted(TF_CONST)))
    d0, d1 = _range(a)
    mt5 = connect(mt5_module(), cfg)
    try:
        rates = mt5.copy_rates_range(broker_name(inst, cfg), getattr(mt5, TF_CONST[step]), d0, d1)
    finally:
        mt5.shutdown()
    if rates is None or not len(rates):
        raise BridgeError("MetaTrader sent no %s bars for %s in that range" % (TF_NAME[step], broker_name(inst, cfg)))
    zone, cache, out = tc.zone_name(a.server_tz), {}, Bars(step, inst["symbol"])
    for r in rates:
        vol = field(r, "real_volume") or field(r, "tick_volume")
        out.append(server_to_utc(int(field(r, "time")), zone, cache), float(field(r, "open")), float(field(r, "high")),
                   float(field(r, "low")), float(field(r, "close")), float(vol or 0))
    merged = hist.save(out, a.data)
    print("%s %s from MetaTrader (%s, times %s -> UTC): %s bars; the cache now holds %s (%s)." % (
        inst["symbol"], TF_NAME[step], broker_name(inst, cfg), zone, "{:,}".format(len(out)), "{:,}".format(len(merged)),
        hist.cache_path(inst["symbol"], step, a.data)))
    return 0


def cmd_ticks(a, cfg):
    inst = tc.resolve(a.symbol, cfg)
    d0, d1 = _range(a)
    mt5 = connect(mt5_module(), cfg)
    try:
        ticks = mt5.copy_ticks_range(broker_name(inst, cfg), d0, d1, getattr(mt5, "COPY_TICKS_ALL", -1))
    finally:
        mt5.shutdown()
    if ticks is None or not len(ticks):
        raise BridgeError("MetaTrader sent no ticks for %s in that range" % broker_name(inst, cfg))
    zone, cache = tc.zone_name(a.server_tz), {}
    rows = []
    for t in ticks:
        ms = int(field(t, "time_msc") or int(field(t, "time")) * 1000)
        utc_ms = server_to_utc(ms // 1000, zone, cache) * 1000 + ms % 1000
        rows.append((utc_ms, float(field(t, "ask")), float(field(t, "bid")), 1.0, 1.0))
    bars = of.tick_rule_bars(rows, 60)
    out = Bars(60, inst["symbol"])
    for k in sorted(bars):
        o, h, l, c, cnt, delta, _spread = bars[k]
        out.append(k, o, h, l, c, cnt, delta)
    merged = hist.save(out, a.data)
    spreads = [bars[k][6] for k in bars]
    print("%s: %s ticks -> %d M1 bars with tick-rule delta; average spread %s; cache %s bars." % (
        inst["symbol"], "{:,}".format(len(rows)), len(out), tc.fmt_price(sum(spreads) / len(spreads), inst),
        "{:,}".format(len(merged))))
    return 0


def gate(a, cfg, tk):
    """(order, inst, request dict) after gates 1-3, or raise with the gate that failed."""
    if tc.broker_profile(cfg)["name"] != "mt5":
        raise BridgeError("gate 1: trader/config.json says \"broker\": \"%s\", not \"mt5\"" % tc.broker_profile(cfg)["name"])
    doc = tc.read_json(a.orders, "orders (run trader-budget first)")
    orders = doc.get("orders", doc) if isinstance(doc, dict) else doc
    if not 1 <= a.index <= len(orders):
        raise BridgeError("there is no order %d" % a.index)
    order = orders[a.index - 1]
    today = a.today or tc.to_local(cfg["timezone"], tc.parse_now(a.now, cfg["timezone"])).date().isoformat()
    fp = tk.fingerprint(order)
    rv, why = tk.risk_verdict(tc.read_json(a.risk, "risk check", required=False), fp, today)
    if rv is None or rv.get("verdict") != "PASS":
        raise BridgeError("gate 2: %s" % (why or "trader-risk BLOCKED it: " + "; ".join(rv.get("reasons", []))))
    rec = tk.latest(tk.load_state(a.state), fp, today)
    if not rec or rec.get("status") != "approved":
        raise BridgeError("gate 3: no yes recorded today for order %d%s (ticket.py approve --index %d --reply ...)" % (
            a.index, "; its last status is %s" % rec["status"] if rec else "", a.index))
    inst = tc.resolve(order["symbol"], cfg)
    call = tk.tool_call(order, inst, cfg)
    return order, inst, call["input"], fp, today


def to_native(mt5, req, tick, info):
    out = dict(req)
    for k in ("action", "type", "type_time", "type_filling"):
        out[k] = getattr(mt5, out[k])
    if out["action"] == getattr(mt5, "TRADE_ACTION_DEAL"):
        out["price"] = tick.ask if req["type"].startswith("ORDER_TYPE_BUY") else tick.bid
    modes = getattr(info, "filling_mode", 0) or 0
    if modes and not modes & 2:                                   # IOC not offered: FOK (1) or RETURN
        out["type_filling"] = getattr(mt5, "ORDER_FILLING_FOK") if modes & 1 else getattr(mt5, "ORDER_FILLING_RETURN")
    for k in ("sl", "tp", "price", "volume"):
        if out.get(k) is not None:
            out[k] = float(out[k])
    return out


def record(a, cfg, fp, today, order, status, extra):
    state = tc.read_json(a.state, "broker state", required=False) or {"orders": []}
    rec = {"at": tc.iso(tc.utc_now()), "date": today, "index": a.index, "fingerprint": fp, "symbol": order["symbol"],
           "side": order.get("side"), "status": status, "via": "trader-mt5 bridge"}
    rec.update(extra)
    state.setdefault("orders", []).append(rec)
    tc.write_json(a.state, state)


def cmd_send(a, cfg):
    tk = ticket_module()
    order, inst, req, fp, today = gate(a, cfg, tk)
    mt5 = connect(mt5_module(), cfg)
    try:
        ac = mt5.account_info()
        demo = getattr(ac, "trade_mode", None) == getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
        sym = req["symbol"]
        if not mt5.symbol_select(sym, True):
            raise BridgeError("MetaTrader does not know %s: set broker_symbol in the config" % sym)
        native = to_native(mt5, req, mt5.symbol_info_tick(sym), mt5.symbol_info(sym))
        chk = mt5.order_check(native)
        ok_check = chk is not None and getattr(chk, "retcode", 1) == 0
        print("Order %d, %s: %s" % (a.index, "DEMO account" if demo else "REAL-MONEY account", json.dumps(req)))
        print("order_check: %s" % ("accepted" if ok_check else "REFUSED (%s %s)" % (
            getattr(chk, "retcode", None), getattr(chk, "comment", mt5.last_error()))))
        if not a.live:
            print("Dry run: nothing sent. Add --live to send it once every gate is open.")
            return 0 if ok_check else 1
        if cfg.get("paper", True) and not demo:
            raise BridgeError("gate 4: \"paper\" is true in the config and this is a real-money account: nothing sent")
        if not ok_check:
            record(a, cfg, fp, today, order, "failed", {"note": "order_check refused: %s" % getattr(chk, "comment", "")})
            raise BridgeError("gate 5: MetaTrader's order_check refused it; nothing sent")
        res = mt5.order_send(native)
        done = res is not None and getattr(res, "retcode", None) == getattr(mt5, "TRADE_RETCODE_DONE", 10009)
        extra = {"broker_order_id": getattr(res, "order", None), "retcode": getattr(res, "retcode", None),
                 "price": getattr(res, "price", None), "note": getattr(res, "comment", "")}
        record(a, cfg, fp, today, order, "placed" if done else "failed", extra)
    finally:
        mt5.shutdown()
    if done:
        print("SENT: MetaTrader order #%s, %s at %s. Recorded in %s. Set the alerts: alerts.py add --from-plan" % (
            extra["broker_order_id"], req["symbol"], extra["price"], a.state))
        return 0
    print("NOT FILLED: retcode %s (%s). Recorded as failed; do not resend without a new risk check and a new yes."
          % (extra["retcode"], extra["note"]))
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="MetaTrader 5 bridge (trader-mt5).")
    ap.add_argument("--config", default="trader/config.json")
    ap.add_argument("--data", default=hist.CACHE)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--server-tz", dest="server_tz", default="MT5",
                    help="the broker server's zone for bar times (default MT5: UTC+2 / +3 on New York's DST dates)")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("status")
    p = sub.add_parser("symbols")
    p.add_argument("--match")
    p = sub.add_parser("export")
    p.add_argument("symbol")
    p.add_argument("--tf", default="M1")
    p.add_argument("--from", dest="frm", required=True)
    p.add_argument("--to")
    p = sub.add_parser("ticks")
    p.add_argument("symbol")
    p.add_argument("--from", dest="frm", required=True)
    p.add_argument("--to")
    p.add_argument("--hours", type=float, default=1.0)
    p = sub.add_parser("send")
    p.add_argument("--index", type=int, required=True)
    p.add_argument("--live", action="store_true", help="actually send (default: a dry run with order_check)")
    p.add_argument("--orders", default="trader/orders.json")
    p.add_argument("--risk", default="trader/state/risk.json")
    p.add_argument("--state", default="trader/state/broker.json")
    p.add_argument("--now")
    p.add_argument("--today")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        cfg = tc.load_config(a.config)
        return {"status": cmd_status, "symbols": cmd_symbols, "export": cmd_export, "ticks": cmd_ticks,
                "send": cmd_send}[a.cmd](a, cfg)
    except (tc.TraderError, ValueError) as e:
        print("bridge.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
