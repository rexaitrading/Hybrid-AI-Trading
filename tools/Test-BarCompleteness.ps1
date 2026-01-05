[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",
  [Parameter(Mandatory=$true)]
  [string]$BarsPath,
  [ValidateSet("AUTO","RTH","ALL")]
  [string]$Window = "AUTO"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Msg){
  Write-Host ("[BAR-CHECK] FAIL-CLOSED: " + $Msg) -ForegroundColor Red
  exit 2
}

if(-not (Test-Path -LiteralPath $BarsPath)){ Fail "Missing BarsPath: $BarsPath" }

# --- Load CSV (minimal dependency) ---
$rows = @()
try {
  $rows = Import-Csv -LiteralPath $BarsPath
} catch {
  Fail ("Import-Csv failed: " + $_.Exception.Message)
}
if(-not $rows -or $rows.Count -lt 3){ Fail "Too few rows (<3) to validate" }

# --- Detect timestamp column ---
$cols = @($rows[0].PSObject.Properties.Name)
$tsCol = $null
foreach($cand in @("ts","timestamp","time","datetime","date")){
  $hit = $cols | Where-Object { $_.ToLowerInvariant() -eq $cand }
  if($hit){ $tsCol = $hit[0]; break }
}
if(-not $tsCol){
  # fallback: first column containing 'time' or 'date'
  $hit2 = $cols | Where-Object { $_.ToLowerInvariant() -match 'time|date' } | Select-Object -First 1
  if($hit2){ $tsCol = $hit2 }
}
if(-not $tsCol){ Fail ("Could not detect timestamp column. Columns=" + ($cols -join ",")) }

# --- Parse timestamps robustly (assume UTC or local; we only need deltas) ---
$ts = New-Object System.Collections.Generic.List[DateTime]
foreach($r in $rows){
  if(-not ($r.PSObject.Properties.Name -contains $tsCol)){
  Fail ("Timestamp column not present tsCol=" + $tsCol + " cols=" + ($cols -join ","))
}
$v = [string]($r.PSObject.Properties[$tsCol].Value)
  if(-not $v){ Fail "Empty timestamp value found" }
  try {
    $dt = # ParseExact for IB-style "yyyyMMdd  HH:mm:ss" (double-space) and single-space fallback
$formats = @("yyyyMMdd  HH:mm:ss","yyyyMMdd HH:mm:ss","yyyy-MM-dd HH:mm:ss","yyyy-MM-ddTHH:mm:ss","o")
$dt = $null
$ok = $false
foreach($fmt in $formats){
  try {
    $dt = [DateTime]::ParseExact($v, $fmt, [System.Globalization.CultureInfo]::InvariantCulture,
      [System.Globalization.DateTimeStyles]::AssumeUniversal)
    $ok = $true
    break
  } catch { }
}
if(-not $ok){
  Fail ("Unparseable timestamp: " + $v)
}
$ts.Add($dt.ToUniversalTime())
  } catch {
    Fail ("Unparseable timestamp: " + $v)
  }
}

# --- Uniqueness ---
$uniq = @($ts | Sort-Object -Unique)
if($uniq.Count -ne $ts.Count){
  Fail ("Duplicate timestamps detected: total=" + $ts.Count + " unique=" + $uniq.Count)
}

# --- Monotonic increasing ---
for($i=1; $i -lt $ts.Count; $i++){
  if($ts[$i] -lt $ts[$i-1]){
    Fail ("Non-monotonic timestamps at i=" + $i + " prev=" + $ts[$i-1].ToString("o") + " cur=" + $ts[$i].ToString("o"))
  }
}

# --- Infer cadence: most common delta in seconds ---
$deltas = @()
for($i=1; $i -lt $ts.Count; $i++){
  $d = ($ts[$i] - $ts[$i-1]).TotalSeconds
  if($d -gt 0 -and $d -lt 3600){ $deltas += [int][Math]::Round($d) }
}
if($deltas.Count -lt 2){ Fail "Cannot infer cadence (insufficient deltas)" }

$cad = ($deltas | Group-Object | Sort-Object Count -Descending | Select-Object -First 1).Name
$cad = [int]$cad
if($cad -notin @(60,300)){
  Write-Host ("[BAR-CHECK] WARN: unusual cadence_sec=" + $cad + " (expected 60 or 300)") -ForegroundColor Yellow
}

# --- Gap detection: any gap > 2x cadence is fail ---
for($i=1; $i -lt $ts.Count; $i++){
  $gap = [int][Math]::Round(($ts[$i] - $ts[$i-1]).TotalSeconds)
  if($gap -gt (2*$cad)){
    Fail ("Gap detected gap_sec=" + $gap + " cadence_sec=" + $cad + " at=" + $ts[$i].ToString("o"))
  }
}

# --- Expected bar count (RTH only) ---
# RTH window 09:30-16:00 ET => 6.5h => 390 minutes
# count = 390 for 1m, 78 for 5m
$expected = $null
if($cad -eq 60){ $expected = 390 }
elseif($cad -eq 300){ $expected = 78 }

if($expected -ne $null){
  # We don't know if file is RTH-only; only enforce strictly when Window=RTH or AUTO and rowcount is near expected
  if($Window -eq "RTH"){
    if($ts.Count -ne $expected){
      Fail ("RTH bar_count mismatch count=" + $ts.Count + " expected=" + $expected + " cadence_sec=" + $cad)
    }
  } else {
    Write-Host ("[BAR-CHECK] INFO: cadence_sec=" + $cad + " count=" + $ts.Count + " expected_RTH=" + $expected) -ForegroundColor DarkGray
  }
}

Write-Host ("[BAR-CHECK] OK symbol=" + $Symbol + " ts_col=" + $tsCol + " cadence_sec=" + $cad + " count=" + $ts.Count) -ForegroundColor Green
exit 0
