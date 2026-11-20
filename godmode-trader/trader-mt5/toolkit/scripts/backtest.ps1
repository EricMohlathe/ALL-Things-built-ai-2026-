<#
.SYNOPSIS
    Run an MT5 Strategy Tester backtest headlessly and return parsed results.

.DESCRIPTION
    Drives terminal64.exe through a generated .ini file, waits for it to finish,
    then parses the HTML report into structured data.

    Nine behaviours this script exists to work around. All confirmed by
    experiment on 2026-08-05, MT5 build 5836.

    0. METATRADER MUST NOT ALREADY BE RUNNING.
       Start terminal64.exe /config:... while an instance is already open and
       Windows hands the command line to that instance, which ignores it. The
       launcher returns exit code 0 within a second. No report is written and
       the tester log gains not a single line, so the failure is indistinguishable
       from a bad symbol or a missing history. This script refuses to start when
       it finds the terminal running, because the alternative is a confident
       wrong diagnosis.

    1. THE AGENT PORT IS THE MOST LIKELY THING TO BREAK.
       The local tester agent binds 127.0.0.1:3000 by default. If ANY other
       program already holds that port, the terminal connects to the stranger,
       is refused, logs one line at severity 2, and abandons the run. It still
       exits with code 0 and writes no report. Nothing says "port conflict".
       This script picks a free port and passes it as Tester/Port.

    2. THE REPORT PATH MUST BE RELATIVE.
       An absolute path such as D:\out\report.htm is accepted and silently
       ignored. A relative name resolves against the terminal DATA folder.
       This is the real cause behind the "empty report from command line"
       reports on the MQL5 forum.

    3. THE .INI MUST NOT HAVE A BOM.
       PowerShell 5.1's Set-Content -Encoding utf8 writes EF BB BF, which
       corrupts the first section header. MT5 then cannot see [Common] and
       fails with "tester not started because the account is not specified".
       This script writes UTF-8 without a BOM.

    4. THE TERMINAL MUST BE WAITED ON.
       terminal64.exe is a GUI application. Use Start-Process -Wait.
       ShutdownTerminal=1 makes it exit by itself once testing completes.

    5. BOTH THE REPORT AND THE LOGS ARE UTF-16 LE.
       Read with -Encoding Unicode.

    6. THE ACCOUNT MUST ALREADY BE LOGGED IN.
       The tester refuses to start without one, even with full local history.
       Common/Login and Common/Server pin a specific saved account, which also
       keeps automation off a live account by accident.

    7. EA INPUTS COME FROM A .SET FILE, NOT THE COMMAND LINE.
       There is no ini key for individual inputs. They go in a .set file
       under MQL5\Profiles\Tester, named by Tester/ExpertParameters. Any
       input left out of the file keeps its compiled default, so a partial
       set file is safe. Format is one name=value line per input.

    8. WITHOUT A SET FILE, THE TESTER IGNORES THE COMPILED DEFAULTS.
       MetaTrader saves the last used inputs to MQL5\Profiles\Tester\
       <ExpertName>.set after every run, and reuses that file whenever
       Tester/ExpertParameters is absent. So editing a default in the
       source, recompiling and running again reproduces the OLD numbers,
       with no warning and a freshly built .ex5 on disk. Measured on
       2026-08-05: identical binary, 8 trades with no set file and 26
       with a set file naming one unrelated input.
       This script therefore writes a set file on every run. That is
       what makes a backtest a function of the source code.

    9. THE TERMINAL OUTLIVES THE PROCESS YOU WAITED ON.
       The report is written, then MetaTrader reloads its profile, opens
       charts and initialises the EA before actually exiting. Measured:
       report at 15:42:10, "exit with code 0" at 15:43:25, 75 seconds
       later. A second backtest started inside that window hits the
       already-running check in note 0 and fails, so the error lands on
       the NEXT run rather than the one that caused it. This script waits
       for the process to disappear before returning.

.PARAMETER Expert
    EA path relative to MQL5\Experts, including the .ex5 extension.
    Example: Advisors\MyEA.ex5

.PARAMETER Symbol
    Broker symbol name. Check the suffix. Exness uses EURUSDm, not EURUSD.
    A wrong name aborts the run with "symbol ... not exist".

.PARAMETER Inputs
    Hashtable of EA inputs to override, for example @{ InpRiskPercent = 0.5 }.
    Only the named inputs change; everything else keeps its default. This is
    what makes it possible to answer "which filter is costing us trades"
    without editing and recompiling the source between runs.

