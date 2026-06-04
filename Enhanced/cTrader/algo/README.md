# cTrader `.algo` packaging — GODMODE_OFEA Enhanced

`.algo` is a cTrader-proprietary binary: it's a zipped folder containing the
compiled `.dll` (built from the C# source in `../Normal/`) plus a
`Manifest.json` plus optional icon. It can only be produced by the cTrader
Windows IDE or by `cAlgoBuilder.exe` — there is no Linux/Mac toolchain and
no public NuGet path for `cTrader.Automate`. (We tried in CI; it can't be
done outside a Windows host with cTrader installed.)

## Build steps (Windows host with cTrader installed)

1. **Open cTrader → cBots → Add new cBot.** Name it `GODMODE_OFEA_Enhanced`.
2. **Paste** the contents of `../Normal/GODMODE_OFEA_Enhanced.cs` into the
   main file editor.
3. **Right-click the cBot in the Solution panel → Add → Existing File** and
   add each `../Normal/Modules/*.cs` in turn. They should appear under the
   cBot in the solution tree.
4. **Build → Build cBot** (or press F5). cTrader generates the `.algo`
   at `Documents\cAlgo\Algorithms\` (path varies by Windows username).
5. **Right-click the `.algo` file → Properties → Copy full path.** The
   `.algo` is now portable.

## Distribution

Drop the `.algo` into this folder when ready. Users can then double-click
to install on any cTrader (Windows, macOS, or any platform where cTrader
runs) — including the Mac Beta. The `.algo` carries everything needed.

## Why CI doesn't build this for you

`cTrader.Automate` is a closed-source assembly redistributed only inside
cTrader's own installer. Ubuntu/macOS GitHub-Actions runners can't resolve
it via NuGet (no public package) and don't ship a cTrader install to run
the proprietary builder. The previous `.github/workflows/ctrader-build.yml`
attempt was removed for this reason — confirmed unworkable on free runners.

If you ever get a self-hosted Windows runner with cTrader installed, the
build can be automated via PowerShell + the cTrader IDE's CLI. Until then,
the workflow above is the supported path.
