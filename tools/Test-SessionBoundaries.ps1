[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",
  [Parameter(Mandatory=$true)]
  [string]$BarsPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Fail([string]$Msg){
  Write-Host ("[SESSION-CHECK] FAIL-CLOSED: " + $Msg) -ForegroundColor Red
  exit 2
}

if(-not (Test-Path -LiteralPath $BarsPath)){ Fail "Missing BarsPath: $BarsPath" }

# America/New_York on Windows
try { $tz = [System.TimeZoneInfo]::FindSystemTimeZoneById("Eastern Standard Time") }
catch { Fail "Could not load Windows TZ 'Eastern Standard Time'" }

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
  foreach($cand in @("timestamp","time","datetime","date","t","ts")){
    $hit = $cols | Where-Object { $_.ToLowerInvariant() -eq $cand }
    if($hit){ $tsCol = $hit[0]; break }
  }
  if(-not $tsCol){
    $hit2 = $cols | Where-Object { $_.ToLowerInvariant() -match 'time|date' } | Select-Object -First 1
    if($hit2){ $tsCol = $hit2 }
  }
  if(-not $tsCol){ Fail ("Could not detect timestamp column. Columns=" + ($cols -join ",")) }

  foreach($r in $rows){
    $v = [string]($r.$tsCol)
    if(-not $v){ Fail "Empty timestamp" }
    try {
      $dt = [DateTime]::Parse($v, [System.Globalization.CultureInfo]::InvariantCulture,
        [System.Globalization.DateTimeStyles]::AssumeUniversal)
      $ts.Add($dt.ToUniversalTime())
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
      $dt = [DateTime]::Parse($v, [System.Globalization.CultureInfo]::InvariantCulture,
        [System.Globalization.DateTimeStyles]::AssumeUniversal)
      $ts.Add($dt.ToUniversalTime())
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
