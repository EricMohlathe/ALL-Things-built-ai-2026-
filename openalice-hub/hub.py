#!/usr/bin/env python3
"""
OpenAlice Hub — orchestration CLI.

One coherent control surface over: platform connectors (MCP), AI backends
(Claude / Hermes-via-9router / your own), and 18 strategy/agent modules —
with ALL order placement forced through a paper-default ExecutionGate.

Run:  python3 hub.py status
      python3 hub.py connectors | ai | strategies
      python3 hub.py analyze BTCUSDT
      python3 hub.py paper BTCUSDT buy 0.1 --price 65000
      python3 hub.py add-connector --name my-broker --mcp "npx -y broker-mcp" --exec
      python3 hub.py add-ai --name mybrain --base-url http://h:1234/v1 --model m
      python3 hub.py live-arm BTCUSDT buy 0.1     # prints the human-confirm flow
"""
from __future__ import annotations
import os, sys, json, argparse

HUB = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HUB)
from openalice_hub.core.execution_gate import ExecutionGate, Order, ExecutionRefused
from openalice_hub.connectors import registry as conn
from openalice_hub.ai_backends import registry as aib
from openalice_hub.strategies.base import load_adapters
from openalice_hub.core import data as datamod, backtest as bt, metrics as met, optimize as opt
from openalice_hub.strategies import builtin
from openalice_hub import godmode as gm
from openalice_hub.strategies import godmode_setups  # registers 25 GM setups

CFG = os.path.join(HUB, "config.json")
REPOS = os.path.normpath(os.path.join(HUB, "..", "repos"))
STRAT_JSON = os.path.join(HUB, "registry", "strategies.json")


def cfg() -> dict:
    try:
        return json.load(open(CFG))
    except Exception:
        return {"mode": "paper", "live_enabled": False, "broker": {}}


def gate() -> ExecutionGate:
    c = cfg()
    return ExecutionGate(mode=c.get("mode", "paper"),
                         live_enabled=c.get("live_enabled", False),
                         broker_creds=c.get("broker", {}))


def cmd_status(a):
    c = cfg(); g = gate()
    print("=" * 60)
    print("  OpenAlice Hub")
    print("=" * 60)
    print("  Safety :", g.banner())
    print("  Mode   :", c.get("mode"), "| live_enabled:", c.get("live_enabled"))
    print("  Default AI:", c.get("default_ai"))
    print(f"  Connectors: {len(conn.list_connectors())} | "
          f"AI backends: {len(aib.list_backends())} | "
          f"Strategies: {len(load_adapters(STRAT_JSON, REPOS))}")
    print("  Repos dir:", REPOS)


def cmd_connectors(a):
    for c in conn.list_connectors():
        flag = "⚡exec" if c.get("exec_capable") else "read"
        print(f"  • {c['name']:<14} [{flag}]  {c.get('mcp_cmd') or c.get('url')}")
        print(f"      add to Claude: {conn.claude_mcp_add_line(c)}")


def cmd_ai(a):
    for b in aib.list_backends():
        st = aib.health(b) if b.get("base_url") else ("native" if b["kind"] == "native" else "no-url")
        en = "on" if b.get("enabled") else "off"
        print(f"  • {b['name']:<16} [{en}] {b['kind']:<18} model={b.get('model') or '-':<22} {st}")


def cmd_strategies(a):
    ads = load_adapters(STRAT_JSON, REPOS)
    for s in ads:
        i = s.info()
        mark = "✓" if i["installed"] else "✗"
        ex = "⚡" if i["exec_surface"] else " "
        print(f"  {mark}{ex} {s.name:<20} {s.kind:<12} {s.lang or '-':<8}")
    print(f"\n  {sum(1 for s in ads if s.installed())}/{len(ads)} repos present. "
          "⚡ = has live-order surface (routes through the gate).")
    print("\n  Built-in runnable strategies (backtest now, zero deps):")
    for name in builtin.REGISTRY:
        print(f"    ▸ {name}   ->  python3 hub.py backtest {name} BTCUSDT")


def cmd_data(a):
    bars = datamod.get_ohlcv(a.symbol, source=a.source, interval=a.interval, limit=a.limit)
    import time as _t
    if not bars:
        print("no data returned"); return
    f, l = bars[0], bars[-1]
    print(f"{a.source}:{a.symbol} {a.interval} — {len(bars)} bars")
    print(f"  {_t.strftime('%Y-%m-%d', _t.gmtime(f['t']))} … {_t.strftime('%Y-%m-%d', _t.gmtime(l['t']))}")
    print(f"  last close: {l['c']}")


