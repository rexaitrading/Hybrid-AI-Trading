#requires -Version 5.1
[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "US",
  [bool]$Enabled = $false,
  [string]$Reason = "",
  [string[]]$AllowedModules = @()
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

# ENABLEMENT_PRESERVE_V2
$explicitEnabled = $PSBoundParameters.ContainsKey("Enabled")
$explicitReason  = $PSBoundParameters.ContainsKey("Reason") -and ((($Reason+"")).Trim().Length -gt 0)
$explicitAllowed = $PSBoundParameters.ContainsKey("AllowedModules")
$enablePathExisting = Join-Path $logsDirOut "market_enablement.json"
$prevEnabled = $null
$prevReason  = ""
$prevAllowed = @()
if((Test-Path -LiteralPath $enablePathExisting)){
  try {
    $prev = (Get-Content -LiteralPath $enablePathExisting -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop)
    try { if($prev.PSObject.Properties.Name -contains "enabled"){ $prevEnabled = [bool]$prev.enabled } } catch { $prevEnabled = $null }
    try { if($prev.PSObject.Properties.Name -contains "reason"){ $prevReason = ([string]$prev.reason) } } catch { $prevReason = "" }
    try { if($prev.PSObject.Properties.Name -contains "allowed_modules"){ $prevAllowed = @($prev.allowed_modules) } } catch { $prevAllowed = @() }
  } catch { $prevEnabled = $null; $prevReason = ""; $prevAllowed=@() }
}

# enabled (never overwrite existing enabled=true unless explicitly passed)
$en = $false
if($explicitEnabled){ $en = [bool]$Enabled }
elseif($prevEnabled -ne $null){ $en = [bool]$prevEnabled }
else { $en = $false }

# reason
$r = (($Reason+"")).Trim()
if($explicitReason){ }
elseif((($prevReason+"")).Trim().Length -gt 0 -and ($prevEnabled -ne $null)){ $r = $prevReason }
else { $r = if($en){ "explicitly_enabled" } else { "default_disabled" } }

# allowed modules
$mods = @()
if($explicitAllowed){ $mods = @($AllowedModules) }
elseif(@($prevAllowed).Count -gt 0){ $mods = @($prevAllowed) }
else { $mods = @() }

# ALLOWLIST_AUTOFILL_FROM_POLICY_V1
if($explicitEnabled -and $en -and (-not $explicitAllowed)){
  $polPath = Join-Path $logsDirOut "market_module_policy.json"
  if(-not (Test-Path -LiteralPath $polPath)){ throw ("[FAIL-CLOSED] enabling market requires policy receipt: " + $polPath) }
  $pol = (Get-Content -LiteralPath $polPath -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop)
  $pm = ""
  try { if($pol.PSObject.Properties.Name -contains "primary_module"){ $pm = ([string]$pol.primary_module).Trim() } } catch { $pm = "" }
  if(-not $pm){ throw "[FAIL-CLOSED] primary_module empty in policy; refusing to enable without allowlist" }
  $mods = @($pm)
}


$out = [ordered]@{
  schema     = "market_enablement.v2"
  market     = (($Market + "")).Trim().ToUpperInvariant()
  as_of_date = $todayLocal
  enabled    = $en
  reason     = $r
  allowed_modules = @($mods)
  ts_utc     = (Get-Date).ToUniversalTime().ToString("o")
}

$outPath = Join-Path $logsDirOut "market_enablement.json"
Write-Utf8NoBomLf $outPath ($out | ConvertTo-Json -Depth 6)

Write-Host ("[ENABLE] wrote " + $outPath + " enabled=" + $en + " reason=" + $r) -ForegroundColor Yellow
return
