<#
  Minimal paper journal/export (PS 5.1-safe)
  Outputs a daily CSV under out\journal\YYYY-MM-DD_paper_summary.csv
  Optional Slack summary via $env:SLACK_WEBHOOK_URL
#>
[CmdletBinding()]
param(
    [ValidateSet('paper','live')][string]$Mode = 'paper',
    [string]$Date = (Get-Date).ToString('yyyy-MM-dd')
)

$ErrorActionPreference = 'Stop'

function Write-Info($m){ Write-Host $m -ForegroundColor Cyan }
function Write-Ok($m){   Write-Host $m -ForegroundColor Green }
function Write-Warn($m){ Write-Host $m -ForegroundColor Yellow }

# Resolve heartbeat by mode (paper-first defaults)
if ($Mode -eq 'live') {
  $hbPath = 'C:\IBC\status\ibg_live_status.json'
  $port   = 4001
} else {
  $hbPath = 'C:\IBC\status\ibg_status.json'
  $port   = 4002
}

# Gather data
$hb = $null; $portListen = $false
if (Test-Path $hbPath) {
  try { $hb = Get-Content $hbPath -Raw | ConvertFrom-Json } catch { $hb = $null }
}
try { $portListen = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue).Count -gt 0 } catch { $portListen = $false }

# Shape a record
$rec = [ordered]@{
  date             = $Date
  mode             = $Mode
  port             = $port
  port_listen      = $portListen
  hb_portUp        = if($hb){ [bool]$hb.portUp } else { $false }
  hb_pid           = if($hb){ $hb.pid } else { $null }
  hb_uptime_sec    = if($hb){ $hb.uptimeSec } else { $null }
  hb_cpu_sec       = if($hb){ $hb.cpuSec } else { $null }
  hb_rss_mb        = if($hb){ $hb.rssMB } else { $null }
  hb_lastPing      = if($hb){ $hb.lastPing } else { $null }
  hb_timestamp     = if($hb){ $hb.timestamp } else { $null }
  gateway_path     = if($hb){ $hb.gatewayPath } else { $null }
  exported_at_iso  = (Get-Date).ToString('s')
}

# Ensure out folder
$outDir = Join-Path $PSScriptRoot '..\out\journal' | Resolve-Path -ErrorAction SilentlyContinue
if (-not $outDir) { $outDir = Join-Path $PSScriptRoot '..\out\journal' }
New-Item -ItemType Directory -Force $outDir | Out-Null

$outCsv = Join-Path $outDir ("{0}_{1}_paper_summary.csv" -f $Date, (Get-Date -Format 'HHmmss'))
# Write CSV (UTF-8 no BOM)
$utf8 = New-Object System.Text.UTF8Encoding($false)
$rec | ConvertTo-Csv -NoTypeInformation | Out-String | % { [IO.File]::WriteAllText($outCsv, ($_ -replace "`r`n","`n"), $utf8) }
Write-Ok "Exported: $outCsv"

# Optional Slack summary
if ($env:SLACK_WEBHOOK_URL -and -not $env:NO_SLACK) {
  $text = ("Post-Market Export {0} {1}: listen={2} hbUp={3} uptimeSec={4}" -f $Date,$Mode,$rec.port_listen,$rec.hb_portUp,$rec.hb_uptime_sec)
  try {
    $payload = @{ text = $text } | ConvertTo-Json -Compress
    Invoke-RestMethod -Method Post -Uri $env:SLACK_WEBHOOK_URL -Body $payload -ContentType 'application/json'
    Write-Ok "Slack summary posted."
  } catch {
    Write-Warn "Slack post failed: $_"
  }
}
