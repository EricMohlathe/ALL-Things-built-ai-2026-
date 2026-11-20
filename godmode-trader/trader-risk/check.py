#!/usr/bin/env python3
"""Pre-trade risk check for trader-risk: forex, commodities, indices and crypto,
long and short. Standard library only, no network.

Reads the proposed orders (trader/orders.json) and checks every one against
your rules (trader/config.json), your account (trader/portfolio.json), prices
and conversion rates (trader/prices.json), the economic calendar
(trader/calendar.json) and what was placed today (trader/state/broker.json).
Each order gets PASS or BLOCK with the reasons. Orders are checked in file
order as if each PASS had filled, so trades that are fine one by one but break
a limit together (two USD shorts, say) are caught.

    python3 check.py                                 # writes trader/state/risk.json
    python3 check.py --now "2026-11-16 08:45 London"
    python3 check.py --orders trader/orders.json --json --no-write

Entries and exits. An ENTRY opens or adds to a position, long or short. An
EXIT only reduces what you hold. Getting out must always be possible: an exit
is checked for format and asset only; every other rule turns into a warning.

What blocks any order:
  format      unknown symbol; side; lots and units that disagree with the
              contract size; a size off the lot step or under the minimum; an
              unknown type or time in force; a limit without a price; a
              bracket without both legs
  asset       a class outside "allowed_classes"; futures with
              "allow_futures": false; a class or kind your broker does not
              carry (Alpaca: crypto spot only; OANDA: no futures, no crypto)
  short       a sell that opens a short when "allow_short" is false or the
              broker cannot short it (crypto spot)

What blocks an entry (on top):
  blocked     a symbol on your "blocked" list
  stop        no stop while "require_stop" is true; a stop on the wrong side
  loss        units x |entry - stop| x the quote-to-account rate over
              max_loss_per_trade. The entry is the limit price, else the WORSE
              of the plan's entry and a fresh price (under 15 minutes old)
  reward:risk under min_reward_risk
  daily loss  the max losses at the stops of today's entries plus this one
              over max_daily_loss (each counts in full, win or lose)
  trades      max_trades_per_day entries already placed today
  daily limit max_orders_per_day orders placed today
  duplicate   the same symbol and side twice in this batch or already today
  leverage    total notional after the order over max_account_leverage x equity
  margin      margin in use after the order over max_margin_use_pct of equity,
              margin = notional / the instrument's leverage cap
  exposure    the net exposure to any one currency or asset (EUR, JPY, XAU,
              BTC ...; your account currency is home and left out) over
              max_currency_exposure_x x equity
  streak      max_consecutive_losses losing results in a row today in your journal
              (trader/journal.csv): stop for the day and review
  prop firm   with a challenge tracked (trader/propfirm.json): no room left today, or a
              loss at the stop (alone, or with the batch so far) over the guardian's
              largest safe risk
  window      outside the session's entry window (after the opening range, until
              entry_cutoff_minutes before the close), or the session is closed
              (weekend, holiday, the FX week's Sunday-to-Friday hours)
  news        a calendar event of "news_blackout_impact" (High) for a currency
              the instrument moves on, within news_blackout_minutes (30) of now

Exit code 0 when every order passes, 1 when any order is blocked. The verdicts go
to trader/state/risk.json with a fingerprint of each order, so trader-broker only
shows an order as ready if THIS exact order passed today.
"""

import argparse
import csv
import datetime
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
PRICE_FIELDS = ("lots", "units", "limit_price", "stop_price", "stop_loss", "take_profit")
TYPES = {"market", "limit", "stop"}
TIFS = {"day", "gtc", "ioc", "fok", "gtd"}
FRESH_MINUTES = 15
EPS = 1e-9
REF_WORDS = {"plan": "the plan's entry", "price": "the latest price", "limit": "the limit price",
             "stop price": "the stop price", "stale price": "an old price"}


class RiskError(tc.TraderError):
    pass


def fingerprint(order):
    """Same function in trader-broker/ticket.py: the exact order that was checked."""
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


def rec_is_entry(rec):
    k = rec.get("kind")
    return k == "entry" if k else True


