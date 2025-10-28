param(
  [string]$Cfg      = "config\paper_runner.yaml",
  [string]$ApiHost  = "127.0.0.1",
  [int]   $Port     = 4002,
  [string]$VenvPy   = ".\.venv\Scripts\python.exe",

  [ValidateSet('', 'BUY', 'SELL')] [string]$Force = '',
  [switch]$Transmit,
  [switch]$Console,

  # New after-hours controls
  [switch]$OutsideRth,
  [ValidateSet('LMT','MKT')] [string]$OrderType = 'LMT',
  [double]$LimitOffset = 0.30,
  [ValidateSet('','SMART','ISLAND','ARCA','NASDAQ')] [string]$Dest = '',
  [switch]$Once
)

# Env for IB API
$env:IB_HOST = $ApiHost
$env:IB_PORT = "$Port"

# Make sure Python can import from .\src
$pwdSrc = (Resolve-Path ".\src").Path
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$pwdSrc;$env:PYTHONPATH" } else { $pwdSrc }

# Invoke runner by path (avoids -m import quirk)
$runnerPath = (Resolve-Path ".\src\hybrid_ai_trading\runners\runner_paper.py").Path
$argsList = @('-u', $runnerPath, '--config', $Cfg)

# Core options
if ($Force)    { $argsList += @('--force', $Force) }
if ($Transmit) { $argsList += '--transmit' }
if ($Console)  { $argsList += @('--json','--log-level','DEBUG','--log-file','NUL') }

# AH options (forward only if present / meaningful)
if ($OutsideRth)           { $argsList += '--outside-rth' }
if ($OrderType)            { $argsList += @('--order-type', $OrderType) }
if ($LimitOffset -ne $null){ $argsList += @('--limit-offset', ('{0:N2}' -f $LimitOffset)) }
if ($Dest)                 { $argsList += @('--dest', $Dest) }
if ($Once)                 { $argsList += '--once' }

# Client id
if (-not $env:IB_CLIENT_ID) { $env:IB_CLIENT_ID = '5007' }
$argsList += @('--client-id', $env:IB_CLIENT_ID)

Write-Host ("Running: {0} {1}" -f $VenvPy, ($argsList -join ' ')) -ForegroundColor Cyan
& $VenvPy @argsList
$exit = $LASTEXITCODE
if ($exit -ne 0) {
  Write-Host "Runner exited with code $exit" -ForegroundColor Yellow
  exit $exit
}
