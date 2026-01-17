[CmdletBinding()]
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
function Allow-NonLiveAny(){
  $mode = $script:__HAT_RUNMODE
  if($mode -eq "LIVE"){ return $false }
  return $true
}


$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$rc = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Resolve-RunContext.ps1") -Market $Market -Symbol NVDA | ConvertFrom-Json
$todayLocal = Slice-Date ([string]$rc.as_of_date)

$logsDir = ([string]$rc.logs_dir_out).Trim()
if(-not $logsDir){ throw "[A3] logsDir unresolved from Resolve-RunContext (fail-closed)" }
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

# GREADY_POLICYB_CLOSED_DAY_BEGIN
# Policy B: market-closed days are NOT evaluated but are diagnostic-OK (ok_today=true).
try {
  if($rc -and ($rc.PSObject.Properties.Name -contains "market_closed_today") -and [bool]$rc.market_closed_today){
    $obj.ok_today = $true
    try { $obj["not_evaluated_market_closed"] = $true } catch { }
    try { if($rc.PSObject.Properties.Name -contains "market_closed_reason"){ $obj["market_closed_reason"] = [string]$rc.market_closed_reason } } catch { }
    try { if($obj.PSObject.Properties.Name -contains "reason"){ $obj.reason = "market_closed_today" } else { $obj["reason"] = "market_closed_today" } } catch { try { $obj["reason"]="market_closed_today" } catch { } }
  }
} catch { }
# GREADY_POLICYB_CLOSED_DAY_END


$evidenceRows = Get-EvidenceTodayRows -LogsDir $logsDir -TodayLocal $todayLocal
$allow = (Allow-NonLiveAny)
if($allow -and $evidenceRows -gt 0){
      # GREADY_PROXY_DENY_RISK_BEGIN
    # Strict: proxy-only GateScore evidence does NOT satisfy RiskGuard global-ready.
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
      $obj.ok_today = $false
      $obj.kill_switch_armed = $true
      $obj.cooldown_minutes = 0
      $obj.reasons = @("deny_proxy_metrics_source")
    } else {
      # G4 minimal non-live guard: with real (non-proxy) GateScore evidence, allow RiskGuard to pass.
      $obj.ok_today = $true
      $obj.kill_switch_armed = $false
      $obj.cooldown_minutes = 0
      $obj.reasons = @("default_nonlive_us")
    }
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
Write-Host ("[RISK] wrote " + $outPath + " ok_today=" + ([bool]$obj.ok_today) + " kill_switch_armed=" + ([bool]$obj.kill_switch_armed) + " reasons=" + ((@($obj.reasons) -join ","))) -ForegroundColor Yellow