def placed_today(state, today):
    return [r for r in (state or {}).get("orders", []) if r.get("status") == "placed" and rec_day(r) == today]


def window_check(inst, sname, now_utc, cfg):
    """(reasons, warnings, label) for a new entry right now in the session."""
    sinst, phase = tc.locate(sname, now_utc, cfg)
    if sinst is None:
        return ["window: the %s does not trade today (%s)" % (tc.SESSIONS[sname]["label"], phase)], [], None
    tz = sinst["tz"]
    stamp = tc.stamp(now_utc, tz)
    warns = []
    if not sinst["calendar_known"]:
        warns.append("the %s holiday calendar is not modeled for %s: check the exchange"
                     % (tc.CALENDAR_LABEL.get(sinst["calendar"], sinst["calendar"]), sinst["date"]))
    if phase != "open":
        return ["window: the %s is %s (%s; it trades %s to %s)" % (
            sinst["label"], "not open yet" if phase == "pre-open" else "closed for today", stamp,
            tc.hm(sinst["open_local"]), tc.hm(sinst["close_local"]))], warns, None
    win = tc.windows(sinst, cfg)
    if sinst["early"]:
        warns.append("early close today (%s): no new entries after %s" % (sinst["early"],
                                                                         tc.hm(win["no_entries_after_local"])))
    if now_utc < win["no_entries_before"]:
        return ["window: no new entries before %s %s, the end of the opening range (it is %s)" % (
            tc.hm(win["no_entries_before_local"]), tc.zone_label(tz), stamp)], warns, None
    if now_utc > win["no_entries_after"]:
        return ["window: no new entries after %s %s (it is %s)" % (
            tc.hm(win["no_entries_after_local"]), tc.zone_label(tz), stamp)], warns, None
    if inst["class"] in ("forex", "commodity", "index") and tc.to_local(tz, now_utc).weekday() == 4:
        warns.append("Friday: be flat before the weekend close, or a Monday gap can jump the stop")
    return [], warns, "%s, %s to %s %s" % (sinst["label"], tc.hm(win["no_entries_before_local"]),
                                           tc.hm(win["no_entries_after_local"]), tc.zone_label(tz))


def news_check(inst, now_utc, calendar, cfg):
    """(reasons, warnings) from trader/calendar.json for this instrument's currencies."""
    minutes = int(cfg.get("news_blackout_minutes") or 0)
    if not minutes:
        return [], []
    if not calendar:
        return [], ["no economic calendar loaded (run /trader-calendar: calendar.py week --write), so the news "
                    "blackout was not checked"]
    impacts = {str(x).lower() for x in cfg.get("news_blackout_impact") or ["High"]}
    curs = {str(c).upper() for c in inst.get("currencies") or []}
    reasons, warns = [], []
    span = [tc.parse_utc(calendar.get("from")), tc.parse_utc(calendar.get("to"))]
    if span[0] and span[1] and not (span[0] <= now_utc <= span[1]):
        warns.append("trader/calendar.json covers %s to %s, not now: fetch this week's" % (
            calendar.get("from", "")[:10], calendar.get("to", "")[:10]))
    for ev in calendar.get("events") or []:
        t = tc.parse_utc(ev.get("time_utc"))
        if t is None or str(ev.get("currency", "")).upper() not in curs:
            continue
        if str(ev.get("impact", "")).lower() not in impacts:
            continue
        gap = (t - now_utc).total_seconds() / 60.0
        if abs(gap) <= minutes:
            reasons.append("news: %s %s at %s (%s), %d minutes %s; no entries %d minutes either side of a %s "
                           "event" % (ev.get("currency"), ev.get("title"),
                                      "%s %s" % (tc.hm(tc.to_local(cfg.get("timezone") or "UTC", t)),
                                                 tc.zone_label(cfg.get("timezone") or "UTC")),
                                      ev.get("impact"), abs(int(round(gap))), "from now" if gap >= 0 else "ago",
                                      minutes, "/".join(sorted(i.title() for i in impacts))))
        elif 0 < gap <= minutes * 4:
            warns.append("%s %s (%s) in %d minutes" % (ev.get("currency"), ev.get("title"), ev.get("impact"),
                                                       int(round(gap))))
    return reasons, warns


