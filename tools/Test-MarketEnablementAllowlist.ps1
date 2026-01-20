#requires -Version 5.1
[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "US"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Slice10([string]$s){ $s=(($s+"")).Trim(); if($s.Length -ge 10){ return $s.Substring(0,10) } return $s }

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $toolsDir) -ErrorAction Stop).Path
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

# Resolve per-market logs dir (single-truth)
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$logsDir = (& $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1") -Market $Market 2>$null | Out-String).Trim()
if(-not $logsDir){ $logsDir = Join-Path $repoRoot ("logs\{0}" -f $Market) }
if(-not (Test-Path -LiteralPath $logsDir)){ throw ("[FAIL-CLOSED] logsDir missing: " + $logsDir) }

$enPath = Join-Path $logsDir "market_enablement.json"
$msPath = Join-Path $logsDir "market_selector.json"

if(-not (Test-Path -LiteralPath $enPath)){ throw ("[FAIL-CLOSED] missing enablement receipt: " + $enPath) }
if(-not (Test-Path -LiteralPath $msPath)){ throw ("[FAIL-CLOSED] missing market selector receipt: " + $msPath) }

$en = (Get-Content -LiteralPath $enPath -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop)
$ms = (Get-Content -LiteralPath $msPath -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop)

$enabled = $false
try { if($en.PSObject.Properties.Name -contains "enabled"){ $enabled = [bool]$en.enabled } } catch { $enabled = $false }
$mods = @()
try { if($en.PSObject.Properties.Name -contains "allowed_modules"){ $mods = @($en.allowed_modules) } } catch { $mods = @() }

$chosen = ""
try { if($ms.PSObject.Properties.Name -contains "chosen_module"){ $chosen = ([string]$ms.chosen_module).Trim() } } catch { $chosen = "" }

if(-not $enabled){ throw ("[FAIL-CLOSED] market not enabled: " + $Market) }
if(@($mods).Count -le 0){ throw ("[FAIL-CLOSED] no allowed_modules for market: " + $Market) }
if(-not $chosen){ throw ("[FAIL-CLOSED] selector has no chosen_module for market: " + $Market) }
if(-not (@($mods) -contains $chosen)){ throw ("[FAIL-CLOSED] chosen_module not allowlisted: " + $chosen) }

Write-Host ("[ALLOWLIST] OK market=" + $Market + " chosen_module=" + $chosen) -ForegroundColor Green
return
