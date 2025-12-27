[CmdletBinding()]
param(
  [int]$TimeoutSec = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$root = Split-Path -Parent $toolsDir
Set-Location $root
Remove-Item Env:HAT_BLOCKG_BUILT_ONCE -ErrorAction SilentlyContinue
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

function RunPyTimeout([string]$Code,[int]$timeoutSec){
  $tmp = [System.IO.Path]::Combine($env:TEMP, ("phase4_compile_{0}.py" -f (Get-Date -Format "yyyyMMdd_HHmmss_fff")))
  [System.IO.File]::WriteAllText($tmp, ($Code + "`n"), (New-Object System.Text.UTF8Encoding($false)))

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $py
  $psi.Arguments = ('"{0}"' -f $tmp)
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
    try { Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue } catch { }
    return @{ rc = 124; out=""; err="timeout" }
  }

  $out = $p.StandardOutput.ReadToEnd()
  $err = $p.StandardError.ReadToEnd()
  try { Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue } catch { }

  return @{ rc = $p.ExitCode; out=$out; err=$err }
}

if (-not (Test-Path $py)) {
  $notes.Add("python_missing") | Out-Null
} else {
  # Phase-4 SAFE: compile sweep only (no pytest; avoids any IB/async hangs)
  $code = @"
import py_compile,sys
files=[
  'src/hybrid_ai_trading/runners/runner_stream.py',
  'src/hybrid_ai_trading/execution/blockg_enforce.py',
  'src/hybrid_ai_trading/broker/ib_safe.py'
]
ok=True
for f in files:
  try:
    py_compile.compile(f, doraise=True)
  except Exception as e:
    print('py_compile_fail', f, type(e).__name__, e)
    ok=False
print('py_compile_ok', ok)
sys.exit(0 if ok else 2)
"@
  $r = RunPyTimeout $code $TimeoutSec
  if ($r.rc -eq 0 -and $r.out -match "py_compile_ok\s+True") {
    $compile_ok = $true
    $notes.Add("py_compile_ok") | Out-Null
  } elseif ($r.rc -eq 124) {
    $compile_ok = $false
    $notes.Add("py_compile_timeout") | Out-Null
    $notes.Add("py_compile_failed") | Out-Null
  } else {
    $compile_ok = $false
    $notes.Add("py_compile_failed") | Out-Null
  }
}

# Phase-4 authoritative: tiny pytest slice (fast, no IB hang)
try {
  $pytest = Join-Path $root ".venv\Scripts\python.exe"
  if (Test-Path $pytest) {
    & $pytest -m pytest -q tests\test_blockg_risk_flatten_guard.py tests\test_blockg_chokepoint_blocks_live.py tests\test_gatescore_fresh_policy.py | Out-Host
    if ($LASTEXITCODE -ne 0) {
      $pytest_ok = $false
      $notes.Add("pytest_slice_fail") | Out-Null
    } else {
      $pytest_ok = $true
      $notes.Add("pytest_slice_ok") | Out-Null
    }
  } else {
    $notes.Add("pytest_python_missing") | Out-Null; $pytest_ok = $false
  }
} catch {
  $notes.Add("pytest_slice_exception") | Out-Null; $pytest_ok = $false
}

# --- FINAL STRICT PHASE-4 POLICY (fail-closed) ---
$ok = ($compile_ok -and $pytest_ok)
if(-not $compile_ok){ $notes.Add("strict_compile_gate_blocked") | Out-Null }
if(-not $pytest_ok){  $notes.Add("strict_pytest_gate_blocked")  | Out-Null }

$payload = [ordered]@{
  ts_utc = $tsUtc
  as_of_date = $today
  phase4_ok_today = $ok
  notes = @($notes)
}
$payloadJson = $payload | ConvertTo-Json -Depth 6
[System.IO.File]::WriteAllText($outJson, ($payloadJson + "`n"), (New-Object System.Text.UTF8Encoding($false)))

Write-Host "[PHASE4] wrote $outJson ok=$ok today=$today" -ForegroundColor Green
if ($ok) { exit 0 } else { exit 2 }
