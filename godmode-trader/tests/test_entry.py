import unittest

from _load import CHARTS, Scratch, core, load, read, run

tc = core()
entry = load("trader-entry", "entry")


def check(sym, now, **kw):
    inst = tc.resolve(sym)
    chart = tc.get_chart(inst, "5m", offline=CHARTS)
    sess = kw.pop("session", None) or inst["session"]
    zone = tc.session_def(sess)["tz"]
    return entry.evaluate(chart, inst, tc.parse_now(now, zone), session=sess, **kw)


class RangeBreakout(unittest.TestCase):
    def test_eurusd_london_long(self):
        r = check("EURUSD", "2026-11-16 08:45")
        self.assertEqual(r["status"], "triggered")
        self.assertEqual(r["range"]["high"], 1.1624)
        self.assertEqual(r["range"]["low"], 1.1608)
        self.assertEqual(r["range"]["bars"], 6)
        t = r["trigger"]
        self.assertEqual((t["side"], t["time"], t["bar_start"], t["bar_index"], t["price"]),
                         ("buy", "08:45", "08:40", 8, 1.16285))
        self.assertEqual(t["time_utc"], "2026-11-16T08:45:00Z")
        self.assertEqual(t["beyond_pips"], 4.5)
        self.assertEqual(r["flat_by"], "16:55")

    def test_a_wick_is_not_a_trigger(self):
        r = check("EURUSD", "2026-11-16 08:40")
        self.assertEqual(r["status"], "waiting")      # the 08:30 bar wicked to 1.16255, closed 1.16230
        self.assertIn("1.5 pips under the range high", r["reason"])

    def test_forming_bar_does_not_count(self):
        r = check("EURUSD", "2026-11-16 08:42")
        self.assertEqual(r["status"], "waiting")
        self.assertEqual(r["forming"]["bar_start"], "08:40")

    def test_range_still_forming(self):
        r = check("EURUSD", "2026-11-16 08:20")
        self.assertEqual((r["status"], r["phase"]), ("waiting", "forming"))
        self.assertEqual(r["range"]["bars"], 4)

    def test_one_side_only(self):
        r = check("EURUSD", "2026-11-16 08:45", side="sell")
        self.assertEqual(r["status"], "waiting")
        self.assertIsNone(r["levels"]["buy"])

    def test_gbpusd_short(self):
        t = check("GBPUSD", "2026-11-16 09:00")["trigger"]
        self.assertEqual((t["side"], t["direction"], t["time"], t["price"], t["level"]),
                         ("sell", "short", "08:40", 1.31255, 1.3129))

    def test_gold_comex_short_in_new_york_time(self):
        r = check("XAUUSD", "2026-11-16 08:50")
        self.assertEqual(r["tz"], "America/New_York")
        self.assertEqual((r["range"]["high"], r["range"]["low"]), (4062.4, 4055.1))
        t = r["trigger"]
        self.assertEqual((t["side"], t["time"], t["price"], t["time_utc"]),
                         ("sell", "08:50", 4053.2, "2026-11-16T13:50:00Z"))

    def test_us500_cash_long(self):
        t = check("US500", "2026-11-16 09:55")["trigger"]
        self.assertEqual((t["side"], t["time"], t["price"]), ("buy", "09:55", 6829.7))

    def test_bitcoin_utc_day_short(self):
        r = check("BTCUSD", "2026-11-16 01:15")
        self.assertEqual((r["range"]["high"], r["range"]["low"], r["range"]["of"]), (95880.0, 95210.0, 12))
        self.assertEqual((r["trigger"]["side"], r["trigger"]["price"]), ("sell", 95150.0))

    def test_no_trigger_expires(self):
        inst = tc.resolve("EURUSD")
        sinst = tc.instance_on("london", "2026-11-16")
        bars = []
        for i, s in enumerate(tc.slots(sinst, 300)):   # a quiet session: every close inside the range
            c = 1.1600 + (0.0004 if i % 2 else 0.0)
            bars.append({"t": tc.ts_of(s), "o": c, "h": c + 0.0002, "l": c - 0.0002, "c": c, "v": 0})
        chart = {"bars": bars, "data_time": None, "source": "test"}
        r = entry.evaluate(chart, inst, tc.parse_now("2026-11-16 16:45 London"))
        self.assertEqual(r["status"], "expired")
        self.assertIn("16:30", r["reason"])

    def test_weekend(self):
        r = check("EURUSD", "2026-11-15 12:00")
        self.assertEqual((r["status"], r["phase"]), ("no-data", "closed"))
        self.assertIn("2026-11-16 08:00 London", r["next_open"])

    def test_pre_open(self):
        r = check("XAUUSD", "2026-11-16 07:00")
        self.assertEqual(r["phase"], "pre-open")
        self.assertIn("08:20", r["reason"])

    def test_level_setup(self):
        r = check("EURUSD", "2026-11-16 08:45", setup="level", level=1.1620, side="buy")
        # the 08:05 bar closes 1.16205 > 1.16200, but no entries before the range ends at 08:30: the 08:25 bar
        self.assertEqual(r["trigger"]["bar_start"], "08:25")
        with self.assertRaises(tc.TraderError):
            check("EURUSD", "2026-11-16 08:45", setup="level", level=1.1620, side="both")

    def test_volume_filter_is_skipped_for_forex(self):
        r = check("EURUSD", "2026-11-16 08:45", min_volume_x=2.0)
        self.assertEqual(r["status"], "triggered")
        self.assertTrue(any("no volume" in n for n in r["notes"]))


class Commands(unittest.TestCase):
    def test_check_writes_entry_json(self):
        with Scratch():
            code, out, _ = run(entry, ["check", "EURUSD", "--now", "2026-11-16 08:45 London", "--offline", CHARTS,
                                       "--write"])
            self.assertEqual(code, 0)
            self.assertIn("TRIGGERED LONG 08:45 London at 1.16285", out)
            doc = read("trader/entry.json")
            self.assertEqual((doc["side"], doc["session"], doc["opening_range"]["mid"]), ("buy", "london", 1.1616))

    def test_watch_replays_bar_by_bar(self):
        with Scratch():
            code, out, _ = run(entry, ["watch", "XAUUSD", "--now", "2026-11-16 08:00 NY", "--offline", CHARTS])
            self.assertEqual(code, 0)
            self.assertIn("watching from the first bar's close at 08:25", out)
            self.assertIn("range set: high 4062.40, low 4055.10", out)
            self.assertIn("TRIGGERED SHORT", out)
            self.assertEqual(read("trader/entry.json")["side"], "sell")

    def test_watchlist(self):
        with Scratch():
            scan = load("trader-scanner", "scan")
            run(scan, ["range", "--offline", CHARTS, "--now", "2026-11-16 09:00 London"])
            code, out, _ = run(entry, ["watchlist", "--offline", CHARTS, "--now", "2026-11-16 09:00 London"])
            self.assertEqual(code, 0)
            self.assertIn("3 of 3 triggered", out)


if __name__ == "__main__":
    unittest.main()
