"""
OHLCV data layer — pure stdlib, no API keys.

Sources:
  binance : crypto, public klines (reliable, no key)   e.g. BTCUSDT, ETHUSDT
  yahoo   : stocks/ETF/FX, chart endpoint (best-effort) e.g. AAPL, SPY
  csv     : local file with columns date,open,high,low,close,volume

Returns a list of bars: {"t": epoch_s, "o","h","l","c","v": float}
Caches under <hub>/data/.
"""
from __future__ import annotations
import os, json, csv, time, urllib.request, urllib.parse

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)
_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) OpenAliceHub/1.0"}


def _get(url: str, timeout: float = 15.0) -> bytes:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _cache_path(source: str, symbol: str, interval: str, limit: int = 1000) -> str:
    safe = symbol.replace("/", "").replace(".", "_").replace("^","i").replace("=","_")
    return os.path.join(DATA_DIR, f"{source}_{safe}_{interval}_{limit}.json")


def from_binance(symbol="BTCUSDT", interval="1d", limit=1000) -> list[dict]:
    rows = []
    end = ""
    while len(rows) < limit:
        n = min(1000, limit - len(rows))
        url = (f"https://api.binance.com/api/v3/klines?symbol={symbol.upper()}"
               f"&interval={interval}&limit={n}{end}")
        chunk = json.loads(_get(url))
        if not chunk:
            break
        rows = chunk + rows
        if len(chunk) < n:
            break
        end = f"&endTime={chunk[0][0]-1}"
    # r[9] = taker buy base volume -> real per-bar order-flow (no key needed)
    return [{"t": int(r[0] // 1000), "o": float(r[1]), "h": float(r[2]),
             "l": float(r[3]), "c": float(r[4]), "v": float(r[5]),
             "bv": float(r[9]), "n": int(r[8])} for r in rows]


def from_yahoo(symbol="AAPL", interval="1d", rng="10y") -> list[dict]:
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(symbol)}?range={rng}&interval={interval}")
    d = json.loads(_get(url))
    res = d["chart"]["result"][0]
    ts = res["timestamp"]
    q = res["indicators"]["quote"][0]
    out = []
    for i, t in enumerate(ts):
        o, h, l, c, v = q["open"][i], q["high"][i], q["low"][i], q["close"][i], q["volume"][i]
        if None in (o, h, l, c):
            continue
        out.append({"t": int(t), "o": float(o), "h": float(h), "l": float(l),
                    "c": float(c), "v": float(v or 0)})
    return out


def from_csv(path: str) -> list[dict]:
    out = []
    with open(path) as fh:
        for row in csv.DictReader(fh):
            row = {k.lower().strip(): v for k, v in row.items()}
            try:
                t = int(time.mktime(time.strptime(row.get("date", row.get("time", "")[:10]), "%Y-%m-%d")))
            except Exception:
                t = 0
            out.append({"t": t, "o": float(row["open"]), "h": float(row["high"]),
                        "l": float(row["low"]), "c": float(row["close"]),
                        "v": float(row.get("volume", 0) or 0)})
    return out


