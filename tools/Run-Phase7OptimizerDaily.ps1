[CmdletBinding()]
param(
  [string]$StatePath   = ".\logs\phase6_portfolio_state.json",
  [string]$BlockGPath  = ".\logs\blockg_status_stub.json",
  [string]$OutDir      = ".\logs\phase7",
  [string]$OutPath     = ".\logs\phase7_optimizer_output.json",
  [string]$SymbolsRaw  = "NVDA,SPY,QQQ",
  [double]$MaxWeight   = 0.60,
  [double]$MinWeight   = 0.00,
  [switch]$Enable
  ,[string]$MetricsPath = ".\logs\phase6_portfolio_metrics.json"
  ,[int]$MinRows = 10
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

function Write-Utf8NoBom {
  param([string]$Path, [string]$Text)
  $enc = New-Object System.Text.UTF8Encoding($false)
# $repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)   # disabled (use env-first bootstrap repoRoot)
  $full = $Path
  if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $Path }
  $dir = Split-Path -Parent $full
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  $t = $Text -replace "`r`n","`n"
  if(-not $t.EndsWith("`n")){ $t += "`n" }
  [System.IO.File]::WriteAllText($full, $t, $enc)
}

function Fail-Closed {
  param([string]$Reason, $Payload)

  # Policy A: market-aware as_of_date (US lane) for daily optimizer
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$rcRaw = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path (Split-Path -Parent $PSCommandPath) "Resolve-RunContext.ps1") -Market US
$rc = $null
try { $rc = $rcRaw | ConvertFrom-Json -ErrorAction Stop } catch { $rc = $null }
if(-not $rc){ Fail-Closed "phase7_runcontext_parse_fail" @{ market="US" } }
$today = ([string]$rc.as_of_date).Trim()
if(-not $today){ Fail-Closed "phase7_runcontext_asof_missing" @{ market="US" } }
  $tsUtc = (Get-Date).ToUniversalTime().ToString("o")

  # normalize payload arrays if present
  try {
    if($null -ne $Payload){
      if($Payload.ContainsKey("symbols") -and ($Payload["symbols"] -is [string])){
        $Payload["symbols"] = @([regex]::Split(($Payload["symbols"] + ""), "[,\s]+") | Where-Object { $_ -and $_.Trim() -ne "" })
      }
      if($Payload.ContainsKey("eligible") -and $null -eq $Payload["eligible"]){
        $Payload["eligible"] = @()
      }
    }
  } catch { }

  $out = [ordered]@{
    ts_utc    = $tsUtc
    as_of_date= $today
    ok        = $false
    reason    = $Reason
    payload   = $Payload
    weights   = @{}
    version   = "phase7.2"
  } | ConvertTo-Json -Depth 12

  Write-Utf8NoBom -Path $OutPath -Text $out
  Write-Host "[PHASE7] FAIL-CLOSED: $Reason" -ForegroundColor Yellow
  exit 2
}

trap {
  $msg  = ($_.Exception.Message + "")
  $line = ($_.InvocationInfo.ScriptLineNumber)
  $text = ($_.InvocationInfo.Line + "")
  Fail-Closed "phase7_unhandled_exception" @{ error=$msg; line=$line; text=$text }
}

function Invoke-BlockGReady {
  [CmdletBinding()]
  param([string]$Symbol)

  $s = (($Symbol + "")).Trim().ToUpperInvariant()
  $tok = @([regex]::Split($s, "[,\s]+") | Where-Object { $_ -and $_.Trim() -ne "" })
  if($tok.Count -ne 1){ return 2 }

  $t = $tok[0]
  if($t -notin @("NVDA","SPY","QQQ")){ return 2 }

  $checker = Join-Path (Split-Path -Parent $PSCommandPath) "Check-BlockGReady.ps1"

  # MUST be child process: checker may 'exit N' or write to stderr when not-ready
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $checker -Symbol $t -Market US -Mode BUILD_ONLY 2>$null | Out-Host
  $code = $LASTEXITCODE
  $ErrorActionPreference = $prev

  Write-Host ("[PHASE7] BlockG check sym={0} exit={1}" -f $t,$code)
  return $code
}

