"""history: years of free market history, cached locally. Standard library only.

  dukascopy   forex, metals, indices, energy: M1 candles back to the 2000s and raw
              ticks (bid, ask, sizes). Files are LZMA-compressed binary (.bi5), one per
              day (candles) or hour (ticks). Ticks give real spreads and a tick-rule delta.
              https://datafeed.dukascopy.com/datafeed/<SYM>/<YYYY>/<MM-1>/<DD>/BID_candles_min_1.bi5
  binance     crypto klines with the TAKER-BUY volume, i.e. real aggressor delta.
              REST: https://api.binance.com/api/v3/klines (1,000 bars a request)
              bulk: https://data.binance.vision/data/spot/monthly/klines/<PAIR>/<TF>/<PAIR>-<TF>-<YYYY-MM>.zip
  histdata    forex M1 a year per file (a free form download; times are EST, UTC-5, no DST).
              Method adapted from claude-trader's download_histdata.py (MIT).
  yahoo       every class: 1m for a week, 5m/15m for 60 days, 1h for two years, daily for decades
  stooq       daily CSV for forex, metals and indices
  fred        macro series as CSV (CPI, yields, payrolls ...), see trader-macro

The cache: trader/data/<SYMBOL>/<TF>.csv (time,open,high,low,close,volume,delta; time =
bar start, unix seconds UTC). New downloads merge into it. Bigger timeframes are built
from smaller ones on demand (Bars.resample), never downloaded twice.
"""

import csv
import datetime
import io
import json
import lzma
import os
import struct
import urllib.error
import urllib.parse
import urllib.request
import zipfile

import tradercore as tc
from bars import Bars, TF, TF_NAME, tf_seconds

CACHE = os.path.join("trader", "data")
BYTES_OPENER = None   # tests swap in a fake: BYTES_OPENER(url, data=None) -> bytes or None (404)

DUKA = "https://datafeed.dukascopy.com/datafeed/%s/%04d/%02d/%02d/%s"
# our symbol -> (Dukascopy symbol, price divisor). Forex divisors are certain (1e5, JPY 1e3);
# the others are checked on decode (a wrong scale gives absurd prices and is refused).
DUKA_MAP = {"XAUUSD": ("XAUUSD", 1e3), "XAGUSD": ("XAGUSD", 1e3), "US500": ("USA500IDXUSD", 1e3),
            "US100": ("USATECHIDXUSD", 1e3), "US30": ("USA30IDXUSD", 1e3), "GER40": ("DEUIDXEUR", 1e3),
            "UK100": ("GBRIDXGBP", 1e3), "FRA40": ("FRAIDXEUR", 1e3), "EU50": ("EUSIDXEUR", 1e3),
            "JPN225": ("JPNIDXJPY", 1e3), "HK50": ("HKGIDXHKD", 1e3), "AUS200": ("AUSIDXAUD", 1e3),
            "USOIL": ("LIGHTCMDUSD", 1e3), "UKOIL": ("BRENTCMDUSD", 1e3), "BTCUSD": ("BTCUSD", 1e1),
            "ETHUSD": ("ETHUSD", 1e1)}
BINANCE = "https://api.binance.com/api/v3/klines?symbol=%s&interval=%s&startTime=%d&endTime=%d&limit=1000"
BINANCE_VISION = "https://data.binance.vision/data/spot/monthly/klines/%s/%s/%s-%s-%04d-%02d.zip"
BINANCE_TF = {60: "1m", 300: "5m", 900: "15m", 1800: "30m", 3600: "1h", 14400: "4h", 86400: "1d"}
HISTDATA_PAGE = "https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/%s/%s"
HISTDATA_POST = "https://www.histdata.com/get.php"
STOOQ = "https://stooq.com/q/d/l/?s=%s&i=d"
STOOQ_MAP = {"US500": "^spx", "US100": "^ndx", "US30": "^dji", "GER40": "^dax", "JPN225": "^nkx", "XAUUSD": "xauusd",
             "XAGUSD": "xagusd"}
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s"


class DataError(tc.TraderError):
    pass


