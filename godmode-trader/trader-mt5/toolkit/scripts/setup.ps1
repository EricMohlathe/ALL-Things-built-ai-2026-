<#
.SYNOPSIS
    Find MetaTrader 5 on this machine and write config\paths.json.

.DESCRIPTION
    Run this once after cloning. It answers the question every other script
    needs: where is MetaTrader on THIS machine.

    There is no fixed answer. MetaTrader keeps its working files in
    %APPDATA%\MetaQuotes\Terminal\<32 hex characters>, and that hex string is
    derived from the installation path, so it differs on every machine and
    changes if the platform is reinstalled elsewhere. Asking a person to find
    it and paste it into a JSON file is where setup usually fails.

    This script instead:
      - scans %APPDATA%\MetaQuotes\Terminal for real data folders
      - reads origin.txt in each one to find the matching installation
      - reads the terminal logs to recover the account number and trade server
      - ranks them by most recently used
      - writes config\paths.json

    If it finds more than one, it lists them and asks. If it finds none, it
    says what to check.

.PARAMETER Force
    Overwrite an existing config\paths.json.

.EXAMPLE
    .\scripts\setup.ps1
#>
[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$configDir  = Join-Path $PSScriptRoot '..\config'
$configPath = Join-Path $configDir 'paths.json'

if ((Test-Path -LiteralPath $configPath) -and -not $Force) {
    Write-Host "config\paths.json already exists. Re-run with -Force to overwrite it." -ForegroundColor Yellow
    Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | Write-Host
    exit 0
}

Write-Host "Looking for MetaTrader 5 on this machine..." -ForegroundColor Cyan

# --- Collect candidate data folders ------------------------------------------

$terminalRoot = Join-Path $env:APPDATA 'MetaQuotes\Terminal'
$candidates   = @()

if (Test-Path -LiteralPath $terminalRoot) {
    foreach ($dir in Get-ChildItem -LiteralPath $terminalRoot -Directory -ErrorAction SilentlyContinue) {

        # Real data folders are named with a 32 character hash. "Common" and
        # "Community" live alongside them and are not data folders.
        if ($dir.Name -notmatch '^[0-9A-Fa-f]{32}$') { continue }

        $expertsDir = Join-Path $dir.FullName 'MQL5\Experts'
        if (-not (Test-Path -LiteralPath $expertsDir)) { continue }

        # origin.txt records which installation this data folder belongs to.
        $installDir = $null
        $originFile = Join-Path $dir.FullName 'origin.txt'
        if (Test-Path -LiteralPath $originFile) {
            $installDir = (Get-Content -LiteralPath $originFile -Raw).Trim()
        }

        $terminalExe   = $null
        $metaEditorExe = $null
        if ($installDir -and (Test-Path -LiteralPath $installDir)) {
            $t = Join-Path $installDir 'terminal64.exe'
            $m = Join-Path $installDir 'MetaEditor64.exe'
            if (Test-Path -LiteralPath $t) { $terminalExe   = $t }
            if (Test-Path -LiteralPath $m) { $metaEditorExe = $m }
        }

        # Most recent log tells us which terminal is actually in use.
        $lastUsed = $dir.LastWriteTime
        $logDir   = Join-Path $dir.FullName 'logs'
        $logs     = @()
        if (Test-Path -LiteralPath $logDir) {
            $logs = @(Get-ChildItem -LiteralPath $logDir -Filter '2*.log' -ErrorAction SilentlyContinue |
                      Sort-Object Name -Descending)
            if ($logs.Count -gt 0) { $lastUsed = $logs[0].LastWriteTime }
        }

        # The logs also record the last successful login, which saves the user
        # from typing an account number and a server name by hand.
        $login  = $null
        $server = $null
        foreach ($log in ($logs | Select-Object -First 5)) {
            $hit = Get-Content -LiteralPath $log.FullName -Encoding Unicode -ErrorAction SilentlyContinue |
                   Select-String -Pattern "'(\d+)': authorized on (\S+)" |
                   Select-Object -Last 1
            if ($hit) {
                $login  = [long]$hit.Matches[0].Groups[1].Value
                $server = $hit.Matches[0].Groups[2].Value
                break
            }
        }

        $candidates += [PSCustomObject]@{
            DataFolder  = $dir.FullName
            InstallDir  = $installDir
            Terminal    = $terminalExe
            MetaEditor  = $metaEditorExe
            IncludePath = (Join-Path $dir.FullName 'MQL5')
            Login       = $login
            Server      = $server
            LastUsed    = $lastUsed
            Complete    = ($null -ne $terminalExe -and $null -ne $metaEditorExe)
        }
    }
}

$candidates = @($candidates | Sort-Object -Property @{Expression='Complete';Descending=$true},
                                                    @{Expression='LastUsed';Descending=$true})

# --- Nothing found -----------------------------------------------------------

if ($candidates.Count -eq 0) {
    Write-Host ""
    Write-Host "No MetaTrader 5 data folder found." -ForegroundColor Red
    Write-Host ""
    Write-Host "Checked: $terminalRoot"
    Write-Host ""
    Write-Host "Usual reasons:"
    Write-Host "  - MetaTrader 5 is installed but has never been opened. Open it once and log in."
    Write-Host "  - It is installed for a different Windows user."
    Write-Host "  - It runs in portable mode, so the data lives next to the .exe rather than in AppData."
    Write-Host ""
    Write-Host "In MetaTrader, File then Open Data Folder shows the correct path. Copy"
    Write-Host "config\paths.example.json to config\paths.json and fill it in by hand."
    exit 1
}

# --- Choose ------------------------------------------------------------------

$chosen = $null

if ($candidates.Count -eq 1) {
    $chosen = $candidates[0]
    Write-Host "Found one installation." -ForegroundColor Green
}
else {
    Write-Host ""
    Write-Host "Found $($candidates.Count) MetaTrader data folders:" -ForegroundColor Yellow
    Write-Host ""
    for ($i = 0; $i -lt $candidates.Count; $i++) {
        $c = $candidates[$i]
        Write-Host ("  [{0}] {1}" -f ($i + 1), $(if ($c.InstallDir) { $c.InstallDir } else { 'installation unknown' })) -ForegroundColor White
        Write-Host ("      account    {0}" -f $(if ($c.Login) { "$($c.Login) on $($c.Server)" } else { 'never logged in' }))
        Write-Host ("      last used  {0:yyyy-MM-dd HH:mm}" -f $c.LastUsed)
        if (-not $c.Complete) {
            Write-Host  "      incomplete: the matching installation was not found on disk" -ForegroundColor DarkYellow
        }
        Write-Host ""
    }
    $answer = Read-Host "Which one do you trade on? Enter a number, or press Enter for 1"
    if ([string]::IsNullOrWhiteSpace($answer)) { $answer = '1' }
    $index = 0
    if (-not [int]::TryParse($answer, [ref]$index) -or $index -lt 1 -or $index -gt $candidates.Count) {
        Write-Host "Not a valid choice." -ForegroundColor Red
        exit 1
    }
    $chosen = $candidates[$index - 1]
}

if (-not $chosen.Complete) {
    Write-Host ""
    Write-Host "That data folder exists but its MetaTrader installation was not found." -ForegroundColor Red
    Write-Host "Expected at: $($chosen.InstallDir)"
    Write-Host "Reinstall MetaTrader, or edit config\paths.json by hand afterwards."
    Write-Host ""
}

# --- Write -------------------------------------------------------------------

if (-not (Test-Path -LiteralPath $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

$config = [ordered]@{
    metaEditor  = $chosen.MetaEditor
    terminal    = $chosen.Terminal
    dataFolder  = $chosen.DataFolder
    includePath = $chosen.IncludePath
}
if ($chosen.Login)  { $config.login  = $chosen.Login }
if ($chosen.Server) { $config.server = $chosen.Server }

# UTF-8 without a BOM. Several MetaTrader and PowerShell paths choke on a BOM.
[System.IO.File]::WriteAllText($configPath,
    ($config | ConvertTo-Json),
    (New-Object System.Text.UTF8Encoding($false)))

Write-Host ""
Write-Host "Wrote config\paths.json" -ForegroundColor Green
Write-Host ""
Write-Host ("  MetaEditor   {0}" -f $config.metaEditor)
Write-Host ("  Terminal     {0}" -f $config.terminal)
Write-Host ("  Data folder  {0}" -f $config.dataFolder)
if ($config.login) {
    Write-Host ("  Account      {0} on {1}" -f $config.login, $config.server)
}
else {
    Write-Host  "  Account      not detected. Log in to MetaTrader once, then run this again."  -ForegroundColor Yellow
    Write-Host  "               The Strategy Tester refuses to start without an account."       -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Next: check your symbol name in Market Watch. Brokers add suffixes," -ForegroundColor Cyan
Write-Host "so it may be EURUSDm rather than EURUSD. Then close MetaTrader and run:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  .\scripts\build.ps1 -File templates\EA_Template.mq5 -Symbol <your symbol> -From 2024.01.01 -To 2024.06.30"
Write-Host ""
