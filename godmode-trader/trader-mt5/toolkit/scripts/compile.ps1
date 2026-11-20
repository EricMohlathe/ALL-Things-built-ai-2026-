<#
.SYNOPSIS
    Compile an MQL5 source file with MetaEditor and return structured results.

.DESCRIPTION
    Wraps metaeditor64.exe so an AI agent can compile and read the errors
    without a human in the loop.

    Three MetaEditor behaviours this script exists to work around. All three
    were confirmed by experiment on 2026-08-05, MetaEditor build 5836.

    1. MetaEditor is a GUI application. Called directly it DETACHES and returns
       in about 100 ms with no exit code, no log and no .ex5. It must be run
       through Start-Process -Wait.

    2. The exit code is NOT a success indicator, and reads backwards.
       A clean compile returns 1. A failed compile returns 0. The most likely
       explanation is that MetaEditor returns the number of files it compiled
       successfully. Either way, a script that treats 0 as success reports
       every failure as a pass. Never trust it. Parse the log instead.

    3. The log is UTF-16 LE with a BOM (FF FE). Read with -Encoding Unicode.
       Reading it as ANSI yields text with a null byte between every character.

    A fourth trap concerns #include. MetaEditor resolves angle-bracket includes
    against ITS OWN data folder, which is derived from a hash of the executable
    path, not from the folder the source file lives in. Compiling a file that
    uses <Trade\Trade.mqh> therefore fails with "file not found" unless the
    include root is supplied. Pass -IncludePath, or use a portable MetaEditor.

.PARAMETER File
    Path to the .mq5 file to compile.

.PARAMETER IncludePath
    MQL5 folder that contains Include\. Required for any source that uses
    angle-bracket includes such as <Trade\Trade.mqh>.

.PARAMETER MetaEditor
    Path to MetaEditor64.exe. Defaults to config\paths.json, then to the
    standard install location.

.PARAMETER Json
    Emit the result as JSON on stdout. This is the mode an agent should use.

.EXAMPLE
    .\scripts\compile.ps1 -File src\Experts\MyEA.mq5 -Json

.OUTPUTS
    PSCustomObject, or JSON with -Json:
      success     bool    true only when the log reports 0 errors
      errorCount  int
      warningCount int
      diagnostics array of { severity, file, line, column, code, message }
      hints       array of correct built-in signatures MetaEditor suggested
      exitCode    int     recorded for the record, deliberately not trusted
      logPath     string
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$File,

    [string]$IncludePath,

    [string]$MetaEditor,

    [switch]$Json
)

$ErrorActionPreference = 'Stop'

# --- Resolve the source file -------------------------------------------------

if (-not (Test-Path -LiteralPath $File)) {
    throw "Source file not found: $File"
}
$srcPath = (Resolve-Path -LiteralPath $File).Path

if ([System.IO.Path]::GetExtension($srcPath) -ne '.mq5') {
    throw "Not an .mq5 file: $srcPath"
}

# --- Resolve MetaEditor ------------------------------------------------------

if (-not $MetaEditor) {
    $configPath = Join-Path $PSScriptRoot '..\config\paths.json'
    if (Test-Path -LiteralPath $configPath) {
        $cfg = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($cfg.metaEditor)  { $MetaEditor  = $cfg.metaEditor }
        if (-not $IncludePath -and $cfg.includePath) { $IncludePath = $cfg.includePath }
    }
}
if (-not $MetaEditor) {
    $MetaEditor = 'C:\Program Files\MetaTrader 5\MetaEditor64.exe'
}
if (-not (Test-Path -LiteralPath $MetaEditor)) {
    throw "MetaEditor not found: $MetaEditor. Set it in config\paths.json or pass -MetaEditor."
}

# --- Compile -----------------------------------------------------------------
# /log with no value writes <source>.log next to the source file.
# Start-Process -Wait is mandatory. See note 1 in the header.

$logPath = [System.IO.Path]::ChangeExtension($srcPath, '.log')
$ex5Path = [System.IO.Path]::ChangeExtension($srcPath, '.ex5')

Remove-Item -LiteralPath $logPath -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $ex5Path -Force -ErrorAction SilentlyContinue

