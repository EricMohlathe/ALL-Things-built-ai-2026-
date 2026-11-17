#!/usr/bin/env python3
"""Builds the offline test fixtures. Deterministic: same seed, same files, any machine.

    python3 tests/fixtures/make_fixtures.py

SYNTHETIC DATA. The bars are seeded random walks in the exact shape of Yahoo's
v8 chart JSON, on each market's real hours (the FX week Sunday 17:00 to Friday
17:00 New York, CME Globex with its daily 17:00-18:00 break, NYSE 9:30-16:00,
crypto 24/7), across both 2026 DST changes. On Monday 2026-11-16 each chart
carries a hand-made setup with known numbers, so the tests can check them to the
tick. The calendar, COT and news files are synthetic too. None of it is a claim
about what any market really did.
"""

import datetime
import gzip
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "trader-core"))
import tradercore as tc  # noqa: E402

UTC = datetime.datetime
STEP = datetime.timedelta(minutes=5)
START = UTC(2026, 9, 20, 0, 0)          # a Sunday, before both DST changes
PLAN_DAY = datetime.date(2026, 11, 16)  # Monday


def ny(utc):
    return tc.to_local("America/New_York", utc)


def fx_open(t):
    """The FX week: Sunday 17:00 to Friday 17:00 New York."""
    n = ny(t)
    wd, mins = n.weekday(), n.hour * 60 + n.minute
    if wd == 5:
        return False
    if wd == 6:
        return mins >= 17 * 60
    if wd == 4:
        return mins < 17 * 60
    return True


def cme_open(t):
    """CME Globex: Sunday 18:00 to Friday 17:00 New York, closed 17:00-18:00 every day."""
    n = ny(t)
    wd, mins = n.weekday(), n.hour * 60 + n.minute
    if wd == 5 or (wd == 6 and mins < 18 * 60) or (wd == 4 and mins >= 17 * 60):
        return False
    return not (17 * 60 <= mins < 18 * 60)


def nyse_open(t):
    n = ny(t)
    if n.weekday() >= 5 or n.date().isoformat() in tc.NYSE_HOLIDAYS:
        return False
    mins = n.hour * 60 + n.minute
    return 9 * 60 + 30 <= mins < 16 * 60


def always(t):
    return True


def fx_profile(t):
    h = t.hour
    if 7 <= h < 10:
        return 1.5
    if 12 <= h < 16:
        return 1.6
    if 10 <= h < 12:
        return 1.1
    if 0 <= h < 7:
        return 0.7
    return 0.6


def gold_profile(t):
    h = t.hour
    return 1.7 if 13 <= h < 16 else 1.2 if 7 <= h < 13 else 0.7


def spx_profile(t):
    n = ny(t)
    m = n.hour * 60 + n.minute - (9 * 60 + 30)
    return 1.9 if m < 30 else 1.3 if m >= 360 else 0.85


def btc_profile(t):
    return 1.3 if 13 <= t.hour < 21 else 1.0


def walk(rng, stamps, start, sigma, profile, digits, vol=None):
    out, p = [], start
    for t in stamps:
        s = sigma * profile(t)
        r = rng.gauss(0, s)
        o, c = p, p * math.exp(r)
        h = max(o, c) * math.exp(abs(rng.gauss(0, s)) * 0.6)
        lo = min(o, c) * math.exp(-abs(rng.gauss(0, s)) * 0.6)
        v = 0 if vol is None else int(vol * profile(t) * (0.5 + rng.random()))
        out.append([t, o, h, lo, c, v])
        p = c
    return out


def build(seed, feed, is_open, start_price, sigma, profile, digits, plant, end, vol=None, live_tick=True,
          begin=START):
    """Pre-plant walk scaled to land on the planted open, the planted bars, then a walk on."""
    rng = random.Random(seed)
    stamps = []
    t = begin
    while t < end:
        if is_open(t):
            stamps.append(t)
        t += STEP
    first = min(plant)
    pre = [s for s in stamps if s < first]
    post = [s for s in stamps if s > max(plant)]
    bars = walk(rng, pre, start_price, sigma, profile, digits, vol)
    k = plant[first][0] / bars[-1][4]
    for b in bars:
        for j in (1, 2, 3, 4):
            b[j] *= k
    for s in sorted(plant):
        o, h, lo, c = plant[s]
        v = 0 if vol is None else int(vol * profile(s) * 1.4)
        bars.append([s, o, h, lo, c, v])
    bars += walk(rng, post, bars[-1][4], sigma, profile, digits, vol)
    data_time = tc.ts_of(end) - 83
    doc = v8(feed, bars, digits, "5m", data_time)
    if live_tick:   # Yahoo's live tick: off the 5-minute grid, it must never count as a bar
        q = doc["chart"]["result"][0]
        q["timestamp"].append(data_time)
        last = bars[-1][4]
        for key in ("open", "high", "low", "close"):
            q["indicators"]["quote"][0][key].append(round(last, digits))
        q["indicators"]["quote"][0]["volume"].append(0)
    return doc


