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

$outPath = Join-Path $logsDir "phase23_status.json"
$oneTap  = Join-Path $logsDir "onetap_summary.json"

# Fail-closed defaults
$ok = $false
$reason = "missing_onetap_summary"
$src_asof = ""

if(Test-Path -LiteralPath $oneTap){
  try {
    $j = Get-Content -LiteralPath $oneTap -Raw -Encoding UTF8 | ConvertFrom-Json
    if($j.PSObject.Properties.Name -contains "as_of_date"){ $src_asof = Slice-Date ([string]$j.as_of_date) }
    if($j.PSObject.Properties.Name -contains "phase23_health_ok_today"){
      $candidate = [bool]$j.phase23_health_ok_today
      if($src_asof -eq $todayLocal){
        $ok = $candidate
        $reason = "from_onetap_summary"
      } else {
        $ok = $false
        $reason = "onetap_stale_as_of_date"
      }
    } else {
      $ok = $false
      $reason = "onetap_missing_phase23_key"
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
Write-Host ("[PHASE23] wrote " + $outPath + " ok_today=" + $ok + " reason=" + $reason + " as_of=" + $todayLocal) -ForegroundColor Cyan
