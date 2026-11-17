"""The README's walk-through, end to end, as real command lines: every number it quotes."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from _load import CALENDAR, CHARTS, NEWS, ROOT


class Pipeline(unittest.TestCase):
    def setUp(self):
        self.old = os.getcwd()
        self.dir = tempfile.mkdtemp(prefix="godmode-pipeline-")
        os.chdir(self.dir)
        os.makedirs("trader")
        shutil.copy(os.path.join(ROOT, "trader-budget", "config.example.json"), "trader/config.json")

    def tearDown(self):
        os.chdir(self.old)
        shutil.rmtree(self.dir, ignore_errors=True)

    def sh(self, folder, script, *args, ok=(0,)):
        p = subprocess.run([sys.executable, os.path.join(ROOT, folder, script)] + list(args),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertIn(p.returncode, ok, "%s %s\n%s\n%s" % (script, args, p.stdout, p.stderr))
        return p.stdout

    def test_one_trade_from_scan_to_fill(self):
        london = "2026-11-16 08:45 London"
        out = self.sh("trader-calendar", "econ.py", "week", "--offline", CALENDAR, "--now", london, "--write")
        self.assertIn("ECB President Lagarde Speaks", out)
        out = self.sh("trader-scanner", "scan.py", "range", "--offline", CHARTS, "--now", "2026-11-16 09:00 London")
        self.assertIn("3 broke out of their range", out)
        out = self.sh("trader-news", "news.py", "--symbols", "EURUSD", "--offline", NEWS, "--charts", CHARTS,
                      "--now", "2026-11-16 08:50 London")
        self.assertIn("+0.16% (up 18.9 pips)", out)
        out = self.sh("trader-entry", "entry.py", "check", "EURUSD", "--offline", CHARTS, "--now", london, "--write")
        self.assertIn("TRIGGERED LONG 08:45 London at 1.16285", out)
        out = self.sh("trader-exit", "exit.py", "plan", "--now", london, "--write")
        self.assertIn("Target        1.16535  2R", out)
        out = self.sh("trader-timemachine", "timemachine.py", "run", "--offline", CHARTS, "--now", london, "--write")
        for s in ("target first   14.7 %", "stop first     53.5 %", "neither        31.8 %",
                  "fired 29 times: 6 target, 23 stop", "Leans toward the stop"):
            self.assertIn(s, out)
        out = self.sh("trader-budget", "size.py", "--now", london, "--write")
        self.assertIn("Size: 0.40 lots EURUSD = 40,000 units, notional $46,514.00 (9.30x", out)
        out = self.sh("trader-risk", "check.py", "--now", london)
        self.assertIn("PASS  #1 buy EURUSD", out)
        self.assertIn("ECB President Lagarde Speaks (High) in 75 minutes", out)
        out = self.sh("trader-risk", "check.py", "--now", "2026-11-16 09:45 London", "--no-write", ok=(1,))
        self.assertIn("news: EUR ECB President Lagarde Speaks at 10:00 London", out)
        out = self.sh("trader-broker", "ticket.py", "show", "--now", london)
        self.assertIn("READY: trader-risk PASS", out)
        out = self.sh("trader-broker", "ticket.py", "approve", "--index", "1", "--reply", "yes GBPUSD", "--now",
                      london, ok=(1,))
        self.assertIn("names GBPUSD", out)
        self.sh("trader-broker", "ticket.py", "approve", "--index", "1", "--reply", "yes", "--now", london)
        self.sh("trader-broker", "ticket.py", "result", "--index", "1", "--status", "placed", "--filled-price",
                "1.16287", "--now", london)
        out = self.sh("trader-alerts", "alerts.py", "add", "--from-plan")
        self.assertIn("EURUSD below 1.1616", out)
        with open("trader/portfolio.json") as fh:
            pf = json.load(fh)
        self.assertEqual(pf["positions"][0], {"symbol": "EURUSD", "units": 40000.0, "avg_price": 1.16287,
                                              "opened": "2026-11-16"})

    def test_the_gold_short(self):
        ny = "2026-11-16 08:50 NY"
        self.sh("trader-entry", "entry.py", "check", "XAUUSD", "--offline", CHARTS, "--now", ny, "--write")
        out = self.sh("trader-exit", "exit.py", "plan", "--now", ny, "--write")
        self.assertIn("Stop          4058.75  range midpoint", out)
        self.assertIn("Target        4042.10", out)
        out = self.sh("trader-budget", "size.py", "--now", ny)
        self.assertIn("Max loss at the stop: $49.95", out)


if __name__ == "__main__":
    unittest.main()
