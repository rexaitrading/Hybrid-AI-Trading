[CmdletBinding()]
param(
  [ValidateSet("PAPER","PAPERLIVE","LIVE")]
  [string]$Mode = "PAPERLIVE",

  [int]$TailLines = 250
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

try {
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [Console]::OutputEncoding = $utf8
  [Console]::InputEncoding  = $utf8
  $global:OutputEncoding    = $utf8
} catch { }

function Fail([string]$m){
  Write-Host ("[FAIL-CLOSED] " + $m) -ForegroundColor Red
  exit 2
}

function SliceTail([string[]]$arr,[int]$n){
  if(-not $arr){ return @() }
  if($n -le 0){ return @() }
  if($arr.Count -le $n){ return $arr }
  return $arr[($arr.Count-$n)..($arr.Count-1)]
}

# Repo root (filesystem truth)
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
try { $repoRoot = (Resolve-Path -LiteralPath $repoRoot -ErrorAction Stop).Path } catch { }
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

$logsRoot = Join-Path $repoRoot "logs"
if(-not (Test-Path -LiteralPath $logsRoot)){
  Fail ("missing logs root: " + $logsRoot)
}

# Threshold
$modeU = ($Mode + "").Trim().ToUpperInvariant()
if($modeU -notin @("PAPER","PAPERLIVE","LIVE")){ Fail ("invalid -Mode=" + $Mode) }

$maxAge = 999999
if($modeU -eq "LIVE"){ $maxAge = 2 }
elseif($modeU -eq "PAPERLIVE"){ $maxAge = 10 }
else { $maxAge = 999999 }

"`n=== IBG WATCHDOG FRESHNESS CHECK ===" | Out-Host
("repoRoot=" + $repoRoot) | Out-Host
("logsRoot=" + $logsRoot) | Out-Host
("mode=" + $modeU + " max_age_min=" + $maxAge) | Out-Host
("now_local=" + (Get-Date).ToString("o")) | Out-Host
("now_utc=" + (Get-Date).ToUniversalTime().ToString("o")) | Out-Host

# Find newest watchdog log anywhere under logs/
# Find newest watchdog log in canonical locations only (FAIL-CLOSED; avoid polluted logs/** recursion)
$canon = @("US","JP","HK","HK_SH","HK_SZ","SG","IN","KR","TW")
$searchDirs = New-Object System.Collections.Generic.List[string]
$searchDirs.Add($logsRoot) | Out-Null
$d1 = Join-Path $logsRoot "scheduled"
if(Test-Path -LiteralPath $d1){ $searchDirs.Add($d1) | Out-Null }
$d2 = Join-Path $logsRoot "ops"
if(Test-Path -LiteralPath $d2){ $searchDirs.Add($d2) | Out-Null }
foreach($m in $canon){
  $dm = Join-Path $logsRoot $m
  if(Test-Path -LiteralPath $dm){ $searchDirs.Add($dm) | Out-Null }
}
$cands = @()
foreach($d in $searchDirs){
  try {
    $cands += @(Get-ChildItem -LiteralPath $d -File -Filter "ibg_api_watch_*.log" -ErrorAction SilentlyContinue)
  } catch { }
}
$cands = @($cands | Sort-Object LastWriteTimeUtc -Descending)

if(-not $cands -or $cands.Count -eq 0){
  "`n[RED] No ibg_api_watch_*.log found under logs/. Likely watcher not running or wrong filename." | Out-Host
  "`nSAFE FIX PATH (no changes applied):" | Out-Host
  "1) Confirm IBG watchdog task/service is running and writing logs." | Out-Host
  "2) Search for similar filenames under logs/: Get-ChildItem -Recurse -Filter '*ibg*watch*' logs" | Out-Host
  "3) If watcher writes elsewhere, update dashboard/watchdog path policy to point to canonical logs root." | Out-Host
  exit 2
}

$top = $cands[0]
$ageMin = [int][math]::Floor(((Get-Date).ToUniversalTime() - $top.LastWriteTimeUtc).TotalMinutes)

"`n=== NEWEST WATCHDOG LOG ===" | Out-Host
("path=" + $top.FullName) | Out-Host
("last_write_local=" + $top.LastWriteTime.ToString("o")) | Out-Host
("last_write_utc=" + $top.LastWriteTimeUtc.ToString("o")) | Out-Host
("age_min_utc=" + $ageMin) | Out-Host

# Read tail
$tail = @()
try { $tail = @(Get-Content -LiteralPath $top.FullName -Tail $TailLines -Encoding UTF8 -ErrorAction Stop) } catch { $tail = @() }

"`n=== TAIL (last $TailLines lines; showing up to 30 summary hits) ===" | Out-Host
$lastLine = if($tail.Count -gt 0){ [string]$tail[-1] } else { "" }
("last_line=" + $lastLine) | Out-Host

# Token scan
$hitsOk = 0
$hitsErr = 0
$hitsConn = 0
$hitsPortUp = 0
$hits1100 = 0
$hitsWatchErr = 0

foreach($ln in $tail){
  $s = ($ln + "")
  if($s -match "WATCH_OK"){ $hitsOk++ }
  if($s -match "CONNECTED"){ $hitsConn++ }
  if($s -match "PORT_UP"){ $hitsPortUp++ }
  if($s -match "Error 1100"){ $hits1100++ }
  if($s -match "WATCH_ERR"){ $hitsWatchErr++ }
  if($s -match "Error 1100" -or $s -match "Connectivity between IBKR" -or $s -match "positions request timed out" -or $s -match "WATCH_ERR"){ $hitsErr++ }
}

("hits: WATCH_OK=" + $hitsOk + " CONNECTED=" + $hitsConn + " PORT_UP=" + $hitsPortUp + " ERR_ANY=" + $hitsErr + " ERR1100=" + $hits1100 + " WATCH_ERR=" + $hitsWatchErr) | Out-Host

# Classify
$classification = "unknown"
$detail = ""

if($ageMin -gt $maxAge){
  $classification = "stale_file"
  $detail = ("age_min=" + $ageMin + " > max_age_min=" + $maxAge)
} elseif($hitsErr -gt 0){
  $classification = "fresh_but_error_tokens"
  $detail = ("age_min=" + $ageMin + " <= max but error tokens present")
} else {
  $classification = "fresh_and_ok"
  $detail = ("age_min=" + $ageMin + " <= max and no error tokens detected")
}

"`n=== RESULT ===" | Out-Host
("status_class=" + $classification) | Out-Host
("detail=" + $detail) | Out-Host

# Extra: detect whether file lives under market subfolder vs logs root
$rel = $top.FullName.Substring($logsRoot.Length).TrimStart('\','/')
("relative_under_logs=" + $rel) | Out-Host
if($rel -match '^(US|JP|HK|SG|IN|KR|TW|HK_SH|HK_SZ)\\'){
  "`n[NOTE] Watchdog log is inside a market folder. Dashboard currently scans logs root only (newest anywhere) - OK, but ensure policy stays consistent." | Out-Host
} else {
  "`n[NOTE] Watchdog log is not in a market folder. This is expected if watcher is global." | Out-Host
}

"`nSAFE FIX PATH (no changes applied):" | Out-Host
if($classification -eq "stale_file"){
  "A) Stale file: watcher likely stopped / Task Scheduler not running / PC sleep." | Out-Host
  "   1) Check Task Scheduler history for the IBG watchdog task around last_write_utc." | Out-Host
  "   2) Confirm PC did not sleep; if it did, enforce wake timers / resume triggers." | Out-Host
  "   3) Re-run the watchdog manually and verify it updates the log file timestamp." | Out-Host
} elseif($classification -eq "fresh_but_error_tokens"){
  "B) Fresh but errors: IBG connectivity is failing." | Out-Host
  "   1) Inspect last 200 lines of log for Error 1100 / WATCH_ERR root line." | Out-Host
  "   2) Confirm IB Gateway is running and API port reachable." | Out-Host
} else {
  "C) Fresh and OK: if dashboard still says stale, suspect time basis mismatch elsewhere." | Out-Host
  "   1) Confirm dashboard uses LastWriteTimeUtc and same maxAge thresholds." | Out-Host
}

exit 0
