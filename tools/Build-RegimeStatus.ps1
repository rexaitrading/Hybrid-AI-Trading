# --- Canonical repo root (deterministic; caller/CWD independent) ---



[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA",

  [ValidateSet("US","JP","HK","HK_SH","HK_SZ","SG","IN","KR","TW")]
  [string]$Market = "US",

  [int]$WindowBars = 180,
  [double]$HighVolStd = 0.004
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n","`n"
  if($Text.Length -gt 0 -and $Text[-1] -ne "`n"){ $Text += "`n" }
  [System.IO.File]::WriteAllText($Path,$Text,$utf8)
}

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $toolsDir)).Path
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

# RUNCONTEXT_READ_BEGIN
$asOfParam = ""
try { $asOfParam = "" } catch { $asOfParam = "" }
try { if(($env:HAT_ASOF_DATE + "") -ne ""){ $asOfParam = ($env:HAT_ASOF_DATE + "") } } catch { }

$rcSym = ($Symbol -replace '^ALL$','NVDA')
$rc = $null
try {
  $psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
  $rcRaw = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Resolve-RunContext.ps1") -Market $Market -Symbol $rcSym 2>$null | Out-String
  $rcRaw = ($rcRaw + "").Trim()
  if($rcRaw){ $rc = $rcRaw | ConvertFrom-Json -ErrorAction Stop } else { $rc = $null }
} catch { $rc = $null }
# Fail-closed defaults
# A3_REGIME_NO_LOCAL_ASOF_BEGIN
$rc_as_of_date = (($env:HAT_AS_OF_DATE + "")).Trim()
if(-not $rc_as_of_date){ $rc_as_of_date = (($env:HAT_ASOF_DATE + "")).Trim() }  # legacy
if(-not $rc_as_of_date){ $rc_as_of_date = "" }  # remain empty if RC unreadable -> regime_ok_today fails later
# A3_REGIME_NO_LOCAL_ASOF_END
$rc_as_of_date_source = "local_fallback"
$rc_market_closed_today = $true
$rc_market_closed_reason = "unknown"
$rc_is_open_now = $false
$rc_session_name = "CLOSED"
$rc_is_trading_day = $false

if($rc){
  try {
    if($rc.PSObject.Properties.Name -contains "as_of_date"){ $rc_as_of_date = [string]$rc.as_of_date }
    if($rc.PSObject.Properties.Name -contains "as_of_date_source"){ $rc_as_of_date_source = [string]$rc.as_of_date_source }
    if($rc.PSObject.Properties.Name -contains "market_closed_today"){ $rc_market_closed_today = [bool]$rc.market_closed_today }
    if($rc.PSObject.Properties.Name -contains "market_closed_reason"){ $rc_market_closed_reason = [string]$rc.market_closed_reason }
    if($rc.PSObject.Properties.Name -contains "is_open_now"){ $rc_is_open_now = [bool]$rc.is_open_now }
    if($rc.PSObject.Properties.Name -contains "session_name"){ $rc_session_name = [string]$rc.session_name }
    if($rc.PSObject.Properties.Name -contains "is_trading_day"){ $rc_is_trading_day = [bool]$rc.is_trading_day }
  } catch { }
} else {
  # If RunContext is unreadable, regime_ok_today should fail-closed later.
  $rc_market_closed_today = $true
  $rc_is_open_now = $false
  $rc_session_name = "CLOSED"
  $rc_is_trading_day = $false
}
# RUNCONTEXT_READ_END


# RUNCONTEXT_REGIME_BEGIN
function Read-RunContextSafe([string]$RepoRoot,[string]$Market,[string]$Symbol,[string]$AsOfDate){
  $rcPath = Join-Path $RepoRoot "tools\Resolve-RunContext.ps1"
  if(-not (Test-Path -LiteralPath $rcPath)){ return $null }

  $psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"

  $tmpDir = Join-Path $env:TEMP ("hat_rc_" + (Get-Date).ToString("yyyyMMdd_HHmmssfff"))
  try { New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null } catch { return $null }
  $outFile = Join-Path $tmpDir "out.txt"
  $errFile = Join-Path $tmpDir "err.txt"

  $argList = @("-NoProfile","-NonInteractive","-ExecutionPolicy","Bypass","-File",$rcPath,"-Market",$Market,"-Symbol",$Symbol)
  if((($AsOfDate + "")).Trim()){ $argList += @("-AsOfDate",$AsOfDate) }

  try {
    $p = Start-Process -FilePath $psExe -ArgumentList $argList -NoNewWindow -Wait -PassThru -RedirectStandardOutput $outFile -RedirectStandardError $errFile
  } catch { return $null }

  $out = ""
  $err = ""
  try { if(Test-Path -LiteralPath $outFile){ $out = Get-Content -LiteralPath $outFile -Raw -Encoding UTF8 } } catch { }
  try { if(Test-Path -LiteralPath $errFile){ $err = Get-Content -LiteralPath $errFile -Raw -Encoding UTF8 } } catch { }

  $rawAll = (($out + "`n" + $err) + "").Trim()

# breadcrumb always (proves rc path + rawAll length)
try {
# [A3_DISABLED]   $dbg = Join-Path $RepoRoot "logs\US\_runcontext_seen_always.txt"
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dbg) | Out-Null
  $msg = "ts_utc=" + (Get-Date).ToUniversalTime().ToString("o") + "`n" +
         "rcPath=" + $rcPath + "`n" +
         "exit=" + $p.ExitCode + "`n" +
         "outLen=" + (($out + "").Length) + "`n" +
         "errLen=" + (($err + "").Length) + "`n" +
         "rawLen=" + (($rawAll + "").Length) + "`n"
  [System.IO.File]::WriteAllText($dbg, $msg, (New-Object System.Text.UTF8Encoding($false)))
} catch { }if(-not $rawAll){
    try {
# [A3_DISABLED]       $dbg = Join-Path $RepoRoot "logs\US\_runcontext_capture_last.txt"
      New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dbg) | Out-Null
      [System.IO.File]::WriteAllText($dbg, ("EMPTY rawAll; exit=" + $p.ExitCode), (New-Object System.Text.UTF8Encoding($false)))
    } catch { }
    return $null
  }

  $i0 = $rawAll.IndexOf('{')
  $i1 = $rawAll.LastIndexOf('}')
  if($i0 -lt 0 -or $i1 -le $i0){
    try {
# [A3_DISABLED]       $dbg = Join-Path $RepoRoot "logs\US\_runcontext_capture_last.txt"
      New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dbg) | Out-Null
      [System.IO.File]::WriteAllText($dbg, ("NO JSON; exit=" + $p.ExitCode + "
" + $rawAll), (New-Object System.Text.UTF8Encoding($false)))
    } catch { }
    return $null
  }

  $json = $rawAll.Substring($i0, ($i1 - $i0 + 1))
  try { return ($json | ConvertFrom-Json -ErrorAction Stop) } catch {
    try {
# [A3_DISABLED]       $dbg = Join-Path $RepoRoot "logs\US\_runcontext_capture_last.txt"
      New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dbg) | Out-Null
      [System.IO.File]::WriteAllText($dbg, ("JSON PARSE FAIL; exit=" + $p.ExitCode + "
" + $rawAll), (New-Object System.Text.UTF8Encoding($false)))
    } catch { }
    return $null
  }
}
# RUNCONTEXT_REGIME_END
# Per-market log root
$logsDirOut = $null
try {
  $logsDirOut = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1") -Market $Market
} catch { $logsDirOut = $null }
# A3_REGIME_LOGSDIR_OUT_BEGIN
# Fallback-only: never overwrite per-market logsDirOut when Get-MarketLogRoot succeeded.
$envOut = (($env:HAT_LOGS_DIR_OUT + "")).Trim()
$envDir = (($env:HAT_LOGS_DIR + "")).Trim()
if(-not $logsDirOut){
  if($envOut){ $logsDirOut = $envOut }
  elseif($envDir){ $logsDirOut = $envDir }
  if(-not $logsDirOut){
    try { $logsDirOut = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1") -Market $Market } catch { $logsDirOut = $null }
    $logsDirOut = (($logsDirOut + "")).Trim()
  }
}
if(-not $logsDirOut){ $logsDirOut = Join-Path (Join-Path $repoRoot "logs") $Market }
# A3_REGIME_LOGSDIR_OUT_END
New-Item -ItemType Directory -Force -Path $logsDirOut | Out-Null

# 1) Crisis producer is authoritative for CRISIS
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$crisisProd = Join-Path $toolsDir "Build-CrisisRegimeStatus.ps1"
if(-not (Test-Path -LiteralPath $crisisProd)){ throw "Missing: $crisisProd" }
  $symCrisis = $Symbol
  if($symCrisis -eq "ALL"){ $symCrisis = "NVDA" }
  $oldHatMarket = $env:HAT_MARKET
  $oldHatOut = $env:HAT_LOGS_DIR_OUT
  $oldHatDir = $env:HAT_LOGS_DIR
  try {
    $env:HAT_MARKET = $Market
    $env:HAT_LOGS_DIR_OUT = $logsDirOut
    $env:HAT_LOGS_DIR = $logsDirOut
    & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $crisisProd -Symbol $symCrisis 2>&1 | Out-Host
  } finally {
    $env:HAT_MARKET = $oldHatMarket
    $env:HAT_LOGS_DIR_OUT = $oldHatOut
    $env:HAT_LOGS_DIR = $oldHatDir
  }
if($LASTEXITCODE -ne 0){ throw "Build-CrisisRegimeStatus failed exit=$LASTEXITCODE" }

$crisisPath = Join-Path $logsDirOut "crisis_regime_status.json"
if(-not (Test-Path -LiteralPath $crisisPath)){
  # fallback to legacy logs if producer wrote there
  # FAIL-CLOSED: do not fall back to other markets for crisis status
}
if(-not (Test-Path -LiteralPath $crisisPath)){ throw "Missing crisis status: $crisisPath" }

$cr = Get-Content -LiteralPath $crisisPath -Raw -Encoding UTF8 | ConvertFrom-Json
$crisis = $false
try { if($cr.PSObject.Properties.Name -contains "crisis_regime"){ $crisis = [bool]$cr.crisis_regime } } catch {}

# 2) Regime classification
$regime = "NORMAL"
$reason = "default_normal"
$rvStd = $null

if($crisis){
  $regime = "CRISIS"
  $reason = "crisis_regime_true"
} else {
  $sym = ($Symbol -replace '^ALL$','NVDA')
  $csv = Join-Path $repoRoot ("data\{0}_1m.csv" -f $sym)
  if(Test-Path -LiteralPath $csv){
    $rows = Import-Csv -LiteralPath $csv
    if($rows.Count -ge 3){
      $n = [Math]::Min([int]$WindowBars, [int]($rows.Count-1))
      $slice = $rows[($rows.Count-1-$n)..($rows.Count-1)]
      $rets = @()
      for($i=1; $i -lt $slice.Count; $i++){
        $p0 = [double]$slice[$i-1].close
        $p1 = [double]$slice[$i].close
        if($p0 -gt 0){ $rets += (($p1/$p0) - 1.0) }
      }
      if($rets.Count -ge 30){
        $mean = ($rets | Measure-Object -Average).Average
        $ss = 0.0
        foreach($r in $rets){ $ss += [Math]::Pow(($r - $mean),2) }
        $std = [Math]::Sqrt($ss / [Math]::Max(1, ($rets.Count-1)))
        $rvStd = $std
        if($std -ge $HighVolStd){
          $regime = "HIGH_VOL"
          $reason = ("realized_std_ge_threshold std=" + $std)
        } else {
          $regime = "NORMAL"
          $reason = ("realized_std_lt_threshold std=" + $std)
        }
      } else { $reason = "insufficient_bars_for_vol" }
    } else { $reason = "insufficient_rows_in_csv" }
  } else { $reason = "missing_data_csv" }
}

$nowUtc = (Get-Date).ToUniversalTime()
$out = [ordered]@{
  ts_utc = $nowUtc.ToString("o")
  symbol = $Symbol
  market = $Market
  as_of_date = $rc_as_of_date
  as_of_date_source = $rc_as_of_date_source
  market_closed_today = [bool]$rc_market_closed_today
  market_closed_reason = $rc_market_closed_reason
  is_open_now = [bool]$rc_is_open_now
  session_name = $rc_session_name
  is_trading_day = [bool]$rc_is_trading_day
  regime = $regime
  regime_ok_today = $true
  regime_reason = $reason
  realized_std_1m = $rvStd
  crisis_regime = [bool]$crisis
}
# RUNCONTEXT_OK_TODAY_BEGIN
if(-not $rc){
  $out["regime_ok_today"] = $false
  $out["regime_reason"] = "runcontext_unreadable"
} else {
  $out["regime_reason"] = $reason
}
# RUNCONTEXT_OK_TODAY_END

$outPath = Join-Path $logsDirOut "regime_status.json"
Write-Utf8NoBomLf $outPath ($out | ConvertTo-Json -Depth 6)
Write-Host ("[REGIME] wrote " + $outPath + " regime=" + $regime + " reason=" + $reason) -ForegroundColor Green
exit 0
