[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)][ValidateSet("true","false")][string]$Ok = "true"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"
if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir | Out-Null }

$today = (Get-Date).ToString("yyyy-MM-dd")
$path  = Join-Path $logsDir "phase5_ev_hard_veto_daily.csv"

# Schema: date,ok,reason
$header = "date,ok,reason"
$row = "$today,$Ok,manual_stub"

$lines = @()
if (Test-Path $path) {
  $lines = @(Get-Content $path -Encoding utf8)
  if ($lines.Count -eq 0) { $lines = @($header) }
  if ($lines[0].Trim() -ne $header) { $lines = @($header) + $lines }
} else {
  $lines = @($header)
}

$lines = $lines | Where-Object { $_ -notmatch "^$today," }
$lines = $lines + $row

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($path, ($lines -join "`r`n") + "`r`n", $utf8NoBom)

Write-Host "[EV-HARD] Wrote/updated $path -> $row" -ForegroundColor Green