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
from openalice_hub.core.execution_gate import ExecutionGate

DASH = os.path.join(HUB, "dashboard")


def _ann(source): return 365 if source == "binance" else 252


def api_strategies():
    return {"builtin": list(builtin.REGISTRY), "grids": list(opt.GRIDS)}


def api_backtest(q):
    sym = q.get("symbol", ["BTCUSDT"])[0]
    name = q.get("strategy", ["sma_cross"])[0]
    source = q.get("source", ["binance"])[0]
    interval = q.get("interval", ["1d"])[0]
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
    bars = datamod.get_ohlcv(sym, source=source, limit=1000)
    if len(bars) < 60:
        return {"error": f"only {len(bars)} bars"}
    r = opt.grid_search(name, bars, gate=ExecutionGate(mode="paper"),
                        ann=_ann(source), metric=metric, top=12)
    return r


ROUTES = {"/api/strategies": lambda q: api_strategies(),
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
