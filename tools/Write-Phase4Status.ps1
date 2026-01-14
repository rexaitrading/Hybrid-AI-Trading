[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")] [string]$Market="US",
  [ValidateSet("NVDA","SPY","QQQ")] [string]$Symbol="NVDA"
)
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

function Get-CanonicalRepoRoot {
  # FAIL-CLOSED canonical repo root (prefer env:HAT_REPO_ROOT if valid)
  $envRoot = ($env:HAT_REPO_ROOT + "").Trim()
  if($envRoot){
    try {
      $r = (Resolve-Path -LiteralPath $envRoot -ErrorAction Stop).Path
      if(Test-Path -LiteralPath (Join-Path $r ".git")){ return $r }
    } catch { }
  }
  $p = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..") -ErrorAction Stop).Path
  while($p -and -not (Test-Path -LiteralPath (Join-Path $p ".git"))){
    $parent = Split-Path -Parent $p
    if(-not $parent -or $parent -eq $p){ break }
    $p = $parent
  }
  if(-not $p -or -not (Test-Path -LiteralPath (Join-Path $p ".git"))){
    throw "[FAIL-CLOSED] repo root not found (.git missing). envRoot=$envRoot scriptRoot=$PSScriptRoot"
  }
  return $p
}

function Get-CanonicalLogRoot([string]$RepoRoot,[string]$Market){
  $m = ([string]$Market).ToUpperInvariant().Trim()
  if(-not $m){ $m = "US" }
  $repoFull = (Resolve-Path -LiteralPath $RepoRoot -ErrorAction Stop).Path
  if(-not (Test-Path -LiteralPath (Join-Path $repoFull ".git"))){
    throw "[FAIL-CLOSED] repo root missing .git: $repoFull"
  }
  $logRoot = Join-Path (Join-Path $repoFull "logs") $m
  if($logRoot -notlike ($repoFull + "*")){
    throw "[FAIL-CLOSED] logRoot escaped repo: logRoot=$logRoot repo=$repoFull"
  }
  New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
  return $logRoot
}

chcp 65001 | Out-Null

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n","`n"
  if($Text.Length -gt 0 -and $Text[-1] -ne "`n"){ $Text += "`n" }
  [System.IO.File]::WriteAllText($Path, $Text, $utf8)
}

function Resolve-RepoRoot(){
  $toolsDir = Split-Path -Parent $PSCommandPath
  $rr = Split-Path -Parent $toolsDir
  try { return (Resolve-Path -LiteralPath $rr -ErrorAction Stop).Path } catch { return $rr }
}
$repoRoot = Resolve-RepoRoot

# Prefer RunContext logs_dir_out (per-market). Fall back to legacy root logs.
# A2: FORCE per-market output dir (do not write root logs for per-market status)
$logsDir = Join-Path $repoRoot ("logs\" + $Market)
if(-not (Test-Path -LiteralPath $logsDir)){
  New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
}
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$rr = Get-CanonicalRepoRoot
$rcRaw = & (Join-Path $rr "tools\Resolve-RunContext.ps1") -Market $Market -Symbol $Symbol | Out-String
$rcRaw = ($rcRaw + "").Trim()
# Parse RunContext JSON safely (slice braces) — fail-closed: if parse fails, keep defaults
if($rcRaw){
  try {
    $ix0 = $rcRaw.IndexOf("{"); $ix1 = $rcRaw.LastIndexOf("}")
    if($ix0 -ge 0 -and $ix1 -gt $ix0){
      $rc = ($rcRaw.Substring($ix0, ($ix1-$ix0+1))) | ConvertFrom-Json
    }
    if($rc -and ($rc.PSObject.Properties.Name -contains "logs_dir") -and $rc.logs_dir){ $logsDir = [string]$rc.logs_dir }
    if($rc -and ($rc.PSObject.Properties.Name -contains "as_of_date") -and $rc.as_of_date){ $todayLocal = [string]$rc.as_of_date }
  } catch { }
}
# [A2] DO NOT reset logsDir to root logs (per-market only)
if($rcRaw){
  try {
    $rc = $rcRaw | ConvertFrom-Json
    if($rc -and ($rc.PSObject.Properties.Name -contains "logs_dir") -and $rc.logs_dir){
      $logsDir = [string]$rc.logs_dir
    }
    if($rc -and ($rc.PSObject.Properties.Name -contains "as_of_date") -and $rc.as_of_date){
      $todayLocal = [string]$rc.as_of_date
    }
  } catch { }
}

if(-not $todayLocal){ $todayLocal = (Get-Date).ToString("yyyy-MM-dd") }
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
$ok = $false
$asOf = ""
$evidence = @()

foreach($cand in @(
  (Join-Path $logsDir "phase4_validation_passed.json"),
  (Join-Path (Join-Path $repoRoot "logs") "phase4_validation_passed.json")
)){
  $p = $cand
  if(Test-Path -LiteralPath $p){ break }
}
if(Test-Path -LiteralPath $p){
  $evidence += $p
  try {
    $j = Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
    if($j){
      if($j.PSObject.Properties.Name -contains "as_of_date"){ $asOf = [string]$j.as_of_date }
      if($j.PSObject.Properties.Name -contains "phase4_ok_today"){ $ok = [bool]$j.phase4_ok_today }
      elseif($j.PSObject.Properties.Name -contains "ok_today"){ $ok = [bool]$j.ok_today }
      elseif($j.PSObject.Properties.Name -contains "passed"){ $ok = [bool]$j.passed }
    }
  } catch { }
}

if(-not $asOf){ $asOf = $todayLocal }
# Enforce today-ness conservatively
$okToday = ($ok -and ($asOf.Substring(0,[Math]::Min(10,$asOf.Length)) -eq $todayLocal))

$out = [ordered]@{
  kind="phase4_status"
  as_of_date=$todayLocal
  evidence_as_of_date=$asOf
  ok_today=[bool]$okToday
  evidence_paths=$evidence
  ts_utc=(Get-Date).ToUniversalTime().ToString("o")
}

Write-Utf8NoBomLf (Join-Path $logsDir "phase4_status.json") (($out | ConvertTo-Json -Depth 6))
Write-Host "[A2] wrote logs\phase4_status.json" -ForegroundColor Green
exit 0