$blockgExitCache = @{}
function Get-BlockGExitCached([string]$sym){
  $k = ([string]$sym).Trim().ToUpperInvariant()
  if(-not $k){ return 2 }
  if($blockgExitCache.ContainsKey($k)){ return [int]$blockgExitCache[$k] }
  $rc = Invoke-BlockGReady -Symbol $k
  $blockgExitCache[$k] = [int]$rc
  return [int]$rc
}

# ---- MAIN ----
# Policy A: market-aware as_of_date (US lane) for daily optimizer
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$rcRaw = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path (Split-Path -Parent $PSCommandPath) "Resolve-RunContext.ps1") -Market US
$rc = $null
try { $rc = $rcRaw | ConvertFrom-Json -ErrorAction Stop } catch { $rc = $null }
if(-not $rc){ Fail-Closed "phase7_runcontext_parse_fail" @{ market="US" } }
$today = ([string]$rc.as_of_date).Trim()
if(-not $today){ Fail-Closed "phase7_runcontext_asof_missing" @{ market="US" } }
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")

# Env override (still fail-closed by default)
if(-not $Enable){
  $envOn = (([string]$env:HAT_PHASE7_ENABLE) + "").Trim()
  if($envOn -eq "1"){ $Enable = $true }
}
if (-not $Enable) { Fail-Closed "optimizer_disabled_failclosed" @{ enable=$false } }
if ($MaxWeight -le 0 -or $MaxWeight -gt 1) { Fail-Closed "invalid_max_weight" @{ MaxWeight=$MaxWeight } }

if (-not (Test-Path $StatePath))  { Fail-Closed "phase6_state_missing_failclosed" @{ StatePath=$StatePath } }
if (-not (Test-Path $BlockGPath)) { Fail-Closed "blockg_status_missing_failclosed" @{ BlockGPath=$BlockGPath } }

