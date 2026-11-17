import copy
import unittest

from _load import CALENDAR, Scratch, core, load, read, run, write

tc = core()
risk = load("trader-risk", "check")
econ = load("trader-calendar", "econ")

PLAN = {"entry": 1.16285, "stop": 1.1616, "target": 1.16535, "max_loss": 50.0, "currency": "USD", "conversion": 1.0,
        "session": "london", "date": "2026-11-16"}
EURUSD = {"symbol": "EURUSD", "class": "forex", "kind": "spot", "side": "buy", "type": "market",
          "time_in_force": "day", "lots": "0.40", "units": "40000", "stop_loss": "1.16160", "take_profit": "1.16535",
          "order_class": "bracket", "plan": PLAN}
CAL = econ.normalize(tc.read_json(CALENDAR))


def cfg(**over):
    c = tc.load_config(None)
    c.update({"balance": 5000, "timezone": "Europe/London"})
    c.update(over)
    return c


def check(orders, when="2026-11-16 08:45 London", portfolio=None, calendar=CAL, state=None, **over):
    return risk.check(orders, cfg(**over), portfolio, {}, None, {}, state, calendar, tc.parse_now(when))


def order(**kw):
    o = copy.deepcopy(EURUSD)
    plan = kw.pop("plan", None)
    o.update(kw)
    if plan:
        o["plan"].update(plan)
    return o


