#requires -Version 5.1
[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "US"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Slice10([string]$s){ $s=(($s+"")).Trim(); if($s.Length -ge 10){ return $s.Substring(0,10) } return $s }
function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n","`n"
  if($Text.Length -gt 0 -and $Text[-1] -ne "`n"){ $Text += "`n" }
  [System.IO.File]::WriteAllText($Path,$Text,$utf8)
}

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $toolsDir) -ErrorAction Stop).Path
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

# logs dir (single-truth)
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$logsDir = (& $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1") -Market $Market 2>$null | Out-String).Trim()
if(-not $logsDir){ $logsDir = Join-Path $repoRoot ("logs\{0}" -f $Market) }
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

# RunContext as_of_date
$rcPath = Join-Path $repoRoot "tools\Resolve-RunContext.ps1"
$rcRaw = & $rcPath -Market $Market -Symbol NVDA 2>$null | Out-String
$rcRaw = (($rcRaw+"")).Trim()
$i0=$rcRaw.IndexOf("{"); $i1=$rcRaw.LastIndexOf("}")
if($i0 -lt 0 -or $i1 -le $i0){ throw "[FAIL-CLOSED] Resolve-RunContext did not return JSON" }
$rc = ($rcRaw.Substring($i0, ($i1-$i0+1)) | ConvertFrom-Json -ErrorAction Stop)
$asof = Slice10 ([string]$rc.as_of_date)
if(-not $asof){ throw "[FAIL-CLOSED] as_of_date empty" }

# Primary module policy (single A+ module per market)
$mk = (($Market+"")).Trim().ToUpperInvariant()
$primary = ""
switch($mk){
  "US"    { $primary = "US_VWAP_Overnight_Reversion" }
  "JP"    { $primary = "JP_Opening_Overreaction_Fade" }
  "KR"    { $primary = "KR_Emotional_Spike_Fade" }
  "TW"    { $primary = "TW_Institutional_Flow_Confirm" }
  "HK"    { $primary = "HK_Index_Relative_Reversion" }
  "HK_SH" { $primary = "HK_Index_Relative_Reversion" }
  "HK_SZ" { $primary = "HK_Index_Relative_Reversion" }
  "SG"    { $primary = "" } # not yet promoted
  "IN"    { $primary = "" } # not yet promoted
  default { $primary = "" }
}

$out = [ordered]@{
  schema        = "market_module_policy.v1"
  market        = $mk
  as_of_date    = $asof
  primary_module = $primary
  allowed_session = "RTH"
  ts_utc        = (Get-Date).ToUniversalTime().ToString("o")
  note          = "Single-module A+ policy. Empty primary_module means market not yet promoted."
}

$outPath = Join-Path $logsDir "market_module_policy.json"
Write-Utf8NoBomLf $outPath ($out | ConvertTo-Json -Depth 6)
Write-Host ("[POLICY] wrote " + $outPath + " primary_module=" + $primary) -ForegroundColor Yellow
return
