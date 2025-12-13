[CmdletBinding()]
param(
  [string]$PyExe = ".\.venv\Scripts\python.exe",
  [string]$TestFilter = "blockg or runcontext or gatescore_daily or phase4_validation",
  [switch]$NoTranscript
)

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$today = (Get-Date).ToString("yyyy-MM-dd")
$ts = (Get-Date).ToString("yyyyMMdd_HHmmss")

$logsDir = Join-Path $repoRoot "logs"
$phase4Dir = Join-Path $logsDir "phase4"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
New-Item -ItemType Directory -Force -Path $phase4Dir | Out-Null

$outStamp = Join-Path $logsDir "phase4_validation_passed.json"
$outJson  = Join-Path $phase4Dir ("phase4_{0}_{1}.json" -f $today, $ts)
$outLog   = Join-Path $phase4Dir ("phase4_{0}_{1}.log" -f $today, $ts)

if (-not $NoTranscript) {
  Start-Transcript -Path $outLog -Append | Out-Null
}

try {
  Write-Host "`n[PHASE4] Canonical daily validation" -ForegroundColor Cyan
  Write-Host "[PHASE4] as_of_date=$today" -ForegroundColor Cyan
  Write-Host "[PHASE4] outStamp=$outStamp" -ForegroundColor Cyan
  Write-Host "[PHASE4] outJson =$outJson" -ForegroundColor Cyan
  Write-Host "[PHASE4] outLog  =$outLog" -ForegroundColor Cyan

  # Run smoke
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $toolsDir "Run-Phase4Smoke.ps1") -PyExe $PyExe -TestFilter $TestFilter
  $ec = $LASTEXITCODE

  $ok = ($ec -eq 0)

  # Write JSON result (daily archived + stamp)
  $obj = [ordered]@{
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    as_of_date = $today
    phase4_ok_today = [bool]$ok
    smoke_exit_code = [int]$ec
    test_filter = $TestFilter
  }

  $json = ($obj | ConvertTo-Json -Depth 4)

  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($outJson, $json, $utf8NoBom)
  [System.IO.File]::WriteAllText($outStamp, $json, $utf8NoBom)

  if ($ok) {
    Write-Host "[PHASE4] PASS -> $outStamp" -ForegroundColor Green
    exit 0
  } else {
    Write-Host "[PHASE4] FAIL(exit=$ec) -> $outStamp" -ForegroundColor Red
    exit $ec
  }
}
finally {
  if (-not $NoTranscript) { Stop-Transcript | Out-Null }
}
