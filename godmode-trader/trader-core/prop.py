"""prop: prop-firm challenge rules, a live guardian and pass-probability simulation.
Standard library only.

Rules change: every number here is a preset you can override in trader/config.json
("prop_firm": {...}) and must check against the firm's current terms before you rely on it.

  ftmo_2step   the FTMO Challenge and Verification as published (target 10 % then 5 %,
               maximum daily loss 5 % and maximum loss 10 % of the initial balance, at
               least 4 trading days, the day resetting at midnight Prague time; the daily
               floor is the day's starting balance minus 5 % of the initial balance)
  generic_2step a common two-phase shape: 8 % then 5 %, 5 % daily, 10 % static
  generic_1step one phase, 10 % target, 4 % daily, 6 % TRAILING maximum loss

The guardian turns the rules into numbers right now: how far equity is from the daily
floor and the overall floor, in money and in trades at your risk, and the largest risk per
trade that keeps a losing streak of `streak` trades inside today's room with a buffer.

The simulation resamples whole trading days from a setup's real (backtest or journal)
trades and plays the challenge forward thousands of times at several risk sizes: the
pass rate, why the rest failed, and the days it took. It is a sizing tool, not a promise.
"""

import random

PRESETS = {
    "ftmo_2step": {"label": "FTMO 2-Step (Challenge, Verification)", "targets_pct": [10.0, 5.0], "daily_loss_pct": 5.0,
                   "max_loss_pct": 10.0, "trailing": False, "min_days": 4, "max_days": None,
                   "day_zone": "Europe/Prague", "news_minutes": 2, "weekend_flat": False,
                   "source": "ftmo.com trading objectives; verify the current terms"},
    "generic_2step": {"label": "Generic 2-step (8 % / 5 %)", "targets_pct": [8.0, 5.0], "daily_loss_pct": 5.0,
                      "max_loss_pct": 10.0, "trailing": False, "min_days": 3, "max_days": None, "day_zone": "UTC",
                      "news_minutes": 0, "weekend_flat": False, "source": "a common industry shape"},
    "generic_1step": {"label": "Generic 1-step (trailing)", "targets_pct": [10.0], "daily_loss_pct": 4.0,
                      "max_loss_pct": 6.0, "trailing": True, "min_days": 3, "max_days": None, "day_zone": "UTC",
                      "news_minutes": 0, "weekend_flat": False, "source": "a common industry shape"},
}


def rules(cfg_prop):
    """The preset named in the config, with any overrides applied."""
    cfg_prop = cfg_prop or {}
    name = cfg_prop.get("preset", "ftmo_2step")
    if name not in PRESETS:
        raise ValueError("unknown prop preset %r: one of %s" % (name, ", ".join(sorted(PRESETS))))
    r = dict(PRESETS[name], preset=name)
    for k in ("targets_pct", "daily_loss_pct", "max_loss_pct", "trailing", "min_days", "max_days", "day_zone",
              "news_minutes", "weekend_flat"):
        if cfg_prop.get(k) is not None:
            r[k] = cfg_prop[k]
    return r


def guardian(rl, initial, balance, equity, day_start, peak=None, phase=1, trading_days=0, risk_per_trade=None,
             streak=4, buffer_pct=20.0):
    """The live picture against the rules (all money in the account currency)."""
    daily_cap = initial * rl["daily_loss_pct"] / 100.0
    daily_floor = day_start - daily_cap
    if rl["trailing"]:
        top = max(peak or initial, initial)
        overall_floor = top - initial * rl["max_loss_pct"] / 100.0
    else:
        overall_floor = initial * (1 - rl["max_loss_pct"] / 100.0)
    floor = max(daily_floor, overall_floor)
    room = equity - floor
    usable = room * (1 - buffer_pct / 100.0)
    target_pct = rl["targets_pct"][min(phase, len(rl["targets_pct"])) - 1] if rl["targets_pct"] else None
    target = initial * (1 + target_pct / 100.0) if target_pct else None
    st = {"daily_floor": round(daily_floor, 2), "overall_floor": round(overall_floor, 2), "binding_floor":
          "daily" if daily_floor >= overall_floor else "overall", "room": round(room, 2),
          "room_pct_initial": round(100.0 * room / initial, 3), "used_today": round(day_start - equity, 2),
          "daily_cap": round(daily_cap, 2), "target": round(target, 2) if target else None,
          "to_target": round(target - equity, 2) if target else None,
          "progress_pct": round(100.0 * (equity - initial) / (target - initial), 1) if target and target > initial else None,
          "trading_days": trading_days, "min_days": rl["min_days"],
          "max_risk_per_trade": round(max(0.0, usable) / streak, 2), "streak_assumed": streak,
          "buffer_pct": buffer_pct, "breached": room <= 0}
    if risk_per_trade:
        st["losses_to_floor"] = int(room // risk_per_trade) if risk_per_trade > 0 else None
    if st["breached"]:
        st["status"] = "BREACHED: equity is at or under the %s floor" % st["binding_floor"]
    elif target and equity >= target and trading_days >= rl["min_days"]:
        st["status"] = "TARGET MET: stop trading this phase and request the review"
    elif usable <= 0:
        st["status"] = "NO ROOM: today's buffer is used up; stop for the day"
    else:
        st["status"] = "OK"
    return st


def simulate(trades, rl, risk_pct, sims=2000, seed=11, phase=1, max_days=250):
    """Bootstrap whole days of R (in their real order inside each day) and run the phase.
    Returns {pass, fail_daily, fail_max, timeout, median_days, risk_pct}."""
    days = {}
    for t in trades:
        days.setdefault(t["date"], []).append(t["r"])
    day_list = list(days.values())
    if not day_list:
        return None
    rng = random.Random(seed)
    target = rl["targets_pct"][min(phase, len(rl["targets_pct"])) - 1] / 100.0
    cap_days = rl.get("max_days") or max_days
    res = {"pass": 0, "fail_daily": 0, "fail_max": 0, "timeout": 0}
    took = []
    for _ in range(sims):
        bal, peak, traded = 1.0, 1.0, 0
        outcome = "timeout"
        for d in range(cap_days):
            day = rng.choice(day_list)
            start = bal
            traded += 1
            for r in day:
                bal += risk_pct / 100.0 * r   # prop firms size from the initial balance: fixed risk
                peak = max(peak, bal)
                floor_all = (peak if rl["trailing"] else 1.0) - rl["max_loss_pct"] / 100.0
                if bal <= start - rl["daily_loss_pct"] / 100.0:
                    outcome = "fail_daily"
                    break
                if bal <= floor_all:
                    outcome = "fail_max"
                    break
            if outcome != "timeout":
                break
            if bal >= 1 + target and traded >= rl["min_days"]:
                outcome = "pass"
                took.append(d + 1)
                break
        res[outcome] += 1
    took.sort()
    out = {k: round(v / float(sims), 4) for k, v in res.items()}
    out.update(risk_pct=risk_pct, sims=sims, median_days=took[len(took) // 2] if took else None,
               trading_days_in_sample=len(day_list))
    return out


def best_risk(trades, rl, risks=(0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0), sims=2000, seed=11, phase=1):
    rows = [simulate(trades, rl, r, sims, seed, phase) for r in risks]
    rows = [r for r in rows if r]
    best = max(rows, key=lambda r: (r["pass"], -r["fail_daily"] - r["fail_max"])) if rows else None
    return {"rows": rows, "best": best}
