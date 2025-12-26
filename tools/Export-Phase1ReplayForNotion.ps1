[CmdletBinding()]
param(
  [string]$OutCsv = ".\logs\notion\phase1_replay_for_notion.csv"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

function Get-Prop([object]$Obj, [string]$Name, $Default){
  if($null -eq $Obj){ return $Default }
  $p = $Obj.PSObject.Properties.Match($Name)
  if($p -and $p.Count -gt 0){ return $p[0].Value }
  return $Default
}

$root = (Resolve-Path ".").Path
$logs = Join-Path $root "logs"
$notionDir = Join-Path $logs "notion"
New-Item -ItemType Directory -Force -Path $notionDir | Out-Null

# Latest Phase-1 hashes CSV (from Run-Phase1ReplayDeterministic)
$hashCsv = Get-ChildItem (Join-Path $logs "phase1_artifacts") -File -Filter "phase1_hashes_*.csv" -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime | Select-Object -Last 1

# Latest run_journal CSV
$runCsv = Get-ChildItem (Join-Path $logs "run_journal") -File -Filter "run_journal_*.csv" -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime | Select-Object -Last 1

# Replay summaries live in repo root today
$sum = Get-ChildItem $root -File -Filter "replay_summary_*.json" -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime

if(-not $sum){ throw "No replay_summary_*.json found in repo root. Run tools\Run-Phase1ReplaySuite.ps1 first." }

$rows = foreach($f in $sum){
  $raw = Get-Content -LiteralPath $f.FullName -Raw -Encoding utf8
  $j = $null
  try { $j = $raw | ConvertFrom-Json } catch { $j = $null }

  $sym = Get-Prop $j "symbol" ""
  if(-not $sym){
    # replay_summary_<SYM>_... fallback
    $parts = $f.BaseName -split "_"
    if($parts.Length -ge 3){ $sym = $parts[2] } else { $sym = "" }
  }

  $asOf = Get-Prop $j "as_of_date" ""
  if(-not $asOf){ $asOf = (Get-Date $f.LastWriteTime).ToString("yyyy-MM-dd") }

  $session = Get-Prop $j "session" ""
  $ok = Get-Prop $j "ok" $true

  [PSCustomObject]@{
    phase = "PHASE1"
    as_of_date = [string]$asOf
    symbol = [string]$sym
    session = [string]$session
    replay_ok = [bool]$ok
    replay_summary_file = $f.Name
    hashes_csv = if($hashCsv){ $hashCsv.Name } else { "" }
    run_journal_csv = if($runCsv){ $runCsv.Name } else { "" }
    notes = ""
  }
}

$OutCsv = (Resolve-Path (Split-Path $OutCsv -Parent)).Path + "\" + (Split-Path $OutCsv -Leaf)
$rows | Export-Csv -NoTypeInformation -Encoding utf8 -LiteralPath $OutCsv -Force

Write-Host "WROTE=$OutCsv" -ForegroundColor Green
if($hashCsv){ Write-Host "HASHES=$($hashCsv.FullName)" -ForegroundColor DarkGreen }
if($runCsv){ Write-Host "RUN_JOURNAL=$($runCsv.FullName)" -ForegroundColor DarkGreen }
exit 0