"""trader-data and the history layer, offline: every source decoded from its real wire format."""

import datetime
import io
import json
import lzma
import os
import struct
import unittest
import zipfile

from _load import Scratch, core, load, run

tc = core()
import history as hist  # noqa: E402
from bars import Bars  # noqa: E402

DAY = datetime.date(2026, 1, 5)          # a Monday in January: Dukascopy's month folder is 00
DAY0 = tc.ts_of(datetime.datetime(2026, 1, 5))


def candles(records, scale=1e5):
    """records [(sec, a, b, c, d, vol)] -> an LZMA .bi5 payload (24-byte big-endian records)."""
    raw = b"".join(struct.pack(">5if", s, int(round(a * scale)), int(round(b * scale)), int(round(c * scale)),
                               int(round(d * scale)), v) for s, a, b, c, d, v in records)
    return lzma.compress(raw)


def ticks(records, scale=1e5):
    raw = b"".join(struct.pack(">3i2f", ms, int(round(ask * scale)), int(round(bid * scale)), av, bv)
                   for ms, ask, bid, av, bv in records)
    return lzma.compress(raw)


class Opener(object):
    """Stands in for the network: url substring -> bytes; records every request."""

    def __init__(self, routes):
        self.routes, self.urls = routes, []

    def __call__(self, url, data=None):
        self.urls.append(url)
        for key, payload in self.routes.items():
            if key in url:
                return payload(url) if callable(payload) else payload
        return None


class With(object):
    def __init__(self, opener):
        self.opener = opener

    def __enter__(self):
        self.old, self.sleep = hist.BYTES_OPENER, tc.SLEEP
        hist.BYTES_OPENER, tc.SLEEP = self.opener, (lambda s: None)
        return self.opener

    def __exit__(self, *exc):
        hist.BYTES_OPENER, tc.SLEEP = self.old, self.sleep


class Dukascopy(unittest.TestCase):
    def test_candles_open_close_low_high_order(self):
        recs = [(0, 1.1000, 1.1010, 1.0995, 1.1012, 5.0), (60, 1.1010, 1.1005, 1.1001, 1.1015, 3.0),
                (120, 1.1005, 1.1020, 1.1004, 1.1022, 4.0)]
        with With(Opener({"BID_candles_min_1": candles(recs)})) as op:
            b = hist.fetch_dukascopy(tc.resolve("EURUSD"), DAY, DAY)
        self.assertIn("/EURUSD/2026/00/05/BID_candles_min_1.bi5", op.urls[0])
        self.assertEqual(len(b), 3)
        self.assertEqual(b.t[0], DAY0)
        self.assertAlmostEqual(b.o[0], 1.1000)
        self.assertAlmostEqual(b.h[0], 1.1012)
        self.assertAlmostEqual(b.l[0], 1.0995)
        self.assertAlmostEqual(b.c[0], 1.1010)

    def test_candles_in_the_other_field_order_are_detected(self):
        recs = [(0, 1.1000, 1.1030, 1.0990, 1.1020, 5.0), (60, 1.1020, 1.1040, 1.1010, 1.1015, 2.0)]   # o h l c
        with With(Opener({"BID_candles": candles(recs)})):
            b = hist.fetch_dukascopy(tc.resolve("EURUSD"), DAY, DAY)
        self.assertAlmostEqual(b.h[0], 1.1030)
        self.assertAlmostEqual(b.c[0], 1.1020)

    def test_a_wrong_scale_is_refused(self):
        recs = [(0, 1.1, 1.101, 1.0995, 1.1012, 5.0)]
        with With(Opener({"BID_candles": candles(recs, scale=1.0)})):
            with self.assertRaises(hist.DataError):
                hist.fetch_dukascopy(tc.resolve("EURUSD"), DAY, DAY)

    def test_missing_days_are_skipped(self):
        with With(Opener({})):
            b = hist.fetch_dukascopy(tc.resolve("EURUSD"), DAY, DAY + datetime.timedelta(days=2))
        self.assertEqual(len(b), 0)

    def test_ticks_build_bars_with_a_tick_rule_delta(self):
        recs = [(1000, 1.10002, 1.10000, 1.0, 1.0), (2000, 1.10012, 1.10010, 1.0, 1.0),
                (3000, 1.10022, 1.10020, 1.0, 1.0), (61000, 1.10012, 1.10010, 1.0, 1.0)]
        with With(Opener({"00h_ticks": ticks(recs)})):
            b = hist.fetch_dukascopy(tc.resolve("EURUSD"), DAY, DAY, ticks=True)
        self.assertEqual(len(b), 2)
        self.assertAlmostEqual(b.o[0], 1.10001)
        self.assertAlmostEqual(b.c[0], 1.10021)
        self.assertEqual(b.v[0], 3)
        self.assertEqual(b.d[0], 2)        # first tick unsigned, then two upticks
        self.assertEqual(b.d[1], -1)       # a downtick in the next minute

    def test_jpy_and_metal_scales(self):
        self.assertEqual(hist.duka_symbol(tc.resolve("USDJPY"))[1], 1e3)
        self.assertEqual(hist.duka_symbol(tc.resolve("EURUSD"))[1], 1e5)
        self.assertEqual(hist.duka_symbol(tc.resolve("XAUUSD"))[0], "XAUUSD")
        self.assertEqual(hist.duka_symbol(tc.resolve("US500"))[0], "USA500IDXUSD")


