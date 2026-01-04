[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",
  [int]$Minutes = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$logs = Join-Path $repo "logs"
if(-not (Test-Path -LiteralPath $logs)){ New-Item -ItemType Directory -Path $logs -Force | Out-Null }

$today = (Get-Date).ToString("yyyy-MM-dd")
$exp = (Get-Date).ToUniversalTime().AddMinutes($Minutes).ToString("o")

$path = Join-Path $logs ("live_arm_{0}.json" -f $Symbol.ToUpperInvariant())
$obj = [ordered]@{
  symbol = $Symbol.ToUpperInvariant()
  as_of_date = $today
  expires_utc = $exp
}
$out = ($obj | ConvertTo-Json -Depth 5)

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$out = ($out -replace "`r`n","`n")
if($out.Length -gt 0 -and $out[-1] -ne "`n"){ $out += "`n" }
[System.IO.File]::WriteAllText($path, $out, $utf8NoBom)

Write-Host "[ARM] Wrote $path expires_utc=$exp" -ForegroundColor Green
exit 0
