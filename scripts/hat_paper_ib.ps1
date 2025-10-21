param(
  [string]$Cfg="config\paper_runner.yaml",
  [string]$Universe="AAPL,MSFT,NVDA",
  [int]$Mdt=1
)
$ErrorActionPreference="Stop"
$env:PYTHONPATH = "$PWD\src;$env:PYTHONPATH"

if (-not $env:IB_HOST)      { $env:IB_HOST = "127.0.0.1" }
if (-not $env:IB_PORT)      { $env:IB_PORT = "7497" }
if (-not $env:IB_CLIENT_ID) { $env:IB_CLIENT_ID = "3021" }

$Py = ".\.venv\Scripts\python.exe"
$args = @(
  "src\hybrid_ai_trading\runners\runner_paper.py",
  "--config", $Cfg,
  "--universe", $Universe,
  "--mdt", [string]$Mdt
)
& $Py $args