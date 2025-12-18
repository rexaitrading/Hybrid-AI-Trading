[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)][string]$AsOf = ""
)

Set-StrictMode -Version Latest

function Resolve-RepoRoot {
  # 0) ENV override is single truth
  $envRoot = (($env:HAT_REPO_ROOT + "")).Trim()
  if($envRoot){
    $full = [System.IO.Path]::GetFullPath($envRoot)
    if(Test-Path -LiteralPath (Join-Path $full "logs")){ return $full }
    if(Test-Path -LiteralPath $full){ return $full }
  }

  # 1) fallback: walk up from script path to find .git
  $scriptPath = $PSCommandPath
  if([string]::IsNullOrWhiteSpace($scriptPath)){ $scriptPath = $MyInvocation.MyCommand.Path }
  if([string]::IsNullOrWhiteSpace($scriptPath)){ throw "[REPOROOT] cannot resolve script path" }

  $d = Split-Path -Parent $scriptPath
  while($true){
    if(Test-Path -LiteralPath (Join-Path $d ".git")){ return $d }
    $parent = Split-Path -Parent $d
    if([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $d){ break }
    $d = $parent
  }
  throw "[REPOROOT] Could not find .git and no HAT_REPO_ROOT set"
}
if([string]::IsNullOrWhiteSpace($scriptPath)){ throw "[EV-HARD] cannot resolve script path" }

  $d = Split-Path -Parent $scriptPath
  while($true){
    if(Test-Path -LiteralPath (Join-Path $d ".git")){ return $d }
    $parent = Split-Path -Parent $d
    if([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $d){ break }
    $d = $parent
  }
  throw "[EV-HARD] Could not find .git by walking up from $scriptPath"
}
$ErrorActionPreference="Stop"

$repoRoot = Resolve-RepoRoot
$repoRoot = Resolve-RepoRoot
Set-Location $repoRoot

$logsDir = Join-Path $repoRoot "logs"
if(-not (Test-Path $logsDir)){ New-Item -ItemType Directory -Force -Path $logsDir | Out-Null }

$today = if($AsOf){ $AsOf } else { (Get-Date).ToString("yyyy-MM-dd") }
$path  = Join-Path $logsDir "phase5_ev_hard_veto_daily.csv"

# Canonical schema
$header = "date,ok,reason"

# INPUT HOOK (computed): later wire to real EV-hard snapshot output.
# For now, compute from presence of a placeholder "ev_hard_snapshot.json" with today's date and ok=true.
$snap = Join-Path $logsDir "ev_hard_snapshot.json"

# --- EVHARD_DEBUG_PATHS ---
Write-Host "[EV-HARD] logsDir=$logsDir" -ForegroundColor DarkCyan
Write-Host "[EV-HARD] snap=$snap exists=$((Test-Path $snap))" -ForegroundColor DarkCyan
# --- END EVHARD_DEBUG_PATHS ---
$ok = $false
$reason = "missing_inputs"

if(Test-Path $snap){
  try {
    $raw = Get-Content $snap -Raw -Encoding utf8
    if ($raw.Length -gt 0 -and [int][char]$raw[0] -eq 65279) { $raw = $raw.TrimStart([char]65279) }
    $o = $raw | ConvertFrom-Json -ErrorAction Stop
    if([string]$o.as_of_date -eq $today -and [bool]$o.ok -eq $true){
      $ok = $true
      $reason = "computed_from_ev_hard_snapshot"
    } else {
      $ok = $false
      $reason = "snapshot_not_ok_or_stale"
    }
  } catch {
    $ok = $false
    $reason = "snapshot_parse_failed"
  }
}

$row = "$today," + ($(if($ok){"true"}else{"false"})) + ",$reason"

$lines = @()
if(Test-Path $path){
  $lines = @(Get-Content $path -Encoding utf8)
  if($lines.Count -eq 0){ $lines = @($header) }
  if($lines[0].Trim() -ne $header){ $lines = @($header) + $lines }
} else {
  $lines = @($header)
}

$lines = $lines | Where-Object { $_ -notmatch "^$today," }
$lines = $lines + $row

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($path, ($lines -join "`n") + "`n", $utf8NoBom)

Write-Host "[EV-HARD] computed -> $row" -ForegroundColor Green
exit 0