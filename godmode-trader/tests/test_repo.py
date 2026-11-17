import json
import os
import re
import subprocess
import sys
import unittest

from _load import ROOT

SKILLS = ["trader-scanner", "trader-news", "trader-calendar", "trader-entry", "trader-exit", "trader-timemachine",
          "trader-risk", "trader-budget", "trader-broker", "trader-alerts", "trader-cot"]
TOOLS = {"trader-scanner": "scan.py", "trader-news": "news.py", "trader-calendar": "econ.py",
         "trader-entry": "entry.py", "trader-exit": "exit.py", "trader-timemachine": "timemachine.py",
         "trader-risk": "check.py", "trader-budget": "size.py", "trader-broker": "ticket.py",
         "trader-alerts": "alerts.py", "trader-cot": "cot.py", "trader-core": "tradercore.py"}
ORDER_PATH = ["trader-scanner", "trader-entry", "trader-exit", "trader-timemachine", "trader-budget", "trader-risk",
              "trader-broker", "trader-alerts"]
EQUITY_ONLY = ["trader-analyst", "trader-pelosi", "place_stock_order", "SEC_USER_AGENT", "nasdaqlisted"]


def frontmatter(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return (m.group(1) if m else ""), text


def text_files():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "trader")]
        for f in files:
            if f.endswith((".md", ".py", ".json", ".xml")) or f == "LICENSE":
                yield os.path.join(base, f)


class Repo(unittest.TestCase):
    def test_eleven_skills_and_the_core(self):
        found = sorted(d for d in os.listdir(ROOT) if os.path.isfile(os.path.join(ROOT, d, "SKILL.md")))
        self.assertEqual(found, sorted(SKILLS))
        self.assertFalse(os.path.exists(os.path.join(ROOT, "trader-core", "SKILL.md")))   # a library, not a skill
        for folder, tool in TOOLS.items():
            self.assertTrue(os.path.isfile(os.path.join(ROOT, folder, tool)), folder)

    def test_frontmatter(self):
        for s in SKILLS:
            fm, text = frontmatter(os.path.join(ROOT, s, "SKILL.md"))
            self.assertIn("name: %s\n" % s, fm + "\n", s)
            self.assertRegex(fm, r"description: ", s)
            self.assertGreater(len(fm), 400, "%s description is too thin" % s)
            self.assertGreater(len(text.splitlines()), 60, s)
            self.assertIn("${CLAUDE_SKILL_DIR}", text, s)

    def test_order_path_skills_carry_the_safety_rule(self):
        for s in ORDER_PATH:
            _, text = frontmatter(os.path.join(ROOT, s, "SKILL.md"))
            low = " ".join(text.lower().split())
            self.assertIn("not financial advice", low, s)
            self.assertIn("explicit yes for that one order", low, s)
            self.assertIn("paper trading by default", low, s)

    def test_plugin_manifests(self):
        with open(os.path.join(ROOT, ".claude-plugin", "plugin.json")) as fh:
            plugin = json.load(fh)
        self.assertEqual((plugin["name"], plugin["skills"], plugin["license"]), ("godmode-trader", "./", "MIT"))
        with open(os.path.join(ROOT, ".claude-plugin", "marketplace.json")) as fh:
            market = json.load(fh)
        self.assertEqual(market["plugins"][0]["name"], "godmode-trader")

    def test_readme(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
            readme = " ".join(fh.read().split())
        for s in SKILLS:
            self.assertIn("/" + s, readme, s)
        for must in ("## Fine print", "Not financial advice", "Paper first", "day-trader-skill", "MIT"):
            self.assertIn(must, readme)

    def test_license_keeps_the_original_notice(self):
        with open(os.path.join(ROOT, "LICENSE")) as fh:
            lic = fh.read()
        self.assertIn("Copyright (c) 2026 Jake Schincariol", lic)
        self.assertIn("MIT License", lic)

    def test_no_em_dashes_and_no_equity_leftovers(self):
        for path in text_files():
            rel = os.path.relpath(path, ROOT)
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            self.assertNotIn(chr(0x2014), text, rel)   # no em dashes
            if rel.startswith("tests" + os.sep):
                continue
            for old in EQUITY_ONLY:
                self.assertNotIn(old, text, "%s still mentions %s" % (rel, old))

    def test_every_tool_runs_on_python_3_8(self):
        for folder, tool in TOOLS.items():
            with open(os.path.join(ROOT, folder, tool), encoding="utf-8") as fh:
                src = fh.read()
            name = "%s/%s" % (folder, tool)
            self.assertNotRegex(src, r"(?m)^\s*(import zoneinfo|from zoneinfo)", name)
            self.assertNotRegex(src, r"(?m)^\s+match \w+.*:$", name)
            for bad in ("list[", "dict[", "tuple[", "set["):
                self.assertNotRegex(src, r"(?<![\w.\"'])%s" % re.escape(bad), name)
            for bad in (".removeprefix(", ".removesuffix(", " | None"):
                self.assertNotIn(bad, src, name)

    def test_the_example_config_is_safe(self):
        with open(os.path.join(ROOT, "trader-budget", "config.example.json")) as fh:
            cfg = json.load(fh)
        self.assertIs(cfg["paper"], True)
        self.assertEqual(cfg["broker"], "paper")
        self.assertIs(cfg["require_stop"], True)
        for k in ("max_loss_per_trade", "max_daily_loss", "max_trades_per_day", "min_reward_risk",
                  "max_account_leverage", "max_margin_use_pct", "max_currency_exposure_x", "news_blackout_minutes"):
            self.assertIn(k, cfg, k)
        self.assertLessEqual(cfg["max_account_leverage"], 10)

    def test_every_tool_prints_its_help(self):
        for folder, tool in TOOLS.items():
            p = subprocess.run([sys.executable, os.path.join(ROOT, folder, tool), "--help"],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            self.assertEqual(p.returncode, 0, "%s/%s: %s" % (folder, tool, p.stderr))

    def test_fixtures_are_reproducible(self):
        import gzip
        import hashlib
        import importlib.util
        import shutil
        import tempfile
        src = os.path.join(ROOT, "tests", "fixtures")
        tmp = tempfile.mkdtemp()
        try:
            shutil.copy(os.path.join(src, "make_fixtures.py"), tmp)
            spec = importlib.util.spec_from_file_location("mf", os.path.join(tmp, "make_fixtures.py"))
            mf = importlib.util.module_from_spec(spec)
            sys.path.insert(0, os.path.join(ROOT, "trader-core"))
            spec.loader.exec_module(mf)
            mf.HERE = tmp
            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()):
                mf.main()
            for rel in ("charts/EURUSD-60d5m.json.gz", "charts/XAUUSD-60d5m.json.gz", "cot/legacy-futures.json.gz",
                        "calendar/ff_calendar_thisweek.json"):
                with open(os.path.join(src, rel), "rb") as a, open(os.path.join(tmp, rel), "rb") as b:
                    self.assertEqual(hashlib.sha256(a.read()).hexdigest(), hashlib.sha256(b.read()).hexdigest(), rel)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
