param(
    [string] $ExtraPytestArgs = ""
)

$ErrorActionPreference = 'Stop'

# Determine repo root
if ($MyInvocation.MyCommand.Path) {
    # Running as a script file: use the script's directory
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $repoRoot  = Resolve-Path (Join-Path $scriptDir '..')
} else {
    # Running interactively (pasted in console): assume current dir is repo root
    $repoRoot = Get-Location
}

Set-Location $repoRoot

# Ensure Python + PYTHONPATH are pointed at THIS repo
$PythonExe      = '.\.venv\Scripts\python.exe'
$env:PYTHONPATH = (Join-Path $repoRoot 'src')

$tests = @(
    'tests/test_portfolio_tracker_full.py',
    'tests/test_execution_engine_phase5_guard.py'
)

Write-Host "[PORTFOLIO] RepoRoot      = $repoRoot" -ForegroundColor Cyan
Write-Host "[PORTFOLIO] PythonExe     = $PythonExe" -ForegroundColor Cyan
Write-Host "[PORTFOLIO] PYTHONPATH    = $env:PYTHONPATH" -ForegroundColor Cyan
Write-Host "[PORTFOLIO] Test files    = $($tests -join ', ')" -ForegroundColor Cyan
Write-Host "[PORTFOLIO] Extra pytest  = $ExtraPytestArgs" -ForegroundColor Cyan

# Build pytest arg list
$pytestArgs = @()
$pytestArgs += $tests
$pytestArgs += '-q'  # quiet by default in scripts

if ($ExtraPytestArgs) {
    # Split on spaces so "-vv -x" works
    $pytestArgs += $ExtraPytestArgs.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)
}

& $PythonExe -m pytest @pytestArgs