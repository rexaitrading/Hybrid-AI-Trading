[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$pidPath = Join-Path $repoRoot "logs\paper_live_pid.json"
if(-not (Test-Path -LiteralPath $pidPath)){
  Write-Host "[OPS] No PID file found: $pidPath" -ForegroundColor Yellow
  exit 0
}

$rec = Get-Content $pidPath -Raw -Encoding utf8 | ConvertFrom-Json
$procId = [int]$rec.pid

$p = Get-Process -Id $procId -ErrorAction SilentlyContinue
if(-not $p){
  Write-Host "[OPS] Process not running (pid=$procId). Removing PID file." -ForegroundColor Yellow
  Remove-Item $pidPath -Force -ErrorAction SilentlyContinue
  exit 0
}

Write-Host "[OPS] Stopping pid=$procId ..." -ForegroundColor Cyan
Stop-Process -Id $procId -Force
Start-Sleep -Milliseconds 250

$p2 = Get-Process -Id $procId -ErrorAction SilentlyContinue
if($p2){
  Write-Host "[OPS] WARNING: pid still alive, force-kill again." -ForegroundColor Yellow
  Stop-Process -Id $procId -Force
}

Remove-Item $pidPath -Force -ErrorAction SilentlyContinue
Write-Host "[OPS] STOPPED." -ForegroundColor Green