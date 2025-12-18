[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)][string]$AsOf = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Resolve-RepoRoot {
  # 0) Single-truth tracked pointer: .hat\repo_root.txt (preferred, ASCII-safe)
  $rootFile = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.hat\repo_root.txt"))
  if(Test-Path -LiteralPath $rootFile){
    $s = (Get-Content -LiteralPath $rootFile -Raw -Encoding UTF8)
    if ($s.Length -gt 0 -and [int][char]$s[0] -eq 65279) { $s = $s.TrimStart([char]65279) }
    $p = $s.Trim()
    if($p){
      $full = [System.IO.Path]::GetFullPath($p)
      if(Test-Path -LiteralPath (Join-Path $full ".git")){ return $full }
      throw "[REPOROOT] .hat/repo_root.txt points to missing repo: $full"
    }
  }

  # 1) ENV override (secondary)
  $envRoot = (($env:HAT_REPO_ROOT + "")).Trim()
  if($envRoot){
    $full = [System.IO.Path]::GetFullPath($envRoot)
    if(Test-Path -LiteralPath (Join-Path $full ".git")){ return $full }
  }

  # 2) Fallback: walk up from script location to find .git
  $d = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
  while($true){
    if(Test-Path -LiteralPath (Join-Path $d ".git")){ return $d }
    $parent = Split-Path -Parent $d
    if([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $d){ break }
    $d = $parent
  }

  throw "[REPOROOT] Could not resolve repo root (.hat pointer/env/.git all failed)"
}
if(Test-Path -LiteralPath (Join-Path $full "logs")){ return $full }
    if(Test-Path -LiteralPath $full){ return $full }
  }

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

$repoRoot = Resolve-RepoRoot
Set-Location $repoRoot

$logsDir = Join-Path $repoRoot "logs"
if(-not (Test-Path $logsDir)){ New-Item -ItemType Directory -Force -Path $logsDir | Out-Null }

$today = if($AsOf){ $AsOf } else { (Get-Date).ToString("yyyy-MM-dd") }
$path  = Join-Path $logsDir "phase5_ev_hard_veto_daily.csv"

$header = "date,ok,reason"
$snap   = Join-Path $logsDir "phase5_ev_hard_veto_snapshot.json"
Write-Host "[EV-HARD] logsDir=$logsDir" -ForegroundColor DarkCyan
Write-Host "[EV-HARD] snap=$snap exists=$((Test-Path $snap))" -ForegroundColor DarkCyan

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
      if($o.PSObject.Properties.Name -contains "reason" -and $o.reason){ $reason = [string]$o.reason }
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

$lines = $lines | Where-Object { $_ -notmatch ("^{0}," -f [regex]::Escape($today)) }
$lines = $lines + $row

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($path, ($lines -join "`n") + "`n", $utf8NoBom)

Write-Host "[EV-HARD] computed -> $row" -ForegroundColor Green
exit 0