def http_bytes(url, data=None, headers=None, timeout=60):
    """GET (or POST `data`) -> bytes; None on HTTP 404 (Dukascopy: no data that day)."""
    if BYTES_OPENER is not None:
        return BYTES_OPENER(url, data)
    h = {"User-Agent": tc.UA}
    h.update(headers or {})
    body = urllib.parse.urlencode(data).encode() if isinstance(data, dict) else data
    req = urllib.request.Request(url, data=body, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise DataError("%s answered HTTP %d" % (url.split("?")[0], e.code))
    except (urllib.error.URLError, OSError) as e:
        raise DataError("could not reach %s: %s" % (urllib.parse.urlsplit(url).netloc, getattr(e, "reason", e)))


# ---------------------------------------------------------------- the cache

def cache_path(symbol, tf, root=CACHE):
    return os.path.join(root, symbol.upper(), "%s.csv" % TF_NAME[tf_seconds(tf)])


def save(bars, root=CACHE):
    """Merge `bars` into the cache; returns the merged series."""
    p = cache_path(bars.symbol, bars.step, root)
    if os.path.exists(p):
        bars = Bars.from_csv(p, bars.symbol).merge(bars)
    bars.to_csv(p)
    return bars


def load(symbol, tf, root=CACHE, t_from=None, t_to=None):
    """The cached series at `tf`, built from the finest cached timeframe below it if needed."""
    step = tf_seconds(tf)
    sym = symbol.upper()
    p = cache_path(sym, step, root)
    if os.path.exists(p):
        b = Bars.from_csv(p, sym)
    else:
        finer = sorted(s for s in set(TF.values()) if s < step and step % s == 0 and
                       os.path.exists(cache_path(sym, s, root)))
        if not finer:
            raise DataError("no cached %s data at %s or finer in %s: download it first (data.py get %s)"
                            % (sym, TF_NAME[step], root, sym))
        b = Bars.from_csv(cache_path(sym, finer[-1], root), sym).resample(step)
    if t_from is not None or t_to is not None:
        b = b.between(t_from or 0, t_to or 2 ** 40)
    return b


def inventory(root=CACHE):
    """[{symbol, tf, bars, first, last}] of everything cached."""
    out = []
    if not os.path.isdir(root):
        return out
    for sym in sorted(os.listdir(root)):
        d = os.path.join(root, sym)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith(".csv") and f[:-4] in TF:
                b = Bars.from_csv(os.path.join(d, f), sym)
                out.append({"symbol": sym, "tf": f[:-4], "bars": len(b),
                            "first": tc.iso(tc.utc_of(b.t[0])) if len(b) else None,
                            "last": tc.iso(tc.utc_of(b.t[-1])) if len(b) else None})
    return out


def quality(bars, expect_gap_hours=72):
    """Gaps, duplicates, zero-range bars and outlier jumps in a series."""
    gaps, zero, jumps = [], 0, []
    import indicators as ind
    a = ind.atr(bars.h, bars.l, bars.c, 50)
    for i in range(1, len(bars)):
        g = bars.t[i] - bars.t[i - 1]
        if g > bars.step and g > expect_gap_hours * 3600:
            gaps.append({"after": tc.iso(tc.utc_of(bars.t[i - 1])), "hours": round(g / 3600.0, 1)})
        if bars.h[i] == bars.l[i]:
            zero += 1
        if a[i - 1] and abs(bars.o[i] - bars.c[i - 1]) > 20 * a[i - 1]:
            jumps.append({"at": tc.iso(tc.utc_of(bars.t[i])), "gap": bars.o[i] - bars.c[i - 1]})
    return {"bars": len(bars), "long_gaps": gaps[:20], "long_gap_count": len(gaps), "zero_range_bars": zero,
            "outlier_jumps": jumps[:20], "outlier_count": len(jumps)}


# ---------------------------------------------------------------- Dukascopy

def duka_symbol(inst):
    if inst["symbol"] in DUKA_MAP:
        return DUKA_MAP[inst["symbol"]]
    if inst["class"] == "forex" and inst["kind"] == "spot":
        return inst["symbol"], (1e3 if inst["quote"] == "JPY" else 1e5)
    raise DataError("Dukascopy has no mapping for %s: use --source yahoo, stooq or binance" % inst["symbol"])


def _sane(rows):
    return sum(1 for r in rows if r[3] <= min(r[1], r[2]) and max(r[1], r[2]) <= r[4]) >= 0.98 * len(rows)


def decode_candles(raw, day_start, scale):
    """BID_candles_min_1.bi5 -> [(t, o, h, l, c, v)]. Records are 24 bytes, big-endian:
    seconds into the day, open, close, low, high (int, x scale) and volume (float). The
    field order is checked on the data itself and swapped if the file says otherwise."""
    if not raw:
        return []
    data = lzma.decompress(raw)
    rows = []
    for k in range(0, len(data) - len(data) % 24, 24):
        s, a, b, c, d, v = struct.unpack(">5if", data[k:k + 24])
        rows.append((day_start + s, a / scale, b / scale, c / scale, d / scale, v))
    if not rows:
        return []
    if _sane([(r[0], r[1], r[2], r[3], r[4]) for r in rows]):          # time, open, close, low, high
        return [(r[0], r[1], r[4], r[3], r[2], r[5]) for r in rows]
    alt = [(r[0], r[1], r[4], r[3], r[2]) for r in rows]                 # as if: time, open, high, low, close
    if _sane(alt):
        return [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in rows]
    raise DataError("the Dukascopy candle file does not decode to sane OHLC: check the price scale")


def decode_ticks(raw, hour_start, scale):
    """HHh_ticks.bi5 -> [(t_ms, ask, bid, ask_vol, bid_vol)]: 20-byte big-endian records,
    milliseconds into the hour, ask, bid (int, x scale), ask and bid volume (float)."""
    if not raw:
        return []
    data = lzma.decompress(raw)
    out = []
    for k in range(0, len(data) - len(data) % 20, 20):
        ms, ask, bid, av, bv = struct.unpack(">3i2f", data[k:k + 20])
        out.append((hour_start * 1000 + ms, ask / scale, bid / scale, av, bv))
    return out


def _check_scale(bars, inst):
    """Refuse prices that cannot be this instrument (a wrong Dukascopy scale)."""
    if not len(bars):
        return
    p = bars.c[-1]
    if p <= 0 or p > 10 ** 7 or p < 100 * inst["tick"]:      # every real market trades well above 100 ticks
        raise DataError("%s decodes to %s: the price scale is wrong; pass --scale" % (inst["symbol"], p))


def fetch_dukascopy(inst, day_from, day_to, ticks=False, scale=None, progress=None):
    """M1 bars for [day_from, day_to] (dates, UTC days). ticks=True builds the M1 bars from
    the raw ticks instead: tick volume, tick-rule delta, true mid prices (24 requests a day)."""
    import orderflow
    sym, sc = duka_symbol(inst)
    sc = scale or sc
    out = Bars(60, inst["symbol"])
    d = day_from
    n = 0
    while d <= day_to:
        start = tc.ts_of(datetime.datetime.combine(d, datetime.time()))
        if not ticks:
            raw = http_bytes(DUKA % (sym, d.year, d.month - 1, d.day, "BID_candles_min_1.bi5"))
            for t, o, h, l, c, v in decode_candles(raw, start, sc):
                if v > 0 or not (o == h == l == c):
                    out.append(t, o, h, l, c, v)
        else:
            for hr in range(24):
                raw = http_bytes(DUKA % (sym, d.year, d.month - 1, d.day, "%02dh_ticks.bi5" % hr))
                bars = orderflow.tick_rule_bars(decode_ticks(raw, start + hr * 3600, sc), 60)
                for k in sorted(bars):
                    o, h, l, c, cnt, delta, _spread = bars[k]
                    out.append(k, o, h, l, c, cnt, delta)
        n += 1
        if progress and n % 30 == 0:
            progress("  dukascopy %s: %s" % (inst["symbol"], d.isoformat()))
        d += datetime.timedelta(days=1)
    _check_scale(out, inst)
    return out


# ---------------------------------------------------------------- Binance

def binance_pair(inst):
    if inst["class"] != "crypto":
        raise DataError("Binance carries crypto only, not %s" % inst["symbol"])
    return inst["base"].upper() + "USDT"


def _kline_rows(rows, step, symbol):
    """Binance kline arrays -> Bars with taker delta: buy = taker buy base volume,
    delta = 2 x taker buy - volume. Times in ms (µs in the 2025+ bulk files)."""
    out = Bars(step, symbol)
    for r in rows:
        t = int(float(r[0]))
        t = t // 1000000 if t > 10 ** 14 else t // 1000
        v, tb = float(r[5]), float(r[9])
        out.append(t, float(r[1]), float(r[2]), float(r[3]), float(r[4]), v, 2 * tb - v)
    return out


def fetch_binance(inst, tf, t_from, t_to, progress=None):
    step = tf_seconds(tf)
    if step not in BINANCE_TF:
        raise DataError("Binance intervals: %s" % ", ".join(BINANCE_TF.values()))
    pair = binance_pair(inst)
    out = Bars(step, inst["symbol"])
    cur = t_from
    while cur < t_to:
        raw = http_bytes(BINANCE % (pair, BINANCE_TF[step], cur * 1000, t_to * 1000 - 1))
        rows = json.loads(raw.decode("utf-8")) if raw else []
        if not isinstance(rows, list) or not rows:
            break
        part = _kline_rows(rows, step, inst["symbol"])
        out = out.merge(part)
        cur = part.t[-1] + step
        if progress:
            progress("  binance %s: to %s" % (pair, tc.iso(tc.utc_of(cur))))
        tc.SLEEP(0.2)
    return out


def fetch_binance_vision(inst, tf, months):
    """Monthly bulk zips (CSV inside, same columns as the REST klines). months = [(y, m)]."""
    step = tf_seconds(tf)
    pair, name = binance_pair(inst), BINANCE_TF[step]
    out = Bars(step, inst["symbol"])
    for y, m in months:
        raw = http_bytes(BINANCE_VISION % (pair, name, pair, name, y, m))
        if not raw:
            continue
        z = zipfile.ZipFile(io.BytesIO(raw))
        text = z.read(z.namelist()[0]).decode("utf-8")
        rows = [r for r in csv.reader(io.StringIO(text)) if r and r[0][:1].isdigit()]
        out = out.merge(_kline_rows(rows, step, inst["symbol"]))
    return out


# ---------------------------------------------------------------- HistData (method from claude-trader, MIT)

def parse_histdata_csv(text, symbol):
    """'YYYYMMDD HHMMSS;open;high;low;close;volume' in EST (UTC-5, no DST) -> M1 Bars (UTC)."""
    out = Bars(60, symbol)
    for line in text.splitlines():
        p = line.strip().split(";")
        if len(p) < 5:
            continue
        try:
            dt = datetime.datetime.strptime(p[0], "%Y%m%d %H%M%S")
        except ValueError:
            continue
        out.append(tc.ts_of(dt) + 5 * 3600, float(p[1]), float(p[2]), float(p[3]), float(p[4]),
                   float(p[5]) if len(p) > 5 and p[5] else 0.0)
    return out


def fetch_histdata(inst, year, month=None):
    if inst["class"] != "forex" and inst["symbol"] not in ("XAUUSD", "XAGUSD"):
        raise DataError("HistData carries forex and gold/silver, not %s" % inst["symbol"])
    pair = inst["symbol"].lower()
    period = "%04d/%d" % (year, month) if month else str(year)
    page = http_bytes(HISTDATA_PAGE % (pair, period))
    text = (page or b"").decode("utf-8", "replace")
    import re
    m = re.search(r'name="tk"[^>]*value="([^"]+)"', text) or re.search(r'value="([a-f0-9]{32})"', text)
    if not m:
        raise DataError("HistData has no download token for %s %s (no data for that period?)" % (inst["symbol"], period))
    raw = http_bytes(HISTDATA_POST, data={"tk": m.group(1), "date": str(year), "datemonth": "%04d%02d" % (
        year, month) if month else str(year), "platform": "ASCII", "timeframe": "M1", "fxpair": inst["symbol"]},
        headers={"Referer": HISTDATA_PAGE % (pair, period)})
    try:
        z = zipfile.ZipFile(io.BytesIO(raw or b""))
    except zipfile.BadZipFile:
        raise DataError("HistData did not send a zip for %s %s" % (inst["symbol"], period))
    name = next((n for n in z.namelist() if n.lower().endswith(".csv")), None)
    if not name:
        raise DataError("no CSV inside the HistData zip")
    return parse_histdata_csv(z.read(name).decode("utf-8", "replace"), inst["symbol"])


# ---------------------------------------------------------------- Yahoo, Stooq

def fetch_yahoo(inst, tf, period="max"):
    """Yahoo history at tf: 1m (period up to 7d), 5m/15m/30m (60d), 1h (730d), 1d (max)."""
    step = tf_seconds(tf)
    interval = {60: "1m", 300: "5m", 900: "15m", 1800: "30m", 3600: "60m", 86400: "1d"}.get(step)
    if interval is None:
        raise DataError("Yahoo intervals: 1m, 5m, 15m, 30m, 1h, 1d (build 4h from 1h)")
    rng = period if period != "max" else {60: "7d", 300: "60d", 900: "60d", 1800: "60d", 3600: "730d"}.get(step, "max")
    ch = tc.parse_chart(tc.yahoo_get(tc.chart_path(inst["feed"], rng, interval)), inst["feed"])
    rows = [b for b in ch["bars"] if step >= 86400 or b["t"] % step == 0]
    return Bars.from_rows(rows, step, inst["symbol"])


def parse_stooq_csv(text, symbol):
    out = Bars(86400, symbol)
    for r in csv.DictReader(io.StringIO(text)):
        try:
            d = datetime.datetime.strptime(r["Date"], "%Y-%m-%d")
            out.append(tc.ts_of(d), float(r["Open"]), float(r["High"]), float(r["Low"]), float(r["Close"]),
                       float(r.get("Volume") or 0))
        except (KeyError, ValueError):
            continue
    return out


def fetch_stooq(inst):
    code = STOOQ_MAP.get(inst["symbol"]) or (inst["symbol"].lower() if inst["class"] == "forex" else None)
    if not code:
        raise DataError("no Stooq code for %s" % inst["symbol"])
    raw = http_bytes(STOOQ % urllib.parse.quote(code))
    b = parse_stooq_csv((raw or b"").decode("utf-8", "replace"), inst["symbol"])
    if not len(b):
        raise DataError("Stooq sent no rows for %s (%s)" % (inst["symbol"], code))
    return b


# ---------------------------------------------------------------- FRED

def parse_fred_csv(text):
    """[(date, value)] from fredgraph.csv; '.' (missing) dropped."""
    out = []
    rows = list(csv.reader(io.StringIO(text)))
    for r in rows[1:]:
        if len(r) < 2 or r[1] in (".", ""):
            continue
        try:
            out.append((datetime.date.fromisoformat(r[0][:10]), float(r[1])))
        except ValueError:
            continue
    return out


def fetch_fred(series):
    raw = http_bytes(FRED % urllib.parse.quote(series))
    rows = parse_fred_csv((raw or b"").decode("utf-8", "replace"))
    if not rows:
        raise DataError("FRED sent no rows for %s" % series)
    return rows


# ---------------------------------------------------------------- one door

def auto_source(inst, tf):
    step = tf_seconds(tf)
    if inst["class"] == "crypto" and inst["kind"] == "spot":
        return "binance"
    if step >= 86400:
        return "yahoo"
    try:
        duka_symbol(inst)
        return "dukascopy"
    except DataError:
        return "yahoo"


def months_between(d0, d1):
    y, m, out = d0.year, d0.month, []
    while (y, m) <= (d1.year, d1.month):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out