def cmd_backtest(a):
    bars = datamod.get_ohlcv(a.symbol, source=a.source, interval=a.interval, limit=a.limit)
    if len(bars) < 30:
        print(f"only {len(bars)} bars — need more history"); return
    strat = builtin.make(a.strategy)
    ann = 365 if a.source == "binance" else 252
    res = bt.run(strat, bars, symbol=a.symbol, cash=a.cash, fee_bps=a.fee, gate=gate(),
                 stop_atr=a.stop, tp_atr=a.tp, trail_atr=a.trail)
    print(met.tearsheet(res, ann))
    if getattr(a, "optimize", False):
        print("\n  …optimizing in conjunction with the backtest:")
        print(opt.render(opt.grid_search(a.strategy, bars, gate=gate(), ann=ann, metric="sharpe", top=8)))


def cmd_godmode_rank(a):
    import time
    names = [n for n in sorted(builtin.REGISTRY) if n.startswith("gm")]
    bars = datamod.get_ohlcv(a.symbol, source=a.source, limit=a.limit)
    if len(bars) < 60:
        print(f"only {len(bars)} bars"); return
    ann = 365 if a.source == "binance" else 252
    bestf = os.path.join(HUB, "registry", "godmode_best.json")
    try:
        best = json.load(open(bestf))
    except Exception:
        best = {}
    rows = []
    for name in names:
        r = opt.grid_search(name, bars, gate=gate(), ann=ann, metric="sharpe", top=1)
        lb = r["leaderboard"]
        if not lb:
            continue
        top = lb[0]
        ex = opt.exit_search(name, top["params"], bars, gate=gate(), ann=ann)
        if ex and ex.get("oos_metric") is not None and (top.get("oos_metric") is None or ex["oos_metric"] > top["oos_metric"]):
            top = {**top, "oos_metric": ex["oos_metric"], "oos_return": ex["oos_return"], "exits": ex["exits"]}
        key = f"{name}|{a.symbol}"; sc = top.get("oos_metric")
        prev = best.get(key); imp = sc is not None and (prev is None or sc > prev.get("oos_metric", -1e9))
        if imp:
            best[key] = {"params": top["params"], "exits": top.get("exits") or {}, "oos_metric": sc,
                         "oos_return": top.get("oos_return"), "is_metric": top["metric"]}
        rows.append((name, top, imp))
    json.dump(best, open(bestf, "w"), indent=2)
    with open(os.path.join(HUB, "logs", "godmode_results.jsonl"), "a") as fh:
        fh.write(json.dumps({"ts": time.time(), "symbol": a.symbol,
                             "ranked": [(n, t.get("oos_metric")) for n, t, _ in rows]}) + "\n")
    rows.sort(key=lambda r: (r[1].get("oos_metric") if r[1].get("oos_metric") is not None else -1e9), reverse=True)
    print("─" * 72)
    print(f"  GODMODE rank — {a.symbol} — all {len(rows)} setups backtested + optimized")
    print(f"  {'setup':<18}{'best params':<26}{'OOS sh':>7}{'OOS ret':>9}{'IS sh':>7}  best-ever")
    print("─" * 72)
    for name, t, imp in rows:
        p = ",".join(f"{k}={v}" for k, v in t["params"].items())
        oos = f"{t['oos_metric']:.2f}" if t.get("oos_metric") is not None else "-"
        oosr = f"{t['oos_return']*100:+.0f}%" if t.get("oos_return") is not None else "-"
        ext = ",".join(f"{k.split('_')[0]}{v}" for k, v in (t.get("exits") or {}).items())
        print(f"  {name:<18}{p:<26}{oos:>7}{oosr:>9}{t['metric']:>7.2f}  {('ex:'+ext) if ext else '':<16}{'↑' if imp else ''}")
    print("─" * 72)
    print("  Ranked by OUT-OF-SAMPLE sharpe. Best-ever params persisted to registry/godmode_best.json")
    print("  → re-run on more data/symbols to keep improving each setup. PAPER. Past ≠ future.")


def cmd_godmode(a):
    print(gm.render())


def cmd_serve(a):
    from openalice_hub import server
    import webbrowser
    try:
        webbrowser.open(f"http://127.0.0.1:{a.port}/run.html")
    except Exception:
        pass
    server.serve(port=a.port)


def cmd_optimize(a):
    bars = datamod.get_ohlcv(a.symbol, source=a.source, interval=a.interval, limit=a.limit)
    if len(bars) < 60:
        print(f"only {len(bars)} bars — need more history to split train/test"); return
    ann = 365 if a.source == "binance" else 252
    res = opt.grid_search(a.strategy, bars, gate=gate(), ann=ann, metric=a.metric, top=a.top)
    print(opt.render(res))


def cmd_analyze(a):
    ads = load_adapters(STRAT_JSON, REPOS)
    print(f"Analysis plan for {a.symbol} across {len(ads)} modules (deep-wired incrementally):")
    for s in ads[:6]:
        r = s.analyze(a.symbol)
        print(f"  - {s.name}: {r['action'][:80]}")
    print("  … (full list: hub.py strategies). Wire an AI: hub.py ai")


