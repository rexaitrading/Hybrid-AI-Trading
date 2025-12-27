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