def v8(feed, bars, digits, gran, data_time, prev_close=None):
    q = {"open": [], "high": [], "low": [], "close": [], "volume": []}
    stamps = []
    for t, o, h, lo, c, v in bars:
        stamps.append(tc.ts_of(t) if isinstance(t, datetime.datetime) else int(t))
        q["open"].append(round(o, digits))
        q["high"].append(round(max(h, o, c), digits))
        q["low"].append(round(min(lo, o, c), digits))
        q["close"].append(round(c, digits))
        q["volume"].append(int(v))
    meta = {"symbol": feed, "currency": "USD", "dataGranularity": gran, "regularMarketTime": data_time,
            "regularMarketPrice": q["close"][-1], "chartPreviousClose": prev_close or q["open"][0],
            "previousClose": prev_close or q["open"][0], "instrumentType": "SYNTHETIC",
            "note": "synthetic fixture: godmode-trader tests/fixtures/make_fixtures.py"}
    return {"chart": {"result": [{"meta": meta, "timestamp": stamps, "indicators": {"quote": [q]}}], "error": None}}


def at(zone, hhmm, day=PLAN_DAY):
    h, m = map(int, hhmm.split(":"))
    return tc.to_utc(zone, datetime.datetime.combine(day, datetime.time(h, m)))


def plant_rows(zone, rows, day=PLAN_DAY):
    return {at(zone, r[0], day): tuple(r[1:]) for r in rows}


EURUSD_LONDON = [  # range 08:00-08:30: high 1.16240, low 1.16080; the 08:40 bar closes above -> long at 08:45
    ("08:00", 1.16150, 1.16210, 1.16095, 1.16180),
    ("08:05", 1.16180, 1.16240, 1.16150, 1.16205),
    ("08:10", 1.16205, 1.16220, 1.16120, 1.16135),
    ("08:15", 1.16135, 1.16160, 1.16080, 1.16110),
    ("08:20", 1.16110, 1.16190, 1.16100, 1.16175),
    ("08:25", 1.16175, 1.16230, 1.16160, 1.16215),
    ("08:30", 1.16215, 1.16255, 1.16190, 1.16230),   # a wick above the high, a close below: no trigger
    ("08:35", 1.16230, 1.16245, 1.16200, 1.16225),
    ("08:40", 1.16225, 1.16300, 1.16220, 1.16285),   # TRIGGER: closes 1.16285 at 08:45
    ("08:45", 1.16285, 1.16320, 1.16260, 1.16310),
]
GBPUSD_LONDON = [  # range high 1.31480, low 1.31290; the 08:35 bar closes below -> short at 08:40
    ("08:00", 1.31400, 1.31480, 1.31360, 1.31420),
    ("08:05", 1.31420, 1.31450, 1.31330, 1.31350),
    ("08:10", 1.31350, 1.31390, 1.31290, 1.31320),
    ("08:15", 1.31320, 1.31410, 1.31300, 1.31380),
    ("08:20", 1.31380, 1.31430, 1.31340, 1.31360),
    ("08:25", 1.31360, 1.31400, 1.31310, 1.31330),
    ("08:30", 1.31330, 1.31350, 1.31280, 1.31310),
    ("08:35", 1.31310, 1.31320, 1.31220, 1.31255),   # TRIGGER: closes 1.31255 at 08:40
]
USDJPY_LONDON = [  # range high 154.820, low 154.560; stays inside
    ("08:00", 154.700, 154.820, 154.640, 154.760),
    ("08:05", 154.760, 154.800, 154.600, 154.640),
    ("08:10", 154.640, 154.700, 154.560, 154.610),
    ("08:15", 154.610, 154.720, 154.590, 154.690),
    ("08:20", 154.690, 154.760, 154.650, 154.710),
    ("08:25", 154.710, 154.780, 154.680, 154.740),
    ("08:30", 154.740, 154.800, 154.700, 154.760),
    ("08:35", 154.760, 154.790, 154.690, 154.720),
    ("08:40", 154.720, 154.780, 154.660, 154.700),
    ("08:45", 154.700, 154.750, 154.620, 154.680),
    ("08:50", 154.680, 154.740, 154.600, 154.650),
    ("08:55", 154.650, 154.720, 154.580, 154.700),
]
GOLD_COMEX = [  # New York: range 08:20-08:35 high 4062.4, low 4055.1; the 08:45 bar closes below -> short at 08:50
    ("08:20", 4058.0, 4061.3, 4056.2, 4060.1),
    ("08:25", 4060.1, 4062.4, 4057.5, 4058.3),
    ("08:30", 4058.3, 4059.0, 4055.1, 4056.0),
    ("08:35", 4056.0, 4058.8, 4055.6, 4057.9),
    ("08:40", 4057.9, 4058.2, 4054.8, 4055.4),       # a wick below the low, a close above: no trigger
    ("08:45", 4055.4, 4056.0, 4051.9, 4053.2),       # TRIGGER: closes 4053.2 at 08:50
    ("08:50", 4053.2, 4054.1, 4050.7, 4051.5),
]
SPX_CASH = [  # New York: range 09:30-09:45 high 6824.50, low 6806.25; the 09:50 bar closes above -> long at 09:55
    ("09:30", 6812.00, 6824.50, 6806.25, 6818.40),
    ("09:35", 6818.40, 6822.10, 6809.80, 6811.30),
    ("09:40", 6811.30, 6819.60, 6807.00, 6816.90),
    ("09:45", 6816.90, 6823.80, 6814.20, 6820.15),
    ("09:50", 6820.15, 6831.40, 6819.60, 6829.70),   # TRIGGER: closes 6829.70 at 09:55
    ("09:55", 6829.70, 6833.00, 6825.10, 6827.60),
]


