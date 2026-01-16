[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "US",

  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA"
)


# --- repo root bootstrap (env-first) ---
$repoRoot = ($env:HAT_REPO_ROOT + "").Trim()
if(-not $repoRoot){
  $repoRoot = & (Join-Path $PSScriptRoot "Go-RepoRoot.ps1")
}
if(-not $repoRoot){ throw "[REPOROOT] FAIL-CLOSED: repoRoot empty (env+Go-RepoRoot)" }
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
# $root = (Resolve-Path ".").Path                 # disabled (use env HAT_REPO_ROOT)
# [A3] removed unsafe Set-Location $root (undefined); repoRoot already set
if(-not (Test-Path ".\.git")){ throw "NOT IN REPO ROOT" }


# A3_MARKET_WIRE_BEGIN
$m0 = (($Market + '''')).Trim().ToUpperInvariant()
if(-not $m0){ $m0 = (($env:HAT_MARKET + '''')).Trim().ToUpperInvariant() }
if(-not $m0){ $m0 = 'US' }
$env:HAT_MARKET = $m0
# A3_SYMBOL_WIRE_BEGIN
$env:HAT_SYMBOL = (($Symbol + "")).Trim().ToUpperInvariant()
if(-not $env:HAT_SYMBOL){ $env:HAT_SYMBOL = "NVDA" }
# A3_SYMBOL_WIRE_END
# A3_MARKET_WIRE_END

function Run-Step([string]$name, [scriptblock]$sb){
  Write-Host "`n==================== $name ====================" -ForegroundColor Cyan
  & $sb
  Write-Host "[OK] $name" -ForegroundColor Green
}

function Run-PS([string]$path, [string[]]$args=@()){
  if(-not (Test-Path $path)){ throw "Missing tool: $path" }
  $a = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$path) + $args
  & powershell @a
  $code = [int]$LASTEXITCODE
  if($code -ne 0){ throw "Tool failed: $path exit=$code" }
  return $code
}

function Run-PSAllowExit([string]$path, [int[]]$okExits, [string[]]$args=@()){
  if(-not (Test-Path $path)){ throw "Missing tool: $path" }
  $a = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$path) + $args
  & powershell @a
  $code = [int]$LASTEXITCODE
  if(-not ($okExits -contains $code)){ throw "Tool failed: $path exit=$code" }
  return $code
}

Run-Step "Phase4: Stamp (todayness)" { Run-PS ".\tools\Run-Phase4Stamp.ps1" @("-Market",$env:HAT_MARKET,"-Symbol",$env:HAT_SYMBOL) }

Run-Step "Phase23: Health daily" { Run-PS ".\tools\Run-Phase23HealthDaily.ps1" @("-Market",$env:HAT_MARKET,"-Symbol",$env:HAT_SYMBOL) }

Run-Step "Phase5: EV-hard snapshot" { Run-PS ".\tools\Build-EvHardSnapshot.ps1" @("-Market",$env:HAT_MARKET,"-Symbol",$env:HAT_SYMBOL) }

Run-Step "Phase5: EV-hard daily veto row" { Run-PS ".\tools\Run-EvHardVetoDaily.ps1" @("-Market",$env:HAT_MARKET,"-Symbol",$env:HAT_SYMBOL) }

Run-Step "Phase2: Micro snapshot (WARN if output missing)" {
  Run-PS ".\tools\Run-Phase2MicroSnapshot.ps1"
  $out = ".\logs\spy_qqq_micro_for_notion.csv"
  if(-not (Test-Path $out)){
    Write-Host "[WARN] Phase2 output missing: logs\spy_qqq_micro_for_notion.csv" -ForegroundColor Yellow
  }
}

Run-Step "Phase3: GateScore PnL summary" { Run-PS ".\tools\Build-GateScorePnlSummary.ps1" @("-Market",$env:HAT_MARKET,"-Symbol",$env:HAT_SYMBOL) }

