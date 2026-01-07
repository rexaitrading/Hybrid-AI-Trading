[CmdletBinding()]
param(
  [string]$Symbol="NVDA",

  # Backward compatible default mode
  [int]$TradingDays=30,

  # New deterministic modes (YYYY-MM-DD)
  [string]$AsOfDate="",
  [string]$StartDate="",
  [string]$EndDate="",

  [string]$IbHost="127.0.0.1",
  [int]$Port=4002,
  [int]$ClientId=77,
  [switch]$UseRth
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$repoRoot = Split-Path -Parent $PSScriptRoot
$barsDir  = Join-Path $repoRoot "logs\bars"
New-Item -ItemType Directory -Force -Path $barsDir | Out-Null

function IsTradingDay([datetime]$d){
  return ($d.DayOfWeek -notin @('Saturday','Sunday'))
}

function _IsIsoDate([string]$s){
  return ($s -match '^\d{4}-\d{2}-\d{2}$')
}

function Build-DateList {
  $need = @()

  if($AsOfDate -and $AsOfDate.Trim().Length -gt 0){
    $d = $AsOfDate.Trim()
    if(-not (_IsIsoDate $d)){ throw "AsOfDate must be YYYY-MM-DD. Got: $d" }
    return @($d)
  }

  $hasRange = (($StartDate -and $StartDate.Trim().Length -gt 0) -or ($EndDate -and $EndDate.Trim().Length -gt 0))
  if($hasRange){
    $sd = ($StartDate + "").Trim()
    $ed = ($EndDate + "").Trim()
    if(-not (_IsIsoDate $sd)){ throw "StartDate must be YYYY-MM-DD. Got: $sd" }
    if(-not (_IsIsoDate $ed)){ throw "EndDate must be YYYY-MM-DD. Got: $ed" }

    $d0 = [datetime]::ParseExact($sd,"yyyy-MM-dd",$null)
    $d1 = [datetime]::ParseExact($ed,"yyyy-MM-dd",$null)
    if($d1 -lt $d0){ throw "EndDate < StartDate" }

    $d = $d0
    while($d -le $d1){
      if(IsTradingDay $d){ $need += $d.ToString("yyyy-MM-dd") }
      $d = $d.AddDays(1)
    }
    return @($need | Sort-Object)
  }

  # default: last N trading days from today
  $d = Get-Date
  while($need.Count -lt $TradingDays){
    if(IsTradingDay $d){ $need += $d.ToString("yyyy-MM-dd") }
    $d = $d.AddDays(-1)
  }
  return @($need | Sort-Object)
}

$need = @(Build-DateList)
if(-not $need -or $need.Count -eq 0){ throw "No trading days to fetch." }

$ok=0; $fail=0; $skip=0
foreach($asOf in $need){
  $dst = Join-Path $barsDir ("{0}_{1}_1m.csv" -f $Symbol.ToUpperInvariant(), $asOf)
  if(Test-Path -LiteralPath $dst){
    Write-Host "[SKIP] $asOf already cached" -ForegroundColor DarkGray
    $skip += 1
    continue
  }

  Write-Host "`n[FETCH] $asOf" -ForegroundColor Cyan

  $script = (Join-Path $repoRoot "tools\Fetch-IbkrBars.ps1")
  & $script -Symbol $Symbol -AsOfDate $asOf -IbHost $IbHost -Port $Port -ClientId $ClientId -UseRth:$UseRth | Out-Host

  if($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $dst)){
    $ok += 1
  } else {
    Write-Host "[WARN] fetch failed for $asOf exit=$LASTEXITCODE" -ForegroundColor Yellow
    $fail += 1
  }

  Start-Sleep -Milliseconds 550
}

Write-Host "`n[SUMMARY] ok=$ok fail=$fail skip=$skip cached_total=$(@(Get-ChildItem $barsDir -File -Filter ""$($Symbol)_*_1m.csv"").Count)" -ForegroundColor Green
if($fail -gt 0){ exit 2 }
exit 0