# plain-name aliases -> Yahoo tickers (forex, commodities, indices)
ALIASES = {
    # forex majors/crosses
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X", "USDCHF": "USDCHF=X",
    "AUDUSD": "AUDUSD=X", "NZDUSD": "NZDUSD=X", "USDCAD": "USDCAD=X", "EURGBP": "EURGBP=X",
    "EURJPY": "EURJPY=X", "GBPJPY": "GBPJPY=X", "USDZAR": "USDZAR=X", "EURZAR": "EURZAR=X",
    # commodities (front-month futures)
    "GOLD": "GC=F", "XAUUSD": "GC=F", "SILVER": "SI=F", "XAGUSD": "SI=F",
    "OIL": "CL=F", "WTI": "CL=F", "BRENT": "BZ=F", "NATGAS": "NG=F",
    "COPPER": "HG=F", "PLATINUM": "PL=F", "PALLADIUM": "PA=F",
    "WHEAT": "ZW=F", "CORN": "ZC=F", "COFFEE": "KC=F", "SUGAR": "SB=F", "COCOA": "CC=F",
    # futures (CME/CBOT front-month via Yahoo)
    "ES": "ES=F", "MES": "ES=F", "SP500FUT": "ES=F",
    "NQ": "NQ=F", "MNQ": "NQ=F", "YM": "YM=F", "MYM": "YM=F",
    "RTY": "RTY=F", "M2K": "RTY=F",
    "ZB": "ZB=F", "ZN": "ZN=F", "ZF": "ZF=F",            # bonds/notes
    "6E": "6E=F", "6B": "6B=F", "6J": "6J=F", "6A": "6A=F", "6C": "6C=F",  # FX futures
    "BTCFUT": "BTC=F", "ETHFUT": "ETH=F",
    # indices
    "SPX": "^GSPC", "SP500": "^GSPC", "NASDAQ": "^IXIC", "NAS100": "^NDX",
    "DOW": "^DJI", "US30": "^DJI", "DAX": "^GDAXI", "FTSE": "^FTSE", "NIKKEI": "^N225",
    "VIX": "^VIX", "DXY": "DX-Y.NYB",
    # Deriv synthetics (source=deriv)
    "VIX75": "R_75", "V75": "R_75", "VIX100": "R_100", "V100": "R_100",
    "VIX50": "R_50", "VIX25": "R_25", "VIX10": "R_10",
    "BOOM500": "BOOM500", "BOOM1000": "BOOM1000",
    "CRASH500": "CRASH500", "CRASH1000": "CRASH1000",
}
DERIV_SYMBOLS = {"R_75","R_100","R_50","R_25","R_10","BOOM500","BOOM1000","CRASH500","CRASH1000","1HZ75V"}


def resolve(symbol: str) -> tuple[str, str]:
    """Return (resolved_symbol, source). Auto-routes: crypto->binance, else yahoo."""
    s = symbol.upper().strip()
    if s in ALIASES:
        r = ALIASES[s]
        return r, ("deriv" if r in DERIV_SYMBOLS else "yahoo")
    if s in DERIV_SYMBOLS:
        return s, "deriv"
    if s.endswith(("USDT", "USDC", "BUSD")) and "=" not in s and "-" not in s:
        return s, "binance"
    if s.endswith("=X") or s.endswith("=F") or s.startswith("^") or "-" in s:
        return s, "yahoo"
    # 6-letter FX pair typed plain (e.g. EURNOK)
    if len(s) == 6 and s.isalpha():
        return s + "=X", "yahoo"
    return s, "yahoo"   # stocks/ETFs default


def get_ohlcv(symbol: str, source="binance", interval="1d", limit=1000,
              use_cache=True, max_age=3600) -> list[dict]:
    if source == "auto":
        symbol, source = resolve(symbol)
    cp = _cache_path(source, symbol, interval, limit)
    if use_cache and os.path.exists(cp) and (time.time() - os.path.getmtime(cp) < max_age):
        try:
            return json.load(open(cp))
        except Exception:
            pass
    if source == "binance":
        bars = from_binance(symbol, interval, limit)
    elif source == "yahoo":
        bars = from_yahoo(symbol, interval)
    elif source == "deriv":
        from . import deriv as _dv
        gran = {"1d": 86400, "4h": 14400, "1h": 3600, "15m": 900, "5m": 300, "1m": 60}.get(interval, 86400)
        bars = _dv.get_candles(symbol, granularity=gran, count=limit)
    elif source == "csv":
        bars = from_csv(symbol)  # symbol = path
    else:
        raise ValueError(f"unknown source: {source}")
    try:
        json.dump(bars, open(cp, "w"))
    except Exception:
        pass
    return bars
