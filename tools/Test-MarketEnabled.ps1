[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","CN_SH","CN_SZ")]
  [string]$Market = "US"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$cfg = Join-Path $repoRoot ("configs\markets\" + $Market + ".json")
if(-not (Test-Path -LiteralPath $cfg)){ throw "Missing market config: $cfg" }

$j = Get-Content -LiteralPath $cfg -Raw -Encoding UTF8 | ConvertFrom-Json

$enabled = $false
try { $enabled = [bool]$j.enabled } catch { $enabled = $false }

# Override: allow forced enable for ops testing only
$force = (($env:HAT_MARKET_FORCE_ENABLE + "") -eq "1")

if(-not $enabled -and -not $force){
  Write-Host ("[MARKET] FAIL-CLOSED: Market disabled by config => " + $Market) -ForegroundColor Red
  exit 2
}

$suffix = ""
if($force){ $suffix = " (FORCED)" }
Write-Host ("[MARKET] OK: enabled => " + $Market + $suffix) -ForegroundColor Green
exit 0