def btc_rows():
    """UTC day: 00:00-01:00 range high 95,880.00, low 95,210.00; the 01:10 bar closes below -> short at 01:15."""
    closes = [95500, 95620, 95700, 95790, 95640, 95520, 95400, 95300, 95450, 95560, 95480, 95420,
              95400, 95330, 95150]
    rows, o = [], 95480.0
    for i, c in enumerate(closes):
        h = max(o, c) + 40
        lo = min(o, c) - 40
        if i == 3:
            h = 95880.0
        if i == 7:
            lo = 95210.0
        if i < 12:
            h, lo = min(h, 95880.0), max(lo, 95210.0)
        rows.append(("%02d:%02d" % divmod(5 * i, 60), o, h, lo, float(c)))
        o = float(c)
    return rows


def daily_series(rng, n, start, sigma, kind):
    """Daily closes with a planted setup in the last bars."""
    c = [start]
    for _ in range(n - 1):
        c.append(c[-1] * math.exp(rng.gauss(0, sigma)))
    if kind == "breakout":
        c[-1] = max(c[-21:-1]) * (1 + 0.6 * sigma)
    elif kind == "breakdown":
        c[-1] = min(c[-21:-1]) * (1 - 0.6 * sigma)
    elif kind == "overbought":
        for i in range(n - 16, n):
            c[i] = c[i - 1] * (1 + 0.9 * sigma)
    elif kind == "oversold":
        for i in range(n - 16, n):
            c[i] = c[i - 1] * (1 - 0.9 * sigma)
    elif kind == "bounce":
        for i in range(n - 17, n - 1):
            c[i] = c[i - 1] * (1 - 0.9 * sigma)
        c[-1] = c[-2] * (1 + 0.5 * sigma)
    elif kind == "fade":
        for i in range(n - 17, n - 1):
            c[i] = c[i - 1] * (1 + 0.9 * sigma)
        c[-1] = c[-2] * (1 - 0.5 * sigma)
    elif kind == "bull_flag":
        for i in range(n - 15, n - 5):
            c[i] = c[i - 1] * (1 + 1.4 * sigma)
        top = c[n - 6]
        for i, f in zip(range(n - 5, n), (0.999, 1.0005, 0.9985, 1.001, 0.9995)):
            c[i] = top * f
    elif kind == "bear_flag":
        for i in range(n - 15, n - 5):
            c[i] = c[i - 1] * (1 - 1.4 * sigma)
        bot = c[n - 6]
        for i, f in zip(range(n - 5, n), (1.001, 0.9995, 1.0015, 0.999, 1.0005)):
            c[i] = bot * f
    elif kind == "squeeze":
        base = c[n - 21]
        for i in range(n - 20, n):
            c[i] = base * (1 + 0.08 * sigma * math.sin(i))
    elif kind == "reclaim":
        for i in range(n - 25, n - 1):
            c[i] = c[i - 1] * (1 - 0.25 * sigma)
        ma = sum(c[-21:-1]) / 20.0
        c[-1] = ma * (1 + 2.5 * sigma)
    elif kind == "lose":
        for i in range(n - 25, n - 1):
            c[i] = c[i - 1] * (1 + 0.25 * sigma)
        ma = sum(c[-21:-1]) / 20.0
        c[-1] = ma * (1 - 2.5 * sigma)
    return c


