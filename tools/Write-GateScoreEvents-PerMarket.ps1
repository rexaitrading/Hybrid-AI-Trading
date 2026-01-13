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

$repoRoot = (Resolve-Path ".").Path
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"

# Resolve per-market log root
$rcRaw = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Resolve-RunContext.ps1") -Market $Market -Symbol $Symbol 2>$null | Out-String
$rcRaw = ($rcRaw + "").Trim()
if(-not $rcRaw){ throw "[GS-PERMKT] RunContext empty" }
$rc = $rcRaw | ConvertFrom-Json
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
  # Fail-closed: do not fabricate events when no evidence exists
  Write-Host ("[GS-PERMKT] FAIL-CLOSED: no paperlive input found for market=" + $Market) -ForegroundColor Yellow
  exit 3
}

$writer = Join-Path $repoRoot "tools\Write-NvdaGateScoreEventsFromPaperlive.ps1"
if(-not (Test-Path -LiteralPath $writer)){ throw "[GS-PERMKT] Missing writer: Write-NvdaGateScoreEventsFromPaperlive.ps1" }

$outPath = Join-Path $logsDirOut "nvda_gatescore_events.jsonl"
Write-Host ("[GS-PERMKT] market=" + $Market + " input=" + $input + " out=" + $outPath + " proxy=" + $proxy) -ForegroundColor Cyan

& $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $writer -InputPath $input -OutPath $outPath -MinEvents $MinEvents -Mode $Mode *>&1 | Out-Host
$code = $LASTEXITCODE
if($code -ne 0){
  Write-Host ("[GS-PERMKT] writer exit_code=" + $code) -ForegroundColor Yellow
  exit $code
}

# If proxy mode, stamp metrics_source so LIVE remains denied
if($proxy){
  Rewrite-MetricsSource $outPath '"metrics_source":"paperlive_real_v1"' '"metrics_source":"proxy_us_paperlive_v1"'
  Rewrite-MetricsSource $outPath '"metrics_source":"paperlive_real_v2"' '"metrics_source":"proxy_us_paperlive_v1"'
  Write-Host ("[GS-PERMKT] proxy stamp applied: metrics_source=proxy_us_paperlive_v1") -ForegroundColor Yellow
}

Write-Host ("[GS-PERMKT] OK wrote " + $outPath) -ForegroundColor Green
exit 0
