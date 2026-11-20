import copy
import json
import unittest

from _load import Scratch, core, load, read, run, write

tc = core()
ticket = load("trader-broker", "ticket")
risk = load("trader-risk", "check")

PLAN = {"entry": 1.16285, "stop": 1.1616, "target": 1.16535, "max_loss": 50.0, "currency": "USD", "conversion": 1.0,
        "notional": 46514.0, "margin": 1550.47, "session": "london", "date": "2026-11-16"}
EURUSD = {"symbol": "EURUSD", "class": "forex", "kind": "spot", "side": "buy", "type": "market",
          "time_in_force": "day", "lots": "0.40", "units": "40000", "stop_loss": "1.16160", "take_profit": "1.16535",
          "order_class": "bracket", "why": "test", "plan": PLAN}
NOW = ["--now", "2026-11-16 08:46 London"]


def cfg(**over):
    c = tc.load_config(None)
    c.update({"balance": 5000, "timezone": "Europe/London"})
    c.update(over)
    return c


class Words(unittest.TestCase):
    def test_fingerprint_is_shared_with_risk(self):
        self.assertEqual(ticket.fingerprint(EURUSD), risk.fingerprint(EURUSD))
        other = dict(EURUSD, lots="0.41", units="41000")
        self.assertNotEqual(ticket.fingerprint(EURUSD), ticket.fingerprint(other))
        self.assertEqual(ticket.fingerprint(dict(EURUSD, why="changed words")), ticket.fingerprint(EURUSD))

    def test_plain_ticket(self):
        text = ticket.plain(EURUSD, tc.resolve("EURUSD"), cfg())
        self.assertIn("BUY 0.40 lots (40,000 units) EURUSD", text)
        self.assertIn("stop-loss 1.16160 (12.5 pips)", text)
        self.assertIn("max loss about $50.00", text)

    def test_the_yes(self):
        inst, c = tc.resolve("EURUSD"), cfg()
        for reply, ok in (("yes", True), ("Yes", True), ("y", True), ("yes, 0.40 lots EURUSD", True),
                          ("yes 0.4", True), ("yes eur/usd", True), ("sure", False), ("ok", False),
                          ("yes to all", False), ("yes but wait", False), ("yes?", False), ("yes GBPUSD", False),
                          ("yes gold", False), ("yes 0.5 lots", False), ("", False), ("no", False)):
            self.assertEqual(ticket.parse_yes(reply, EURUSD, inst, c, ["EURUSD"])[0], ok, reply)


class Brokers(unittest.TestCase):
    def call(self, broker, order=EURUSD):
        return ticket.tool_call(order, tc.resolve(order["symbol"]), cfg(broker=broker))

    def test_oanda(self):
        c = self.call("oanda", dict(EURUSD, side="sell", stop_loss="1.16410", take_profit="1.16035"))
        body = c["input"]["order"]
        self.assertEqual((body["instrument"], body["units"], body["type"]), ("EUR_USD", "-40000", "MARKET"))
        self.assertEqual(body["stopLossOnFill"]["price"], "1.16410")
        gold = dict(EURUSD, symbol="XAUUSD", lots="0.09", units="9", stop_loss="4058.75", take_profit="4042.10")
        self.assertEqual(self.call("oanda", gold)["input"]["order"]["instrument"], "XAU_USD")

    def test_mt5(self):
        c = self.call("mt5")
        self.assertEqual((c["input"]["type"], c["input"]["volume"], c["input"]["sl"]), ("ORDER_TYPE_BUY", 0.4, 1.1616))
        self.assertIn('trade.Buy(0.4, "EURUSD"', c["mql5"])
        lim = self.call("mt5", dict(EURUSD, type="limit", limit_price="1.16280"))
        self.assertEqual((lim["input"]["action"], lim["input"]["type"]), ("TRADE_ACTION_PENDING", "ORDER_TYPE_BUY_LIMIT"))
        suff = ticket.tool_call(EURUSD, tc.resolve("EURUSD"), cfg(broker="mt5", symbol_suffix=".m"))
        self.assertEqual(suff["input"]["symbol"], "EURUSD.m")

    def test_ctrader(self):
        code = self.call("ctrader")["input"]["code"]
        self.assertIn("ExecuteMarketOrder(TradeType.Buy, s.Name, 40000", code)
        self.assertIn("0.00125 / s.PipSize", code)

    def test_alpaca_and_ibkr(self):
        btc = dict(EURUSD, symbol="BTCUSD", lots="0.0684", units="0.0684", time_in_force="gtc")
        c = self.call("alpaca", btc)
        self.assertEqual((c["tool"], c["input"]["symbol"], c["input"]["qty"]), ("place_crypto_order", "BTC/USD", "0.0684"))
        self.assertTrue(any("protect" in n for n in c["notes"]))
        ib = self.call("ibkr")["input"]
        self.assertEqual((ib["contract"]["symbol"], ib["contract"]["secType"]), ("EUR", "CASH"))
        self.assertEqual([x["orderType"] for x in ib["children"]], ["LMT", "STP"])


