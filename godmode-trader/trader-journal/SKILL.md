---
name: trader-journal
description: >-
  Trading Journal. Records every decision (WATCH, REVIEW, SKIP, PAPER, LIVE)
  with its entry, stop, target, horizon and cost estimate BEFORE the outcome,
  then the later observation separately, and works out the result in R after
  costs. Imports the current trade plan, or the last DEX scan's research
  rows. Refuses an observation dated before its decision, and marks a result
  without a stop or a cost estimate as incomplete. Shows a dashboard (scans,
  reviewed pairs, decisions, complete outcomes, win rate, expectancy, by
  setup, data quality), writes an HTML page, and keeps a lessons file the
  desk reads each session. Use when the user says "journal", "log this
  trade", "paper trade it", "record the decision", "how am I doing", "my
  stats", "win rate", "what did I learn", "lesson", or after a trade closes.
argument-hint: "[add|from-plan|from-dex|observe|list|stats|html|lesson|lessons]"
---

# trader-journal

The journal is where an edge is proven or disproven with your own fills,
your own discipline and your own costs. A backtest is the best case; the
journal is the honest one.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/journal.py" add --symbol EURUSD --decision PAPER --side buy \
    --entry 1.16285 --stop 1.16160 --target 1.16535 --costs 0.8pips --setup GM01 --horizon "to 16:55 London"
python3 "${CLAUDE_SKILL_DIR}/journal.py" from-plan                     # trader/plan.json as a decision
python3 "${CLAUDE_SKILL_DIR}/journal.py" from-dex --labels WATCH REVIEW   # the last DEX scan
python3 "${CLAUDE_SKILL_DIR}/journal.py" observe 7 --outcome target    # or --price 1.16420
python3 "${CLAUDE_SKILL_DIR}/journal.py" list --open
python3 "${CLAUDE_SKILL_DIR}/journal.py" stats                         # the dashboard
python3 "${CLAUDE_SKILL_DIR}/journal.py" html                          # trader/journal.html
python3 "${CLAUDE_SKILL_DIR}/journal.py" lesson "No breakouts the hour before CPI" --tag news
python3 "${CLAUDE_SKILL_DIR}/journal.py" lessons --tag news
```

## The file

`trader/journal.csv`, one row a decision, opens in Google Sheets or Excel:

ID | Timestamp | Chain | Symbol | Pair address | Snapshot price | Decision |
Side | Setup | Source | Hypothetical entry | Stop assumption | Target
assumption | Costs/slippage assumption | Horizon | Later observed price |
Observed at | Simulated outcome | R | Notes

The guide's twelve columns plus the pack's own (ID, Symbol, Side, Setup,
Source, Horizon, Observed at, R).

## The rules it enforces

1. A PAPER or LIVE decision needs its entry and stop at the time of the
   decision, and the stop must be on the losing side.
2. Costs (`--costs 0.8pips`, `0.1%`, `12bps` or a price distance) are part of
   the decision. Without them the result is "incomplete" and carries no R.
3. An observation dated before its decision is refused.
4. WATCH / REVIEW / SKIP rows are research: they get an observation but no R.
5. A later price is not proof that a hypothetical order would have filled.

## The dashboard

`stats` shows total scans and reviewed pairs (from trader/dex), decisions by
label, complete outcomes, open and incomplete ones, win rate, expectancy and
total in R, the same by setup, and data quality (snapshot rows without a
price, decisions without costs). Under 30 complete outcomes it says so:
that is too few to judge anything.

## Lessons

`lesson` appends one dated line to `trader/lessons.md`. The desk prints the
latest three each session, and the reflector agent proposes new ones after a
review. Keep them short, specific and testable ("skip GM01 on ECB days"), and
test a lesson in `/trader-lab` before it becomes a rule.

## Where it goes next

- `/trader-propfirm sim --journal trader/journal.csv` gives the pass odds of
  a challenge from your own record.
- `/trader-lab` compares your live R to the setup's backtest R: a large gap
  is execution, costs or discipline.

This is not financial advice.