.EXAMPLE
    .\scripts\backtest.ps1 -Expert "Advisors\MyEA.ex5" -Symbol EURUSDm `
        -From 2024.03.01 -To 2024.05.31 -Json

.EXAMPLE
    .\scripts\backtest.ps1 -Expert "MyEA.ex5" -Symbol EURUSDm -Period M5 `
        -From 2024.01.01 -To 2024.06.30 -Inputs @{ InpUseH4Regime = $false }
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Expert,
    [Parameter(Mandatory = $true)][string]$Symbol,
    [string]$Period  = 'H1',
    [string]$From    = '2024.01.01',
    [string]$To      = '2024.12.31',

    # 0 every tick, 1 one minute OHLC, 2 open prices, 3 math, 4 real ticks
    [ValidateRange(0, 4)][int]$Model = 1,

    [double]$Deposit  = 10000,
    [string]$Currency = 'USD',
    [string]$Leverage = '1:100',

    [string]$Terminal,
    [string]$DataFolder,
    [long]$Login,
    [string]$Server,

    [hashtable]$Inputs,
    [int]$TimeoutSeconds = 1800,
    [switch]$Json
)

$ErrorActionPreference = 'Stop'

# --- Configuration -----------------------------------------------------------

$configPath = Join-Path $PSScriptRoot '..\config\paths.json'
if (Test-Path -LiteralPath $configPath) {
    $cfg = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $Terminal   -and $cfg.terminal)   { $Terminal   = $cfg.terminal }
    if (-not $DataFolder -and $cfg.dataFolder) { $DataFolder = $cfg.dataFolder }
    if (-not $Login      -and $cfg.login)      { $Login      = [long]$cfg.login }
    if (-not $Server     -and $cfg.server)     { $Server     = $cfg.server }
}
if (-not $Terminal)   { throw "terminal64.exe path not set. Add 'terminal' to config\paths.json." }
if (-not $DataFolder) { throw "MT5 data folder not set. Add 'dataFolder' to config\paths.json. Find it in MetaTrader: File, Open Data Folder." }
if (-not (Test-Path -LiteralPath $Terminal))   { throw "Terminal not found: $Terminal" }
if (-not (Test-Path -LiteralPath $DataFolder)) { throw "Data folder not found: $DataFolder" }

$expertFull = Join-Path $DataFolder "MQL5\Experts\$Expert"
if (-not (Test-Path -LiteralPath $expertFull)) {
    throw "Expert not found: $expertFull. Compile it and deploy the .ex5 into MQL5\Experts first."
}

# --- MetaTrader must not already be running. See note 4. ---------------------

$running = @(Get-Process -Name 'terminal64' -ErrorAction SilentlyContinue |
             Where-Object { $_.Path -eq $Terminal })
if ($running.Count -gt 0) {
    $pids = ($running | ForEach-Object { $_.Id }) -join ', '
    throw @"
MetaTrader 5 is already running (PID $pids) from $Terminal.

Launching terminal64.exe with /config: while an instance is already open does
not start a test. Windows hands the command line to the running instance, which
ignores it, and the launcher exits with code 0. No report is written and nothing
appears in the tester log, so the failure looks like a data or symbol problem.

Close MetaTrader 5 and run this again.
"@
}

# --- Pick a free agent port. See note 1. -------------------------------------

function Test-PortFree([int]$portNumber) {
    $inUse = Get-NetTCPConnection -LocalPort $portNumber -State Listen -ErrorAction SilentlyContinue
    return ($null -eq $inUse)
}

$port = $null
foreach ($candidate in 3000..3050) {
    if (Test-PortFree $candidate) { $port = $candidate; break }
}
if (-not $port) { throw "No free TCP port found in 3000-3050 for the tester agent." }
if ($port -ne 3000) {
    Write-Verbose "Port 3000 is taken by another program. Using $port for the tester agent."
}

# --- Build the .ini. Relative report name, no BOM. See notes 2 and 3. --------

$stamp      = Get-Date -Format 'yyyyMMdd-HHmmss'
$reportName = "bt-$stamp.htm"
$reportInData = Join-Path $DataFolder $reportName

# --- EA inputs, if any. See note 7. ------------------------------------------

# A set file is written on EVERY run, even with no overrides. Passing one is
# what makes the test read the EA's compiled defaults. See note 8.
$setDir = Join-Path $DataFolder 'MQL5\Profiles\Tester'
if (-not (Test-Path -LiteralPath $setDir)) {
    New-Item -ItemType Directory -Path $setDir -Force | Out-Null
}
$setName = "auto-$stamp.set"
$setPath = Join-Path $setDir $setName