class Flow(unittest.TestCase):
    def test_ready_only_after_risk_and_once(self):
        with Scratch():
            write("trader/orders.json", {"orders": [EURUSD]})
            code, out, _ = run(ticket, ["show"] + NOW)
            self.assertEqual(code, 1)
            self.assertIn("NOT READY: trader-risk has not checked", out)
            run(risk, ["--now", "2026-11-16 08:45 London"])
            code, out, _ = run(ticket, ["show"] + NOW)
            self.assertEqual(code, 0)
            self.assertIn("READY: trader-risk PASS", out)
            code, out, _ = run(ticket, ["approve", "--index", "1", "--reply", "sure"] + NOW)
            self.assertEqual(code, 1)
            code, out, _ = run(ticket, ["approve", "--index", "1", "--reply", "yes"] + NOW)
            self.assertEqual(code, 0)
            code, _, err = run(ticket, ["approve", "--index", "1", "--reply", "yes"] + NOW)
            self.assertIn("APPROVED by you", err)
            code, out, _ = run(ticket, ["result", "--index", "1", "--status", "placed", "--broker-id", "X1",
                                        "--filled-price", "1.16287"] + NOW)
            self.assertEqual(code, 0)
            pf = read("trader/portfolio.json")
            self.assertEqual(pf["positions"][0]["units"], 40000.0)

    def test_a_changed_order_is_not_ready(self):
        with Scratch():
            write("trader/orders.json", {"orders": [EURUSD]})
            run(risk, ["--now", "2026-11-16 08:45 London"])
            write("trader/orders.json", {"orders": [dict(EURUSD, lots="0.39", units="39000")]})
            code, out, _ = run(ticket, ["show"] + NOW)
            self.assertIn("this exact order was not in the last risk check", out)


class Fills(unittest.TestCase):
    def test_long_round_trip_and_a_short_in_yen(self):
        with Scratch():
            run(ticket, ["fill", "--symbol", "EURUSD", "--side", "buy", "--lots", "0.40", "--price", "1.16287"] + NOW)
            code, out, _ = run(ticket, ["fill", "--symbol", "EURUSD", "--side", "sell", "--units", "20000",
                                        "--price", "1.16410"] + NOW)
            self.assertIn("Realized $24.60", out)
            pf = read("trader/portfolio.json")
            self.assertEqual((pf["balance"], pf["positions"][0]["units"]), (5024.6, 20000.0))
            run(ticket, ["fill", "--symbol", "USDJPY", "--side", "sell", "--units", "50000", "--price", "154.550"] + NOW)
            code, out, _ = run(ticket, ["fill", "--symbol", "USDJPY", "--side", "buy", "--units", "50000",
                                        "--price", "154.250"] + NOW)
            self.assertIn("Realized $97.24", out)     # 0.30 yen x 50,000 = 15,000 yen at 1/154.25

    def test_flatten_and_protect(self):
        with Scratch():
            write("trader/portfolio.json", {"currency": "USD", "balance": 5000,
                                            "positions": [{"symbol": "XAUUSD", "units": -9, "avg_price": 4053.2}]})
            write("trader/plan.json", {"symbol": "XAUUSD", "stop": 4058.75, "flat_by": "13:25"})
            code, out, _ = run(ticket, ["flatten", "--symbol", "XAUUSD"] + NOW)
            self.assertEqual(code, 0)
            o = read("trader/orders.json")["orders"][0]
            self.assertEqual((o["side"], o["units"], o["lots"]), ("buy", "9", "0.09"))
            code, out, _ = run(ticket, ["protect", "--symbol", "XAUUSD"] + NOW)
            o = read("trader/orders.json")["orders"][0]
            self.assertEqual((o["side"], o["type"], o["stop_price"]), ("buy", "stop", "4058.75"))
            code, _, err = run(ticket, ["flatten", "--symbol", "EURUSD"] + NOW)
            self.assertIn("nothing to close", err)


if __name__ == "__main__":
    unittest.main()
