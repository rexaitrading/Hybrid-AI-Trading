[CmdletBinding()]
param(
  [int]$TimeoutSec = 60,
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "ALL",
  [switch]$RunPython
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

# Deterministic repo root (Unicode-safe)
$toolsDir = Split-Path -Parent $PSCommandPath
$root = Split-Path -Parent $toolsDir
Set-Location $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "[GS-BUILD] python missing: $py" }

$env:PYTHONNOUSERSITE="1"
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH = (Join-Path $root "src")

$logDir = Join-Path $root "logs\gatescore"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$ts = (Get-Date).ToString("yyyyMMdd_HHmmss")
$outLog = Join-Path $logDir ("daily_build_" + $ts + ".out.txt")
$errLog = Join-Path $logDir ("daily_build_" + $ts + ".err.txt")

$csv = Join-Path $root "logs\gatescore_daily_summary.csv"
if (-not (Test-Path $csv)) { throw "[GS-BUILD] missing input csv: $csv" }

$todayUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")

# --- TODAY-ONLY NORMALIZE (institutional hygiene) ---
# NOTE: Do NOT mutate source CSV on disk. Keep history for audit + Notion + Intel.
Write-Host ("[GS-BUILD] input csv (read-only)=" + $csv + " today_utc=" + $todayUtc) -ForegroundColor Cyan
# --- END TODAY-ONLY NORMALIZE ---


function Get-SessionDate([string]$sym){
  $rows = @(Import-Csv -LiteralPath $csv)
  $r = $rows | Where-Object { $_.symbol -eq $sym } | Sort-Object as_of_date -Descending | Select-Object -First 1
  if (-not $r) { return "" }
  return [string]$r.as_of_date
}

function Has-SessionRow([string]$sym){
  $sd = Get-SessionDate -sym $sym
  if (-not $sd) { return $false }
  try {
    $rows = @(Import-Csv -LiteralPath $csv)
    $symU = $sym.ToUpperInvariant()
    $sd10 = ([string]$sd).Substring(0,10)
    return ($rows | Where-Object {
      ($_.symbol + "").ToUpperInvariant() -eq $symU -and
      (([string]$_.as_of_date).Substring(0,10)) -eq $sd10
    } | Measure-Object).Count -gt 0
  } catch {
    return $false
  }
}

$startUtc = (Get-Date).ToUniversalTime()

function Kill-LeftoverVenvPython([datetime]$sinceUtc){
  $sinceWmi = $sinceUtc.ToString("yyyyMMddHHmmss.ffffff") + "+000"
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object {
      $_.CommandLine -match [regex]::Escape($py) -and
      $_.CreationDate -ge $sinceWmi
    } |
    ForEach-Object {
      try { Stop-Process -Id $_.ProcessId -Force } catch { }
    }
}

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
  $childPid = $proc.Id

  if (-not $proc.WaitForExit($timeoutSec * 1000)) {
    try { Stop-Process -Id $childPid -Force } catch { }
    "[TIMEOUT] killed pid=$childPid after ${timeoutSec}s args=$($args -join ' ')" | Out-File -FilePath $errLog -Encoding utf8
    Kill-LeftoverVenvPython -sinceUtc $startUtc
    return 124
  }

  $out = $proc.StandardOutput.ReadToEnd()
  $err = $proc.StandardError.ReadToEnd()
  if ($out) { $out | Out-File -FilePath $outLog -Encoding utf8 }
  if ($err) { $err | Out-File -FilePath $errLog -Encoding utf8 }

  Kill-LeftoverVenvPython -sinceUtc $startUtc
  return $proc.ExitCode
}

$syms = @("NVDA","SPY","QQQ")
if ($Symbol -ne "ALL") { $syms = @($Symbol.ToUpper()) }

# Fail-closed PRECHECK (session-based, not "today-based")
foreach($s in $syms){
  if (-not (Has-SessionRow -sym $s)) {
    $sd = Get-SessionDate -sym $s
    Write-Host ("[GS-BUILD] FAIL-CLOSED: missing session row for {0} in {1} today={2} session={3}" -f $s,$csv,$todayUtc,$sd) -ForegroundColor Yellow
    exit 2
  }
}

if (-not $RunPython) {
  Write-Host "[GS-BUILD] OK (no-python) symbols=$($syms -join ',') csv=$csv" -ForegroundColor Green
  exit 0
}

foreach($s in $syms){
  $code = "import sys,runpy; sys.path.insert(0,r'$env:PYTHONPATH'); runpy.run_module('hybrid_ai_trading.gatescore.daily_build', run_name='__main__')"
  $rc = RunPyTimeout @("-I","-X","faulthandler","-c",$code,"--csv",$csv,"--symbol",$s) $TimeoutSec
  if ($rc -ne 0) {
    Write-Host "[GS-BUILD] FAIL symbol=$s rc=$rc logs=$logDir" -ForegroundColor Yellow
    exit $rc
  }
}

Write-Host "[GS-BUILD] OK (python) symbols=$($syms -join ',') logs=$logDir" -ForegroundColor Green
exit 0
