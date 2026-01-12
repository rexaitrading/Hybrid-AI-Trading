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
$ns = [string]$j.log_namespace
if(-not $ns){ $ns = $Market }

$root = Join-Path $repoRoot ("logs\" + $ns)
if(-not (Test-Path -LiteralPath $root)){
  New-Item -ItemType Directory -Force -Path $root | Out-Null
}
$root
