[CmdletBinding()]
param(
  [switch]$Once,
  [switch]$DryDrill
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
chcp 65001 | Out-Null

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repo

$py = Join-Path $repo '.venv\Scripts\python.exe'
if(-not (Test-Path -LiteralPath $py)){ throw "Missing venv python: $py" }

$env:HAT_IS_PAPER = '1'
$env:HAT_SYMBOL   = 'NVDA'

$args = @('-m','hybrid_ai_trading.runners.paper_runner','--universe','NVDA','--ib-snapshots','--log-file','auto')
if($Once){ $args += '--once' } else { $args += '--once' }
if($DryDrill){ $args += '--dry-drill' } else { $args += '--dry-drill' }

& $py @args
exit $LASTEXITCODE