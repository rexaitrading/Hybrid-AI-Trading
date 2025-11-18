param(
    [switch]$VerboseOutput
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to repo root (script directory is tools/)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
Set-Location $root

Write-Host "[HybridAITrading] Running Replay micro-suite (bar-replay + preflight)..." -ForegroundColor Cyan

# Ensure we are in the venv if needed (assumes .venv in repo root)
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    $venvPy = Join-Path $root ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPy)) {
        throw "python not on PATH and .venv not found at $venvPy"
    }
    $env:PATH = (Split-Path $venvPy) + ";" + $env:PATH
}

$argsList = @(
    "tests/test_replay_wrapper_json.py",
    "tests/utils/test_preflight_sanity.py",
    "-q"
)

if ($VerboseOutput) {
    $argsList = $argsList | Where-Object { $_ -ne "-q" }
}

Write-Host ("python -m pytest " + ($argsList -join " ")) -ForegroundColor DarkGray
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "python"
$psi.Arguments = "-m pytest " + ($argsList -join " ")
$psi.UseShellExecute = $false
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
    throw "Replay micro-suite failed with exit code $($proc.ExitCode)"
}

Write-Host "[HybridAITrading] Replay micro-suite: ALL GREEN" -ForegroundColor Green
