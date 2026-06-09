"""
StrategyAdapter — one uniform interface over every integrated repo.

The 18 repos are heterogeneous (Python strategies, an LSTM freqtrade strat, a
.NET-ish forex bot, agent swarms, MCP servers). They DON'T merge into one binary.
Instead each is wrapped as an adapter that knows:
  - where it lives, what language, whether it touches a live broker
  - how to run it (run_hint)
  - an analyze() entry the hub can call (deep wiring is incremental per repo)

This keeps the hub coherent while the underlying repos stay independent.
"""
from __future__ import annotations
import os, json, shutil, subprocess


class StrategyAdapter:
    def __init__(self, spec: dict, repos_dir: str):
        self.name = spec["name"]
        self.kind = spec.get("kind", "strategy")
        self.lang = spec.get("lang", "")
        self.exec_surface = spec.get("exec_surface", False)
        self.run_hint = spec.get("run_hint", "")
        self.repo = os.path.join(repos_dir, spec.get("repo", self.name))
        self.enabled = spec.get("enabled", True)

    def installed(self) -> bool:
        return os.path.isdir(self.repo)

    def info(self) -> dict:
        return {"name": self.name, "kind": self.kind, "lang": self.lang,
                "exec_surface": self.exec_surface, "installed": self.installed(),
                "repo": self.repo, "run_hint": self.run_hint}

    def analyze(self, symbol: str, ai=None) -> dict:
        """Default analyze = describe how to engage this module for `symbol`.
        Repos get deep-wired incrementally; until then this returns guidance so
        the hub never silently pretends a module ran when it didn't."""
        return {"module": self.name, "symbol": symbol, "kind": self.kind,
                "installed": self.installed(),
                "action": self.run_hint or f"see {self.repo} README",
                "deep_wired": False}


def load_adapters(strategies_json: str, repos_dir: str) -> list[StrategyAdapter]:
    try:
        specs = json.load(open(strategies_json))
    except Exception:
        specs = []
    return [StrategyAdapter(s, repos_dir) for s in specs]
