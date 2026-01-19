  [ValidateSet("US","JP","HK","HK_SH","HK_SZ","SG","IN","KR","TW")]
param(
  [ValidateSet("US","JP","HK","HK_SH","HK_SZ","SG","IN","KR","TW")]
  [string]$Market = "US"
)

Set-StrictMode -Version Latest
# --- HAT_RUNMODE_SINGLETRUTH_BEGIN
$toolsDir = Split-Path -Parent $PSCommandPath
$rmPath = Join-Path $toolsDir "Resolve-HatRunMode.ps1"
if(-not (Test-Path -LiteralPath $rmPath)){ throw "[FAIL-CLOSED] missing Resolve-HatRunMode.ps1" }
$rmRaw = (& $rmPath 2>&1 | Out-String)
$ix0 = $rmRaw.IndexOf("{"); $ix1 = $rmRaw.LastIndexOf("}")
if($ix0 -lt 0 -or $ix1 -le $ix0){ throw "[FAIL-CLOSED] Resolve-HatRunMode did not return JSON" }
$rmObj = ($rmRaw.Substring($ix0, ($ix1 - $ix0 + 1)) | ConvertFrom-Json -ErrorAction Stop)
$script:__HAT_RUNMODE = ([string]$rmObj.run_mode).Trim().ToUpperInvariant()
# --- HAT_RUNMODE_SINGLETRUTH_END
$ErrorActionPreference="Stop"

# HK Stock Connect routing: write to MarketOut, compute RunContext on MarketBase
$MarketOut = ($Market + "").Trim().ToUpperInvariant()
if(-not $MarketOut){ $MarketOut = "US" }
$MarketBase = $MarketOut
if($MarketBase -eq "HK_SH" -or $MarketBase -eq "HK_SZ"){ $MarketBase = "HK" }

