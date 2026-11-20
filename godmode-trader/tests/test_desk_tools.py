"""The desk's tools, offline: structure, prop firm, macro, DEX research, journal, the MT5
bridge (against a fake MetaTrader5 package) and the desk brief."""

import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unittest

from _load import CALENDAR, CHARTS, ROOT, Scratch, core, load, read, run, write

tc = core()
import history as hist  # noqa: E402
from bars import Bars  # noqa: E402


class Net(object):
    """Stands in for the network: url substring -> bytes."""

    def __init__(self, routes):
        self.routes, self.urls = routes, []

    def __call__(self, url, data=None):
        self.urls.append(url)
        for k, v in self.routes.items():
            if k in url:
                return v(url) if callable(v) else v
        return None

    def __enter__(self):
        self.old, self.sleep = hist.BYTES_OPENER, tc.SLEEP
        hist.BYTES_OPENER, tc.SLEEP = self, (lambda s: None)
        return self

    def __exit__(self, *exc):
        hist.BYTES_OPENER, tc.SLEEP = self.old, self.sleep


# ---------------------------------------------------------------- structure

class Structure(unittest.TestCase):
    def setUp(self):
        self.st = load("trader-structure", "structure")

    def test_read_shape_levels_and_clock(self):
        inst = tc.resolve("EURUSD")
        bars, src = hist.series(inst, "M15", offline=CHARTS)
        r = self.st.read(inst, bars, ["H1", "H4", "D1"], src)
        self.assertEqual([f["tf"] for f in r["frames"]], ["H1", "H4", "D1"])
        self.assertIn(r["base"]["bias"], ("bullish", "bearish", "neutral"))
        names = {x["name"] for x in r["levels"]}
        self.assertTrue({"PDH", "PDL", "PDC", "DO", "NYMO", "PWH", "PWL"} <= names, names)
        d = [abs(x["distance"]) for x in r["levels"]]
        self.assertEqual(d, sorted(d))
        self.assertIn(r["flow"]["delta_source"], ("clv", "measured"))
        cut = bars.slice(0, bars.last_closed_at(tc.ts_of(datetime.datetime(2026, 11, 16, 7, 0))) + 1)
        self.assertEqual(self.st.read(inst, cut, ["H1"], src)["base"]["killzone"], "london_open")   # 02:00 New York

    def test_cli(self):
        with Scratch():
            code, out, err = run(self.st, ["--offline", CHARTS, "read", "XAUUSD", "--write"])
            self.assertEqual(code, 0, err)
            self.assertIn("Timeframes: H1", out)
            self.assertIn("Order flow, CLV proxy delta, an estimate", out)
            self.assertTrue(os.path.exists("trader/structure/XAUUSD.json"))
            code, out, _ = run(self.st, ["--offline", CHARTS, "levels", "BTCUSD"])
            self.assertIn("previous day high", out)
            code, _, err = run(self.st, ["read", "EURUSD"])                 # nothing cached
            self.assertEqual(code, 1)
            self.assertIn("data.py get EURUSD", err)


# ---------------------------------------------------------------- prop firm