def losing_streak(journal_rows, today, zone):
    """Losing results in a row at the end of today's observed PAPER / LIVE journal outcomes."""
    done = [r for r in journal_rows or [] if r.get("R") not in (None, "") and r.get("Observed at")
            and r.get("Decision") in ("PAPER", "LIVE")]
    done = [r for r in done if tc.to_local(zone, tc.parse_utc(r["Observed at"])).date().isoformat() == today]
    done.sort(key=lambda r: r["Observed at"])
    n = 0
    for r in reversed(done):
        if float(r["R"]) <= 0:
            n += 1
        else:
            break
    return n


def prop_guard(path, cfg):
    """The prop-firm guardian for today, or None when no challenge is tracked."""
    st = tc.read_json(path, "prop-firm state", required=False)
    if not st:
        return None
    import prop
    rl = prop.rules(dict(cfg.get("prop_firm") or {}, preset=st.get("preset", "ftmo_2step")))
    days = st.get("days") or {}
    start = (days.get(st.get("today")) or {}).get("start", st["balance"])
    g = prop.guardian(rl, st["size"], st["balance"], st.get("equity", st["balance"]), start, st.get("peak"),
                      st.get("phase", 1), sum(1 for d in days.values() if d.get("traded")))
    g["label"] = rl["label"]
    return g


