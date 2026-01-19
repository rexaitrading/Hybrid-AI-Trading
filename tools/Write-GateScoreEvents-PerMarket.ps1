[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market="US",
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol="NVDA",
  [ValidateSet("rewrite","append","prune")]
  [string]$Mode="append",
  [int]$MinEvents=10
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n","`n"
  if($Text.Length -gt 0 -and $Text[-1] -ne "`n"){ $Text += "`n" }
  [System.IO.File]::WriteAllText($Path, $Text, $utf8)
}
# PROXY_STAMP_JSONL_BEGIN
function Stamp-ProxyMetricsSourceJsonl([string]$Path){
  if(-not (Test-Path -LiteralPath $Path)){ return }
  $in = @(Get-Content -LiteralPath $Path -Encoding UTF8)
  if(-not $in -or $in.Count -eq 0){ return }
  $out = New-Object System.Collections.Generic.List[string]
  $changed = 0
  foreach($ln in $in){
    $t = (($ln + "")).Trim()
    if(-not $t){ continue }
    try {
      $o = $t | ConvertFrom-Json -ErrorAction Stop
      if($null -ne $o){
        $prior = $null
        if($o.PSObject.Properties.Name -contains "metrics_source"){ $prior = [string]$o.metrics_source }
        if($prior -ne "proxy_us_paperlive_v1"){
          $o | Add-Member -NotePropertyName metrics_source -NotePropertyValue "proxy_us_paperlive_v1" -Force
          $changed++
        }
        $out.Add(($o | ConvertTo-Json -Compress))
        continue
      }
    } catch { }
    $out.Add($t)
  }
  if($changed -le 0){ return }
  $txt2 = ($out.ToArray() -join "`n")
  $txt2 = $txt2 -replace "`r`n","`n"
  if($txt2.Length -gt 0 -and $txt2[-1] -ne "`n"){ $txt2 += "`n" }
  [System.IO.File]::WriteAllText($Path, $txt2, (New-Object System.Text.UTF8Encoding($false)))
}
# PROXY_STAMP_JSONL_END


function Rewrite-MetricsSource([string]$Path,[string]$From,[string]$To){
  if(-not (Test-Path -LiteralPath $Path)){ return }
  $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
  if(-not $raw){ return }
  # line-based JSONL rewrite; minimal mutation
  $raw2 = $raw.Replace($From,$To)
  if($raw2 -ne $raw){
    Write-Utf8NoBomLf $Path $raw2
  }
}

function Resolve-RepoRoot(){
  $toolsDir = Split-Path -Parent $PSCommandPath
  $rr = Split-Path -Parent $toolsDir
  try { return (Resolve-Path -LiteralPath $rr -ErrorAction Stop).Path } catch { return $rr }
}
$repoRoot = Resolve-RepoRoot
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"

# Resolve per-market log root
$rcRaw = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Resolve-RunContext.ps1") -Market $Market -Symbol $Symbol 2>$null | Out-String
$rcRaw = ($rcRaw + "").Trim()
if(-not $rcRaw){ throw "[GS-PERMKT] RunContext empty" }
$rc = $rcRaw | ConvertFrom-Json
# ASOF_ENV_BEGIN
try {
  if($rc -and ($rc.PSObject.Properties.Name -contains 'as_of_date')){
    $d = (([string]$rc.as_of_date)).Trim()
    if($d.Length -gt 10){ $d = $d.Substring(0,10) }
    if($d -match '^\d{4}-\d{2}-\d{2}$'){ $env:HAT_ASOF_DATE = $d }
  }
} catch { }
# ASOF_ENV_END
# LOGSDIROUT_FS_TRUTH_BEGIN
# FS-truth: do NOT trust RunContext logs_dir_out string (can be mojibake); build logs path from repoRoot + market.
$m2 = ([string]$Market).Trim().ToUpperInvariant()
if(-not $m2){ $m2 = "US" }
$logsDirOut = Join-Path (Join-Path $repoRoot "logs") $m2
New-Item -ItemType Directory -Force -Path $logsDirOut | Out-Null
# LOGSDIROUT_FS_TRUTH_END

# Candidate inputs (local first)
$localInputs = @(
  (Join-Path $logsDirOut "nvda_phase5_paperlive_results.jsonl"),
  (Join-Path $logsDirOut "nvda_phase5_paperlive_results_today.jsonl"),
  (Join-Path $logsDirOut "nvda_phase5_paperexec_results.jsonl")
)

$input = ""
foreach($p in $localInputs){
  if(Test-Path -LiteralPath $p){ $input = $p; break }
}

