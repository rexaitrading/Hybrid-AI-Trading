[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","CN_SH","CN_SZ")] [string]$Market="US",
  [ValidateSet("NVDA","SPY","QQQ")] [string]$Symbol="NVDA"
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

$repoRoot = (Resolve-Path ".").Path

# Prefer RunContext logs_dir_out (per-market). Fall back to legacy root logs.
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$rcRaw = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Resolve-RunContext.ps1") -Market $Market -Symbol $Symbol | Out-String
$rcRaw = ($rcRaw + "").Trim()
$logsDir = Join-Path $repoRoot "logs"
if($rcRaw){
  try {
    $rc = $rcRaw | ConvertFrom-Json
    if($rc -and ($rc.PSObject.Properties.Name -contains "logs_dir_out") -and $rc.logs_dir_out){
      $logsDir = [string]$rc.logs_dir_out
    }
    if($rc -and ($rc.PSObject.Properties.Name -contains "as_of_date") -and $rc.as_of_date){
      $todayLocal = [string]$rc.as_of_date
    }
  } catch { }
}

New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
$todayLocal = (Get-Date).ToString("yyyy-MM-dd")
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
  as_of_date=$asOf
  ok_today=[bool]$okToday
  evidence_paths=$evidence
  ts_utc=(Get-Date).ToUniversalTime().ToString("o")
}

Write-Utf8NoBomLf (Join-Path $logsDir "phase4_status.json") (($out | ConvertTo-Json -Depth 6))
Write-Host "[A2] wrote logs\phase4_status.json" -ForegroundColor Green
exit 0