def cmd_paper(a):
    g = gate()
    o = Order(symbol=a.symbol, side=a.side, qty=a.qty, price=a.price, connector="paper")
    try:
        print(json.dumps(g.place(o), indent=2))
    except ExecutionRefused as e:
        print("REFUSED:", e)


def cmd_live_arm(a):
    g = gate()
    o = Order(symbol=a.symbol, side=a.side, qty=a.qty, price=a.price, connector="live")
    print("Safety banner:", g.banner())
    try:
        tok = g.arm_live(o)
        print(f"\nLIVE order armed. To actually place it, a HUMAN must type this token back:")
        print(f"    TOKEN = {tok}   (expires in 120s, matches ONLY this exact order)")
        print(f"Then: place(order, confirm_token=TOKEN). No agent can self-confirm.")
    except ExecutionRefused as e:
        print("\nLIVE is locked:", e)
        print("To unlock: set live_enabled=true in config.json AND add broker creds. Still gated per-order.")


def cmd_add_connector(a):
    e = conn.add_connector(a.name, a.mcp, exec_capable=a.exec,
                           transport=a.transport, url=a.url or "")
    print("added connector:", json.dumps(e))
    print("wire into Claude:", conn.claude_mcp_add_line(e))


def cmd_add_ai(a):
    e = aib.add_backend(a.name, a.base_url, a.model, api_key=a.key or "")
    print("added AI backend:", json.dumps({k: v for k, v in e.items() if k != "api_key"}))


def main():
    p = argparse.ArgumentParser(prog="hub.py", description="OpenAlice Hub")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(f=cmd_status)
    sub.add_parser("connectors").set_defaults(f=cmd_connectors)
    sub.add_parser("ai").set_defaults(f=cmd_ai)
    sub.add_parser("strategies").set_defaults(f=cmd_strategies)
    sp = sub.add_parser("analyze"); sp.add_argument("symbol"); sp.set_defaults(f=cmd_analyze)
    sp = sub.add_parser("paper"); sp.add_argument("symbol"); sp.add_argument("side", choices=["buy", "sell"])
    sp.add_argument("qty", type=float); sp.add_argument("--price", type=float, default=None); sp.set_defaults(f=cmd_paper)
    sp = sub.add_parser("live-arm"); sp.add_argument("symbol"); sp.add_argument("side", choices=["buy", "sell"])
    sp.add_argument("qty", type=float); sp.add_argument("--price", type=float, default=None); sp.set_defaults(f=cmd_live_arm)
    sp = sub.add_parser("add-connector"); sp.add_argument("--name", required=True); sp.add_argument("--mcp", default="")
    sp.add_argument("--transport", default="stdio"); sp.add_argument("--url", default=""); sp.add_argument("--exec", action="store_true"); sp.set_defaults(f=cmd_add_connector)
    sp = sub.add_parser("add-ai"); sp.add_argument("--name", required=True); sp.add_argument("--base-url", dest="base_url", required=True)
    sp.add_argument("--model", required=True); sp.add_argument("--key", default=""); sp.set_defaults(f=cmd_add_ai)
    sp = sub.add_parser("backtest"); sp.add_argument("strategy"); sp.add_argument("symbol")
    sp.add_argument("--source", default="binance", choices=["binance", "yahoo", "csv"]); sp.add_argument("--interval", default="1d")
    sp.add_argument("--limit", type=int, default=1000); sp.add_argument("--cash", type=float, default=10000.0)
    sp.add_argument("--fee", type=float, default=10.0); sp.add_argument("--optimize", action="store_true")
    sp.add_argument("--stop", type=float, default=None); sp.add_argument("--tp", type=float, default=None)
    sp.add_argument("--trail", type=float, default=None); sp.set_defaults(f=cmd_backtest)
    sp = sub.add_parser("data"); sp.add_argument("symbol")
    sp.add_argument("--source", default="binance", choices=["binance", "yahoo", "csv"]); sp.add_argument("--interval", default="1d")
    sp.add_argument("--limit", type=int, default=1000); sp.set_defaults(f=cmd_data)
    sp = sub.add_parser("optimize"); sp.add_argument("strategy"); sp.add_argument("symbol")
    sp.add_argument("--metric", default="sharpe", choices=["sharpe", "total_return", "sortino"])
    sp.add_argument("--top", type=int, default=10); sp.add_argument("--source", default="binance", choices=["binance", "yahoo", "csv"])
    sp.add_argument("--interval", default="1d"); sp.add_argument("--limit", type=int, default=1000); sp.set_defaults(f=cmd_optimize)
    sp = sub.add_parser("serve"); sp.add_argument("--port", type=int, default=7871); sp.set_defaults(f=cmd_serve)
    sub.add_parser("godmode").set_defaults(f=cmd_godmode)
    sp = sub.add_parser("godmode-rank"); sp.add_argument("symbol")
    sp.add_argument("--source", default="binance", choices=["binance", "yahoo", "csv"])
    sp.add_argument("--limit", type=int, default=1000); sp.set_defaults(f=cmd_godmode_rank)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
