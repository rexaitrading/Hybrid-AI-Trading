[CmdletBinding()]
param(
  [int]$TimeoutSec = 180,
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
$csvToday = Join-Path $root "logs\gatescore_daily_summary_today.csv"
# IMPORTANT: never overwrite $csv (canonical). Today-only normalize writes to $csvToday.
if (-not (Test-Path $csv)) { throw "[GS-BUILD] missing input csv: $csv" }

# Trading-day "today" must follow LOCAL session day; allow override via env HAT_ASOF_DATE.
# Trading-day "today" must follow LOCAL session day; allow override via env HAT_ASOF_DATE.
$today = (($env:HAT_ASOF_DATE + "")).Trim()

try {
} catch {
  Write-Host ("[GS-BUILD] WARNING: daily_summary_from_events failed: " + $_.Exception.Message) -ForegroundColor Yellow
}

if([string]::IsNullOrWhiteSpace($today)){ $today = (Get-Date).ToString("yyyy-MM-dd") }

# --- Build canonical GateScore daily summary from events (fail-closed; no fabrication) ---
if([string]::IsNullOrWhiteSpace($today)){ Write-Host "[GS-BUILD] FAIL-CLOSED: empty today/as_of_date" -ForegroundColor Yellow; exit 2 }
try {
  $pyArgsDailySummary = @("-m","hybrid_ai_trading.gatescore.daily_summary_from_events","--as-of-date",$today,"--csv",$csv,"--logs",(Join-Path $root "logs"))
  & $py $pyArgsDailySummary | Out-Host
} catch {
  Write-Host ("[GS-BUILD] WARNING: daily_summary_from_events failed: " + $_.Exception.Message) -ForegroundColor Yellow
}
# --- END build daily summary from events ---

if([string]::IsNullOrWhiteSpace($today)){
}

# --- TODAY-ONLY NORMALIZE (institutional hygiene) ---
try {
  $rowsAll = @(Import-Csv -LiteralPath $csv)
  $rowsToday = @($rowsAll | Where-Object { ([string]$_.as_of_date).Substring(0,10) -eq $today })
  if ($rowsToday.Count -gt 0) {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $out = ($rowsToday | ConvertTo-Csv -NoTypeInformation) -join "`n"
    if ($out.Length -gt 0 -and $out[-1] -ne "`n") { $out += "`n" }
    [System.IO.File]::WriteAllText($csvToday, $out, $utf8NoBom)
    Write-Host "[GS-BUILD] today-only normalized: $csvToday rows=$($rowsToday.Count) as_of_date=$today" -ForegroundColor Cyan
  } else {
    Write-Host "[GS-BUILD] WARNING: no today rows found in $csv (kept as-is)" -ForegroundColor Yellow
  }
} catch {
  Write-Host "[GS-BUILD] WARNING: today-only normalization failed: $($_.Exception.Message)" -ForegroundColor Yellow
}
# --- END TODAY-ONLY NORMALIZE ---


function Get-SessionLabel(){
  # Log-only label; does NOT imply readiness.
  $now = Get-Date
  $hm = [int]($now.ToString("HHmm"))
  if($hm -lt 930){ return "PM" }       # pre-market
  elseif($hm -lt 1600){ return "RTH" } # regular
  else { return "AH" }                 # after-hours
}

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

function RunPyTimeout([string[]]$pyArgs,[int]$timeoutSec){
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $py
  $psi.Arguments = ($pyArgs -join " ")
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
    $argLine = $proc.StartInfo.Arguments
    ("[TIMEOUT] killed pid={0} after {1}s args={2} outLog={3} errLog={4}" -f $childPid,$timeoutSec,$argLine,$outLog,$errLog) | Out-File -FilePath $errLog -Encoding utf8
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

# Required symbols policy (scopes ALL-mode precheck).
# Default portfolio: NVDA,SPY,QQQ
# Paper-locked DailyOps may set: HAT_GS_REQUIRED_SYMBOLS="NVDA"
$reqEnv = ("" + $env:HAT_GS_REQUIRED_SYMBOLS).Trim()
if(-not $reqEnv){ $syms = @("NVDA","SPY","QQQ") }
else { $syms = @($reqEnv.Split(",") | ForEach-Object { (""+$_).Trim().ToUpper() } | Where-Object { $_ }) }
if ($Symbol -ne "ALL") { $syms = @($Symbol.ToUpper()) }

# Fail-closed PRECHECK (session-based, not "today-based")
foreach($s in $syms){
  if (-not (Has-SessionRow -sym $s)) {
    $sd = Get-SessionDate -sym $s
    Write-Host ("[GS-BUILD] FAIL-CLOSED: missing session row for {0} in {1} today={2} session_label=$(Get-SessionLabel) asof={3}" -f $s,$csv,$today,$sd) -ForegroundColor Yellow
    exit 2
  }
}

if (-not $RunPython) {
  # --- Institutional rule: explicit symbol runs MUST pass python threshold eval (fail-closed) ---
  if($Symbol -and ($Symbol.ToUpperInvariant() -ne "ALL")){
    try {
      exit $LASTEXITCODE
    } catch {
      Write-Host ("[GS-BUILD] FAIL-CLOSED: python eval failed: " + $_.Exception.Message) -ForegroundColor Red
      exit 2
    }
  }
  # --- END institutional rule ---
  # Write-Host "[GS-BUILD] OK (no-python) symbols=$($syms -join ',') csv=$csv" -ForegroundColor Green
  exit 0
}

foreach($s in $syms){
  $rc = RunPyTimeout -pyArgs @("-I","-X","faulthandler","-m","hybrid_ai_trading.gatescore.daily_build","--csv",$csv,"--symbol",$s) -timeoutSec $TimeoutSec
  if ($rc -ne 0) {
    Write-Host "[GS-BUILD] FAIL symbol=$s rc=$rc logs=$logDir" -ForegroundColor Yellow
    exit $rc
  }
}

Write-Host "[GS-BUILD] OK (python) symbols=$($syms -join ',') logs=$logDir" -ForegroundColor Green
exit 0
