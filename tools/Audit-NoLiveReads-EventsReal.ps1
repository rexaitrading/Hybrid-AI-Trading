[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$tools = Split-Path -Parent $PSCommandPath
$repo  = Split-Path -Parent $tools

$live = @(
  Join-Path $repo "src\hybrid_ai_trading\execution\**\*.py",
  Join-Path $repo "src\hybrid_ai_trading\broker\**\*.py",
  Join-Path $repo "src\hybrid_ai_trading\runners\**\*.py"
)

$pat = 'events_real\.jsonl|gatescore_events_real\.jsonl'
$m = @(Select-String -Path $live -Pattern $pat -ErrorAction SilentlyContinue)

if($m.Count -gt 0){
  Write-Host "[AUDIT] FAIL: live modules reference *_events_real.jsonl (research-only; fail-closed)" -ForegroundColor Red
  $m | Select-Object Path,LineNumber,Line | Format-Table -AutoSize | Out-Host
  exit 2
}

Write-Host "[AUDIT] OK: no live module references *_events_real.jsonl" -ForegroundColor Green
exit 0
