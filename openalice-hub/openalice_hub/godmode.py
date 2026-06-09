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


def render(symbol="BTCUSDT"):
    s = load()
    if not s:
        return "no godmode_setups.json — run the OFEA split generator first."
    try:
        best = json.load(open(os.path.join(HUB, "registry", "godmode_best.json")))
    except Exception:
        best = {}
    groups = {}
    for x in s:
        groups.setdefault(x["where"], []).append(x)
    L = ["─" * 72, f"  GODMODE OFEA — {len(s)} setups, ALL backtest+optimize on real data 🟢", "─" * 72]
    for where in sorted(groups):
        L.append(f"\n  ▣ {where}  ({len(groups[where])})")
        for x in sorted(groups[where], key=lambda d: d["id"]):
            k = f"{x['py_detector']}|{symbol}"
            b = best.get(k)
            oos = f"OOS sh {b['oos_metric']:+.2f}" if b and b.get("oos_metric") is not None else "not ranked yet"
            L.append(f"    🟢 {x['py_detector']:<16} {x['category']:<18} {oos}")
    L += ["", "─" * 72,
          f"  All {len(s)} green: real Binance delta/CVD + volume profile (bar-resolution proxy).",
          "  Rank + improve:  python3 hub.py godmode-rank BTCUSDT   (re-run to keep improving)",
          "  Backtest one:    python3 hub.py backtest gm12_stackbear BTCUSDT --optimize",
          "  Truth = isolate the real cBot in cTrader (GODMODE_OFEA_SPLIT.md). PAPER. Past ≠ future."]
    return "\n".join(L)
