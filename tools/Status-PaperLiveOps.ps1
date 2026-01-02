[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$pidPath = Join-Path $repoRoot "logs\paper_live_pid.json"
$hbPath  = Join-Path $repoRoot "logs\paper_live_heartbeat.json"

if(Test-Path -LiteralPath $pidPath){
  $rec = Get-Content $pidPath -Raw -Encoding utf8 | ConvertFrom-Json
  $procId = [int]$rec.pid
  $p = Get-Process -Id $procId -ErrorAction SilentlyContinue

  if($p){
    Write-Host "[OPS] RUNNING pid=$procId symbol=$($rec.symbol)" -ForegroundColor Green
    Write-Host ("[OPS] stdout: " + $rec.stdout) -ForegroundColor DarkGray
    Write-Host ("[OPS] stderr: " + $rec.stderr) -ForegroundColor DarkGray
  } else {
    Write-Host "[OPS] NOT RUNNING (stale pid file) pid=$procId" -ForegroundColor Yellow
  }
} else {
  Write-Host "[OPS] No PID file (not started)." -ForegroundColor Yellow
}

if(Test-Path -LiteralPath $hbPath){
  $hb = Get-Content $hbPath -Raw -Encoding utf8
  Write-Host "[OPS] Heartbeat:" -ForegroundColor Cyan
  Write-Host $hb
} else {
  Write-Host "[OPS] No heartbeat yet: $hbPath" -ForegroundColor Yellow
}