import datetime
import os
import unittest

from _load import CHARTS, ROOT, core

tc = core()
UTC = datetime.datetime


def zoneinfo_offset(zone, utc):
    try:
        import importlib
        zi = importlib.import_module("zoneinfo").ZoneInfo(zone)
    except Exception:
        return None
    return int(utc.replace(tzinfo=datetime.timezone.utc).astimezone(zi).utcoffset().total_seconds() // 60)


class TimeZones(unittest.TestCase):
    def test_built_in_dst_rules_match_the_iana_database(self):
        if zoneinfo_offset("Europe/London", UTC(2026, 1, 1)) is None:
            self.skipTest("no zoneinfo / tz data on this Python")
        bad = []
        for z in tc.ZONES:
            t = UTC(2025, 1, 1)
            while t < UTC(2029, 1, 1):
                if z == "FX/NewYork_Close":          # not an IANA zone: New York + 7 hours, always
                    want = zoneinfo_offset("America/New_York", t) + 420
                else:
                    want = zoneinfo_offset(z, t)
                if tc.offset_minutes(z, t) != want:
                    bad.append((z, t))
                t += datetime.timedelta(hours=3)
        self.assertEqual(bad, [])

    def test_mt5_server_time_is_new_york_plus_seven(self):
        self.assertEqual(tc.zone_name("MT5"), "FX/NewYork_Close")
        self.assertEqual(tc.offset_minutes("MT5", UTC(2026, 1, 15)), 120)
        self.assertEqual(tc.offset_minutes("MT5", UTC(2026, 3, 8, 7, 0)), 180)   # with New York, not Europe
        self.assertEqual(tc.offset_minutes("MT5", UTC(2026, 3, 8, 6, 59)), 120)
        self.assertEqual(tc.offset_minutes("Europe/Prague", UTC(2026, 7, 1)), 120)

    def test_dst_switch_moments_2026(self):
        # US: 2026-03-08 07:00 UTC and 2026-11-01 06:00 UTC; EU: last Sundays 01:00 UTC
        self.assertEqual(tc.offset_minutes("America/New_York", UTC(2026, 3, 8, 6, 59)), -300)
        self.assertEqual(tc.offset_minutes("America/New_York", UTC(2026, 3, 8, 7, 0)), -240)
        self.assertEqual(tc.offset_minutes("America/New_York", UTC(2026, 11, 1, 5, 59)), -240)
        self.assertEqual(tc.offset_minutes("America/New_York", UTC(2026, 11, 1, 6, 0)), -300)
        self.assertEqual(tc.offset_minutes("Europe/London", UTC(2026, 3, 29, 1, 0)), 60)
        self.assertEqual(tc.offset_minutes("Europe/London", UTC(2026, 10, 25, 1, 0)), 0)
        self.assertEqual(tc.offset_minutes("Australia/Sydney", UTC(2026, 7, 1)), 600)
        self.assertEqual(tc.offset_minutes("Australia/Sydney", UTC(2026, 12, 1)), 660)
        self.assertEqual(tc.offset_minutes("Asia/Tokyo", UTC(2026, 7, 1)), 540)

    def test_local_to_utc_round_trips(self):
        for z in ("America/New_York", "Europe/London", "Europe/Berlin", "Australia/Sydney", "Asia/Tokyo"):
            t = UTC(2026, 1, 1)
            while t < UTC(2027, 1, 1):
                loc = tc.to_local(z, t)
                self.assertEqual(tc.to_local(z, tc.to_utc(z, loc)), loc, (z, t))
                t += datetime.timedelta(hours=5)

    def test_parse_now_forms(self):
        self.assertEqual(tc.parse_now("2026-11-16 08:45", "Europe/London"), UTC(2026, 11, 16, 8, 45))
        self.assertEqual(tc.parse_now("2026-11-16 08:45 NY"), UTC(2026, 11, 16, 13, 45))
        self.assertEqual(tc.parse_now("2026-07-16 08:45 London"), UTC(2026, 7, 16, 7, 45))
        self.assertEqual(tc.parse_now("2026-11-16T08:45:00Z", "Asia/Tokyo"), UTC(2026, 11, 16, 8, 45))
        self.assertEqual(tc.parse_now("2026-11-16T10:45:00+02:00"), UTC(2026, 11, 16, 8, 45))
        with self.assertRaises(tc.TraderError):
            tc.parse_now("yesterday")

    def test_zone_names(self):
        self.assertEqual(tc.zone_name("London"), "Europe/London")
        self.assertEqual(tc.zone_name("ET"), "America/New_York")
        self.assertEqual(tc.zone_name("SAST"), "Africa/Johannesburg")
        with self.assertRaises(tc.TraderError):
            tc.zone_name("Middle/Earth")


class Holidays(unittest.TestCase):
    def test_easter_and_the_rule_calendars(self):
        self.assertEqual(tc.easter(2026), datetime.date(2026, 4, 5))
        self.assertEqual(tc.easter(2027), datetime.date(2027, 3, 28))
        lse = tc._rule_holidays("lse", 2026)
        self.assertIn("2026-12-28", lse)          # Boxing Day moves off Saturday
        self.assertIn("2026-08-31", lse)
        self.assertIn("2026-04-06", tc._rule_holidays("xetra", 2026))
        self.assertEqual(tc.holiday("fx", datetime.date(2026, 12, 25)), "Christmas Day (FX closed)")
        self.assertEqual(tc.holiday("nyse", datetime.date(2026, 11, 26)), "Thanksgiving Day")
        self.assertIsNone(tc.holiday("jpx", datetime.date(2026, 1, 1)))
        self.assertFalse(tc.calendar_known("jpx", 2026))


class Sessions(unittest.TestCase):
    def test_london_keeps_london_time_across_dst(self):
        winter = tc.session_instance("london", datetime.date(2026, 11, 16))
        summer = tc.session_instance("london", datetime.date(2026, 7, 15))
        self.assertEqual(winter["open_utc"], UTC(2026, 11, 16, 8, 0))
        self.assertEqual(summer["open_utc"], UTC(2026, 7, 15, 7, 0))
        self.assertEqual(len(tc.slots(winter, 300)), 108)

    def test_us_cash_holidays_and_early_close(self):
        self.assertIsNone(tc.session_instance("us_cash", datetime.date(2026, 11, 26)))
        early = tc.session_instance("us_cash", datetime.date(2026, 11, 27))
        self.assertEqual(early["close_utc"], UTC(2026, 11, 27, 18, 0))
        self.assertEqual(early["early"], "day after Thanksgiving")
        self.assertEqual(len(tc.slots(early, 300)), 42)
        cfg = tc.load_config(None)
        cfg["sessions"] = {"us_cash": {"no_entries_after": "15:30", "flat_by": "15:55"}}
        w = tc.windows(tc.session_instance("us_cash", datetime.date(2026, 11, 27), cfg), cfg)
        self.assertEqual(tc.hm(w["no_entries_after_local"]), "12:30")
        self.assertEqual(tc.hm(w["flat_by_local"]), "12:55")

    def test_lunch_breaks(self):
        tse = tc.session_instance("tse", datetime.date(2026, 11, 16))
        self.assertEqual(len(tc.slots(tse, 300)), 66)
        hk = tc.session_instance("hkex", datetime.date(2026, 11, 16))
        self.assertEqual(len(tc.slots(hk, 300)), 66)

    def test_crypto_trades_every_day(self):
        sun = tc.session_instance("utc", datetime.date(2026, 11, 15))
        self.assertEqual((sun["close_utc"] - sun["open_utc"]).total_seconds(), 86400)
        self.assertIsNone(tc.session_instance("london", datetime.date(2026, 11, 15)))

    def test_default_windows(self):
        w = tc.windows(tc.session_instance("london", datetime.date(2026, 11, 16)))
        self.assertEqual([tc.hm(w[k + "_local"]) for k in ("range_end", "no_entries_before", "no_entries_after",
                                                         "flat_by")], ["08:30", "08:30", "16:30", "16:55"])

    def test_locate_phases(self):
        self.assertEqual(tc.locate("london", UTC(2026, 11, 16, 7, 0))[1], "pre-open")
        self.assertEqual(tc.locate("london", UTC(2026, 11, 16, 9, 0))[1], "open")
        self.assertEqual(tc.locate("london", UTC(2026, 11, 16, 18, 0))[1], "closed")
        self.assertEqual(tc.locate("london", UTC(2026, 11, 15, 9, 0)), (None, "weekend"))
        self.assertEqual(tc.next_open("london", UTC(2026, 11, 14, 9, 0))["date"], "2026-11-16")


class Instruments(unittest.TestCase):
    def test_registry_covers_four_classes(self):
        reg = tc.registry(None, extra_path="")
        by = {}
        for i in reg.values():
            by[i["class"]] = by.get(i["class"], 0) + 1
        self.assertGreaterEqual(by["forex"], 40)
        self.assertGreaterEqual(by["commodity"], 15)
        self.assertGreaterEqual(by["index"], 15)
        self.assertGreaterEqual(by["crypto"], 10)
        self.assertEqual(len(reg), 100)

    def test_aliases(self):
        for alias, sym in (("eur/usd", "EURUSD"), ("EURUSD=X", "EURUSD"), ("gold", "XAUUSD"), ("NAS100", "US100"),
                           ("btc-usd", "BTCUSD"), ("DAX", "GER40"), ("WTI", "USOIL"), ("es=f", "ES")):
            self.assertEqual(tc.resolve(alias)["symbol"], sym, alias)
        with self.assertRaisesRegex(tc.TraderError, "did you mean"):
            tc.resolve("EURUSE")

    def test_specs(self):
        e, j, g, es = tc.resolve("EURUSD"), tc.resolve("USDJPY"), tc.resolve("XAUUSD"), tc.resolve("ES")
        self.assertEqual((e["pip"], e["digits"], e["contract"], e["leverage"]), (0.0001, 5, 100000, 30))
        self.assertEqual((j["pip"], j["digits"]), (0.01, 3))
        self.assertEqual((g["contract"], g["leverage"], g["session"]), (100, 20, "comex"))
        self.assertEqual((es["contract"], es["lot_step"], es["unit"]), (50, 1, "contract"))
        self.assertEqual(tc.resolve("AUDUSD")["leverage"], 20)   # not an ESMA major
        self.assertEqual(tc.resolve("BTCUSD")["leverage"], 2)

    def test_overrides_and_custom_instruments(self):
        cfg = tc.load_config(None)
        cfg["instruments"] = {"XAUUSD": {"contract": 10}, "ABCUSD": {"class": "crypto", "feed": "ABC-USD", "quote": "USD",
                                                                     "tick": 0.01, "contract": 1}}
        reg = tc.registry(cfg, extra_path="")
        self.assertEqual(reg["XAUUSD"]["contract"], 10)
        self.assertEqual(reg["ABCUSD"]["session"], "utc")
        cfg["instruments"] = {"NEWX": {"class": "forex"}}
        with self.assertRaisesRegex(tc.TraderError, "needs"):
            tc.registry(cfg, extra_path="")


class Money(unittest.TestCase):
    def test_ticks_round_away_for_stops(self):
        self.assertEqual(str(tc.stop_tick(1.161675, 0.00001, True)), "1.16167")
        self.assertEqual(str(tc.stop_tick(1.161675, 0.00001, False)), "1.16168")
        self.assertEqual(str(tc.to_tick(6812.37, 0.25)), "6812.25")
        self.assertEqual(str(tc.to_tick(95123.456, 5.0, "down")), "95120")

    def test_distances(self):
        self.assertEqual(tc.fmt_dist(0.00125, tc.resolve("EURUSD")), "12.5 pips")
        self.assertEqual(tc.fmt_dist(18.25, tc.resolve("US500")), "18.25 points")
        self.assertEqual(tc.fmt_dist(5.55, tc.resolve("XAUUSD")), "55.5 pips")

    def test_conversion(self):
        rates = {"EURUSD": 1.16, "USDJPY": 150.0}
        self.assertAlmostEqual(tc.conversion("EUR", "USD", rates), 1.16)
        self.assertAlmostEqual(tc.conversion("USD", "JPY", rates), 150.0)
        self.assertAlmostEqual(tc.conversion("EUR", "JPY", rates), 174.0)
        self.assertAlmostEqual(tc.quote_to_account(tc.resolve("USDJPY"), "USD", {}, 150.0), 1 / 150.0)
        with self.assertRaisesRegex(tc.TraderError, "need a EUR/USD rate"):
            tc.quote_to_account(tc.resolve("GER40"), "USD", {}, 24000)

    def test_account_state_and_exposure(self):
        cfg = tc.load_config(None)
        pf = {"currency": "USD", "balance": 5000, "positions": [{"symbol": "EURUSD", "units": 40000, "avg_price": 1.16},
                                                                {"symbol": "USDJPY", "units": -50000, "avg_price": 150}]}
        st = tc.account_state(cfg, pf, {}, {"EURUSD": 1.17, "USDJPY": 149.0})
        self.assertAlmostEqual(st["upnl"], 400 + 50000 * 1.0 / 149.0, 2)
        self.assertAlmostEqual(st["exposure"]["EUR"], 46800.0)
        self.assertGreater(st["exposure"]["JPY"], 0)       # short USDJPY = long yen
        self.assertNotIn("USD", st["exposure"])


class Charts(unittest.TestCase):
    def test_offline_chart_and_the_live_tick(self):
        inst = tc.resolve("EURUSD")
        ch = tc.get_chart(inst, "5m", offline=CHARTS)
        self.assertEqual(ch["feed"], "EURUSD=X")
        self.assertTrue(any(b["t"] % 300 for b in ch["bars"]))   # the fixture carries Yahoo's live tick
        sb = tc.session_bars(ch, tc.instance_on("london", "2026-11-16"), 300)
        self.assertTrue(all(b["t"] % 300 == 0 for b in sb["bars"]))
        self.assertEqual(sb["bars"][0]["o"], 1.1615)

    def test_wrong_feed_is_refused(self):
        with self.assertRaisesRegex(tc.TraderError, "holds"):
            tc.get_chart(tc.resolve("GBPUSD"), "5m", offline=os.path.join(CHARTS, "EURUSD-60d5m.json.gz"))

    def test_fill_gaps(self):
        t0 = UTC(2026, 11, 16, 8)
        bars = [{"t": tc.ts_of(t0 + datetime.timedelta(minutes=5 * i)), "o": 1, "h": 1, "l": 1, "c": 1.0 + i, "v": 0,
                 "slot": i, "start": t0 + datetime.timedelta(minutes=5 * i),
                 "end": t0 + datetime.timedelta(minutes=5 * i + 5)} for i in (0, 1, 3)]
        out, n = tc.fill_gaps(bars, 3, 1)
        self.assertEqual((n, out[2]["c"], out[2]["filled"]), (1, 2.0, True))
        self.assertEqual(tc.fill_gaps(bars, 3, 0), (None, 1))

    def test_cli(self):
        import subprocess
        import sys
        p = subprocess.run([sys.executable, os.path.join(ROOT, "trader-core", "tradercore.py"), "show", "gold"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(p.returncode, 0)
        self.assertIn('"symbol": "XAUUSD"', p.stdout)


if __name__ == "__main__":
    unittest.main()
