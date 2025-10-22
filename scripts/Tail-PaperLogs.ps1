param([string]$LogFile = "logs/runner_paper.jsonl", [int]$Lines = 120)
if (-not (Test-Path $LogFile)) { "No log at $LogFile"; exit 0 }
Get-Content -LiteralPath $LogFile -Tail $Lines |
  Select-String '"risk_checks"|"risk_enforced_denied"|"decision_snapshot"|"once_done"|"loop_stop"'
