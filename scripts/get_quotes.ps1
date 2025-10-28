param(
  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$ArgsPassthrough
)

$ErrorActionPreference = 'Stop'

# Prefer your project venv; otherwise fall back to system Python
$py = 'C:\Dev\HybridAITrading\.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
  $cmd = Get-Command python, py -EA SilentlyContinue | Select-Object -First 1
  if (-not $cmd) { throw "No Python found. Please install Python or activate your venv." }
  $py = $cmd.Source
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $root 'get_quotes.py'
if (-not (Test-Path $script)) { throw "Missing get_quotes.py at $script" }

# Run python with all user-provided flags/symbols
& $py $script @ArgsPassthrough