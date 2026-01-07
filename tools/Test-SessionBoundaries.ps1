[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",
  [string]$BarsPath = ""
)

Set-StrictMode -Version Latest
# NONINTERACTIVE_BARSROOT_BEGIN
try {
  if (-not $BarsPath -or ($BarsPath + "").Trim().Length -eq 0) {
  }
} catch { }
# NONINTERACTIVE_BARSROOT_END
$ErrorActionPreference="Stop"

function Fail([string]$Msg){
  Write-Host ("[SESSION-CHECK] FAIL-CLOSED: " + $Msg) -ForegroundColor Red
  exit 2
}

# PH1_AUTO_BARSROOT_BEGIN
function Resolve-BarsPath([string]$Symbol,[string]$BarsPath){
  $sym = ($Symbol + "").ToUpperInvariant().Trim()
  $bp = ($BarsPath + "").Trim()

  if($bp){
    if(Test-Path -LiteralPath $bp){ return $bp }
    Fail ("Missing BarsPath: " + $bp)
  }

  $envp = ($env:HAT_BARS_ROOT + "").Trim()
  if($envp){
    if(Test-Path -LiteralPath $envp){
      $it = Get-Item -LiteralPath $envp
      if($it.PSIsContainer){
        $today = (Get-Date).ToString("yyyy-MM-dd")
        $cand = Join-Path $envp ("{0}_{1}_1m.csv" -f $sym,$today)
        if(Test-Path -LiteralPath $cand){ return $cand }
        $latest = Get-ChildItem -LiteralPath $envp -File -Filter ("{0}_*_1m.csv" -f $sym) -ErrorAction SilentlyContinue |
          Sort-Object Name | Select-Object -Last 1
        if($latest){ return $latest.FullName }
      } else {
        return $it.FullName
      }
    }
  }

  $barsDir = Join-Path (Split-Path -Parent $PSScriptRoot) "logs\bars"
  $today2 = (Get-Date).ToString("yyyy-MM-dd")
  $cand2 = Join-Path $barsDir ("{0}_{1}_1m.csv" -f $sym,$today2)
  if(Test-Path -LiteralPath $cand2){ return $cand2 }

  $latest2 = Get-ChildItem -LiteralPath $barsDir -File -Filter ("{0}_*_1m.csv" -f $sym) -ErrorAction SilentlyContinue |
    Sort-Object Name | Select-Object -Last 1
  if($latest2){ return $latest2.FullName }

  Fail ("Could not resolve bars file for symbol=" + $sym + " (set -BarsPath or env:HAT_BARS_ROOT)")
}
$BarsPath = Resolve-BarsPath -Symbol $Symbol -BarsPath $BarsPath
# PH1_AUTO_BARSROOT_END
if(-not (Test-Path -LiteralPath $BarsPath)){ Fail "Missing BarsPath: $BarsPath" }

# America/New_York on Windows
try { $tz = [System.TimeZoneInfo]::FindSystemTimeZoneById("Eastern Standard Time") }
catch { Fail "Could not load Windows TZ 'Eastern Standard Time'" }
# --- Timestamp parse allowlist (explicit, fail-closed) ---
$TS_FORMATS = @(
  "yyyyMMdd  HH:mm:ss",
  "yyyyMMdd HH:mm:ss",
  "yyyy-MM-dd HH:mm:ss",
  "yyyy-MM-ddTHH:mm:ss",
  "yyyy-MM-ddTHH:mm:ss.fff",
  "yyyy-MM-ddTHH:mm:ssZ",
  "yyyy-MM-ddTHH:mm:ss.fffZ"
)
function Try-ParseTs([string]$S){
  $s2 = ($S + "").Trim()
  $ci = [System.Globalization.CultureInfo]::InvariantCulture
  try {
    # If explicit Z/ISO, treat as UTC
    if($s2.EndsWith("Z") -or $s2.Contains("T")){
      $dtz = [DateTime]::Parse($s2, $ci, [System.Globalization.DateTimeStyles]::AssumeUniversal)
      return $dtz.ToUniversalTime()
    }
    # Otherwise, treat as ET-local clock time and convert to UTC
    $dtLocal = [DateTime]::ParseExact($s2, [string[]]$TS_FORMATS, $ci, [System.Globalization.DateTimeStyles]::None)
    $dtLocal = [DateTime]::SpecifyKind($dtLocal, [DateTimeKind]::Unspecified)
    return [System.TimeZoneInfo]::ConvertTimeToUtc($dtLocal, $tz)
  } catch {
    return $null
  }
}

