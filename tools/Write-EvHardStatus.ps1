[CmdletBinding()]
param()

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
$logsDir  = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$todayLocal = (Get-Date).ToString("yyyy-MM-dd")
$okToday = $false
$asOf = $todayLocal
$reason = ""
$evidence=@()

$p = Join-Path $logsDir "phase5_ev_hard_veto_evidence.json"
if(Test-Path -LiteralPath $p){
  $evidence += $p
  try{
    $j = Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
    if($j){
      if($j.PSObject.Properties.Name -contains "as_of_date"){ $asOf = [string]$j.as_of_date }
      if($asOf){ $asOf = $asOf.Substring(0,[Math]::Min(10,$asOf.Length)) }
      if($j.PSObject.Properties.Name -contains "ev_hard_daily_ok_today"){ $okToday = [bool]$j.ev_hard_daily_ok_today }
      elseif($j.PSObject.Properties.Name -contains "ok_today"){ $okToday = [bool]$j.ok_today }
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
