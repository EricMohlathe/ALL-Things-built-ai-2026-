"""trader-news, trader-calendar and trader-cot."""

import unittest

from _load import CALENDAR, CHARTS, COT, NEWS, Scratch, core, load, read, run, write

tc = core()
news = load("trader-news", "news")
econ = load("trader-calendar", "econ")
cot = load("trader-cot", "cot")


class News(unittest.TestCase):
    def test_tags(self):
        self.assertEqual(news.tags_for("Fed's Powell signals a rate cut as CPI cools"), ["central bank", "inflation"])
        self.assertIn("crypto risk", news.tags_for("Exchange hack drains $40 million"))
        self.assertIn("energy", news.tags_for("OPEC+ extends cuts; crude jumps"))
        self.assertEqual(news.tags_for("A quiet afternoon"), [])

    def test_parse_rss(self):
        items = news.parse_rss(open(NEWS + "/yahoo-EURUSD.xml").read())
        self.assertEqual(len(items), 4)
        self.assertEqual(items[0]["time"].isoformat(), "2026-11-16T07:40:00")

    def test_shows_each_item_once_with_events_and_the_move(self):
        with Scratch():
            write("trader/calendar.json", econ.normalize(tc.read_json(CALENDAR)))
            argv = ["--symbols", "EURUSD", "BTCUSD", "--offline", NEWS, "--charts", CHARTS, "--now",
                    "2026-11-16 08:50 London"]
            code, out, _ = run(news, argv)
            self.assertEqual(code, 0)
            self.assertIn("CALENDAR Mon 10:00  EUR High   ECB President Lagarde Speaks", out)
            self.assertIn("[crypto risk]", out)
            self.assertIn("EURUSD (euro / US dollar)  1.16310", out)
            code, out, _ = run(news, argv + ["--no-calendar"])
            self.assertIn("no new headlines since your last check", out)


class Calendar(unittest.TestCase):
    def setUp(self):
        self.cal = econ.normalize(tc.read_json(CALENDAR))

    def test_normalize_to_utc(self):
        ev = [e for e in self.cal["events"] if e["title"] == "FOMC Meeting Minutes"][0]
        self.assertEqual((ev["currency"], ev["time_utc"], ev["impact"]), ("USD", "2026-11-18T19:00:00Z", "High"))
        self.assertEqual(self.cal["events"], sorted(self.cal["events"], key=lambda e: e["time_utc"]))

    def test_blackout(self):
        cfg = tc.load_config(None)
        inside, evs = econ.blackout(self.cal, tc.resolve("EURUSD"), tc.parse_now("2026-11-16 09:45 London"), cfg)
        self.assertTrue(inside)
        self.assertEqual(evs[0]["title"], "ECB President Lagarde Speaks")
        self.assertFalse(econ.blackout(self.cal, tc.resolve("USDJPY"), tc.parse_now("2026-11-16 09:45 London"), cfg)[0])
        self.assertTrue(econ.blackout(self.cal, tc.resolve("XAUUSD"), tc.parse_now("2026-11-17 13:15 London"), cfg)[0])

    def test_currencies(self):
        cfg = tc.load_config(None)
        self.assertEqual(econ.currencies_for(["EURUSD", "GER40", "XAUUSD", "HK50"], cfg), ["EUR", "USD", "HKD", "CNY"])

    def test_commands(self):
        with Scratch():
            code, out, _ = run(econ, ["week", "--offline", CALENDAR, "--now", "2026-11-16 08:45 London",
                                      "--currencies", "GBP", "--impact", "high", "--write"])
            self.assertEqual(code, 0)
            self.assertIn("CPI y/y", out)
            self.assertEqual(len(read("trader/calendar.json")["events"]), 13)
            self.assertEqual(run(econ, ["blackout", "--symbol", "EURUSD", "--offline", CALENDAR, "--now",
                                        "2026-11-16 09:45 London"])[0], 1)
            self.assertEqual(run(econ, ["blackout", "--symbol", "EURUSD", "--offline", CALENDAR, "--now",
                                        "2026-11-16 08:45 London"])[0], 0)


class Cot(unittest.TestCase):
    def setUp(self):
        self.data = cot.parse_rows(tc.read_json(COT))

    def test_rows_and_the_index(self):
        eur = self.data["099741"]
        self.assertEqual((len(eur), eur[-1]["date"], eur[-1]["spec_net"]), (160, "2026-11-10", 88000))
        a = cot.analyse(eur, 156)
        self.assertEqual((a["cot_index"], a["crowded"], a["weeks"]), (100.0, "long", 156))

    def test_a_usd_base_pair_is_flipped(self):
        a = cot.analyse(self.data["097741"], 156)
        self.assertEqual((a["cot_index"], a["crowded"]), (0.0, "short"))          # yen futures: crowded short
        v = cot.view(tc.resolve("USDJPY"), a)
        self.assertEqual((v["bias"], v["cot_index"], v["crowded"], v["inverted"]), ("long", 100.0, "long", True))

    def test_latest_command(self):
        with Scratch():
            code, out, _ = run(cot, ["latest", "--offline", COT, "--symbols", "EURUSD,USDJPY,XAUUSD", "--write"])
            self.assertEqual(code, 0)
            self.assertIn("crowded long, flipped: JPY futures vs USDJPY", out)
            self.assertEqual([m["symbol"] for m in read("trader/cot.json")["markets"]], ["EURUSD", "USDJPY", "XAUUSD"])
            code, _, err = run(cot, ["latest", "--offline", COT, "--symbols", "GER40"])
            self.assertIn("no COT market", err)


if __name__ == "__main__":
    unittest.main()
