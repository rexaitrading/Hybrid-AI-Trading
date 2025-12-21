[CmdletBinding()]
param(
  [int]$TimeoutSec = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = (Resolve-Path ".").Path
Set-Location $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "[GS-BUILD] python missing: $py" }

# Isolation + determinism
$env:PYTHONNOUSERSITE="1"
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH = (Join-Path $root "src")

function RunPyTimeout([string[]]$args,[int]$timeoutSec){
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $py
  $psi.Arguments = ($args -join " ")
  $psi.WorkingDirectory = $root
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError  = $true
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true

  $proc = New-Object System.Diagnostics.Process
  $proc.StartInfo = $psi
  [void]$proc.Start()

  # IMPORTANT: do NOT use $pid (collides with read-only $PID)
  $childPid = $proc.Id

  if (-not $proc.WaitForExit($timeoutSec * 1000)) {
    try { Stop-Process -Id $childPid -Force } catch { }
    Write-Host "[GS-BUILD] TIMEOUT after ${timeoutSec}s (killed pid=$childPid)" -ForegroundColor Yellow
    exit 124
  }

  $out = $proc.StandardOutput.ReadToEnd()
  $err = $proc.StandardError.ReadToEnd()

  # Keep output minimal to avoid console stalls
  if ($err) {
    Write-Host "[GS-BUILD] stderr (first 20 lines):" -ForegroundColor Yellow
    ($err -split "`r?`n" | Select-Object -First 20) | ForEach-Object { $_ | Out-Host }
  }

  Write-Host "[GS-BUILD] rc=$($proc.ExitCode) pid=$childPid" -ForegroundColor Yellow
  exit $proc.ExitCode
}

RunPyTimeout @("-I","-m","hybrid_ai_trading.gatescore.daily_build") $TimeoutSec
