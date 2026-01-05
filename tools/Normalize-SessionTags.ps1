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
foreach($cand in @("timestamp","time","datetime","date","t","ts")){
  $hit = $cols | Where-Object { $_.ToLowerInvariant() -eq $cand }
  if($hit){ $tsCol = $hit[0]; break }
}
if(-not $tsCol){
  $hit2 = $cols | Where-Object { $_.ToLowerInvariant() -match 'time|date' } | Select-Object -First 1
  if($hit2){ $tsCol = $hit2 }
}
if(-not $tsCol){ Fail ("Could not detect timestamp column. Columns=" + ($cols -join ",")) }

# ZoneInfo (py not allowed; use .NET)
try {
  $tz = [System.TimeZoneInfo]::FindSystemTimeZoneById("Eastern Standard Time")
} catch {
  Fail "Could not load Windows TZ 'Eastern Standard Time'"
}

# Tagging boundaries (ET)
# PRE: 04:00-09:30, RTH: 09:30-16:00, POST: 16:00-20:00, else: OFF
foreach($r in $rows){
  $v = [string]($r.$tsCol)
  if(-not $v){ Fail "Empty timestamp value found" }
  try {
    $dt = [DateTime]::Parse($v, [System.Globalization.CultureInfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::AssumeUniversal)
    $utc = $dt.ToUniversalTime()
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