DAILY = [  # symbol, start, daily sigma, planted setup
    ("EURUSD", 1.15, 0.004, "breakout"), ("GBPUSD", 1.32, 0.005, "breakdown"),
    ("USDJPY", 150.0, 0.005, "overbought"), ("AUDUSD", 0.66, 0.006, "oversold"),
    ("USDCHF", 0.80, 0.004, None), ("XAUUSD", 3900.0, 0.010, "bull_flag"),
    ("XAGUSD", 48.0, 0.016, "squeeze"), ("USOIL", 62.0, 0.018, "bear_flag"),
    ("US500", 6700.0, 0.008, "reclaim"), ("GER40", 24000.0, 0.009, "lose"),
    ("JPN225", 48000.0, 0.011, None), ("BTCUSD", 98000.0, 0.025, "bounce"),
    ("ETHUSD", 3300.0, 0.032, "fade"), ("SOLUSD", 150.0, 0.040, None),
]


def daily_bundle():
    out = {}
    end = PLAN_DAY - datetime.timedelta(days=1)      # closes through Friday 2026-11-13 (crypto: Sunday 11-15)
    for k, (sym, start, sigma, kind) in enumerate(DAILY):
        inst = tc.resolve(sym)
        rng = random.Random(1000 + k)
        days = []
        d = end - datetime.timedelta(days=95)
        while d <= end:
            if inst["class"] == "crypto" or d.weekday() < 5:
                days.append(d)
            d += datetime.timedelta(days=1)
        closes = daily_series(rng, len(days), start, sigma, kind)
        bars = []
        sess = tc.session_def(inst["session"])
        for d, c in zip(days, closes):
            t = tc.to_utc(sess["tz"], datetime.datetime.combine(d, datetime.time(0, 0)))
            o = c * math.exp(rng.gauss(0, sigma / 3))
            bars.append([t, o, max(o, c) * (1 + sigma / 2), min(o, c) * (1 - sigma / 2), c, 0 if
                         inst["class"] == "forex" else 1000000 * (1 + rng.random())])
        # today's partial daily bar: present in Yahoo's answer, dropped by the scanner until the close
        t = tc.to_utc(sess["tz"], datetime.datetime.combine(PLAN_DAY, datetime.time(0, 0)))
        bars.append([t, closes[-1], closes[-1] * 1.001, closes[-1] * 0.999, closes[-1] * 1.0005, 0])
        doc = v8(inst["feed"], bars, inst["digits"], "1d", tc.ts_of(tc.to_utc("UTC", datetime.datetime(2026, 11, 16, 6))))
        out[inst["feed"]] = doc
    return out


