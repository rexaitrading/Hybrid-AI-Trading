[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market="US",
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol="NVDA"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
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
$rcRaw = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Resolve-RunContext.ps1") -Market $Market -Symbol $Symbol | Out-String
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

Write-Utf8NoBomLf (Join-Path $logsDir "ev_hard_status.json") (($out | ConvertTo-Json -Depth 6))
Write-Host "[A2] wrote logs\ev_hard_status.json" -ForegroundColor Green
exit 0
