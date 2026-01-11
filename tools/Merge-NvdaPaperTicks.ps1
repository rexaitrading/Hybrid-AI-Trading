[CmdletBinding()]
param(
  [string]$LogsDir = ".\logs",
  [string]$StreamPath = ".\logs\nvda_paperlive_stream_today.jsonl",
  [string]$MarkerPath = ".\logs\nvda_paperlive_stream_today.last_merged.txt",
  [string]$LocalOutDir = "",
  [switch]$Trace
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Trace gate (hard OFF by default):
# enable if caller passed -Trace OR env:HAT_TRACE_MERGE is truthy
$envTrace = (([string]$env:HAT_TRACE_MERGE) + "").Trim().ToLowerInvariant()
$TraceEnabled = $false
if($PSBoundParameters.ContainsKey("Trace") -and $Trace.IsPresent){ $TraceEnabled = $true }
elseif($envTrace -in @("1","true","yes","y","on")){ $TraceEnabled = $true }

# Trace gate: enable via -Trace OR env:HAT_TRACE_MERGE=1/true/yes/on
$envTrace = (([string]$env:HAT_TRACE_MERGE) + "").Trim().ToLowerInvariant()
$TraceEnabled = $Trace -or ($envTrace -in @("1","true","yes","y","on"))


function Trace([string]$m){
  if(-not $TraceEnabled){ return }
  try {
    [System.IO.Directory]::CreateDirectory("C:\Trading\tmp") | Out-Null
    $p = ("C:\Trading\tmp\merge_trace_" + (Get-Date).ToString("yyyyMMdd") + ".txt")
    [System.IO.File]::AppendAllText($p, ((Get-Date).ToString("o") + " " + $m + "`n"), (New-Object System.Text.UTF8Encoding($false)))
  } catch {}
}
# --- Normalize paths first (NO OneDrive enumeration yet) ---
$logsFull   = [System.IO.Path]::GetFullPath($LogsDir)
$streamReal = [System.IO.Path]::GetFullPath($StreamPath)
$markerReal = [System.IO.Path]::GetFullPath($MarkerPath)
if($TraceEnabled){ Trace ("ENTER pid=" + $PID) }
if($TraceEnabled){ Trace ("LogsDir=" + $logsFull) }
if($TraceEnabled){ Trace ("StreamReal=" + $streamReal) }
if($TraceEnabled){ Trace ("MarkerReal=" + $markerReal) }
if($TraceEnabled){ Trace ("LocalOutDir=" + $LocalOutDir) }

if(-not [System.IO.Directory]::Exists($logsFull)){
  throw ("Missing LogsDir: " + $logsFull)
}

# --- If LocalOutDir set, write stream/marker locally, then copy back ---
$useStream = $streamReal
$useMarker = $markerReal
if($LocalOutDir){
  $localFull = [System.IO.Path]::GetFullPath($LocalOutDir)
  [System.IO.Directory]::CreateDirectory($localFull) | Out-Null
  $useStream = [System.IO.Path]::Combine($localFull, [System.IO.Path]::GetFileName($streamReal))
  $useMarker = [System.IO.Path]::Combine($localFull, [System.IO.Path]::GetFileName($markerReal))
}
if($TraceEnabled){ Trace ("UseStream=" + $useStream) }
if($TraceEnabled){ Trace ("UseMarker=" + $useMarker) }

# Ensure stream directory exists + file exists
$useStreamDir = [System.IO.Path]::GetDirectoryName($useStream)
if($useStreamDir){ [System.IO.Directory]::CreateDirectory($useStreamDir) | Out-Null }
if(-not [System.IO.File]::Exists($useStream)){
  [System.IO.File]::WriteAllText($useStream, "", (New-Object System.Text.UTF8Encoding($false)))
}

# Read last marker
$last = ""
if([System.IO.File]::Exists($useMarker)){
  try {
    $last = ([System.IO.File]::ReadAllLines($useMarker, [System.Text.Encoding]::UTF8) | Select-Object -First 1).Trim()
  } catch {}
}
if($TraceEnabled){ Trace ("LastMarker=" + $last) }

# --- Enumerate tick files via .NET (avoids OneDrive Get-ChildItem hangs) ---
# pattern: nvda_paperlive_tick_YYYYMMDD_HHMMSS.jsonl
if($TraceEnabled){ Trace "ENUM_BEGIN" }
$all = New-Object System.Collections.Generic.List[string]
foreach($p in [System.IO.Directory]::EnumerateFiles($logsFull, "nvda_paperlive_tick_*.jsonl", [System.IO.SearchOption]::TopDirectoryOnly)){
  $name = [System.IO.Path]::GetFileName($p)
  if($name -match '^nvda_paperlive_tick_\d{8}_\d{6}\.jsonl$'){
    $all.Add($p) | Out-Null
  }
}
$files = @($all | Sort-Object { [System.IO.Path]::GetFileName($_) })
if($TraceEnabled){ Trace ("ENUM_DONE total=" + $files.Count) }

# Filter by marker
if($last){
  $files = @($files | Where-Object { ([System.IO.Path]::GetFileName($_)) -gt $last })
}
if(-not $files -or $files.Count -eq 0){
  Write-Host "[MERGE] No new tick files to merge." -ForegroundColor Yellow
  exit 0
}

# Safety limit
$MAX_FILES = 2000
if($files.Count -gt $MAX_FILES){
  Write-Host ("[MERGE] WARN: too many tick files (" + $files.Count + "), limiting to " + $MAX_FILES) -ForegroundColor Yellow
  $files = @($files | Select-Object -First $MAX_FILES)
}

# Atomic append: copy existing stream -> tmp, append new ticks, then replace
$tmp = $useStream + ".tmp_" + (Get-Date).ToString("yyyyMMdd_HHmmss")
try { if([System.IO.File]::Exists($tmp)){ [System.IO.File]::Delete($tmp) } } catch {}

# Copy existing stream -> tmp
[System.IO.File]::Copy($useStream, $tmp, $true)

function AppendFile([string]$src,[string]$dst){
  $fs = [System.IO.File]::Open($src,[System.IO.FileMode]::Open,[System.IO.FileAccess]::Read,[System.IO.FileShare]::ReadWrite)
  try{
    $sr = New-Object System.IO.StreamReader($fs, [System.Text.Encoding]::UTF8, $true)
    try{
      $sw = New-Object System.IO.StreamWriter($dst, $true, (New-Object System.Text.UTF8Encoding($false)))
      try{
        while(-not $sr.EndOfStream){
          $line = $sr.ReadLine()
          if($null -ne $line){ $sw.WriteLine($line) }
        }
      } finally { $sw.Flush(); $sw.Dispose() }
    } finally { $sr.Dispose() }
  } finally { $fs.Dispose() }
}

$merged = 0
foreach($p in $files){
  try{
    $len = (New-Object System.IO.FileInfo($p)).Length
    if($len -le 0){ continue }
  } catch { continue }

  AppendFile -src $p -dst $tmp
  $last = [System.IO.Path]::GetFileName($p)
  $merged++
}

# Replace stream
[System.IO.File]::Copy($tmp, $useStream, $true)
try { [System.IO.File]::Delete($tmp) } catch {}

# Write marker
[System.IO.File]::WriteAllText($useMarker, ($last + "`n"), (New-Object System.Text.UTF8Encoding($false)))

Write-Host ("[MERGE] merged={0} last={1}" -f $merged,$last) -ForegroundColor Green

# Copy back to OneDrive real paths (best-effort)
if($LocalOutDir){
  try { [System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($streamReal)) | Out-Null } catch {}
  try { [System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($markerReal)) | Out-Null } catch {}
  try { [System.IO.File]::Copy($useStream, $streamReal, $true) } catch {}
  try { [System.IO.File]::Copy($useMarker, $markerReal, $true) } catch {}
}

exit 0