class PropFirm(unittest.TestCase):
    def test_challenge_flow(self):
        pf = load("trader-propfirm", "propfirm")
        with Scratch():
            run(pf, ["--now", "2026-11-16 08:00 London", "init", "--size", "100000"])
            run(pf, ["--now", "2026-11-16 15:00 London", "update", "--balance", "101000", "--equity", "100500"])
            run(pf, ["--now", "2026-11-17 09:00 London", "update", "--equity", "99000", "--traded"])
            code, out, _ = run(pf, ["--json", "status"])
            g = json.loads(out)
            self.assertEqual((g["daily_floor"], g["overall_floor"], g["room"]), (96000.0, 90000.0, 3000.0))
            self.assertEqual(g["max_risk_per_trade"], 600.0)
            self.assertEqual(g["trading_days"], 2)
            write("trader/orders.json", {"orders": [{"symbol": "EURUSD", "plan": {"max_loss": 450}},
                                                    {"symbol": "XAUUSD", "plan": {"max_loss": 900}}]})
            code, out, _ = run(pf, ["check"])
            self.assertEqual(code, 1)
            self.assertIn("order 1 EURUSD: OK", out)
            self.assertIn("order 2 XAUUSD: TOO BIG", out)
            code, out, _ = run(pf, ["--now", "2026-11-18 09:00 London", "update", "--equity", "95900"])
            self.assertEqual(code, 1)                                       # under the daily floor
            write("trader/lab.json", {"trades": [{"date": "2026-01-%02d" % (1 + k // 2), "r": 1.0 if k % 3 else -1.0}
                                                 for k in range(60)]})
            code, out, err = run(pf, ["sim", "--trades", "trader/lab.json", "--sims", "200", "--risks", "0.5,1"])
            self.assertEqual(code, 0, err)
            self.assertIn("PASS", out)

    def test_rules_text(self):
        pf = load("trader-propfirm", "propfirm")
        with Scratch():
            code, out, _ = run(pf, ["rules", "--preset", "generic_1step", "--size", "50000"])
        self.assertIn("TRAILING", out)
        self.assertIn("$5,000.00", out)


# ---------------------------------------------------------------- macro

def fred_doc():
    def monthly(n, f):
        out, y, m = [], 2024, 1
        for k in range(n):
            out.append((datetime.date(y, m, 1).isoformat(), f(k)))
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        return out

    def daily(n, f):
        d0 = datetime.date(2025, 6, 1)
        return [((d0 + datetime.timedelta(days=k)).isoformat(), f(k)) for k in range(n)]
    return {"CPIAUCSL": monthly(34, lambda k: 300 * 1.0025 ** k), "CPILFESL": monthly(34, lambda k: 310 * 1.003 ** k),
            "PCEPILFE": monthly(34, lambda k: 120 * 1.002 ** k),
            "UNRATE": monthly(34, lambda k: 4.0 if k < 28 else 4.0 + 0.25 * (k - 27)),
            "PAYEMS": monthly(34, lambda k: 158000 + 200 * k), "DFF": daily(530, lambda k: 4.33),
            "DGS2": daily(530, lambda k: 4.0 + 0.003 * k), "DGS10": daily(530, lambda k: 4.4),
            "T10Y2Y": daily(530, lambda k: -0.2), "DFII10": daily(530, lambda k: 2.0 + 0.002 * k),
            "DTWEXBGS": daily(530, lambda k: 120 + 0.02 * k), "VIXCLS": daily(530, lambda k: 30.0),
            "IR3TIB01USM156N": monthly(34, lambda k: 5.0), "IR3TIB01EZM156N": monthly(34, lambda k: 3.0 - 0.02 * k),
            "IR3TIB01JPM156N": monthly(34, lambda k: 0.1)}


class Macro(unittest.TestCase):
    def setUp(self):
        self.m = load("trader-macro", "macro")

    def test_reads(self):
        with Scratch():
            write("trader/data/macro/fred.json", fred_doc())
            data = self.m.load_fred("trader/data")
            d = self.m.dashboard(data)
            self.assertAlmostEqual(d["CPIAUCSL"]["yoy"], 100 * (1.0025 ** 12 - 1), places=6)
            self.assertTrue(d["UNRATE"]["sahm_triggered"])
            self.assertIn("inverted", " ".join(d["regime"]))
            c = self.m.dollar_compass(data)
            self.assertEqual([p["score"] for p in c["pillars"]], [1, 1, -1, 1])
            self.assertEqual(c["read"], "a dollar tailwind")
            r = self.m.differential(data, "EURUSD")
            self.assertLess(r["differential"], 0)
            self.assertIn("short EURUSD earns the carry", r["carry"])
            self.assertEqual(self.m.gold_backdrop(data)["read"], "a gold headwind")
            code, out, _ = run(self.m, ["diff", "GBPUSD"])
            self.assertEqual(code, 1)

    def test_network_reads(self):
        fng = json.dumps({"data": [{"value": "22", "value_classification": "Extreme Fear", "timestamp": "1763251200"}]})
        rss = ("<rss><channel><item><title>FOMC statement</title><link>https://example.org/a</link>"
               "<pubDate>Wed, 18 Nov 2026 19:00:00 GMT</pubDate></item></channel></rss>")
        with Scratch(), Net({"alternative.me": fng.encode(), "federalreserve.gov": rss.encode(),
                             "fredgraph.csv?id=CPIAUCSL": b"observation_date,CPIAUCSL\n2026-01-01,320.5\n"}):
            code, out, _ = run(self.m, ["feargreed"])
            self.assertIn("22 (Extreme Fear)", out)
            code, out, _ = run(self.m, ["cb", "--banks", "Fed"])
            self.assertIn("FOMC statement", out)
            code, out, _ = run(self.m, ["refresh", "CPIAUCSL"])
            self.assertEqual(code, 0)
            self.assertIn("CPIAUCSL", read("trader/data/macro/fred.json"))


# ---------------------------------------------------------------- DEX

def dex_pair(chain, addr, sym, base, price, liq, vol, buys=100, sells=90, age_h=500, ch24=2.0):
    now_ms = int(time.time() * 1000)
    return {"chainId": chain, "dexId": "raydium", "url": "https://dexscreener.com/%s/%s" % (chain, addr),
            "pairAddress": addr, "baseToken": {"symbol": sym, "address": base}, "quoteToken": {"symbol": "USDC"},
            "priceUsd": str(price), "liquidity": {"usd": liq}, "volume": {"h24": vol},
            "priceChange": {"h1": 0.5, "h24": ch24}, "txns": {"h24": {"buys": buys, "sells": sells}}, "fdv": 1e9,
            "pairCreatedAt": now_ms - age_h * 3600000}


class Dex(unittest.TestCase):
    def setUp(self):
        self.d = load("trader-dex", "dex")

    def test_labels_and_identity(self):
        now = tc.utc_now()
        rows = [self.d.row_of(p, "x", tc.iso(now), tc.ts_of(now)) for p in (
            dex_pair("solana", "A", "SOL", "So111", 180, 2e7, 5e7), dex_pair("solana", "B", "SOL", "Fake", 0.002, 3000, 900, age_h=5),
            dex_pair("ethereum", "C", "ETH", "0xeth", 3100, 9e7, 2e8), dex_pair("base", "D", "TOK", "0xt", 1, 1e6, 1e6, buys=500, sells=100))]
        self.d.classify(rows, 50000, 50000)
        lab = {r["pair_address"]: r for r in rows}
        self.assertEqual(lab["A"]["label"], "REVIEW")                     # another token calls itself SOL
        self.assertIn("same symbol", lab["A"]["flags"])
        self.assertEqual(lab["B"]["label"], "SKIP")
        self.assertIn("new pool", lab["B"]["flags"])
        self.assertEqual(lab["C"]["label"], "WATCH")
        self.assertIn("one-sided flow", lab["D"]["flags"])

    def test_scan_prompts_history(self):
        sol = {"pairs": [dex_pair("solana", "A", "SOL", "So111", 180, 2e7, 5e7)]}
        eth = {"pairs": [dex_pair("ethereum", "C", "ETH", "0xeth", 3100, 9e7, 2e8)]}
        with Scratch(), Net({"q=SOL": json.dumps(sol).encode(), "q=ETH": json.dumps(eth).encode()}) as net:
            code, out, err = run(self.d, ["scan"])
            self.assertEqual(code, 0, err)
            self.assertIn("2 rows", out)
            self.assertIn("q=SOL%2FUSDC", net.urls[0])
            code, out, _ = run(self.d, ["prompts"])
            self.assertIn("You are an AI market-research assistant in PAPER MODE.", out)
            self.assertIn("Output: REJECT / NEEDS MORE DATA / PAPER TEST ONLY.", out)
            self.assertIn('"C","ETH"', out)
            code, out, _ = run(self.d, ["history", "A"])
            self.assertIn("1 snapshots", out)
        with Scratch(), Net({}):
            code, _, err = run(self.d, ["scan"])
            self.assertEqual(code, 1)
            self.assertIn("do not invent values", err)


# ---------------------------------------------------------------- journal

class Journal(unittest.TestCase):
    def setUp(self):
        self.j = load("trader-journal", "journal")

    def test_decision_before_outcome(self):
        with Scratch():
            code, _, err = run(self.j, ["--now", "2026-11-16T08:45:00Z", "add", "--symbol", "EURUSD", "--decision", "PAPER",
                                        "--side", "buy", "--entry", "1.16285", "--stop", "1.16160", "--target", "1.16535",
                                        "--costs", "0.8pips", "--setup", "GM01"])
            self.assertEqual(code, 0, err)
            run(self.j, ["--now", "2026-11-16T08:50:00Z", "add", "--symbol", "XAUUSD", "--decision", "PAPER", "--side",
                         "sell", "--entry", "4053.2", "--stop", "4058.75", "--target", "4042.1"])
            code, _, err = run(self.j, ["add", "--symbol", "EURUSD", "--decision", "PAPER", "--side", "buy"])
            self.assertIn("needs --entry and --stop", err)
            code, _, err = run(self.j, ["add", "--symbol", "EURUSD", "--decision", "PAPER", "--side", "buy",
                                        "--entry", "1.1", "--stop", "1.2"])
            self.assertIn("wrong side", err)
            run(self.j, ["--now", "2026-11-16T12:00:00Z", "observe", "1", "--outcome", "target"])
            run(self.j, ["--now", "2026-11-16T12:00:00Z", "observe", "2", "--price", "4050"])
            code, _, err = run(self.j, ["--now", "2026-11-15T12:00:00Z", "observe", "1", "--price", "1.2"])
            self.assertIn("before the decision", err)
            rows = self.j.read_rows("trader/journal.csv")
            self.assertEqual(rows[0]["R"], "1.936")                       # 2R gross less 0.8 pips on 12.5
            self.assertTrue(rows[1]["Simulated outcome"].startswith("incomplete"))
            code, out, _ = run(self.j, ["--json", "stats"])
            st = json.loads(out)
            self.assertEqual((st["simulated_outcomes"], st["incomplete"]), (1, 1))
            self.assertEqual(st["by_setup"]["GM01"]["expectancy_r"], 1.936)
            run(self.j, ["html"])
            with open("trader/journal.html", encoding="utf-8") as fh:
                page = fh.read()
            self.assertIn("<title>Trading Journal</title>", page)
            self.assertIn("prefers-color-scheme:dark", page)
            run(self.j, ["lesson", "Costs first", "--tag", "process"])
            code, out, _ = run(self.j, ["lessons", "--tag", "process"])
            self.assertIn("[process]: Costs first", out)

    def test_imports(self):
        with Scratch():
            write("trader/plan.json", {"symbol": "EURUSD", "class": "forex", "side": "buy", "entry": 1.16285,
                                       "stop": 1.1616, "target": 1.16535, "setup": "range", "flat_by": "16:55"})
            code, out, err = run(self.j, ["from-plan"])
            self.assertEqual(code, 0, err)
            write("trader/dex/latest.json", {"file": "x.csv", "rows": [
                {"timestamp_utc": "2026-11-16T08:00:00Z", "chain": "solana", "base_symbol": "SOL", "quote_symbol": "USDC",
                 "pair_address": "A", "price_usd": 180.0, "label": "WATCH", "flags": ""},
                {"timestamp_utc": "2026-11-16T08:00:00Z", "chain": "solana", "base_symbol": "X", "quote_symbol": "USDC",
                 "pair_address": "B", "price_usd": None, "label": "SKIP", "flags": "missing price"}]})
            code, out, _ = run(self.j, ["from-dex"])
            self.assertIn("Added 1 research", out)
            rows = self.j.read_rows("trader/journal.csv")
            self.assertEqual([r["Decision"] for r in rows], ["PAPER", "WATCH"])
            self.assertEqual(rows[0]["Costs/slippage assumption"], "8e-05")   # the instrument's typical spread


# ---------------------------------------------------------------- MT5 bridge

class FakeMT5(types.ModuleType):
    ACCOUNT_TRADE_MODE_DEMO, TRADE_ACTION_DEAL, TRADE_ACTION_PENDING = 0, 1, 5
    ORDER_TYPE_BUY, ORDER_TYPE_SELL, ORDER_TYPE_BUY_LIMIT, ORDER_TYPE_SELL_LIMIT = 0, 1, 2, 3
    ORDER_TIME_GTC, ORDER_FILLING_FOK, ORDER_FILLING_IOC, ORDER_FILLING_RETURN = 0, 0, 1, 2
    TRADE_RETCODE_DONE, TIMEFRAME_M15, TIMEFRAME_M1, COPY_TICKS_ALL = 10009, 15, 1, -1

    def __init__(self, demo=True, check_ok=True):
        types.ModuleType.__init__(self, "MetaTrader5")
        self.demo, self.check_ok, self.sent = demo, check_ok, []

    def initialize(self, **kw):
        return True

    def shutdown(self):
        pass

    def last_error(self):
        return (1, "ok")

    def account_info(self):
        return types.SimpleNamespace(login=12345678, server="Broker-Demo", trade_mode=0 if self.demo else 2,
                                     currency="USD", balance=5000.0, equity=5000.0, margin=0.0, margin_free=5000.0,
                                     leverage=30)

    def terminal_info(self):
        return types.SimpleNamespace(company="Broker", connected=True, trade_allowed=True)

    def positions_get(self):
        return ()

    def orders_get(self):
        return ()

    def symbol_select(self, s, on):
        return True

    def symbol_info_tick(self, s):
        return types.SimpleNamespace(ask=1.16290, bid=1.16282)

    def symbol_info(self, s):
        return types.SimpleNamespace(filling_mode=2)

    def order_check(self, req):
        return types.SimpleNamespace(retcode=0 if self.check_ok else 10019, comment="Done" if self.check_ok else "No money")

    def order_send(self, req):
        self.sent.append(req)
        return types.SimpleNamespace(retcode=10009, order=777, price=req["price"], comment="Request executed")

    def copy_rates_range(self, sym, tf, d0, d1):
        jan = int((datetime.datetime(2026, 1, 15, 10) - datetime.datetime(1970, 1, 1)).total_seconds())
        jul = int((datetime.datetime(2026, 7, 15, 10) - datetime.datetime(1970, 1, 1)).total_seconds())
        return [{"time": t, "open": 1.1, "high": 1.2, "low": 1.0, "close": 1.15, "tick_volume": 10, "real_volume": 0}
                for t in (jan, jul)]


class Mt5Bridge(unittest.TestCase):
    """The README's EURUSD trade through budget, risk and the user's yes, then the bridge."""

    def setUp(self):
        self.old = os.getcwd()
        self.dir = tempfile.mkdtemp(prefix="godmode-mt5-")
        os.chdir(self.dir)
        os.makedirs("trader")
        with open(os.path.join(ROOT, "trader-budget", "config.example.json")) as fh:
            cfg = json.load(fh)
        cfg["broker"] = "mt5"
        write("trader/config.json", cfg)
        self.br = load("trader-mt5", "bridge")
        self.saved = sys.modules.get("MetaTrader5")

    def tearDown(self):
        if self.saved is None:
            sys.modules.pop("MetaTrader5", None)
        else:
            sys.modules["MetaTrader5"] = self.saved
        os.chdir(self.old)
        shutil.rmtree(self.dir, ignore_errors=True)

    def sh(self, folder, script, *args):
        p = subprocess.run([sys.executable, os.path.join(ROOT, folder, script)] + list(args),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def prepare(self, approve=True):
        london = "2026-11-16 08:45 London"
        self.sh("trader-calendar", "econ.py", "week", "--offline", CALENDAR, "--now", london, "--write")
        self.sh("trader-entry", "entry.py", "check", "EURUSD", "--offline", CHARTS, "--now", london, "--write")
        self.sh("trader-exit", "exit.py", "plan", "--now", london, "--write")
        self.sh("trader-budget", "size.py", "--now", london, "--write")
        self.sh("trader-risk", "check.py", "--now", london)
        if approve:
            self.sh("trader-broker", "ticket.py", "approve", "--index", "1", "--reply", "yes", "--now", london)

    def send(self, *extra, demo=True, check_ok=True):
        fake = FakeMT5(demo, check_ok)
        sys.modules["MetaTrader5"] = fake
        code, out, err = run(self.br, ["send", "--index", "1", "--today", "2026-11-16"] + list(extra))
        return code, out, err, fake

    def test_gates(self):
        self.prepare(approve=False)
        code, out, err, fake = self.send("--live")
        self.assertEqual(code, 1)
        self.assertIn("gate 3", err)
        self.assertEqual(fake.sent, [])
        self.sh("trader-broker", "ticket.py", "approve", "--index", "1", "--reply", "yes", "--now", "2026-11-16 08:45 London")
        code, out, err, fake = self.send()                                   # dry run
        self.assertEqual(code, 0, err)
        self.assertIn("order_check: accepted", out)
        self.assertIn("Dry run: nothing sent", out)
        self.assertEqual(fake.sent, [])
        code, out, err, fake = self.send("--live", demo=False)              # paper on, real money: refused
        self.assertIn("gate 4", err)
        self.assertEqual(fake.sent, [])
        code, out, err, fake = self.send("--live")                          # demo account: allowed
        self.assertEqual(code, 0, err)
        self.assertIn("SENT: MetaTrader order #777", out)
        self.assertEqual(fake.sent[0]["price"], 1.1629)                     # a buy fills at the ask
        self.assertEqual((fake.sent[0]["sl"], fake.sent[0]["tp"]), (1.1616, 1.16535))
        state = read("trader/state/broker.json")
        self.assertEqual(state["orders"][-1]["status"], "placed")
        code, out, err, fake = self.send("--live")                          # the same yes cannot send twice
        self.assertIn("gate 3", err)
        self.assertEqual(fake.sent, [])

    def test_gate_one_and_order_check(self):
        self.prepare()
        cfg = read("trader/config.json")
        cfg["broker"] = "paper"
        write("trader/config.json", cfg)
        code, out, err, fake = self.send("--live")
        self.assertIn("gate 1", err)
        cfg["broker"] = "mt5"
        write("trader/config.json", cfg)
        code, out, err, fake = self.send("--live", check_ok=False)
        self.assertIn("gate 5", err)
        self.assertEqual(fake.sent, [])

    def test_export_converts_server_time(self):
        sys.modules["MetaTrader5"] = FakeMT5()
        code, out, err = run(self.br, ["export", "EURUSD", "--tf", "M15", "--from", "2026-01-01", "--to", "2026-08-01"])
        self.assertEqual(code, 0, err)
        b = hist.load("EURUSD", "15m")
        self.assertEqual([tc.iso(tc.utc_of(t)) for t in b.t], ["2026-01-15T08:00:00Z", "2026-07-15T07:00:00Z"])

    def test_without_the_package(self):
        sys.modules["MetaTrader5"] = None
        code, out, err = run(self.br, ["status"])
        self.assertEqual(code, 1)
        self.assertIn("pip install MetaTrader5", err)


# ---------------------------------------------------------------- desk

class Desk(unittest.TestCase):
    def test_ideas_need_a_corrected_edge(self):
        desk = load("trader-desk", "desk")
        summary = {"GM03:EURUSD:M15": {"setup": "GM03", "symbol": "EURUSD", "tf": "M15", "family": "smc", "trades": 400,
                                       "expectancy_r": 0.25, "p_value": 1e-6},
                   "GM14:XAUUSD:M15": {"setup": "GM14", "symbol": "XAUUSD", "tf": "M15", "family": "liquidity",
                                       "trades": 300, "expectancy_r": 0.1, "p_value": 0.04}}
        for k in range(20):
            summary["GM%02d:US500:M15" % (k + 1)] = {"setup": "GM%02d" % (k + 1), "symbol": "US500", "tf": "M15",
                                                     "family": "x", "trades": 100, "expectancy_r": -0.1, "p_value": 0.9}
        with Scratch():
            write("trader/lab/summary.json", summary)
            run(load("trader-calendar", "econ"), ["week", "--offline", CALENDAR, "--now", "2026-11-16 07:00 London",
                                                  "--write"])
            code, out, err = run(desk, ["--offline", CHARTS, "--now", "2026-11-16 07:00 London", "brief", "EURUSD",
                                        "XAUUSD", "US500", "--write"])
            self.assertEqual(code, 0, err)
            self.assertIn("1. EURUSD GM03 M15", out)
            self.assertIn("after 22 tests", out)
            self.assertIn("ECB President Lagarde Speaks", out)
            watch = out.split("WATCH ONLY")[1]
            self.assertIn("XAUUSD", watch)                                  # p 0.04 does not survive 22 tests
            self.assertIn("no COT: run cot.py latest --write", out)
            self.assertTrue(os.path.exists("trader/brief.md"))
            code, out, _ = run(desk, ["--json", "--offline", CHARTS, "--now", "2026-11-16 07:00 London", "brief", "EURUSD"])
            d = json.loads(out)
            self.assertTrue(d["structure"]["EURUSD"]["as_of"] <= "2026-11-16T07:00:00Z")

    def test_nothing_proven(self):
        desk = load("trader-desk", "desk")
        with Scratch():
            code, out, _ = run(desk, ["--offline", CHARTS, "brief", "BTCUSD"])
        self.assertIn("None today", out)
        self.assertIn("no lab results", out)


if __name__ == "__main__":
    unittest.main()
