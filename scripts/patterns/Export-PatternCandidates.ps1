$ErrorActionPreference = 'Stop'
Set-Location C:\Dev\HybridAITrading
if (-not (Test-Path '.\.venv\Scripts\python.exe')) { throw '.venv python not found at .\.venv\Scripts\python.exe' }
$env:HAT_REPLAY_LOG   = $env:HAT_REPLAY_LOG   ?? 'data\replay_log.ndjson'
$env:HAT_PATTERNS_DIR = $env:HAT_PATTERNS_DIR ?? 'data\patterns'
& .\.venv\Scripts\python.exe .\src\hybrid_ai_trading\patterns\pattern_memory.py
