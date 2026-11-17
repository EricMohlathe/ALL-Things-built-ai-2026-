import unittest

from _load import CALENDAR, CHARTS, Scratch, core, load, read, run, write

tc = core()
alerts = load("trader-alerts", "alerts")
econ = load("trader-calendar", "econ")
CAL = econ.normalize(tc.read_json(CALENDAR))


def cfg():
    c = tc.load_config(None)
    c["timezone"] = "Europe/London"
    return c


def q(price, prev=None, when="2026-11-16T09:00:00Z"):
    return {"price": price, "time": tc.parse_utc(when), "prev_close": prev, "feed": "x"}


class Rules(unittest.TestCase):
    def test_plan_alerts_follow_the_side(self):
        long_ = alerts.rules_from_plan({"symbol": "EURUSD", "side": "buy", "stop": 1.1616, "target": 1.16535,
                                        "date": "2026-11-16", "flat_by": "16:55", "tz": "Europe/London"}, cfg())
        short = alerts.rules_from_plan({"symbol": "XAUUSD", "side": "sell", "stop": 4058.75, "target": 4042.1,
                                        "date": "2026-11-16", "flat_by": "13:25", "tz": "America/New_York"}, cfg())
        self.assertEqual([(r["type"], r.get("price")) for r in long_[:2]], [("below", 1.1616), ("above", 1.16535)])
        self.assertEqual([(r["type"], r.get("price")) for r in short[:2]], [("above", 4058.75), ("below", 4042.1)])
        self.assertEqual((short[2]["at"], short[2]["tz"]), ("13:25", "America/New_York"))

    def test_price_alerts_ring_once_and_rearm(self):
        rules = [{"id": "a", "symbol": "EURUSD", "type": "above", "price": 1.165},
                 {"id": "b", "symbol": "EURUSD", "type": "above", "price": 1.165, "rearm": True}]
        now = tc.parse_now("2026-11-16 09:00 London")
        rang, st = alerts.evaluate(rules, {}, now, {"EURUSD": q(1.1652)}, None, cfg())
        self.assertEqual([r["id"] for r, _ in rang], ["a", "b"])
        rang, st = alerts.evaluate(rules, st, now, {"EURUSD": q(1.1653)}, None, cfg())
        self.assertEqual(rang, [])
        rang, st = alerts.evaluate(rules, st, now, {"EURUSD": q(1.1640)}, None, cfg())
        rang, st = alerts.evaluate(rules, st, now, {"EURUSD": q(1.1651)}, None, cfg())
        self.assertEqual([r["id"] for r, _ in rang], ["b"])

    def test_pct_session_time_and_event(self):
        rules = [{"id": "m", "symbol": "BTCUSD", "type": "pct_move", "pct": 3, "direction": "down"},
                 {"id": "s", "type": "session_open", "session": "london"},
                 {"id": "t", "type": "time", "at": "09:30", "tz": "Europe/London", "label": "check"},
                 {"id": "e", "type": "event", "currencies": ["EUR"], "impact": ["High"], "minutes": 15}]
        now = tc.parse_now("2026-11-16 09:46 London")
        rang, st = alerts.evaluate(rules, {}, now, {"BTCUSD": q(92000, 95500)}, CAL, cfg())
        self.assertEqual(sorted(r["id"] for r, _ in rang), ["e", "m", "s", "t"])
        rang, st = alerts.evaluate(rules, st, tc.parse_now("2026-11-16 09:50 London"), {"BTCUSD": q(91000, 95500)},
                                   CAL, cfg())
        self.assertEqual(rang, [])
        rang, _ = alerts.evaluate(rules, st, tc.parse_now("2026-11-17 09:46 London"), {"BTCUSD": q(91000, 95500)},
                                  CAL, cfg())
        self.assertEqual(sorted(r["id"] for r, _ in rang), ["m", "s", "t"])

    def test_clock(self):
        lines = "\n".join(alerts.clock_lines(tc.parse_now("2026-11-16 13:30 London"), cfg()))
        self.assertIn("Overlap: london + ny", lines)
        self.assertIn("OPEN   comex", lines)
        weekend = "\n".join(alerts.clock_lines(tc.parse_now("2026-11-15 12:00 London"), cfg()))
        self.assertIn("Forex: CLOSED for the weekend", weekend)


class Commands(unittest.TestCase):
    def test_quote_add_check(self):
        with Scratch():
            code, out, _ = run(alerts, ["quote", "EURUSD", "XAUUSD", "--offline", CHARTS, "--now",
                                        "2026-11-16 08:45 London", "--write"])
            self.assertEqual(code, 0)
            p = read("trader/prices.json")
            self.assertEqual(p["prices"]["EURUSD"], 1.16285)
            self.assertEqual(p["detail"]["EURUSD"]["time"], "2026-11-16T08:45:00Z")
            write("trader/plan.json", {"symbol": "EURUSD", "side": "buy", "stop": 1.1616, "target": 1.16535,
                                       "date": "2026-11-16", "flat_by": "16:55", "tz": "Europe/London"})
            run(alerts, ["add", "--from-plan"])
            self.assertEqual(len(read("trader/alerts.json")["rules"]), 3)
            code, out, _ = run(alerts, ["check", "--offline", CHARTS, "--now", "2026-11-16 08:50 London"])
            self.assertEqual(code, 1)
            code, out, _ = run(alerts, ["list"])
            self.assertIn("eurusd-plan-stop", out)


if __name__ == "__main__":
    unittest.main()
