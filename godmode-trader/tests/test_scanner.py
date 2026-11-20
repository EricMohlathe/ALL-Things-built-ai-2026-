import math
import unittest

from _load import CHARTS, DAILY, Scratch, core, load, read, run

tc = core()
scan = load("trader-scanner", "scan")
PLANTED = {"EURUSD": "breakout_20d", "GBPUSD": "breakdown_20d", "USDJPY": "overbought", "AUDUSD": "oversold",
           "XAUUSD": "bull_flag", "XAGUSD": "squeeze", "USOIL": "bear_flag", "US500": "reclaim_ma20",
           "GER40": "lose_ma20", "BTCUSD": "oversold_bounce", "ETHUSD": "overbought_fade"}


class Setups(unittest.TestCase):
    def walk(self, n=90, drift=0.0):
        return [100 * math.exp(0.004 * math.sin(i * 1.7) + drift * i) for i in range(n)]

    def test_breakout_and_breakdown(self):
        c = self.walk()
        up = c[:-1] + [max(c[-21:-1]) * 1.01]
        down = c[:-1] + [min(c[-21:-1]) * 0.99]
        self.assertIn("breakout_20d", scan.find_setups(up)[0])
        self.assertIn("breakdown_20d", scan.find_setups(down)[0])

    def test_rsi_extremes(self):
        up = [100 * (1.01 ** i) for i in range(40)]
        self.assertIn("overbought", scan.find_setups(up)[0])
        self.assertEqual(scan.bias_of(["overbought", "breakout_20d", "reclaim_ma20"]), "long")
        self.assertEqual(scan.bias_of(["squeeze"]), "neutral")

    def test_planted_daily_setups(self):
        cfg = tc.load_config(None)
        insts = [tc.resolve(s) for s in list(PLANTED) + ["JPN225", "SOLUSD", "USDCHF"]]
        data, failed = scan.load_bundle(DAILY, insts)
        self.assertEqual(failed, {})
        hits, counts, _ = scan.scan_daily(data, insts, tc.parse_now("2026-11-16 09:00 London"), cfg)
        got = {h["symbol"]: h["setups"] for h in hits}
        for sym, tag in PLANTED.items():
            self.assertIn(tag, got.get(sym, []), sym)
        self.assertNotIn("JPN225", got)
        self.assertEqual(counts["scanned"], 14)

    def test_todays_partial_bar_waits_for_the_close(self):
        cfg = tc.load_config(None)
        inst = tc.resolve("EURUSD")
        data, _ = scan.load_bundle(DAILY, [inst])
        before = scan.daily_closes(data["EURUSD"], inst, tc.parse_now("2026-11-16 09:00 London"), cfg)
        after = scan.daily_closes(data["EURUSD"], inst, tc.parse_now("2026-11-16 17:30 London"), cfg)
        self.assertEqual(before[-1][0].isoformat(), "2026-11-13")
        self.assertEqual(after[-1][0].isoformat(), "2026-11-16")


class RangeScan(unittest.TestCase):
    def test_breakouts_in_each_instruments_own_session(self):
        with Scratch():
            code, out, _ = run(scan, ["range", "--offline", CHARTS, "--now", "2026-11-16 09:00 London"])
            self.assertEqual(code, 0)
            doc = read("trader/watchlist.json")
            got = [(h["symbol"], h["direction"], h["time"], h["session"]) for h in doc["hits"]]
            self.assertEqual(got, [("BTCUSD", "short", "01:15", "utc"), ("GBPUSD", "short", "08:40", "london"),
                                   ("EURUSD", "long", "08:45", "london")])
            self.assertIn("2 not open yet", out)

    def test_one_session_and_one_side(self):
        with Scratch():
            code, _, _ = run(scan, ["range", "--offline", CHARTS, "--now", "2026-11-16 09:00 London",
                                    "--class", "forex", "--side", "buy"])
            self.assertEqual(code, 0)
            self.assertEqual([h["symbol"] for h in read("trader/watchlist.json")["hits"]], ["EURUSD"])

    def test_universe(self):
        with Scratch():
            code, out, _ = run(scan, ["universe", "--class", "forex,crypto"])
            self.assertEqual(code, 0)
            self.assertIn("43 forex, 11 crypto", out)
            code, out, _ = run(scan, ["universe", "--futures", "--no-write"])
            self.assertIn("100 instruments", out)


if __name__ == "__main__":
    unittest.main()
