[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$tools = Split-Path -Parent $PSCommandPath
$repo  = Split-Path -Parent $tools

$liveRoots = @(
  (Join-Path $repo "src\hybrid_ai_trading\execution"),
  (Join-Path $repo "src\hybrid_ai_trading\broker"),
  (Join-Path $repo "src\hybrid_ai_trading\runners")
)

# Enumerate concrete files (no globs) for deterministic auditing
$liveFiles = New-Object System.Collections.Generic.List[string]
foreach($root in $liveRoots){
  if(Test-Path -LiteralPath $root){
    foreach($fi in (Get-ChildItem -LiteralPath $root -Recurse -File -Filter "*.py" -ErrorAction SilentlyContinue)){
      $liveFiles.Add($fi.FullName) | Out-Null
    }
  }
}

if($liveFiles.Count -eq 0){
  Write-Host "[AUDIT] ERROR: no live .py files found under execution/broker/runners" -ForegroundColor Yellow
  exit 1
}

$live = @($liveFiles.ToArray())


$pat = 'events_real\.jsonl|gatescore_events_real\.jsonl'
$m = @(Select-String -Path $live -Pattern $pat -ErrorAction SilentlyContinue)

if($m.Count -gt 0){
  Write-Host "[AUDIT] FAIL: live modules reference *_events_real.jsonl (research-only; fail-closed)" -ForegroundColor Red
  $m | Select-Object Path,LineNumber,Line | Format-Table -AutoSize | Out-Host
  exit 2
}

Write-Host "[AUDIT] OK: no live module references *_events_real.jsonl" -ForegroundColor Green
exit 0
