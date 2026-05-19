# ctrader-algo/

This folder holds the compiled cBot binary — `GODMODE_OFEA.algo` — that Mac
cTrader Desktop and the web cTrader builds can import via
**Automate → + Add cBot → Add Existing**.

## Why this folder exists

The `.cs` source lives in `../ctrader/GODMODE_OFEA/`. cTrader Desktop on
**Windows** compiles that source into a `.algo` package via its built-in
IDE. cTrader on **Mac** does not include the IDE — it can only consume
already-compiled `.algo` files. So this folder is the publish target for
the compiled artifact, separate from the source.

## Honest status: CI build is not available

An earlier `.github/workflows/ctrader-build.yml` attempted to compile
`.algo` headlessly on a GitHub Actions runner. **It does not work.** The
cTrader API DLLs (`cAlgo.API.dll`, `cAlgo.API.Alert.dll`) ship inside the
cTrader Desktop installer and are not available as a public NuGet package
under any redistributable license. Every attempted CI run failed at
compile-time because the runner has no way to resolve the `cAlgo.API`
namespace.

We removed the workflow. **The supported build path is manual on Windows
cTrader Desktop.** See below.

## How to produce a `.algo` file

### Build manually on Windows cTrader Desktop

1. **Get Windows.** Pick whichever you can use:
   - Parallels Desktop / VMware Fusion / UTM (Windows VM on your Mac)
   - A separate Windows PC
   - A cloud Windows VPS (~$10–20/month) — Vultr, Contabo, AWS EC2
   - A coworking PC with cTrader installed

2. **Install cTrader Desktop on the Windows machine** — from your broker's
   site or `ctrader.com`. Free, ~500 MB.

3. **Copy the source into the cAlgo Sources folder:**
   ```
   Documents\cAlgo\Sources\Robots\GODMODE_OFEA\
   ├── GODMODE_OFEA.cs
   └── Modules\
       ├── OFCommon.cs
       ├── DeltaEngine.cs
       └── (all other .cs files)
   ```

4. **Open cTrader → Automate → right-click `GODMODE_OFEA` → Build.**
   Wait for "Build succeeded".

5. **Find the compiled file at:**
   ```
   Documents\cAlgo\Sources\Robots\GODMODE_OFEA\bin\Release\GODMODE_OFEA.algo
   ```

6. **Transfer to Mac** — Parallels shared folder, iCloud, AirDrop, USB,
   email-to-self, whatever's easiest.

7. **Mac cTrader → Automate → + Add cBot → Add Existing → select the file.**

### Optional: commit the `.algo` here

If you want the binary archived in the repo (so anyone can grab it
without rebuilding), drop it in this folder and commit:

```bash
cp /path/to/GODMODE_OFEA.algo ctrader-algo/
git add ctrader-algo/GODMODE_OFEA.algo
git commit -m "Pre-built v1.x.y .algo (Windows cTrader Desktop)"
git push
```

The `.gitignore` in this folder allows `.algo` files specifically while
excluding intermediate build output.

### If you can't access Windows at all

Two fallback options:

1. **Pay a freelancer** to compile it for you. Fiverr/Upwork: search
   "compile cTrader cBot". Hand them the `ctrader/GODMODE_OFEA/` folder,
   pay $5–20, get back the `.algo`.

2. **Use MT5 on Mac instead.** MetaTrader 5 has a native macOS app and the
   build is the same logic. The repo's `MT5_Unified/` is what you'd
   use. MetaEditor is included in the Mac MT5 download — no Windows
   needed.

## Verifying a `.algo` is valid

Size should be roughly **50–200 KB**. Open in any zip tool — you should
see a `.dll` and a manifest. If it's <10 KB or refuses to open, the build
is broken; rebuild.