Run-Step "BlockG: Build contract" { Run-PS ".\tools\Build-BlockGStatusStub.ps1" @("-Symbol",$env:HAT_SYMBOL,"-Market",$env:HAT_MARKET) }

Run-Step "BlockG: Contract-only checker (deterministic)" {
  $code = Run-PSAllowExit ".\tools\Invoke-BlockGCheck.ps1" @(0,2) @("-Symbol",$Symbol,"-Mode","ALL_STRICT","-Market",$env:HAT_MARKET)
  if($code -eq 0){
    Write-Host "[BLOCKG] READY (exit=0)" -ForegroundColor Green
  } else {
    Write-Host "[BLOCKG] NOT READY (exit=2) - expected fail-closed state" -ForegroundColor Yellow
  }
}

Run-Step "Test slice: BlockG + execution guards" {
  & pytest -q `
    tests/test_blockg_enforce.py `
    tests/execution/test_blockg_order_manager_guard.py
  if($LASTEXITCODE -ne 0){ throw "pytest slice failed exit=$LASTEXITCODE" }
}

Run-Step "OneTap: Summary" {
  # A3_STUBPATH_BEGIN
  $mkt = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant()
  if(-not $mkt){ $mkt = "US" }
  $contract = if($mkt -eq "US"){ ".\logs\blockg_status_stub.json" } else { (".\logs\{0}\blockg_status_stub.json" -f $mkt) }
  # A3_STUBPATH_END
  if(Test-Path $contract){
    $j = Get-Content $contract -Raw -Encoding utf8 | ConvertFrom-Json
    $state = if([bool]$j.nvda_blockg_ready){"READY"} else {"NOT READY"}
    Write-Host ("STATE=" + $state) -ForegroundColor Yellow

    $reasons = @()
    try { $reasons = @($j.reasons_not_ready) } catch { $reasons = @() }
    Write-Host "TOP REASONS:" -ForegroundColor Cyan
    $reasons | Select-Object -First 5 | ForEach-Object { " - " + $_ } | Out-Host

        Write-Host "FILES:" -ForegroundColor Cyan
    # A3_FILES_LIST_MARKET_BEGIN
    $mkt2 = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant()
    if(-not $mkt2){ $mkt2 = "US" }

    $p_stub = if($mkt2 -eq "US"){"logs\blockg_status_stub.json"} else {("logs\{0}\blockg_status_stub.json" -f $mkt2)}
    $p_ev   = if($mkt2 -eq "US"){"logs\ev_hard_snapshot.json"}     else {("logs\{0}\ev_hard_snapshot.json" -f $mkt2)}
    $p_veto = if($mkt2 -eq "US"){"logs\phase5_ev_hard_veto_daily.csv"} else {("logs\{0}\phase5_ev_hard_veto_daily.csv" -f $mkt2)}
    $p_pnl  = if($mkt2 -eq "US"){"logs\gatescore_pnl_summary.csv"} else {("logs\{0}\gatescore_pnl_summary.csv" -f $mkt2)}
    $p_evt  = if($mkt2 -eq "US"){"logs\nvda_gatescore_events.jsonl"} else {("logs\{0}\nvda_gatescore_events.jsonl" -f $mkt2)}

    (" - " + $p_stub) | Out-Host
    (" - " + $p_ev)   | Out-Host
    (" - " + $p_veto) | Out-Host
    (" - " + $p_pnl)  | Out-Host
    (" - " + $p_evt)  | Out-Host
    # A3_FILES_LIST_MARKET_END" - logs\ev_hard_snapshot.json" | Out-Host
    " - logs\phase5_ev_hard_veto_daily.csv" | Out-Host
    " - logs\gatescore_pnl_summary.csv" | Out-Host
    " - logs\nvda_gatescore_events.jsonl" | Out-Host
  } else {
    Write-Host "STATE=UNKNOWN (missing logs\blockg_status_stub.json)" -ForegroundColor Yellow
  }
}

Write-Host "`nDONE: Run-Phase1ToPhase7Daily completed successfully." -ForegroundColor Yellow
exit 0
