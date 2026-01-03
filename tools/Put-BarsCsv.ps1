[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Symbol,
  [Parameter(Mandatory=$true)][string]$AsOfDate,  # YYYY-MM-DD
  [Parameter(Mandatory=$true)][string]$SourceCsv  # columns: ts,open,high,low,close,volume (or time/timestamp variants)
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$dstDir = Join-Path $repo "logs\bars"
New-Item -ItemType Directory -Force -Path $dstDir | Out-Null

$Symbol = $Symbol.ToUpperInvariant()
$dst = Join-Path $dstDir ("{0}_{1}_1m.csv" -f $Symbol,$AsOfDate)

Copy-Item -LiteralPath $SourceCsv -Destination $dst -Force
Write-Host "[BARS] wrote $dst"