function Get-Tag([DateTime]$utc){
  $et = [System.TimeZoneInfo]::ConvertTimeFromUtc($utc, $tz)
  $tod = $et.TimeOfDay
  $pre0  = [TimeSpan]::FromHours(4)
  $rth0  = [TimeSpan]::FromHours(9) + [TimeSpan]::FromMinutes(30)
  $rth1  = [TimeSpan]::FromHours(16)
  $post1 = [TimeSpan]::FromHours(20)

  if($tod -ge $pre0 -and $tod -lt $rth0){ return "PRE" }
  if($tod -ge $rth0 -and $tod -lt $rth1){ return "RTH" }
  if($tod -ge $rth1 -and $tod -lt $post1){ return "POST" }
  return "OFF"
}

# Load timestamps from CSV or JSONL
$ext = ([System.IO.Path]::GetExtension($BarsPath) + "").ToLowerInvariant()
$ts = New-Object System.Collections.Generic.List[DateTime]

if($ext -eq ".csv"){
  $rows = Import-Csv -LiteralPath $BarsPath
  if(-not $rows -or $rows.Count -lt 3){ Fail "Too few rows (<3)" }

  $cols = @($rows[0].PSObject.Properties.Name)
  $tsCol = $null
  foreach($cand in @("ts","timestamp","time","datetime","date")){
    $hit = $cols | Where-Object { $_.ToLowerInvariant() -eq $cand }
    if($hit){ $tsCol = [string]$hit; break }
  }
  if(-not $tsCol){ Fail ("Could not detect timestamp column. Columns=" + ($cols -join ",")) }

  foreach($r in $rows){
    if(-not ($rows[0].PSObject.Properties.Name -contains $tsCol)){
  Fail ("Timestamp column not present tsCol=" + $tsCol + " cols=" + ($cols -join ","))
}
$v = [string]($r.PSObject.Properties[$tsCol].Value)
    if(-not $v){ Fail "Empty timestamp" }
    try {
      $dt = Try-ParseTs -S $v
      if(-not $dt){ throw "bad_ts" }
      $ts.Add($dt)
    } catch { Fail ("Unparseable timestamp: " + $v) }
  }
}
elseif($ext -eq ".jsonl"){
  $lines = Get-Content -LiteralPath $BarsPath -Encoding utf8
  if(-not $lines -or $lines.Count -lt 3){ Fail "Too few lines (<3)" }

  foreach($ln in $lines){
    if(-not $ln.Trim()){ continue }
    try { $o = $ln | ConvertFrom-Json } catch { Fail "Invalid JSONL line" }

    $v = ""
    foreach($cand in @("ts","timestamp","time","datetime","date")){
      if($o.PSObject.Properties.Name -contains $cand){ $v = [string]$o.$cand; break }
    }
    if(-not $v){ Fail "JSONL missing timestamp field (ts/timestamp/time/datetime/date)" }

    try {
      $dt = Try-ParseTs -S $v
      if(-not $dt){ throw "bad_ts" }
      $ts.Add($dt)
    } catch { Fail ("Unparseable timestamp: " + $v) }
  }
}
else{
  Fail ("Unsupported extension: " + $ext + " (use .csv or .jsonl)")
}

if($ts.Count -lt 3){ Fail "No timestamps parsed" }

# Distribution check
$tags = @{}
foreach($d in $ts){
  $t = Get-Tag $d
  if(-not $tags.ContainsKey($t)){ $tags[$t]=0 }
  $tags[$t]++
}

# Fail-closed: must have meaningful RTH
if((-not $tags.ContainsKey("RTH")) -or ($tags["RTH"] -lt 10)){
  Fail ("Too few RTH bars detected (RTH=" + ($tags["RTH"] + 0) + ")")
}

Write-Host ("[SESSION-CHECK] OK symbol=" + $Symbol + " tags=" +
  (($tags.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ",")) -ForegroundColor Green
exit 0