class Binance(unittest.TestCase):
    ROWS = [[1767571200000, "90000", "90500", "89900", "90400", "10", 0, "0", 5, "7", "0", "0"],
            [1767571500000, "90400", "90450", "90100", "90200", "8", 0, "0", 5, "2", "0", "0"]]

    def test_klines_carry_taker_delta(self):
        with With(Opener({"api.binance.com": json.dumps(self.ROWS).encode()})) as op:
            b = hist.fetch_binance(tc.resolve("BTCUSD"), "5m", 1767571200, 1767571800)
        self.assertIn("symbol=BTCUSDT", op.urls[0])
        self.assertEqual(len(b), 2)
        self.assertEqual(b.d[0], 4.0)            # 2 x 7 - 10: buyers took 7 of 10
        self.assertEqual(b.d[1], -4.0)

    def test_bulk_monthly_zip(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("BTCUSDT-5m-2026-01.csv", "\n".join(",".join(str(x) for x in r) for r in self.ROWS))
        with With(Opener({"data.binance.vision": buf.getvalue()})) as op:
            b = hist.fetch_binance_vision(tc.resolve("BTCUSD"), "5m", [(2026, 1)])
        self.assertIn("BTCUSDT-5m-2026-01.zip", op.urls[0])
        self.assertEqual(len(b), 2)

    def test_not_crypto(self):
        with self.assertRaises(hist.DataError):
            hist.binance_pair(tc.resolve("EURUSD"))


class Parsers(unittest.TestCase):
    def test_histdata_is_est_without_dst(self):
        b = hist.parse_histdata_csv("20260706 170000;1.1;1.2;1.0;1.15;0\n", "EURUSD")
        self.assertEqual(tc.iso(tc.utc_of(b.t[0])), "2026-07-06T22:00:00Z")   # July: still UTC-5

    def test_stooq_and_fred(self):
        b = hist.parse_stooq_csv("Date,Open,High,Low,Close,Volume\n2026-01-02,1,2,0.5,1.5,100\n", "US500")
        self.assertEqual((len(b), b.c[0], b.step), (1, 1.5, 86400))
        rows = hist.parse_fred_csv("observation_date,CPIAUCSL\n2026-01-01,320.5\n2026-02-01,.\n")
        self.assertEqual(rows, [(datetime.date(2026, 1, 1), 320.5)])


class BarsAndCache(unittest.TestCase):
    def series(self, n=120, step=60, t0=DAY0):
        b = Bars(step, "EURUSD")
        for i in range(n):
            p = 1.1 + 0.0001 * i
            b.append(t0 + i * step, p, p + 0.0002, p - 0.0002, p + 0.0001, 1.0, 1.0 if i % 2 else -1.0)
        return b

    def test_resample_drops_the_unfinished_bar(self):
        b = self.series(150)
        h = b.resample("1h")
        self.assertEqual(len(h), 2)                       # 150 minutes: two whole hours, the third unfinished
        self.assertEqual(h.o[0], b.o[0])
        self.assertEqual(h.c[1], b.c[119])
        self.assertEqual(h.d[0], 0.0)

    def test_last_closed_and_first_from(self):
        h = self.series(180).resample("1h")
        self.assertEqual(h.last_closed_at(DAY0 + 3600), 0)
        self.assertEqual(h.last_closed_at(DAY0 + 3599), -1)
        self.assertEqual(h.first_from(DAY0 + 1), 1)
        self.assertEqual(h.index_at(DAY0 + 1), -1)

    def test_cache_round_trip_and_merge(self):
        with Scratch():
            hist.save(self.series(60))
            hist.save(self.series(60, t0=DAY0 + 3600))
            b = hist.load("EURUSD", "1m")
            self.assertEqual(len(b), 120)
            self.assertEqual(b.d[1], 1.0)
            self.assertEqual(len(hist.load("EURUSD", "1h")), 2)
            self.assertEqual(hist.inventory()[0]["bars"], 120)
            with self.assertRaises(hist.DataError):
                hist.load("GBPUSD", "1h")


class DataCli(unittest.TestCase):
    def test_get_info_quality_resample(self):
        data = load("trader-data", "data")
        recs = [(60 * k, 1.1 + k * 1e-5, 1.1 + k * 1e-5 + 5e-6, 1.1 + k * 1e-5 - 1e-5, 1.1 + k * 1e-5 + 2e-5, 1.0)
                for k in range(180)]
        with Scratch(), With(Opener({"BID_candles": candles(recs)})):
            code, out, err = run(data, ["get", "EURUSD", "--from", "2026-01-05", "--to", "2026-01-05"])
            self.assertEqual(code, 0, err)
            self.assertIn("180 bars downloaded", out)
            code, out, _ = run(data, ["--json", "info"])
            self.assertEqual(json.loads(out)[0]["bars"], 180)
            code, out, _ = run(data, ["resample", "EURUSD", "--to", "H1"])
            self.assertIn("3 bars", out)
            code, out, _ = run(data, ["--json", "quality", "EURUSD"])
            self.assertEqual(json.loads(out)["bars"], 180)

    def test_import_mt5_csv_in_server_time(self):
        data = load("trader-data", "data")
        with Scratch():
            with open("mt5.csv", "w") as fh:
                fh.write("2026.07.06 10:00,1.1,1.2,1.0,1.15,10\n2026.07.06 10:15,1.15,1.25,1.1,1.2,12\n")
            code, out, err = run(data, ["import", "EURUSD", "--csv", "mt5.csv", "--tf", "M15", "--tz", "Europe/Athens"])
            self.assertEqual(code, 0, err)
            b = hist.load("EURUSD", "15m")
            self.assertEqual(tc.iso(tc.utc_of(b.t[0])), "2026-07-06T07:00:00Z")   # Athens is UTC+3 in July

    def test_fred(self):
        data = load("trader-data", "data")
        with Scratch(), With(Opener({"fredgraph.csv?id=CPIAUCSL": b"observation_date,CPIAUCSL\n2026-01-01,320.5\n"})):
            code, out, err = run(data, ["fred", "CPIAUCSL"])
            self.assertEqual(code, 0, err)
            self.assertTrue(os.path.exists(os.path.join("trader", "data", "macro", "fred.json")))


if __name__ == "__main__":
    unittest.main()
