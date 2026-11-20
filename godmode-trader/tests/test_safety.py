"""The safety layer: the approval-gate hook, the risk manager's losing-streak pause and
prop-firm guard, and the agent desk's definitions."""

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from _load import CALENDAR, CHARTS, ROOT, core, read, write

tc = core()
GATE = os.path.join(ROOT, "hooks", "approval_gate.py")
AGENTS = ["strategist", "smc-analyst", "macro-analyst", "quant-researcher", "risk-skeptic", "position-monitor",
          "reflector"]


class Project(object):
    def __enter__(self):
        self.old = os.getcwd()
        self.dir = tempfile.mkdtemp(prefix="godmode-safety-")
        os.chdir(self.dir)
        os.makedirs("trader/state")
        with open(os.path.join(ROOT, "trader-budget", "config.example.json")) as fh:
            self.cfg = json.load(fh)
        write("trader/config.json", self.cfg)
        return self

    def __exit__(self, *exc):
        os.chdir(self.old)
        shutil.rmtree(self.dir, ignore_errors=True)

    def sh(self, folder, script, *args):
        p = subprocess.run([sys.executable, os.path.join(ROOT, folder, script)] + list(args),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        return p.returncode, p.stdout, p.stderr


def gate(event):
    p = subprocess.run([sys.executable, GATE], input=json.dumps(event), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True)
    assert p.returncode == 0, p.stderr
    if not p.stdout.strip():
        return None, ""
    out = json.loads(p.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse"
    return out["permissionDecision"], out["permissionDecisionReason"]


class ApprovalGate(unittest.TestCase):
    def approved(self, status="approved"):
        cfg = tc.load_config("trader/config.json")
        today = tc.to_local(cfg["timezone"], tc.utc_now()).date().isoformat()
        write("trader/state/risk.json", {"date": today, "results": [{"fingerprint": "f1", "verdict": "PASS"},
                                                                    {"fingerprint": "f2", "verdict": "BLOCK"}]})
        recs = [{"date": today, "fingerprint": "f1", "status": "approved", "symbol": "EURUSD", "side": "buy",
                 "index": 1, "at": today + "T08:45", "plain": "BUY 0.40 lots EURUSD"},
                {"date": today, "fingerprint": "f2", "status": "approved", "symbol": "XAUUSD", "side": "sell",
                 "index": 2, "at": today + "T08:50"}]
        if status != "approved":
            recs.append({"date": today, "fingerprint": "f1", "status": status, "symbol": "EURUSD", "side": "buy"})
        write("trader/state/broker.json", {"orders": recs})
        return today

    def ev(self, tool, inp):
        return {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": inp, "cwd": os.getcwd()}

    def test_only_order_tools_are_touched(self):
        with Project():
            for tool in ("mcp__github__create_pull_request", "mcp__Co-Invest__close_position",
                         "mcp__Co-Invest__suggest_order", "mcp__Co-Invest__view_open_orders", "Bash"):
                self.assertEqual(gate(self.ev(tool, {"symbol": "EURUSD"})), (None, ""), tool)

    def test_a_matching_approved_order_still_asks(self):
        with Project():
            self.approved()
            d, why = gate(self.ev("mcp__oanda__create_order", {"order": {"instrument": "EUR_USD", "units": "40000"}}))
            self.assertEqual(d, "ask")
            self.assertIn("matches approved order #1", why)
            self.assertIn("PAPER", why)
            d, _ = gate(self.ev("mcp__x__placeOrder", {"symbol": "EURUSD", "side": "BUY"}))
            self.assertEqual(d, "ask")

    def test_everything_else_is_denied(self):
        with Project():
            d, why = gate(self.ev("mcp__Co-Invest__execute_order", {"symbol": "EURUSD", "side": "buy"}))
            self.assertEqual(d, "deny")                                       # nothing approved yet
            self.assertIn("explicit yes", why)
            self.approved()
            d, why = gate(self.ev("mcp__Co-Invest__execute_order", {"symbol": "GBPUSD", "side": "buy"}))
            self.assertEqual(d, "deny")
            self.assertIn("does not match", why)
            d, _ = gate(self.ev("mcp__Co-Invest__execute_order", {"symbol": "EURUSD", "side": "sell"}))
            self.assertEqual(d, "deny")
            d, _ = gate(self.ev("mcp__Co-Invest__execute_order", {"symbol": "XAUUSD", "side": "sell"}))
            self.assertEqual(d, "deny")                                       # approved but risk BLOCKED it
            d, why = gate(self.ev("mcp__Co-Invest__execute_order", {"amount": 5}))
            self.assertEqual(d, "deny")
            self.assertIn("cannot tell which symbol", why)

    def test_a_used_approval_cannot_send_twice(self):
        with Project():
            self.approved(status="placed")
            d, _ = gate(self.ev("mcp__Co-Invest__execute_order", {"symbol": "EURUSD", "side": "buy"}))
            self.assertEqual(d, "deny")

    def test_it_fails_closed(self):
        with Project():
            self.approved()
            with open("trader/state/risk.json", "w") as fh:
                fh.write("{not json")
            d, why = gate(self.ev("mcp__Co-Invest__execute_order", {"symbol": "EURUSD", "side": "buy"}))
            self.assertEqual(d, "deny")
            self.assertIn("could not verify", why)

    def test_hooks_json(self):
        with open(os.path.join(ROOT, "hooks", "hooks.json")) as fh:
            doc = json.load(fh)
        h = doc["hooks"]["PreToolUse"][0]
        self.assertEqual(h["matcher"], "mcp__.*")
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/hooks/approval_gate.py", h["hooks"][0]["command"])


class RiskUpgrades(unittest.TestCase):
    def orders(self, p):
        london = "2026-11-16 08:45 London"
        for folder, script, args in (("trader-calendar", "econ.py", ["week", "--offline", CALENDAR, "--now", london, "--write"]),
                                     ("trader-entry", "entry.py", ["check", "EURUSD", "--offline", CHARTS, "--now", london,
                                                                   "--write"]),
                                     ("trader-exit", "exit.py", ["plan", "--now", london, "--write"]),
                                     ("trader-budget", "size.py", ["--now", london, "--write"])):
            code, out, err = p.sh(folder, script, *args)
            self.assertEqual(code, 0, out + err)
        return london

    def journal(self, rs):
        cols = ["ID", "Timestamp", "Decision", "Symbol", "R", "Observed at"]
        with open("trader/journal.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for k, r in enumerate(rs, 1):
                w.writerow({"ID": k, "Timestamp": "2026-11-16T06:00:00Z", "Decision": "PAPER", "Symbol": "GBPUSD",
                            "R": r, "Observed at": "2026-11-16T07:%02d:00Z" % k})

    def test_losing_streak_pauses_entries(self):
        with Project() as p:
            london = self.orders(p)
            self.journal(["1.0", "-1.0", "-1.0"])
            code, out, _ = p.sh("trader-risk", "check.py", "--now", london, "--no-write")
            self.assertEqual(code, 0, out)
            self.assertIn("Losing results in a row today: 2.", out)
            self.journal(["-1.0", "-1.0", "-1.0"])
            code, out, _ = p.sh("trader-risk", "check.py", "--now", london, "--no-write")
            self.assertEqual(code, 1)
            self.assertIn("streak: 3 losing results in a row today", out)
            code, out, _ = p.sh("trader-risk", "check.py", "--now", "2026-11-17 08:45 London", "--no-write")
            self.assertNotIn("streak:", out)                                  # a new day

    def test_prop_firm_guard(self):
        with Project() as p:
            london = self.orders(p)
            write("trader/propfirm.json", {"preset": "ftmo_2step", "size": 100000.0, "currency": "USD", "phase": 1,
                                           "balance": 95000.0, "equity": 95000.0, "peak": 100000.0, "today": "2026-11-16",
                                           "days": {"2026-11-16": {"start": 95000.0, "traded": True}}})
            code, out, _ = p.sh("trader-risk", "check.py", "--now", london, "--no-write")
            self.assertEqual(code, 0, out)
            self.assertIn("Prop firm (FTMO 2-Step", out)
            st = read("trader/propfirm.json")
            st["equity"] = 90100.0
            write("trader/propfirm.json", st)
            code, out, _ = p.sh("trader-risk", "check.py", "--now", london, "--no-write")
            self.assertEqual(code, 1)
            self.assertIn("prop firm: $50.00 at the stop is over the $20.00", out)


class AgentDesk(unittest.TestCase):
    def test_agents(self):
        found = sorted(f[:-3] for f in os.listdir(os.path.join(ROOT, "agents")) if f.endswith(".md"))
        self.assertEqual(found, sorted(AGENTS))
        for a in AGENTS:
            with open(os.path.join(ROOT, "agents", a + ".md"), encoding="utf-8") as fh:
                text = fh.read()
            m = re.match(r"^---\nname: (.+)\ndescription: (.+)\ntools: (.+)\n---\n", text)
            self.assertTrue(m, a)
            self.assertEqual(m.group(1), a)
            self.assertGreater(len(m.group(2)), 120, a)
            self.assertNotIn("Write", m.group(3), "%s should not write files" % a)
            low = " ".join(text.lower().split())
            self.assertTrue("never" in low and ("place" in low or "trade" in low), a)
            for bad in ("ticket.py approve --index", "bridge.py send --index 1 --live"):
                self.assertNotIn(bad, text, a)


if __name__ == "__main__":
    unittest.main()
