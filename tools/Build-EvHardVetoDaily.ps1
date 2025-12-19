[CmdletBinding()]
param()

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$logs = Join-Path $repoRoot "logs"
if(-not (Test-Path $logs)){ New-Item -ItemType Directory -Force -Path $logs | Out-Null }

$today = (Get-Date).ToString("yyyy-MM-dd")
$out   = Join-Path $logs "phase5_ev_hard_veto_daily.csv"

# FAIL-CLOSED: default False until wired to real EV-hard snapshot evidence.
$evHardOk = $false

# Preserve header + replace existing today row if present
$lines = @()
if(Test-Path $out){
  $lines = Get-Content $out -Encoding utf8
}

if($lines.Count -eq 0){
  $lines = @("date,ev_hard_ok")
} else {
  if($lines[0] -ne "date,ev_hard_ok"){ $lines = @("date,ev_hard_ok") + $lines }
}

# remove any existing today row
$lines = $lines | Where-Object { $_ -notlike "$today,*" }

# append today row
$lines += ("$today," + ($evHardOk.ToString()))

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($out, ($lines -join "`n"), $utf8NoBom)

Write-Host "[EV-HARD] wrote $out => $today,$evHardOk" -ForegroundColor Green