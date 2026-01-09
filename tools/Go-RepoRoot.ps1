[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

if(-not (Test-Path -LiteralPath (Join-Path $repoRoot ".git"))){
  throw ("NOT IN REPO ROOT: " + $repoRoot)
}

Set-Location -LiteralPath $repoRoot
$repoRoot
