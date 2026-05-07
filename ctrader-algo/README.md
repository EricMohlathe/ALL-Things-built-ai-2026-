# ctrader-algo/

This folder holds the compiled cBot binary — `GODMODE_OFEA.algo` — that Mac
cTrader (and the Linux/web cTrader builds) can import directly via
**Automate → + Add cBot → Add Existing**.

## Why this folder exists separately

The `.cs` source lives in `../ctrader/GODMODE_OFEA/`. cTrader Desktop on
**Windows** compiles that source into a `.algo` package via its built-in
IDE. cTrader on **Mac** does not include the IDE — it can only consume
already-compiled `.algo` files. So we maintain this folder as the publish
target for the compiled artifact, separate from the source.

## How to get a `.algo` file here

Three paths, in order of operator preference:

### Option A — let GitHub Actions build it for you (recommended)

The repo's `.github/workflows/ctrader-build.yml` workflow runs on every
push to the cTrader source. It uses a Windows runner, restores cTrader's
`cTrader.Automate` NuGet package, runs `dotnet build`, and packages the
result as `GODMODE_OFEA.algo`.

How to grab the build:
1. Go to the GitHub repo → **Actions** tab
2. Click the latest successful "ctrader-build" run
3. Scroll to **Artifacts** at the bottom
4. Download `GODMODE_OFEA-algo.zip`
5. Unzip → you have `GODMODE_OFEA.algo`
6. Drop it on Mac cTrader: **Automate → + Add cBot → Add Existing**

The workflow runs in a few minutes. Note: the GitHub-Actions-built
`.algo` is functionally identical to a desktop-built one but is **not
code-signed**. If your broker enforces signed-only cBots, fall back to
Option B.

### Option B — build manually on Windows cTrader Desktop

(See the prior step-by-step in the conversation. Short version:)

1. On a Windows machine or VM:
   - Install cTrader Desktop from your broker
   - Copy `../ctrader/GODMODE_OFEA/` into `Documents\cAlgo\Sources\Robots\`
   - Open cTrader → Automate → right-click `GODMODE_OFEA` → Build
2. Locate the file:
   - `Documents\cAlgo\Sources\Robots\GODMODE_OFEA\bin\Release\GODMODE_OFEA.algo`
3. Copy that `.algo` into this `ctrader-algo/` folder and commit, **or**
   transfer it directly to your Mac via shared folder / iCloud / AirDrop.

### Option C — pay a freelancer or borrow a Windows session

If you don't have Windows access at all, post the job on Fiverr/Upwork
("compile a cTrader cBot from C# source"). Send the source from
`../ctrader/GODMODE_OFEA/`, get back the `.algo`. Drop it here.

## Verifying a `.algo` is the right one

The file should be approximately 50–150 KB. Open in any zip tool — you
should see a `.dll` (the cBot assembly) and a manifest. If it's
significantly smaller or won't open, the build is broken.

## Why the folder may be empty in git

`.algo` files are build outputs, not source. We don't commit binaries by
default. The CI workflow uploads them as **build artifacts** on the
Actions tab — you download from there rather than from the file tree.

If you want to commit a known-good build for posterity (e.g. a release
tag), drop the `.algo` here and `git add` it. The `.gitignore` in this
folder allows hand-committed `.algo` files but ignores intermediate
build output.
