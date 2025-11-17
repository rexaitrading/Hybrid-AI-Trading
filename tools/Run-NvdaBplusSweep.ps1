param(
    [string] $JsonlPath = 'research\nvda_bplus_replay_trades.jsonl',
    [double] $Start     = -0.10,
    [double] $Stop      = 0.20,
    [double] $Step      = 0.02,
    [int]    $Limit     = 0
)

$ErrorActionPreference = 'Stop'

$repoRoot = 'C:\Users\rhcy9\OneDrive\文件\HybridAITrading'
Set-Location $repoRoot

$env:PYTHONPATH = "$repoRoot;$repoRoot\src"

.\.venv\Scripts\activate.ps1

$py = '.\.venv\Scripts\python.exe'

& $py -m tools.nvda_bplus_threshold_sweep `
    --jsonl $JsonlPath `
    --limit $Limit `
    --start $Start `
    --stop $Stop `
    --step $Step