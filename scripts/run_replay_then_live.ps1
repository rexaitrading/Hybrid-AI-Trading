Param(
  [string]$Symbol   = "AAPL",
  [string]$Date     = (Get-Date).AddDays(-1).ToString("yyyy-MM-dd"),
  [string]$Interval = "1m",
  [string]$Strategy = "orb",
  [int]   $LiveMinutes = 45
)

$ErrorActionPreference='Stop'
Set-Location (git rev-parse --show-toplevel)
[Environment]::CurrentDirectory = (Get-Location).Path

# 0) hygiene
pre-commit run --all-files

# 1) REPLAY  export trades JSON
$replayOut = ".artifacts/journal/replay/$($Symbol)_$($Date).json"
New-Item -ItemType Directory -Force (Split-Path $replayOut) | Out-Null
python -m hybrid_ai_trading.tools.bar_replay `
  --symbol $Symbol --date $Date --interval $Interval --strategy $Strategy `
  --log_trades true --journal_out $replayOut

# 2) REPLAY  Notion
python -m hybrid_ai_trading.tools.replay_logger_hook `
  --input $replayOut --to_notion true --notion_db Trades --tag "replay:$Strategy"

# 3) LIVE (paper)  export trades JSON
$liveOut = ".artifacts/journal/live/$($Symbol)_$($Date)_live.json"
New-Item -ItemType Directory -Force (Split-Path $liveOut) | Out-Null
python -m hybrid_ai_trading.runners.runner_paper `
  --symbols $Symbol --strategy $Strategy --minutes $LiveMinutes `
  --journal_out $liveOut

# 4) LIVE  Notion
python -m hybrid_ai_trading.tools.replay_logger_hook `
  --input $liveOut --to_notion true --notion_db Trades --tag "live:$Strategy"

Write-Host "ReplayLive complete for $Symbol ($Strategy). Logs at: $replayOut ; $liveOut" -ForegroundColor Green
