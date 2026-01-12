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
$ok = $false
$asOf = ""
$evidence = @()

$p = Join-Path $logsDir "phase4_validation_passed.json"
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
