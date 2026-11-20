import unittest

from _load import CHARTS, Scratch, core, load, run, write

tc = core()
tm = load("trader-timemachine", "timemachine")

EURUSD_PLAN = {"symbol": "EURUSD", "side": "buy", "date": "2026-11-16", "session": "london", "entry": 1.16285,
               "stop": 1.1616, "target": 1.16535, "entry_time": "08:45", "entry_bar": 8, "setup": "range",
               "opening_range": {"high": 1.1624, "low": 1.1608, "minutes": 30}, "stop_rule": "range_mid",
               "flat_by": "16:55", "flat_by_utc": "2026-11-16T16:55:00Z", "interval": "5m"}


def machine(plan, replays=10000, seed=19, until=None, now="2026-11-16T12:00:00Z"):
    cfg = tc.load_config(None)
    p = tm.normalize_plan(plan, cfg)
    inst = tc.resolve(p["symbol"])
    chart = tc.get_chart(inst, "5m", offline=CHARTS)
    return tm.time_machine(chart, p, inst, cfg, tc.parse_now(now), replays, seed, 2, until)


class Replays(unittest.TestCase):
    def test_eurusd_numbers_are_reproducible(self):
        doc = machine(EURUSD_PLAN)
        m, h = doc["mc"], doc["history"]
        self.assertEqual((m["p_target"], m["p_stop"], m["p_neither"]), (0.1469, 0.5355, 0.3176))
        self.assertEqual((m["pool_sessions"], m["bars_left"], m["until"]), (40, 98, "16:55"))
        self.assertEqual((h["sessions"], h["triggered"], h["target"], h["stop"]), (40, 29, 6, 23))
        self.assertTrue(doc["verdict"].startswith("Leans toward the stop"))
        self.assertAlmostEqual(m["p_target"] + m["p_stop"] + m["p_neither"], 1.0, 3)

    def test_same_seed_same_numbers(self):
        a = machine(EURUSD_PLAN, replays=1500, seed=7)["mc"]
        b = machine(EURUSD_PLAN, replays=1500, seed=7)["mc"]
        c = machine(EURUSD_PLAN, replays=1500, seed=8)["mc"]
        self.assertEqual(a["p_target"], b["p_target"])
        self.assertEqual(a["bands"], b["bands"])
        self.assertNotEqual(a["sample_paths"], c["sample_paths"])

    def test_gold_short(self):
        plan = {"symbol": "XAUUSD", "side": "sell", "date": "2026-11-16", "session": "comex", "entry": 4053.2,
                "stop": 4058.75, "target": 4042.1, "entry_time": "08:50", "setup": "range"}
        doc = machine(plan, replays=3000, now="2026-11-16T16:00:00Z")
        self.assertEqual(doc["plan"]["entry_bar"], 5)
        self.assertEqual(doc["history"]["rule"]["stop_rule"], "range_mid")
        self.assertEqual((doc["mc"]["p_target"], doc["mc"]["p_stop"]), (0.3, 0.7))
        self.assertEqual(doc["mc"]["until"], "13:25")

    def test_until_close(self):
        doc = machine(EURUSD_PLAN, replays=500, until="close")
        self.assertEqual((doc["mc"]["until"], doc["mc"]["bars_left"]), ("17:00", 99))

    def test_refusals(self):
        with self.assertRaisesRegex(tc.TraderError, "stop < entry < target"):
            machine(dict(EURUSD_PLAN, stop=1.17))
        with self.assertRaisesRegex(tc.TraderError, "full london session"):
            plan = dict(EURUSD_PLAN, symbol="GBPUSD", entry=1.31255, stop=1.3138, target=1.3100, side="sell",
                        entry_time="08:40", entry_bar=None)
            plan.pop("flat_by_utc")
            machine(plan)
        with self.assertRaisesRegex(tc.TraderError, "not the close of a 5-minute bar"):
            machine(dict(EURUSD_PLAN, entry_time="08:47", entry_bar=None))
        with self.assertRaisesRegex(tc.TraderError, "not in the data"):
            machine(EURUSD_PLAN, now="2026-11-16T08:40:00Z")


class Commands(unittest.TestCase):
    def test_run_and_chart(self):
        with Scratch():
            write("trader/plan.json", EURUSD_PLAN)
            code, out, err = run(tm, ["run", "--offline", CHARTS, "--now", "2026-11-16 12:00 London", "--replays",
                                      "2000", "--write"])
            self.assertEqual(code, 0, err)
            self.assertIn("2,000 replays of the rest of the session, 08:45 to 16:55 London", out)
            code, out, _ = run(tm, ["chart", "--from"])
            self.assertEqual(code, 0)
            self.assertIn("target", out)
            self.assertIn("stop", out)


if __name__ == "__main__":
    unittest.main()
