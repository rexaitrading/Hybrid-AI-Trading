[CmdletBinding()]
param(
  [string]$LogsDir = ".\logs",
  [string]$StreamPath = ".\logs\nvda_paperlive_stream_today.jsonl",
  [string]$MarkerPath = ".\logs\nvda_paperlive_stream_today.last_merged.txt"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if(-not (Test-Path -LiteralPath $LogsDir)){ throw "Missing LogsDir: $LogsDir" }
if(-not (Test-Path -LiteralPath $StreamPath)){
  $dir = Split-Path -Parent $StreamPath
  if($dir -and -not (Test-Path $dir)){ New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  [System.IO.File]::WriteAllText((Resolve-Path $dir).Path + "\" + (Split-Path -Leaf $StreamPath), "", (New-Object System.Text.UTF8Encoding($false)))
}

$last = ""
if(Test-Path -LiteralPath $MarkerPath){
  $last = ((Get-Content -LiteralPath $MarkerPath -Encoding utf8 | Select-Object -First 1) + "").Trim()
}

$ticks = @(Get-ChildItem -LiteralPath $LogsDir -File -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match '^nvda_paperlive_tick_\d{8}_\d{6}\.jsonl$' } |
  Sort-Object Name)

$toMerge = $ticks
if($last){ $toMerge = @($ticks | Where-Object { $_.Name -gt $last }) }

if($toMerge.Count -eq 0){
  Write-Host "[MERGE] No new tick files to merge." -ForegroundColor Yellow
  exit 0
}

foreach($fi in $toMerge){
  Get-Content -LiteralPath $fi.FullName -Encoding utf8 | Add-Content -LiteralPath $StreamPath -Encoding utf8
  $last = $fi.Name
}

Set-Content -LiteralPath $MarkerPath -Value $last -Encoding utf8
Write-Host ("[MERGE] merged={0} last={1}" -f $toMerge.Count, $last) -ForegroundColor Green
exit 0