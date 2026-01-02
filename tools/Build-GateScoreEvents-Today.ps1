[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "ALL",

  [int]$MinEvents = 1,
  [switch]$AllowConstantPrice
)

# --- Institutional: flat-price gate (fail-closed unless -AllowConstantPrice) ---
function Get-UniquePriceCount([string]$sym,[string]$asof,[string]$repo){
  $f = Join-Path $repo ("logs\paper_live_{0}_{1}.jsonl" -f $sym,$asof)
  if(-not (Test-Path $f)){ return -1 }
  $px = New-Object System.Collections.Generic.HashSet[string]
  foreach($ln in (Get-Content $f -Encoding utf8)){
    $s = ($ln + "").Trim(); if(-not $s){ continue }
    try{
      $r = $s | ConvertFrom-Json
      $v = [double]($r.price_map.$sym)
      if($v -gt 0){ [void]$px.Add(("{0:F4}" -f $v)) }
    } catch {}
  }
  return $px.Count
}


Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"
$today    = (Get-Date).ToString("yyyy-MM-dd")

function Pick([string]$sym){
  $p = & (Join-Path $toolsDir "Pick-TodayPaperliveSource.ps1") -Symbol $sym -LogsDir $logsDir
  $rc = $LASTEXITCODE
  if($rc -ne 0){ return $null }
  $s = ("" + $p).Trim()
  if([string]::IsNullOrWhiteSpace($s)){ return $null }
  return $s
}

function Run-One([string]$sym){
  $symU = $sym.ToUpper()
  $pick = Pick $symU
  if(-not $pick){
    Write-Host ("[GS-EVENTS] {0} no today source (picker rc!=0)" -f $symU) -ForegroundColor Red
    return @{sym=$symU; ok=$false; reason="no_today_source"; input=""; rows=0}
  }
  if(-not (Test-Path -LiteralPath $pick)){
    Write-Host ("[GS-EVENTS] {0} missing input: {1}" -f $symU,$pick) -ForegroundColor Red
    return @{sym=$symU; ok=$false; reason="missing_input"; input=$pick; rows=0}
  }

  $out = Join-Path $logsDir ("{0}_gatescore_events.jsonl" -f $symU.ToLower())

  # --- Institutional: flat-price gate (uniform; fail-closed unless -AllowConstantPrice) ---
  $repoRoot = (Get-Location).Path
  $u = Get-UniquePriceCount $symU $today $repoRoot
  if((-not $AllowConstantPrice) -and ($u -ge 0) -and ($u -lt 2)){
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($out, "", $utf8NoBom)
    Write-Host ("[{0}-GS-EVENTS] FAIL-CLOSED: degenerate_constant_metrics (unique_prices={1}) -> wrote STUB file only (no official events)" -f $symU,$u)
    return @{sym=$symU; ok=$false; rc=4; reason="degenerate_constant_metrics"; unique_prices=$u; input=$pick; out=$out; rows=0}
  }

  $writer = switch($symU){
    "NVDA" { Join-Path $toolsDir "Write-NvdaGateScoreEventsFromPaperlive.ps1" }
    "SPY"  { Join-Path $toolsDir "Write-SpyGateScoreEventsFromPaperlive.ps1" }
    "QQQ"  { Join-Path $toolsDir "Write-QqqGateScoreEventsFromPaperlive.ps1" }
  }

  if(-not (Test-Path -LiteralPath $writer)){
    Write-Host ("[GS-EVENTS] {0} missing writer: {1}" -f $symU,$writer) -ForegroundColor Red
    return @{sym=$symU; ok=$false; reason="missing_writer"; input=$pick; rows=0}
  }

  # Tighten-only: never fabricate; pass through writer which already ignores synthetic.
  & powershell -NoProfile -ExecutionPolicy Bypass -File $writer -InputPath $pick -OutPath $out -Mode rewrite -MinEvents $MinEvents | Out-Host
  $rc = $LASTEXITCODE

  $rows = 0
  if(Test-Path -LiteralPath $out){
    $rows = @(Get-Content -LiteralPath $out -Encoding utf8).Count
  }

  return @{sym=$symU; ok=($rc -eq 0); rc=$rc; input=$pick; out=$out; rows=$rows}
}

$syms = @()
if($Symbol -eq "ALL"){ $syms = @("NVDA","SPY","QQQ") } else { $syms = @($Symbol) }

$results = @()
foreach($s in $syms){ $results += (Run-One $s) }

# Fail-closed if any required symbol has 0 rows OR rc != 0
$bad = @($results | Where-Object { (-not $_.ok) -or ($_.rows -lt 1) })
$payload = [ordered]@{
  as_of_date = $today
  results = $results
  ok = ($bad.Count -eq 0)
  bad = $bad
}
$payload | ConvertTo-Json -Depth 6 | Out-Host

if($bad.Count -eq 0){ exit 0 }
exit 2
