[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market="US",
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol="NVDA"
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

# Prefer RunContext logs_dir (per-market). Fall back to legacy root logs.
# A2: FORCE per-market output dir (do not write root logs for per-market status)
$logsDir = Join-Path $repoRoot ("logs\" + $Market)
if(-not (Test-Path -LiteralPath $logsDir)){
  New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
}
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$rr = Get-CanonicalRepoRoot
$rcRaw = & (Join-Path $rr "tools\Resolve-RunContext.ps1") -Market $Market -Symbol $Symbol | Out-String
$rcRaw = ($rcRaw + "").Trim()

$logsDir = Join-Path $repoRoot "logs"
$todayLocal = $null

if($rcRaw){
  try{
    $rc = $rcRaw | ConvertFrom-Json
    if($rc){
      if(($rc.PSObject.Properties.Name -contains "logs_dir") -and $rc.logs_dir){
        $logsDir = [string]$rc.logs_dir
      } elseif(($rc.PSObject.Properties.Name -contains "logs_dir_out") -and $rc.logs_dir_out){
        $logsDir = [string]$rc.logs_dir_out
      }
      if(($rc.PSObject.Properties.Name -contains "as_of_date") -and $rc.as_of_date){
        $todayLocal = [string]$rc.as_of_date
      }
    }
  } catch { }
}

if(-not $todayLocal){ $todayLocal = (Get-Date).ToString("yyyy-MM-dd") }

New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$okToday = $false
$asOf = $todayLocal
$reason = ""
$evidence=@()

# Evidence candidates (per-market first, then root logs)
$cands = @(
  (Join-Path $logsDir "phase5_ev_hard_veto_evidence.json"),
  (Join-Path $logsDir "ev_hard_evidence.json"),
  (Join-Path $logsDir "ev_hard_snapshot.json"),
  (Join-Path (Join-Path $repoRoot "logs") "phase5_ev_hard_veto_evidence.json"),
  (Join-Path (Join-Path $repoRoot "logs") "ev_hard_evidence.json"),
  (Join-Path (Join-Path $repoRoot "logs") "ev_hard_snapshot.json")
)

$p = $null
foreach($cand in $cands){
  if(Test-Path -LiteralPath $cand){ $p = $cand; break }
}

if($p){
  $evidence += $p
  try{
    $j = Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
    if($j){
      if($j.PSObject.Properties.Name -contains "as_of_date"){ $asOf = [string]$j.as_of_date }
      if($asOf){ $asOf = $asOf.Substring(0,[Math]::Min(10,$asOf.Length)) }
      if($j.PSObject.Properties.Name -contains "ev_hard_daily_ok_today"){ $okToday = [bool]$j.ev_hard_daily_ok_today }
      elseif($j.PSObject.Properties.Name -contains "ok_today"){ $okToday = [bool]$j.ok_today }
elseif($j.PSObject.Properties.Name -contains "ok"){ $okToday = [bool]$j.ok }
      if($j.PSObject.Properties.Name -contains "reason"){ $reason = [string]$j.reason }
    }
  } catch { $okToday = $false }
}

# conservative today-ness
if($asOf -ne $todayLocal){ $okToday = $false }

$out = [ordered]@{
  kind="ev_hard_status"
  as_of_date=$asOf
  ok_today=[bool]$okToday
  reason=$reason
  evidence_paths=$evidence
  ts_utc=(Get-Date).ToUniversalTime().ToString("o")
}

# A2_EV_HARD_OK_TODAY_GUARD_BEGIN
# Contract: ok_today must ONLY be true when as_of_date == market-aware todayLocal (RunContext).
try{
  function _Slice10([string]$d){
    $s = ([string]$d).Trim()
    if($s.Length -ge 10){ return $s.Substring(0,10) }
    return $s
  }

  # Determine Market/Symbol for RunContext (fail-closed fallback).
  $m = $null; $s = $null
  try { if(Get-Variable -Name "Market" -Scope Local -ErrorAction SilentlyContinue){ $m = ($Market + "") } } catch { }
  try { if(Get-Variable -Name "Symbol" -Scope Local -ErrorAction SilentlyContinue){ $s = ($Symbol + "") } } catch { }
  if(-not $m){ $m = (($env:HAT_MARKET + "")).Trim() }
  if(-not $s){ $s = (($env:HAT_SYMBOL + "")).Trim(); if(-not $s){ $s = "NVDA" } }

  $todayLocal = (Get-Date).ToString("yyyy-MM-dd")
  try{
    $rcPath = Join-Path $repoRoot "tools\Resolve-RunContext.ps1"
    if(Test-Path -LiteralPath $rcPath){
      $raw = (& $rcPath -Market $m -Symbol $s | Out-String).Trim()
      $i0 = $raw.IndexOf("{"); $i1 = $raw.LastIndexOf("}")
      if($i0 -ge 0 -and $i1 -gt $i0){
        $rc = ($raw.Substring($i0, ($i1-$i0+1))) | ConvertFrom-Json
        if($rc -and $rc.as_of_date){ $todayLocal = _Slice10 ([string]$rc.as_of_date) }
      }
    }
  } catch { }

  # Enforce todayness on whichever object is being written (common variable names).
  $candidates = @("payload","out","outObj","status","statusObj","j","o","res","result")
  foreach($nm in $candidates){
    $vv = Get-Variable -Name $nm -Scope Local -ErrorAction SilentlyContinue
    if(-not $vv){ continue }
    $obj = $vv.Value
    if($null -eq $obj){ continue }

    # Hashtable / dictionary
    if(($obj -is [hashtable]) -or ($obj -is [System.Collections.IDictionary])){
      if($obj.Contains("as_of_date") -and $obj.Contains("ok_today")){
        $a = ""; try { $a = _Slice10 ([string]$obj["as_of_date"]) } catch { $a="" }
        if((-not $a) -or ($a -ne $todayLocal)){ $obj["ok_today"] = $false }
      }
      continue
    }

    # PSCustomObject
    try{
      $p = $obj.PSObject.Properties.Name
      if(($p -contains "as_of_date") -and ($p -contains "ok_today")){
        $a = ""; try { $a = _Slice10 ([string]$obj.as_of_date) } catch { $a="" }
        if((-not $a) -or ($a -ne $todayLocal)){ $obj.ok_today = $false }
      }
    } catch { }
  }
} catch { }
# A2_EV_HARD_OK_TODAY_GUARD_END

Write-Utf8NoBomLf (Join-Path $logsDir "ev_hard_status.json") (($out | ConvertTo-Json -Depth 6))
Write-Host "[A2] wrote logs\ev_hard_status.json" -ForegroundColor Green
exit 0
