[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)][ValidateSet("NVDA","SPY","QQQ","ALL")][string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if(-not (Test-Path -LiteralPath $Path)){ return $null }
  $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
  if ($raw.Length -gt 0 -and [int][char]$raw[0] -eq 65279) { $raw = $raw.TrimStart([char]65279) }
  try { return ($raw | ConvertFrom-Json -ErrorAction Stop) } catch { return $null }
}

function Get-Bool($v) {
  if ($v -is [bool]) { return $v }
  if ($v -is [string]) {
    $t = $v.Trim().ToLowerInvariant()
    if ($t -in @("true","1","yes","y")) { return $true }
    if ($t -in @("false","0","no","n")) { return $false }
  }
  if ($v -is [int] -or $v -is [double]) { return [bool]$v }
  return $false
}

function Resolve-ContractPath {
  param([Parameter(Mandatory=$true)][string]$Sym)

  $envPath = (($env:HAT_BLOCKG_CONTRACT_PATH + "")).Trim()
  if (-not $envPath) { $envPath = (($env:BLOCKG_CONTRACT_PATH + "")).Trim() }
  if ($envPath) { return $envPath }

  $logs = Join-Path $repoRoot "logs"
  $per = Join-Path $logs ("blockg_status_stub_{0}.json" -f $Sym.ToLowerInvariant())
  $canonical = Join-Path $logs "blockg_status_stub.json"

  if (Test-Path -LiteralPath $per) { return $per }
  if (Test-Path -LiteralPath $canonical) { return $canonical }
  return $per
}

function Check-One {
  param([Parameter(Mandatory=$true)][string]$Sym)

  $path = Resolve-ContractPath -Sym $Sym
  if (-not (Test-Path -LiteralPath $path)) {
    return [ordered]@{ ok=$false; exit=2; why="missing_contract"; path=$path }
  }

  $c = Read-JsonFile -Path $path
  if (-not $c) {
    return [ordered]@{ ok=$false; exit=2; why="contract_parse_failed"; path=$path }
  }

  $today = (Get-Date).ToString("yyyy-MM-dd")
  $asOf  = [string]$c.as_of_date
  if ($asOf -ne $today) {
    return [ordered]@{ ok=$false; exit=3; why="contract_stale"; path=$path; as_of=$asOf; today=$today }
  }

  # Per-symbol ready flag
  $flag = $null
  switch($Sym){
    "NVDA" { $flag = $c.nvda_blockg_ready }
    "SPY"  { $flag = $c.spy_blockg_ready }
    "QQQ"  { $flag = $c.qqq_blockg_ready }
  }
  if ($flag -eq $null) {
    return [ordered]@{ ok=$false; exit=3; why="missing_symbol_ready_flag"; path=$path }
  }

  if (Get-Bool $flag) {
    return [ordered]@{ ok=$true; exit=0; why="ready"; path=$path }
  }

  # Explain failure (contract-only)
  $phase4  = Get-Bool $c.phase4_ok_today
  $phase23 = Get-Bool $c.phase23_health_ok_today
  $evhard  = Get-Bool $c.ev_hard_daily_ok_today

  # GateScore: prefer per-symbol, else gatescore_ok_today, else gatescore_fresh_today
  $gs_ok = $false
  $gsField = ($Sym.ToLowerInvariant() + "_gatescore_ok_today")
  if ($c.PSObject.Properties.Name -contains $gsField) { $gs_ok = Get-Bool $c.$gsField }
  elseif ($c.PSObject.Properties.Name -contains "gatescore_ok_today") { $gs_ok = Get-Bool $c.gatescore_ok_today }
  elseif ($c.PSObject.Properties.Name -contains "gatescore_fresh_today") { $gs_ok = Get-Bool $c.gatescore_fresh_today }
  else { return [ordered]@{ ok=$false; exit=3; why="missing_gatescore_fields"; path=$path } }

  if (-not $phase4)  { return [ordered]@{ ok=$false; exit=10; why="phase4_ok_today=false"; path=$path } }
  if (-not $phase23) { return [ordered]@{ ok=$false; exit=11; why="phase23_health_ok_today=false"; path=$path } }
  if (-not $evhard)  { return [ordered]@{ ok=$false; exit=12; why="ev_hard_daily_ok_today=false"; path=$path } }
  if (-not $gs_ok)   { return [ordered]@{ ok=$false; exit=13; why="gatescore_ok_today=false"; path=$path } }

  return [ordered]@{ ok=$false; exit=14; why="symbol_ready_flag=false"; path=$path }
}

if($Symbol -eq "ALL"){
  $bad = $false
  foreach($s in @("NVDA","SPY","QQQ")){
    $r = Check-One -Sym $s
    Write-Host ("[BLOCK-G] {0} ok={1} why={2} path={3}" -f $s,$r.ok,$r.why,$r.path) -ForegroundColor Cyan
    if(-not $r.ok){ $bad = $true }
  }
  if($bad){ exit 2 } else { exit 0 }
} else {
  $r = Check-One -Sym $Symbol
  Write-Host ("[BLOCK-G] {0} ok={1} why={2} path={3}" -f $Symbol,$r.ok,$r.why,$r.path) -ForegroundColor Cyan
  exit $r.exit
}