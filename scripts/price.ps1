param([Parameter(Mandatory=$true)][string]$Symbol)

$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "$PWD\src;$env:PYTHONPATH"

$code = @"
from hybrid_ai_trading.utils.providers import load_providers, get_price
cfg = load_providers("config/providers.yaml")
print(get_price("$Symbol", cfg))
"@

$tmp = Join-Path $env:TEMP ("price_{0}.py" -f ([guid]::NewGuid().ToString("N")))
[IO.File]::WriteAllText($tmp, $code, (New-Object System.Text.UTF8Encoding($false)))

& .\.venv\Scripts\python.exe $tmp
Remove-Item $tmp -ErrorAction SilentlyContinue
