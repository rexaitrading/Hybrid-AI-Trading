[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ArgsLine
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$env:PYTHONPATH = (Join-Path $repoRoot "src")

& py -c $ArgsLine
exit $LASTEXITCODE