try { $s6 = Get-Content -Path $StatePath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { Fail-Closed "phase6_state_parse_fail" @{ StatePath=$StatePath } }
try { $bg = Get-Content -Path $BlockGPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { Fail-Closed "blockg_parse_fail" @{ BlockGPath=$BlockGPath } }
if (-not (Test-Path $MetricsPath)) { Fail-Closed "phase6_metrics_missing_failclosed" @{ MetricsPath=$MetricsPath } }
try { $m6 = Get-Content -Path $MetricsPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { Fail-Closed "phase6_metrics_parse_fail" @{ MetricsPath=$MetricsPath } }

$as6 = (($s6.as_of_date + "")).Substring(0,10)
$todayLocal = (Get-Date).ToString("yyyy-MM-dd")
$todayUtc   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
if($as6 -ne $todayLocal -and $as6 -ne $todayUtc){
  Fail-Closed "phase6_state_stale" @{ as_of_date=$s6.as_of_date; today_local=$todayLocal; today_utc=$todayUtc }
}
if (-not [bool]$s6.ok) { Fail-Closed "phase6_state_not_ok" @{ ok=$s6.ok; reason=$s6.reason } }

if (($bg.as_of_date + "").Substring(0,10) -ne $today) { Fail-Closed "blockg_stale" @{ as_of_date=$bg.as_of_date; today=$today } }

# Parse symbols deterministically
$raw = (($SymbolsRaw + "")).Trim().ToUpperInvariant()
$raw = [regex]::Replace($raw, "\p{Z}+", " ")
$raw = [regex]::Replace($raw, "\s+", " ")

$tmp = @()
$m = [regex]::Matches($raw, "(NVDA|SPY|QQQ)")
if($m.Count -gt 0){
  $seen=@{}
  foreach($x in $m){ if(-not $seen.ContainsKey($x.Value)){ $seen[$x.Value]=$true; $tmp += $x.Value } }
} else {
  foreach($t in [regex]::Split($raw, "[,\s]+")){
    $u = (($t + "")).Trim().ToUpperInvariant()
    if($u -ne ""){ $tmp += $u }
  }
}

[string[]]$SymbolList = $tmp
Write-Host ("[PHASE7] SymbolList_count=" + @($SymbolList).Count)
Write-Host ("[PHASE7] SymbolList=" + ($SymbolList -join ","))

if(-not $SymbolList -or @($SymbolList).Count -eq 0){
  Fail-Closed "no_symbols" @{ raw=$raw; symbols=@(); eligible=@() }
}

# Eligibility: BlockG ready AND Phase6 metrics evidence (Policy A realism)
$eligible_blockg = @()
foreach($s in @($SymbolList)){
  if((Get-BlockGExitCached $s) -eq 0){ $eligible_blockg += $s }
}

# metrics evidence map: symbol -> {rows, source_exists}
$rowsBy = @{}
try{
  if($m6 -and $m6.PSObject.Properties.Name -contains "phase6"){
    foreach($r in @($m6.phase6.symbols)){
      $sym = ([string]$r.symbol).ToUpperInvariant()
      $rows = 0
      $okSrc = $false
      try { $rows  = [int]$r.rows } catch { $rows = 0 }
      try { $okSrc = [bool]$r.source_exists } catch { $okSrc = $false }
      $rowsBy[$sym] = @{ rows=$rows; source_exists=$okSrc }
    }
  }
} catch { }

$eligible = @()
foreach($s in @($eligible_blockg)){
  $su = ([string]$s).ToUpperInvariant()
  if($rowsBy.ContainsKey($su)){
    $ri = $rowsBy[$su]
    if([bool]$ri.source_exists -and [int]$ri.rows -ge [int]$MinRows){
      $eligible += $su
    }
  }
}

if(-not $eligible -or @($eligible).Count -eq 0){
  Fail-Closed "no_eligible_symbols" @{ symbols=@($SymbolList); eligible=@($eligible); raw=$raw }
}

# Equal weights among eligible, cap, renormalize
$w = @{}
foreach($s in @($SymbolList)){ $w[$s] = 0.0 }

$base = 1.0 / [double]@($eligible).Count
foreach($s in @($eligible)){ $w[$s] = $base }

# Cap (do NOT renormalize  renorm cancels the cap). Remainder -> CASH.
$capped = @{}
$sum = 0.0
foreach($s in @($eligible)){
  $c = [Math]::Min([double]$w[$s], [double]$MaxWeight)
  $capped[$s] = $c
  $sum += $c
}
if($sum -le 0){ Fail-Closed "weights_sum_nonpositive_after_cap" @{ MaxWeight=$MaxWeight; eligible=@($eligible) } }

foreach($s in @($eligible)){ $w[$s] = [double]$capped[$s] }

$rem = 1.0 - [double]$sum
if($rem -gt 1e-12){
  $w["CASH"] = [double]$rem
}# Emit artifacts
# $repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)   # disabled (use env-first bootstrap repoRoot)
$fullOutDir = $OutDir
if (-not [System.IO.Path]::IsPathRooted($fullOutDir)) { $fullOutDir = Join-Path $repoRoot $OutDir }
if (-not (Test-Path $fullOutDir)) { New-Item -ItemType Directory -Force -Path $fullOutDir | Out-Null }

$weightsObj = [ordered]@{}
foreach($k in @($w.Keys)){ $weightsObj[$k] = [double]$w[$k] }

$out = [ordered]@{
  ts_utc     = $tsUtc
  as_of_date = $today
  ok         = $true
  reason     = "phase7_optimizer_ok"
  weights    = $weightsObj
  payload    = @{
    symbols  = @($SymbolList)
    eligible = @($eligible)
    raw      = $raw
    max_weight = [double]$MaxWeight
    min_weight = [double]$MinWeight
    phase6_state_path = $StatePath
    blockg_path = $BlockGPath
  }
  version    = "phase7.2"
} | ConvertTo-Json -Depth 12

# JSON outputs
Write-Utf8NoBom -Path (Join-Path $fullOutDir "phase7_weights.json") -Text $out
Write-Utf8NoBom -Path $OutPath -Text $out

# CSV outputs (NO BlockG-Ready function here; trust Invoke-BlockGReady)
$csvPath = Join-Path $fullOutDir "phase7_weights.csv"
$csv = @()
$csv += "as_of_date,symbol,weight,eligible,blockg_ready"
foreach($s in @($SymbolList)){
  $csv += ("{0},{1},{2},{3},{4}" -f $today,$s,[double]$w[$s],([bool](@($eligible) -contains $s)),([bool]((Get-BlockGExitCached $s) -eq 0)))
}
Write-Utf8NoBom -Path $csvPath -Text ($csv -join "`n")

Write-Host "[PHASE7] OK -> wrote outputs to $fullOutDir" -ForegroundColor Cyan
exit 0
