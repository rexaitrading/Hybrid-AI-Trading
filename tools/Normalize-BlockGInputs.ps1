[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"
if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir | Out-Null }

function Normalize-CsvToDateOkReason {
  param([Parameter(Mandatory=$true)][string]$Path)

  $header = "date,ok,reason"
  if (-not (Test-Path $Path)) {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $header + "`r`n", $utf8NoBom)
    return
  }

  $lines = @(Get-Content $Path -Encoding utf8)
  if ($lines.Count -eq 0) { $lines = @($header) }

  # Collect rows into map(date -> row)
  $map = @{}  # date -> "date,ok,reason"
  foreach ($ln in $lines) {
    if ([string]::IsNullOrWhiteSpace($ln)) { continue }

    # Skip any header-ish lines
    $t = $ln.Trim()
    if ($t -match '^(date,|\"date\")') {
      continue
    }

    # Remove quotes
    $t = $t -replace '"',''
    $parts = $t.Split(",")
    if ($parts.Count -lt 2) { continue }

    $d = ($parts[0] + "").Trim()
    if ($d.Length -ge 10) { $d = $d.Substring(0,10) }
    if ($d -notmatch '^\d{4}-\d{2}-\d{2}$') { continue }

    # Heuristics: if legacy has (date,True) treat as ok=true
    $ok = ($parts[1] + "").Trim().ToLowerInvariant()
    if ($ok -in @("true","1","yes","y")) { $ok = "true" }
    elseif ($ok -in @("false","0","no","n")) { $ok = "false" }
    else { $ok = "false" }

    $reason = "normalized"
    if ($parts.Count -ge 3) {
      $reason = ($parts[2] + "").Trim()
      if ([string]::IsNullOrWhiteSpace($reason)) { $reason = "normalized" }
    }

    $map[$d] = ("{0},{1},{2}" -f $d,$ok,$reason)
  }

  $out = @($header) + ($map.Keys | Sort-Object | ForEach-Object { $map[$_] })
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($out -join "`r`n") + "`r`n", $utf8NoBom)
}

Normalize-CsvToDateOkReason -Path (Join-Path $logsDir "phase23_health_daily.csv")
Normalize-CsvToDateOkReason -Path (Join-Path $logsDir "phase5_ev_hard_veto_daily.csv")

Write-Host "[NORMALIZE] Block-G inputs normalized (date,ok,reason)." -ForegroundColor Green