param(
  # Prefer module path (no function) for modules that act as scripts:
  #   -Entry "hybrid_ai_trading.runners.paper_trader"
  # If you do have a function, you can pass: module:function
  [string]$Entry = "hybrid_ai_trading.runners.paper_trader",
  # Or run a file directly (fallback):
  [string]$ScriptPath = "",
  [string]$Config = "config\paper_runner.yaml",
  [string]$UseLivePriceRM = "1"
)
$ErrorActionPreference='Stop'
$env:PYTHONPATH = "$PWD\src;$env:PYTHONPATH"
$env:HAT_USE_LIVE_PRICE_RM = $UseLivePriceRM

function Run-ModuleOrScript {
  param([string]$Entry, [string]$ScriptPath, [string]$Config)

  if ($Entry) {
    # Build a temp runner that either calls module:function or runs module as script (__main__)
    $py = if ($Entry -match '^[\w\.]+:[\w\.]+$') {
@"
import sys, importlib, runpy
modstr, fnstr = "$Entry".split(":",1)
mod = importlib.import_module(modstr)
fn  = getattr(mod, fnstr, None)
if callable(fn):
    sys.argv = ['runner','--config', r'$Config']
    fn()
else:
    sys.argv = ['-m', modstr, '--config', r'$Config']
    runpy.run_module(modstr, run_name='__main__')
"@
    } else {
@"
import sys, runpy
modstr = "$Entry"
sys.argv = ['-m', modstr, '--config', r'$Config']
runpy.run_module(modstr, run_name='__main__')
"@
    }
    $tmp = Join-Path $env:TEMP ("runner_{0}.py" -f ([guid]::NewGuid().ToString("N")))
    [IO.File]::WriteAllText($tmp, $py, (New-Object System.Text.UTF8Encoding($false)))
    & .\.venv\Scripts\python.exe $tmp
    $code = $LASTEXITCODE
    Remove-Item $tmp -ErrorAction SilentlyContinue
    return $code
  }

  if (-not $ScriptPath) { $ScriptPath = ".\src\hybrid_ai_trading\runners\paper_trader.py" }
  if (-not (Test-Path $ScriptPath)) { throw "Runner script not found: $ScriptPath" }
  & .\.venv\Scripts\python.exe $ScriptPath --config $Config
  return $LASTEXITCODE
}

exit (Run-ModuleOrScript -Entry $Entry -ScriptPath $ScriptPath -Config $Config)
