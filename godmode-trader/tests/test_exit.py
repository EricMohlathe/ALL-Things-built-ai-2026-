import unittest

from _load import CHARTS, Scratch, core, load, read, run, write

tc = core()
ex = load("trader-exit", "exit")
D = tc.D


class Compute(unittest.TestCase):
    def test_long_range_mid(self):
        c = ex.compute(tc.resolve("EURUSD"), "buy", 1.16285, "range_mid", None, "r", D(2), 1.1624, 1.1608)
        self.assertEqual((str(c["stop"]), str(c["target"]), str(c["risk"]), str(c["reward_risk"])),
                         ("1.16160", "1.16535", "0.00125", "2.00"))

    def test_short_rounds_the_stop_up(self):
        c = ex.compute(tc.resolve("XAUUSD"), "sell", 4053.2, "range_mid", None, "r", D(2), 4062.4, 4055.1)
        self.assertEqual((str(c["stop"]), str(c["target"]), str(c["risk"])), ("4058.75", "4042.10", "5.55"))
        c = ex.compute(tc.resolve("EURUSD"), "sell", 1.16285, "pct", D("0.1"), "r", D(1))
        self.assertEqual(str(c["stop"]), "1.16402")          # 1.164012... rounded UP, away from a short entry

    def test_range_far_and_pips(self):
        c = ex.compute(tc.resolve("BTCUSD"), "sell", 95150, "range_far", None, "r", D(2), 95880, 95210)
        self.assertEqual((str(c["stop"]), str(c["target"])), ("95880.00", "93690.00"))
        c = ex.compute(tc.resolve("USDJPY"), "sell", 154.55, "pips", D(15), "pips", D(30))
        self.assertEqual((str(c["stop"]), str(c["target"]), c["target_label"]),
                         ("154.700", "154.250", "30 pips from the entry (2.0R)"))

    def test_refusals(self):
        e = tc.resolve("EURUSD")
        with self.assertRaisesRegex(tc.TraderError, "floor"):
            ex.compute(e, "buy", 1.16285, "pips", D(2), "r", D(2))
        with self.assertRaisesRegex(tc.TraderError, "goes under"):
            ex.compute(e, "buy", 1.16285, "price", D("1.1650"), "r", D(2))
        with self.assertRaisesRegex(tc.TraderError, "goes over"):
            ex.compute(e, "sell", 1.16285, "price", D("1.1600"), "r", D(2))
        with self.assertRaisesRegex(tc.TraderError, "target"):
            ex.compute(e, "sell", 1.16285, "pips", D(10), "price", D("1.1650"))

    def test_atr(self):
        bars = [{"h": 1.0 + i * 0.001 + 0.002, "l": 1.0 + i * 0.001, "c": 1.0 + i * 0.001 + 0.001} for i in range(5)]
        atr, n = ex.atr_of(bars)
        self.assertEqual(n, 5)
        self.assertAlmostEqual(atr, 0.002)


class Plans(unittest.TestCase):
    def test_plan_from_entry_json(self):
        with Scratch():
            entry = load("trader-entry", "entry")
            run(entry, ["check", "EURUSD", "--now", "2026-11-16 08:45 London", "--offline", CHARTS, "--write"])
            code, out, _ = run(ex, ["plan", "--now", "2026-11-16 08:45 London", "--write"])
            self.assertEqual(code, 0, out)
            self.assertIn("Stop          1.16160  range midpoint", out)
            p = read("trader/plan.json")
            self.assertEqual((p["side"], p["entry"], p["stop"], p["target"], p["risk_pips"], p["flat_by"],
                              p["flat_by_utc"], p["entry_time"], p["session"]),
                             ("buy", 1.16285, 1.1616, 1.16535, 12.5, "16:55", "2026-11-16T16:55:00Z", "08:45", "london"))

    def test_atr_stop_from_the_session(self):
        with Scratch():
            entry = load("trader-entry", "entry")
            run(entry, ["check", "EURUSD", "--now", "2026-11-16 08:45 London", "--offline", CHARTS, "--write"])
            code, out, err = run(ex, ["plan", "--now", "2026-11-16 08:45 London", "--stop", "atr:1.5", "--offline",
                                      CHARTS, "--json"])
            self.assertEqual(code, 0, err)
            self.assertIn("ATR(9)", out)

    def test_untriggered_entry_is_refused(self):
        with Scratch():
            write("trader/entry.json", {"symbol": "EURUSD", "status": "waiting", "side": "both", "session": "london"})
            code, _, err = run(ex, ["plan"])
            self.assertEqual(code, 1)
            self.assertIn("not picked a side", err)

    def test_flags_and_a_late_flat_by(self):
        with Scratch():
            code, _, err = run(ex, ["plan", "--symbol", "XAUUSD", "--side", "sell", "--entry", "4053.2",
                                    "--range-high", "4062.4", "--range-low", "4055.1", "--session", "comex",
                                    "--date", "2026-11-16", "--time", "08:50", "--flat-by", "14:00"])
            self.assertEqual(code, 1)
            self.assertIn("after the COMEX", err)
            code, out, err = run(ex, ["plan", "--symbol", "XAUUSD", "--side", "sell", "--entry", "4053.2",
                                      "--range-high", "4062.4", "--range-low", "4055.1", "--session", "comex",
                                      "--date", "2026-11-16", "--time", "08:50", "--now", "2026-11-16 08:50 NY"])
            self.assertEqual(code, 0, err)
            self.assertIn("Flat by       13:25 New York", out)


if __name__ == "__main__":
    unittest.main()