def check(orders, cfg, portfolio=None, prices=None, price_times=None, rates=None, state=None, calendar=None,
          now=None, today=None, journal=None, prop=None):
    """Pure function. {"results": [...], "pass": n, "block": n, "warnings": [...]}."""
    c = dict(tc.DEFAULTS)
    c.update(cfg or {})
    c["account_currency"] = str(c.get("account_currency") or "USD").upper()
    acct = c["account_currency"]
    now_utc = now or tc.utc_now()
    prices = {str(k).upper(): float(v) for k, v in (prices or {}).items() if _f(v)}
    rates = dict(rates or {})
    reg = tc.registry(c)
    st = tc.account_state(c, portfolio, rates, prices, reg)
    top_warn = list(st["warnings"])
    prof = tc.broker_profile(c)
    today = today or tc.to_local(c["timezone"], now_utc).date().isoformat()
    blocked = {str(b).upper() for b in c.get("blocked") or []}
    allowed = set(c.get("allowed_classes") or tc.CLASSES)
    done_today = placed_today(state, today)
    entries_today = [r for r in done_today if rec_is_entry(r)]
    loss_today = 0.0
    for r in entries_today:
        ml = _f(r.get("max_loss"))
        if ml is None:
            top_warn.append("an entry placed today (%s %s) has no max loss in the log; not counted in the daily loss"
                            % (r.get("side"), r.get("symbol")))
        else:
            loss_today += ml
    placed_keys = {(str(r.get("symbol", "")).upper(), r.get("side")) for r in done_today}
    if not c.get("paper", True):
        top_warn.append("LIVE account (\"paper\": false): these orders use real money")
    equity = st["equity"]
    seen, results = set(), []
    batch_entries, batch_loss = 0, 0.0
    streak_cap = int(c.get("max_consecutive_losses") or 0)
    streak = losing_streak(journal, today, c["timezone"]) if journal else 0

    for i, o in enumerate(orders, 1):
        reasons, warns, info, later = [], [], [], []
        raw_sym = str(o.get("symbol", "")).strip()
        side = str(o.get("side", "")).strip().lower()
        typ = str(o.get("type", "market")).strip().lower()
        tif = str(o.get("time_in_force", "day")).strip().lower()
        plan = o.get("plan") if isinstance(o.get("plan"), dict) else {}
        try:
            inst = tc.resolve(raw_sym, c, reg)
            sym = inst["symbol"]
        except tc.TraderError as e:
            inst, sym = None, raw_sym.upper()
            reasons.append("format: %s" % e)
        if side not in ("buy", "sell"):
            reasons.append("format: side must be buy or sell, got %r" % o.get("side"))
        for k in PRICE_FIELDS:
            if o.get(k) is not None:
                v = _f(o.get(k))
                if v is None or v <= 0:
                    reasons.append("format: %s must be a positive number, got %r" % (k, o.get(k)))
                elif not isinstance(o.get(k), str):
                    warns.append("send %s as a string (\"%s\")" % (k, o.get(k)))
        if typ not in TYPES:
            reasons.append("format: unknown order type %r" % typ)
        if tif not in TIFS:
            reasons.append("format: unknown time_in_force %r" % tif)
        if typ == "limit" and o.get("limit_price") is None:
            reasons.append("format: a limit order needs a limit_price")
        if typ == "stop" and o.get("stop_price") is None:
            reasons.append("format: a stop order needs a stop_price")
        lots, units = _f(o.get("lots")), _f(o.get("units"))
        bracket = str(o.get("order_class") or "").lower() == "bracket"
        if inst:
            if lots is None and units is None:
                reasons.append("format: give lots or units")
            elif lots is None:
                lots = units / inst["contract"]
            elif units is None:
                units = lots * inst["contract"]
            if lots is not None and units is not None and abs(lots * inst["contract"] - units) > 1e-6 * max(1, units):
                reasons.append("format: %s lots x %s contract = %s units, not %s" % (
                    tc.num(lots), tc.num(inst["contract"]), tc.num(lots * inst["contract"]), tc.num(units)))
            if lots is not None:
                steps = lots / inst["lot_step"]
                if abs(steps - round(steps)) > 1e-6:
                    reasons.append("format: %s lots is not a whole number of %s steps" % (tc.num(lots),
                                                                                       tc.num(inst["lot_step"])))
                if lots < inst["min_lot"] - EPS:
                    reasons.append("format: %s lots is under the %s minimum" % (tc.num(lots), tc.num(inst["min_lot"])))
            if bracket and (o.get("stop_loss") is None or o.get("take_profit") is None):
                reasons.append("format: a bracket order needs both stop_loss and take_profit")
            # asset
            if inst["class"] not in allowed:
                reasons.append("asset: %s is %s; your allowed_classes are %s" % (sym, inst["class"],
                                                                                 ", ".join(sorted(allowed))))
            if inst["kind"] == "future" and not c.get("allow_futures", True):
                reasons.append("asset: %s is a futures contract and \"allow_futures\" is false" % sym)
            if inst["class"] not in prof["classes"] or inst["kind"] not in prof["kinds"]:
                reasons.append("asset: %s (%s %s) is not something %s carries in this pack" % (
                    sym, inst["class"], inst["kind"], prof["label"]))

        # the reference price
        plan_entry = _f(plan.get("entry"))
        live = prices.get(sym) if (price_times is None or tc.fresh(price_times, sym, now_utc, FRESH_MINUTES)) else None
        long = side == "buy"
        ref, ref_from = None, None
        if typ == "limit":
            ref, ref_from = _f(o.get("limit_price")), "limit"
        elif typ == "stop":
            ref, ref_from = _f(o.get("stop_price")), "stop price"
        if ref is None:
            cands = [(p, w) for p, w in ((plan_entry, "plan"), (live, "price")) if p]
            if cands:
                ref, ref_from = (max if long else min)(cands, key=lambda x: x[0])
                if ref_from == "price" and plan_entry:
                    info.append("%s last %s is past the plan's entry %s: the risk is measured from it" % (
                        sym, tc.fmt_price(ref, inst), tc.fmt_price(plan_entry, inst)))
            elif sym in prices:
                ref, ref_from = prices[sym], "stale price"
        if plan_entry and live is None and sym in prices and price_times is not None and typ == "market":
            warns.append("the %s price in trader/prices.json is older than %d minutes: not used" % (sym, FRESH_MINUTES))

        # entry or exit
        held = tc.held_units(st, sym)
        kind = "entry"
        if units is not None:
            if side == "sell" and held > EPS and units <= held + EPS:
                kind = "exit"
            elif side == "buy" and held < -EPS and units <= -held + EPS:
                kind = "exit"
        if kind == "entry" and side == "sell" and inst:
            if not c.get("allow_short", True):
                reasons.append("short: selling %s opens a short and \"allow_short\" is false" % sym)
            elif not prof.get("short", True) or (inst["class"] == "crypto" and inst["kind"] == "spot"
                                                 and prof["name"] == "alpaca"):
                reasons.append("short: %s cannot short %s (spot); you can only sell what you hold" % (prof["label"], sym))

        conv = notional = margin = None
        max_loss = risk_u = rr = None
        stop = _f(o.get("stop_loss")) or _f(plan.get("stop"))
        target = _f(o.get("take_profit")) or _f(plan.get("target"))
        if inst and ref and units:
            try:
                conv = tc.quote_to_account(inst, acct, rates, ref)
            except tc.TraderError as e:
                later.append("conversion: %s" % e)
        if inst and ref and units and conv:
            notional = units * ref * conv
            margin = notional / tc.leverage_cap(inst, c)
        if inst and kind == "entry":
            if sym in blocked:
                later.append("blocked: %s is on your blocked list" % sym)
            leg, pstop = _f(o.get("stop_loss")), _f(plan.get("stop"))
            if leg and pstop and abs(leg - pstop) > inst["tick"] / 2:
                warns.append("the bracket stop %s differs from the plan's %s: the bracket's is the one the broker "
                             "uses" % (tc.fmt_price(leg, inst), tc.fmt_price(pstop, inst)))
            if stop and not leg:
                warns.append("the stop %s is in the plan only, not at the broker: place it right after the fill and "
                             "set an alert (alerts.py add --from-plan)" % tc.fmt_price(stop, inst))
            if not stop:
                if c.get("require_stop", True):
                    later.append("stop: no stop. Every entry needs one (\"require_stop\": true): from trader-exit and "
                                 "trader-budget")
                else:
                    warns.append("no stop: the loss is not capped, so it is not counted in the daily loss")
            elif ref:
                if (long and stop >= ref - EPS) or (not long and stop <= ref + EPS):
                    later.append("stop: the stop %s must be %s the entry %s for a %s" % (
                        tc.fmt_price(stop, inst), "below" if long else "above", tc.fmt_price(ref, inst), side))
                else:
                    risk_u = abs(ref - stop)
                    if conv and units:
                        max_loss = round(units * risk_u * conv, 2)
                        cap = _f(c.get("max_loss_per_trade"))
                        if cap and max_loss > cap + 0.005:
                            later.append("loss: %s units x %s x %s = %s at the stop, over your %s max loss per trade"
                                         % (tc.num(units), tc.fmt_dist(risk_u, inst), tc.num(round(conv, 6)),
                                            tc.money(max_loss, acct), tc.money(cap, acct)))
                    mrr = _f(c.get("min_reward_risk"))
                    if target:
                        if (long and target <= ref + EPS) or (not long and target >= ref - EPS):
                            later.append("target: the target %s must be %s the entry %s" % (
                                tc.fmt_price(target, inst), "above" if long else "below", tc.fmt_price(ref, inst)))
                        else:
                            rr = round(abs(target - ref) / risk_u, 2)
                            if mrr and rr < mrr - 1e-9:
                                later.append("reward:risk: %.2f is under your minimum %s" % (rr, tc.num(mrr)))
                    elif mrr:
                        later.append("reward:risk: no target to measure it against (min_reward_risk %s)" % tc.num(mrr))
            daily = _f(c.get("max_daily_loss"))
            if daily and max_loss is not None and loss_today + batch_loss + max_loss > daily + 0.005:
                later.append("daily loss: %s already at risk today plus %s for this one = %s, over your %s daily "
                             "loss limit" % (tc.money(loss_today + batch_loss, acct), tc.money(max_loss, acct),
                                             tc.money(loss_today + batch_loss + max_loss, acct), tc.money(daily, acct)))
            if streak_cap and streak >= streak_cap:
                later.append("streak: %d losing results in a row today in your journal (limit %d): stop for the day "
                             "and review (journal.py stats)" % (streak, streak_cap))
            if prop:
                if prop["breached"] or prop["status"].startswith("NO ROOM"):
                    later.append("prop firm: %s (%s)" % (prop["status"], prop["label"]))
                elif max_loss is not None and max_loss > prop["max_risk_per_trade"] + 0.005:
                    later.append("prop firm: %s at the stop is over the %s that %d losses in a row allow inside today's "
                                 "room (propfirm.py status)" % (tc.money(max_loss, acct),
                                                               tc.money(prop["max_risk_per_trade"], acct),
                                                               prop["streak_assumed"]))
                elif max_loss is not None and batch_loss + max_loss > prop["room"] * 0.8 + 0.005:
                    later.append("prop firm: this batch would risk %s of today's %s room" % (
                        tc.money(batch_loss + max_loss, acct), tc.money(prop["room"], acct)))
            cap_t = int(c.get("max_trades_per_day") or 0)
            if cap_t and len(entries_today) + batch_entries >= cap_t:
                later.append("trades: %d entries placed today plus %d passed earlier in this batch, your limit is %d a "
                             "day" % (len(entries_today), batch_entries, cap_t))
            if notional is not None and equity > 0:
                lev = _f(c.get("max_account_leverage"))
                after = (st["notional"] + notional) / equity
                if lev and after > lev + 1e-9:
                    later.append("leverage: %s notional open plus %s for this one = %.2fx your %s equity, over your "
                                 "%sx" % (tc.money(st["notional"], acct), tc.money(notional, acct), after,
                                          tc.money(equity, acct), tc.num(lev)))
                mm = _f(c.get("max_margin_use_pct"))
                m_after = 100.0 * (st["margin"] + margin) / equity
                if mm and m_after > mm + 1e-9:
                    later.append("margin: %s in use plus %s = %.1f%% of equity, over your %s%%" % (
                        tc.money(st["margin"], acct), tc.money(margin, acct), m_after, tc.num(mm)))
                if m_after > 100:
                    later.append("margin: not enough free margin at %s:1" % tc.num(tc.leverage_cap(inst, c)))
                xcap = _f(c.get("max_currency_exposure_x"))
                adds = tc.exposure_of(inst, units if long else -units, notional, acct)
                for bucket, v in sorted(adds.items()):
                    before = st["exposure"].get(bucket, 0.0)
                    now_x = (before + v) / equity
                    if xcap and abs(now_x) > xcap + 1e-9:
                        later.append("exposure: net %s %s would be %s, %.2fx equity, over your %sx" % (
                            "long" if now_x > 0 else "short", bucket, tc.money(abs(before + v), acct), abs(now_x),
                            tc.num(xcap)))
                    elif abs(before) > EPS and (before > 0) == (v > 0):
                        warns.append("correlated: this adds to an open %s %s position (%s before, %s after)" % (
                            "long" if v > 0 else "short", bucket, tc.money(abs(before), acct),
                            tc.money(abs(before + v), acct)))
                info.append("notional %s (%.2fx the account after), margin about %s at %s:1" % (
                    tc.money(notional, acct), after, tc.money(margin, acct), tc.num(tc.leverage_cap(inst, c))))
            sname = plan.get("session") or inst["session"]
            win_r, win_w, win_label = window_check(inst, sname, now_utc, c)
            later.extend(win_r)
            warns.extend(win_w)
            n_r, n_w = news_check(inst, now_utc, calendar, c)
            later.extend(n_r)
            warns.extend(n_w)
            if stop and ref and risk_u:
                info.insert(0, "entry %s (%s), stop %s, target %s: risk %s a unit" % (
                    tc.fmt_price(ref, inst), REF_WORDS.get(ref_from, ref_from), tc.fmt_price(stop, inst),
                    tc.fmt_price(target, inst) if target else "none", tc.fmt_dist(risk_u, inst)))
                info.insert(1, "max loss %s%s, reward:risk %s%s" % (
                    tc.money(max_loss, acct) if max_loss is not None else "unknown",
                    (" (limit %s)" % tc.money(c["max_loss_per_trade"], acct)) if _f(c.get("max_loss_per_trade")) else "",
                    ("%.2f" % rr) if rr is not None else "n/a",
                    (" (min %s)" % tc.num(c["min_reward_risk"])) if _f(c.get("min_reward_risk")) else ""))
            if win_label:
                info.append("entry window: %s" % win_label)
        if inst and kind == "exit":
            win_r, _, _ = window_check(inst, plan.get("session") or inst["session"], now_utc, c)
            later.extend(win_r)
        key = (sym, side)
        if key in seen:
            later.append("duplicate: a second %s %s in this batch" % (side, sym))
        if key in placed_keys:
            later.append("duplicate: a %s %s was already placed today" % (side, sym))
        passed_so_far = sum(1 for r in results if r["verdict"] == "PASS")
        cap_n = int(c.get("max_orders_per_day") or 0)
        if cap_n and len(done_today) + passed_so_far >= cap_n:
            later.append("daily limit: %d placed today plus %d passed earlier in this batch, your limit is %d a day"
                         % (len(done_today), passed_so_far, cap_n))
        seen.add(key)
        if kind == "entry":
            reasons.extend(later)
        else:
            warns.extend("exit, not blocked: " + x for x in later)
        verdict = "BLOCK" if reasons else "PASS"
        if verdict == "PASS" and inst and units:
            signed = units if long else -units
            if kind == "entry":
                batch_entries += 1
                batch_loss += max_loss or 0.0
            px = ref or prices.get(sym) or 0.0
            st["positions"].append({"symbol": sym, "units": signed, "avg_price": px, "price": px})
            if notional is not None:
                if kind == "entry":
                    st["notional"] += notional
                    st["margin"] += margin
                    for k, v in tc.exposure_of(inst, signed, notional, acct).items():
                        st["exposure"][k] = st["exposure"].get(k, 0.0) + v
                else:
                    st["notional"] = max(0.0, st["notional"] - notional)
                    st["margin"] = max(0.0, st["margin"] - margin)
                    for k, v in tc.exposure_of(inst, signed, notional, acct).items():
                        st["exposure"][k] = st["exposure"].get(k, 0.0) + v
        results.append({
            "index": i, "symbol": sym, "side": side, "kind": kind,
            "amount": "%s lots (%s units)" % (o.get("lots") or tc.num(lots or 0), o.get("units") or tc.num(units or 0)),
            "entry_ref": ref, "entry_ref_from": ref_from, "stop": stop, "target": target,
            "risk_per_unit": risk_u, "max_loss": max_loss, "reward_risk": rr,
            "notional": round(notional, 2) if notional is not None else None,
            "margin": round(margin, 2) if margin is not None else None,
            "fingerprint": fingerprint(o), "verdict": verdict, "reasons": reasons, "warnings": warns, "info": info,
        })
    return {
        "date": today, "now_utc": tc.iso(now_utc), "now": tc.stamp(now_utc, c["timezone"]),
        "paper": bool(c.get("paper", True)), "broker": prof["name"], "currency": acct, "results": results,
        "pass": sum(1 for r in results if r["verdict"] == "PASS"),
        "block": sum(1 for r in results if r["verdict"] == "BLOCK"), "warnings": top_warn,
        "account": {"balance": round(st["balance"], 2), "equity": round(equity, 2),
                    "notional_after": round(st["notional"], 2), "margin_after": round(st["margin"], 2),
                    "exposure_after": {k: round(v, 2) for k, v in sorted(st["exposure"].items())}},
        "today": {"orders_placed": len(done_today), "entries_placed": len(entries_today),
                  "loss_at_risk": round(loss_today, 2), "losing_streak": streak},
        "prop_firm": {k: prop[k] for k in ("label", "status", "room", "max_risk_per_trade")} if prop else None,
    }


