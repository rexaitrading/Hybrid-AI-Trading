[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA",

  
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "US",

  [ValidateSet("ALL_STRICT","SYMBOL_ONLY","BUILD_ONLY")]
  [string]$Mode = "ALL_STRICT",

  [switch]$Build
)
function Resolve-FullPath([string]$p){
  try {
    if([string]::IsNullOrWhiteSpace($p)){ return $p }
    $rp = Resolve-Path -LiteralPath $p -ErrorAction Stop
    return $rp.Path
  } catch {
    return $p
  }
}
# --- PATH BAN (institutional) ---
try {
  $pwdPath = (Get-Location).Path
  if($pwdPath -match '\?\?'){
    Write-Host ("[PATH] FAIL-CLOSED: banned token '??' in PWD => " + $pwdPath) -ForegroundColor Red
    exit 2
  }
} catch {
  Write-Host ("[PATH] FAIL-CLOSED: guard error => " + $_.Exception.Message) -ForegroundColor Red
  exit 2
}
# --- END PATH BAN ---

Set-StrictMode -Version Latest
# --- OUTPUT ENCODING (institutional) ---
try {
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [Console]::OutputEncoding = $utf8
  [Console]::InputEncoding  = $utf8
  $global:OutputEncoding    = $utf8
} catch { }
# --- END OUTPUT ENCODING ---
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
# --- CANONICALIZE repoRoot (institutional) ---
try {
  $rr = Resolve-Path -LiteralPath $repoRoot -ErrorAction Stop
  $repoRoot = $rr.Path
} catch {
  # keep original, but do not allow wildcard-like tokens
}
# --- END CANONICALIZE repoRoot ---

# --- logs roots (StrictMode-safe) ---
$logsDir = Join-Path $repoRoot "logs"
$logsDirOut = $null
try {
  $logsDirOut = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1") -Market $Market
} catch { $logsDirOut = $null }
# G_READY_LOGSDIROUT_FAILCLOSED_BEGIN
if(-not $logsDirOut){
  # Fail-closed: per-market contract must not bleed into root logs
  Fail-Contract ("market_log_root_missing market=" + (($Market + "")).Trim().ToUpperInvariant())
}
# G_READY_LOGSDIROUT_FAILCLOSED_END
# --- end logs roots ---


