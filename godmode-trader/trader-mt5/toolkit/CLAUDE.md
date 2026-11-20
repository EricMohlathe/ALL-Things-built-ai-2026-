# CLAUDE.md

The rules for this repository live in **[AGENTS.md](AGENTS.md)**. Read that
file first and follow it exactly. This file only tells you where things are.

Both files are kept deliberately short because they load on every request.

## Knowledge base

The knowledge lives under `.agents/skills/`. That directory name is Codex's
convention, but the files are plain Markdown and apply to you equally.

Read the one you need. Do not read all of them by reflex.

| Read this file | When |
|---|---|
| `.agents/skills/mql5-patterns/SKILL.md` | Before writing any EA logic |
| `.agents/skills/mql5-compile-errors/SKILL.md` | When `compile.ps1` reports errors |
| `.agents/skills/mql5-strategy-intake/SKILL.md` | When the user describes a strategy |
| `.agents/skills/mt5-backtest-report/SKILL.md` | After a backtest, when explaining the numbers |

Each `SKILL.md` lists further files under its own `references/` directory. Open
those only when the `SKILL.md` says they are relevant, so that a large
knowledge base does not cost tokens on every request.

## The two commands

```powershell
.\scripts\compile.ps1  -File "src\Experts\<name>.mq5" -Json
.\scripts\backtest.ps1 -Expert "<name>.ex5" -Symbol <symbol> -From 2024.01.01 -To 2024.12.31 -Json
```

Both return JSON. `compile.ps1` includes a `hints` field with the correct
signature of any built-in function called incorrectly. Read it before guessing.

## Start from a template

Copy one of these to `src/Experts/<name>.mq5` and fill in the STRATEGY section.
Never start an EA from an empty file.

- `templates/EA_Template.mq5` for market entries with a fixed point stop.
- `templates/EA_Template_Structural.mq5` for pending limit orders with a stop
  and target computed from structure.

Section 3 of [AGENTS.md](AGENTS.md) explains how to tell which one a strategy
needs.

## Recording what you learn is mandatory

See section 6 of [AGENTS.md](AGENTS.md). New compile errors and newly verified
snippets go back into the skill reference files. This is what makes the
repository improve over time, and it is the reason it exists.
