[CmdletBinding()]
param(
  [int]$LookbackMinutes = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

$since = (Get-Date).AddMinutes(-1 * $LookbackMinutes)
$outDir = Join-Path $repoRoot "logs\ibg_death"
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
$ts = Get-Date -Format "yyyyMMdd_HHmmss"

$sys = Join-Path $outDir "system_$ts.txt"
$tsk = Join-Path $outDir "taskscheduler_$ts.txt"
$app = Join-Path $outDir "application_$ts.txt"

Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=$since} |
  Select-Object TimeCreated,Id,ProviderName,Message |
  Out-File -LiteralPath $sys -Encoding utf8

Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-TaskScheduler/Operational'; StartTime=$since} |
  Select-Object TimeCreated,Id,Message |
  Out-File -LiteralPath $tsk -Encoding utf8

Get-WinEvent -FilterHashtable @{LogName='Application'; StartTime=$since; Id=1000,1001} |
  Select-Object TimeCreated,Id,ProviderName,Message |
  Out-File -LiteralPath $app -Encoding utf8

Write-Host "[IBG-DEATH] wrote:" -ForegroundColor Yellow
Write-Host "  $sys" -ForegroundColor Yellow
Write-Host "  $tsk" -ForegroundColor Yellow
Write-Host "  $app" -ForegroundColor Yellow
exit 0