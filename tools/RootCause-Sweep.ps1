[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function OK($m){ Write-Host "[OK]  $m" -ForegroundColor Green }
function BAD($m){ Write-Host "[BAD] $m" -ForegroundColor Red }
function INFO($m){ Write-Host "[..] $m" -ForegroundColor Yellow }

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

# --- Core paths
$venv = Join-Path $repo ".venv\Scripts\python.exe"
if (Test-Path $venv) { OK "venv python exists" } else { BAD "missing $venv" }

# --- IBG port
$ibHost = $env:IB_HOST; if ([string]::IsNullOrWhiteSpace($ibHost)) { $ibHost="::1" }
$ibPort = $env:IB_PORT; if ([string]::IsNullOrWhiteSpace($ibPort)) { $ibPort="4002" }
$tnc = Test-NetConnection $ibHost -Port ([int]$ibPort) -WarningAction SilentlyContinue
if ($tnc.TcpTestSucceeded) { OK "IB API reachable at $ibHost`:$ibPort" } else { BAD "IB API NOT reachable at $ibHost`:$ibPort" }

# --- runner_stream process
$ps = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { ($_.CommandLine + "") -match 'runner_stream\.py' }
if ($ps) {
  OK ("runner_stream alive count={0}" -f ($ps | Measure-Object).Count)
} else {
  BAD "runner_stream not running"
}

# --- Block-G status file (if you use it)
$bg = Join-Path $repo "logs\blockg_status_stub.json"
if (Test-Path $bg) { OK "Block-G status stub exists (logs\blockg_status_stub.json)" } else { INFO "Block-G status stub not found (ok if not building today)" }

# --- Phase scripts existence (smoke)
$must = @(
  "tools\Run-IntelPipeline.ps1",
  "tools\stream.ps1",
  "tools\start_stream_realtime.ps1",
  "tools\Ops-24x7.ps1"
)
foreach($m in $must){
  if (Test-Path (Join-Path $repo $m)) { OK "$m present" } else { BAD "$m missing" }
}