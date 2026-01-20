#requires -Version 5.1
[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "US",
  [bool]$Enabled = $false,
  [string]$Reason = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Slice10([string]$s){
  $s = (($s + "")).Trim()
  if($s.Length -ge 10){ return $s.Substring(0,10) }
  return $s
}

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n","`n"
  if($Text.Length -gt 0 -and $Text[-1] -ne "`n"){ $Text += "`n" }
  [System.IO.File]::WriteAllText($Path,$Text,$utf8)
}

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $toolsDir) -ErrorAction Stop).Path
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

# RunContext is single truth for as_of_date + logs_dir_out
$rcPath = Join-Path $repoRoot "tools\Resolve-RunContext.ps1"
if(-not (Test-Path -LiteralPath $rcPath)){ throw "[FAIL-CLOSED] missing Resolve-RunContext.ps1" }

$rcRaw = & $rcPath -Market $Market -Symbol NVDA 2>$null | Out-String
$rcRaw = (($rcRaw + "")).Trim()
$i0 = $rcRaw.IndexOf("{"); $i1 = $rcRaw.LastIndexOf("}")
if($i0 -lt 0 -or $i1 -le $i0){ throw "[FAIL-CLOSED] Resolve-RunContext did not return JSON" }
$rc = ($rcRaw.Substring($i0, ($i1-$i0+1)) | ConvertFrom-Json -ErrorAction Stop)

$todayLocal = Slice10 ([string]$rc.as_of_date)

$logsDirOut = ""
try {
  if($rc.PSObject.Properties.Name -contains "logs_dir_out"){
    $logsDirOut = ([string]$rc.logs_dir_out).Trim()
  }
} catch { $logsDirOut = "" }

if(-not $logsDirOut){
  try {
    if($rc.PSObject.Properties.Name -contains "logs_dir"){
      $logsDirOut = ([string]$rc.logs_dir).Trim()
    }
  } catch { $logsDirOut = "" }
}

if(-not $todayLocal){ throw "[FAIL-CLOSED] todayLocal empty" }
if(-not $logsDirOut){ throw "[FAIL-CLOSED] logsDirOut empty" }

New-Item -ItemType Directory -Force -Path $logsDirOut | Out-Null

$en = [bool]$Enabled
$r  = (($Reason + "")).Trim()
if(-not $r){
  $r = if($en){ "explicitly_enabled" } else { "default_disabled" }
}

$out = [ordered]@{
  schema     = "market_enablement.v1"
  market     = (($Market + "")).Trim().ToUpperInvariant()
  as_of_date = $todayLocal
  enabled    = $en
  reason     = $r
  ts_utc     = (Get-Date).ToUniversalTime().ToString("o")
}

$outPath = Join-Path $logsDirOut "market_enablement.json"
Write-Utf8NoBomLf $outPath ($out | ConvertTo-Json -Depth 6)

Write-Host ("[ENABLE] wrote " + $outPath + " enabled=" + $en + " reason=" + $r) -ForegroundColor Yellow
return
