"""Indicators, SMC / ICT structure and order flow on hand-made series with known answers."""

import unittest

from _load import core

core()
import indicators as ind  # noqa: E402
import smc  # noqa: E402
import orderflow as of  # noqa: E402


class Indicators(unittest.TestCase):
    def test_moving_averages(self):
        x = [1.0, 2, 3, 4, 5, 6]
        self.assertEqual(ind.sma(x, 3), [None, None, 2.0, 3.0, 4.0, 5.0])
        e = ind.ema(x, 3)
        self.assertEqual(e[2], 2.0)                    # seeded with the SMA
        self.assertAlmostEqual(e[3], 3.0)
        self.assertAlmostEqual(e[5], 5.0)

    def test_rsi_extremes(self):
        up = [float(i) for i in range(30)]
        self.assertAlmostEqual(ind.rsi(up, 14)[-1], 100.0)
        down = [float(30 - i) for i in range(30)]
        self.assertAlmostEqual(ind.rsi(down, 14)[-1], 0.0)

    def test_atr_of_constant_range(self):
        h = [10.0 + 0 * i for i in range(30)]
        l = [9.0] * 30
        c = [9.5] * 30
        self.assertAlmostEqual(ind.atr(h, l, c, 14)[-1], 1.0)

    def test_vwap_resets_each_anchor(self):
        t = [0, 60, 86400, 86460]
        h = l = c = [10.0, 20.0, 30.0, 30.0]
        v = [1.0, 1.0, 1.0, 3.0]
        w = ind.vwap(t, h, l, c, v)
        self.assertEqual(w["vwap"][1], 15.0)
        self.assertEqual(w["vwap"][2], 30.0)          # new day, fresh VWAP

    def test_correlation(self):
        a = [1.0, 2, 3, 4, 5]
        self.assertAlmostEqual(ind.correlation(a, [2.0, 4, 6, 8, 10]), 1.0)
        self.assertAlmostEqual(ind.correlation(a, [5.0, 4, 3, 2, 1]), -1.0)

    def test_adx_and_regime_shapes(self):
        n = 200
        c = [100 + i * 0.5 for i in range(n)]
        h = [x + 0.3 for x in c]
        l = [x - 0.3 for x in c]
        adx = ind.adx(h, l, c)[0]
        self.assertGreater(adx[-1], 50)                # a straight line trends hard
        self.assertEqual(len(ind.regime(h, l, c)), n)


def zigzag():
    """Up, a pullback, a higher high that breaks the first swing high, then a collapse."""
    path = [10, 11, 12, 13, 12, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10, 9, 8]
    h = [p + 0.2 for p in path]
    l = [p - 0.2 for p in path]
    c = [float(p) for p in path]
    o = [c[0]] + c[:-1]
    return o, h, l, c


