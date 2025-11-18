param(
    [Parameter(Mandatory = $true)][string]$Symbol,
    [Parameter(Mandatory = $true)][string]$SessionDate,  # yyyy-MM-dd
    [string]$SummaryJson
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root      = Split-Path -Parent $scriptDir
Set-Location $root

# Ensure python is available (assumes .venv in repo root if PATH lacks python)
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    $venvPy = Join-Path $root ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPy)) {
        throw "python not on PATH and .venv not found at $venvPy"
    }
    $env:PATH = (Split-Path $venvPy) + ";" + $env:PATH
}

# Ensure src/ is on PYTHONPATH so hybrid_ai_trading.tools.* is importable
$srcPath = Join-Path $root "src"
if ($env:PYTHONPATH) {
    if ($env:PYTHONPATH -notlike "*$srcPath*") {
        $env:PYTHONPATH = "$srcPath;$env:PYTHONPATH"
    }
} else {
    $env:PYTHONPATH = $srcPath
}

Write-Host "[HybridAITrading] Running single-symbol replay session stub..." -ForegroundColor Cyan
Write-Host "  Symbol      = $Symbol" -ForegroundColor DarkGray
Write-Host "  SessionDate = $SessionDate" -ForegroundColor DarkGray

$argsList = @(
    "-m", "hybrid_ai_trading.tools.replay_to_notion",
    "--symbol", $Symbol,
    "--session", $SessionDate
)

if ($SummaryJson) {
    $argsList += @("--summary-json", $SummaryJson)
}

Write-Host ("python " + ($argsList -join " ")) -ForegroundColor DarkGray

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "python"
$psi.Arguments = ($argsList -join " ")
$psi.UseShellExecute        = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true

$proc = New-Object System.Diagnostics.Process
$proc.StartInfo = $psi
$null = $proc.Start()

$stdout = $proc.StandardOutput.ReadToEnd()
$stderr = $proc.StandardError.ReadToEnd()
$proc.WaitForExit()

Write-Host $stdout
if ($stderr) {
    Write-Host $stderr -ForegroundColor Red
}

if ($proc.ExitCode -ne 0) {
    throw "run_replay_session stub failed with exit code $($proc.ExitCode)"
}

Write-Host "[HybridAITrading] Replay  Notion stub completed (see .logs/replay_to_notion_*.log)" -ForegroundColor Green
