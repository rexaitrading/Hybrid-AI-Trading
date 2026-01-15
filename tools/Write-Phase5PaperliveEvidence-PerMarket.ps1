[CmdletBinding()]
param(
  [ValidateSet("ALL","US","JP","HK","SG","IN","KR","TW","CN_SH","CN_SZ","HK_SH","HK_SZ")]
  [string]$Market="ALL",

  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol="NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Resolve-RepoRoot(){
  $toolsDir = Split-Path -Parent $PSCommandPath
  $rr = Split-Path -Parent $toolsDir
  try { return (Resolve-Path -LiteralPath $rr -ErrorAction Stop).Path } catch { return $rr }
}

function Normalize-Utf8Lf([string]$Path){
  # keep file UTF-8 no-BOM + LF + final newline (safe for JSONL)
  $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
  $raw = $raw -replace "`r`n","`n"
  if($raw.Length -eq 0 -or $raw[-1] -ne "`n"){ $raw += "`n" }
  [System.IO.File]::WriteAllText($Path, $raw, (New-Object System.Text.UTF8Encoding($false)))
}

$mode = (($env:HAT_MODE + "")).Trim().ToUpperInvariant()
if($mode -eq "LIVE"){
  throw "[PH5-EVID] FAIL-CLOSED: refusing to copy paperlive evidence while HAT_MODE=LIVE"
}

$repoRoot = Resolve-RepoRoot
$logsRoot = Join-Path $repoRoot "logs"
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"

$srcA = Join-Path $logsRoot ("{0}_phase5_paperlive_results.jsonl" -f $Symbol.ToLowerInvariant())
$srcB = Join-Path $logsRoot ("{0}_phase5_paperlive_results_today.jsonl" -f $Symbol.ToLowerInvariant())

$srcs = @()
if(Test-Path -LiteralPath $srcA){ $srcs += $srcA }
if(Test-Path -LiteralPath $srcB){ $srcs += $srcB }

if($srcs.Count -eq 0){
  throw ("[PH5-EVID] FAIL-CLOSED: missing global inputs: " + $srcA + " and " + $srcB)
}

$targets = @("US","JP","HK","SG","IN","KR","TW","CN_SH","CN_SZ")
if($Market -ne "ALL"){
  $m0 = $Market.ToUpperInvariant()
  $targets = @($m0)
}

foreach($m in $targets){
  $ld = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1") -Market $m
  $ld = ($ld + "").Trim()
  if(-not $ld){ throw "[PH5-EVID] Get-MarketLogRoot returned empty for " + $m }

  New-Item -ItemType Directory -Force -Path $ld | Out-Null

  foreach($src in $srcs){
    $name = Split-Path -Leaf $src
    $dst = Join-Path $ld $name

    Copy-Item -LiteralPath $src -Destination $dst -Force
    Normalize-Utf8Lf $dst

    Write-Host ("[PH5-EVID] wrote " + $dst) -ForegroundColor Green
  }
}

exit 0
