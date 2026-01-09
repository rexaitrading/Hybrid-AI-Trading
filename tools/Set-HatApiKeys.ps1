[CmdletBinding()]
param(
  [switch]$Persist,
  [switch]$SetYouTube
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

function Read-Secret([string]$Prompt){
  $sec = Read-Host $Prompt -AsSecureString
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
  try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

function Upsert-Line([string[]]$Lines,[string]$Key,[string]$Value){
  if([string]::IsNullOrWhiteSpace($Value)){ return $Lines }
  $re = "^(?i)" + [regex]::Escape($Key) + "\s*="
  $out = @()
  $found = $false
  foreach($ln in $Lines){
    if($ln -match $re){
      $out += ($Key + "=" + $Value)
      $found = $true
    } else {
      $out += $ln
    }
  }
  if(-not $found){ $out += ($Key + "=" + $Value) }
  return $out
}

Write-Host "`n[KEY-WIZARD] Enter keys (input hidden for secrets). Leave blank to skip." -ForegroundColor Cyan

$poly = Read-Secret "POLYGON_API_KEY"
$alpKey = Read-Secret "ALPACA_API_KEY"
$alpSec = Read-Secret "ALPACA_SECRET_KEY"
$bz = Read-Secret "BENZINGA_API_KEY"

$yt = ""
if($SetYouTube){
  Write-Host "`nYouTube channel IDs are NOT secrets." -ForegroundColor DarkGray
  Write-Host "Format: UCxxxxxxxxxxxxxxxxxxxxxx;UCyyyyyyyyyyyyyyyyyyyyyy" -ForegroundColor DarkGray
  $yt = (Read-Host "HAT_YT_CHANNEL_IDS").Trim()
}

# set in current process
if($poly){ $env:POLYGON_API_KEY = $poly; if(-not $env:POLYGON_KEY){ $env:POLYGON_KEY = $poly } }
if($alpKey){ $env:ALPACA_API_KEY = $alpKey }
if($alpSec){ $env:ALPACA_SECRET_KEY = $alpSec }
if($bz){ $env:BENZINGA_API_KEY = $bz }
if($yt){ $env:HAT_YT_CHANNEL_IDS = $yt }

if($Persist){
  $vault = Join-Path $repoRoot ".secrets\hat_keys.env"
  if(-not (Test-Path -LiteralPath (Split-Path -Parent $vault))){
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $vault) | Out-Null
  }
  $lines = @()
  if(Test-Path -LiteralPath $vault){ $lines = Get-Content -LiteralPath $vault -Encoding utf8 }
  $lines = Upsert-Line $lines "POLYGON_API_KEY" $poly
  $lines = Upsert-Line $lines "POLYGON_KEY" $poly
  $lines = Upsert-Line $lines "ALPACA_API_KEY" $alpKey
  $lines = Upsert-Line $lines "ALPACA_SECRET_KEY" $alpSec
  $lines = Upsert-Line $lines "BENZINGA_API_KEY" $bz
  if($yt){ $lines = Upsert-Line $lines "HAT_YT_CHANNEL_IDS" $yt }

  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($vault, (($lines -join "`n") + "`n"), $utf8NoBom)
  Write-Host "[KEY-WIZARD] Saved to .secrets\hat_keys.env" -ForegroundColor Green
# Always regenerate canonical cleaned+report immediately (single source of truth for runtime)
# Always regenerate canonical cleaned+report immediately (single source of truth for runtime)
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "Rebuild-HatKeysClean.ps1") | Out-Host
if($LASTEXITCODE -ne 0){ throw ("[KEY-WIZARD] FAIL-CLOSED: rebuild cleaned keys failed (exit=" + $LASTEXITCODE + ")") }
}

Write-Host "[KEY-WIZARD] Done." -ForegroundColor Green
