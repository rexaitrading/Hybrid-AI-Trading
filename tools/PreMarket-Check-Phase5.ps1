param(
    [switch]$VerbosePreMarket
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$preMarket  = Join-Path $scriptRoot "PreMarket-Check.ps1"
$sanity     = Join-Path $scriptRoot "Phase5-OptionA-Sanity.ps1"

if (-not (Test-Path $preMarket)) {
    Write-Host "[PHASE-5 WRAPPER] MISSING PreMarket-Check.ps1 at $preMarket" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[PHASE-5 WRAPPER] Running base PreMarket-Check.ps1..." -ForegroundColor Cyan

# Run PreMarket-Check in a child PowerShell so its 'exit' does not kill this wrapper
$preArgs = @("-ExecutionPolicy", "Bypass", "-File", $preMarket)
if ($VerbosePreMarket) { $preArgs += "-Verbose" }

& powershell @preArgs
$code = $LASTEXITCODE

Write-Host "[PHASE-5 WRAPPER] PreMarket-Check.ps1 exit code: $code" -ForegroundColor DarkCyan

if ($code -ne 0) {
    Write-Host "[PHASE-5 WRAPPER] Skipping Phase-5 sanity because pre-market check failed." -ForegroundColor Yellow
    exit $code
}

# Phase-5 sanity script
if (Test-Path $sanity) {
    Write-Host ""
    Write-Host "[PHASE-5 WRAPPER] Running Phase-5 Option A multi-symbol sanity..." -ForegroundColor Cyan
    & $sanity
} else {
    Write-Host "[PHASE-5 WRAPPER] Phase5-OptionA-Sanity.ps1 not found; skipping Phase-5 sanity." -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "[PHASE-5 WRAPPER] Done. Returning original pre-market exit code: $code" -ForegroundColor Green
exit $code