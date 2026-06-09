"""
GODMODE OFEA split — the 25 setups decomposed out of the 1,573-line monolith.

The monolith (GODMODE_OFEA..cs) scores all 25 setups into ONE counter and fires
one trade/bar, so the backtest can't say which setup makes or loses money
(see GODMODE_OFEA_MASTER_COMPENDIUM.md). This module registers each setup as a
SEPARATE, trackable unit and is honest about where each can actually be tested:

  ohlcv          -> the hub's Python backtester can run a PROXY (price-structure)
  volume-profile -> hub can approximate from OHLCV (coarse; real needs footprint)
  orderflow      -> needs tick/delta/footprint -> cTrader Strategy Tester only
  multi-symbol   -> needs a second correlated symbol feed

A proxy ≠ the exact cBot logic. Truth comes from per-setup isolation in cTrader.
"""
from __future__ import annotations
import os, json

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETUPS = os.path.join(HUB, "registry", "godmode_setups.json")


def load():
    try:
        return json.load(open(SETUPS))
    except Exception:
        return []


def render():
    s = load()
    if not s:
        return "no godmode_setups.json — run the OFEA split generator first."
    groups = {}
    for x in s:
        groups.setdefault(x["where"], []).append(x)
    L = ["─" * 70, f"  GODMODE OFEA — {len(s)} setups split out of the monolith", "─" * 70]
    for where in sorted(groups):
        L.append(f"\n  ▣ {where}  ({len(groups[where])})")
        for x in sorted(groups[where], key=lambda d: d["id"]):
            mark = "✓" if x["hub_backtestable"] else "·"
            L.append(f"    {mark} GM{x['id']:02d} {x['code']:<10} {x['category']:<18} → {x['isolated_ea']}")
    bt = [x for x in s if x["hub_backtestable"]]
    L += ["", "─" * 70,
          f"  {len(bt)}/{len(s)} are price-structure → hub can proxy-backtest now.",
          "  The rest need cTrader order flow. Cut-list: GODMODE_OFEA_SPLIT.md.",
          "  Why split: one blended score can't tell winning setups from losing ones."]
    return "\n".join(L)