chcp 65001 | Out-Null

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n","`n"
  if($Text.Length -gt 0 -and $Text[-1] -ne "`n"){ $Text += "`n" }
  [System.IO.File]::WriteAllText($Path,$Text,$utf8)
}
function Slice-Date([string]$s){
  $s = ($s + "").Trim()
  if($s.Length -ge 10){ return $s.Substring(0,10) }
  return $s
}

function Get-EvidenceTodayRows([string]$LogsDir,[string]$TodayLocal){
  $ev = Join-Path $LogsDir "nvda_gatescore_events.jsonl"
  if(-not (Test-Path -LiteralPath $ev)){ return 0 }
  try{
    $pat = '"as_of_date":"{0}"' -f $TodayLocal
    $n = (Select-String -LiteralPath $ev -Pattern $pat -SimpleMatch -ErrorAction SilentlyContinue | Measure-Object).Count
    return [int]$n
  } catch { return 0 }
}
function Has-ProxyMetricsToday([string]$LogsDir,[string]$TodayLocal){
  $ev = Join-Path $LogsDir "nvda_gatescore_events.jsonl"
  if(-not (Test-Path -LiteralPath $ev)){ return $true } # fail-closed
  try{
    $patDay = '"as_of_date":"{0}"' -f $TodayLocal
    $hits = Select-String -LiteralPath $ev -Pattern $patDay -SimpleMatch -ErrorAction SilentlyContinue
    foreach($h in $hits){
      if($h.Line -match '"metrics_source":"proxy_'){ return $true }
    }
    return $false
  } catch { return $true } # fail-closed
}
function Allow-NonLiveUs([string]$Market){
  # Non-LIVE may evaluate any market; LIVE remains strict fail-closed.
  $mode = $script:__HAT_RUNMODE
  if($mode -eq "LIVE"){ return $false }
  return $true
}


$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$rc = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Resolve-RunContext.ps1") -Market $MarketBase -Symbol NVDA | ConvertFrom-Json
$todayLocal = Slice-Date ([string]$rc.as_of_date)

$logsDir = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1") -Market $MarketOut
if(-not $logsDir){ $logsDir = Join-Path $repoRoot "logs" }
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null;
$outPath = Join-Path $logsDir "market_dna.json"
$obj = [ordered]@{
  ts_utc     = (Get-Date).ToUniversalTime().ToString("o")
  market     = $MarketOut
  as_of_date = $todayLocal
  ok_today   = $false
  dna_class  = "unknown"
  reason     = "stub_not_implemented"
}

try {
  if($rc -and ($rc.PSObject.Properties.Name -contains "market_closed_today") -and [bool]$rc.market_closed_today){
    $obj.ok_today = $true
    try { $obj["not_evaluated_market_closed"] = $true } catch { }
    try { if($rc.PSObject.Properties.Name -contains "market_closed_reason"){ $obj["market_closed_reason"] = [string]$rc.market_closed_reason } } catch { }
    $obj.reason = "market_closed_today"
  }
} catch { }


$evidenceRows = Get-EvidenceTodayRows -LogsDir $logsDir -TodayLocal $todayLocal
$allow = (Allow-NonLiveUs -Market $Market)
if($allow -and $evidenceRows -gt 0){
  # GREADY_PROXY_DENY_MAIN_BEGIN
  # Strict: proxy-only GateScore evidence does NOT satisfy Global-Ready.
  $proxyRowsToday = 0
  try {
    $evPath = Join-Path $logsDir "nvda_gatescore_events.jsonl"
    if(Test-Path -LiteralPath $evPath){
      $patDay = '"as_of_date":"{0}"' -f $todayLocal
      foreach($h in (Select-String -LiteralPath $evPath -Pattern $patDay -SimpleMatch -ErrorAction SilentlyContinue)){
        if($h.Line -match '"metrics_source":"proxy_'){ $proxyRowsToday += 1 }
      }
    }
  } catch { $proxyRowsToday = $evidenceRows }
  if($proxyRowsToday -ge $evidenceRows){
  # moved_by_proxydeny $obj.ok_today = $true
  $obj.dna_class = "institutional-compression"
  $obj.reason = "default_nonlive_us"
    # Deny (keep ok_today false), but set accurate reason(s)
    try {
      if($obj.Contains("reason")){ $obj.reason = "deny_proxy_metrics_source" }
      if($obj.Contains("reasons")){ $obj.reasons = @("deny_proxy_metrics_source") }
    } catch {
      try { $obj.reason = "deny_proxy_metrics_source" } catch { }
    }
  } else {
    # allow non-proxy evidence
    $obj.ok_today = $true
  }
# GREADY_PROXY_DENY_MAIN_END
} else {
  if(-not $allow){ $obj.reason = "blocked_policy_nonlive_us_only" }
  elseif($evidenceRows -le 0){
  # GREADY_PROXY_REASON_BEGIN
  # Strict policy: proxy-only GateScore evidence does NOT satisfy Global-Ready.
  # But the reason must be accurate (avoid "missing evidence" when proxy rows exist).
  try {
    $todayRows = 0
    $todayProxyRows = 0
    $evPath = Join-Path $logsDir "nvda_gatescore_events.jsonl"
    if(Test-Path -LiteralPath $evPath){
      foreach($ln in (Get-Content -LiteralPath $evPath -Encoding UTF8)){
        $s = ($ln + "").Trim(); if(-not $s){ continue }
        try {
          $e = $s | ConvertFrom-Json
          $d = ""
          if($e.PSObject.Properties.Name -contains "as_of_date"){
            $d = ([string]$e.as_of_date)
            if($d.Length -ge 10){ $d = $d.Substring(0,10) }
          }
          if($d -ne $todayLocal){ continue }
          $todayRows += 1
          $ms = ""
          if($e.PSObject.Properties.Name -contains "metrics_source"){ $ms = ([string]$e.metrics_source).Trim() }
          if($ms -match '^(?i)proxy_'){ $todayProxyRows += 1 }
        } catch { }
      }
    }
    if($todayRows -gt 0 -and $todayProxyRows -ge $todayRows){
      $obj.reason = "deny_proxy_metrics_source"
    } else {
      $obj.reason = "missing_gatescore_evidence_today"
    }
  } catch {
    $obj.reason = "missing_gatescore_evidence_today"
  }
  # GREADY_PROXY_REASON_END
}
}
$obj["evidence_path"] = (Join-Path $logsDir "nvda_gatescore_events.jsonl")
$obj["evidence_rows_today"] = [int]$evidenceRows

Write-Utf8NoBomLf $outPath ($obj | ConvertTo-Json -Depth 6)
Write-Host ("[DNA] wrote " + $outPath + " ok_today=" + ([bool]$obj.ok_today) + " reason=" + ([string]$obj.reason)) -ForegroundColor Yellow
