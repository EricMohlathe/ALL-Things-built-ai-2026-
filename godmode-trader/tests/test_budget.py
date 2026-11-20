import unittest

from _load import Scratch, core, load, read, run, write

tc = core()
size = load("trader-budget", "size")

EURUSD = {"symbol": "EURUSD", "side": "buy", "date": "2026-11-16", "session": "london", "tz": "Europe/London",
          "setup": "range", "entry": 1.16285, "stop": 1.1616, "target": 1.16535, "entry_time": "08:45",
          "flat_by": "16:55", "flat_by_utc": "2026-11-16T16:55:00Z"}
GOLD = {"symbol": "XAUUSD", "side": "sell", "date": "2026-11-16", "session": "comex", "tz": "America/New_York",
        "setup": "range", "entry": 4053.2, "stop": 4058.75, "target": 4042.1, "flat_by": "13:25"}


def sized(plan, cfg_over=None, rates=None, portfolio=None, prices=None, limit=None, price=None, today="2026-11-16"):
    cfg = tc.load_config(None)
    cfg.update({"balance": 5000})
    cfg.update(cfg_over or {})
    st = tc.account_state(cfg, portfolio, rates or {}, prices or {})
    inst = tc.resolve(plan["symbol"], cfg)
    return size.size_trade(plan, inst, cfg, st, rates or {}, limit, price, today), inst, cfg


class Sizing(unittest.TestCase):
    def test_eurusd_bound_by_max_loss(self):
        s, inst, cfg = sized(EURUSD)
        self.assertEqual((s["lots"], s["units"], s["max_loss"], s["bound_by"]), (0.4, 40000.0, 50.0, "max loss"))
        self.assertEqual((s["notional"], s["margin"], s["account_leverage_after"]), (46514.0, 1550.47, 9.3))
        o = size.bracket_order(s, inst, cfg)
        self.assertEqual((o["lots"], o["units"], o["stop_loss"], o["take_profit"], o["order_class"]),
                         ("0.40", "40000", "1.16160", "1.16535", "bracket"))

    def test_gold_short(self):
        s, _, _ = sized(GOLD)
        self.assertEqual((s["side"], s["lots"], s["units"], s["max_loss"], s["risk_pips"]), ("sell", 0.09, 9.0, 49.95, 55.5))

    def test_usdjpy_leverage_binds_and_converts_with_its_own_price(self):
        plan = dict(EURUSD, symbol="USDJPY", side="sell", entry=154.55, stop=154.7, target=154.25)
        s, _, _ = sized(plan)
        self.assertEqual((s["bound_by"], s["lots"], s["max_loss"]), ("leverage", 0.5, 48.53))
        self.assertAlmostEqual(s["conversion"], 1 / 154.55, 9)

    def test_a_euro_index_needs_a_rate(self):
        plan = dict(EURUSD, symbol="GER40", entry=24310, stop=24270, target=24390, session="xetra")
        with self.assertRaisesRegex(tc.TraderError, "EUR/USD rate"):
            sized(plan)
        s, _, _ = sized(plan, rates={"EURUSD": 1.162})
        self.assertEqual((s["lots"], s["max_loss"]), (1.0, 46.48))

    def test_futures_contracts(self):
        plan = dict(EURUSD, symbol="MES", session="us_cash", entry=6830.0, stop=6825.0, target=6840.0)
        s, _, _ = sized(plan)                          # 5 points x $5 = $25 a contract: 2 by max loss,
        self.assertEqual((s["lots"], s["max_loss"], s["bound_by"]), (1.0, 25.0, "leverage"))   # but $34,150 notional
        s, _, _ = sized(plan, {"balance": 50000})
        self.assertEqual((s["lots"], s["max_loss"], s["bound_by"]), (2.0, 50.0, "max loss"))
        plan = dict(plan, symbol="ES")                 # 5 points x $50 = $250 > $50
        s, inst, cfg = sized(plan)
        self.assertEqual(s["lots"], 0.0)
        self.assertIn("risks $250.00", s["refusal"])
        self.assertIsNone(size.bracket_order(s, inst, cfg))

    def test_crypto_coins_and_the_brokers_leverage(self):
        plan = dict(EURUSD, symbol="BTCUSD", side="sell", session="utc", entry=95150, stop=95880, target=93690)
        s, _, _ = sized(plan)
        # 2:1 crypto: $47,575 margin a coin, 50 % of $5,000 allows 0.0525 BTC before the $50 max loss does
        self.assertEqual((s["lots"], s["max_loss"], s["leverage_cap"], s["bound_by"]), (0.0525, 38.32, 2.0, "margin"))
        s, _, _ = sized(plan, {"balance": 20000})
        self.assertEqual((s["lots"], s["max_loss"], s["bound_by"]), (0.0684, 49.93, "max loss"))
        s, _, _ = sized(plan, {"broker": "alpaca"})
        self.assertEqual(s["leverage_cap"], 1.0)

    def test_a_worse_fresh_price_is_used(self):
        s, _, _ = sized(EURUSD, price=1.16300)
        self.assertEqual((s["entry"], s["entry_from"]), (1.163, "price"))
        s, _, _ = sized(EURUSD, price=1.16270)          # better for a long: the plan's entry stays
        self.assertEqual(s["entry_from"], "plan")
        s, _, _ = sized(GOLD, price=4052.0)             # worse for a short = lower
        self.assertEqual(s["entry_from"], "price")

    def test_refusals(self):
        with self.assertRaisesRegex(tc.TraderError, "today is"):
            sized(EURUSD, today="2026-11-17")
        s, _, _ = sized(dict(EURUSD, target=1.1635))
        self.assertIn("reward:risk", s["refusal"])
        with self.assertRaisesRegex(tc.TraderError, "already happened"):
            sized(EURUSD, limit=1.1660)
        with self.assertRaisesRegex(tc.TraderError, "blocked"):
            sized(EURUSD, {"blocked": ["EURUSD"]})

    def test_open_positions_use_up_the_room(self):
        pf = {"currency": "USD", "balance": 5000, "positions": [{"symbol": "GBPUSD", "units": 20000, "avg_price": 1.315}]}
        s, _, _ = sized(EURUSD, portfolio=pf, prices={"GBPUSD": 1.315})
        self.assertEqual((s["bound_by"], s["lots"]), ("leverage", 0.2))


class Command(unittest.TestCase):
    def test_writes_one_order(self):
        with Scratch():
            write("trader/plan.json", EURUSD)
            code, out, _ = run(size, ["--now", "2026-11-16 08:45 London", "--write"])
            self.assertEqual(code, 0)
            self.assertIn("Size: 0.40 lots EURUSD = 40,000 units", out)
            doc = read("trader/orders.json")
            self.assertEqual((doc["status"], doc["paper"], len(doc["orders"])), ("proposed", True, 1))


if __name__ == "__main__":
    unittest.main()
