#!/usr/bin/env python3
"""Macro for trader-macro: inflation, jobs, rates, the curve, the dollar, volatility, rate
differentials for any currency pair, crypto sentiment and central-bank headlines, from free
public sources. Standard library only.

    python3 macro.py refresh                      # download the FRED series below -> trader/data/macro/fred.json
    python3 macro.py dashboard                    # CPI, core CPI, core PCE, jobs, Fed, yields, curve, dollar, VIX
    python3 macro.py diff EURUSD                  # the 3-month rate differential and its trend (carry)
    python3 macro.py dollar                       # the four-pillar US dollar compass
    python3 macro.py gold                         # real yields + the dollar: the gold backdrop
    python3 macro.py feargreed                    # crypto Fear & Greed (alternative.me), last 30 days
    python3 macro.py cb                           # Fed, ECB, BoE and BoJ press releases

Sources: FRED (fred.stlouisfed.org, CSV), OECD 3-month interbank rates on FRED for the
differentials, alternative.me for crypto sentiment, the central banks' own RSS feeds. All
free; FRED updates monthly data with a lag, so read the "as of" dates.

Macro is a backdrop, not a trigger: it tells you which way the wind blows this month, not
where price goes this hour. The economic calendar (/trader-calendar) says WHEN numbers land.
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

CORE = ["CPIAUCSL", "CPILFESL", "PCEPILFE", "UNRATE", "PAYEMS", "DFF", "DGS2", "DGS10", "T10Y2Y", "DFII10",
        "DTWEXBGS", "VIXCLS"]
RATES = {"USD": "IR3TIB01USM156N", "EUR": "IR3TIB01EZM156N", "GBP": "IR3TIB01GBM156N", "JPY": "IR3TIB01JPM156N",
         "CAD": "IR3TIB01CAM156N", "AUD": "IR3TIB01AUM156N", "CHF": "IR3TIB01CHM156N", "NZD": "IR3TIB01NZM156N"}
LABELS = {"CPIAUCSL": "CPI", "CPILFESL": "core CPI", "PCEPILFE": "core PCE", "UNRATE": "unemployment",
          "PAYEMS": "payrolls", "DFF": "fed funds", "DGS2": "US 2-year", "DGS10": "US 10-year",
          "T10Y2Y": "10y-2y curve", "DFII10": "10-year real yield", "DTWEXBGS": "broad dollar index",
          "VIXCLS": "VIX"}
FNG = "https://api.alternative.me/fng/?limit=30&format=json"
CB_FEEDS = {"Fed": "https://www.federalreserve.gov/feeds/press_all.xml",
            "ECB": "https://www.ecb.europa.eu/rss/press.html",
            "BoE": "https://www.bankofengland.co.uk/rss/news",
            "BoJ": "https://www.boj.or.jp/en/rss/whatsnew.xml"}


def cache_path(root):
    return os.path.join(root, "macro", "fred.json")


def load_fred(root):
    doc = tc.read_json(cache_path(root), "FRED cache", required=False) or {}
    if not doc:
        raise tc.TraderError("no macro data yet: run macro.py refresh (or data.py fred CPIAUCSL ...)")
    return {k: [(datetime.date.fromisoformat(d), float(v)) for d, v in rows] for k, rows in doc.items()}


def series(data, key):
    s = data.get(key)
    if not s:
        raise tc.TraderError("%s is not in the macro cache: run macro.py refresh" % key)
    return s


def at_or_before(s, day):
    best = None
    for d, v in s:
        if d <= day:
            best = (d, v)
        else:
            break
    return best


def yoy(s, months_back=0):
    """Year-on-year % change of a monthly index, `months_back` observations ago."""
    if len(s) < 13 + months_back:
        return None
    i = len(s) - 1 - months_back
    return 100.0 * (s[i][1] / s[i - 12][1] - 1)


def change(s, days):
    """Latest value minus the value `days` calendar days earlier."""
    last_d, last_v = s[-1]
    old = at_or_before(s, last_d - datetime.timedelta(days=days))
    return None if old is None else last_v - old[1]


def pct_change(s, days):
    last_d, last_v = s[-1]
    old = at_or_before(s, last_d - datetime.timedelta(days=days))
    return None if old is None or not old[1] else 100.0 * (last_v / old[1] - 1)


def trend_word(x, eps=0.0):
    if x is None:
        return "n/a"
    return "rising" if x > eps else "falling" if x < -eps else "flat"


# ---------------------------------------------------------------- reads

def dashboard(data):
    out = {}
    for k in ("CPIAUCSL", "CPILFESL", "PCEPILFE"):
        s = series(data, k)
        now, before = yoy(s), yoy(s, 3)
        out[k] = {"label": LABELS[k], "as_of": s[-1][0].isoformat(), "yoy": now,
                  "yoy_3m_ago": before, "trend": trend_word(None if now is None or before is None else now - before, 0.05)}
    u = series(data, "UNRATE")
    avg3 = [sum(v for _, v in u[k - 2:k + 1]) / 3.0 for k in range(2, len(u))]
    sahm = avg3[-1] - min(avg3[-13:-1]) if len(avg3) >= 13 else None
    out["UNRATE"] = {"label": "unemployment", "as_of": u[-1][0].isoformat(), "value": u[-1][1],
                     "change_3m": u[-1][1] - u[-4][1] if len(u) >= 4 else None,
                     "sahm_gap": sahm, "sahm_triggered": sahm is not None and sahm >= 0.5}
    p = series(data, "PAYEMS")
    m = [p[k][1] - p[k - 1][1] for k in range(1, len(p))]
    out["PAYEMS"] = {"label": "payrolls", "as_of": p[-1][0].isoformat(), "last_change_k": m[-1] if m else None,
                     "avg_3m_k": sum(m[-3:]) / 3.0 if len(m) >= 3 else None}
    for k, days in (("DFF", 90), ("DGS2", 90), ("DGS10", 90), ("T10Y2Y", 90), ("DFII10", 90), ("VIXCLS", 30)):
        s = series(data, k)
        out[k] = {"label": LABELS[k], "as_of": s[-1][0].isoformat(), "value": s[-1][1], "change": change(s, days),
                  "window_days": days}
    d = series(data, "DTWEXBGS")
    out["DTWEXBGS"] = {"label": LABELS["DTWEXBGS"], "as_of": d[-1][0].isoformat(), "value": d[-1][1],
                       "change_pct_3m": pct_change(d, 90)}
    curve = out["T10Y2Y"]["value"]
    vix = out["VIXCLS"]["value"]
    core = out["CPILFESL"]["yoy"]
    regime = []
    if core is not None:
        regime.append("core inflation %.1f%% and %s" % (core, out["CPILFESL"]["trend"]))
    regime.append("the curve is %s (%+.2f)" % ("inverted" if curve < 0 else "positive", curve))
    regime.append("volatility %s (VIX %.1f)" % ("stressed" if vix >= 25 else "calm" if vix < 15 else "normal", vix))
    if out["UNRATE"]["sahm_triggered"]:
        regime.append("the Sahm rule has triggered (unemployment's 3-month average is 0.5 points over its 12-month low)")
    out["regime"] = regime
    return out


def dollar_compass(data):
    """Four pillars, each +1 (dollar tailwind), -1 (headwind) or 0."""
    pillars = []
    c2 = change(series(data, "DGS2"), 90)
    pillars.append(("rates", 0 if c2 is None or abs(c2) < 0.10 else (1 if c2 > 0 else -1),
                    "the 2-year yield %s %+.2f in 3 months" % (trend_word(c2, 0.10), c2 or 0)))
    cr = change(series(data, "DFII10"), 90)
    pillars.append(("real yields", 0 if cr is None or abs(cr) < 0.10 else (1 if cr > 0 else -1),
                    "the 10-year real yield %s %+.2f" % (trend_word(cr, 0.10), cr or 0)))
    p = series(data, "PAYEMS")
    m = [p[k][1] - p[k - 1][1] for k in range(1, len(p))][-3:]
    u = series(data, "UNRATE")
    du = u[-1][1] - u[-4][1] if len(u) >= 4 else 0
    avg = sum(m) / len(m) if m else 0
    g = 1 if avg >= 150 and du <= 0 else -1 if avg < 50 or du >= 0.3 else 0
    pillars.append(("growth", g, "payrolls %+.0fk a month on average, unemployment %+.1f in 3 months" % (avg, du)))
    vix = series(data, "VIXCLS")[-1][1]
    pillars.append(("risk", 1 if vix >= 25 else -1 if vix < 15 else 0,
                    "VIX %.1f: %s" % (vix, "haven demand helps the dollar" if vix >= 25 else
                                      "risk-on, the dollar tends to soften" if vix < 15 else "neutral")))
    score = sum(x[1] for x in pillars)
    word = "a dollar tailwind" if score >= 2 else "a dollar headwind" if score <= -2 else "mixed for the dollar"
    dx = pct_change(series(data, "DTWEXBGS"), 90)
    return {"pillars": [{"pillar": n, "score": s, "why": w} for n, s, w in pillars], "score": score, "read": word,
            "dollar_3m_pct": dx}


def differential(data, pair):
    base, quote = pair[:3].upper(), pair[3:6].upper()
    for ccy in (base, quote):
        if ccy not in RATES:
            raise tc.TraderError("no rate series for %s: differentials cover %s" % (ccy, ", ".join(sorted(RATES))))
    sb, sq = series(data, RATES[base]), series(data, RATES[quote])
    day = min(sb[-1][0], sq[-1][0])
    now = at_or_before(sb, day)[1] - at_or_before(sq, day)[1]
    old_day = day - datetime.timedelta(days=92)
    ob, oq = at_or_before(sb, old_day), at_or_before(sq, old_day)
    before = ob[1] - oq[1] if ob and oq else None
    return {"pair": base + quote, "as_of": day.isoformat(), "base_rate": at_or_before(sb, day)[1],
            "quote_rate": at_or_before(sq, day)[1], "differential": now,
            "change_3m": None if before is None else now - before,
            "carry": "long %s earns the carry" % (base + quote) if now > 0 else "short %s earns the carry" % (base + quote)
            if now < 0 else "no carry either way",
            "source": "OECD 3-month interbank rates via FRED (monthly)"}


def gold_backdrop(data):
    cr = change(series(data, "DFII10"), 90)
    dx = pct_change(series(data, "DTWEXBGS"), 90)
    score = (1 if cr is not None and cr < -0.10 else -1 if cr is not None and cr > 0.10 else 0) + \
        (1 if dx is not None and dx < -1 else -1 if dx is not None and dx > 1 else 0)
    return {"real_yield": series(data, "DFII10")[-1][1], "real_yield_change_3m": cr, "dollar_change_3m_pct": dx,
            "score": score, "read": "a gold tailwind" if score >= 1 else "a gold headwind" if score <= -1 else "neutral"}


# ---------------------------------------------------------------- network reads

def fetch_fng():
    raw = hist.http_bytes(FNG)
    doc = json.loads((raw or b"{}").decode("utf-8"))
    rows = doc.get("data") or []
    if not rows:
        raise tc.TraderError("alternative.me sent no Fear & Greed data")
    return [{"value": int(r["value"]), "label": r.get("value_classification", ""),
             "date": tc.iso(tc.utc_of(int(r["timestamp"])))[:10]} for r in rows]


def news_module():
    spec = importlib.util.spec_from_file_location("trader_news_for_macro", os.path.join(HERE, "..", "trader-news", "news.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fetch_cb(banks):
    news = news_module()
    out = []
    for bank in banks:
        raw = hist.http_bytes(CB_FEEDS[bank])
        if not raw:
            out.append({"bank": bank, "error": "no answer"})
            continue
        try:
            items = news.parse_rss(raw.decode("utf-8", "replace"))
        except tc.TraderError as e:
            out.append({"bank": bank, "error": str(e)})
            continue
        for it in items[:8]:
            out.append({"bank": bank, "title": it["title"], "link": it["link"],
                        "time": tc.iso(it["time"]) if it["time"] else None})
    return out


# ---------------------------------------------------------------- commands

def f2(x, fmt="%.2f"):
    return "n/a" if x is None else fmt % x


def cmd_refresh(a, cfg):
    wanted = a.series or (CORE + sorted(set(RATES.values())))
    path = cache_path(a.data)
    old = tc.read_json(path, "FRED cache", required=False) or {}
    got, failed = [], []
    for s in wanted:
        try:
            rows = hist.fetch_fred(s)
        except tc.TraderError as e:
            failed.append("%s (%s)" % (s, e))
            continue
        old[s] = [(d.isoformat(), v) for d, v in rows]
        got.append(s)
        tc.SLEEP(0.2)
    tc.write_json(path, old)
    print("Saved %d series to %s%s." % (len(got), path, "; failed: " + ", ".join(failed) if failed else ""))
    return 0 if got else 1


def cmd_dashboard(a, cfg):
    d = dashboard(load_fred(a.data))
    if a.json:
        print(json.dumps(d, indent=2))
        return 0
    print("US macro (FRED; monthly data lags a month or more):")
    for k in ("CPIAUCSL", "CPILFESL", "PCEPILFE"):
        x = d[k]
        print("  %-18s %s%% y/y (%s%% 3 months ago, %s), as of %s" % (x["label"], f2(x["yoy"]), f2(x["yoy_3m_ago"]),
                                                                    x["trend"], x["as_of"]))
    u, p = d["UNRATE"], d["PAYEMS"]
    print("  %-18s %.1f%% (%s in 3 months)%s, as of %s" % (
        "unemployment", u["value"], f2(u["change_3m"], "%+.1f"), "; SAHM RULE TRIGGERED" if u["sahm_triggered"] else "",
        u["as_of"]))
    print("  %-18s %sk last month, %sk a month over 3 months, as of %s" % (
        "payrolls", f2(p["last_change_k"], "%+.0f"), f2(p["avg_3m_k"], "%+.0f"), p["as_of"]))
    for k in ("DFF", "DGS2", "DGS10", "T10Y2Y", "DFII10", "VIXCLS"):
        x = d[k]
        print("  %-18s %.2f (%s over %d days), as of %s" % (x["label"], x["value"], f2(x["change"], "%+.2f"),
                                                          x["window_days"], x["as_of"]))
    x = d["DTWEXBGS"]
    print("  %-18s %.2f (%s%% over 3 months), as of %s" % ("broad dollar index", x["value"], f2(x["change_pct_3m"], "%+.2f"),
                                                          x["as_of"]))
    print("Regime: %s." % "; ".join(d["regime"]))
    return 0


def cmd_dollar(a, cfg):
    c = dollar_compass(load_fred(a.data))
    if a.json:
        print(json.dumps(c, indent=2))
        return 0
    print("US dollar compass: %+d of 4, %s (the broad dollar index %s%% over 3 months)" % (
        c["score"], c["read"], f2(c["dollar_3m_pct"], "%+.2f")))
    for p in c["pillars"]:
        print("  %-12s %+d  %s" % (p["pillar"], p["score"], p["why"]))
    print("A backdrop for USD pairs, gold and US indices, not a timing signal.")
    return 0


def cmd_diff(a, cfg):
    data = load_fred(a.data)
    rows = [differential(data, p) for p in a.pairs]
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    for r in rows:
        print("%s: %s %.2f%% vs %s %.2f%% = %+.2f points (%s in 3 months), as of %s: %s." % (
            r["pair"], r["pair"][:3], r["base_rate"], r["pair"][3:], r["quote_rate"], r["differential"],
            f2(r["change_3m"], "%+.2f"), r["as_of"], r["carry"]))
    print("Source: OECD 3-month interbank rates via FRED. A widening differential tends to support the higher-yielder; "
          "your broker's swap rates are what you actually pay or earn overnight.")
    return 0


def cmd_gold(a, cfg):
    g = gold_backdrop(load_fred(a.data))
    if a.json:
        print(json.dumps(g, indent=2))
        return 0
    print("Gold backdrop: %s. 10-year real yield %.2f%% (%s in 3 months), broad dollar %s%% in 3 months." % (
        g["read"], g["real_yield"], f2(g["real_yield_change_3m"], "%+.2f"), f2(g["dollar_change_3m_pct"], "%+.2f")))
    print("Falling real yields and a softer dollar have historically supported gold; central-bank buying and "
          "geopolitics can override both.")
    return 0


def cmd_feargreed(a, cfg):
    rows = fetch_fng()
    tc.write_json(os.path.join(a.data, "macro", "feargreed.json"), rows)
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    now = rows[0]
    avg7 = sum(r["value"] for r in rows[:7]) / min(7, len(rows))
    print("Crypto Fear & Greed: %d (%s) on %s; 7-day average %.0f; 30 days ago %d." % (
        now["value"], now["label"], now["date"], avg7, rows[-1]["value"]))
    print("Extreme fear has often come near lows and extreme greed near highs, but both can last for weeks.")
    return 0


def cmd_cb(a, cfg):
    banks = a.banks or sorted(CB_FEEDS)
    rows = fetch_cb(banks)
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    for r in rows:
        if r.get("error"):
            print("  %-4s could not read the feed: %s" % (r["bank"], r["error"]))
        else:
            print("  %-4s %s  %s" % (r["bank"], (r["time"] or "")[:16].replace("T", " "), r["title"]))
    print("Headlines only: read the statement itself before you act on a word in it.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Macro backdrop (trader-macro).")
    ap.add_argument("--config", default="trader/config.json")
    ap.add_argument("--data", default=hist.CACHE, help="the data folder (default trader/data)")
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("refresh")
    p.add_argument("series", nargs="*", help="FRED series ids (default: the dashboard's and the rate series)")
    sub.add_parser("dashboard")
    sub.add_parser("dollar")
    sub.add_parser("gold")
    p = sub.add_parser("diff")
    p.add_argument("pairs", nargs="+", help="e.g. EURUSD USDJPY AUDNZD")
    sub.add_parser("feargreed")
    p = sub.add_parser("cb")
    p.add_argument("--banks", nargs="*", choices=sorted(CB_FEEDS))
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        cfg = tc.load_config(a.config)
        return {"refresh": cmd_refresh, "dashboard": cmd_dashboard, "dollar": cmd_dollar, "gold": cmd_gold,
                "diff": cmd_diff, "feargreed": cmd_feargreed, "cb": cmd_cb}[a.cmd](a, cfg)
    except (tc.TraderError, ValueError) as e:
        print("macro.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
