[CmdletBinding()]
param(
  [string]$InPath  = ".\logs\phase6_portfolio_state.json",
  [string]$OutPath = ".\logs\phase6_daily_summary.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

if(-not (Test-Path -LiteralPath $InPath)){
  throw "Missing input JSON: $InPath"
}

$p = Get-Content -LiteralPath $InPath -Raw -Encoding utf8 | ConvertFrom-Json

# Notion-friendly: one row per day
$ready = ""
if($null -ne $p.ready_symbols){
  $ready = [string]::Join(",", @($p.ready_symbols))
}

$row = [ordered]@{
  as_of_date     = [string]$p.as_of_date
  ok             = [string]$p.ok
  reason         = [string]$p.reason
  ready_symbols  = $ready
  ts_utc         = [string]$p.ts_utc
  version        = [string]$p.version
}

$csv = @([pscustomobject]$row) | ConvertTo-Csv -NoTypeInformation

$enc = New-Object System.Text.UTF8Encoding($false)
$full = Join-Path (Split-Path -Parent (Split-Path -Parent $PSCommandPath)) $OutPath
$dir = Split-Path -Parent $full
if($dir -and -not (Test-Path $dir)){ New-Item -ItemType Directory -Force -Path $dir | Out-Null }

# LF only + newline at end
$payload = (($csv -join "`n") -replace "`r`n","`n") + "`n"
[System.IO.File]::WriteAllText($full, $payload, $enc)

Write-Host "[PHASE6] wrote $full" -ForegroundColor Green
Write-Host ("[PHASE6] summary as_of={0} ok={1} ready={2}" -f $row.as_of_date, $row.ok, $row.ready_symbols) -ForegroundColor Cyan
exit 0