def cot_records():
    """Socrata (publicreporting.cftc.gov) Legacy Futures Only rows, 160 weeks a market."""
    markets = [("099741", "EURO FX - CHICAGO MERCANTILE EXCHANGE", 40000, 30000, "high"),
               ("097741", "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE", -20000, 25000, "low"),
               ("088691", "GOLD - COMMODITY EXCHANGE INC.", 180000, 40000, None),
               ("13874A", "E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE", -60000, 80000, None),
               ("133741", "BITCOIN - CHICAGO MERCANTILE EXCHANGE", 500, 800, None)]
    rows = []
    last = datetime.date(2026, 11, 10)   # a Tuesday: the as-of date of the report released Friday 11-13
    for k, (code, name, mid, swing, plant) in enumerate(markets):
        rng = random.Random(500 + k)
        net = mid
        for w in range(159, -1, -1):
            d = last - datetime.timedelta(weeks=w)
            net += rng.gauss(0, swing / 8.0)
            net = mid + 0.92 * (net - mid)
            if plant == "high" and w == 0:
                net = mid + swing * 1.6
            if plant == "low" and w == 0:
                net = mid - swing * 1.6
            oi = abs(mid) * 4 + swing * 6
            longs = int(oi * 0.3 + max(net, 0) + 5000)
            shorts = int(longs - net)
            rows.append({"market_and_exchange_names": name, "report_date_as_yyyy_mm_dd": d.isoformat() + "T00:00:00.000",
                         "cftc_contract_market_code": code, "open_interest_all": str(int(oi)),
                         "noncomm_positions_long_all": str(longs), "noncomm_positions_short_all": str(shorts),
                         "comm_positions_long_all": str(int(oi * 0.45 - net / 2)),
                         "comm_positions_short_all": str(int(oi * 0.45 + net / 2)),
                         "nonrept_positions_long_all": str(int(oi * 0.08)),
                         "nonrept_positions_short_all": str(int(oi * 0.08))})
    rows.sort(key=lambda r: (r["cftc_contract_market_code"], r["report_date_as_yyyy_mm_dd"]))
    for i, r in enumerate(rows):
        if i and rows[i - 1]["cftc_contract_market_code"] == r["cftc_contract_market_code"]:
            p = rows[i - 1]
            r["change_in_noncomm_long_all"] = str(int(r["noncomm_positions_long_all"]) - int(p["noncomm_positions_long_all"]))
            r["change_in_noncomm_short_all"] = str(int(r["noncomm_positions_short_all"]) - int(p["noncomm_positions_short_all"]))
    return rows


CALENDAR = [  # ForexFactory weekly export shape (nfs.faireconomy.media/ff_calendar_thisweek.json); New York times
    ("Bank Holiday", "JPY", "2026-11-16T00:00:00-05:00", "Holiday", "", ""),
    ("ECB President Lagarde Speaks", "EUR", "2026-11-16T05:00:00-05:00", "High", "", ""),
    ("Empire State Manufacturing Index", "USD", "2026-11-16T08:30:00-05:00", "Medium", "-2.1", "-3.4"),
    ("RBA Monetary Policy Meeting Minutes", "AUD", "2026-11-16T19:30:00-05:00", "Medium", "", ""),
    ("CPI y/y", "GBP", "2026-11-18T02:00:00-05:00", "High", "3.4%", "3.6%"),
    ("Core Retail Sales m/m", "USD", "2026-11-17T08:30:00-05:00", "High", "0.3%", "0.2%"),
    ("Retail Sales m/m", "USD", "2026-11-17T08:30:00-05:00", "High", "0.2%", "0.4%"),
    ("FOMC Meeting Minutes", "USD", "2026-11-18T14:00:00-05:00", "High", "", ""),
    ("Crude Oil Inventories", "USD", "2026-11-18T10:30:00-05:00", "Medium", "-1.2M", "2.0M"),
    ("Unemployment Claims", "USD", "2026-11-19T08:30:00-05:00", "Medium", "221K", "218K"),
    ("Flash Manufacturing PMI", "EUR", "2026-11-20T04:00:00-05:00", "Medium", "49.6", "49.4"),
    ("Retail Sales m/m", "GBP", "2026-11-20T02:00:00-05:00", "High", "0.3%", "-0.4%"),
    ("National Core CPI y/y", "JPY", "2026-11-19T18:30:00-05:00", "Medium", "2.9%", "3.0%"),
]
NEWS = {
    "EURUSD": [("Euro firms as traders weigh ECB rate path ahead of Lagarde remarks", "2026-11-16T07:40:00Z"),
               ("Dollar slips in Asia as US yields ease", "2026-11-16T03:12:00Z"),
               ("FX week ahead: retail sales, FOMC minutes and UK CPI in focus", "2026-11-15T21:00:00Z"),
               ("EUR/USD analysis: the 1.1600 handle holds again", "2026-11-13T15:30:00Z")],
    "XAUUSD": [("Gold eases from record as dollar steadies; Fed minutes eyed", "2026-11-16T12:05:00Z"),
               ("Central bank gold buying stays strong, WGC says", "2026-11-16T09:20:00Z"),
               ("Gold ETF outflows slow for a second week", "2026-11-14T18:00:00Z")],
    "BTCUSD": [("Bitcoin slides below $95,500 as ETF flows turn negative", "2026-11-16T01:30:00Z"),
               ("SEC delays decision on another crypto ETF application", "2026-11-15T22:10:00Z"),
               ("Exchange hack drains $40 million in hot wallet exploit", "2026-11-15T16:45:00Z")],
}


