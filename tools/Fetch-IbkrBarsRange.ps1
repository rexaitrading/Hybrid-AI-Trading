[CmdletBinding()]
param(
  [string]$Symbol="NVDA",
  [int]$TradingDays=30,
  [string]$IbHost="127.0.0.1",
  [int]$Port=4002,
  [int]$ClientId=77,
  [switch]$UseRth
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$repoRoot = Split-Path -Parent $PSScriptRoot
$barsDir = Join-Path $repoRoot "logs\bars"
New-Item -ItemType Directory -Force -Path $barsDir | Out-Null

function IsTradingDay([datetime]$d){ return ($d.DayOfWeek -notin @('Saturday','Sunday')) }

# Build last N trading days (holiday handling later)
$need=@()
$d=Get-Date
while($need.Count -lt $TradingDays){
  if(IsTradingDay $d){ $need += $d.ToString("yyyy-MM-dd") }
  $d=$d.AddDays(-1)
}
$need=@($need | Sort-Object)

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

  # In-process call (no nested powershell.exe) so exit semantics are deterministic
  try {
    & $script -Symbol $Symbol -AsOfDate $asOf -IbHost $IbHost -Port $Port -ClientId $ClientId -UseRth:$UseRth | Out-Host
  } catch {
    Write-Host ("[WARN] in-proc fetch threw for " + $asOf + ": " + [CmdletBinding()]
param(
  [string]$Symbol="NVDA",
  [int]$TradingDays=30,
  [string]$IbHost="127.0.0.1",
  [int]$Port=4002,
  [int]$ClientId=77,
  [switch]$UseRth
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$repoRoot = Split-Path -Parent $PSScriptRoot
$barsDir = Join-Path $repoRoot "logs\bars"
New-Item -ItemType Directory -Force -Path $barsDir | Out-Null

function IsTradingDay([datetime]$d){ return ($d.DayOfWeek -notin @('Saturday','Sunday')) }

# Build last N trading days (holiday handling later)
$need=@()
$d=Get-Date
while($need.Count -lt $TradingDays){
  if(IsTradingDay $d){ $need += $d.ToString("yyyy-MM-dd") }
  $d=$d.AddDays(-1)
}
$need=@($need | Sort-Object)

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
  $argv = @(
    "-File", $script,
    "-Symbol", $Symbol,
    "-AsOfDate", $asOf,
    "-IbHost", $IbHost,
    "-Port", $Port,
    "-ClientId", $ClientId
  )
  if($UseRth.IsPresent){ $argv += @("-UseRth") }

  & powershell -NoProfile -ExecutionPolicy Bypass @argv | Out-Host

  if($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $dst)){
    $ok += 1
  } else {
    Write-Host "[WARN] fetch failed for $asOf exit=$LASTEXITCODE" -ForegroundColor Yellow
    $fail += 1
  }

  Start-Sleep -Milliseconds 550
}

Write-Host "`n[SUMMARY] ok=$ok fail=$fail skip=$skip cached_total=$(@(Get-ChildItem $barsDir -File -Filter "$($Symbol)_*_1m.csv").Count)" -ForegroundColor Green
exit 0.Exception.Message) -ForegroundColor Yellow
  }

  # Contract: file existence is truth
  if(Test-Path -LiteralPath $dst){
    $ok += 1
  } else {
    Write-Host "[WARN] fetch failed for $asOf (missing file) exit=$LASTEXITCODE" -ForegroundColor Yellow
    $fail += 1
  }if($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $dst)){
    $ok += 1
  } else {
    Write-Host "[WARN] fetch failed for $asOf exit=$LASTEXITCODE" -ForegroundColor Yellow
    $fail += 1
  }

  Start-Sleep -Milliseconds 550
}

Write-Host "`n[SUMMARY] ok=$ok fail=$fail skip=$skip cached_total=$(@(Get-ChildItem $barsDir -File -Filter "$($Symbol)_*_1m.csv").Count)" -ForegroundColor Green
exit 0