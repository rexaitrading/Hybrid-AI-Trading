[CmdletBinding()]
param(
  [string[]]$Markets = @("HK","SG","JP"),
  [ValidateSet("NVDA","SPY","QQQ")][string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
# --- HAT_RUNMODE_SINGLETRUTH_BEGIN
$toolsDir = Split-Path -Parent $PSCommandPath
$rmPath = Join-Path $toolsDir "Resolve-HatRunMode.ps1"
if(-not (Test-Path -LiteralPath $rmPath)){ throw "[FAIL-CLOSED] missing Resolve-HatRunMode.ps1" }
$rmRaw = (& $rmPath 2>&1 | Out-String)
$ix0 = $rmRaw.IndexOf("{"); $ix1 = $rmRaw.LastIndexOf("}")
if($ix0 -lt 0 -or $ix1 -le $ix0){ throw "[FAIL-CLOSED] Resolve-HatRunMode did not return JSON" }
$rmObj = ($rmRaw.Substring($ix0, ($ix1 - $ix0 + 1)) | ConvertFrom-Json -ErrorAction Stop)
$script:__HAT_RUNMODE = ([string]$rmObj.run_mode).Trim().ToUpperInvariant()
# --- HAT_RUNMODE_SINGLETRUTH_END
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

if($script:__HAT_RUNMODE -eq "LIVE"){
  throw "[FAIL-CLOSED] refusing Run-OneTap-WhenRTH in LIVE"
}

function RC([string]$m,[string]$sym){
  $raw = (& .\tools\Resolve-RunContext.ps1 -Market $m -Symbol $sym | Out-String)
  $raw = (($raw + "")).Trim()
  if(-not $raw){ return $null }
  $i0 = $raw.IndexOf("{"); $i1 = $raw.LastIndexOf("}")
  if($i0 -lt 0 -or $i1 -le $i0){ return $null }
  $json = $raw.Substring($i0, ($i1-$i0+1))
  try { return ($json | ConvertFrom-Json -ErrorAction Stop) } catch { return $null }
}

foreach($m in $Markets){
  "`n=== RTH-GUARD market=$m symbol=$Symbol ===" | Out-Host
  $rc = RC $m $Symbol
  if(-not $rc){
    Write-Host ("[SKIP] Resolve-RunContext empty for " + $m) -ForegroundColor Yellow
    continue
  }

  $sess = ($rc.session_name + "")
  $open = [bool]$rc.is_open_now
  $closed = [bool]$rc.market_closed_today
  $asOf = ($rc.as_of_date + "")
  # A3: propagate market-aware as_of_date to env for downstream tools (StrictMode-safe)
  $asOf10 = ($asOf + "").Trim()
  if($asOf10.Length -ge 10){ $asOf10 = $asOf10.Substring(0,10) }
  if($asOf10 -match '^\d{4}-\d{2}-\d{2}$'){ $env:HAT_ASOF_DATE = $asOf10 }
  Write-Host ("as_of_date=" + $asOf + " session=" + $sess + " is_open_now=" + $open + " market_closed_today=" + $closed)

  if(-not $open -or $sess -ne "RTH"){
    Write-Host ("[SKIP] not RTH/open (session=" + $sess + " open=" + $open + ")") -ForegroundColor Yellow
    continue
  }

  # Intel pulse (if available)
  if(Test-Path -LiteralPath ".\tools\Run-IntelPipeline-Minimal.ps1"){
    Write-Host ("[RUN] IntelPipeline-Minimal market=" + $m) -ForegroundColor Cyan
    $env:HAT_MARKET = $m
    $env:HAT_SYMBOL = $Symbol
    .\tools\Run-IntelPipeline-Minimal.ps1 2>&1 | Out-Host
  } else {
    Write-Host "[WARN] missing Run-IntelPipeline-Minimal.ps1" -ForegroundColor Yellow
  }

  # OneTap
  Write-Host ("[RUN] OneTap market=" + $m) -ForegroundColor Cyan
  .\tools\Run-DailyReadiness-OneTap.ps1 -Market $m -Symbol $Symbol 2>&1 | Out-Host
  Write-Host ("[DONE] market=" + $m + " EXITCODE=" + $LASTEXITCODE) -ForegroundColor Cyan
}
