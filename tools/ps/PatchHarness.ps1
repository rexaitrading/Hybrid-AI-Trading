[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Utf8NoBomLF {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)][string]$Text
  )

  # Resolve relative paths against repo root (current location),
  # not whatever .NET thinks is the process base dir (e.g. system32).
  if(-not [System.IO.Path]::IsPathRooted($Path)){
    $Path = Join-Path (Get-Location).Path $Path
  }

  # Ensure parent directory exists (helps for logs/test writes)
  $dir = Split-Path -Parent $Path
  if($dir -and -not (Test-Path -LiteralPath $dir)){
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
  }

  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Text -replace "`r`n","`n"), $utf8NoBom)
}
function Backup-File {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [string]$Tag="bak"
  )
  $stamp = Get-Date -Format yyyyMMdd_HHmmss
  $dst = "$Path.$($Tag)_$stamp"
  Copy-Item -LiteralPath $Path -Destination $dst -Force
  return $dst
}