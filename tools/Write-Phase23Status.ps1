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
$evidence=@()

$p = Join-Path $logsDir "phase23_health.csv"
if(Test-Path -LiteralPath $p){
  $evidence += $p
  try{
    $rows = @(Import-Csv -LiteralPath $p)
    foreach($r in $rows){
      $d = ""
      if($r.PSObject.Properties.Name -contains "as_of_date"){ $d = [string]$r.as_of_date }
      elseif($r.PSObject.Properties.Name -contains "date"){ $d = [string]$r.date }
      if($d){ $d = $d.Substring(0,[Math]::Min(10,$d.Length)) }
      if($d -eq $todayLocal){
        $asOf = $d
        if($r.PSObject.Properties.Name -contains "phase23_ok"){ $okToday = ([string]$r.phase23_ok).ToLower() -in @("1","true","yes") }
        elseif($r.PSObject.Properties.Name -contains "phase23_health_ok_today"){ $okToday = ([string]$r.phase23_health_ok_today).ToLower() -in @("1","true","yes") }
        break
      }
    }
  } catch { $okToday = $false }
}

$out = [ordered]@{
  kind="phase23_status"
  as_of_date=$asOf
  ok_today=[bool]$okToday
  evidence_paths=$evidence
  ts_utc=(Get-Date).ToUniversalTime().ToString("o")
}

Write-Utf8NoBomLf (Join-Path $logsDir "phase23_status.json") (($out | ConvertTo-Json -Depth 6))
Write-Host "[A2] wrote logs\phase23_status.json" -ForegroundColor Green
exit 0
