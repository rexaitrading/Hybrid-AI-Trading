[CmdletBinding()]
param(
  [int]$IntervalSec = 60,
  [int]$LookbackMinutes = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

$log = Join-Path $repoRoot ("logs\ibg_death_watch_" + (Get-Date -Format yyyyMMdd) + ".log")
"START " + (Get-Date -Format o) | Add-Content -LiteralPath $log -Encoding utf8

$wasAlive = $false

while ($true) {
  $ts = Get-Date -Format o
  $p = Get-Process -Name ibgateway -ErrorAction SilentlyContinue
  $alive = [bool]($null -ne $p)

  ("$ts alive=$alive") | Add-Content -LiteralPath $log -Encoding utf8

  if ($wasAlive -and (-not $alive)) {
    ("$ts DEAD_DETECTED lookback_min=$LookbackMinutes") | Add-Content -LiteralPath $log -Encoding utf8

    try {
      & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Capture-IBGDeathContext.ps1") -LookbackMinutes $LookbackMinutes | Out-Host
      ("$ts CAPTURE_OK") | Add-Content -LiteralPath $log -Encoding utf8
    } catch {
      ("$ts CAPTURE_FAIL " + $_.Exception.Message) | Add-Content -LiteralPath $log -Encoding utf8
    }
  }

  $wasAlive = $alive
  Start-Sleep -Seconds $IntervalSec
}