class Structure(unittest.TestCase):
    def test_swings_are_known_only_after_the_right_bars(self):
        o, h, l, c = zigzag()
        sw = smc.swings(h, l, 2, 2)
        hi = [s for s in sw if s["kind"] == "H"]
        self.assertEqual(hi[0]["i"], 3)
        self.assertEqual(hi[0]["at"], 5)

    def test_bos_then_choch(self):
        o, h, l, c = zigzag()
        ev, trend = smc.structure(h, l, c, smc.swings(h, l, 2, 2))
        kinds = [(e["kind"], e["dir"]) for e in ev]
        self.assertIn(("BOS", "up"), kinds)
        self.assertEqual(kinds[-1], ("CHoCH", "down"))
        self.assertEqual(trend[-1], "down")

    def test_fvg_touch_and_fill(self):
        h = [10.5, 10.5, 12.0, 12.5, 11.4, 10.4]
        l = [9.5, 10.0, 10.4, 11.5, 11.0, 9.9]
        c = [10.0, 10.4, 11.8, 12.2, 11.2, 10.0]
        g = smc.fvgs(h, l, c)[0]
        self.assertEqual((g["side"], g["i"], g["at"]), ("bull", 2, 3))
        self.assertEqual((g["bottom"], g["top"]), (10.5, 11.5))
        self.assertEqual(g["touched_at"], 4)
        self.assertEqual(g["filled_at"], 5)

    def test_order_block_is_the_last_opposite_candle(self):
        o = [10.0, 10.5, 10.4, 10.2, 10.6, 11.5]
        c = [10.5, 10.4, 10.2, 10.6, 11.5, 11.8]
        h = [max(a, b) + 0.1 for a, b in zip(o, c)]
        l = [min(a, b) - 0.1 for a, b in zip(o, c)]
        obs = smc.order_blocks(o, h, l, c, [{"at": 5, "dir": "up", "kind": "BOS", "swing_i": 1}])
        self.assertEqual(obs[0]["i"], 2)
        self.assertEqual(obs[0]["side"], "bull")

    def test_sweep_and_displacement(self):
        h, l, c = [10.0, 10.6], [9.0, 9.5], [9.5, 9.9]
        self.assertTrue(smc.sweep_at(1, h, l, c, 10.2, "high"))
        self.assertTrue(smc.sweep_at(1, h, l, c, 9.6, "low"))
        self.assertFalse(smc.sweep_at(1, h, l, c, 9.4, "low"))       # never traded below it
        self.assertEqual(smc.displacement([10.0], [12.05], [9.95], [12.0], [1.0], 0, 1.5), 1)
        self.assertEqual(smc.displacement([10.0], [10.5], [9.9], [10.4], [1.0], 0, 1.5), 0)

    def test_killzones_and_silver_bullet_in_new_york_time(self):
        self.assertEqual(smc.killzone(2 * 60 + 30), "london_open")
        self.assertEqual(smc.killzone(8 * 60), "ny_am")
        self.assertEqual(smc.killzone(21 * 60), "asia")       # wraps midnight
        self.assertEqual(smc.silver_bullet(10 * 60 + 15), "am_sb")
        self.assertIsNone(smc.silver_bullet(11 * 60))

    def test_premium_discount_and_ote(self):
        self.assertEqual(smc.premium_discount(110.0, 100.0, 108.0)[0], "premium")
        self.assertEqual(smc.premium_discount(110.0, 100.0, 102.0)[0], "discount")
        lo, hi = smc.ote_zone(100.0, 110.0)
        self.assertTrue(102.0 <= lo < hi <= 104.0)

    def test_liquidity_pools(self):
        sw = [{"i": 1, "at": 3, "price": 10.0, "kind": "H"}, {"i": 5, "at": 7, "price": 10.01, "kind": "H"}]
        h = [9.0] * 8 + [10.2]
        pools = smc.liquidity(sw, h, [8.0] * 9, 0.05)
        self.assertEqual(pools[0]["kind"], "EQH")
        self.assertEqual(pools[0]["swept_at"], 8)


class OrderFlow(unittest.TestCase):
    def test_clv_delta_sign(self):
        d = of.delta_clv([1.0, 1.0], [2.0, 2.0], [0.0, 0.0], [2.0, 0.0], [10.0, 10.0])
        self.assertEqual(d, [10.0, -10.0])

    def test_cvd_resets_on_a_new_key(self):
        self.assertEqual(of.cvd([1, 1, 1, 1], ["a", "a", "b", "b"]), [1, 2, 1, 2])

    def test_volume_profile_poc_and_value_area(self):
        h = [10.0] * 10 + [12.0]
        l = [9.0] * 10 + [11.0]
        c = [9.5] * 10 + [11.5]
        p = of.volume_profile(h, l, c, [10.0] * 11, bins=30)
        self.assertTrue(9.0 <= p["poc"] <= 10.0)
        self.assertLessEqual(p["val"], p["poc"])
        self.assertGreaterEqual(p["vah"], p["poc"])

    def test_absorption_and_divergence(self):
        n = 25
        o = [10.0] * n
        h = [10.5] * n
        l = [9.5] * n
        c = [10.0] * n
        v = [100.0 + (i % 3) for i in range(n)]
        v[-1] = 1000.0
        h[-1], l[-1], c[-1] = 10.1, 9.95, 10.05
        d = [0.0] * n
        d[-1] = -500.0
        self.assertEqual(of.absorption(o, h, l, c, v, d, [1.0] * n, n - 1), "bullish")
        hh = [10.0] * 20 + [11.0]
        cum = [5.0] * 20 + [4.0]
        self.assertEqual(of.divergence(hh, [9.0] * 21, cum, 20), "bearish")

    def test_tick_rule_bars(self):
        bars = of.tick_rule_bars([(0, 1.0002, 1.0, 1, 1), (1000, 1.0004, 1.0002, 1, 1),
                                  (2000, 1.0001, 0.9999, 1, 1)], 60)
        o, h, l, c, cnt, delta, spread = bars[0]
        self.assertEqual((cnt, delta), (3, 0))           # unsigned, up, down
        self.assertAlmostEqual(spread, 0.0002)


if __name__ == "__main__":
    unittest.main()
