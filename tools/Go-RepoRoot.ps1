[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

function Fail([string]$m){ throw "[REPOROOT] FAIL-CLOSED: $m" }

# Find .git by walking up from THIS tools directory (no git calls, no encoding surprises)
$toolsDir = $PSScriptRoot
if(-not $toolsDir){ Fail "PSScriptRoot empty" }

$cur = [System.IO.Path]::GetFullPath((Split-Path -Parent $toolsDir))
for($i=0; $i -lt 20; $i++){
  if(Test-Path -LiteralPath (Join-Path $cur ".git")){
    Write-Output $cur
    return
  }
  $parent = Split-Path -Parent $cur
  if(-not $parent -or $parent -eq $cur){ break }
  $cur = $parent
}

Fail "Unable to locate repo root (no .git found walking up)"