$proxy = $false
if(-not $input){
  # Global fallback: Phase-5 evidence may still be global-only in plumbing stage
  $gDir = Join-Path $repoRoot "logs"
  $gInputs = @(
    (Join-Path $gDir "nvda_phase5_paperlive_results.jsonl"),
    (Join-Path $gDir "nvda_phase5_paperlive_results_today.jsonl"),
    (Join-Path $gDir "nvda_phase5_paperexec_results.jsonl")
  )
  foreach($p in $gInputs){
    if(Test-Path -LiteralPath $p){
      $input = $p
      if($Market -ne "US"){ $proxy = $true }
      break
    }
  }
}
if(-not $input){
  # Plumbing-only fallback: allow using US market paperlive inputs for non-US markets
  if($Market -ne "US"){
    $usDir = Join-Path (Join-Path $repoRoot "logs") "US"
    $usInputs = @(
      (Join-Path $usDir "nvda_phase5_paperlive_results.jsonl"),
      (Join-Path $usDir "nvda_phase5_paperlive_results_today.jsonl"),
      (Join-Path $usDir "nvda_phase5_paperexec_results.jsonl")
    )
    foreach($p in $usInputs){
      if(Test-Path -LiteralPath $p){ $input = $p; $proxy = $true; break }
    }
  }
}
if(-not $input){
  # Global fallback: Phase-5 evidence may still be global-only in plumbing stage
  $gDir = Join-Path $repoRoot "logs"
  $gInputs = @(
    (Join-Path $gDir "nvda_phase5_paperlive_results.jsonl"),
    (Join-Path $gDir "nvda_phase5_paperlive_results_today.jsonl"),
    (Join-Path $gDir "nvda_phase5_paperexec_results.jsonl")
  )
  foreach($p in $gInputs){
    if(Test-Path -LiteralPath $p){
      $input = $p
      if($Market -ne "US"){ $proxy = $true }
      break
    }
  }
}

if(-not $input){
  # Fail-closed: do not fabricate events when no evidence exists
  Write-Host ("[GS-PERMKT] FAIL-CLOSED: no paperlive input found for market=" + $Market) -ForegroundColor Yellow
  exit 3
}

$symU = (([string]$Symbol).Trim().ToUpperInvariant())
if(-not $symU){ $symU = "NVDA" }
$writer = switch($symU){
  "NVDA" { Join-Path $repoRoot "tools\Write-NvdaGateScoreEventsFromPaperlive.ps1" }
  "SPY"  { Join-Path $repoRoot "tools\Write-SpyGateScoreEventsFromPaperlive.ps1" }
  "QQQ"  { Join-Path $repoRoot "tools\Write-QqqGateScoreEventsFromPaperlive.ps1" }
  default { Join-Path $repoRoot "tools\Write-NvdaGateScoreEventsFromPaperlive.ps1" }
}
if(-not (Test-Path -LiteralPath $writer)){ throw "[GS-PERMKT] Missing writer: Write-NvdaGateScoreEventsFromPaperlive.ps1" }

$outPath = Join-Path $logsDirOut (("{0}_gatescore_events.jsonl" -f $symU.ToLowerInvariant()))
Write-Host ("[GS-PERMKT] market=" + $Market + " input=" + $input + " out=" + $outPath + " proxy=" + $proxy) -ForegroundColor Cyan
# PROXY_MODE_ENV_BEGIN
try {
  if($proxy){ $env:HAT_GATESCORE_PROXY_MODE = "1" } else { Remove-Item Env:\HAT_GATESCORE_PROXY_MODE -ErrorAction SilentlyContinue }
} catch { }
# PROXY_MODE_ENV_END

& $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $writer -InputPath $input -OutPath $outPath -MinEvents $MinEvents -Mode $Mode *>&1 | Out-Host
$code = $LASTEXITCODE
if($code -ne 0){
  Write-Host ("[GS-PERMKT] writer exit_code=" + $code) -ForegroundColor Yellow
  exit $code
}
# CANON_OUTPATH_FOR_PROXY_STAMP_BEGIN
# Always stamp the canonical filesystem path (prevents mojibake path mismatch)
try {
  if(Test-Path -LiteralPath $outPath){
    $outPath = (Resolve-Path -LiteralPath $outPath).Path
  }
} catch { }
# CANON_OUTPATH_FOR_PROXY_STAMP_END
# If proxy mode, stamp metrics_source so LIVE remains denied# TODAYLOCAL_BEGIN
# market-day truth (RunContext)
$todayLocal = ""
try {
  if($rc -and ($rc.PSObject.Properties.Name -contains "as_of_date")){
    $todayLocal = (([string]$rc.as_of_date)).Trim()
    if($todayLocal.Length -gt 10){ $todayLocal = $todayLocal.Substring(0,10) }
  }
} catch { $todayLocal = "" }
# TODAYLOCAL_END

# If non-US market, stamp metrics_source so LIVE remains denied (fail-closed, deterministic)
$m2 = ([string]$Market).Trim().ToUpperInvariant()
if(-not $m2){ $m2 = "US" }
# GS_PROXY_STAMP_ONLY_WHEN_PROXY_BEGIN
if($proxy){
# GS_PROXY_STAMP_ONLY_WHEN_PROXY_END
  Stamp-ProxyMetricsSourceJsonl $outPath
  Write-Host ("[GS-PERMKT] proxy stamp applied: metrics_source=proxy_us_paperlive_v1") -ForegroundColor Yellow
}
Write-Host ("[GS-PERMKT] OK wrote " + $outPath) -ForegroundColor Green
exit 0