"""The Setup Lab: the backtest engine's fill rules, no look-ahead in any setup, the statistics,
the prop-firm rules and the lab CLI, all offline."""

import datetime
import json
import os
import sys
import unittest

from _load import CHARTS, ROOT, Scratch, core, load, read, run

tc = core()
sys.path.insert(0, os.path.join(ROOT, "trader-lab"))
import engine  # noqa: E402
import stats  # noqa: E402
import prop  # noqa: E402
import setups as S  # noqa: E402
from bars import Bars  # noqa: E402

T0 = tc.ts_of(datetime.datetime(2026, 1, 5, 8, 0))
EURUSD = tc.resolve("EURUSD")


def bars_from(rows, step=300, t0=T0):
    b = Bars(step, "EURUSD")
    for k, (o, h, l, c) in enumerate(rows):
        b.append(t0 + k * step, o, h, l, c, 1.0)
    return b


def flat(n, p=1.1):
    return [(p, p + 0.0005, p - 0.0005, p)] * n


class Script(object):
    """A setup that fires the signals it is given at fixed bars."""
    defaults, grid, warmup = {}, {}, 1

    def __init__(self, at, rule=None):
        self.at, self.rule = at, rule

    def prepare(self, ctx):
        pass

    def signal(self, ctx, i):
        return self.at.get(i)

    def exit_rule(self, ctx, i, pos):
        return self.rule(ctx, i, pos) if self.rule else False


def fixture(sym):
    return Bars.from_chart(tc.get_chart(tc.resolve(sym), "5m", "60d", offline=CHARTS, tag="60d5m"), symbol=sym)


class Engine(unittest.TestCase):
    NOCOST = {"spread": 0.0}

    def test_market_entry_fills_at_the_next_open_with_half_the_spread(self):
        rows = flat(10)
        rows[3] = (1.1010, 1.1012, 1.1008, 1.1010)
        rows[4] = (1.1010, 1.1100, 1.1005, 1.1090)            # target hit
        b = bars_from(rows)
        st = Script({2: engine.Signal("buy", 1.0990, 1.1050)})
        res = engine.run(b, st, EURUSD, cfg={"spread": 0.0002})
        t = res["trades"][0]
        self.assertAlmostEqual(t["entry"], 1.1011)            # open 1.1010 + half of 2 pips... of 0.0002
        self.assertEqual(t["outcome"], "target")
        self.assertAlmostEqual(t["gross_r"], (1.1050 - 1.1011) / (1.1011 - 1.0990), places=4)
        self.assertLess(t["r"], t["gross_r"])                 # the exit half-spread is paid too

    def test_a_bar_touching_stop_and_target_is_a_loss(self):
        rows = flat(10)
        rows[3] = (1.1000, 1.1100, 1.0900, 1.1000)
        st = Script({2: engine.Signal("buy", 1.0950, 1.1050)})
        t = engine.run(bars_from(rows), st, EURUSD, cfg=self.NOCOST)["trades"][0]
        self.assertEqual(t["outcome"], "stop")
        self.assertAlmostEqual(t["r"], -1.0)

    def test_a_gap_through_the_stop_fills_at_the_open(self):
        rows = flat(10)
        rows[4] = (1.0900, 1.0910, 1.0890, 1.0900)
        st = Script({2: engine.Signal("buy", 1.0950, 1.1200)})
        t = engine.run(bars_from(rows), st, EURUSD, cfg=self.NOCOST)["trades"][0]
        self.assertEqual(t["exit"], 1.0900)
        self.assertLess(t["r"], -1.0)

    def test_limit_orders_fill_or_expire_and_both_are_logged(self):
        rows = flat(12)
        rows[5] = (1.1000, 1.1005, 1.0980, 1.0990)
        st = Script({2: engine.Signal("buy", 1.0950, 1.1100, entry=1.0985, expiry_bars=5, max_bars=2),
                     8: engine.Signal("buy", 1.0900, 1.1100, entry=1.0950, expiry_bars=2)})
        res = engine.run(bars_from(rows), st, EURUSD, cfg=self.NOCOST)
        self.assertEqual(res["trades"][0]["entry"], 1.0985)
        reasons = [s["reason"] for s in res["signals"] if not s["taken"]]
        self.assertIn("limit not filled", reasons)

    def test_signals_while_in_a_trade_are_logged_not_taken(self):
        st = Script({2: engine.Signal("buy", 1.0950, 1.1100), 3: engine.Signal("sell", 1.1100, 1.0900)})
        res = engine.run(bars_from(flat(10)), st, EURUSD, cfg=self.NOCOST)
        self.assertEqual([s["reason"] for s in res["signals"]], ["", "already in a trade"])

    def test_exit_rule_time_stop_and_break_even(self):
        st = Script({2: engine.Signal("buy", 1.0950, None, max_bars=3)})
        t = engine.run(bars_from(flat(10)), st, EURUSD, cfg=self.NOCOST)["trades"][0]
        self.assertEqual((t["outcome"], t["bars"]), ("time", 3))
        st = Script({2: engine.Signal("buy", 1.0950, None)}, rule=lambda ctx, i, pos: i >= 6)
        t = engine.run(bars_from(flat(10)), st, EURUSD, cfg=self.NOCOST)["trades"][0]
        self.assertEqual(t["outcome"], "rule")
        rows = flat(10)
        rows[4] = (1.1000, 1.1060, 1.0999, 1.1050)            # +1.2R
        rows[5] = (1.1050, 1.1051, 1.0990, 1.0995)            # back through entry
        st = Script({2: engine.Signal("buy", 1.0950, 1.1200, be_at_r=1.0)})
        t = engine.run(bars_from(rows), st, EURUSD, cfg=self.NOCOST)["trades"][0]
        self.assertEqual(t["outcome"], "be")
        self.assertAlmostEqual(t["r"], 0.0)

    def test_window_start_between_bars(self):
        b = bars_from(flat(100))
        st = Script({k: engine.Signal("buy", 1.0950, 1.1100, max_bars=1) for k in range(0, 100, 5)})
        res = engine.run(b, st, EURUSD, cfg=self.NOCOST, start=b.t[50] - 7, end=b.t[80])
        self.assertTrue(all(b.t[50] <= x["signal_t"] < b.t[80] for x in res["trades"]))


