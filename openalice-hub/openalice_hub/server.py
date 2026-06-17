"""
Live launcher — stdlib HTTP server. Serves the dashboard AND a JSON API so the
cockpit can actually RUN backtests/optimizations in the browser.

Loopback only (127.0.0.1). Read/analyze only — no order endpoints are exposed
over HTTP (placing orders stays in the CLI, behind the ExecutionGate).
"""
from __future__ import annotations
import os, sys, json, urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HUB)
from openalice_hub.core import data as datamod, backtest as bt, metrics as met, optimize as opt
from openalice_hub.strategies import builtin
from openalice_hub.strategies import godmode_setups  # registers 26 GM setups
from openalice_hub.core.execution_gate import ExecutionGate

DASH = os.path.join(HUB, "dashboard")


def _ann(source): return 365 if source == "binance" else 252


def _res(sym, source):
    return datamod.resolve(sym) if source == "auto" else (sym, source)


ELITE = {
    "gm_confluence":  {"market": "BTCUSDT", "stats": "PF 2.44 · 65 trd · WF +33% · 1h: PF 2.13/188 trd", "concept": "orderflow vote ensemble"},
    "gm24_poorhl":    {"market": "BTCUSDT", "stats": "PF 2.82 · 149 trd OOS",                            "concept": "auction liquidity PA"},
    "gm12_stackbear": {"market": "BTCUSDT", "stats": "PF 6.17 · 35 trd OOS · ETH PF 28 small-sample",    "concept": "footprint orderflow"},
    "gm17_lpsy":      {"market": "BTCUSDT", "stats": "PF 3.43 · 36 trd OOS",                             "concept": "Wyckoff orderflow"},
    "gm19_obreturn":  {"market": "GOLD",    "stats": "PF 21.6 · 28 trd OOS (small sample) · NQ ex:stop3/tp6", "concept": "orderblock liquidity"},
    "deity_trend":    {"market": "GOLD",    "stats": "WF +35% 3/4 folds · SILVER PF 1.95",               "concept": "CVD+breakout (orderflow+PA)"},
    "archon_orb":     {"market": "NQ",      "stats": "PF 2.56 OOS · 79 trd · DD −9% · WF +27.9% (refined ex:stop1.5/tp3/trail2)", "concept": "vol-breakout PA"},
}

# Honest per-asset-class coverage of the elite roster (validated markets only)
COVERAGE = {
    "crypto":      "gm_confluence/gm24/gm12/gm17 on BTC (+ETH)",
    "commodities": "deity_trend GOLD·SILVER, gm19 GOLD, archon_orb GOLD",
    "futures":     "archon_orb NQ (WF-validated) · ES screened",
    "indices":     "via index FUTURES: NQ=NASDAQ100, ES=SP500, YM=US30 (cash-index daily: no edge found — honest)",
    "forex":       "via FX FUTURES (real volume): deity_trend 6B PF1.41, archon_orb 6E PF1.52 (spot FX lacks volume for orderflow EAs)",
    "stocks":      "screened SPY/AAPL: NO validated edge with elite EAs on daily bars — do not trade, says the data",
    "options":     "no keyless options-chain feed exists; trade the validated underlying/futures instead, or add a paid vendor (Polygon/Tradier) key",
    "prop_firms":  "propcheck/propsize vs FTMO·Topstep·Apex·FundedNext on ANY of the above",
}


def api_strategies():
    # ELITE-gated: only validated high-PF strategies exposed in the runner
    return {"builtin": list(ELITE), "elite": ELITE, "coverage": COVERAGE, "all_count": len(builtin.REGISTRY)}


def api_backtest(q):
    sym = q.get("symbol", ["BTCUSDT"])[0]
    name = q.get("strategy", ["sma_cross"])[0]
    source = q.get("source", ["binance"])[0]
    interval = q.get("interval", ["1d"])[0]
    sym, source = _res(sym, source)
    bars = datamod.get_ohlcv(sym, source=source, interval=interval, limit=1000)
    if len(bars) < 30:
        return {"error": f"only {len(bars)} bars"}
    res = bt.run(builtin.make(name), bars, symbol=sym, gate=ExecutionGate(mode="paper"))
    m = met.compute(res, _ann(source))
    eq = res["equity_curve"]
    step = max(1, len(eq) // 200)
    return {"strategy": name, "symbol": sym, "source": source, "metrics": m,
            "equity": eq[::step], "bars": res["bars"], "trades": len(res["trades"])}


def api_optimize(q):
    sym = q.get("symbol", ["BTCUSDT"])[0]
    name = q.get("strategy", ["sma_cross"])[0]
    source = q.get("source", ["binance"])[0]
    metric = q.get("metric", ["sharpe"])[0]
    sym, source = _res(sym, source)
    bars = datamod.get_ohlcv(sym, source=source, limit=1000)
    if len(bars) < 60:
        return {"error": f"only {len(bars)} bars"}
    r = opt.grid_search(name, bars, gate=ExecutionGate(mode="paper"),
                        ann=_ann(source), metric=metric, top=12)
    return r


def api_systems(q):
    try:
        return json.load(open(os.path.join(HUB, "registry", "systems.json")))
    except Exception:
        return []


def api_roster(q):
    """Validated multi-market portfolio roster (3 presets) for the Universal Controller."""
    try:
        return json.load(open(os.path.join(HUB, "registry", "roster_meta.json")))
    except Exception:
        return {}


def api_portfolio(q):
    from openalice_hub.core import portfolio as pf
    return pf.run()


ROUTES = {"/api/strategies": lambda q: api_strategies(),
          "/api/systems": api_systems,
          "/api/roster": api_roster,
          "/api/portfolio": lambda q: api_portfolio(q),
          "/api/backtest": api_backtest, "/api/optimize": api_optimize}


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=DASH, **k)

    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path in ROUTES:
            try:
                body = json.dumps(ROUTES[u.path](urllib.parse.parse_qs(u.query)), default=str).encode()
                self.send_response(200)
            except Exception as e:
                body = json.dumps({"error": str(e)}).encode()
                self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()


def serve(port=7871, host="127.0.0.1"):
    httpd = ThreadingHTTPServer((host, port), H)
    print(f"OpenAlice Hub live launcher → http://{host}:{port}/run.html")
    print("  loopback only · read/analyze API · Ctrl-C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    serve()
