[CmdletBinding()]
param(
  [string]$OutPath = ".\logs\phase2_micro_cost_snapshot.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$repoRoot = (Resolve-Path ".").Path
$logsDir = Join-Path $repoRoot "logs"
$today = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")

function Pick-File([string]$todayPath, [string]$basePath){
  if(Test-Path $todayPath){ return $todayPath }
  if(Test-Path $basePath){ return $basePath }
  return $null
}

$spy = Pick-File (Join-Path $logsDir "spy_phase5_paperlive_results_with_micro_today.jsonl") (Join-Path $logsDir "spy_phase5_paperlive_results_with_micro.jsonl")
$qqq = Pick-File (Join-Path $logsDir "qqq_phase5_paperlive_results_with_micro_today.jsonl") (Join-Path $logsDir "qqq_phase5_paperlive_results_with_micro.jsonl")

function Summarize([string]$path){
  if(-not $path){ return @{ path=$null; rows=0; micro_avg=0.0 } }
  $rows=0; $sum=0.0; $n=0
  foreach($line in Get-Content -LiteralPath $path -Encoding utf8){
    if([string]::IsNullOrWhiteSpace($line)){ continue }
    $rows++
    try {
      $j = $line | ConvertFrom-Json
      # try common fields
      $v = $null
      if($j.PSObject.Properties.Name -contains "micro_score"){ $v = $j.micro_score }
      elseif($j.PSObject.Properties.Name -contains "mean_micro_score"){ $v = $j.mean_micro_score }
      elseif($j.PSObject.Properties.Name -contains "micro"){ $v = $j.micro }
      if($null -ne $v){
        $d=0.0
        if([double]::TryParse(($v+""), [ref]$d)){
          $sum += $d; $n++
        }
      }
    } catch { }
  }
  $avg = if($n -gt 0){ $sum / $n } else { 0.0 }
  return @{ path=$path; rows=$rows; micro_avg=[Math]::Round($avg,6) }
}

$spyS = Summarize $spy
$qqqS = Summarize $qqq

$ok = (($spyS.rows + $qqqS.rows) -gt 0)
$reason = if($ok){"phase2_micro_snapshot_ok"}else{"phase2_inputs_missing"}

$out = [ordered]@{
  ts_utc = $tsUtc
  as_of_date = $today
  ok = $ok
  reason = $reason
  inputs = @{
    spy = $spyS
    qqq = $qqqS
  }
  version = "phase2.1"
} | ConvertTo-Json -Depth 8

$enc = New-Object System.Text.UTF8Encoding($false)
$full = Join-Path $repoRoot $OutPath
[System.IO.File]::WriteAllText($full, ($out -replace "`r`n","`n") + "`n", $enc)

Write-Host "[PHASE2] wrote $full ok=$ok reason=$reason" -ForegroundColor Green
exit (0)