# One "name=value" line per input. Values must be invariant culture:
# a Vietnamese or German locale would write 0,75 and MT5 would read 0.
$setLines = @("; generated by backtest.ps1 $stamp")
if ($Inputs) {
    $setLines += foreach ($key in $Inputs.Keys) {
        $raw = $Inputs[$key]
        $val = if ($raw -is [bool])   { if ($raw) { 'true' } else { 'false' } }
               elseif ($raw -is [double] -or $raw -is [decimal] -or $raw -is [single]) {
                   [string]::Format([cultureinfo]::InvariantCulture, '{0}', $raw)
               }
               else { "$raw" }
        "$key=$val"
    }
}
[System.IO.File]::WriteAllText($setPath, (($setLines -join "`r`n") + "`r`n"),
                               (New-Object System.Text.UTF8Encoding($false)))

$iniLines = @(
    '[Common]'
)
if ($Login)  { $iniLines += "Login=$Login" }
if ($Server) { $iniLines += "Server=$Server" }
$iniLines += @(
    ''
    '[Tester]'
    "Expert=$Expert"
    "Symbol=$Symbol"
    "Period=$Period"
    "Model=$Model"
    'ExecutionMode=0'
    'Optimization=0'
    'OptimizationCriterion=0'
    "FromDate=$From"
    "ToDate=$To"
    'ForwardMode=0'
    "Deposit=$Deposit"
    "Currency=$Currency"
    "Leverage=$Leverage"
    'UseLocal=1'
    'UseRemote=0'
    'UseCloud=0'
    'Visual=0'
    "Port=$port"
    "Report=$reportName"
    'ReplaceReport=1'
    'ShutdownTerminal=1'
)
if ($setName) { $iniLines += "ExpertParameters=$setName" }

$iniPath = Join-Path $env:TEMP "mt5-backtest-$stamp.ini"
[System.IO.File]::WriteAllText($iniPath, ($iniLines -join "`r`n") + "`r`n",
                               (New-Object System.Text.UTF8Encoding($false)))

# --- Run. See note 4. --------------------------------------------------------

$sw = [Diagnostics.Stopwatch]::StartNew()
$proc = Start-Process -FilePath $Terminal -ArgumentList "/config:`"$iniPath`"" -PassThru
if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
    $proc.Kill()
    throw "Terminal did not exit within $TimeoutSeconds seconds. ShutdownTerminal may have failed."
}
$sw.Stop()
Remove-Item -LiteralPath $iniPath -Force -ErrorAction SilentlyContinue

# The process we waited on is not the whole story. See note 9. Wait for the
# terminal to actually leave the process table, otherwise the next run trips
# the already-running guard at the top of this script and fails for a reason
# that has nothing to do with it.
$lingerDeadline = (Get-Date).AddSeconds(180)
while ((Get-Date) -lt $lingerDeadline) {
    $lingering = @(Get-Process -Name 'terminal64' -ErrorAction SilentlyContinue |
                   Where-Object { $_.Path -eq $Terminal })
    if ($lingering.Count -eq 0) { break }
    Start-Sleep -Milliseconds 500
}

if (-not (Test-Path -LiteralPath $reportInData)) {
    $hint = "No report at $reportInData. Check $DataFolder\Tester\logs for the reason. " +
            "The usual causes are a wrong symbol name (check the broker's suffix), " +
            "an account that is not logged in, or a date range with no history."
    throw $hint
}

# Move the report and its charts out of the data folder into the repo.
$reportDir = Join-Path $PSScriptRoot '..\reports'
if (-not (Test-Path -LiteralPath $reportDir)) {
    New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
}
$reportFinal = Join-Path $reportDir $reportName
Move-Item -LiteralPath $reportInData -Destination $reportFinal -Force
# MT5 writes companion PNG charts next to the report.
Get-ChildItem -LiteralPath $DataFolder -Filter "$([System.IO.Path]::GetFileNameWithoutExtension($reportName))*.png" -ErrorAction SilentlyContinue |
    ForEach-Object { Move-Item -LiteralPath $_.FullName -Destination $reportDir -Force }

# --- Parse. See note 5. ------------------------------------------------------

$raw   = Get-Content -LiteralPath $reportFinal -Raw -Encoding Unicode
$text  = ($raw -replace '<[^>]+>', "`n") -replace '&nbsp;', ' '
$cells = $text -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }

function Get-Metric([string]$label) {
    for ($i = 0; $i -lt $cells.Count - 1; $i++) {
        if ($cells[$i] -eq "$label`:" -or $cells[$i] -eq $label) { return $cells[$i + 1] }
    }
    # Several labels carry a qualifier the caller should not have to know:
    # "Profit Trades (% of total):", "Maximum consecutive wins ($):".
    # Fall back to a prefix match so a MetaQuotes wording change does not
    # silently turn a metric into a blank column.
    for ($i = 0; $i -lt $cells.Count - 1; $i++) {
        if ($cells[$i].StartsWith($label)) { return $cells[$i + 1] }
    }
    return $null
}
function Get-Number([string]$label) {
    $v = Get-Metric $label
    if ($null -eq $v) { return $null }
    if ($v -match '^\s*(-?[\d\s,]+\.?\d*)') {
        return [double](($Matches[1] -replace '[\s,]', ''))
    }
    return $null
}

