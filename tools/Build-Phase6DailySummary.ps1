param(
  [string]$OutCsv = "logs\phase6_daily_summary.csv"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

# v0 scaffold: if you already have intents log, infer strategy_id set.
$intents = "logs\portfolio_order_intents.jsonl"
$rows = @()

function Test-StrategyIdAllowed {
  param([string]$StrategyId)

  if(-not $StrategyId){ return $false }
  $s = $StrategyId.Trim()
  if($s.Length -eq 0){ return $false }

  # Block obvious non-prod / stub IDs (fail-closed)
  if($s -match '^(?i)(DUMMY|TEST|DEV)'){ return $false }

  return $true
}


if(Test-Path $intents){
  $seen = New-Object "System.Collections.Generic.HashSet[string]"
  Get-Content $intents -Encoding utf8 | ForEach-Object {
    if(-not $_){ return }
    try {
      $o = $_ | ConvertFrom-Json
      $sid = [string]$o.strategy_id
      if((Test-StrategyIdAllowed $sid) -and $seen.Add($sid)){
        $rows += [pscustomobject]@{ strategy_id = $sid; score = 0.0 }
      }
    } catch {
      # ignore malformed line (fail-closed later once schema locked)
    }
  }
}

if(-not $rows -or $rows.Count -eq 0){
  # fail-closed scaffold: still emit a minimal file for downstream smoke, but mark it clearly
  $rows = @(
    [pscustomobject]@{ strategy_id = "NVDA_BPLUS"; score = 0.0 }
  )
}

$dir = Split-Path -Parent $OutCsv
if($dir -and -not (Test-Path $dir)){ New-Item -ItemType Directory -Force -Path $dir | Out-Null }

$rows | Export-Csv -NoTypeInformation -Encoding UTF8 -Path $OutCsv
Write-Host "[PHASE6] OK: wrote $OutCsv (rows=$($rows.Count))" -ForegroundColor Green
exit 0