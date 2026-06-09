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


def _cache_path(source: str, symbol: str, interval: str) -> str:
    safe = symbol.replace("/", "").replace(".", "_")
    return os.path.join(DATA_DIR, f"{source}_{safe}_{interval}.json")


def from_binance(symbol="BTCUSDT", interval="1d", limit=1000) -> list[dict]:
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol.upper()}&interval={interval}&limit={min(limit,1000)}"
    rows = json.loads(_get(url))
    # r[9] = taker buy base volume -> real per-bar order-flow (no key needed)
    return [{"t": int(r[0] // 1000), "o": float(r[1]), "h": float(r[2]),
             "l": float(r[3]), "c": float(r[4]), "v": float(r[5]),
             "bv": float(r[9]), "n": int(r[8])} for r in rows]


def from_yahoo(symbol="AAPL", interval="1d", rng="2y") -> list[dict]:
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
    # indices
    "SPX": "^GSPC", "SP500": "^GSPC", "NASDAQ": "^IXIC", "NAS100": "^NDX",
    "DOW": "^DJI", "US30": "^DJI", "DAX": "^GDAXI", "FTSE": "^FTSE", "NIKKEI": "^N225",
    "VIX": "^VIX", "DXY": "DX-Y.NYB",
}


def resolve(symbol: str) -> tuple[str, str]:
    """Return (resolved_symbol, source). Auto-routes: crypto->binance, else yahoo."""
    s = symbol.upper().strip()
    if s in ALIASES:
        return ALIASES[s], "yahoo"
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
    cp = _cache_path(source, symbol, interval)
    if use_cache and os.path.exists(cp) and (time.time() - os.path.getmtime(cp) < max_age):
        try:
            return json.load(open(cp))
        except Exception:
            pass
    if source == "binance":
        bars = from_binance(symbol, interval, limit)
    elif source == "yahoo":
        bars = from_yahoo(symbol, interval)
    elif source == "csv":
        bars = from_csv(symbol)  # symbol = path
    else:
        raise ValueError(f"unknown source: {source}")
    try:
        json.dump(bars, open(cp, "w"))
    except Exception:
        pass
    return bars
