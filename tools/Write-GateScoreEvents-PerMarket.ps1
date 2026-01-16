[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ","CN_SH","CN_SZ")]
  [string]$Market="US",
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol="NVDA",
  [ValidateSet("rewrite","append","prune")]
  [string]$Mode="rewrite",
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
    $t = ($ln + '''').Trim()
    if(-not $t){ continue }
    try {
      $o = $t | ConvertFrom-Json -ErrorAction Stop
      if($o){
        if($o.PSObject.Properties.Name -contains 'metrics_source'){ $o.metrics_source = 'proxy_us_paperlive_v1' }
        else { $o | Add-Member -NotePropertyName 'metrics_source' -NotePropertyValue 'proxy_us_paperlive_v1' -Force }
        $out.Add(($o | ConvertTo-Json -Compress))
        $changed++
      }
    } catch {
      $out.Add($t)
    }
  }
  if($changed -gt 0){
    $txt = (($out.ToArray() -join "
") + "
")
    [System.IO.File]::WriteAllText($Path, $txt, (New-Object System.Text.UTF8Encoding($false)))
  }
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
$logsDirOut = [string]$rc.logs_dir_out
if(-not $logsDirOut){ throw "[GS-PERMKT] RunContext missing logs_dir_out" }
New-Item -ItemType Directory -Force -Path $logsDirOut | Out-Null

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

$writer = Join-Path $repoRoot "tools\Write-NvdaGateScoreEventsFromPaperlive.ps1"
if(-not (Test-Path -LiteralPath $writer)){ throw "[GS-PERMKT] Missing writer: Write-NvdaGateScoreEventsFromPaperlive.ps1" }

$outPath = Join-Path $logsDirOut "nvda_gatescore_events.jsonl"
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
# If proxy mode, stamp metrics_source so LIVE remains denied
if($proxy){
  Stamp-ProxyMetricsSourceJsonl $outPath
  Write-Host ("[GS-PERMKT] proxy stamp applied: metrics_source=proxy_us_paperlive_v1") -ForegroundColor Yellow
}
Write-Host ("[GS-PERMKT] OK wrote " + $outPath) -ForegroundColor Green
exit 0