class Entries(unittest.TestCase):
    def test_the_example_passes(self):
        r = check([EURUSD])
        self.assertEqual((r["pass"], r["block"]), (1, 0))
        res = r["results"][0]
        self.assertEqual((res["kind"], res["max_loss"], res["notional"], res["margin"]), ("entry", 50.0, 46514.0, 1550.47))
        self.assertTrue(any("ECB" in w for w in res["warnings"]))
        self.assertEqual(r["account"]["exposure_after"], {"EUR": 46514.0})

    def test_news_blackout(self):
        res = check([EURUSD], "2026-11-16 09:45 London")["results"][0]
        self.assertEqual(res["verdict"], "BLOCK")
        self.assertTrue(any(x.startswith("news: EUR ECB President Lagarde Speaks at 10:00 London") for x in res["reasons"]))
        self.assertEqual(check([EURUSD], "2026-11-16 09:45 London", news_blackout_minutes=0)["block"], 0)

    def test_no_calendar_is_a_warning(self):
        res = check([EURUSD], calendar=None)["results"][0]
        self.assertEqual(res["verdict"], "PASS")
        self.assertTrue(any("no economic calendar" in w for w in res["warnings"]))

    def test_session_window(self):
        for when, why in (("2026-11-16 08:20 London", "no new entries before 08:30"),
                          ("2026-11-16 16:40 London", "no new entries after 16:30"),
                          ("2026-11-16 07:00 London", "not open yet"),
                          ("2026-11-15 12:00 London", "does not trade today (weekend)")):
            res = check([EURUSD], when)["results"][0]
            self.assertEqual(res["verdict"], "BLOCK", when)
            self.assertTrue(any(why in x for x in res["reasons"]), (when, res["reasons"]))

    def test_loss_and_reward_risk(self):
        res = check([order(lots="0.50", units="50000", plan={"max_loss": 62.5})])["results"][0]
        self.assertTrue(any(x.startswith("loss: ") for x in res["reasons"]))
        res = check([order(take_profit="1.16350")])["results"][0]
        self.assertTrue(any(x.startswith("reward:risk") for x in res["reasons"]))
        res = check([order(stop_loss="1.16400")])["results"][0]
        self.assertTrue(any("must be below" in x for x in res["reasons"]))

    def test_exposure_stacks_across_orders(self):
        eurgbp = order(symbol="EURGBP", lots="0.05", units="5000", stop_loss="0.88200", take_profit="0.88800",
                       plan={"entry": 0.8840, "stop": 0.882, "target": 0.888})
        r = risk.check([EURUSD, eurgbp], cfg(), None, {}, None, {"GBPUSD": 1.315}, None, CAL,
                       tc.parse_now("2026-11-16 08:45 London"))
        self.assertEqual(r["results"][0]["verdict"], "PASS")
        second = r["results"][1]
        self.assertEqual(second["verdict"], "BLOCK")
        self.assertTrue(any(x.startswith("exposure: net long EUR") for x in second["reasons"]), second["reasons"])
        self.assertTrue(any(x.startswith("leverage:") for x in second["reasons"]))

    def test_shorts(self):
        short = order(side="sell", stop_loss="1.16410", take_profit="1.16035",
                      plan={"stop": 1.1641, "target": 1.16035})
        self.assertEqual(check([short])["block"], 0)
        res = check([short], allow_short=False)["results"][0]
        self.assertTrue(any(x.startswith("short:") for x in res["reasons"]))

    def test_brokers_and_classes(self):
        res = check([EURUSD], broker="alpaca")["results"][0]
        self.assertTrue(any("is not something Alpaca" in x for x in res["reasons"]))
        res = check([EURUSD], allowed_classes=["crypto"])["results"][0]
        self.assertTrue(any(x.startswith("asset:") for x in res["reasons"]))
        btc = order(symbol="BTCUSD", side="sell", lots="0.01", units="0.01", stop_loss="95880.00",
                    take_profit="93690.00", time_in_force="gtc",
                    plan={"entry": 95150, "stop": 95880, "target": 93690, "session": "utc"})
        res = check([btc], "2026-11-16 01:20 London", broker="alpaca", leverage={})["results"][0]
        self.assertTrue(any("cannot short BTCUSD" in x for x in res["reasons"]))

    def test_format(self):
        res = check([order(lots="0.405", units="40500")])["results"][0]
        self.assertTrue(any("lot" in x and "step" in x for x in res["reasons"]))
        res = check([order(lots="0.40", units="4000")])["results"][0]
        self.assertTrue(any("contract" in x for x in res["reasons"]))
        res = check([order(symbol="NOPE")])["results"][0]
        self.assertTrue(any(x.startswith("format: unknown instrument") for x in res["reasons"]))

    def test_daily_limits_from_the_log(self):
        state = {"orders": [{"status": "placed", "date": "2026-11-16", "symbol": "GBPUSD", "side": "buy",
                             "kind": "entry", "max_loss": 50.0} for _ in range(3)]}
        res = check([EURUSD], state=state)["results"][0]
        self.assertTrue(any(x.startswith("trades:") for x in res["reasons"]))
        self.assertTrue(any(x.startswith("daily loss:") for x in res["reasons"]))
        self.assertEqual(check([EURUSD, EURUSD])["results"][1]["verdict"], "BLOCK")   # duplicate


class Exits(unittest.TestCase):
    def test_an_exit_is_never_blocked_by_the_rules(self):
        pf = {"currency": "USD", "balance": 5000, "positions": [{"symbol": "EURUSD", "units": 40000, "avg_price": 1.16285}]}
        close = {"symbol": "EURUSD", "side": "sell", "type": "market", "time_in_force": "day", "lots": "0.40",
                 "units": "40000"}
        r = check([close], "2026-11-16 16:58 London", portfolio=pf)
        res = r["results"][0]
        self.assertEqual((res["kind"], res["verdict"]), ("exit", "PASS"))
        self.assertTrue(any(w.startswith("exit, not blocked: window") for w in res["warnings"]))


class Command(unittest.TestCase):
    def test_writes_fingerprinted_verdicts(self):
        with Scratch():
            write("trader/orders.json", {"orders": [EURUSD]})
            write("trader/calendar.json", CAL)
            code, out, _ = run(risk, ["--now", "2026-11-16 08:45 London"])
            self.assertEqual(code, 0, out)
            doc = read("trader/state/risk.json")
            self.assertEqual(doc["results"][0]["fingerprint"], risk.fingerprint(EURUSD))
            self.assertEqual(doc["date"], "2026-11-16")


if __name__ == "__main__":
    unittest.main()