def report(res):
    acct = res["currency"]
    lines = ["WARNING: " + w for w in res["warnings"]]
    if res["warnings"]:
        lines.append("")
    for r in res["results"]:
        lines.append("%-5s #%d %s %s %s, %s" % (r["verdict"], r["index"], r["side"], r["symbol"], r["amount"],
                                                r["kind"]))
        for x in r.get("info", []):
            lines.append("          " + x)
        for x in r["reasons"]:
            lines.append("        - " + x)
        for x in r["warnings"]:
            lines.append("        ~ " + x)
    a = res["account"]
    lines.append("")
    lines.append("%d passed, %d blocked at %s. Equity %s; after the passed orders: notional %s, margin %s (%s account, "
                 "%s)." % (res["pass"], res["block"], res["now"], tc.money(a["equity"], acct),
                           tc.money(a["notional_after"], acct), tc.money(a["margin_after"], acct),
                           "paper" if res["paper"] else "LIVE", res["broker"]))
    if a["exposure_after"]:
        lines.append("Net exposure after: " + ", ".join("%s %s %s" % (k, "long" if v > 0 else "short",
                                                                     tc.money(abs(v), acct))
                                                        for k, v in a["exposure_after"].items()) + ".")
    if res.get("prop_firm"):
        pf = res["prop_firm"]
        lines.append("Prop firm (%s): %s, room %s, largest safe risk %s a trade." % (
            pf["label"], pf["status"], tc.money(pf["room"], acct), tc.money(pf["max_risk_per_trade"], acct)))
    if res["today"].get("losing_streak"):
        lines.append("Losing results in a row today: %d." % res["today"]["losing_streak"])
    if res["block"]:
        lines.append("Blocked orders do not go to the broker. Fix the order or your rules, then check again.")
    else:
        lines.append("Every order passed. trader-broker still asks you yes or no for each one.")
    lines.append(tc.NOTE_ADVICE)
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check proposed orders against your limits (trader-risk).")
    ap.add_argument("--orders", default="trader/orders.json")
    ap.add_argument("--config", default="trader/config.json")
    ap.add_argument("--portfolio", default="trader/portfolio.json")
    ap.add_argument("--prices", default="trader/prices.json")
    ap.add_argument("--calendar", default="trader/calendar.json")
    ap.add_argument("--state", default="trader/state/broker.json")
    ap.add_argument("--journal", default="trader/journal.csv", help="for the losing-streak pause")
    ap.add_argument("--prop", default="trader/propfirm.json", help="a tracked prop-firm challenge, if any")
    ap.add_argument("--rate", action="append", metavar="PAIR=RATE")
    ap.add_argument("--now", help='pretend it is this time, e.g. "2026-11-16 08:45 London"')
    ap.add_argument("--today", help="YYYY-MM-DD (default: today in the config's time zone)")
    ap.add_argument("--out", default="trader/state/risk.json")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        cfg = tc.load_config(a.config)
        now = tc.parse_now(a.now, cfg["timezone"])
        if a.today and not re.match(r"^\d{4}-\d{2}-\d{2}$", a.today):
            raise RiskError("--today wants a date like 2026-11-16")
        doc = tc.read_json(a.orders, "orders file (run trader-budget first)")
        orders = doc.get("orders", doc) if isinstance(doc, dict) else doc
        if not isinstance(orders, list) or not orders:
            raise RiskError("no orders in %s" % a.orders)
        portfolio = tc.read_json(a.portfolio, "portfolio", required=False)
        pdoc = tc.read_json(a.prices, "prices", required=False) or {}
        prices, times = tc.load_prices(pdoc)
        rates = tc.rates_from(pdoc, cfg, tc.parse_rates(a.rate))
        state = tc.read_json(a.state, "broker state", required=False)
        calendar = tc.read_json(a.calendar, "calendar", required=False)
        journal = None
        if os.path.exists(a.journal):
            with open(a.journal, newline="", encoding="utf-8") as fh:
                journal = list(csv.DictReader(fh))
        res = check(orders, cfg, portfolio, prices, times, rates, state, calendar, now, a.today, journal,
                    prop_guard(a.prop, cfg))
        if pdoc.get("as_of"):
            res["prices_as_of"] = pdoc["as_of"]
        if not a.no_write:
            tc.write_json(a.out, dict(res, checked_at=tc.iso(tc.utc_now()), orders_file=a.orders))
    except tc.TraderError as e:
        print("check.py: %s" % e, file=sys.stderr)
        return 1
    print(json.dumps(res, indent=2) if a.json else report(res))
    return 1 if res["block"] else 0


if __name__ == "__main__":
    sys.exit(main())