# --- Normalize symbol early (defensive, deterministic) ---
$s = ($Symbol + "").ToUpperInvariant()
if($s -notin @("NVDA","SPY","QQQ","ALL")){ Fail-Script ("Invalid -Symbol=" + $Symbol) }
# --- END normalize ---
function Write-Utf8NoBom {
  param([string]$Path, [string]$Text)
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n", "`n"
  if ($Text.Length -gt 0 -and $Text[-1] -ne "`n") { $Text += "`n" }
  [System.IO.File]::WriteAllText((Resolve-Path $Path).Path, $Text, $utf8NoBom)
}

function Read-Json {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { return $null }
  $raw = Get-Content -LiteralPath $Path -Encoding utf8 -Raw
  if (-not $raw) { return $null }
  return ($raw | ConvertFrom-Json -ErrorAction Stop)
}


function Dump-Reasons($st){
  try{
    if($st -and ($st.PSObject.Properties.Name -contains "reasons_not_ready")){
      $r = @($st.reasons_not_ready)

      # OPT_CLOSED_DAY_REASONS_FILTER_BEGIN
      # Optional clean: on closed-day diagnostic failure, print only operator-actionable reasons (no gating change).
      try {
        $head = ""
        if(Get-Variable -Name "__contract_fail_msg" -Scope Script -ErrorAction SilentlyContinue){
          $head = (($script:__contract_fail_msg + "")).Trim()
        }
        if($head -like "market_closed_today=true (diagnostic failed prerequisites)*"){
          $keep = New-Object System.Collections.Generic.List[string]
          $wl = @(
            "^market_closed_today",
            "^intel_ok_today",
            "^nvda_intel_ok_today",
            "^gatescore_ok_live_today",
            "^metrics_source_missing_for_symbol=",
            "^(nvda|spy|qqq)_blockg_ready=",
            "^ev_hard_"
          )
          foreach($x in @($r)){
            $t = (($x + "")).Trim()
            if(-not $t){ continue }
            foreach($p in $wl){ if($t -match $p){ $keep.Add($t) | Out-Null; break } }
          }
          # Always keep the headline first
          if($head){ $r = @($head) + @($keep) } else { $r = @($keep) }
        }
      } catch { }
      # OPT_CLOSED_DAY_REASONS_FILTER_END


      # DIAG: always include the contract failure headline as a reason (if present)
      try {
        if(Get-Variable -Name "__contract_fail_msg" -Scope Script -ErrorAction SilentlyContinue){
          $m = (($script:__contract_fail_msg + "")).Trim()
          if($m){ $r = @($m) + @($r) }
        }
      } catch { }


      # SYMBOL_ONLY: filter out other-symbol contamination + strict-all reasons
      if(($mode + "") -eq "SYMBOL_ONLY"){
        $sym = ($s + "")
        $r2 = @()
        foreach($x in $r){
          $t = ($x + "")
          if($t -match 'metrics_source_missing_for_symbol='){ continue }
          if($t -match '^strict_option_b_blocks_spy_qqq='){ continue }
          # keep only reasons clearly about this symbol OR global daily fields
          if($t -match '(^phase23_|^phase4_|^ev_hard_|^gatescore_|^intel_|^market_closed_|^crisis_|^global_ready_|^market_dna_|^edge_validity_|^dependency_risk_|^risk_guard_|^nvda_blockg_ready=|^spy_blockg_ready=|^qqq_blockg_ready=)'){
            # if a per-symbol ready flag appears, keep only if matches requested symbol
            if($t -match '^(nvda|spy|qqq)_blockg_ready='){
              if($sym -eq "NVDA" -and $t -match '^nvda_'){ $r2 += $t; continue }
              if($sym -eq "SPY"  -and $t -match '^spy_'){  $r2 += $t; continue }
              if($sym -eq "QQQ"  -and $t -match '^qqq_'){  $r2 += $t; continue }
              continue
            }
            $r2 += $t
          }
        }
        $r = $r2
      }

      # DERIVE_REASONS_FROM_FIELDS_BEGIN
      # Diagnostic-only: if stub fields indicate failed gates but reasons_not_ready is sparse,
      # emit derived reasons so operator can act. Does NOT change gating.
      try {
        $extra = New-Object System.Collections.Generic.List[string]
        function _Add([string]$x){ if($x){ $extra.Add($x) | Out-Null } }

        if($st.PSObject.Properties.Name -contains "global_ready_ok_today"){
          if(-not [bool]$st.global_ready_ok_today){ _Add "global_ready_ok_today=false" }
        }
        foreach($k in @("market_dna_ok_today","edge_validity_ok_today","dependency_risk_ok_today","risk_guard_ok_today")){
          try {
            if($st.PSObject.Properties.Name -contains $k){ if(-not [bool]$st.$k){ _Add ($k + "=false") } }
          } catch { }
        }

        if($st.PSObject.Properties.Name -contains "intel_ok_today"){ if(-not [bool]$st.intel_ok_today){ _Add "intel_ok_today=false" } }
        if($st.PSObject.Properties.Name -contains "nvda_intel_ok_today"){ if(-not [bool]$st.nvda_intel_ok_today){ _Add "nvda_intel_ok_today=false" } }

        if($st.PSObject.Properties.Name -contains "gatescore_ok_live_today"){
          if(-not [bool]$st.gatescore_ok_live_today){ _Add "gatescore_ok_live_today=false" }
        }

        # merge extras (dedup) into $r
        if($extra.Count -gt 0){
          $seen2 = @{}
          foreach($x in @($r)){ $s=($x+""); if($s){ $seen2[$s]=1 } }
          foreach($x in $extra){ $s=($x+""); if($s -and (-not $seen2.ContainsKey($s))){ $r += $s; $seen2[$s]=1 } }
        }
      } catch { }
      # DERIVE_REASONS_FROM_FIELDS_END

      if($r -and $r.Count -gt 0){
        Write-Host "[BLOCKG] reasons_not_ready:" -ForegroundColor DarkYellow
        foreach($x in $r){
          Write-Host ("[BLOCKG]  - " + ($x + "")) -ForegroundColor DarkYellow
        }
      }
    }
  } catch { }
}function Fail-Contract([string]$Msg) {
  # DIAG: capture contract fail headline for reasons output (StrictMode-safe)
  $script:__contract_fail_msg = ($Msg + "")
  Write-Host "[BLOCKG] NOT READY: $Msg" -ForegroundColor Red
  try { Dump-Reasons $st } catch { }
  exit 2
}


function Fail([string]$Msg) {
  # Backward-compatible shim: treat any Fail() usage as contract failure (exit 2)
  Fail-Contract $Msg
}
function Fail-Script([string]$Msg) {
  Write-Host "[BLOCKG] ERROR: $Msg" -ForegroundColor Yellow
  exit 1
}

# --- Mode normalization ---
$mode = (($Mode + "")).Trim().ToUpperInvariant()
if($mode -notin @("ALL_STRICT","SYMBOL_ONLY","BUILD_ONLY")){ Fail-Script ("Invalid -Mode=" + $Mode) }
if($s -eq "ALL" -and $mode -eq "SYMBOL_ONLY"){ Fail-Script "Invalid combination: -Symbol ALL with -Mode SYMBOL_ONLY" }
# --- END Mode normalization ---

# NONLIVE_ONLY_NONUS_BEGIN
# Policy: non-US markets are NON-LIVE only until JP-native LIVE minima + evidence exist.
# Fail-closed: deny LIVE for non-US regardless of other gates.
$mkt = (($Market + "")).Trim().ToUpperInvariant()
 $runMode = (($env:HAT_MODE + "")).Trim().ToUpperInvariant()
if($runMode -eq "LIVE" -and $mkt -ne "US"){
  Fail-Contract ("nonlive_only_market market=" + $mkt)
}
# NONLIVE_ONLY_NONUS_END


# 1) Optional build step (single semantic owner)
if ($Build) {
  $builder = Join-Path $toolsDir "Build-BlockGStatusStub.ps1"
  if (-not (Test-Path -LiteralPath $builder)) { Fail "Missing builder: $builder" }

  Write-Host "[BLOCKG] Build requested: running Build-BlockGStatusStub.ps1" -ForegroundColor Cyan
  $psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
  & $psExe -NoProfile -ExecutionPolicy Bypass -Command "& '$builder' -Symbol '$Symbol'" *>&1 | Out-Host
  if ($LASTEXITCODE -ne 0) { Fail "Build-BlockGStatusStub.ps1 failed exit=$LASTEXITCODE" }
}

# 2) Load contract JSON (contract-only validation)
# Phase-5: per-market logs root (default US). Env override always wins.
$defaultPath = $null
try {
  $mr = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1") -Market $Market
  if($mr){ $defaultPath = Join-Path $mr "blockg_status_stub.json" }
} catch { }
if(-not $defaultPath){ $defaultPath = Join-Path $repoRoot "logs\blockg_status_stub.json" }
$statusPath = $env:HAT_BLOCKG_STATUS_PATH
if (-not $statusPath) { $statusPath = $defaultPath }

# --- CANONICALIZE + BAN statusPath (institutional) ---
$statusPath = Resolve-FullPath $statusPath
if(($statusPath + "") -match "\?\?"){
  Write-Host ("[PATH] FAIL-CLOSED: banned token '??' in statusPath => " + $statusPath) -ForegroundColor Red
  exit 2
}
# --- END CANONICALIZE + BAN statusPath ---
$st = Read-Json $statusPath
# CRISIS_VETO_BEGIN
# Institutional: crisis regime veto is highest priority. Deny before any other gates.
try{
  if($st -and ($st.PSObject.Properties.Name -contains "crisis_regime") -and [bool]$st.crisis_regime){
    Fail-Contract "crisis_regime=true"
  }
} catch {
  Fail-Contract "crisis_regime check failed"
}
# CRISIS_VETO_END
# CRASHMODE_FLATTEN_GATE_BEGIN
# Institutional: if crisis_regime=true, require flatten evidence ok=true (defense-in-depth).
try{
  if($st -and ($st.PSObject.Properties.Name -contains "crisis_regime") -and [bool]$st.crisis_regime){
    if(-not ($st.PSObject.Properties.Name -contains "crashmode_flatten_ok")){ Fail-Contract "missing crashmode_flatten_ok" }
    if(-not [bool]$st.crashmode_flatten_ok){ Fail-Contract "crashmode_flatten_ok=false" }
  }
} catch {
  Fail-Contract "crashmode flatten gate failed"
}
# CRASHMODE_FLATTEN_GATE_END

# REGIME_VETO_BEGIN
# Institutional: explicit regime gating (fail-closed). CRISIS defaults to protect capital.
try{
  $rg = ""
  if($st -and ($st.PSObject.Properties.Name -contains "regime")){ $rg = [string]$st.regime }
  if(-not $rg){ Fail-Contract "regime missing" }
  $rg = $rg.ToUpper().Trim()
  if($rg -notin @("NORMAL","HIGH_VOL","CRISIS")){ Fail-Contract ("invalid regime=" + $rg) }

  if($rg -eq "CRISIS"){
    $allowAlpha = $false
    try { if($st.PSObject.Properties.Name -contains "crisis_alpha_enabled"){ $allowAlpha = [bool]$st.crisis_alpha_enabled } } catch { $allowAlpha = $false }
    if(-not $allowAlpha){ Fail-Contract "regime=CRISIS (alpha disabled)" }

    $need = @(
      "crisis_alpha_replay_evidence.json",
      "slippage_stress_status.json",
      "regime_risk_caps.json",
      "kill_switch_status.json"
    )
    foreach($fn in $need){
      $p = Join-Path $logsDir $fn
      if(-not (Test-Path -LiteralPath $p)){ Fail-Contract ("crisis alpha missing " + $fn) }
      $j = Read-Json $p
      if(-not $j){ Fail-Contract ("crisis alpha unreadable " + $fn) }
      if(-not ($j.PSObject.Properties.Name -contains "ok")){ Fail-Contract ("crisis alpha missing ok in " + $fn) }
      if(-not [bool]$j.ok){ Fail-Contract ("crisis alpha ok=false in " + $fn) }
    }
  }
} catch {
  Fail-Contract "regime gate failed"
}
# REGIME_VETO_END


# --- CONTRACT SEMANTICS LEVEL (fail-closed) ---
if ($st) {
  try {
    $sem = ""
    if($st.PSObject.Properties.Name -contains "contract_semantics_level"){ $sem = [string]$st.contract_semantics_level }
    if(-not $sem){ $sem = "UNKNOWN" }
    if($sem -ne "FULL_LIVE_ELIGIBLE"){
      Fail ("contract_semantics_level=" + $sem)
    }
  } catch {
    Fail "contract_semantics_level check failed"
  }
}
# --- END CONTRACT SEMANTICS LEVEL ---

# --- EV-hard date clarity (audit-only; contract semantics unchanged) ---
if($st){
  if($st.PSObject.Properties.Name -contains "ev_hard_daily_as_of_date"){
    Write-Host ("[BLOCKG] ev_hard_daily_as_of_date=" + [string]$st.ev_hard_daily_as_of_date) -ForegroundColor DarkGray
  }
  if($st.PSObject.Properties.Name -contains "ev_hard_session_as_of_date"){
    Write-Host ("[BLOCKG] ev_hard_session_as_of_date=" + [string]$st.ev_hard_session_as_of_date) -ForegroundColor DarkGray
  }
}

# --- BUILD_ONLY: allow producers to run (do not require LIVE readiness) ---
if(($mode + "") -eq "BUILD_ONLY"){
  foreach($k in @("phase4_ok_today","phase23_health_ok_today")){
    if(-not ($st.PSObject.Properties.Name -contains $k)){ Fail ("Missing field: " + $k) }
  }
  Write-Host ("[BLOCKG] BUILD_ONLY OK: contract loaded; LIVE readiness not enforced (Symbol=" + $Symbol + ")") -ForegroundColor Yellow
  exit 0
}
# --- END BUILD_ONLY ---

# MARKET_SESSION_GATE_BEGIN
# Phase-5: market session gate via Resolve-RunContext (single truth).
# Policy:
# - If market_closed_today=true => closed-day branch handles diagnostic exit=10 (existing behavior).
# - If open day and Mode=ALL_STRICT => require session_name == "RTH" (deny pre/open/lunch/afterclose).
try {
  $asOf = ""
  if($st -and ($st.PSObject.Properties.Name -contains "as_of_date")){
    $asOf = [string]$st.as_of_date
    if($asOf.Length -ge 10){ $asOf = $asOf.Substring(0,10) }
  }

  $rcPath = Join-Path $repoRoot "tools\Resolve-RunContext.ps1"
  if(Test-Path -LiteralPath $rcPath){
    $rcArgs = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$rcPath,"-Market",$Market,"-Symbol",$Symbol)
    if(($asOf + "").Trim()){ $rcArgs += @("-AsOfDate",$asOf) }

    $rcRaw = & powershell @rcArgs 2>$null | Out-String
    $rcRaw = ($rcRaw + "").Trim()
    if($rcRaw){
      $ix0 = $rcRaw.IndexOf('{')
      $ix1 = $rcRaw.LastIndexOf('}')
      if($ix0 -ge 0 -and $ix1 -gt $ix0){
        $rcJson = $rcRaw.Substring($ix0, ($ix1 - $ix0 + 1))
        $rc = $rcJson | ConvertFrom-Json -ErrorAction Stop

        if($rc -and (-not [bool]$rc.market_closed_today)){
          if(($mode + "") -eq "ALL_STRICT"){
            $sn = ([string]$rc.session_name).Trim().ToUpperInvariant()
            if($sn -ne "RTH"){
              Fail-Contract ("market_session_not_rth session_name=" + [string]$rc.session_name)
            }
          }
        }
      }
    }
  }
} catch { }
# MARKET_SESSION_GATE_END


# MARKET_CLOSED_FAILCLOSED_CHECK_BEGIN
# Institutional clarity: when market is closed we fail-closed with an explicit operator message.
try {
  if ($st -and ($st.PSObject.Properties.Name -contains "market_closed_today") -and [bool]$st.market_closed_today) {
    # MARKET_CLOSED_PRINT_PROXY_VETO_BEGIN
    try {
      if ($st.PSObject.Properties.Name -contains "gatescore_metrics_source") {
        $ms = ([string]$st.gatescore_metrics_source).Trim()
        if ($ms -match "^(?i)proxy_") {
          Write-Host ("[BLOCKG] NOTE: gatescore_metrics_source_disallowed_for_live=" + $ms) -ForegroundColor Yellow
        }
      }
    } catch { }
    # MARKET_CLOSED_PRINT_PROXY_VETO_END

    # Closed-day diagnostic policy:
    # - LIVE is ALWAYS disallowed on closed days.
    # - DIAGNOSTIC OK (exit=10) requires: Phase4 ok + Phase23 ok + GateScore recent-enough + EV-hard evidence exists.
    # - We do NOT require gatescore_fresh_today or ev_hard_daily_ok_today on a closed day.
    $diagOk = $true

  # INTEL_CHECK_BEGIN
  try{
    $intelOk = $false
    if($st.PSObject.Properties.Name -contains "intel_ok_today"){ $intelOk = [bool]$st.intel_ok_today }
    $symIntelOk = $intelOk
    if($s -eq "NVDA" -and ($st.PSObject.Properties.Name -contains "nvda_intel_ok_today")){
      $symIntelOk = [bool]$st.nvda_intel_ok_today
    }

    if(-not $symIntelOk){
      $diagOk = $false
      $why += "intel_not_ok_today"
    }
  } catch {
    $diagOk = $false
    $why += "intel_check_exception"
  }
  # INTEL_CHECK_END
    # 1) Core producers
    if (-not ($st.PSObject.Properties.Name -contains "phase4_ok_today") -or (-not [bool]$st.phase4_ok_today)) { $diagOk = $false }
    # A3_DIAG_POLICYB_ACCEPT_BEGIN
    # Policy B diagnostic: if status explicitly says not_evaluated_market_closed=true, treat as diagnostic-ok for prerequisites (LIVE remains denied).
    $p23NotEval = $false
    $evNotEval  = $false
    try { if($st.PSObject.Properties.Name -contains "not_evaluated_market_closed"){ $p23NotEval = [bool]$st.not_evaluated_market_closed } } catch { $p23NotEval = $false }
    try { if($st.PSObject.Properties.Name -contains "ev_hard_not_evaluated_market_closed"){ $evNotEval = [bool]$st.ev_hard_not_evaluated_market_closed } } catch { $evNotEval = $false }
    # A3_DIAG_POLICYB_ACCEPT_END
    if (-not ($st.PSObject.Properties.Name -contains "phase23_health_ok_today") -or (-not [bool]$st.phase23_health_ok_today)) { $diagOk = $false }

    # 2) GateScore age policy (fields already in contract)
    if (-not ($st.PSObject.Properties.Name -contains "gatescore_recent_enough") -or (-not [bool]$st.gatescore_recent_enough)) { $diagOk = $false }
    $maxAgeDays = 3  # closed-day local constant (StrictMode-safe)
    try { $age = [int]$st.gatescore_age_days } catch { $diagOk = $false }
    if ($diagOk -and ($age -gt $maxAgeDays)) { $diagOk = $false }

    # 3) EV-hard evidence exists (session ok OR explicitly not-evaluated because market closed OR has daily as-of)
    $evEvidenceOk = $false
    try {
      if (($st.PSObject.Properties.Name -contains "ev_hard_session_ok") -and [bool]$st.ev_hard_session_ok) { $evEvidenceOk = $true }
      elseif (($st.PSObject.Properties.Name -contains "ev_hard_not_evaluated_market_closed") -and [bool]$st.ev_hard_not_evaluated_market_closed) { $evEvidenceOk = $true }
      elseif (($st.PSObject.Properties.Name -contains "ev_hard_daily_as_of_date") -and ([string]$st.ev_hard_daily_as_of_date).Trim() -ne "") { $evEvidenceOk = $true }
    } catch { $evEvidenceOk = $false }
    if (-not $evEvidenceOk) { $diagOk = $false }

    if ($diagOk) {
      Write-Host "[BLOCKG] CLOSED DAY: DIAGNOSTIC OK (pipeline healthy; LIVE remains disallowed)" -ForegroundColor Yellow
      # GS_LIVE_STATUS_NOTE_CLOSED_BEGIN
      try {
        if(($st.PSObject.Properties.Name -contains "gatescore_ok_today") -and ($st.PSObject.Properties.Name -contains "gatescore_ok_live_today")){
          if([bool]$st.gatescore_ok_today -and (-not [bool]$st.gatescore_ok_live_today)){
            Write-Host "[BLOCKG] NOTE: GateScore passes diagnostic thresholds but FAILS LIVE thresholds (insufficient samples/edge for live)" -ForegroundColor Yellow
          }
        }
      } catch { }
      # GS_LIVE_STATUS_NOTE_CLOSED_END
      exit 10
    }

    Fail "market_closed_today=true (diagnostic failed prerequisites)"
  }
} catch { }
# MARKET_CLOSED_FAILCLOSED_CHECK_END
if (-not $st) { Fail "Missing/invalid Block-G status JSON at: $statusPath" }



# --- GateScore session-age policy (contract-only; do not recompute) ---
$MAX_GS_AGE_DAYS = 3
# 3A) Per-symbol GateScore validation (contract-only)
function Get-GS([string]$sym){
  if(-not ($st.PSObject.Properties.Name -contains "gatescore_by_symbol")){ return $null }
  $gsb = $st.gatescore_by_symbol
  if($null -eq $gsb){ return $null }
  $k = $sym.ToUpperInvariant()
  if(-not ($gsb.PSObject.Properties.Name -contains $k)){ return $null }
  return $gsb.$k
}

# 3) Validate required daily quality fields (fail-closed)
# NOTE: contract defines these booleans (default false if absent)
$reqFields = @(
  "regime_ok_today",
  "regime",
  "crisis_ok_today",
  "global_ready_ok_today",
  "market_dna_ok_today",
  "edge_validity_ok_today",
  "dependency_risk_ok_today",
  "risk_guard_ok_today",
  "phase4_ok_today",
  "ev_hard_daily_ok_today",
  "gatescore_fresh_today"
)

foreach ($k in $reqFields) {
  if (-not ($st.PSObject.Properties.Name -contains $k)) { Fail "Missing field: $k" }
  if (-not [bool]$st.$k) { Fail "$k=false" }
}


# GS_LIVE_STATUS_NOTE_BEGIN
try {
  if($st -and ($st.PSObject.Properties.Name -contains "gatescore_ok_today") -and ($st.PSObject.Properties.Name -contains "gatescore_ok_live_today")){
    if([bool]$st.gatescore_ok_today -and (-not [bool]$st.gatescore_ok_live_today)){
      Write-Host "[BLOCKG] NOTE: GateScore passes diagnostic thresholds but FAILS LIVE thresholds (insufficient samples/edge for live)" -ForegroundColor Yellow
    }
  }
} catch { }
# GS_LIVE_STATUS_NOTE_END

# GateScore age policy (fail-closed)
if (-not [bool]$st.gatescore_recent_enough) { Fail "gatescore_recent_enough=false" }
try { $age = [int]$st.gatescore_age_days } catch { Fail "gatescore_age_days invalid" }
if ($age -gt $MAX_GS_AGE_DAYS) { Fail ("gatescore_age_days=" + $age + " max=" + $MAX_GS_AGE_DAYS) }
# Per-symbol GateScore checks (contract-only)
# OPTIONAL_GATESCORE_BY_SYMBOL_POLICY_BEGIN
# Policy:
# - If contract contains per-symbol *_blockg_ready keys, then gatescore_by_symbol is OPTIONAL and we DO NOT
#   dereference per-symbol GateScore objects (avoids StrictMode property-not-found).
# - If *_blockg_ready keys are absent, we require gatescore_by_symbol.<SYM> (legacy behavior).
function Has-SymReadyKey([string]$sym){
  $k = ($sym.ToLowerInvariant() + "_blockg_ready")
  return ($st -and ($st.PSObject.Properties.Name -contains $k))
}

$hasGsb = ($st.PSObject.Properties.Name -contains "gatescore_by_symbol")
$hasAnyReadyKey = (Has-SymReadyKey "NVDA") -or (Has-SymReadyKey "SPY") -or (Has-SymReadyKey "QQQ")
$requireGsb = (-not $hasAnyReadyKey)

# GateScore object checks (only when present OR required)
if($hasGsb){
  if ($s -ne "ALL") {
    $gs = Get-GS $s
    if (-not $gs) {
      $k = ($s.ToLowerInvariant() + "_blockg_ready")
      if (-not ($st.PSObject.Properties.Name -contains $k)) { Fail ("Missing gatescore_by_symbol." + $s) }
      # Contract has *_blockg_ready => gatescore_by_symbol optional; skip deref of $gs.*
    }
    if((-not [bool]$gs.samples_ok) -or (-not [bool]$gs.threshold_ok)){
      $msg = "$s gatescore "
      $msg += "samples_ok=$([bool]$gs.samples_ok) "
      $msg += "threshold_ok=$([bool]$gs.threshold_ok) "
      $msg += "cnt=$($gs.count_signals) min_cnt=$($gs.min_signals) "
      $msg += "pnl=$($gs.pnl_samples) min_pnl=$($gs.min_pnl_samples) "
      $msg += "edge=$($gs.mean_edge_ratio) min_edge=$($gs.min_edge_ratio) "
      $msg += "micro=$($gs.mean_micro_score) min_micro=$($gs.min_micro_score)"
      Fail $msg
    }
  } else {
    foreach($sym in @("NVDA","SPY","QQQ")) {
      $gs = Get-GS $sym
      if (-not $gs) {
        $k = ($sym.ToLowerInvariant() + "_blockg_ready")
        if (-not ($st.PSObject.Properties.Name -contains $k)) { Fail ("Missing gatescore_by_symbol." + $sym) }
        # Contract has *_blockg_ready => gatescore_by_symbol optional; skip deref of $gs.*
      }
      if((-not [bool]$gs.samples_ok) -or (-not [bool]$gs.threshold_ok)){
        $msg = "$sym gatescore "
        $msg += "samples_ok=$([bool]$gs.samples_ok) "
        $msg += "threshold_ok=$([bool]$gs.threshold_ok) "
        $msg += "cnt=$($gs.count_signals) min_cnt=$($gs.min_signals) "
        $msg += "pnl=$($gs.pnl_samples) min_pnl=$($gs.min_pnl_samples) "
        $msg += "edge=$($gs.mean_edge_ratio) min_edge=$($gs.min_edge_ratio) "
        $msg += "micro=$($gs.mean_micro_score) min_micro=$($gs.min_micro_score)"
        Fail $msg
      }
    }
  }
} elseif($requireGsb) {
  # Legacy fail-closed: no *_blockg_ready keys to trust, so gatescore_by_symbol is required.
  if ($s -ne "ALL") { Fail ("Missing gatescore_by_symbol." + $s) }
  foreach($sym in @("NVDA","SPY","QQQ")) { Fail ("Missing gatescore_by_symbol." + $sym) }
}
# OPTIONAL_GATESCORE_BY_SYMBOL_POLICY_END

# 4) Per-symbol readiness (fail-closed)
function SymReady([string]$sym) {
  $key = ($sym.ToLower() + "_blockg_ready")
  if (-not ($st.PSObject.Properties.Name -contains $key)) { return $false }
  return [bool]$st.$key
}
# $s normalized earlier
if ($s -eq "ALL") {
  foreach ($sym in @("NVDA","SPY","QQQ")) {
    if (-not (SymReady $sym)) { Fail "$sym not ready ($($sym.ToLower())_blockg_ready=false)" }
  }
} else {
  if (-not (SymReady $s)) { Fail "$s not ready ($($s.ToLower())_blockg_ready=false)" }
}
Write-Host ("[BLOCKG] READY: Symbol={0} StatusFile={1}" -f $Symbol,(Split-Path -Leaf $statusPath)) -ForegroundColor Green
exit 0
