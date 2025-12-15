[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$RelativePath
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$repoRoot = (Get-Location).Path
if (-not (Test-Path (Join-Path $repoRoot "src"))) { throw "Not in repo root: src/ missing" }

$abs = Join-Path $repoRoot $RelativePath
Write-Output $abs
