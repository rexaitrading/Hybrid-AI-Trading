[CmdletBinding()]
param(
    [ValidateSet("NVDA","SPY","QQQ","ALL")]
    [string]$Symbol = "ALL",
    [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
    [string]$Market = "",
    [switch]$StrictToday
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

# Market-aware logs dir
$m = (($Market + "")).Trim().ToUpperInvariant()
if(-not $m){ $m = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant() }
if(-not $m){ $m = "US" }
$Market = $m

$gm = Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1"
# A3_GS_PNL_BEGIN
$logsDir = (($env:HAT_LOGS_DIR + "")).Trim()
if($env:HAT_MARKET -and (-not $logsDir)){ throw "[FAIL-CLOSED] HAT_MARKET set but HAT_LOGS_DIR missing (A3 wiring required)" }
if(-not $logsDir){ $logsDir = Join-Path $repoRoot "logs" }
# A3_GS_PNL_END
if(Test-Path -LiteralPath $gm){
  $ld = (& "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $gm -Market $Market | Out-String).Trim()
  if($ld){ $logsDir = $ld }
} else {
  $logsDir = Join-Path (Join-Path $repoRoot "logs") $Market
}
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

# Market-aware today (RunContext)
# A3_GS_PNL_TODAY_BEGIN
$today = (($env:HAT_AS_OF_DATE + "")).Trim()
if(-not $today){ $today = (($env:HAT_ASOF_DATE + "")).Trim() }  # legacy fallback
if(-not $today){
  $rcPath = Join-Path $repoRoot "tools\Resolve-RunContext.ps1"
  if(Test-Path -LiteralPath $rcPath){
    $rawRc = (& $rcPath -Market $Market -Symbol NVDA | Out-String).Trim()
    $i0=$rawRc.IndexOf("{"); $i1=$rawRc.LastIndexOf("}")
    if($i0 -ge 0 -and $i1 -gt $i0){ $rc = ($rawRc.Substring($i0, ($i1-$i0+1))) | ConvertFrom-Json }
    if($rc -and $rc.as_of_date){ $today = ([string]$rc.as_of_date).Substring(0,10) }
  }
}
if(-not $today -and $env:HAT_MARKET){ throw "[FAIL-CLOSED] missing as_of_date for market context" }
if($today.Length -ge 10){ $today = $today.Substring(0,10) }
$env:HAT_AS_OF_DATE = $today
# A3_GS_PNL_TODAY_END
try{
  $rcPath = Join-Path $repoRoot "tools\Resolve-RunContext.ps1"
  if(Test-Path -LiteralPath $rcPath){
    $rawRc = (& $rcPath -Market $Market -Symbol NVDA | Out-String).Trim()
    $i0 = $rawRc.IndexOf("{"); $i1 = $rawRc.LastIndexOf("}")
    if($i0 -ge 0 -and $i1 -gt $i0){
      $rc = ($rawRc.Substring($i0, ($i1-$i0+1))) | ConvertFrom-Json
      if($rc -and $rc.as_of_date){ $today = ([string]$rc.as_of_date).Substring(0,10) }
    }
  }
} catch { }

$outPath = Join-Path $logsDir "gatescore_pnl_summary.csv"
# ------------------------------
# FAST PATH: NVDA-only JSONL scan (PS5-safe; no ConvertFrom-Json)
# ------------------------------
function _TryMatchDate([string]$s){
  if(-not $s){ return "" }
  $m = [regex]::Match($s, '"as_of_date"\s*:\s*"(?<d>\d{4}-\d{2}-\d{2})"')
  if($m.Success){ return $m.Groups["d"].Value }
  $m = [regex]::Match($s, '"(ts_utc|ts|timestamp)"\s*:\s*"(?<d>\d{4}-\d{2}-\d{2})')
  if($m.Success){ return $m.Groups["d"].Value }
  return ""
}
function _HasEligibleTrue([string]$s){
  if(-not $s){ return $true }
  if($s -match '"eligible"\s*:\s*false'){ return $false }
  if($s -match '"eligible"\s*:\s*true'){ return $true }
  return $true
}
function _TryNum([string]$s,[string[]]$keys){
  foreach($k in $keys){
    $m = [regex]::Match($s, '"' + [regex]::Escape($k) + '"\s*:\s*(?<n>-?\d+(\.\d+)?)')
    if($m.Success){ return [double]$m.Groups["n"].Value }
  }
  return $null
}
function _StageToLocal([string]$Path){
  $dstDir = "C:\Trading\tmp"
  if(-not (Test-Path -LiteralPath $dstDir)){ New-Item -ItemType Directory -Force -Path $dstDir | Out-Null }
  $dst = Join-Path $dstDir ("nvda_gs_" + (Get-Date).ToString("yyyyMMdd_HHmmss") + ".jsonl")
  Copy-Item -LiteralPath $Path -Destination $dst -Force
  return $dst
}
function Fast-NvdaSummaryFromJsonl([string]$Path,[string]$TargetDate){
  $cnt = 0
  $edgeSum=0.0; $edgeN=0
  $microSum=0.0; $microN=0
  $pnlSum=0.0; $pnlN=0
  if(-not (Test-Path -LiteralPath $Path)){ throw ("Missing file: " + $Path) }
  foreach($ln0 in [System.IO.File]::ReadLines([System.IO.Path]::GetFullPath($Path))){
  # (streamed)
      $ln = ($ln0+"").Trim()
      if(-not $ln){ continue }
      $d = _TryMatchDate $ln
      if($d -ne $TargetDate){ continue }
      if(-not (_HasEligibleTrue $ln)){ continue }
      $cnt++
      $v = _TryNum $ln @("edge_ratio","mean_edge_ratio","edge","ev_edge_ratio")
      if($null -ne $v){ $edgeSum += $v; $edgeN++ }
      $v = _TryNum $ln @("micro_score","mean_micro_score","micro","micro_score_today")
      if($null -ne $v){ $microSum += $v; $microN++ }
      $v = _TryNum $ln @("realized_pnl","pnl","net_pnl","pnl_usd")
      if($null -ne $v){ $pnlSum += $v; $pnlN++ }
  }
  $pnlSamples = $cnt
  if($pnlN -gt 0){ $pnlSamples = $pnlN }
  $meanEdge = 0.0
  if($edgeN -gt 0){ $meanEdge = $edgeSum / [double]$edgeN }
  $meanMicro = 0.0
  if($microN -gt 0){ $meanMicro = $microSum / [double]$microN }
  $meanPnl = 0.0
  if($pnlN -gt 0){ $meanPnl = $pnlSum / [double]$pnlN }
  return [pscustomobject]@{
    count_signals    = [int]$cnt
    pnl_samples      = [int]$pnlSamples
    mean_edge_ratio  = [double]$meanEdge
    mean_micro_score = [double]$meanMicro
    mean_pnl         = [double]$meanPnl
    has_eligible     = [bool]($cnt -gt 0)
  }
}
function Resolve-EventFile([string]$logsDir,[string]$sym){
    $std  = Join-Path $logsDir ("{0}_gatescore_events.jsonl" -f $sym.ToLower())
    $real = Join-Path $logsDir ("{0}_gatescore_events_real.jsonl" -f $sym.ToLower())
    # Institutional: prefer canonical std file when it is non-trivial (avoid full-file scans).
    # Reason: std can be large (tens of MB). Scanning entire file to find max_date is slow and fragile.
    $STD_MIN_BYTES = 1048576  # 1MB
    $hasStd  = Test-Path -LiteralPath $std
    $hasReal = Test-Path -LiteralPath $real
    if((-not $hasStd) -and (-not $hasReal)){ return "" }
    if($hasStd){
        try {
            $len = (Get-Item -LiteralPath $std).Length
            if($len -ge $STD_MIN_BYTES){ return $std }
        } catch { return $std }
        # std exists but is small: still prefer it over real unless real is larger
        if(-not $hasReal){ return $std }
        try {
            $rlen = (Get-Item -LiteralPath $real).Length
            if($rlen -gt (Get-Item -LiteralPath $std).Length){ return $real }
        } catch { }
        return $std
    }
    return $real
}
function Resolve-StdOnlyFile([string]$logsDir,[string]$sym){
    $std = Join-Path $logsDir ("{0}_gatescore_events.jsonl" -f $sym.ToLower())
    if (Test-Path -LiteralPath $std) { return $std }
    return ""
}
function _SliceDate([string]$d) {
    if (-not $d) { return "" }
    if ($d.Length -ge 10) { return $d.Substring(0,10) }
    return $d
}
function _TryDouble([object]$v) {
    $x = 0.0
    if ($null -eq $v) { return $null }
    if ([double]::TryParse([string]$v, [ref]$x)) { return $x }
    return $null
}
function _TryString([object]$v) {
    if ($null -eq $v) { return "" }
    return [string]$v
}
function Read-Jsonl([string]$Path) {
    if([string]::IsNullOrWhiteSpace($Path)){ return @() }
    if (-not (Test-Path -LiteralPath $Path)) { return @() }

    $out = New-Object System.Collections.Generic.List[object]
    try {
        foreach($ln in [System.IO.File]::ReadLines([System.IO.Path]::GetFullPath($Path))) {
            $s = ($ln + "").Trim()
            if (-not $s) { continue }
            try {
                $o = ($s | ConvertFrom-Json)
                if($null -ne $o){ $out.Add($o) | Out-Null }
            } catch { }
        }
    } catch { }
    return $out.ToArray()
}
function Get-EventDate($e) {
    $props = $e.PSObject.Properties.Name
    foreach ($k in @("as_of_date","date","trading_day")) {
        if ($props -contains $k) {
            $v = _TryString ($e.$k)
            if ($v) { return _SliceDate $v }
        }
    }
    foreach ($k in @("ts_utc","ts","timestamp")) {
        if ($props -contains $k) {
            $t = _TryString ($e.$k)
            if ($t.Length -ge 10) { return $t.Substring(0,10) }
        }
    }
    return ""
}
function Get-Num($e, [string[]]$keys) {
    $props = $e.PSObject.Properties.Name
    foreach ($k in $keys) {
        if ($props -contains $k) {
            $v = _TryDouble ($e.$k)
            if ($null -ne $v) { return $v }
        }
    }
    return $null
}
function Mean($arr) {
    if ($arr.Count -eq 0) { return 0.0 }
    $sum = 0.0
    foreach ($v in $arr) { $sum += [double]$v }
    return $sum / [double]$arr.Count
}
function Get-EventPnlSamples($events) {
    $sum = 0
    foreach ($e in $events) {
        try {
            $v = $null
            if ($e -and ($e.PSObject.Properties.Name -contains "pnl_samples")) { $v = $e.pnl_samples }
            elseif ($e -and ($e.PSObject.Properties.Name -contains "pnlSamples")) { $v = $e.pnlSamples }
            elseif ($e -and ($e.PSObject.Properties.Name -contains "sample_count")) { $v = $e.sample_count }
            elseif ($e -and ($e.PSObject.Properties.Name -contains "samples")) { $v = $e.samples }

            if ($null -eq $v) { continue }
            $s = ([string]$v)
            if ([string]::IsNullOrWhiteSpace($s)) { continue }

            $n = 0
            if ([int]::TryParse($s, [ref]$n)) { $sum += $n; continue }

            $d = 0.0
            if ([double]::TryParse($s, [ref]$d)) { $sum += [int]$d; continue }
        } catch { }
    }
    return [int]$sum
}
$eventFiles = @(
    @{ sym="NVDA"; path=(Resolve-StdOnlyFile $logsDir "NVDA"); std=(Resolve-StdOnlyFile $logsDir "NVDA") },
    @{ sym="SPY";  path=(Resolve-EventFile $logsDir "SPY");  std=(Resolve-StdOnlyFile $logsDir "SPY") },
    @{ sym="QQQ";  path=(Resolve-EventFile $logsDir "QQQ");  std=(Resolve-StdOnlyFile $logsDir "QQQ") }
)
$wanted = @()
switch ($Symbol.ToUpperInvariant()) {
    "NVDA" { $wanted = @("NVDA") }
    "SPY"  { $wanted = @("SPY") }
    "QQQ"  { $wanted = @("QQQ") }
    "ALL"  { $wanted = @("NVDA","SPY","QQQ") }
}
$rowsOut = New-Object System.Collections.Generic.List[object]
foreach ($it in $eventFiles) {
    $sym = [string]$it.sym
    if ($wanted -notcontains $sym) { continue }
    $path = [string]$it.path
    if([string]::IsNullOrWhiteSpace($path) -or (-not (Test-Path -LiteralPath $path))){ continue }
    if($sym -eq "NVDA" -and ($wanted -contains "NVDA")){
      $targetDate = $today
      if(-not $StrictToday){ $targetDate = $today }
$local = _StageToLocal $path; $m = Fast-NvdaSummaryFromJsonl -Path $local -TargetDate $targetDate
      if(-not $m.has_eligible){
  if($StrictToday){
    continue
  }
  # Non-strict: write sentinel freshness row (zeros) so downstream ops wiring can proceed
  $row = [pscustomobject]@{
    as_of_date       = $targetDate
    symbol           = $sym
    count_signals    = 0
    pnl_samples      = 0
    mean_edge_ratio  = 0.0
    mean_micro_score = 0.0
    mean_pnl         = 0.0
    eligible_count   = 0
    has_eligible     = $false
  }
  $rowsOut.Add($row) | Out-Null
  continue
}
      $row = [pscustomobject]@{
        as_of_date       = $targetDate
        symbol           = $sym
        count_signals    = [int]$m.count_signals
        pnl_samples      = [int]$m.pnl_samples
        mean_edge_ratio  = [double]$m.mean_edge_ratio
        mean_micro_score = [double]$m.mean_micro_score
        mean_pnl         = [double]$m.mean_pnl
        eligible_count   = [int]$m.count_signals
        has_eligible     = [bool]$true
      }
      $rowsOut.Add($row) | Out-Null
      continue
    }
    $events = @(Read-Jsonl $path)
    # GS_SUMMARY_DEBUG_NVDA_BEGIN
    if($sym -eq "NVDA"){
      $mx = ""
      foreach($ee in $events){
        $ed = Get-EventDate $ee
        if($ed){
          if($mx -eq "" -or $ed -gt $mx){ $mx = $ed }
        }
      }
      Write-Host ("[GS-SUMMARY] NVDA path=" + $path + " max_date=" + $mx + " today=" + $today) -ForegroundColor Cyan
    }
    # GS_SUMMARY_DEBUG_NVDA_END
    $stdPath = [string]$it.std
    $stdEvents = @()
    if((-not [string]::IsNullOrWhiteSpace($stdPath)) -and (Test-Path -LiteralPath $stdPath)) { $stdEvents = @(Read-Jsonl $stdPath) }
    if ($events.Count -eq 0) { continue }
    
    # Determine latest event date in this file (fail-closed if none)
    $latest = ""
    foreach ($e in $events) {
        $ed = Get-EventDate $e
        if ($ed) {
            if ($latest -eq "" -or $ed -gt $latest) { $latest = $ed }
        }
    }
    if ($latest -eq "") { continue }
    $targetDate = if($StrictToday){ $today } else { $latest }
    if (-not $StrictToday -and $targetDate -ne $today) {
        Write-Host ("GateScore PnL summary: WARN {0} events are stale (latest={1}, today={2})" -f $sym,$targetDate,$today) -ForegroundColor Yellow
    }
    if ($StrictToday -and $latest -ne $today) {
        Write-Host ("GateScore PnL summary: STRICT-TODAY no events for today={0} (latest={1})" -f $today,$latest) -ForegroundColor Yellow
    }
$todayEvents = New-Object System.Collections.Generic.List[object]
    foreach ($e in $events) {
        if ((Get-EventDate $e) -eq $targetDate) { $todayEvents.Add($e) | Out-Null }
    }
$stdTodayEvents = New-Object System.Collections.Generic.List[object]
    if ($stdEvents.Count -gt 0) {
        foreach ($se in $stdEvents) {
            if ((Get-EventDate $se) -eq $targetDate) { $stdTodayEvents.Add($se) | Out-Null }
        }
        $stdTodayEvents = @($stdTodayEvents | Where-Object {
            -not ($_.PSObject.Properties.Name -contains "eligible") -or [bool]$_.eligible
        })
    }
    if ($todayEvents.Count -eq 0) { continue }
    # Drop ineligible events (fail-closed against zero-metric pollution)
    $todayEvents = @($todayEvents | Where-Object {
        -not ($_.PSObject.Properties.Name -contains "eligible") -or [bool]$_.eligible
    })
    # If no eligible events exist for targetDate:
    # - StrictToday => fail-closed (skip)
    # - Non-strict  => write sentinel freshness row (zeros) so Block-G can see latest date
    if ($todayEvents.Count -eq 0) {
        if ($StrictToday) { continue }
        $row = [pscustomobject]@{
            as_of_date       = $targetDate
            symbol           = $sym
            count_signals    = 0
            pnl_samples      = 0
            mean_edge_ratio  = 0.0
            mean_micro_score = 0.0
            mean_pnl         = 0.0
            has_eligible     = $false
        }
        $rowsOut.Add($row) | Out-Null
        continue
    }
    $edgeSourceEvents = if ($stdTodayEvents.Count -gt 0) { $stdTodayEvents } else { $todayEvents }
    $microSourceEvents = $edgeSourceEvents
    $pnlSourceEvents = $todayEvents
$edgeVals = New-Object System.Collections.Generic.List[double]
$microVals = New-Object System.Collections.Generic.List[double]
$pnlVals = New-Object System.Collections.Generic.List[double]
    foreach ($e in $pnlSourceEvents) {
        $pnl   = Get-Num $e @("realized_pnl","pnl","net_pnl","pnl_usd")
        if ($null -ne $pnl)   { $pnlVals.Add([double]$pnl) | Out-Null }
    }
    foreach ($e in $edgeSourceEvents) {
        $edge  = Get-Num $e @("edge_ratio","mean_edge_ratio","edge","ev_edge_ratio")
        if ($null -ne $edge)  { $edgeVals.Add([double]$edge) | Out-Null }
    }
    foreach ($e in $microSourceEvents) {
        $micro = Get-Num $e @("micro_score","mean_micro_score","micro","micro_score_today")
        if ($null -ne $micro) { $microVals.Add([double]$micro) | Out-Null }
    }
    # pnl_samples semantics:
    # 1) Prefer numeric pnl samples (realized_pnl count)
    # 2) Else fallback to declared per-event pnl_samples
    # 3) Else fallback to count_signals (wiring-safe)
    $rowPnlSamples = [int]$pnlVals.Count
    if ($rowPnlSamples -le 0) {
        $declSum = Get-EventPnlSamples $todayEvents
        if ($declSum -gt 0) { $rowPnlSamples = $declSum }
    }
    if ($rowPnlSamples -le 0) { $rowPnlSamples = [int]$todayEvents.Count }
    $row = [pscustomobject]@{
        as_of_date       = $targetDate
        symbol           = $sym
        count_signals    = [int]$todayEvents.Count
        pnl_samples      = [int]$rowPnlSamples
        mean_edge_ratio  = [double](Mean $edgeVals)
        mean_micro_score = [double](Mean $microVals)
        mean_pnl         = [double](Mean $pnlVals)
        eligible_count  = [int]$todayEvents.Count
        has_eligible    = [bool]($todayEvents.Count -gt 0)
    }
    $rowsOut.Add($row) | Out-Null
}
if ($rowsOut.Count -eq 0) {
    Write-Error "GateScore PnL summary: no usable 'today' events found. Refusing to write $outPath (fail-closed)."
    exit 2
}
$allZero = $true
foreach ($r in $rowsOut) {
    if ($r.count_signals -gt 0 -or $r.pnl_samples -gt 0 -or $r.mean_edge_ratio -ne 0.0 -or $r.mean_micro_score -ne 0.0 -or $r.mean_pnl -ne 0.0) {
        $allZero = $false; break
    }
}
if ($allZero) {
    if ($StrictToday) {
        Write-Error "GateScore PnL summary: computed rows are all zeros. Refusing to write $outPath (fail-closed)."
        exit 3
    }
    Write-Host "GateScore PnL summary: rows are zeros (sentinel freshness). Writing anyway (non-strict)." -ForegroundColor Yellow
}
Write-Host "GateScore PnL summary: writing $outPath" -ForegroundColor Cyan
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$csv = $rowsOut | Sort-Object symbol | ConvertTo-Csv -NoTypeInformation
[System.IO.File]::WriteAllLines($outPath, [string[]]$csv, $utf8NoBom)
Write-Host "GateScore PnL summary: sample rows:" -ForegroundColor Yellow
$rowsOut | Format-Table -AutoSize
exit 0
