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

Write-Host "[PHASE5] RepoRoot     = $repoRoot" -ForegroundColor Cyan
Write-Host "[PHASE5] PythonExe    = $PythonExe" -ForegroundColor Cyan
Write-Host "[PHASE5] PYTHONPATH   = $env:PYTHONPATH" -ForegroundColor Cyan
Write-Host "[PHASE5] Pytest args  = -k `"phase5`" $ExtraPytestArgs" -ForegroundColor Cyan

# Run the same slice as CI
& $PythonExe -m pytest tests -k "phase5" -q $ExtraPytestArgs