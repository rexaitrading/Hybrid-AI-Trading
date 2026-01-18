[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market="US",
  [string]$Symbol="NVDA"
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

# Normalize CN_* -> HK_* (no engine constraints)
$marketIn = ($Market + "").Trim().ToUpperInvariant()
switch($marketIn){
default { }
}

$toolsDir = Split-Path -Parent $PSCommandPath
$rcPath   = Join-Path $toolsDir "Resolve-RunContext.ps1"

# Single truth: use RunContext for logs_dir_out + as_of_date
$rcRaw = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $rcPath -Market $Market -Symbol $Symbol 2>$null | Out-String
$rcRaw = ($rcRaw + "").Trim()
if(-not $rcRaw){ throw "Resolve-RunContext returned empty stdout" }
$rc = $rcRaw | ConvertFrom-Json

$ld = [string]$rc.logs_dir_out
if(-not $ld){ throw "RunContext logs_dir_out missing" }
New-Item -ItemType Directory -Force -Path $ld | Out-Null

$asOf = [string]$rc.as_of_date
if(-not $asOf){ $asOf = (Get-Date).ToString("yyyy-MM-dd") }

  $mode = $script:__HAT_RUNMODE
if(-not $mode){ $mode = "PAPER" }
$isLive = ($mode -eq "LIVE")

$outPath     = Join-Path $ld "crisis_regime_status.json"
$flattenPath = Join-Path $ld "crashmode_flatten_status.json"

function _Slice([string]$d){
  $t=(($d+"")).Trim()
  if($t.Length -ge 10){ $t=$t.Substring(0,10) }
  $t
}

# Defaults
$okToday = $false
$crisisRegime = $false
$reason = "missing_flatten_status_fail_closed"

# LIVE: require flatten ok for the same as_of_date
if(Test-Path -LiteralPath $flattenPath){
  try {
    $fj = Get-Content -LiteralPath $flattenPath -Raw -Encoding UTF8 | ConvertFrom-Json

    $fok = $false
    if($fj.PSObject.Properties.Name -contains "ok_today"){ $fok = [bool]$fj.ok_today }
    elseif($fj.PSObject.Properties.Name -contains "ok"){ $fok = [bool]$fj.ok }

    $fDate = ""
    if($fj.PSObject.Properties.Name -contains "as_of_date"){ $fDate = _Slice ([string]$fj.as_of_date) }
    elseif($fj.PSObject.Properties.Name -contains "ts_utc"){
      $dto = [DateTimeOffset]::Parse(([string]$fj.ts_utc))
      $fDate = _Slice ($dto.UtcDateTime.ToString("yyyy-MM-dd"))
    }

    if($fok -and $fDate -eq $asOf){
      $okToday = $true
      $crisisRegime = $false
      $reason = "flatten_ok_today"
    } else {
      $okToday = $false
      $crisisRegime = $false
      $reason = "flatten_stale_or_not_ok"
    }
  } catch {
    $okToday = $false
    $crisisRegime = $false
    $reason = "flatten_parse_error_fail_closed"
  }
}

# NON-LIVE: never block paper ops
if(-not $isLive){
  $okToday = $true
  $crisisRegime = $false
  if($reason -eq "flatten_stale_or_not_ok"){ $reason = "nonlive_default_ok_flatten_stale" }
  elseif($reason -eq "missing_flatten_status_fail_closed"){ $reason = "nonlive_default_ok_missing_flatten" }
  elseif($reason -eq "flatten_parse_error_fail_closed"){ $reason = "nonlive_default_ok_flatten_parse_error" }
  else { $reason = ("nonlive_default_ok_" + $reason) }
}

$payload = [ordered]@{
  ts_utc       = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date   = $asOf
  ok_today     = [bool]$okToday
  crisis_regime= [bool]$crisisRegime
  reason       = [string]$reason
  source       = "crashmode_flatten_status"
}

# UTF-8 no BOM + LF
$json = ($payload | ConvertTo-Json -Depth 6) -replace "`r`n","`n"
if($json.Length -gt 0 -and $json[-1] -ne "`n"){ $json += "`n" }
[System.IO.File]::WriteAllText($outPath,$json,(New-Object System.Text.UTF8Encoding($false)))

Write-Output ("[CRISIS] wrote " + $outPath + " ok_today=" + $okToday + " mode=" + $mode + " as_of=" + $asOf + " reason=" + $reason)
