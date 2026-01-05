[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$BarsPath,
  [string]$OutPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Fail([string]$Msg){
  Write-Host ("[SESSION-NORM] FAIL-CLOSED: " + $Msg) -ForegroundColor Red
  exit 2
}

if(-not (Test-Path -LiteralPath $BarsPath)){ Fail "Missing BarsPath: $BarsPath" }

# Load CSV
try { $rows = Import-Csv -LiteralPath $BarsPath } catch { Fail ("Import-Csv failed: " + $_.Exception.Message) }
if(-not $rows -or $rows.Count -lt 3){ Fail "Too few rows (<3)" }

# Detect timestamp column
$cols = @($rows[0].PSObject.Properties.Name)
$tsCol = $null
foreach($cand in @("ts","timestamp","time","datetime","date")){
  $hit = $cols | Where-Object { $_.ToLowerInvariant() -eq $cand }
  if($hit){ $tsCol = [string]$hit; break }
}
if(-not $tsCol){ Fail ("Could not detect timestamp column. Columns=" + ($cols -join ",")) }

# ZoneInfo (py not allowed; use .NET)
try {
  $tz = [System.TimeZoneInfo]::FindSystemTimeZoneById("Eastern Standard Time")
} catch {
  Fail "Could not load Windows TZ 'Eastern Standard Time'"
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
function Try-ParseTsUtc([string]$S){
  $s2 = ($S + "").Trim()
  $ci = [System.Globalization.CultureInfo]::InvariantCulture
  try {
    if($s2.EndsWith("Z") -or $s2.Contains("T")){
      $dtz = [DateTime]::Parse($s2, $ci, [System.Globalization.DateTimeStyles]::AssumeUniversal)
      return $dtz.ToUniversalTime()
    }
    $dtLocal = [DateTime]::ParseExact($s2, [string[]]$TS_FORMATS, $ci, [System.Globalization.DateTimeStyles]::None)
    $dtLocal = [DateTime]::SpecifyKind($dtLocal, [DateTimeKind]::Unspecified)
    return [System.TimeZoneInfo]::ConvertTimeToUtc($dtLocal, $tz)
  } catch {
    return $null
  }
}
}

# Tagging boundaries (ET)
# PRE: 04:00-09:30, RTH: 09:30-16:00, POST: 16:00-20:00, else: OFF
foreach($r in $rows){
  if(-not ($rows[0].PSObject.Properties.Name -contains $tsCol)){
  Fail ("Timestamp column not present tsCol=" + $tsCol + " cols=" + ($cols -join ","))
}
$v = [string]($r.PSObject.Properties[$tsCol].Value)
  if(-not $v){ Fail "Empty timestamp value found" }
  try {
    $utc = Try-ParseTsUtc -S $v
    if(-not $utc){ throw "bad_ts" }
    $et  = [System.TimeZoneInfo]::ConvertTimeFromUtc($utc, $tz)

    $tod = $et.TimeOfDay
    $pre0  = [TimeSpan]::FromHours(4)
    $rth0  = [TimeSpan]::FromHours(9) + [TimeSpan]::FromMinutes(30)
    $rth1  = [TimeSpan]::FromHours(16)
    $post1 = [TimeSpan]::FromHours(20)

    $tag = "OFF"
    if($tod -ge $pre0 -and $tod -lt $rth0){ $tag = "PRE" }
    elseif($tod -ge $rth0 -and $tod -lt $rth1){ $tag = "RTH" }
    elseif($tod -ge $rth1 -and $tod -lt $post1){ $tag = "POST" }

    Add-Member -InputObject $r -NotePropertyName "session_tag" -NotePropertyValue $tag -Force
  } catch {
    Fail ("Unparseable timestamp: " + $v)
  }
}

if(-not $OutPath){
  $p = [System.IO.Path]::GetFullPath($BarsPath)
  $dir = [System.IO.Path]::GetDirectoryName($p)
  $name = [System.IO.Path]::GetFileNameWithoutExtension($p)
  $ext = [System.IO.Path]::GetExtension($p)
  $OutPath = [System.IO.Path]::Combine($dir, ($name + ".session" + $ext))
}

try {
  $rows | Export-Csv -LiteralPath $OutPath -NoTypeInformation
} catch {
  Fail ("Export-Csv failed: " + $_.Exception.Message)
}

Write-Host ("[SESSION-NORM] OK wrote=" + $OutPath) -ForegroundColor Green
exit 0