def rss(items):
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<rss version="2.0"><channel>',
           "<title>Yahoo Finance (synthetic fixture)</title>"]
    for i, (title, when) in enumerate(items):
        dt = tc.parse_utc(when)
        pub = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
        out.append("<item><title>%s</title><link>https://finance.yahoo.com/news/fixture-%d</link>"
                   "<pubDate>%s</pubDate><guid>fixture-%d-%s</guid></item>"
                   % (title.replace("&", "&amp;"), i, pub, i, dt.strftime("%Y%m%d%H%M")))
    out.append("</channel></rss>")
    return "\n".join(out) + "\n"


def write_gz(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    raw = json.dumps(doc, separators=(",", ":")).encode("utf-8")
    with open(path, "wb") as fh:          # fixed mtime: the same bytes on every run
        with gzip.GzipFile(fileobj=fh, mode="wb", mtime=0, filename="") as gz:
            gz.write(raw)


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def main():
    charts = os.path.join(HERE, "charts")
    end_london = UTC(2026, 11, 16, 11, 0)
    write_gz(os.path.join(charts, "EURUSD-60d5m.json.gz"),
             build(11, "EURUSD=X", fx_open, 1.1640, 0.00011, fx_profile, 5,
                   plant_rows("Europe/London", EURUSD_LONDON), end_london))
    write_gz(os.path.join(charts, "GBPUSD-60d5m.json.gz"),
             build(12, "GBPUSD=X", fx_open, 1.3200, 0.00013, fx_profile, 5,
                   plant_rows("Europe/London", GBPUSD_LONDON), end_london, begin=UTC(2026, 11, 9, 0, 0)))
    write_gz(os.path.join(charts, "USDJPY-60d5m.json.gz"),
             build(13, "USDJPY=X", fx_open, 153.50, 0.00012, fx_profile, 3,
                   plant_rows("Europe/London", USDJPY_LONDON), end_london, begin=UTC(2026, 11, 9, 0, 0)))
    write_gz(os.path.join(charts, "XAUUSD-60d5m.json.gz"),
             build(21, "GC=F", cme_open, 3980.0, 0.00055, gold_profile, 1,
                   plant_rows("America/New_York", GOLD_COMEX), UTC(2026, 11, 16, 15, 30), vol=900))
    write_gz(os.path.join(charts, "US500-60d5m.json.gz"),
             build(31, "^GSPC", nyse_open, 6750.0, 0.0011, spx_profile, 2,
                   plant_rows("America/New_York", SPX_CASH), UTC(2026, 11, 16, 16, 0), vol=180000000))
    write_gz(os.path.join(charts, "BTCUSD-60d5m.json.gz"),
             build(41, "BTC-USD", always, 97000.0, 0.0018, btc_profile, 2,
                   plant_rows("UTC", btc_rows()), UTC(2026, 11, 16, 6, 0), vol=40000000))
    write_gz(os.path.join(HERE, "scanner", "daily-3mo1d.json.gz"), daily_bundle())
    write_text(os.path.join(HERE, "calendar", "ff_calendar_thisweek.json"),
               json.dumps([{"title": t, "country": c, "date": d, "impact": i, "forecast": f, "previous": p}
                           for t, c, d, i, f, p in CALENDAR], indent=1) + "\n")
    write_gz(os.path.join(HERE, "cot", "legacy-futures.json.gz"), cot_records())
    for sym, items in NEWS.items():
        write_text(os.path.join(HERE, "news", "yahoo-%s.xml" % sym), rss(items))
    print("fixtures written under %s" % HERE)


if __name__ == "__main__":
    main()
