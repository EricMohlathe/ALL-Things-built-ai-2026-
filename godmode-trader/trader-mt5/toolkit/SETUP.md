# Setup

One-time setup on a new Windows machine. Roughly 30 minutes.

Work through it in order. Step 6 is the one that silently breaks everything if
skipped, and nothing will tell you that is the reason.

---

## 1. Windows

Windows 10 or 11. This is not optional. Compiling and backtesting cannot be
automated on macOS: MetaTrader runs there through a Wine compatibility layer,
MetaQuotes does not support driving MetaEditor from the command line under it,
and the Strategy Tester agent has no macOS build.

You can write code, use Git and read the knowledge base on a Mac. You cannot
compile or backtest.

## 2. MetaTrader 5

Install the build your broker provides, not a generic one. Log in to your
account and leave it logged in.

Then find your data folder: **File → Open Data Folder** in MetaTrader. Copy
that path, you need it in step 5. It looks like:

```
C:\Users\<you>\AppData\Roaming\MetaQuotes\Terminal\<32 hex characters>
```

The hex string is different on every machine. Do not copy it from anyone else.

## 3. Git

Install from [git-scm.com](https://git-scm.com). Accept the defaults.

Then clone this repository somewhere outside Program Files, for example
`D:\mql5-workspace`.

## 4. PowerShell execution policy

Windows blocks unsigned scripts by default. Every script in this repository
will refuse to start until you allow them. Open PowerShell and run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

This applies to your user account only and does not weaken the machine.

## 5. config\paths.json

One command:

```powershell
.\scripts\setup.ps1
```

It scans `%APPDATA%\MetaQuotes\Terminal`, matches each data folder to its
installation through `origin.txt`, reads your account number and trade server
out of the terminal logs, and writes `config\paths.json` for you.

If more than one MetaTrader is installed it lists them with the account and the
last time each was used, and asks which one you trade on.

Expected output:

```
Found one installation.

Wrote config\paths.json

  MetaEditor   C:\Program Files\MetaTrader 5\MetaEditor64.exe
  Terminal     C:\Program Files\MetaTrader 5\terminal64.exe
  Data folder  C:\Users\you\AppData\Roaming\MetaQuotes\Terminal\D0E8...
  Account      12345678 on YourBroker-MT5Demo
```

If it reports that the account was not detected, open MetaTrader, log in, close
it, and run `.\scripts\setup.ps1 -Force` again. The Strategy Tester refuses to
start without an account.

`paths.json` is not committed to Git. It holds your account number and paths
that are specific to this machine. To fill it in by hand instead, copy
`config\paths.example.json` to `config\paths.json` and edit it.

## 6. Codex sandbox mode

**Skip this and the agent cannot run anything.**

Open `C:\Users\<you>\.codex\config.toml` and make sure it contains:

```toml
[windows]
sandbox = "unelevated"
```

The other mode, `elevated`, runs commands as a separate low-privilege Windows
user. That user cannot read your saved credentials, so every command dies with:

```
windows sandbox: CryptUnprotectData failed: 2148073483
```

The agent will retry, fail again, and then report that it could not determine
the result. Nothing in that message mentions the sandbox setting. On one
measurement the failed attempt burned three times the tokens of the successful
one, so this costs quota as well as time.

## 7. Check your symbol name

Brokers rename instruments. Open **Market Watch** in MetaTrader and read the
exact name.

Exness, for example, uses `EURUSDm`, `XAUUSDm`, `BTCUSDm`. Every symbol carries
the suffix. Other brokers use `.m`, `.raw`, `x`, or nothing at all.

A wrong symbol name does not produce a warning. The backtest aborts:

```
Tester   symbol EURUSD not exist
```

## 8. Verify

Close MetaTrader first, then:

```powershell
.\scripts\build.ps1 -File templates\EA_Template.mq5 -Symbol <your symbol> -From 2024.01.01 -To 2024.06.30
```

Expected: a compile with zero errors, then a backtest summary with history
quality 100% and a non-zero trade count.

The template's built-in strategy is a plain moving average cross and will
probably lose money. That is fine and expected. This step proves the toolchain
works, not that the strategy is any good.

---

## When something goes wrong

### The backtest produces no report, and the terminal exits with code 0

Almost always a **port conflict**. The Strategy Tester agent needs a free TCP
port starting at 3000. If another program holds it, MetaTrader connects to that
program, is refused, and abandons the run without saying why.

`backtest.ps1` scans 3000 to 3050 and uses the first free port, so this should
not reach you. To check by hand:

```powershell
Get-NetTCPConnection -LocalPort 3000 -State Listen |
  ForEach-Object { Get-Process -Id $_.OwningProcess }
```

### "tester not started because the account is not specified"

MetaTrader is not logged in, or `login` and `server` in `config\paths.json` do
not match a saved account. The tester refuses to run without an account even
when all the history is already on disk.

### "symbol ... not exist"

Wrong symbol name. See step 7.

### The agent cannot run any command

See step 6.

### A script will not start at all

See step 4.

### MetaTrader is open while a backtest runs

Close it. Two terminals cannot share one data folder. Automation launches its
own instance and exits when finished.
