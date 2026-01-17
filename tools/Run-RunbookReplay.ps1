[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "US",

  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  [ValidateSet("PAPER","PAPERLIVE","LIVE")]
  [string]$Mode = "PAPERLIVE",

  # Optional: force a historical as_of_date (YYYY-MM-DD). If blank, use RunContext.as_of_date.
  [string]$AsOfDate = "",

  [switch]$NoConsole
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

try {
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [Console]::OutputEncoding = $utf8
  [Console]::InputEncoding  = $utf8
  $global:OutputEncoding    = $utf8
} catch { }

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $t = ($Text -replace "`r`n","`n" -replace "`r","`n")
  if($t.Length -eq 0 -or $t[-1] -ne "`n"){ $t += "`n" }
  [System.IO.File]::WriteAllText($Path, $t, (New-Object System.Text.UTF8Encoding($false)))
}
function Fail([string]$m){
  Write-Host ("[FAIL-CLOSED] " + $m) -ForegroundColor Red
  exit 2
}
function Slice10([string]$d){
  $s = ([string]$d).Trim()
  if($s.Length -ge 10){ return $s.Substring(0,10) }
  return $s
}
function Read-JsonFromStdout([string]$raw){
  $r = (($raw + "")).Trim()
  $i0 = $r.IndexOf('{'); $i1 = $r.LastIndexOf('}')
  if($i0 -lt 0 -or $i1 -le $i0){ return $null }
  try { return ($r.Substring($i0, ($i1-$i0+1)) | ConvertFrom-Json -ErrorAction Stop) } catch { return $null }
}

$mk = (($Market + "")).Trim().ToUpperInvariant()
$sy = (($Symbol + "")).Trim().ToUpperInvariant()

# Policy A: non-US markets only support NVDA
if($mk -ne "US" -and $sy -in @("SPY","QQQ")){
  Fail ("PolicyA symbol_not_applicable_for_market market=" + $mk + " symbol=" + $sy)
}

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
try { $repoRoot = (Resolve-Path -LiteralPath $repoRoot -ErrorAction Stop).Path } catch { }

# Required tools
$rcPath  = Join-Path $toolsDir "Resolve-RunContext.ps1"
$p4Path  = Join-Path $toolsDir "Write-Phase4Status.ps1"
$p23Path = Join-Path $toolsDir "Write-Phase23Status.ps1"
$evhPath = Join-Path $toolsDir "Write-EvHardStatus.ps1"
$bgPath  = Join-Path $toolsDir "Build-BlockGStatusStub.ps1"
$dashPath= Join-Path $toolsDir "Build-OpsDashboard.ps1"
$ksPath  = Join-Path $toolsDir "Write-KillSwitchStatus.ps1"

foreach($p in @($rcPath,$p4Path,$p23Path,$evhPath,$bgPath,$dashPath,$ksPath)){
  if(-not (Test-Path -LiteralPath $p)){ Fail ("missing tool: " + $p) }
}

# Resolve RunContext (single truth)
$rcRaw = (& $rcPath -Market $mk -Symbol $sy 2>&1 | Out-String)
$rcObj = Read-JsonFromStdout $rcRaw
if(-not $rcObj){ Fail ("Resolve-RunContext did not return JSON (market=" + $mk + ")") }

if(-not ($rcObj.PSObject.Properties.Name -contains "logs_dir_out")){ Fail "RunContext missing logs_dir_out" }
if(-not ($rcObj.PSObject.Properties.Name -contains "as_of_date")){ Fail "RunContext missing as_of_date" }

$logsDirOut = ([string]$rcObj.logs_dir_out).Trim()
if(-not $logsDirOut){ Fail "RunContext logs_dir_out empty" }

$asOf = Slice10 ([string]$rcObj.as_of_date)
if($AsOfDate){
  $a = Slice10 $AsOfDate
  if($a -notmatch '^\d{4}-\d{2}-\d{2}$'){ Fail ("invalid -AsOfDate=" + $AsOfDate) }
  $asOf = $a
}

# Output report path
if(-not (Test-Path -LiteralPath $logsDirOut)){ New-Item -ItemType Directory -Force -Path $logsDirOut | Out-Null }
$reportPath = Join-Path $logsDirOut "runbook_replay_report.json"

# Set env for called tools (authoritative session context)
$env:HAT_MODE      = $Mode
$env:HAT_MARKET    = $mk
$env:HAT_SYMBOL    = $sy
$env:HAT_ASOF_DATE = $asOf
$env:HAT_LOGS_DIR  = $logsDirOut

$steps = @()
$fail = $false

function Run-Step([string]$name,[scriptblock]$sb){
  $ts0 = (Get-Date).ToUniversalTime().ToString("o")
  $exit = 0
  $err = ""
  try {
    & $sb
    if($LASTEXITCODE -ne $null -and [int]$LASTEXITCODE -ne 0){ $exit = [int]$LASTEXITCODE }
  } catch {
    $exit = 2
    $err = $_.Exception.Message
  }
  $ts1 = (Get-Date).ToUniversalTime().ToString("o")
  $script:steps += [pscustomobject]@{
    name = $name
    ts_utc_start = $ts0
    ts_utc_end = $ts1
    exit_code = $exit
    error = $err
  }
  if($exit -ne 0){ $script:fail = $true }
  if(-not $NoConsole){
    $c = if($exit -eq 0){ "Green" } else { "Red" }
    Write-Host ("[RUNBOOK] step=" + $name + " exit=" + $exit + " err=" + $err) -ForegroundColor $c
  }
}

# Execute deterministic steps
Run-Step "phase4_status" { & $p4Path -Market $mk -Symbol $sy | Out-Null }
Run-Step "phase23_status" { & $p23Path -Market $mk -Symbol $sy | Out-Null }
Run-Step "ev_hard_status" { & $evhPath -Market $mk -Symbol $sy | Out-Null }
Run-Step "blockg_stub"    { & $bgPath  -Market $mk -Symbol $sy | Out-Null }
Run-Step "ops_dashboard"  { & $dashPath -Market $mk -Symbol $sy -Mode $Mode -EmitConsole:(-not $NoConsole) | Out-Null }
Run-Step "killswitch_status" { & $ksPath -Market $mk -Symbol $sy -Mode $Mode -NoConsole:$NoConsole | Out-Null }

# Build report (always emitted)
$report = [pscustomobject]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  market = $mk
  symbol = $sy
  run_mode = $Mode
  as_of_date = $asOf
  logs_dir_out = $logsDirOut
  ok = (-not $fail)
  steps = @($steps)
}

try {
  $json = ($report | ConvertTo-Json -Depth 8)
  Write-Utf8NoBomLf $reportPath $json
} catch {
  # Always emit a minimal fail-closed report if JSON serialization fails (PS5.1 safety)
  $fallback = [pscustomobject]@{
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    market = $mk
    symbol = $sy
    run_mode = $Mode
    as_of_date = $asOf
    logs_dir_out = $logsDirOut
    ok = $false
    report_error = ("report_serialize_failed: " + $_.Exception.Message)
  }
  Write-Utf8NoBomLf $reportPath ($fallback | ConvertTo-Json -Depth 5)
}

if(-not $NoConsole){
  Write-Host ("[RUNBOOK] wrote " + $reportPath + " ok=" + (-not $fail)) -ForegroundColor Cyan
}

if($fail){ exit 2 }
exit 0
