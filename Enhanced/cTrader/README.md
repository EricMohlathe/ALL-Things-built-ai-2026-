# Enhanced/cTrader — install on cTrader

Two paths depending on platform.

## A) Normal/ (recommended) — paste-in via cTrader IDE

Works on Windows, macOS (cTrader Beta), Linux via Wine.

1. Open cTrader → cBots → **Add new cBot** → name it `GODMODE_OFEA_Enhanced`.
2. Paste contents of `Normal/GODMODE_OFEA_Enhanced.cs` into the main editor.
3. Right-click the cBot → **Add → Existing File** for each `Normal/Modules/*.cs`.
4. **Build → Build cBot** (F5). On success, the cBot appears in the
   "cBots" tab ready to attach to a chart.
5. Right-click → **Add Instance** → set inputs (RiskPct, KellyKappa, etc.) → Start.

## B) algo/ — distribute as a single `.algo` file

See `algo/README.md`. Build path only — produces a portable `.algo` that
can be installed by double-click on any cTrader (including macOS).

## Coexistence with the base cTrader build

The Enhanced cBot is a separate project (different namespace, different
class). You can run it alongside the base `ctrader/GODMODE_OFEA/GODMODE_OFEA.cs`
build — both on the same chart if you wish. Different magic numbers, no
trade-management conflicts.