class Setups(unittest.TestCase):
    def test_registry(self):
        gm = [n for n in S.REGISTRY if n.startswith("GM")]
        self.assertEqual(len(gm), 26)
        self.assertEqual(sorted(gm), ["GM%02d" % k for k in range(1, 27)])
        self.assertIn("CT01", S.REGISTRY)
        self.assertIn("CT02", S.REGISTRY)
        for n, c in S.REGISTRY.items():
            self.assertTrue(c.title and c.family and c.tf, n)
            for k in c.grid:
                self.assertIn(k, c.defaults, "%s grid key %s has no default" % (n, k))
        self.assertEqual(len(S.grid_of(S.get("GM01"))), 8)
        with self.assertRaises(tc.TraderError):
            S.get("GM99")

    def test_every_gm_setup_names_its_mt5_and_ctrader_files(self):
        lib = os.path.join(ROOT, "..", "MT5_MasterLibrary")
        for n in sorted(S.REGISTRY):
            if not n.startswith("GM"):
                continue
            f = S.REGISTRY[n].files()
            self.assertTrue(f["mt5"].startswith("MT5_MasterLibrary/Experts/GODMODE/%s_" % n), n)
            self.assertTrue(f["ctrader"].startswith("cTrader_MasterLibrary/%s_" % n), n)
            if os.path.isdir(lib):                       # inside the full repository, the files exist
                for rel in f.values():
                    self.assertTrue(os.path.exists(os.path.join(ROOT, "..", rel)), rel)

    def test_no_setup_looks_ahead(self):
        """Signals before a cut are the same whether or not the bars after it exist."""
        full = fixture("XAUUSD").resample("15m")
        cut = int(len(full) * 0.7)
        short = full.slice(0, cut)
        inst = tc.resolve("XAUUSD")
        smt = fixture("EURUSD").resample("15m")
        for n in sorted(S.REGISTRY):
            cfg = {"smt_bars": smt}
            a = engine.run(full, S.get(n), inst, cfg=dict(cfg))["signals"]
            b = engine.run(short, S.get(n), inst, cfg=dict(cfg))["signals"]
            limit = short.t[cut - 60]          # wider than any limit order's expiry (a decision made later)
            key = lambda s: (s["t"], s["side"], s["taken"], s["reason"], s["tag"])  # noqa: E731
            self.assertEqual([key(s) for s in a if s["t"] < limit], [key(s) for s in b if s["t"] < limit], n)

    def test_every_setup_runs_on_every_class(self):
        for sym in ("EURUSD", "US500", "BTCUSD"):
            b = fixture(sym)
            inst = tc.resolve(sym)
            for n in sorted(S.REGISTRY):
                st = S.get(n)
                if inst["class"] not in st.classes:
                    continue
                res = engine.run(b if st.tf == "M5" else b.resample(st.tf), st, inst)
                for t in res["trades"]:
                    self.assertIn(t["side"], ("buy", "sell"))
                    self.assertTrue(t["outcome"] in ("stop", "target", "time", "rule", "be", "trail", "end"), n)

    def gapped(self):
        """Weekday sessions that open away from the last close, then drift back."""
        b = Bars(900, "EURUSD")
        t, p = T0, 1.1000
        for day in range(40):
            gap = 0.0030 * (1 if day % 2 else -1)
            p += gap
            for k in range(40):
                drift = -gap / 30.0 if k < 30 else 0.0
                o = p
                p += drift + 0.00002 * ((k % 3) - 1)
                b.append(t, o, max(o, p) + 0.0002, min(o, p) - 0.0002, p, 1.0)
                t += 900
            t += 3 * 3600
        return b

    def test_gap_setups_trade_real_gaps(self):
        b = self.gapped()
        for n in ("GM20", "GM23"):
            res = engine.run(b, S.get(n), EURUSD, cfg={"spread": 0.00001})
            self.assertGreater(len(res["trades"]), 5, n)
        fade = engine.run(b, S.get("GM20"), EURUSD, cfg={"spread": 0.00001})["trades"]
        self.assertGreater(sum(1 for t in fade if t["outcome"] == "target"), len(fade) // 2)

    def test_rsi2_leaves_on_its_own_rule_and_smt_needs_a_partner(self):
        b = fixture("EURUSD").resample("1h")
        res = engine.run(b, S.get("GM19"), EURUSD)
        self.assertTrue(any(t["outcome"] == "rule" for t in res["trades"]))
        res = engine.run(b, S.get("GM24"), EURUSD)
        self.assertEqual(res["trades"], [])
        self.assertIn("needs a correlated market", res["signals"][0]["reason"])


class Stats(unittest.TestCase):
    def trades(self, rs, day0=1):
        return [{"r": r, "date": "2026-01-%02d" % (day0 + k // 2), "entry_t": T0 + k * 3600, "bars": 3,
                 "mae_r": 0.5, "mfe_r": 1.0, "outcome": "target" if r > 0 else "stop", "hour_ny": k % 24}
                for k, r in enumerate(rs)]

    def test_metrics(self):
        m = stats.metrics(self.trades([2.0, -1.0, 2.0, -1.0]))
        self.assertEqual(m["win_rate"], 50.0)
        self.assertEqual(m["expectancy_r"], 0.5)
        self.assertEqual(m["profit_factor"], 2.0)
        self.assertEqual(m["payoff"], 2.0)
        self.assertEqual(m["max_dd_r"], 1.0)
        self.assertIn("too few", m["verdict"])
        self.assertEqual(stats.metrics(self.trades([1.0]))["p_value"], 1.0 - 0.5)   # one trade: no evidence
        self.assertEqual(stats.metrics([])["verdict"], "no trades")

    def test_p_values(self):
        self.assertAlmostEqual(stats.p_value(2.0, 1000), 0.0455, places=3)
        self.assertAlmostEqual(stats.p_value(2.228, 10), 0.05, places=3)          # t table, df = 10
        self.assertEqual(stats.p_value(1.0, 0), 1.0)

    def test_holm(self):
        adj = stats.holm({"a": 0.01, "b": 0.04, "c": 0.03})
        self.assertEqual(adj, {"a": 0.03, "c": 0.06, "b": 0.06})

    def test_monte_carlo_is_repeatable(self):
        rs = [1.0, -1.0, 2.0, -1.0, -1.0, 1.5] * 10
        a, b = stats.monte_carlo(rs, sims=300, seed=3), stats.monte_carlo(rs, sims=300, seed=3)
        self.assertEqual(a, b)
        self.assertLessEqual(a["max_dd_pct"]["p50"], a["max_dd_pct"]["p95"])

    def test_walk_forward_keeps_only_test_trades(self):
        day = 86400

        def window(p, t0, t1):
            return [{"r": p["edge"], "date": str(t), "entry_t": t} for t in range(t0, t1, day)]
        wf = stats.walk_forward(window, [{"edge": 0.5}, {"edge": -0.5}], 0, 40 * day, 10, 5, min_trades=1)
        self.assertEqual(len(wf["folds"]), 6)
        self.assertTrue(all(f["params"] == {"edge": 0.5} for f in wf["folds"]))
        self.assertEqual(wf["oos"]["trades"], 30)

    def test_robustness_and_tiering_and_combine(self):
        good = {"trades": 50, "expectancy_r": 1.0}
        bad = {"trades": 50, "expectancy_r": -0.2}
        r = stats.robustness([({}, good)] + [({}, bad)] * 5)
        self.assertIsNotNone(r["warning"])
        tr = stats.tiering(self.trades([-1.0] * 60 + [1.0] * 10), window=20, min_trades=20)
        self.assertGreater(tr["skipped"], 0)
        a = {"d%d" % k: (1.0 if k % 2 else -0.5) for k in range(60)}
        m = {"trades": 60, "expectancy_r": 0.25, "p_value": 0.01, "t_stat": 3.0}
        out = stats.combine({"A": m, "B": dict(m, t_stat=2.0)}, {"A": a, "B": dict(a)})
        self.assertEqual(out["portfolio"], ["A"])
        self.assertIn("correlates", out["notes"][1]["why"])


class Prop(unittest.TestCase):
    def test_ftmo_preset_and_overrides(self):
        rl = prop.rules({"preset": "ftmo_2step"})
        self.assertEqual((rl["targets_pct"], rl["daily_loss_pct"], rl["max_loss_pct"], rl["min_days"]),
                         ([10.0, 5.0], 5.0, 10.0, 4))
        self.assertEqual(prop.rules({"preset": "ftmo_2step", "daily_loss_pct": 4})["daily_loss_pct"], 4)
        with self.assertRaises(ValueError):
            prop.rules({"preset": "nope"})

    def test_guardian_daily_floor_from_the_day_start(self):
        rl = prop.rules({"preset": "ftmo_2step"})
        g = prop.guardian(rl, 100000, 101000, 99000, day_start=101000, risk_per_trade=500)
        self.assertEqual(g["daily_floor"], 96000.0)
        self.assertEqual(g["overall_floor"], 90000.0)
        self.assertEqual(g["binding_floor"], "daily")
        self.assertEqual(g["room"], 3000.0)
        self.assertEqual(g["losses_to_floor"], 6)
        self.assertEqual(g["status"], "OK")
        self.assertTrue(prop.guardian(rl, 100000, 96000, 95900, day_start=101000)["breached"])

    def test_trailing_floor_follows_the_peak(self):
        rl = prop.rules({"preset": "generic_1step"})
        g = prop.guardian(rl, 100000, 104000, 104000, day_start=104000, peak=105000)
        self.assertEqual(g["overall_floor"], 99000.0)

    def test_simulate(self):
        rl = prop.rules({"preset": "ftmo_2step"})
        win = [{"date": "2026-01-%02d" % d, "r": 1.0} for d in range(1, 11)]
        s = prop.simulate(win, rl, 1.0, sims=50)
        self.assertEqual(s["pass"], 1.0)
        self.assertEqual(s["median_days"], 10)                 # +1 % a day to +10 %
        lose = [{"date": "2026-01-%02d" % d, "r": -1.0} for d in range(1, 11)]
        self.assertEqual(prop.simulate(lose, rl, 1.0, sims=50)["fail_max"], 1.0)
        self.assertEqual(prop.simulate([{"date": "d", "r": -3.0}] * 2, rl, 1.0, sims=20)["fail_daily"], 1.0)


class LabCli(unittest.TestCase):
    def setUp(self):
        self.lab = load("trader-lab", "lab")

    def lab_run(self, *args):
        return run(self.lab, ["--offline", CHARTS] + list(args))

    def test_list(self):
        with Scratch():
            code, out, _ = run(self.lab, ["--json", "list"])
        rows = json.loads(out)
        self.assertEqual(len(rows), 28)
        self.assertEqual(rows[2]["setup"], "GM01")

    def test_run_and_save(self):
        with Scratch():
            code, out, err = self.lab_run("run", "GM01", "EURUSD", "--by", "hour", "--trades", "2", "--save")
            self.assertEqual(code, 0, err)
            self.assertIn("GM01 on EURUSD M5", out)
            self.assertIn("by hour (New York)", out)
            self.assertIn("GM01_OpeningRangeBreakout.mq5", out)
            doc = read("trader/lab/EURUSD/GM01-M5.json")
            self.assertEqual(doc["metrics"]["trades"], len(doc["trades"]))
            self.assertIn("GM01:EURUSD:M5", read("trader/lab/summary.json"))
            code, out, _ = self.lab_run("run", "GM07", "EURUSD", "--json", "--set", "k=2.5")
            self.assertEqual(json.loads(out)["params"]["k"], 2.5)

    def test_rank_reports_adjusted_p(self):
        with Scratch():
            code, out, err = self.lab_run("rank", "EURUSD", "BTCUSD", "--family", "liquidity")
        self.assertEqual(code, 0, err)
        self.assertIn("P(ADJ)", out)
        self.assertIn("by luck alone", out)
        self.assertIn("not designed for crypto: GM02@BTCUSD", out)

    def test_optimize_mc_prop_tier_portfolio(self):
        with Scratch():
            code, out, err = self.lab_run("optimize", "GM21", "XAUUSD", "--keys", "target")
            self.assertEqual(code, 0, err)
            self.assertIn("Walk-forward", out)
            code, out, err = self.lab_run("mc", "GM14", "XAUUSD", "--sims", "200", "--risk", "0.5")
            self.assertEqual(code, 0, err)
            self.assertIn("0.50% risk a trade", out)
            code, out, err = self.lab_run("prop", "GM14", "XAUUSD", "--sims", "100", "--risks", "0.5,1")
            self.assertEqual(code, 0, err)
            self.assertIn("FTMO 2-Step", out)
            code, out, err = self.lab_run("tier", "GM14", "XAUUSD")
            self.assertEqual(code, 0, err)
            code, out, err = self.lab_run("portfolio", "EURUSD", "XAUUSD", "--setups", "GM14,GM21")
            self.assertEqual(code, 0, err)
            self.assertIn("Holm-adjusted", out)

    def test_errors(self):
        with Scratch():
            code, _, err = self.lab_run("run", "GM99", "EURUSD")
            self.assertEqual(code, 1)
            self.assertIn("unknown setup", err)
            code, _, err = run(self.lab, ["run", "GM01", "EURUSD"])              # nothing cached
            self.assertEqual(code, 1)
            self.assertIn("data.py get EURUSD", err)


if __name__ == "__main__":
    unittest.main()
