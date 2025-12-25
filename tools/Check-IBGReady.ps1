[CmdletBinding()]
param(
  [string]$IbHost = "127.0.0.1",
  [int]$Port = 4002,
  [int]$ClientId = 15,
  [string]$RepoRoot = (Resolve-Path ".").Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"


$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

function Fail([string]$msg){
  Write-Host ("IBG_READY=0 :: " + $msg) -ForegroundColor Red
  exit 2
}

# 1) Process
$p = Get-Process -Name ibgateway -ErrorAction SilentlyContinue | Select-Object -First 1
if(-not $p){ Fail "ibgateway process not running" }

# 2) Port listening + owner (authoritative via Get-NetTCPConnection)
$c = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if(-not $c){ Fail "port $Port not LISTENING" }
$ownerPid = [int]$c.OwningProcess
Write-Host ("IBG_PORT_OWNER_PID=" + $ownerPid) -ForegroundColor DarkGray
if($p){
  $ibgPid = [int]$p.Id
  if($ownerPid -ne $ibgPid){ Fail "port $Port owned by PID=$ownerPid not ibgateway PID=$ibgPid" }
}
# 3) Repo-native read-only smoke
$env:IB_GATEWAY_HOST = $IbHost
$env:IB_GATEWAY_PORT = "$Port"
$env:IB_CLIENT_ID    = "$ClientId"

$smoke = Join-Path $RepoRoot "tools\ibg_repo_smoke_readonly.py"
if(-not (Test-Path $smoke)){ Fail "missing $smoke" }

powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $toolsDir "python.ps1") $smoke | Out-Host

Write-Host "IBG_READY=1" -ForegroundColor Green
exit 0
