# Notice

This folder is the MT5 Agent Toolkit by Giang Vuong Hoang, copied unmodified under
the MIT License (see LICENSE in this folder): the verified MQL5 patterns, the
compile-error reference, the strategy-intake and backtest-report guides, the EA
templates, the PowerShell compile / backtest / build scripts and the two example
strategies.

It is a self-contained workspace for Windows with MetaTrader 5 installed: copy this
folder to that machine, run `scripts/setup.ps1`, then follow `SETUP.md`. Inside it,
`.agents/skills/` holds the toolkit's own agent guides; GODMODE Trader's
`/trader-mt5` skill points to them by path.

The GODMODE Expert Advisors themselves live in `MT5_MasterLibrary/Experts/GODMODE/`
of the parent repository; `/trader-lab` tests the same setups in Python first.
