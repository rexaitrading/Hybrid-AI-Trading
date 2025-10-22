param(
  [Parameter(Mandatory=$true, ValueFromRemainingArguments=$true)]
  [string[]]$Symbols
)
$ErrorActionPreference='Stop'
$env:PYTHONPATH = "$PWD\src;$env:PYTHONPATH"

# Build Python list literal safely
$syms = ($Symbols | ForEach-Object { '"' + ($_ -replace '"','\"') + '"' }) -join ","

$py = @"
from hybrid_ai_trading.utils.providers import load_providers, get_prices
cfg = load_providers("config/providers.yaml")
print(get_prices([$syms], cfg))
"@

$tmp = Join-Path $env:TEMP ("snapshot_{0}.py" -f ([guid]::NewGuid().ToString("N")))
[IO.File]::WriteAllText($tmp, $py, (New-Object System.Text.UTF8Encoding($false)))
& .\.venv\Scripts\python.exe $tmp
Remove-Item $tmp -ErrorAction SilentlyContinue
