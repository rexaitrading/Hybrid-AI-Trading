[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Find-GitRoot([string]$start){
  $p = (Resolve-Path -LiteralPath $start -ErrorAction Stop).Path
  while($true){
    if(Test-Path -LiteralPath (Join-Path $p ".git")){ return $p }
    $parent = Split-Path -Parent $p
    if(-not $parent -or $parent -eq $p){ break }
    $p = $parent
  }
  throw "[REPOROOT] FAIL-CLOSED: could not find .git from start=$start"
}

# Prefer current working directory (most reliable under OneDrive localized paths)
$root = Find-GitRoot (Get-Location).Path
$root = [System.IO.Path]::GetFullPath($root)

Write-Output $root
