<#
.SYNOPSIS
    Compile, deploy and backtest an Expert Advisor in one command.

.DESCRIPTION
    Chains the three steps that used to be manual:

      1. compile.ps1        source .mq5  ->  .ex5
      2. deploy             copy the .ex5 into the MT5 data folder, where the
                            Strategy Tester looks for it
      3. backtest.ps1       run the test and parse the report

    Stops at the first failure. If compilation fails you get the errors and
    nothing else runs, which is what an agent wants: a short, specific answer.

    Step 2 exists because MetaEditor writes the .ex5 next to the source, but
    the tester only loads Experts from <data folder>\MQL5\Experts. Without it
    the two halves of the toolchain never meet.

.PARAMETER File
    Source .mq5, relative to the repository root or absolute.

.PARAMETER Symbol
    Broker symbol name including any suffix, for example EURUSDm.

.PARAMETER CompileOnly
    Stop after a successful compile. Use during a fix-the-errors loop, where
    running a backtest each time is wasted.

.EXAMPLE
    .\scripts\build.ps1 -File src\Experts\MyEA.mq5 -Symbol EURUSDm -From 2024.01.01 -To 2024.06.30

.EXAMPLE
    .\scripts\build.ps1 -File src\Experts\MyEA.mq5 -CompileOnly -Json
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$File,

    [string]$Symbol,
    [string]$Period = 'H1',
    [string]$From   = '2024.01.01',
    [string]$To     = '2024.12.31',
    [ValidateRange(0, 4)][int]$Model = 1,
    [double]$Deposit = 10000,
    [hashtable]$Inputs,

    [switch]$CompileOnly,
    [switch]$Json
)

$ErrorActionPreference = 'Stop'

$compile  = Join-Path $PSScriptRoot 'compile.ps1'
$backtest = Join-Path $PSScriptRoot 'backtest.ps1'

# ---------------------------------------------------------------- 1. compile

$compileResult = & $compile -File $File -Json | ConvertFrom-Json

if (-not $compileResult.success) {
    $out = [PSCustomObject]@{
        stage        = 'compile'
        success      = $false
        errorCount   = $compileResult.errorCount
        warningCount = $compileResult.warningCount
        diagnostics  = $compileResult.diagnostics
        hints        = $compileResult.hints
        nextStep     = 'Fix the earliest error, then run this again. Later errors are usually knock-on noise. Read hints first, they contain the correct signatures.'
    }
    if ($Json) { $out | ConvertTo-Json -Depth 5 } else {
        Write-Host "COMPILE FAILED  $($out.errorCount) error(s)" -ForegroundColor Red
        foreach ($d in $out.diagnostics) {
            Write-Host ("  line {0,-5} error {1,-5} {2}" -f $d.line, $d.code, $d.message) -ForegroundColor Red
        }
        foreach ($h in $out.hints) { Write-Host "  hint: $h" -ForegroundColor Cyan }
        $out
    }
    exit 1
}

$ex5 = $compileResult.output

if ($CompileOnly) {
    $out = [PSCustomObject]@{
        stage        = 'compile'
        success      = $true
        warningCount = $compileResult.warningCount
        output       = $ex5
    }
    if ($Json) { $out | ConvertTo-Json -Depth 3 } else {
        Write-Host "COMPILE OK  ->  $([System.IO.Path]::GetFileName($ex5))" -ForegroundColor Green
        $out
    }
    exit 0
}

# ----------------------------------------------------------------- 2. deploy

if (-not $Symbol) {
    throw "-Symbol is required unless -CompileOnly is used. Use the broker's exact name, suffix included, for example EURUSDm."
}

$configPath = Join-Path $PSScriptRoot '..\config\paths.json'
if (-not (Test-Path -LiteralPath $configPath)) {
    throw "config\paths.json not found. Copy config\paths.example.json to config\paths.json and fill in the paths for this machine."
}
$cfg = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $cfg.dataFolder) {
    throw "'dataFolder' missing from config\paths.json. Find it in MetaTrader: File, Open Data Folder."
}

$expertsDir = Join-Path $cfg.dataFolder 'MQL5\Experts'
if (-not (Test-Path -LiteralPath $expertsDir)) {
    throw "Experts folder not found: $expertsDir. Check 'dataFolder' in config\paths.json."
}

$ex5Name = [System.IO.Path]::GetFileName($ex5)
Copy-Item -LiteralPath $ex5 -Destination (Join-Path $expertsDir $ex5Name) -Force

# --------------------------------------------------------------- 3. backtest

$btArgs = @{
    Expert  = $ex5Name
    Symbol  = $Symbol
    Period  = $Period
    From    = $From
    To      = $To
    Model   = $Model
    Deposit = $Deposit
    Json    = $true
}
if ($Inputs -and $Inputs.Count -gt 0) { $btArgs['Inputs'] = $Inputs }

$btResult = & $backtest @btArgs | ConvertFrom-Json

# Remove the deployed binary. Keeping it would leave a stale copy that the
# tester might silently reuse after a failed compile.
Remove-Item -LiteralPath (Join-Path $expertsDir $ex5Name) -Force -ErrorAction SilentlyContinue

$out = [PSCustomObject]@{
    stage           = 'backtest'
    success         = $true
    warningCount    = $compileResult.warningCount
    symbol          = $btResult.symbol
    period          = $btResult.period
    from            = $btResult.from
    to              = $btResult.to
    historyQuality  = $btResult.historyQuality
    totalTrades     = $btResult.totalTrades
    profitTrades    = $btResult.profitTrades
    lossTrades      = $btResult.lossTrades
    winRatePercent  = $btResult.winRatePercent
    averageWin      = $btResult.averageWin
    averageLoss     = $btResult.averageLoss
    payoffRatio     = $btResult.payoffRatio
    largestWin      = $btResult.largestWin
    largestLoss     = $btResult.largestLoss
    maxConsecWins   = $btResult.maxConsecWins
    maxConsecLosses = $btResult.maxConsecLosses
    netProfit       = $btResult.netProfit
    profitFactor    = $btResult.profitFactor
    expectedPayoff  = $btResult.expectedPayoff
    recoveryFactor  = $btResult.recoveryFactor
    sharpeRatio     = $btResult.sharpeRatio
    equityDrawdown  = $btResult.equityDrawdown
    reportPath      = $btResult.reportPath
    warnings        = $btResult.warnings
}

if ($Json) {
    $out | ConvertTo-Json -Depth 4
}
else {
    Write-Host "BUILD OK" -ForegroundColor Green
    Write-Host ("  {0} {1}  {2} to {3}" -f $out.symbol, $out.period, $out.from, $out.to)
    Write-Host ("  history quality {0}   {1} trades   {2:N2} net profit" -f
                $out.historyQuality, $out.totalTrades, $out.netProfit)
    Write-Host ("  win rate {0}% ({1}W / {2}L)   average win {3:N2} vs loss {4:N2}   payoff {5} to 1" -f
                $out.winRatePercent, $out.profitTrades, $out.lossTrades,
                $out.averageWin, $out.averageLoss, $out.payoffRatio)
    Write-Host ("  profit factor {0}   recovery {1}   max equity drawdown {2}" -f
                $out.profitFactor, $out.recoveryFactor, $out.equityDrawdown)
    foreach ($w in $out.warnings) { Write-Host "  WARNING: $w" -ForegroundColor Yellow }
    Write-Host "  report: $($out.reportPath)" -ForegroundColor DarkGray
    $out
}
exit 0