$quality = Get-Metric 'History Quality'

# "Profit Trades" reads "13 (50.00%)". Keep both halves: the count matters for
# whether the sample means anything, the percentage is what people ask for.
function Get-Percent([string]$label) {
    $v = Get-Metric $label
    if ($v -match '\(([\d.]+)%\)') { return [double]$Matches[1] }
    return $null
}

$avgWin  = Get-Number 'Average profit trade'
$avgLoss = Get-Number 'Average loss trade'

# Average win divided by average loss. Win rate on its own is the most
# misleading number in the report; paired with this it becomes usable.
# A system winning 40% of the time at 2.3 to 1 is healthy. One winning
# 75% at 0.4 to 1 is not, and the win rate alone cannot tell them apart.
$payoffRatio = $null
if ($avgWin -and $avgLoss -and $avgLoss -ne 0) {
    $payoffRatio = [math]::Round($avgWin / [math]::Abs($avgLoss), 2)
}

$result = [PSCustomObject]@{
    expert          = $Expert
    symbol          = $Symbol
    period          = $Period
    from            = $From
    to              = $To
    model           = $Model
    historyQuality  = $quality
    bars            = Get-Number 'Bars'
    ticks           = Get-Number 'Ticks'
    netProfit       = Get-Number 'Total Net Profit'
    grossProfit     = Get-Number 'Gross Profit'
    grossLoss       = Get-Number 'Gross Loss'
    profitFactor    = Get-Number 'Profit Factor'
    expectedPayoff  = Get-Number 'Expected Payoff'
    recoveryFactor  = Get-Number 'Recovery Factor'
    sharpeRatio     = Get-Number 'Sharpe Ratio'
    balanceDrawdown = Get-Metric 'Balance Drawdown Maximal'
    equityDrawdown  = Get-Metric 'Equity Drawdown Maximal'
    totalTrades     = Get-Number 'Total Trades'
    totalDeals      = Get-Number 'Total Deals'
    profitTrades    = Get-Number 'Profit Trades'
    lossTrades      = Get-Number 'Loss Trades'
    winRatePercent  = Get-Percent 'Profit Trades'
    averageWin      = $avgWin
    averageLoss     = $avgLoss
    payoffRatio     = $payoffRatio
    largestWin      = Get-Number 'Largest profit trade'
    largestLoss     = Get-Number 'Largest loss trade'
    maxConsecWins   = Get-Number 'Maximum consecutive wins'
    maxConsecLosses = Get-Number 'Maximum consecutive losses'
    elapsedSeconds  = [math]::Round($sw.Elapsed.TotalSeconds, 1)
    agentPort       = $port
    reportPath      = $reportFinal
    warnings        = @()
}

# History quality below 100% makes every other number unreliable.
if ($quality -and $quality -notmatch '^100') {
    $result.warnings += "History quality is $quality, not 100%. Results are not trustworthy. Download more history before believing these numbers."
}
if ($result.totalTrades -eq 0) {
    $result.warnings += 'Zero trades. The EA never entered. Check entry conditions, spread filter and symbol.'
}

if ($Json) {
    $result | ConvertTo-Json -Depth 4
}
else {
    Write-Host "$Expert on $Symbol $Period, $From to $To" -ForegroundColor Cyan
    Write-Host ("  history quality {0}   {1} trades   {2:N2} net profit" -f
                $result.historyQuality, $result.totalTrades, $result.netProfit)
    Write-Host ("  win rate {0}% ({1}W / {2}L)   average win {3:N2} vs loss {4:N2}   payoff {5} to 1" -f
                $result.winRatePercent, $result.profitTrades, $result.lossTrades,
                $result.averageWin, $result.averageLoss, $result.payoffRatio)
    Write-Host ("  profit factor {0}   recovery {1}   sharpe {2}" -f
                $result.profitFactor, $result.recoveryFactor, $result.sharpeRatio)
    Write-Host ("  max equity drawdown {0}   worst losing streak {1}" -f
                $result.equityDrawdown, $result.maxConsecLosses)
    foreach ($w in $result.warnings) { Write-Host "  WARNING: $w" -ForegroundColor Yellow }
    Write-Host "  report: $reportFinal" -ForegroundColor DarkGray
    $result
}
