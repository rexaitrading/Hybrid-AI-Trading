param(
  [string]$Cfg="config\paper_runner.yaml",
  [string]$Universe="AAPL,MSFT,NVDA",
  [int]$Mdt=1,
  [switch]$PreferProviders
)
$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "$PWD\src;$env:PYTHONPATH"
$Py = ".\.venv\Scripts\python.exe"

# Build arg list safely
$args = @(
  "src\hybrid_ai_trading\runners\runner_paper.py",
  "--config", $Cfg,
  "--universe", $Universe,
  "--mdt", [string]$Mdt,
  "--provider-only"
)
if ($PreferProviders) { $args += "--prefer-providers" }

& $Py $args
