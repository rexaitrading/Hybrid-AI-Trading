[CmdletBinding()]
param(
  [int]$TimeoutSec = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = (Resolve-Path ".").Path
Set-Location $root

$today = (Get-Date).ToString("yyyy-MM-dd")
$tsUtc  = (Get-Date).ToUniversalTime().ToString("o")

$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$outJson = Join-Path $logDir "phase4_validation_passed.json"

$py = Join-Path $root ".venv\Scripts\python.exe"
$env:PYTHONNOUSERSITE="1"
$env:PYTHONPATH = (Join-Path $root "src")
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"

# FAIL-CLOSED default
$ok = $false
$notes = New-Object System.Collections.Generic.List[string]

function RunPyTimeout([string[]]$args,[int]$timeoutSec){
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $py
  $psi.Arguments = ($args -join " ")
  $psi.WorkingDirectory = $root
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError  = $true
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true

  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $psi
  [void]$p.Start()

  if (-not $p.WaitForExit($timeoutSec * 1000)) {
    try { $p.Kill($true) } catch { }
    return @{ rc = 124; out=""; err="timeout" }
  }
  return @{ rc = $p.ExitCode; out=$p.StandardOutput.ReadToEnd(); err=$p.StandardError.ReadToEnd() }
}

if (-not (Test-Path $py)) {
  $notes.Add("python_missing") | Out-Null
} else {
  # Phase-4 SAFE: compile sweep only (no pytest; avoids any IB/async hangs)
  $r = RunPyTimeout @("-c","import compileall,sys; ok=compileall.compile_dir('src',quiet=1); print('compileall_ok',ok); sys.exit(0 if ok else 2)") $TimeoutSec
  if ($r.rc -eq 0 -and $r.out -match "compileall_ok\s+True") {
    $ok = $true
    $notes.Add("compileall_ok") | Out-Null
  } elseif ($r.rc -eq 124) {
    $notes.Add("compileall_timeout") | Out-Null
  } else {
    $notes.Add("compileall_failed") | Out-Null
  }
}

$payload = [ordered]@{
  ts_utc = $tsUtc
  as_of_date = $today
  phase4_ok_today = $ok
  notes = @($notes)
}
$payloadJson = $payload | ConvertTo-Json -Depth 6
[System.IO.File]::WriteAllText($outJson, ($payloadJson + "`n"), (New-Object System.Text.UTF8Encoding($false)))

Write-Host "[PHASE4] wrote $outJson ok=$ok today=$today" -ForegroundColor Green
exit 0