$cliArgs = @("/compile:`"$srcPath`"", '/log')
if ($IncludePath) {
    $cliArgs += "/include:`"$IncludePath`""
}

$proc = Start-Process -FilePath $MetaEditor -ArgumentList $cliArgs `
                      -Wait -PassThru -NoNewWindow
$exitCode = $proc.ExitCode

if (-not (Test-Path -LiteralPath $logPath)) {
    throw "MetaEditor produced no log at $logPath. It may have failed to start, or the source path may be unreadable to it."
}

# --- Parse the log -----------------------------------------------------------
# UTF-16 LE with BOM. See note 3 in the header.

$lines = Get-Content -LiteralPath $logPath -Encoding Unicode

$reDiag = '^(?<file>.+?)\((?<line>\d+),(?<col>\d+)\)\s*:\s*(?<sev>error|warning)\s+(?<code>\d+):\s*(?<msg>.+?)\s*$'
$reHint = '^.+?\s*:\s*information:\s*info\s+built-in:\s*(?<sig>.+?)\s*$'
$reDone = '^Result:\s*(?<errors>\d+)\s+errors?,\s*(?<warnings>\d+)\s+warnings?'

$diagnostics = @()
$hints       = @()
$errorCount  = $null
$warnCount   = $null

foreach ($line in $lines) {
    if ($line -match $reDiag) {
        $diagnostics += [PSCustomObject]@{
            severity = $Matches['sev']
            file     = $Matches['file']
            line     = [int]$Matches['line']
            column   = [int]$Matches['col']
            code     = [int]$Matches['code']
            message  = $Matches['msg']
        }
        continue
    }
    if ($line -match $reHint) {
        $hints += $Matches['sig']
        continue
    }
    if ($line -match $reDone) {
        $errorCount = [int]$Matches['errors']
        $warnCount  = [int]$Matches['warnings']
    }
}

if ($null -eq $errorCount) {
    throw "Could not find the 'Result:' summary line in $logPath. The log format may have changed in this MetaEditor build."
}

# Success is decided by the log, never by the exit code. See note 2.
$success = ($errorCount -eq 0)

# Cross-check: a clean compile must have produced an .ex5.
if ($success -and -not (Test-Path -LiteralPath $ex5Path)) {
    $success = $false
    $diagnostics += [PSCustomObject]@{
        severity = 'error'
        file     = $srcPath
        line     = 0
        column   = 0
        code     = 0
        message  = 'Log reported 0 errors but no .ex5 was produced.'
    }
    $errorCount = 1
}

$result = [PSCustomObject]@{
    success      = $success
    errorCount   = $errorCount
    warningCount = $warnCount
    diagnostics  = @($diagnostics | Where-Object { $_.severity -eq 'error' }) +
                   @($diagnostics | Where-Object { $_.severity -eq 'warning' })
    hints        = @($hints | Select-Object -Unique)
    source       = $srcPath
    output       = if ($success) { $ex5Path } else { $null }
    exitCode     = $exitCode
    logPath      = $logPath
}

if ($Json) {
    $result | ConvertTo-Json -Depth 5
}
else {
    if ($result.success) {
        Write-Host "OK  $([System.IO.Path]::GetFileName($srcPath))  ->  $([System.IO.Path]::GetFileName($ex5Path))" -ForegroundColor Green
        if ($result.warningCount -gt 0) {
            Write-Host "    $($result.warningCount) warning(s)" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "FAIL  $([System.IO.Path]::GetFileName($srcPath))  $($result.errorCount) error(s)" -ForegroundColor Red
    }
    foreach ($d in $result.diagnostics) {
        $colour = if ($d.severity -eq 'error') { 'Red' } else { 'Yellow' }
        Write-Host ("  {0}({1},{2}) {3} {4}: {5}" -f
            [System.IO.Path]::GetFileName($d.file), $d.line, $d.column,
            $d.severity, $d.code, $d.message) -ForegroundColor $colour
    }
    foreach ($h in $result.hints) {
        Write-Host "  hint: correct signature is $h" -ForegroundColor Cyan
    }
    $result
}

# Exit code for the caller follows the Unix convention, unlike MetaEditor's.
if (-not $success) { exit 1 }
exit 0
