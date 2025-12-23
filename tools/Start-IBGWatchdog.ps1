[CmdletBinding()]
param(
  [int]$IntervalSec = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

$log = Join-Path $repoRoot ("logs\ibg_watchdog_" + (Get-Date -Format yyyyMMdd) + ".log")
"START " + (Get-Date -Format o) | Add-Content -LiteralPath $log -Encoding utf8

while ($true) {
  $ts = Get-Date -Format o
  $procs = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'ibgateway|tws|java' })
  $alive = [bool]($procs.Count -gt 0)
  $uptime = if ($alive) { ($procs | Sort-Object StartTime | Select-Object -First 1).StartTime.ToString("o") } else { "" }
  ("$ts alive=$alive start=$uptime") | Add-Content -LiteralPath $log -Encoding utf8
  Start-Sleep -Seconds $IntervalSec
}