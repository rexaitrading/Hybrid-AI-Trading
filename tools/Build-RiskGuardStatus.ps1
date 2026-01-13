[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","CN_SH","CN_SZ")]
  [string]$Market = "US"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
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
  $mode = ($env:HAT_MODE + "").Trim().ToUpperInvariant()
  if($mode -eq "LIVE"){ return $false }
  return ($Market.ToUpperInvariant() -eq "US")
}


$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$rc = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Resolve-RunContext.ps1") -Market $Market -Symbol NVDA | ConvertFrom-Json
$todayLocal = Slice-Date ([string]$rc.as_of_date)

$logsDir = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1") -Market $Market
if(-not $logsDir){ $logsDir = Join-Path $repoRoot "logs" }
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null;
$outPath = Join-Path $logsDir "risk_guard_status.json"
$obj = [ordered]@{
  ts_utc            = (Get-Date).ToUniversalTime().ToString("o")
  market            = $Market
  as_of_date        = $todayLocal
  ok_today          = $false
  kill_switch_armed = $true
  cooldown_minutes  = 0
  reasons           = @("stub_not_implemented")
}

$evidenceRows = Get-EvidenceTodayRows -LogsDir $logsDir -TodayLocal $todayLocal
$allow = (Allow-NonLiveUs -Market $Market)
if($allow -and $evidenceRows -gt 0){
  $obj.ok_today = $true
  $obj.kill_switch_armed = $false
  $obj.cooldown_minutes = 0
  $obj.reasons = @("default_nonlive_us")
} else {
  $rs = @()
  if(-not $allow){ $rs += "blocked_policy_nonlive_us_only" }
  elseif($evidenceRows -le 0){ $rs += "missing_gatescore_evidence_today" }
  if($rs.Count -eq 0){ $rs = @("stub_not_implemented") }
  $obj.reasons = $rs
}
$obj["evidence_path"] = (Join-Path $logsDir "nvda_gatescore_events.jsonl")
$obj["evidence_rows_today"] = [int]$evidenceRows

Write-Utf8NoBomLf $outPath ($obj | ConvertTo-Json -Depth 8)
Write-Host ("[RISK] wrote " + $outPath + " ok_today=false reason=stub_not_implemented") -ForegroundColor Yellow
