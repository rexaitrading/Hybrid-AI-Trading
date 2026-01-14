[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","CN_SH","CN_SZ")]
  [string]$Market = "US"
)

Set-StrictMode -Version Latest
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

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"

# Single truth date
$rc = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Resolve-RunContext.ps1") -Market $Market -Symbol NVDA | ConvertFrom-Json
$todayLocal = Slice-Date ([string]$rc.as_of_date)

$logsDir = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1") -Market $Market
if(-not $logsDir){ $logsDir = Join-Path $repoRoot "logs" }
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
$outDir = $logsDir
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$outPath = Join-Path $outDir "ev_hard_status.json"
$oneTap  = Join-Path $logsDir "onetap_summary.json"

# Snapshot-first (A2 truth): prefer per-market veto snapshot or evidence snapshot; fallback to onetap_summary only if missing/stale.
$snapVeto = Join-Path $logsDir "phase5_ev_hard_veto_snapshot.json"
$snapEv   = Join-Path $logsDir "ev_hard_snapshot.json"

# Fail-closed defaults (already set above): $ok=$false, $reason=..., $src_asof=""
try {
  if(Test-Path -LiteralPath $snapVeto){
    $sj = Get-Content -LiteralPath $snapVeto -Raw -Encoding UTF8 | ConvertFrom-Json
    $sa = ""
    if($sj.PSObject.Properties.Name -contains "as_of_date"){ $sa = Slice-Date ([string]$sj.as_of_date) }
    if($sa -eq $todayLocal){
      if($sj.PSObject.Properties.Name -contains "ok_today"){ $ok = [bool]$sj.ok_today }
      elseif($sj.PSObject.Properties.Name -contains "ok"){ $ok = [bool]$sj.ok }
      $src_asof = $sa
      $reason = "from_veto_snapshot"
    }
  } elseif(Test-Path -LiteralPath $snapEv){
    $ej = Get-Content -LiteralPath $snapEv -Raw -Encoding UTF8 | ConvertFrom-Json
    $ea = ""
    if($ej.PSObject.Properties.Name -contains "as_of_date"){ $ea = Slice-Date ([string]$ej.as_of_date) }
    if($ea -eq $todayLocal){
      if($ej.PSObject.Properties.Name -contains "ok_today"){ $ok = [bool]$ej.ok_today }
      elseif($ej.PSObject.Properties.Name -contains "ok"){ $ok = [bool]$ej.ok }
      $src_asof = $ea
      $reason = "from_evidence_snapshot"
    }
  }
} catch {
  # keep fail-closed defaults; allow onetap fallback below
}

# Fail-closed defaults
$ok = $false
$reason = "missing_onetap_summary"
$src_asof = ""

if(Test-Path -LiteralPath $oneTap){
  try {
    $j = Get-Content -LiteralPath $oneTap -Raw -Encoding UTF8 | ConvertFrom-Json
    if($j.PSObject.Properties.Name -contains "as_of_date"){ $src_asof = Slice-Date ([string]$j.as_of_date) }
    if($j.PSObject.Properties.Name -contains "ev_hard_daily_ok_today"){
      $candidate = [bool]$j.ev_hard_daily_ok_today
      if($src_asof -eq $todayLocal){
        $ok = $candidate
        $reason = "from_onetap_summary"
      } else {
        $ok = $false
        $reason = "onetap_stale_as_of_date"
      }
    } else {
      $ok = $false
      $reason = "onetap_missing_ev_hard_key"
    }
  } catch {
    $ok = $false
    $reason = "onetap_parse_failed"
  }
}

$obj = [ordered]@{
  ts_utc   = (Get-Date).ToUniversalTime().ToString("o")
  market   = $Market
  as_of_date = $todayLocal
  ok_today = [bool]$ok
  reason   = $reason
  evidence_path = $oneTap
  evidence_as_of_date = $src_asof
}

Write-Utf8NoBomLf $outPath ($obj | ConvertTo-Json -Depth 6)
Write-Host ("[EV-HARD] wrote " + $outPath + " ok_today=" + $ok + " reason=" + $reason + " as_of=" + $todayLocal) -ForegroundColor Cyan
